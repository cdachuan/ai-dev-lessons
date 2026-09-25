# -*- coding: utf-8 -*-
"""自研 ReAct 循环：决策归 AI，执行归代码。max_steps 兜底防死循环。

messages.append(msg) 先于遍历 msg.tool_calls；每个结果以 role=tool 塞回。
"""
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 注册扩展工具：ML 实验链 + 质量画像。必须用 tools.TOOL_REGISTRY 本体 update，
# 因为 execute_tool 闭包引用的是 tools 模块的注册表对象，重新绑定名字无效。
from data_agent import tools as _tools
from data_agent.tools import execute_tool
from data_agent.ml.tools import ML_TOOL_REGISTRY, TOOL_SCHEMAS_ML
from data_agent.ml.profile import profile_quality
from data_agent.governance.tools import GOV_TOOL_REGISTRY, GOV_TOOL_SCHEMAS

EXTRA_SCHEMAS = TOOL_SCHEMAS_ML + [{
    "type": "function",
    "function": {
        "name": "profile_quality",
        "description": "数据质量画像：每列缺失率、异常值、疑似脏列、目标分布。真实数据上跑任何实验前先调用；mock 数据也可用于确认数据干净。",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string"},
                "dict_file": {"type": "string", "description": "字典文件名，ML数据集用 dictionary_ml.yaml"},
            },
            "required": ["dataset"],
        },
    },
}]
_tools.TOOL_REGISTRY.update(ML_TOOL_REGISTRY)
_tools.TOOL_REGISTRY["profile_quality"] = profile_quality
_tools.TOOL_REGISTRY.update(GOV_TOOL_REGISTRY)
TOOL_SCHEMAS = _tools.TOOL_SCHEMAS + EXTRA_SCHEMAS + GOV_TOOL_SCHEMAS

from data_agent.dictionary import get_root as _get_root
from data_agent.project import get_project_root

def _load_env() -> None:
    """加载项目 .env；项目根未定时静默跳过（da use 等命令先于项目存在）。"""
    try:
        load_dotenv(get_project_root() / ".env")
    except ValueError:
        pass

_load_env()

SYSTEM_PROMPT = """你是数分 Agent，专注数据分析，不是通用助手。工作守则：

1. 任何分析前先 profile_data 了解数据全貌，不直接臆测列含义。
2. 列名和过滤取值必须来自数据字典（工具会校验），字典里查不到、口径不清时，明确说不知道并停下问人——敢说不知道是产品要求，不是丢脸。
3. groupby_sum 的结果必须用 verify_groupby_sum 核验，pass=false 不得作为结论输出。
4. 你知道 verify 只能保证执行自洽，不能保证口径正确。给结论时声明用的口径（如「completed 口径不含退款」）。
5. 输出结论用中文，给数字时附口径声明。
6. 治理规则：跑完有复用价值的分析（分组统计/实验结论/固化流程），用 propose_asset 提交入库提案（带口径声明），等用户审批；重要决策写 blackboard_entry（决策+why），让用户确认。你无权自行入库。
7. 用户审批通过的资产（lookup_library 可查）优先复用：命中就直接用资产回答并注明出处（资产名+口径），未命中才现算。"""

def _bi_prompt(dataset: str) -> str:
    """BI 模式 prompt：数据集由调用方指定，字典负责口径。"""
    return f"""你是大屏问数助手，服务数字人语音问答。数据集固定用 {dataset}（其列/取值/口径以数据字典为准，工具会校验）。铁律：

1. 只做取数查询。分组求和用 groupby_sum；求平均/计数/去重/波动/最值、要TopN（最高最低N个）、按每天/每月/每周分组，用 groupby_agg（agg 参数选聚合方式，top_n 取前N，date_grain 选时间粒度）。回答格式固定三段：
   【答】一句话结论（含数字）
   【口径】本次统计口径声明
   【图表】单独一行，以 CHART_SPEC: 开头接 JSON，schema 为
   {{"chart_type": "bar|line|pie|map", "dimension": "<分组列>", "measure": "<指标列>", "data": [{{"name": "...", "value": 123}}, ...]}}
   ——data 直接来自工具返回的 result；省份维度用 chart_type=map。
2. 取数后必须用对应的 verify 工具核验（groupby_sum→verify_groupby_sum，groupby_agg→verify_groupby_agg，把 result 原样传给 expected，verify 参数与取数参数保持一致），pass=true 才输出【答】。注意步数预算：最多 4 步，所以第 1 步直接取数（不要先 profile），第 2 步 verify，第 3 步作答（三段格式），第 4 步仅当核验通过才 propose_asset。
3. 不做多轮分析、不跑实验、不写黑板。
4. 超出取数范围的问题（因果/归因/预测/建议/与数据无关的），回答：
   【答】这个问题需要深入分析，已转交分析师工作台处理。
   （不输出 CHART_SPEC）
5. 字典里查不到的维度/取值：直接说「该口径未登记，请联系数据管理员」，不猜。
6. 回答精炼：口语化，总共不超过 80 字（不含 CHART_SPEC），数字保留两位。"""

# 各模式的工具白名单（BI 模式只留取数+资产查询；提案不放工具，防 agent 跳过作答）
_BI_TOOLS = {"profile_data", "groupby_sum", "groupby_agg", "pivot_table", "trend_compare",
             "verify_groupby_sum", "verify_groupby_agg", "verify_pivot_table", "verify_trend_compare",
             "lookup_library"}


class DataAgent:
    def __init__(self, max_steps: int = 10, mode: str = "analyst", dataset: str = "dash_orders"):
        self.mode = mode
        self.dataset = dataset  # BI 模式的数据源，由调用方指定，字典校验口径
        self.max_steps = max_steps if mode == "analyst" else min(max_steps, 4)  # 3步答题+1步提案
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置——请把 key 写入 .env（该文件已 gitignore）")
        self.client = OpenAI(api_key=api_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        base_prompt = SYSTEM_PROMPT if mode == "analyst" else _bi_prompt(dataset)
        self.messages: list = [{"role": "system", "content": base_prompt}]
        self.trace: list = []  # 每步留痕，供 steps/ 落盘与前端展示
        # BI 模式：工具白名单过滤（schemas 和 registry 都要收敛，防越权调用）
        if mode == "bi":
            self.schemas = [s for s in TOOL_SCHEMAS if s["function"]["name"] in _BI_TOOLS]
        else:
            self.schemas = TOOL_SCHEMAS

    def ask(self, user_input: str) -> dict:
        """跑一轮 ReAct。快问短链：先查 approved library，命中即注入提示词。"""
        # ---- 快问短链：资产命中先给 agent 提示，缩短链长 ----
        from data_agent.governance import lookup_library
        hits = lookup_library(user_input)
        content = user_input
        if hits:
            top = hits[0]
            content = (f"{user_input}\n\n[系统提示] 资产库命中：{top['name']}（口径：{top['caliber']}；"
                       f"来源：{', '.join(top.get('source_steps', []))}）。优先复用该资产回答，并注明出处。")
        self.messages.append({"role": "user", "content": content})
        final_reply = None

        for step in range(self.max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.schemas,
            )
            msg = resp.choices[0].message

            # 先 append 再遍历——ReAct 铁律
            self.messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                final_reply = msg.content
                self.trace.append({"step": step, "type": "answer", "content": msg.content})
                break

            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = execute_tool(call.function.name, args)
                self.trace.append({"step": step, "type": "tool", "name": call.function.name, "args": args, "result": result})
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                })
        else:
            final_reply = "达到步数上限仍未收敛，中止。已执行的步骤见 trace。"
            self.trace.append({"type": "max_steps_hit"})

        # BI 模式资产沉淀：回答成功后，代码层自动提案（不让 agent 决策，防跳过作答）
        if self.mode == "bi" and final_reply and "CHART_SPEC" in (final_reply or ""):
            self._auto_propose(final_reply)

        return {"reply": final_reply, "trace": self.trace}

    def _auto_propose(self, reply: str) -> None:
        """BI 现算结果自动提案入库（人审批后生效）。失败静默，不影响问答。"""
        try:
            import re
            from data_agent.governance import propose_asset
            m = re.search(r'CHART_SPEC:\s*(\{.*\})', reply, re.S)
            if not m:
                return
            spec = json.loads(m.group(1))
            dim, measure = spec.get("dimension", ""), spec.get("measure", "")
            if not dim or not measure:
                return
            # 已提案过同名资产的跳过（防重复）
            from data_agent.governance import list_pending, lookup_library
            name = f"{self.dataset}_{dim}_{measure}_sum"
            if any(p["name"] == name for p in list_pending()):
                return
            if any(h["name"] == name for h in lookup_library(f"{self.dataset} {dim} {measure}")):
                return
            propose_asset(
                name=name,
                kind="result_table",
                description=f"BI 问数现算：{self.dataset} 按 {dim} 汇总 {measure}",
                caliber=f"{self.dataset} 全量，按 {dim} 分组对 {measure} 求和",
                params={"dataset": self.dataset, "group_col": dim, "value_col": measure},
                source_steps=["bi_ask"],
            )
        except Exception:
            pass  # 资产沉淀是 best-effort，问答优先

# -*- coding: utf-8 -*-
"""ReAct循环核心：LLM决策→调工具→观察→循环，最多10步，每步落盘留痕。

复用capstone_kit的ReAct骨架思路，适配数据洞察场景。
"""
import json
import os
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from . import tools as T

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
MAX_STEPS = 10

# 工具注册表
TOOL_REGISTRY = {
    "profile": T.profile,
    "groupby_agg": T.groupby_agg,
    "monthly_trend": T.monthly_trend,
    "rfm_table": T.rfm_table,
    "bar_chart": T.bar_chart,
    "line_chart": T.line_chart,
    "verify": T.verify,
}

# 工具schema定义
tools = [
    {"type": "function", "function": {
        "name": "profile",
        "description": "数据画像：返回表结构、行数、列信息。任何分析前必须先调它了解数据。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "groupby_agg",
        "description": "通用分组聚合。按某列分组，对另一列做聚合（sum/mean/count/nunique）。",
        "parameters": {"type": "object", "properties": {
            "group_col": {"type": "string", "description": "分组列名，如 'Country'"},
            "value_col": {"type": "string", "description": "聚合值列名，默认 'revenue'"},
            "agg": {"type": "string", "description": "聚合方式: sum/mean/count/nunique", "enum": ["sum", "mean", "count", "nunique"]},
            "top_n": {"type": "integer", "description": "取前N名，不填则全部"}},
            "required": ["group_col"]}}},
    {"type": "function", "function": {
        "name": "monthly_trend",
        "description": "月度趋势统计，返回按月聚合的指标值，自动标注不完整月份。",
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "description": "统计指标列名，默认 'revenue'"}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "rfm_table",
        "description": "RFM客户分层：按Recency/Frequency/Monetary评分，分为高/中/低价值客户。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "bar_chart",
        "description": "生成横向柱状图HTML。用于展示分类对比数据。",
        "parameters": {"type": "object", "properties": {
            "items": {"type": "array", "items": {"type": "string"}, "description": "分类标签列表"},
            "values": {"type": "array", "items": {"type": "number"}, "description": "数值列表"},
            "title": {"type": "string", "description": "图表标题"},
            "out_html": {"type": "string", "description": "输出HTML文件路径，如 'output/bar.html'"}},
            "required": ["items", "values", "title", "out_html"]}}},
    {"type": "function", "function": {
        "name": "line_chart",
        "description": "生成折线图HTML，支持多条线。用于展示趋势数据。",
        "parameters": {"type": "object", "properties": {
            "x_items": {"type": "array", "items": {"type": "string"}, "description": "X轴标签列表"},
            "series_dict": {"type": "object", "description": "{系列名: 数值列表} 的字典"},
            "title": {"type": "string", "description": "图表标题"},
            "out_html": {"type": "string", "description": "输出HTML文件路径"}},
            "required": ["x_items", "series_dict", "title", "out_html"]}}},
    {"type": "function", "function": {
        "name": "verify",
        "description": "结果自检：用独立pandas代码复算结论。出最终数字结论前必须调用。",
        "parameters": {"type": "object", "properties": {
            "claim": {"type": "string", "description": "要验证的结论"},
            "independent_code": {"type": "string", "description": "独立pandas表达式"}},
            "required": ["claim", "independent_code"]}}},
]

SYSTEM_PROMPT = (
    "你是数据洞察分析Agent。铁律：\n"
    "① 分析前先调 profile 了解数据结构；\n"
    "② 分组聚合用 groupby_agg，月度趋势用 monthly_trend，客户分层用 rfm_table；\n"
    "③ 可视化用 bar_chart（柱状图）或 line_chart（折线图），图表保存到 output/ 目录；\n"
    "④ 出最终数字结论前必须调 verify 用独立写法复算，复算一致才回答；\n"
    "⑤ 如果问题超出数据能回答的范围，直接说缺少什么，不编答案。"
)


def run_agent(user_query: str, max_steps: int = MAX_STEPS, verbose: bool = True) -> tuple[str, list]:
    """跑一次完整 ReAct 循环。返回 (答案文本, 过程记录 list)。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未检测到 DEEPSEEK_API_KEY。先跑 python main.py --selftest（无需key），"
            "或按 README 配置 key 后再提问。")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    trace = []

    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="deepseek-v4-flash", messages=messages, tools=tools)
        msg = resp.choices[0].message

        if not msg.tool_calls:
            trace.append({"step": step + 1, "type": "final", "content": msg.content})
            return msg.content, trace

        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            if verbose:
                print(f"  [step {step + 1}] -> {call.function.name}({args})")
            try:
                result = TOOL_REGISTRY[call.function.name](**args)
            except Exception as e:
                result = {"ok": False, "error": f"执行失败: {e}"}
            trace.append({"step": step + 1, "type": "tool_call",
                          "tool": call.function.name, "args": args, "result": result})
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False)})

    return "（达到最大步数仍未给出答案——检查问题是否超出数据能回答的范围）", trace


def save_trace(user_query: str, answer: str, trace: list) -> Path:
    """每次运行落盘一个 JSON：runs/YYYYmmdd-HHMMSS.json。"""
    RUNS_DIR.mkdir(exist_ok=True)
    fname = datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
    payload = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "question": user_query,
        "answer": answer,
        "steps": trace,
    }
    path = RUNS_DIR / fname
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

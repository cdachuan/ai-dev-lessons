# -*- coding: utf-8 -*-
"""ReAct 循环（28 课骨架）+ 35 课工程化增量：步数预算、过程落盘留痕。"""
import json
import os
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from . import tools as T

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
MAX_STEPS = 8

TOOL_REGISTRY = {
    "profile": T.profile,
    "group_sum": T.group_sum,
    "count_distinct": T.count_distinct,
    "group_count": T.group_count,
    "verify": T.verify,
}

tools = [
    {"type": "function", "function": {
        "name": "profile",
        "description": "读取订单数据，返回表结构画像（行数/列/类型/状态与渠道取值/前3行）。任何分析前必须先调它了解数据。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "group_sum",
        "description": "按某列分组，对金额列求和。filter_status 用于过滤订单状态（如'已完成'）——算销售额前必须想清楚是否剔除已退款，并在最终回答里写明口径。",
        "parameters": {"type": "object", "properties": {
            "group_col": {"type": "string", "description": "分组列名，如 '品类' 或 '渠道'"},
            "value_col": {"type": "string", "description": "求和列名，默认 '金额'"},
            "filter_status": {"type": "string", "description": "可选，只保留该状态，如 '已完成'"}},
            "required": ["group_col"]}}},
    {"type": "function", "function": {
        "name": "group_count",
        "description": "按某列分组计数（订单量）。filter_status 可选。算退款率时分母用全部订单、分子用状态='已退款'。",
        "parameters": {"type": "object", "properties": {
            "group_col": {"type": "string", "description": "分组列名，如 '渠道'"},
            "filter_status": {"type": "string", "description": "可选状态过滤"}},
            "required": ["group_col"]}}},
    {"type": "function", "function": {
        "name": "count_distinct",
        "description": "对某列去重计数，用于'有多少个不同的X'。不是 count（会把重复算进去）。",
        "parameters": {"type": "object", "properties": {
            "col": {"type": "string", "description": "列名，如 '订单号'"}},
            "required": ["col"]}}},
    {"type": "function", "function": {
        "name": "verify",
        "description": "【出最终数字结论前必须调用】用独立写法的 pandas 表达式复算结论。independent_code 必须与主算法不同（如布尔索引+sum，而非再 groupby 一次）。",
        "parameters": {"type": "object", "properties": {
            "claim": {"type": "string", "description": "要验证的结论，如 '数码销售额15750元（剔除退款）'"},
            "independent_code": {"type": "string",
                                 "description": "独立 pandas 表达式，如 df[df['状态']=='已完成'].query(\"品类=='数码'\")['金额'].sum()"}},
            "required": ["claim", "independent_code"]}}},
]

SYSTEM_PROMPT = (
    "你是电商数据分析 Agent。铁律：\n"
    "① 分析前先调 profile 了解数据；\n"
    "② 算金额指标前先想口径（是否剔除已退款），并在回答中写明口径；\n"
    "③ 出最终数字结论前必须调 verify 用独立写法复算，复算一致才回答；\n"
    "④ '多少个不同的X'用 count_distinct，不要用 count；\n"
    "⑤ 如果问题里的口径在数据中无法确定（如'利润'但没有成本列），"
    "直接说缺少什么、需要用户确认什么，不许编一个口径硬答。"
)


def run_agent(user_query, max_steps=MAX_STEPS, verbose=True):
    """跑一次完整 ReAct 循环。返回 (答案文本, 过程记录 list)。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未检测到 DEEPSEEK_API_KEY。先跑 python main.py --selftest（无需 key），"
            "或按 README 配置 key 后再提问。")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    trace = []  # 35 课：完整过程留痕

    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=tools)
        msg = resp.choices[0].message

        if not msg.tool_calls:
            trace.append({"step": step + 1, "type": "final", "content": msg.content})
            return msg.content, trace

        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            if verbose:
                print(f"  [step {step + 1}] → {call.function.name}({args})")
            try:
                result = TOOL_REGISTRY[call.function.name](**args)
            except Exception as e:
                result = {"error": f"执行失败: {e}"}
            trace.append({"step": step + 1, "type": "tool_call",
                          "tool": call.function.name, "args": args, "result": result})
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False)})

    return "（达到最大步数仍未给出答案——检查问题是否超出数据能回答的范围）", trace


def save_trace(user_query, answer, trace):
    """每次运行落盘一个 JSON：runs/YYYYmmdd-HHMMSS.json（中间产物可见）。"""
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

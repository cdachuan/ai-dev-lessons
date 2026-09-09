# -*- coding: utf-8 -*-
"""
34课 · 数分 Agent：ReAct + 核验卡口
在 28 课 ReAct 骨架上，把「台区工具」换成「数据分析工具」，
并加一个本课核心增量：出结论前自动复算（verify 工具）。

用法：
  1. 设置环境变量 DEEPSEEK_API_KEY（不写死在代码里）
  2. python agent_data_verify.py "各品类销售额（剔除退款）"
"""
import json, os
import pandas as pd
from openai import OpenAI

DATA = r"D:\学习\AI\工具实操\orders_60.csv"

# ---------- 工具函数：都是普通 Python，AI 决定调哪个 ----------
def load_data():
    """读数据，返回表结构画像 + 前3行（感知层雏形）"""
    df = pd.read_csv(DATA)
    return {
        "行数": len(df),
        "列": list(df.columns),
        "类型": {c: str(t) for c, t in df.dtypes.items()},
        "状态取值": df["status"].unique().tolist(),
        "前3行": df.head(3).to_dict("records"),
    }

def groupby_sum(group_col, value_col, filter_status=None):
    """按某列分组，对某列求和。filter_status 可过滤状态（口径开关）"""
    df = pd.read_csv(DATA)
    if filter_status:
        df = df[df["status"] == filter_status]
    s = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
    return {"group_col": group_col, "value_col": value_col,
            "filter_status": filter_status,
            "结果": {k: int(v) for k, v in s.items()}}

def nunique(col):
    """去重计数（31课小测 nunique 的机器版）"""
    df = pd.read_csv(DATA)
    return {"col": col, "去重计数": int(df[col].nunique())}

def verify(claim, independent_code):
    """【核验卡口】用独立路径复算 claim，对比是否一致。
    independent_code 是 AI 自己写的一段独立 pandas 表达式。
    注意：这里只做「执行 + 对比」，不信任 AI 的 claim 本身。"""
    df = pd.read_csv(DATA)
    # 安全执行 AI 给的核验代码（本课仅演示，生产环境要沙箱）
    namespace = {"df": df, "pd": pd}
    try:
        real = eval(independent_code, {"__builtins__": {}}, namespace)
    except Exception as e:
        return {"核验": "失败", "原因": f"核验代码执行出错: {e}"}
    # Series / ndarray / numpy标量 → 转成可 JSON 序列化的 Python 对象
    def _to_jsonable(v):
        import numpy as np
        if isinstance(v, pd.Series):
            return {str(k): (int(x) if float(x).is_integer() else float(x)) for k, x in v.items()}
        if isinstance(v, pd.DataFrame):
            return v.to_dict("records")
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        return v
    real = _to_jsonable(real)
    # 尝试对比 claim 和 real
    return {"claim": claim, "独立复算": real, "待人工比对": True}

# ---------- 工具注册 ----------
TOOL_REGISTRY = {
    "load_data": load_data,
    "groupby_sum": groupby_sum,
    "nunique": nunique,
    "verify": verify,
}

tools = [
    {"type": "function", "function": {
        "name": "load_data",
        "description": "读取订单数据文件，返回表结构画像（行数/列/类型/状态取值/前3行）。任何分析前必须先调它了解数据。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "groupby_sum",
        "description": "按某列分组，对某列求和。filter_status 用于过滤订单状态（如'已完成'）——算销售额时必须先想清楚是否要过滤已退款订单。",
        "parameters": {"type": "object", "properties": {
            "group_col": {"type": "string", "description": "分组的列名，如 category"},
            "value_col": {"type": "string", "description": "求和的列名，如 amount"},
            "filter_status": {"type": "string", "description": "可选，只保留该状态的订单，如'已完成'"}},
        "required": ["group_col", "value_col"]}}},
    {"type": "function", "function": {
        "name": "nunique",
        "description": "对某列去重计数。用于'有多少个客户'这类问题（不是 count，count 会把重复算进去）。",
        "parameters": {"type": "object", "properties": {
            "col": {"type": "string", "description": "要去重计数的列名，如 customer_id"}},
        "required": ["col"]}}},
    {"type": "function", "function": {
        "name": "verify",
        "description": "【必须调用】出最终结论前，用独立代码路径复算结果，验证 claim 是否正确。independent_code 用 pandas 写一段与 groupby_sum 不同的算法（如布尔索引+sum），对同一口径复算。",
        "parameters": {"type": "object", "properties": {
            "claim": {"type": "string", "description": "你要验证的结论，如'数码销售额9932元'"},
            "independent_code": {"type": "string", "description": "独立的pandas表达式，如 df[df.status=='已完成'][df.category=='数码'].amount.sum()"}},
        "required": ["claim", "independent_code"]}}},
]

# ---------- ReAct 循环（28课骨架，原样保留）----------
def run_agent(user_query, max_steps=8):
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    messages = [
        {"role": "system", "content":
            "你是数据分析 Agent。铁律：① 分析前先 load_data 了解数据；"
            "② 算销售额等金额指标前，先想口径——是否要排除'已退款'订单；"
            "③ 出最终数字结论前，必须调用 verify 用独立路径复算，复算通过才回答；"
            "④ '多少客户'用 nunique 去重，不是 count。"},
        {"role": "user", "content": user_query},
    ]
    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=tools)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content
        messages.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            print(f"  [step {step+1}] → {call.function.name}({args})")
            try:
                result = TOOL_REGISTRY[call.function.name](**args)
            except Exception as e:
                result = {"error": f"执行失败: {e}"}
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False)})
    return "（达到最大步数，Agent 未给出答案）"

if __name__ == "__main__":
    q = os.sys.argv[1] if len(os.sys.argv) > 1 else "各品类销售额（剔除退款）"
    print(run_agent(q))

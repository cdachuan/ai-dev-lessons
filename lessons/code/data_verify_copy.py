# 我打算复刻一下agent_data_verify.py
import pandas as pd
import numpy as np
import json
import os
from openai import OpenAI

# 先梳理一下结构
# 1.找数据
DATA = r"D:\学习\AI\工具实操\orders_60.csv"



# 2.定义工具
# 我需要什么工具？
# 1.读取数据
# 2.构建数据结构画像
# 3.查看数据统计信息
# 4.聚合运算工具
# 5.去重计数
# 6.核验卡口用独立路径复算 claim，对比是否一致

# 1.读取数据
def load_data():
    """读取订单数据，返回表结构画像"""
    df = pd.read_csv(DATA)
    return {
        "行数": len(df),
        "列": list(df.columns),
        "类型": {c: str(t) for c, t in df.dtypes.items()},
        "前3行": df.head(3).to_dict("records"),
    }

# 2.构建数据结构画像
def build_data_profile():
    """构建数据结构画像（行数/列数/类型/前3行）"""
    df = pd.read_csv(DATA)
    return {
        "行数": df.shape[0],
        "列数": df.shape[1],
        "类型": {c: str(t) for c, t in df.dtypes.items()},
        "前3行": df.head(3).to_dict("records")}

# 3.查看数据统计信息
def data_stats():
    """查看数据统计信息（描述性统计）"""
    df = pd.read_csv(DATA)
    return df.describe().to_dict("records")

# 4.聚合运算工具
def groupby_sum(group_col, value_col, filter_status=None):
    """按某列分组，对某列求和。filter_status 可过滤状态（口径开关）"""
    df = pd.read_csv(DATA)
    if filter_status:
        df = df[df["status"] == filter_status]
    s = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
    return {"group_col": group_col, "value_col": value_col,
            "filter_status": filter_status,
            "结果": {k: int(v) for k, v in s.items()}}
# 5.去重计数
def unique_count(col):
    """对某列去重计数"""
    df = pd.read_csv(DATA)
    return {"列": col, "去重计数": int(df[col].nunique())}

# 6.核验卡口用独立路径复算 claim，对比是否一致
def verify_claim(claim_col, calc_col):
    """核验 claim 列是否与 calc_col 列一致"""
    df = pd.read_csv(DATA)
    return {"claim_col": claim_col, "calc_col": calc_col,
            "一致": (df[claim_col] == df[calc_col]).all()}

# 3.注册工具
TOOL_REGISTRY = {
    "load_data": load_data,
    "build_data_profile": build_data_profile,
    "data_stats": data_stats,
    "groupby_sum": groupby_sum,
    "unique_count": unique_count,
    "verify_claim": verify_claim,
}

# 工具描述重要有：
# 1.工具名称
# 2.工具描述
# 3.工具参数
# 4.工具返回值
# 5.工具示例
tools = [
    {"type": "function", "function": {
        "name": "load_data",
        "description": "读取订单数据文件，返回DataFrame。任何分析前必须先调它了解数据。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "build_data_profile",
        "description": "构建数据结构画像（行数/列数/类型/前3行）",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "data_stats",
        "description": "查看数据统计信息（描述性统计）",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "groupby_sum",
        "description": "按某列分组，对某列求和。filter_status 可过滤状态（口径开关）",
        "parameters": {"type": "object", "properties": {
            "group_col": {"type": "string", "description": "分组列名，如 category"},
            "value_col": {"type": "string", "description": "求和列名，如 amount"},
            "filter_status": {"type": "string", "description": "可选，只保留该状态的订单，如'已完成'"}},
        "required": ["group_col", "value_col"]}}},
    {"type": "function", "function": {
        "name": "unique_count",
        "description": "对某列去重计数。用于'有多少个客户'这类问题（不是 count，count 会把重复算进去）。",
        "parameters": {"type": "object", "properties": {
            "col": {"type": "string", "description": "要去重计数的列名，如 customer_id"}},
        "required": ["col"]}}},
    {"type": "function", "function": {
        "name": "verify_claim",
        "description": "核验 claim 列是否与 calc_col 列一致",
        "parameters": {"type": "object", "properties": {
            "claim_col": {"type": "string", "description": "claim 列名"},
            "calc_col": {"type": "string", "description": "calc_col 列名"}},
        "required": ["claim_col", "calc_col"]}}},
]

# 4.AI 调用工具
# 这里要怎么调用工具？搭建一个react应用，用户可以在应用中输入指令，应用会调用ai api，ai会返回结果，应用会展示给用户。

def run_agent(instruction, max_steps=5):
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )
    message = [
        {"role": "system", "content": "你是一个专业的数据分析师，负责分析订单数据。"},
        {"role": "user", "content": instruction}
    ]

    for step in range(max_steps):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=message,
            tools=tools,
            tool_choice="auto",
            temperature=0.5,
        )
        mag = response.choices[0].message
        if not mag.tool_calls:
            print(mag.content)
            return mag.content
        message.append(mag)
        print(mag.content)
        for call in mag.tool_calls:
            args = json.loads(call.function.arguments)
            print(f"  [step {step+1}] → {call.function.name}({args})")
            try:
                result = TOOL_REGISTRY[call.function.name](**args)
            except Exception as e:
                result = {"error": f"执行失败: {e}"}
            message.append({
                "role": "tool", "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

if __name__ == "__main__":
    input = input("我是您的智能数据分析师，您可以输入指令来分析数据: ")
    run_agent(input)


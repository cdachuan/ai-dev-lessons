# -*- coding: utf-8 -*-
"""数分工具集：动作固化、数据外置。所有工具返回前过 _to_jsonable。

verify 边界（铁律2）：核验只用独立算法路径复算同一口径，保证自洽不保证正确。
口径对不对，字典说了算（人写）；执行忠实度，verify 说了算。
"""
import json
import pandas as pd
from pathlib import Path

from core.dictionary import col, valid_values, dataset_file, get_dataset_entry
from core.jsonable import _to_jsonable

ROOT = Path(__file__).resolve().parent.parent

_DATA_CACHE: dict = {}


def _load(dataset: str) -> pd.DataFrame:
    """原数据物理只读：加载后只做派生，绝不写回原文件。"""
    if dataset not in _DATA_CACHE:
        path = dataset_file(dataset)
        _DATA_CACHE[dataset] = pd.read_csv(path)
    return _DATA_CACHE[dataset].copy()  # 永远给副本，原表不可变


# ---------- 工具 1：机械画像 ----------
def profile_data(dataset: str) -> dict:
    """机械画像：shape/列类型/缺失/nunique/describe。LLM 读卡片不读原始数据。"""
    df = _load(dataset)
    card = {
        "dataset": dataset,
        "shape": list(df.shape),
        "columns": {},
    }
    for c in df.columns:
        card["columns"][c] = {
            "dtype": str(df[c].dtype),
            "missing": int(df[c].isna().sum()),
            "nunique": int(df[c].nunique()),
            "sample": _to_jsonable(df[c].dropna().head(3).tolist()),
        }
    num_cols = df.select_dtypes("number").columns.tolist()
    if num_cols:
        card["describe"] = _to_jsonable(df[num_cols].describe().round(3).to_dict())
    return _to_jsonable(card)


# ---------- 工具 2：分组聚合（列名/取值从字典查，不写死） ----------
def groupby_sum(dataset: str, group_col: str, value_col: str, filter_col: str = None, filter_value: str = None) -> dict:
    """按 group_col 聚合 value_col 求和，可选先按 filter_col=filter_value 过滤。"""
    df = _load(dataset)
    g = col(dataset, group_col)
    v = col(dataset, value_col)
    if filter_col is not None:
        f = col(dataset, filter_col)
        if filter_value is None:
            raise ValueError("给了 filter_col 就必须给 filter_value")
        vv = valid_values(dataset, filter_col)
        if vv and filter_value not in vv:
            raise ValueError(f"'{filter_value}' 不在 {filter_col} 的有效值里: {vv}。口径不清就停下问人。")
        df = df[df[f] == filter_value]
    result = df.groupby(g)[v].sum().sort_values(ascending=False)
    return _to_jsonable({"group_col": g, "value_col": v, "filter": f"{f}=={filter_value}" if filter_col else None, "result": result})


# ---------- 工具 3：verify 双路径核验 ----------
def verify_groupby_sum(dataset: str, group_col: str, value_col: str, expected: dict, filter_col: str = None, filter_value: str = None) -> dict:
    """独立算法路径复算：布尔索引+手动分组 vs groupby。一致才放行。"""
    df = _load(dataset)
    g = col(dataset, group_col)
    v = col(dataset, value_col)
    if filter_col is not None:
        f = col(dataset, filter_col)
        df = df[df[f] == filter_value]

    # 路径 B：不用 groupby，用 dict 手动累加
    manual = {}
    for _, row in df.iterrows():
        k = row[g]
        manual[k] = manual.get(k, 0) + float(row[v])
    manual = {k: round(x, 6) for k, x in manual.items()}

    mismatches = {k: {"groupby": expected.get(k), "manual": manual.get(k)}
                  for k in set(expected) | set(manual)
                  if abs((expected.get(k) or 0) - manual.get(k, 0)) > 0.01}
    return _to_jsonable({
        "pass": len(mismatches) == 0,
        "method": "groupby vs 布尔索引+dict累加（独立路径）",
        "mismatches": mismatches,
    })


# ---------- 注册表 ----------
TOOL_REGISTRY = {
    "profile_data": profile_data,
    "groupby_sum": groupby_sum,
    "verify_groupby_sum": verify_groupby_sum,
}

# 给 LLM 看的说明书：description 写「什么时候用」，不只写功能
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "profile_data",
            "description": "对数据集做机械画像，返回 shape/列类型/缺失/基数/数值分布。任何分析开始前必须先调用它了解全貌，不要直接读原始数据。",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string", "description": "数据集名，必须在 dictionary.yaml 里注册"}},
                "required": ["dataset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "groupby_sum",
            "description": "分组求和。当问题形如「按X分组统计Y之和/总额」时用。列名用字典里的逻辑名，不要自己猜物理列名；过滤取值必须用字典 valid_values 里的值，口径不清就拒绝回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "group_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "filter_col": {"type": "string", "description": "可选，过滤列"},
                    "filter_value": {"type": "string", "description": "可选，过滤值，必须来自字典 valid_values"},
                },
                "required": ["dataset", "group_col", "value_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_groupby_sum",
            "description": "核验卡口：对 groupby_sum 的结果做双路径复算，必须核对。每次调用 groupby_sum 后必须紧接着用它的结果调用本工具，pass=false 时不得把结果当作结论输出。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "group_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "expected": {"type": "object", "description": "groupby_sum 返回的 result 字典原样传入"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                },
                "required": ["dataset", "group_col", "value_col", "expected"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    """执行工具，错误也返回给 AI 继续推理，不炸循环。"""
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": f"未知工具 {name}，可用: {list(TOOL_REGISTRY)}"}, ensure_ascii=False)
    try:
        return json.dumps(TOOL_REGISTRY[name](**args), ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

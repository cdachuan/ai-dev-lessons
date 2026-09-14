# -*- coding: utf-8 -*-
"""工具层：四个普通 Python 函数，由 Agent（大模型）决定调用哪个。

设计铁律（34/35 课）：
- 全部工具只读原数据，没有任何修改/删除操作
- verify 用独立代码路径复算，不信任被核验的结论本身
"""
from pathlib import Path
import pandas as pd

# 换自己的数据：改这一行即可（相对脚本目录定位，换机器/换目录也能跑——36 课）
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "orders.csv"


def _df():
    return pd.read_csv(DATA_FILE, encoding="utf-8-sig")


def profile():
    """读数据，返回表结构画像 + 前3行（感知层：模型读卡片不读全表）。"""
    df = _df()
    return {
        "行数": len(df),
        "列": list(df.columns),
        "类型": {c: str(t) for c, t in df.dtypes.items()},
        "状态取值": df["状态"].unique().tolist(),
        "渠道取值": df["渠道"].unique().tolist(),
        "前3行": df.head(3).to_dict("records"),
    }


def group_sum(group_col, value_col="金额", filter_status=None):
    """按某列分组，对某列求和。filter_status 可过滤状态（口径开关）。

    算销售额时口径问题：要不要先剔除「已退款」？由提问者的意图决定，
    Agent 必须在结论里写明自己用的口径。
    """
    df = _df()
    if filter_status:
        df = df[df["状态"] == filter_status]
    s = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
    return {
        "group_col": group_col,
        "value_col": value_col,
        "filter_status": filter_status,
        "结果": {k: int(v) for k, v in s.items()},
    }


def count_distinct(col):
    """去重计数。'有多少个不同的 X' 用 nunique，不是 count。"""
    df = _df()
    return {"col": col, "去重计数": int(df[col].nunique())}


def group_count(group_col, filter_status=None):
    """按某列分组计数行数（订单量）。可按状态过滤。"""
    df = _df()
    if filter_status:
        df = df[df["状态"] == filter_status]
    s = df.groupby(group_col).size().sort_values(ascending=False)
    return {
        "group_col": group_col,
        "filter_status": filter_status,
        "结果": {k: int(v) for k, v in s.items()},
    }


def verify(claim, independent_code):
    """【核验卡口】用独立路径复算 claim。

    independent_code 是另写的一段 pandas 表达式（必须与主算法写法不同），
    在只有 df / pd 的命名空间里执行。本课仅演示，生产环境要放沙箱。
    返回复算值，由 Agent（和看 runs 留痕的人）比对 claim。
    """
    df = _df()
    namespace = {"df": df, "pd": pd}
    try:
        real = eval(independent_code, {"__builtins__": {}}, namespace)
    except Exception as e:
        return {"核验": "失败", "原因": f"核验代码执行出错: {e}"}

    def _to_jsonable(v):
        import numpy as np
        if isinstance(v, pd.Series):
            return {str(k): (int(x) if float(x).is_integer() else round(float(x), 4))
                    for k, x in v.items()}
        if isinstance(v, pd.DataFrame):
            return v.to_dict("records")
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, np.floating):
            return round(float(v), 4)
        return v

    return {"claim": claim, "独立复算": _to_jsonable(real)}

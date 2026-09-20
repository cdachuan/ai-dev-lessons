# -*- coding: utf-8 -*-
"""工具层：数据洞察Agent的全部工具函数。

基于ecommerce_toolkit改造，统一返回格式 {"ok": bool, "data": ..., "error": ...}
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# 数据文件路径（可通过环境变量DATA_PATH覆盖）
import os
DATA_FILE = Path(os.environ.get(
    "DATA_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "ecommerce" / "online_retail_2010_2011.csv")
))


def _load_data():
    """加载并预处理数据，返回清洗后的DataFrame。"""
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["CustomerID"])
    df["CustomerID"] = df["CustomerID"].astype(int)
    df = df[df["UnitPrice"] > 0]
    df["revenue"] = df["Quantity"] * df["UnitPrice"]
    df.loc[
        df["InvoiceNo"].astype(str).str.startswith("C") | (df["Quantity"] < 0),
        "revenue",
    ] = df.loc[
        df["InvoiceNo"].astype(str).str.startswith("C") | (df["Quantity"] < 0),
        "revenue",
    ].abs() * -1
    return df


# ============================================================
# 工具函数：数据画像
# ============================================================

def profile() -> dict[str, Any]:
    """数据画像：返回表结构、行数、列信息、关键字段取值。

    Returns:
        {"ok": True, "data": {...}} 或 {"ok": False, "error": "..."}
    """
    try:
        df = _load_data()
        return {
            "ok": True,
            "data": {
                "行数": len(df),
                "列": list(df.columns),
                "类型": {c: str(t) for c, t in df.dtypes.items()},
                "国家取值": df["Country"].unique().tolist()[:10],
                "前3行": df.head(3).to_dict("records"),
            },
        }
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


# ============================================================
# 工具函数：分组聚合
# ============================================================

def groupby_agg(
    group_col: str,
    value_col: str = "revenue",
    agg: str = "sum",
    top_n: int | None = None,
) -> dict[str, Any]:
    """通用分组聚合。

    Args:
        group_col: 分组列名
        value_col: 聚合值列名
        agg: 聚合方式 sum/mean/count/nunique
        top_n: 取前N名

    Returns:
        {"ok": True, "data": {...}} 或 {"ok": False, "error": "..."}
    """
    try:
        df = _load_data()
        if agg == "nunique":
            result = df.groupby(group_col)[value_col].nunique().sort_values(ascending=False)
        else:
            result = getattr(df.groupby(group_col)[value_col], agg)().sort_values(ascending=False)
        if top_n:
            result = result.head(top_n)
        return {"ok": True, "data": {str(k): round(float(v), 2) for k, v in result.items()}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


# ============================================================
# 工具函数：月度趋势
# ============================================================

def monthly_trend(metric: str = "revenue") -> dict[str, Any]:
    """月度趋势统计，自动标注不完整月份。

    Args:
        metric: 统计指标列名

    Returns:
        {"ok": True, "data": {"series": {...}, "note": "..."}} 或错误
    """
    try:
        df = _load_data()
        tmp = df.copy()
        tmp["ym"] = tmp["InvoiceDate"].dt.to_period("M")
        result = tmp.groupby("ym")[metric].sum()

        note = ""
        max_period = result.index.max()
        if max_period.month < 12:
            note = f"注意: {max_period} 数据不完整（仅包含部分日期）"

        return {
            "ok": True,
            "data": {
                "series": {str(k): round(float(v), 2) for k, v in result.items()},
                "note": note,
            },
        }
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


# ============================================================
# 工具函数：RFM客户分层
# ============================================================

def rfm_table() -> dict[str, Any]:
    """RFM客户分层表。

    R(Recency): 距今天数
    F(Frequency): 订单数
    M(Monetary): 消费总额

    Returns:
        {"ok": True, "data": {"table": [...], "summary": {...}}}
    """
    try:
        df = _load_data()
        ref_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
        rfm = df.groupby("CustomerID").agg(
            recency=("InvoiceDate", lambda x: (ref_date - x.max()).days),
            frequency=("InvoiceNo", "nunique"),
            monetary=("revenue", "sum"),
        ).reset_index()

        for col, ascending in [("recency", True), ("frequency", False), ("monetary", False)]:
            try:
                rfm[f"{col[:1]}_score"] = (
                    6 - pd.qcut(rfm[col], 5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
                )
            except Exception:
                # 如果qcut失败（数据分布不均），用rank近似
                rfm[f"{col[:1]}_score"] = (
                    6 - pd.cut(rfm[col].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
                )

        rfm["total_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

        def _label(s):
            if s >= 12:
                return "高价值客户"
            elif s >= 8:
                return "中价值客户"
            else:
                return "低价值客户"

        rfm["segment"] = rfm["total_score"].apply(_label)
        summary = rfm["segment"].value_counts().to_dict()
        table = rfm[["CustomerID", "recency", "frequency", "monetary",
                       "r_score", "f_score", "m_score", "total_score", "segment"]].head(20).to_dict("records")

        return {
            "ok": True,
            "data": {
                "table": table,
                "summary": summary,
                "reference_date": str(ref_date),
            },
        }
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


# ============================================================
# 工具函数：图表生成
# ============================================================

def bar_chart(
    items: list[str],
    values: list[float],
    title: str,
    out_html: str,
) -> dict[str, Any]:
    """横向柱状图，保存为HTML。

    Args:
        items: 分类标签列表
        values: 数值列表
        title: 图表标题
        out_html: 输出HTML文件路径

    Returns:
        {"ok": True, "data": {"file": str}} 或 {"ok": False, "error": "..."}
    """
    try:
        from pyecharts.charts import Bar
        from pyecharts import options as opts

        bar = (
            Bar(init_opts=opts.InitOpts(width="900px", height="500px"))
            .add_xaxis(items)
            .add_yaxis("", values, label_opts=opts.LabelOpts(position="right"))
            .reversal_axis()
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=0)),
                yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=0)),
            )
        )
        bar.render(out_html)
        return {"ok": True, "data": {"file": out_html}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def line_chart(
    x_items: list[str],
    series_dict: dict[str, list[float]],
    title: str,
    out_html: str,
) -> dict[str, Any]:
    """折线图，支持多条线，保存为HTML。

    Args:
        x_items: X轴标签列表
        series_dict: {系列名: 数值列表} 的字典
        title: 图表标题
        out_html: 输出HTML文件路径

    Returns:
        {"ok": True, "data": {"file": str}} 或 {"ok": False, "error": "..."}
    """
    try:
        from pyecharts.charts import Line
        from pyecharts import options as opts

        line = Line(init_opts=opts.InitOpts(width="900px", height="500px"))
        line.add_xaxis(x_items)
        for name, vals in series_dict.items():
            line.add_yaxis(name, vals, is_smooth=True)
        line.set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
        line.render(out_html)
        return {"ok": True, "data": {"file": out_html}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


# ============================================================
# 工具函数：结果自检verify
# ============================================================

def verify(claim: str, independent_code: str) -> dict[str, Any]:
    """结果自检：用独立代码路径复算claim。

    Args:
        claim: 要验证的结论
        independent_code: 独立pandas表达式

    Returns:
        {"ok": True, "data": {"claim": str, "独立复算": ...}} 或错误
    """
    try:
        df = _load_data()
        namespace = {"df": df, "pd": pd}
        real = eval(independent_code, {"__builtins__": {}}, namespace)

        import numpy as np
        def _to_jsonable(v):
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

        return {"ok": True, "data": {"claim": claim, "独立复算": _to_jsonable(real)}}
    except Exception as e:
        return {"ok": False, "data": None, "error": f"核验代码执行出错: {e}"}

# -*- coding: utf-8 -*-
"""电商数据分析工具箱 — 9个可复用的规范工具函数。
【变式1 · 埋错版（8处bug）】逐个找出并修复，验收 = 变式验收_check.py 对本文件全 PASS。
【规则】禁止 diff 对照原版偷看——先跑 check 看哪个函数挂，自己读代码定位。

设计原则：
- 统一返回格式 {"ok": bool, "data": ..., "error": ...}
- 每个函数独立，可单独调用
- 数据只读，不修改源文件
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# ============================================================
# 工具函数
# ============================================================


def read_orders(path: str | Path, usecols: list[str] | None = None) -> dict[str, Any]:
    """读取订单CSV并转换日期字段。

    Args:
        path: CSV文件路径
        usecols: 要读取的列名列表，None则读全部

    Returns:
        {"ok": True, "data": DataFrame} 或 {"ok": False, "error": "..."}
    """
    try:
        df = pd.read_csv(path, usecols=usecols, encoding="gbk")
        if "InvoiceDate" in df.columns:
            df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
        return {"ok": True, "data": df}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def clean_orders(
    df: pd.DataFrame,
    drop_customer_na: bool = True,
) -> dict[str, Any]:
    """清洗订单数据。

    业务逻辑说明：
    1. CustomerID缺失 → 默认剔除（约25%缺失，无法归因到客户）
    2. InvoiceNo以C开头 或 Quantity<0 → 退货单，revenue记为负数
       （为什么记负数而不是删行：退货是真实业务，GMV应反映净销售，
       直接删行会虚增销售额）
    3. UnitPrice<=0 → 异常数据剔除（免费赠送/测试订单不计入统计）

    Args:
        df: 原始订单DataFrame
        drop_customer_na: 是否剔除CustomerID缺失的行

    Returns:
        {"ok": True, "data": 清洗后的DataFrame} 或 {"ok": False, "error": "..."}
    """
    try:
        df = df.copy()
        if drop_customer_na:
            df = df.dropna(subset=["CustomerID"])
            df["CustomerID"] = df["CustomerID"].astype(int)

        df = df[df["UnitPrice"] >= 0]

        df["revenue"] = df["Quantity"] * df["UnitPrice"]
        df.loc[
            df["InvoiceNo"].astype(str).str.startswith("C") | (df["Quantity"] < 0),
            "revenue",
        ] = df.loc[
            df["InvoiceNo"].astype(str).str.startswith("C") | (df["Quantity"] < 0),
            "revenue",
        ].abs()

        return {"ok": True, "data": df}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def kpi_summary(
    df: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """计算KPI摘要：总GMV、订单数、客单价、购买客户数、退货率。

    Args:
        df: 含revenue列的清洗后DataFrame
        start: 起始日期字符串，如 "2011-01-01"，None则不限
        end: 截止日期字符串，None则不限

    Returns:
        {"ok": True, "data": {各指标字典}} 或 {"ok": False, "error": "..."}
    """
    try:
        tmp = df.copy()
        if start:
            tmp = tmp[tmp["InvoiceDate"] >= pd.Timestamp(start)]
        if end:
            tmp = tmp[tmp["InvoiceDate"] <= pd.Timestamp(end)]

        total_gmv = float(tmp["revenue"].sum())
        # 订单口径：只数有正销售(购买)的发票，退货单不计入订单数
        pos_orders = int(tmp.loc[tmp["Quantity"] >= 0, "InvoiceNo"].nunique())
        customer_count = int(tmp["CustomerID"].nunique())
        # 客单价 = 净GMV / 有购买行为的订单数（退货单不是一次"单"）
        avg_price = round(total_gmv / pos_orders, 2) if pos_orders else 0
        # 人均消费（ARPU）单列，别和客单价混
        arpu = round(total_gmv / customer_count, 2) if customer_count else 0

        is_return = tmp["InvoiceNo"].astype(str).str.startswith("C") | (tmp["Quantity"] < 0)
        return_revenue = tmp.loc[is_return, "revenue"].sum()
        total_abs = tmp["revenue"].abs().sum()
        return_rate = round(return_revenue / total_abs * 100, 2) if total_abs else 0

        return {
            "ok": True,
            "data": {
                "总GMV": round(total_gmv, 2),
                "订单数": pos_orders,
                "购买客户数": customer_count,
                "客单价": avg_price,
                "人均消费ARPU": arpu,
                "退货率(%)": return_rate,
                "时间范围": f"{tmp['InvoiceDate'].min()} ~ {tmp['InvoiceDate'].max()}",
            },
        }
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def groupby_agg(
    df: pd.DataFrame,
    group_col: str,
    value_col: str = "revenue",
    agg: str = "sum",
    top_n: int | None = None,
) -> dict[str, Any]:
    """通用分组聚合。

    Args:
        df: 清洗后的DataFrame
        group_col: 分组列名
        value_col: 聚合值列名
        agg: 聚合方式 sum/mean/count/nunique
        top_n: 取前N名，None则全部

    Returns:
        {"ok": True, "data": Series.to_dict()} 或 {"ok": False, "error": "..."}
    """
    try:
        if agg == "nunique":
            result = df.groupby(group_col)[value_col].nunique().sort_values(ascending=False)
        else:
            result = getattr(df.groupby(group_col)[value_col], agg)().sort_values(ascending=True)
        if top_n:
            result = result.head(top_n)
        return {"ok": True, "data": {str(k): round(float(v), 2) for k, v in result.items()}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def monthly_trend(
    df: pd.DataFrame,
    metric: str = "revenue",
) -> dict[str, Any]:
    """月度趋势统计，自动标注2011-12为不完整月份。

    Args:
        df: 含InvoiceDate列的DataFrame
        metric: 统计指标列名

    Returns:
        {"ok": True, "data": {"series": {...}, "note": "..."}} 或错误
    """
    try:
        tmp = df.copy()
        tmp["ym"] = tmp["InvoiceDate"].dt.to_period("M")
        result = tmp.groupby("ym")[metric].sum()

        note = ""
        max_period = result.index.max()
        if max_period.month < 0:
            note = f"⚠ {max_period} 数据不完整（仅包含部分日期）"

        return {
            "ok": True,
            "data": {
                "series": {str(k): round(float(v), 2) for k, v in result.items()},
                "note": note,
            },
        }
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def country_top(df: pd.DataFrame, n: int = 10) -> dict[str, Any]:
    """国家GMV排名Top N。

    Args:
        df: 含revenue和Country列的DataFrame
        n: 取前N名

    Returns:
        {"ok": True, "data": {...}} 或 {"ok": False, "error": "..."}
    """
    try:
        result = df.groupby("Country")["revenue"].sum().sort_values(ascending=False).head(n)
        return {"ok": True, "data": {k: round(float(v), 2) for k, v in result.items()}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def rfm_table(df: pd.DataFrame) -> dict[str, Any]:
    """RFM客户分层表。

    R(Recency): 距今天数 → 分数1-5（越小越好，天数少=高分）
    F(Frequency): 订单数 → 分数1-5
    M(Monetary): 消费总额 → 分数1-5

    分层标签:
    - 总分>=12: 高价值客户
    - 总分>=8: 中价值客户
    - 总分<8: 低价值客户

    Args:
        df: 含CustomerID/InvoiceDate/InvoiceNo/revenue的DataFrame

    Returns:
        {"ok": True, "data": {"table": [...], "summary": {...}}}
    """
    try:
        ref_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
        rfm = df.groupby("CustomerID").agg(
            recency=("InvoiceDate", lambda x: (ref_date - x.max()).days),
            frequency=("InvoiceNo", "nunique"),
            monetary=("revenue", "sum"),
        ).reset_index()

        for col, ascending in [("recency", True), ("frequency", False), ("monetary", False)]:
            rfm[f"{col[:1]}_score"] = (
                pd.qcut(rfm[col], 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
            )

        if "r_score" in rfm.columns and "f_score" in rfm.columns and "m_score" in rfm.columns:
            rfm["total_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]
        else:
            rfm["total_score"] = 3

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
                       "r_score", "f_score", "m_score", "total_score", "segment"]].to_dict("records")

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


def bar_chart(
    items: list[str],
    values: list[float],
    title: str,
    out_html: str | Path,
) -> dict[str, Any]:
    """pyecharts横向柱状图，保存为HTML。

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
        from pyecharts.render import make_snapshot

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
        bar.render(str(out_html))
        return {"ok": True, "data": {"file": str(out_html)}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def line_chart(
    x_items: list[str],
    series_dict: dict[str, list[float]],
    title: str,
    out_html: str | Path,
) -> dict[str, Any]:
    """pyecharts折线图，支持多条线，保存为HTML。

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
        line.render(str(out_html))
        return {"ok": True, "data": {"file": str(out_html)}}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}

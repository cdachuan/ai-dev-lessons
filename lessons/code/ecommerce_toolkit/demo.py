# -*- coding: utf-8 -*-
"""电商工具箱Demo — 无需API Key，直接运行验证。

输出:
  output/kpi_summary.txt    — KPI摘要
  output/monthly_trend.csv  — 月度趋势数据
  output/top10_country.html — Top10国家GMV柱状图
"""
from pathlib import Path
import pandas as pd

from tools import (
    read_orders,
    clean_orders,
    kpi_summary,
    groupby_agg,
    monthly_trend,
    country_top,
    bar_chart,
)

DATA_PATH = Path(r"D:\学习\ai-dev\data\ecommerce\online_retail_2010_2011.csv")
OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 50)
    print("  电商数据分析工具箱 Demo")
    print("=" * 50)

    # 1. 读取数据
    print("\n[1/5] 读取CSV...")
    res = read_orders(DATA_PATH)
    if not res["ok"]:
        print(f"  ERROR: {res['error']}")
        return
    df_raw = res["data"]
    print(f"  原始行数: {len(df_raw):,}")

    # 2. 清洗
    print("[2/5] 清洗数据...")
    res = clean_orders(df_raw, drop_customer_na=True)
    if not res["ok"]:
        print(f"  ERROR: {res['error']}")
        return
    df = res["data"]
    print(f"  清洗后行数: {len(df):,}")

    # 3. KPI摘要
    print("[3/5] 计算KPI...")
    res = kpi_summary(df)
    if res["ok"]:
        kpi = res["data"]
        lines = []
        lines.append("电商数据 KPI 摘要")
        lines.append("-" * 40)
        for k, v in kpi.items():
            lines.append(f"  {k}: {v}")
        txt = "\n".join(lines)
        print(txt)
        (OUT_DIR / "kpi_summary.txt").write_text(txt, encoding="utf-8")
        print(f"  -> 已保存 {OUT_DIR / 'kpi_summary.txt'}")

    # 4. 月度趋势
    print("[4/5] 月度趋势...")
    res = monthly_trend(df, metric="revenue")
    if res["ok"]:
        trend = res["data"]
        print(f"  {trend['note']}" if trend["note"] else "  月份完整")
        rows = [{"month": k, "revenue": v} for k, v in trend["series"].items()]
        pd.DataFrame(rows).to_csv(OUT_DIR / "monthly_trend.csv", index=False, encoding="utf-8-sig")
        print(f"  -> 已保存 {OUT_DIR / 'monthly_trend.csv'}")

    # 5. Top10国家柱状图
    print("[5/5] Top10国家GMV图...")
    res = country_top(df, n=10)
    if res["ok"]:
        data = res["data"]
        bar_chart(
            items=list(data.keys())[::-1],
            values=list(data.values())[::-1],
            title="Top 10 国家 GMV",
            out_html=OUT_DIR / "top10_country.html",
        )
        print(f"  -> 已保存 {OUT_DIR / 'top10_country.html'}")

    print("\n" + "=" * 50)
    print("  Demo 完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()

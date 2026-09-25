# -*- coding: utf-8 -*-
"""变式1 · 验收脚本

用法:
    python 变式/变式验收_check.py 变式/变式1_tools_埋错版.py

原理: 用同一份真实电商数据分别跑 [原版 tools.py] 和 [你修的埋错版]，
      逐函数对比结果。全部 PASS = 修复完成。
      （行为对齐原版 = bug 清零，不用知道 bug 在哪）

数据: 变式/sales_dirty.csv（自动从桌面复制；没有则脚本自动生成同分布数据）
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = HERE / "sales_dirty.csv"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ensure_data():
    """生成确定性 Online Retail schema 数据（与工具箱函数签名匹配）。

    注意：桌面 sales_orders_dirty_5k.csv 是中文列名 schema（data_doctor 练习用），
    与本工具箱不匹配，不混用。本变式自带数据，seed 固定可复现。
    """
    if DATA.exists():
        return "cached"
    import pandas as pd
    import numpy as np
    rng = np.random.default_rng(42)
    n = 3000
    df = pd.DataFrame({
        "InvoiceNo": [f"INV{i:05d}" for i in range(n)],
        "InvoiceDate": pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 360, n), unit="D"),
        # 客户池 300 人 → 人均约10单，frequency 拉开梯度（qcut 5箱不塌）
        "CustomerID": rng.choice(np.arange(10000, 10300), n).astype(float),
        "Quantity": rng.integers(1, 20, n),
        "UnitPrice": rng.uniform(2, 100, n).round(2),
        "Country": rng.choice(["China", "Germany", "France", "UK"], n, p=[0.5, 0.2, 0.15, 0.15]),
    })
    # 埋真实业务脏点（clean_orders 的口径就是为这些设计的）
    df.loc[df.sample(frac=0.05, random_state=1).index, "UnitPrice"] = 0        # 免费单
    df.loc[df.sample(frac=0.08, random_state=2).index, "CustomerID"] = None    # 客户缺失
    ret = df.sample(frac=0.06, random_state=3).index
    df.loc[ret, "Quantity"] = -df.loc[ret, "Quantity"]                         # 退货
    df.loc[ret, "InvoiceNo"] = "C" + df.loc[ret, "InvoiceNo"]
    df.loc[df.sample(frac=0.01, random_state=4).index, "UnitPrice"] = -5       # 异常价
    # 数据截断到2025-11（触发 monthly_trend 的不完整月份警告）
    df = df[df["InvoiceDate"] < "2025-11-15"]
    df.to_csv(DATA, index=False, encoding="utf-8-sig")
    return "generated"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    fixed_path = Path(sys.argv[1])
    if not fixed_path.exists():
        print(f"找不到文件: {fixed_path}")
        sys.exit(1)

    src = ensure_data()
    orig = load_module(ROOT / "tools.py", "tools_orig")
    fixed = load_module(fixed_path, "tools_fixed")

    results = []

    def check(name, fn_orig, fn_fixed):
        try:
            a, b = fn_orig(), fn_fixed()
            ok = a == b
            results.append((name, ok, "" if ok else f"\n    原版={str(a)[:120]}\n    你的={str(b)[:120]}"))
        except Exception as e:
            results.append((name, False, f"你的版本抛异常: {type(e).__name__}: {e}"))

    # —— 数据准备（两边同起点） ——
    r1_o = orig.read_orders(DATA)
    r1_f = fixed.read_orders(DATA)
    check("read_orders（读取）",
          lambda: (r1_o["ok"], list(r1_o.get("data", pd_empty()).columns) if r1_o["ok"] else r1_o.get("error")),
          lambda: (r1_f["ok"], list(r1_f.get("data", pd_empty()).columns) if r1_f["ok"] else r1_f.get("error")))

    if not (r1_o["ok"] and r1_f["ok"]):
        print("读取阶段就失败，先修 read_orders。原版错误:", r1_o.get("error"), "你的:", r1_f.get("error"))
        sys.exit(1)

    r2_o = orig.clean_orders(r1_o["data"])
    r2_f = fixed.clean_orders(r1_f["data"])
    check("clean_orders（清洗/退货口径）",
          lambda: (int(len(r2_o["data"])), round(float(r2_o["data"]["revenue"].sum()), 2),
                   int((r2_o["data"]["revenue"] < 0).sum())),
          lambda: (int(len(r2_f["data"])), round(float(r2_f["data"]["revenue"].sum()), 2),
                   int((r2_f["data"]["revenue"] < 0).sum())))

    dfo, dff = r2_o["data"], r2_f["data"]
    check("kpi_summary（KPI六指标）",
          lambda: orig.kpi_summary(dfo)["data"],
          lambda: fixed.kpi_summary(dff)["data"])

    check("groupby_agg（品类Top3）",
          lambda: orig.groupby_agg(dfo, "Country", top_n=3)["data"],
          lambda: fixed.groupby_agg(dff, "Country", top_n=3)["data"])

    check("monthly_trend（月度趋势+警告）",
          lambda: (orig.monthly_trend(dfo)["data"]["series"], orig.monthly_trend(dfo)["data"]["note"]),
          lambda: (fixed.monthly_trend(dff)["data"]["series"], fixed.monthly_trend(dff)["data"]["note"]))

    check("rfm_table（RFM分层汇总）",
          lambda: (orig.rfm_table(dfo)["data"]["summary"], str(orig.rfm_table(dfo)["data"]["reference_date"])),
          lambda: (fixed.rfm_table(dff)["data"]["summary"], str(fixed.rfm_table(dff)["data"]["reference_date"])))

    # —— 报告 ——
    print(f"\n数据源: {src}")
    print("=" * 52)
    npass = 0
    for name, ok, msg in results:
        mark = "PASS" if ok else "FAIL"
        npass += ok
        print(f"[{mark}] {name}{msg}")
    print("=" * 52)
    print(f"{npass}/{len(results)} 通过")
    if npass == len(results):
        print("🎉 全部通过，bug 已清零。数一数自己找到了几处，对答案看 变式/变式1_答案.md")
    else:
        print("还有 bug。提示：挂掉的那个函数里，逐行对照它的 docstring 口径说明读。")


def pd_empty():
    import pandas as pd
    return pd.DataFrame()


if __name__ == "__main__":
    main()

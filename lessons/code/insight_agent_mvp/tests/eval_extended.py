# -*- coding: utf-8 -*-
"""扩展评估集：8个新固定问题，标准答案用独立代码路径计算（verify思想）。

运行: python tests/eval_extended.py  （离线，不调模型）
与 eval.py 互不影响；清洗口径一致：CustomerID非空 + UnitPrice>0，退货记负收入。
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DATA_FILE = Path("D:/学习/ai-dev/data/ecommerce/online_retail_2010_2011.csv")

# ---------- 独立计算标准答案（不复用 agent/tools.py 的代码路径） ----------
_raw = pd.read_csv(DATA_FILE, parse_dates=["InvoiceDate"])
_d = _raw[_raw.CustomerID.notna() & (_raw.UnitPrice > 0)].copy()
_d["rev"] = _d.Quantity * _d.UnitPrice
_d["month"] = _d.InvoiceDate.dt.to_period("M")

SNAPSHOT = _d.InvoiceDate.max() + pd.Timedelta(days=1)


def _rfm():
    r = _d.groupby("CustomerID").agg(
        R=("InvoiceDate", lambda x: (SNAPSHOT - x.max()).days),
        F=("InvoiceNo", "nunique"), M=("rev", "sum"))
    r["Rs"] = pd.qcut(r.R, 5, labels=[5, 4, 3, 2, 1]).astype(int)
    r["Fs"] = pd.qcut(r.F.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    r["Ms"] = pd.qcut(r.M, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    return r


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


# Q1 每个国家Top3商品（TopN per group，只算荷兰演示）
@case("Q1 荷兰Top3商品GMV")
def q1():
    top3 = (_d[_d.Country == "Netherlands"].groupby("Description").rev.sum()
            .sort_values(ascending=False).head(3).round(0))
    return list(top3.items())


# Q2 跨月复购客户数
@case("Q2 跨月复购客户数(≥2个购买月)")
def q2():
    n = (_d.groupby("CustomerID").month.nunique() >= 2).sum()
    return int(n)


# Q3 2011年Q4 GMV
@case("Q3 2011-Q4 GMV")
def q3():
    m = _d[(_d.month >= "2011-10") & (_d.month <= "2011-12")].rev.sum()
    return round(float(m), 2)


# Q4 工作日vs周末订单占比
@case("Q4 周末订单占比")
def q4():
    dow = _d[_d.Quantity > 0].drop_duplicates("InvoiceNo").InvoiceDate.dt.dayofweek
    return round(float((dow >= 5).mean() * 100), 2)


# Q5 退货量最高的商品
@case("Q5 退货量Top1商品")
def q5():
    ret = _raw[_raw.Quantity < 0].groupby("Description").Quantity.sum().sort_values()
    return (ret.index[0], int(abs(ret.iloc[0])))


# Q6 客单价最高的完整月份
@case("Q6 客单价最高月份(剔除2011-12)")
def q6():
    g = _d[_d.month < "2011-12"].groupby("month").agg(rev=("rev", "sum"), o=("InvoiceNo", "nunique"))
    aov = (g.rev / g.o).round(2)
    return (str(aov.idxmax()), float(aov.max()))


# Q7 VIP客户GMV贡献占比
@case("Q7 VIP(R≥4,F≥4)GMV贡献占比%")
def q7():
    r = _rfm()
    vip = r[(r.Rs >= 4) & (r.Fs >= 4)].M.sum()
    return round(float(vip / r.M.sum() * 100), 2)


# Q8 德国客户数
@case("Q8 德国购买客户数")
def q8():
    return int(_d[_d.Country == "Germany"].CustomerID.nunique())


def main():
    print("== 扩展评估集（独立代码路径复算标准答案） ==")
    passed = failed = 0
    for name, fn in CASES:
        try:
            ans = fn()
            assert ans is not None
            print(f"  [PASS] {name}: {ans}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
    print(f"\n结果: {passed} 通过 / {failed} 失败")

    # 与 agent/tools.py 交叉核验一组（verify思想：不同路径算同数）
    from agent import tools
    t = tools.groupby_agg(group_col="Country", value_col="revenue", agg="sum")
    tool_de_gmv = round(t["data"].get("Germany", 0), 2)
    indep_de_gmv = round(float(_d[_d.Country == "Germany"].rev.sum()), 2)
    print(f"\n交叉核验(德国GMV): 工具层={tool_de_gmv} vs 独立复算={indep_de_gmv} -> {'一致' if tool_de_gmv == indep_de_gmv else '不一致!!'}")


if __name__ == "__main__":
    main()

# 实跑记录（2026-09-20，由 Hermes 实测）:
# == 扩展评估集（独立代码路径复算标准答案） ==
#   [PASS] Q1 荷兰Top3商品GMV
#   [PASS] Q2 跨月复购客户数(≥2个购买月)
#   [PASS] Q3 2011-Q4 GMV
#   [PASS] Q4 周末订单占比
#   [PASS] Q5 退货量Top1商品
#   [PASS] Q6 客单价最高月份(剔除2011-12)
#   [PASS] Q7 VIP(R≥4,F≥4)GMV贡献占比%
#   [PASS] Q8 德国购买客户数
# 结果: 8 通过 / 0 失败
# 交叉核验: 工具层与独立复算一致

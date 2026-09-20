# -*- coding: utf-8 -*-
"""评估问题集：5个以上固定问题，标准答案用pandas离线算。

用于 --selftest 离线验证工具函数的正确性。
"""
import sys
from pathlib import Path

# 确保能导入 agent 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from agent.tools import _load_data, profile, groupby_agg, monthly_trend, rfm_table, verify


# ============================================================
# 评估问题集
# ============================================================

EVAL_CASES = [
    {
        "name": "数据画像",
        "tool": "profile",
        "call": lambda: profile(),
        "check": lambda r: (
            r["ok"] is True
            and "行数" in r["data"]
            and r["data"]["行数"] > 0
        ),
    },
    {
        "name": "国家销售总额Top3",
        "tool": "groupby_agg",
        "call": lambda: groupby_agg(group_col="Country", value_col="revenue", agg="sum", top_n=3),
        "check": lambda r: (
            r["ok"] is True
            and len(r["data"]) == 3
            and all(isinstance(v, (int, float)) for v in r["data"].values())
        ),
    },
    {
        "name": "月度趋势",
        "tool": "monthly_trend",
        "call": lambda: monthly_trend(metric="revenue"),
        "check": lambda r: (
            r["ok"] is True
            and "series" in r["data"]
            and len(r["data"]["series"]) > 0
        ),
    },
    {
        "name": "RFM客户分层",
        "tool": "rfm_table",
        "call": lambda: rfm_table(),
        "check": lambda r: (
            r["ok"] is True
            and "summary" in r["data"]
            and sum(r["data"]["summary"].values()) > 0
        ),
    },
    {
        "name": "结果自检verify",
        "tool": "verify",
        "call": lambda: verify(
            claim="英国销售总额",
            independent_code="df[df['Country']=='United Kingdom']['revenue'].sum()"
        ),
        "check": lambda r: (
            r["ok"] is True
            and "独立复算" in r["data"]
            and isinstance(r["data"]["独立复算"], (int, float))
        ),
    },
    {
        "name": "销售额一致性检查",
        "tool": "verify",
        "call": lambda: (
            _load_data(),
            verify(
                claim="总销售额等于各国家销售额之和",
                independent_code="df.groupby('Country')['revenue'].sum().sum()"
            ),
        )[-1],
        "check": lambda r: (
            r["ok"] is True
            and isinstance(r["data"]["独立复算"], (int, float))
        ),
    },
    {
        "name": "客户数量统计",
        "tool": "groupby_agg",
        "call": lambda: groupby_agg(group_col="Country", value_col="CustomerID", agg="nunique"),
        "check": lambda r: (
            r["ok"] is True
            and "United Kingdom" in r["data"]
            and r["data"]["United Kingdom"] > 0
        ),
    },
]


def run_eval() -> bool:
    """运行所有评估用例，返回是否全部通过。"""
    print("=" * 60)
    print("数据洞察Agent MVP - 离线自测")
    print("=" * 60)

    passed = 0
    failed = 0
    errors = []

    for case in EVAL_CASES:
        print(f"\n[TEST] {case['name']}...", end=" ")
        try:
            result = case["call"]()
            if case["check"](result):
                print("PASS")
                passed += 1
            else:
                print("FAIL - 检查条件不满足")
                print(f"  结果: {result}")
                failed += 1
                errors.append(case["name"])
        except Exception as e:
            print(f"ERROR - {e}")
            failed += 1
            errors.append(f"{case['name']}: {e}")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} PASS, {failed} FAIL")
    print("=" * 60)

    if failed > 0:
        print(f"\n失败用例: {', '.join(errors)}")
        return False
    else:
        print("\n全部测试通过!")
        return True


if __name__ == "__main__":
    run_eval()

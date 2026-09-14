# -*- coding: utf-8 -*-
"""固定测试问题集（35 课）：无需 key、不调模型，纯 pandas 离线核对。

每道题两列：
- expected：人工（教练）事先用独立代码算好的标准答案
- 实测：直接调用 Agent 的工具函数得到的结果
两者一致才算通过。这同时演示了 34 课的核验思想——
评估集就是给整个 Agent 准备的 verify。

换自己的数据后：先改这里的问题和 expected，再跑 selftest。
"""
from agent import tools as T

# 标准答案（用与工具实现不同的写法，在示例数据上独立算得）
EXPECTED = {
    "各品类销售额_剔除退款": {
        "数码": 15750, "家居": 6150, "服饰": 3440, "食品": 1830},
    "销售额合计_剔除退款": 27170,
    "各渠道订单量_全部": {"天猫": 29, "抖音": 17, "自营": 14},
    "各渠道退款率_percent": {"天猫": 3.4, "抖音": 17.6, "自营": 0.0},
    "不同订单号数": 60,
}


def run_selftest():
    passed, failed = [], []

    def check(name, cond, detail=""):
        (passed if cond else failed).append(name)
        mark = "PASS" if cond else "FAIL"
        print(f"  [{mark}] {name}" + (f"  -> {detail}" if detail and not cond else ""))

    print("== 固定测试问题集（离线，不调模型） ==")

    # Q1 各品类销售额（剔除退款）—— 口径：只算状态='已完成'
    r1 = T.group_sum("品类", filter_status="已完成")["结果"]
    check("Q1 各品类销售额(剔除退款)", r1 == EXPECTED["各品类销售额_剔除退款"],
          f"得到 {r1}")

    # Q1b 总额独立复算：布尔索引 + sum（与 groupby 不同的路径）
    df_total = T._df()
    total = int(df_total[df_total["状态"] == "已完成"]["金额"].sum())
    check("Q1b 销售额合计独立复算", total == EXPECTED["销售额合计_剔除退款"],
          f"得到 {total}")

    # Q2 各渠道订单量（全部订单，含退款）
    r2 = T.group_count("渠道")["结果"]
    check("Q2 各渠道订单量(全部)", r2 == EXPECTED["各渠道订单量_全部"], f"得到 {r2}")

    # Q3 各渠道退款率 = 已退款单数 / 全部订单
    all_n = T.group_count("渠道")["结果"]
    refund_n = T.group_count("渠道", filter_status="已退款")["结果"]
    rate = {k: round(refund_n.get(k, 0) / all_n[k] * 100, 1) for k in all_n}
    check("Q3 各渠道退款率", rate == EXPECTED["各渠道退款率_percent"], f"得到 {rate}")

    # Q4 多少个不同订单号（nunique，不是 count）
    n = T.count_distinct("订单号")["去重计数"]
    check("Q4 不同订单号数(nunique)", n == EXPECTED["不同订单号数"], f"得到 {n}")

    # Q5 核验卡口本身要能抓住错误 claim
    v_ok = T.verify("数码15750",
                    "df[df['状态']=='已完成'].query('品类==\"数码\"')['金额'].sum()")
    check("Q5a verify 能复算正确值", v_ok.get("独立复算") == 15750, f"得到 {v_ok}")
    v_bad = T.verify("不存在的列也能跑", "df['不存在列'].sum()")
    check("Q5b verify 出错时返回失败而非崩溃", v_bad.get("核验") == "失败")

    print(f"\n结果：{len(passed)} 通过 / {len(failed)} 失败")
    if failed:
        print("失败项：", failed)
        return 1
    print("全部通过。数据口径与工具行为一致，可以配 key 向 Agent 提问了。")
    return 0

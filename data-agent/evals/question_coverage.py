# -*- coding: utf-8 -*-
"""BI 工具覆盖率考题集 v2（v1 + OP交叉验证修正）

v2 变更（2026-09-22 交叉验证）：
- 改写 5 道内部术语题（id 19/28/30/35 + TopN理由）
- 时间趋势拆分：实测 groupby_sum 对天级日期列可分组 → "每天销售额"判能答；
  月/周粒度和环比仍缺 → 加 date_grain 参数后可救
- 补 12 题（OP 补充清单，电商高频口语化问法）
- 资产命中题注明前置条件：口径匹配的资产已入库

工具面版本对照：
- "v1工具" = profile_data / groupby_sum(sum+单条件等值过滤) / verify
- "v2工具" = + groupby_agg(agg=sum|mean|count|nunique, top_n, date_grain=day|month|week) + verify 泛化
"""
from collections import Counter

# cat ∈ 分组聚合/聚合变体/TopN/透视/时间趋势/比率派生/数值过滤/资产命中/超界转介
# v1: 现有v1工具能否答;  v2: 泛化后能否答
QUESTIONS = [
    # ---- 分组聚合 ----
    {"id": 1,  "q": "各品类的销售额分别是多少", "cat": "分组聚合", "v1": True},
    {"id": 2,  "q": "各省份的订单金额总和", "cat": "分组聚合", "v1": True},
    {"id": 3,  "q": "各销售渠道的销售额", "cat": "分组聚合", "v1": True},
    {"id": 4,  "q": "已完成订单里，各品类的销售额是多少", "cat": "分组聚合", "v1": True},
    {"id": 5,  "q": "京东渠道的各省销售额分布", "cat": "分组聚合", "v1": True},
    {"id": 6,  "q": "每个状态各有多少金额", "cat": "分组聚合", "v1": True},
    {"id": 7,  "q": "广东省的各品类销售情况", "cat": "分组聚合", "v1": True},
    {"id": 8,  "q": "淘宝和京东各自的销售额对比", "cat": "分组聚合", "v1": True,
     "note": "两次调用拼接，LLM提取拼答，OP判'可接受'"},
    # ---- 聚合变体（v2 的 agg 参数救回） ----
    {"id": 9,  "q": "各品类的平均客单价是多少", "cat": "聚合变体", "v1": False, "v2": True},
    {"id": 10, "q": "每个省份有多少笔订单", "cat": "聚合变体", "v1": False, "v2": True},
    {"id": 11, "q": "各渠道有几个不同的品类在卖", "cat": "聚合变体", "v1": False, "v2": True},
    {"id": 12, "q": "哪个品类的订单数最多", "cat": "聚合变体", "v1": False, "v2": True},
    {"id": 13, "q": "各省订单的平均金额", "cat": "聚合变体", "v1": False, "v2": True},
    # ---- TopN（v1实测：groupby_sum返回已排序dict，取前N=纯提取 → v1能答） ----
    {"id": 14, "q": "销售额最高的5个省份", "cat": "TopN", "v1": True,
     "note": "交叉验证改判：返回已排序，LLM取前5是提取不是计算"},
    {"id": 15, "q": "卖得最差的3个品类是哪些", "cat": "TopN", "v1": True},
    {"id": 16, "q": "销售额前十的渠道", "cat": "TopN", "v1": True},
    # ---- 透视（v3 pivot_table 救回） ----
    {"id": 17, "q": "各品类在各渠道的销售额分别是多少", "cat": "透视", "v1": False, "v2": False, "v3": True},
    {"id": 18, "q": "每个月各品类的销售额对比", "cat": "透视", "v1": False, "v2": False, "v3": True},
    {"id": 19, "q": "各省各状态的订单金额分别是多少", "cat": "透视", "v1": False, "v2": False, "v3": True,
     "note": "v2改写：去掉'矩阵'术语"},
    # ---- 时间趋势（v2 的 date_grain 救回月/周；环比不救） ----
    {"id": 20, "q": "每天的销售额趋势", "cat": "时间趋势", "v1": True,
     "note": "实测：group_col=日期列天级分组可跑（2026-09-22实跑证据）"},
    {"id": 21, "q": "这个月和上个月的销售额对比", "cat": "时间趋势", "v1": False, "v2": True},
    {"id": 22, "q": "销售额比上个月增长了百分之多少", "cat": "时间趋势", "v1": False, "v2": False, "v3": True,
     "note": "v3: trend_compare+verify_trend_compare 救回"},
    {"id": 23, "q": "哪个周的销售额最高", "cat": "时间趋势", "v1": False, "v2": True},
    # ---- 比率派生（v2 不救：口径复合计算，资产复用是正道） ----
    {"id": 24, "q": "各品类的退款率是多少", "cat": "比率派生", "v1": False,
     "note": "若退款率资产在库→可命中；此处按'无资产新口径'保守判"},
    {"id": 25, "q": "哪个渠道的完成率最低", "cat": "比率派生", "v1": False},
    {"id": 26, "q": "各品类销售额占总盘子的百分比", "cat": "比率派生", "v1": False,
     "note": "OP补充：占比类"},
    # ---- 数值过滤（v3 的 filter_op+filter2 救回） ----
    {"id": 27, "q": "金额超过5000的订单有多少笔", "cat": "数值过滤", "v1": False, "v2": False, "v3": True},
    {"id": 28, "q": "大单都集中在哪些品类", "cat": "数值过滤", "v1": False, "v2": False, "v3": True,
     "note": "v2改写：'大单'口语化；v3: 区间过滤救回（'大单'阈值需LLM或人定义，算口径对话）"},
    {"id": 29, "q": "已退款且金额超过1000的订单", "cat": "数值过滤", "v1": False, "v2": False, "v3": True,
     "note": "v3: 双条件过滤救回"},
    # ---- 资产命中（前置：对应口径资产已入库——ecommerce_demo 实有2条） ----
    {"id": 30, "q": "各品类已完成订单的销售额是多少", "cat": "资产命中", "v1": True,
     "note": "v2改写：去括号术语；命中 category_sales_completed 资产"},
    {"id": 31, "q": "各品类的退款率（按订单数口径）是多少", "cat": "资产命中", "v1": True,
     "note": "命中 category_refund_rate 资产"},
    # ---- 超界转介（设计上不该答，不入分母） ----
    {"id": 32, "q": "为什么华南地区销售额下滑了", "cat": "超界转介", "v1": False},
    {"id": 33, "q": "下个月销售额能到多少", "cat": "超界转介", "v1": False},
    {"id": 34, "q": "退货率高是因为物流问题吗", "cat": "超界转介", "v1": False},
    {"id": 35, "q": "应该加大哪个渠道的投放", "cat": "超界转介", "v1": False},
    # ---- OP 补充的 12 题（口语化高频） ----
    {"id": 36, "q": "这个月销售额是多少", "cat": "时间趋势", "v1": False, "v2": True},
    {"id": 37, "q": "哪个渠道的订单量最多", "cat": "聚合变体", "v1": False, "v2": True},
    {"id": 38, "q": "各品类的退货率是多少", "cat": "比率派生", "v1": False},
    {"id": 39, "q": "已退款和已完成订单的销售额各是多少", "cat": "分组聚合", "v1": True},
    {"id": 40, "q": "各渠道的客单价是多少", "cat": "聚合变体", "v1": False, "v2": True},
    {"id": 41, "q": "最近一周的销售额趋势", "cat": "时间趋势", "v1": False, "v2": True},
    {"id": 42, "q": "哪个省份的订单数增长最快", "cat": "时间趋势", "v1": False, "v2": False, "v3": True,
     "note": "v3: trend_compare按省过滤或逐省对比可救（分组增长场景稍复杂但工具已够）"},
    {"id": 43, "q": "各品类订单金额波动大不大", "cat": "聚合变体", "v1": False,
     "note": "std聚合，v2的agg白名单若含std则救"},
    {"id": 44, "q": "大促期间比平时卖得怎么样", "cat": "时间趋势", "v1": False,
     "note": "需大促日期口径定义，超固定合同"},
    {"id": 45, "q": "各渠道销售额环比增长了多少", "cat": "时间趋势", "v1": False,
     "note": "环比，v2不救"},
    {"id": 46, "q": "一天当中哪个时段订单最多", "cat": "时间趋势", "v1": False,
     "note": "schema无小时字段，数据缺口不是工具缺口"},
    {"id": 47, "q": "卖得最好的品类占总销售额多少", "cat": "比率派生", "v1": False},
]


def summary():
    total = len(QUESTIONS)
    cnt = Counter(q["cat"] for q in QUESTIONS)
    referable = cnt.get("超界转介", 0)
    bi_scope = total - referable

    def cov(version):
        # v3可答 = v1或v2或v3 任一为 True
        ok_keys = {"v1": ("v1",), "v2": ("v1", "v2"), "v3": ("v1", "v2", "v3")}[version]
        return sum(1 for q in QUESTIONS if q["cat"] != "超界转介"
                   and any(q.get(k) is True for k in ok_keys))

    v1r, v2r, v3r = cov("v1"), cov("v2"), cov("v3")

    print(f"考题总数: {total}（BI应答分母 {bi_scope}，转介 {referable} 不入分母）")
    print("\n各形态分布与判定:")
    for c, n in cnt.most_common():
        items = [q for q in QUESTIONS if q["cat"] == c]
        stat = lambda keys: sum(1 for q in items if any(q.get(k) is True for k in keys))
        v1n = stat(("v1",))
        v2n = stat(("v1", "v2"))
        v3n = stat(("v1", "v2", "v3"))
        print(f"  {c}: {n}题  v1可答{v1n} → v2可答{v2n} → v3可答{v3n}")
    print(f"\n覆盖率: v1 {v1r}/{bi_scope}={v1r/bi_scope*100:.0f}%"
          f"  → v2 {v2r}/{bi_scope}={v2r/bi_scope*100:.0f}%"
          f"  → v3 {v3r}/{bi_scope}={v3r/bi_scope*100:.0f}%")

    remain = [(q["id"], q["q"]) for q in QUESTIONS
              if q["cat"] != "超界转介" and not any(q.get(k) is True for k in ("v1", "v2", "v3"))]
    print(f"\nv3 后仍缺口 {len(remain)} 题:")
    for i, q in remain:
        print(f"  #{i} {q}")


if __name__ == "__main__":
    summary()

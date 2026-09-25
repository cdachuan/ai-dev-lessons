# -*- coding: utf-8 -*-
"""无 key 联调：直接打工具层，验证字典/画像/聚合/核验四件套跑通。"""
import sys, json
sys.path.insert(0, ".")
from data_agent.tools import profile_data, groupby_sum, verify_groupby_sum

print("=== 1. 画像 ===")
card = profile_data("orders")
print(json.dumps(card, ensure_ascii=False, indent=1)[:800])

print("\n=== 2. 分组聚合（completed 口径） ===")
r = groupby_sum("orders", group_col="category", value_col="amount", filter_col="status", filter_value="completed")
print(json.dumps(r, ensure_ascii=False))

print("\n=== 3. verify 双路径核验 ===")
v = verify_groupby_sum("orders", "category", "amount", expected=r["result"], filter_col="status", filter_value="completed")
print(json.dumps(v, ensure_ascii=False))

print("\n=== 4. 反例：无效取值应被字典拦下 ===")
try:
    groupby_sum("orders", "category", "amount", filter_col="status", filter_value="已完成")
except ValueError as e:
    print("已拦截:", e)

print("\n=== 5. 反例：字典里没有的列 ===")
try:
    groupby_sum("orders", "cat", "amount")
except KeyError as e:
    print("已拦截:", e)

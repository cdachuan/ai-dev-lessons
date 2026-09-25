# -*- coding: utf-8 -*-
"""带已知规律的 ML mock 数据：refund_prob = sigmoid(0.8*高金额 + 1.5*数码 - 0.5*家居)

已知答案（工具层验收的考题）：
- 高金额（>500）退款概率显著更高
- 数码类目退款风险最高，家居最低
- 金额是最重要特征
"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(7)
np.random.seed(7)

N = 800
categories = ["数码", "家居", "服饰", "食品"]

rows = []
for i in range(N):
    amount = round(random.uniform(9.9, 999.0), 2)
    category = random.choice(categories)
    # 已知规律：logit = 0.8*(amount>500) + 1.5*(category==数码) - 0.5*(category==家居) - 1.0
    logit = -1.0
    if amount > 500:
        logit += 0.8
    if category == "数码":
        logit += 1.5
    if category == "家居":
        logit -= 0.5
    prob = 1 / (1 + np.exp(-logit))
    refunded = 1 if random.random() < prob else 0
    rows.append({
        "order_id": f"M{i:06d}",
        "amount": amount,
        "category": category,
        "user_orders_30d": random.randint(1, 8),
        "discount_rate": round(random.uniform(0, 0.3), 2),
        "refunded": refunded,
        "created_at": (datetime(2026, 8, 1) + timedelta(minutes=random.randint(0, 31 * 24 * 60))).strftime("%Y-%m-%d %H:%M:%S"),
    })

df = pd.DataFrame(rows)
df.to_csv("data/ml_orders.csv", index=False, encoding="utf-8-sig")
print(f"生成 {len(df)} 行 -> data/ml_orders.csv")
print("退款率:", df["refunded"].mean().round(4))
print(df.groupby("category")["refunded"].agg(["mean", "count"]).round(3))
print("高金额(>500) vs 低金额 退款率:")
print(df.assign(high=df["amount"] > 500).groupby("high")["refunded"].mean().round(3))

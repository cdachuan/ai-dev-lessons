# -*- coding: utf-8 -*-
"""生成 mock 订单数据，供联调用。"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

N = 500
statuses = ["completed"] * 300 + ["cancelled"] * 80 + ["pending"] * 70 + ["refunded"] * 50
random.shuffle(statuses)
categories = ["数码", "家居", "服饰", "食品"]

rows = []
for i in range(N):
    rows.append({
        "order_id": f"O{i:06d}",
        "user_id": f"U{random.randint(1, 120):04d}",
        "status": statuses[i],
        "amount": round(random.uniform(9.9, 999.0), 2),
        "category": random.choice(categories),
        "created_at": (datetime(2026, 8, 1) + timedelta(minutes=random.randint(0, 31 * 24 * 60))).strftime("%Y-%m-%d %H:%M:%S"),
    })

df = pd.DataFrame(rows)
df.to_csv("data/orders.csv", index=False, encoding="utf-8-sig")
print(f"生成 {len(df)} 行 -> data/orders.csv")
print(df.head())
print(df["status"].value_counts())

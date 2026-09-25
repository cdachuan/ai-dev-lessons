# -*- coding: utf-8 -*-
"""大屏问数 mock 宽表：带地区（省）+ 日期维度，供 BI 模式问数和地图下钻演示。"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(99)
np.random.seed(99)

PROVINCES = {
    "广东": 1.6, "浙江": 1.3, "江苏": 1.2, "上海": 1.1, "北京": 1.05,
    "四川": 0.9, "湖北": 0.8, "福建": 0.75, "山东": 0.7, "河南": 0.6,
    "湖南": 0.55, "安徽": 0.5,
}
CATEGORIES = ["数码", "家居", "服饰", "食品"]

N = 3000
rows = []
for i in range(N):
    prov = random.choices(list(PROVINCES), weights=list(PROVINCES.values()))[0]
    cat = random.choice(CATEGORIES)
    days_ago = random.randint(0, 59)
    date = (datetime(2026, 8, 31) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    amount = round(random.uniform(19.9, 1299.0), 2)
    rows.append({
        "order_id": f"D{i:06d}",
        "province": prov,
        "category": cat,
        "amount": amount,
        "order_date": date,
    })

df = pd.DataFrame(rows)
df.to_csv("data/dash_orders.csv", index=False, encoding="utf-8-sig")
print(f"生成 {len(df)} 行 -> data/dash_orders.csv")
print(df.groupby("province")["amount"].sum().sort_values(ascending=False).head(5).round(0))
print("日期范围:", df["order_date"].min(), "→", df["order_date"].max())

# -*- coding: utf-8 -*-
"""场景2：脏数据护栏 — Agent面对真实世界的CSV。

演示四类脏数据的"检测→处理→留痕"三步：
  1. 缺失值（CustomerID为空）
  2. 负数退货行（Quantity < 0 或 InvoiceNo以'C'开头）
  3. 异常单价（UnitPrice <= 0 或 > 5000）
  4. 重复发票行（完全相同的行）
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "ecommerce" / "online_retail_2010_2011.csv"
ROWS_LIMIT = 10000  # 只读前1万行


def _log(msg: str) -> None:
    print(f"  [LOG] {msg}")


def load_raw() -> pd.DataFrame:
    _log(f"读取 {DATA_FILE.name} 前 {ROWS_LIMIT} 行...")
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig", nrows=ROWS_LIMIT)
    _log(f"原始行数: {len(df)}")
    return df


def clean_data(raw: pd.DataFrame) -> dict:
    """执行全部四类清洗，返回统计。"""
    df = raw.copy()
    df["_cleaned_by"] = ""  # 留痕列
    stats: dict[str, int] = {}

    # ---- 1. 缺失值：CustomerID ----
    mask_missing = df["CustomerID"].isna()
    n = int(mask_missing.sum())
    _log(f"[缺失值- CustomerID] 检测到 {n} 行问题")
    _log(f"[缺失值- CustomerID] 处理: 丢弃 {n} 行 → 剩余 {len(df) - n} 行")
    df = df.loc[~mask_missing].copy()
    stats["缺失值(CustomerID)"] = n

    # ---- 2. 负数退货行 ----
    mask_return = (df["Quantity"] < 0) | (df["InvoiceNo"].astype(str).str.startswith("C"))
    df_returned = df.loc[mask_return].copy()
    df_returned["_cleaned_by"] = "退货"
    n2 = int(mask_return.sum())
    _log(f"[负数退货] 检测到 {n2} 行问题")
    _log(f"[负数退货] 处理: 丢弃 {n2} 行 → 剩余 {len(df) - n2} 行")
    df = df.loc[~mask_return].copy()
    stats["负数退货"] = n2

    # ---- 3. 异常单价 ----
    mask_price = (df["UnitPrice"] <= 0) | (df["UnitPrice"] > 5000)
    n3 = int(mask_price.sum())
    _log(f"[异常单价] 检测到 {n3} 行问题")
    _log(f"[异常单价] 处理: 丢弃 {n3} 行 → 剩余 {len(df) - n3} 行")
    df = df.loc[~mask_price].copy()
    stats["异常单价(<=0或>5000)"] = n3

    # ---- 4. 重复行 ----
    mask_dup = df.duplicated(keep="first")
    n4 = int(mask_dup.sum())
    _log(f"[重复发票行] 检测到 {n4} 行问题")
    _log(f"[重复发票行] 处理: 丢弃 {n4} 行 → 剩余 {len(df) - n4} 行")
    df = df.loc[~mask_dup].copy()
    stats["重复行"] = n4

    stats["清洗前行数"] = len(raw)
    stats["清洗后行数"] = len(df)
    stats["总丢弃行数"] = len(raw) - len(df)

    return {"stats": stats, "cleaned_df": df, "returned_df": df_returned}


def run_demo() -> None:
    print("=" * 60)
    print("Demo 2: 脏数据护栏")
    print("=" * 60)

    raw = load_raw()
    result = clean_data(raw)
    stats = result["stats"]

    print("\n--- 清洗统计 ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 展示退货样本
    ret = result["returned_df"]
    if len(ret) > 0:
        print(f"\n--- 退货行样本（前5行）---")
        print(ret[["InvoiceNo", "Description", "Quantity", "UnitPrice"]].head().to_string(index=False))

    # 展示清洗后数据画像
    cleaned = result["cleaned_df"]
    print(f"\n--- 清洗后数据画像 ---")
    print(f"  行数: {len(cleaned)}")
    print(f"  列数: {len(cleaned.columns)}")
    print(f"  UnitPrice 范围: {cleaned['UnitPrice'].min():.2f} ~ {cleaned['UnitPrice'].max():.2f}")
    print(f"  Quantity 范围: {cleaned['Quantity'].min()} ~ {cleaned['Quantity'].max()}")
    print(f"  唯一客户数: {cleaned['CustomerID'].nunique()}")

    # 前3行样本
    print(f"\n--- 清洗后前3行 ---")
    print(cleaned[["InvoiceNo", "Description", "Quantity", "UnitPrice", "CustomerID"]].head(3).to_string(index=False))


if __name__ == "__main__":
    run_demo()

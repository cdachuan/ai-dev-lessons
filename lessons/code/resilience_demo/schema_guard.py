# -*- coding: utf-8 -*-
"""场景3：Schema防护 — Agent面对字段缺失或类型变化。

演示：
  1. 列名映射表（兼容不同来源的字段名差异）
  2. 类型断言（字段类型变了就报清晰错误）
  3. 字段缺失时报明确错误，而不是深层 stack trace
"""
from __future__ import annotations

from typing import Any


def _log(msg: str) -> None:
    print(f"  [LOG] {msg}")


# ============================================================
# 1. 列名映射表
# ============================================================

# 真实世界的字段名可能因数据源不同而变化
# 映射表：期望列名 → 可能的别名列表
COLUMN_ALIASES: dict[str, list[str]] = {
    "InvoiceNo": ["InvoiceNo", "invoice_no", "invoiceNumber", "order_id"],
    "StockCode": ["StockCode", "stock_code", "sku", "product_code"],
    "Description": ["Description", "description", "item_name", "product_name"],
    "Quantity": ["Quantity", "quantity", "qty", "count"],
    "InvoiceDate": ["InvoiceDate", "invoice_date", "order_date", "date"],
    "UnitPrice": ["UnitPrice", "unit_price", "price", "amount"],
    "CustomerID": ["CustomerID", "customer_id", "customerID", "buyer_id"],
    "Country": ["Country", "country", "region", "location"],
}


def resolve_columns(df_columns: list[str]) -> dict[str, str]:
    """将实际列名映射到标准列名。

    Returns:
        {标准列名: 实际列名} 的映射
    """
    mapping: dict[str, str] = {}
    actual_lower = {c.lower(): c for c in df_columns}

    for std_name, aliases in COLUMN_ALIASES.items():
        found = False
        for alias in aliases:
            if alias in df_columns:
                mapping[std_name] = alias
                found = True
                break
            if alias.lower() in actual_lower:
                mapping[std_name] = actual_lower[alias.lower()]
                found = True
                break
        if not found:
            mapping[std_name] = None  # type: ignore[assignment]

    return mapping


def enforce_schema(data: dict[str, Any], required_fields: list[str]) -> dict[str, Any]:
    """检查字典中是否存在必需字段，缺失则报清晰错误。"""
    missing = [f for f in required_fields if f not in data]
    if missing:
        available = ", ".join(sorted(data.keys()))
        raise KeyError(
            f"缺少必需字段: {missing}。可用字段: [{available}]"
        )
    return data


# ============================================================
# 2. 类型断言
# ============================================================

def _type_name(t: type | tuple) -> str:
    """获取类型的可读名称，支持 tuple 如 (int, float)。"""
    if isinstance(t, tuple):
        return " | ".join(x.__name__ for x in t)
    return t.__name__


def assert_types(data: dict[str, Any], type_map: dict[str, type | tuple]) -> None:
    """检查字段类型，不匹配则报清晰错误。"""
    errors = []
    for field, expected_type in type_map.items():
        if field not in data:
            continue  # 缺失由 enforce_schema 处理
        val = data[field]
        if not isinstance(val, expected_type):
            errors.append(
                f"字段 '{field}' 期望 {_type_name(expected_type)}，"
                f"实际是 {type(val).__name__}（值={repr(val)[:50]}）"
            )
    if errors:
        raise TypeError("类型校验失败:\n  " + "\n  ".join(errors))


# ============================================================
# 3. 健壮的数据加载器
# ============================================================

def safe_load(record: dict[str, Any]) -> dict[str, Any]:
    """安全加载一条记录：先映射列名，再校验字段，再校验类型。"""
    # Step 1: 列名映射
    mapped = {}
    mapping = resolve_columns(list(record.keys()))
    for std_name, actual_name in mapping.items():
        if actual_name is not None:
            mapped[std_name] = record[actual_name]

    _log(f"列名映射完成: {list(mapping.values())} → {list(mapping.keys())}")

    # Step 2: 必需字段检查
    required = ["InvoiceNo", "Quantity", "UnitPrice", "CustomerID"]
    enforce_schema(mapped, required)
    _log(f"必需字段检查通过: {required}")

    # Step 3: 类型断言
    assert_types(mapped, {
        "InvoiceNo": str,
        "Quantity": (int, float),
        "UnitPrice": (int, float),
        "CustomerID": (int, float, str),
    })
    _log("类型断言通过")

    return mapped


# ============================================================
# Demo
# ============================================================

def run_demo() -> None:
    print("=" * 60)
    print("Demo 3: Schema防护")
    print("=" * 60)

    # ---- Case 1: 正常数据 ----
    print("\n--- Case 1: 正常数据（标准列名）---")
    good_record = {
        "InvoiceNo": "536365",
        "StockCode": "85123A",
        "Description": "WHITE HANGING HEART T-LIGHT HOLDER",
        "Quantity": 6,
        "InvoiceDate": "2010-12-01 08:26:00",
        "UnitPrice": 2.55,
        "CustomerID": 17850.0,
        "Country": "United Kingdom",
    }
    try:
        result = safe_load(good_record)
        print(f"  [OK] {result}")
    except (KeyError, TypeError) as e:
        print(f"  [FAIL] {e}")

    # ---- Case 2: 列名不同（来自另一个数据源）----
    print("\n--- Case 2: 列名变了（别名兼容）---")
    aliased_record = {
        "order_id": "536366",
        "product_code": "22633",
        "item_name": "HAND WARMER UNION JACK",
        "qty": 6,
        "order_date": "2010-12-01 08:28:00",
        "price": 1.85,
        "buyer_id": 17850,
        "region": "United Kingdom",
    }
    try:
        result = safe_load(aliased_record)
        print(f"  [OK] {result}")
    except (KeyError, TypeError) as e:
        print(f"  [FAIL] {e}")

    # ---- Case 3: 缺少必需字段 ----
    print("\n--- Case 3: 缺少字段（CustomerID缺失）---")
    bad_record = {
        "InvoiceNo": "536367",
        "Quantity": 3,
        "UnitPrice": 5.99,
        # CustomerID 缺失！
    }
    try:
        result = safe_load(bad_record)
        print(f"  [OK] {result}")
    except KeyError as e:
        print(f"  [清晰错误] {e}")
    except TypeError as e:
        print(f"  [清晰错误] {e}")

    # ---- Case 4: 字段类型变了（字符串变成数字）----
    print("\n--- Case 4: 类型变化（InvoiceNo变成数字）---")
    type_changed = {
        "InvoiceNo": 536368,       # 原来是str，现在是int
        "Quantity": "七",           # 原来是int，现在是中文
        "UnitPrice": "free",       # 原来是float，现在是str
        "CustomerID": 17851,
    }
    try:
        result = safe_load(type_changed)
        print(f"  [OK] {result}")
    except (KeyError, TypeError) as e:
        print(f"  [清晰错误] {e}")

    # ---- Case 5: 全是陌生列名 ----
    print("\n--- Case 5: 完全陌生的列名（无法映射）---")
    unknown_record = {
        "col_a": 1,
        "col_b": 2,
        "col_c": 3,
    }
    try:
        result = safe_load(unknown_record)
        print(f"  [OK] {result}")
    except (KeyError, TypeError) as e:
        print(f"  [清晰错误] {e}")


if __name__ == "__main__":
    run_demo()

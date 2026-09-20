# -*- coding: utf-8 -*-
"""data_doctor · 任意CSV一键体检（可复用工具）

函数式API：
    from doctor import full_check
    full_check("data.csv")   # 画像+质量+异常+建议+健康分

设计原则（对应41课三护栏）：
  检测 → 处理建议（不自动改数据）→ 留痕。数分的活，工具只诊断不越权。
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

CHUNK = 200_000  # 大文件分块读取阈值


def _load(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    if p.stat().st_size > CHUNK * 500:  # >100MB 走分块
        rows = []
        for ch in pd.read_csv(p, chunksize=CHUNK):
            rows.append(ch)
        return pd.concat(rows, ignore_index=True)
    return pd.read_csv(p)


def profile(path: str | Path) -> dict:
    """数据画像：行列/内存/每列类型、缺失率、唯一值数。"""
    df = _load(path)
    cols = {}
    for c in df.columns:
        s = df[c]
        cols[c] = {
            "dtype": str(s.dtype),
            "缺失率%": round(s.isna().mean() * 100, 2),
            "唯一值": int(s.nunique(dropna=True)),
        }
    return {"ok": True, "data": {
        "行数": len(df), "列数": df.shape[1],
        "内存MB": round(df.memory_usage(deep=True).sum() / 1e6, 1),
        "列": cols,
    }}


def quality_report(path: str | Path) -> dict:
    """质量报告：缺失TOP/疑似ID列/常数列/高基数/疑似重复行/混合类型。"""
    df = _load(path)
    issues = []
    miss = df.isna().mean().sort_values(ascending=False)
    for c in miss.index[miss > 0.3]:
        issues.append(f"列 `{c}` 缺失率 {miss[c]*100:.1f}% (>30%需重点关注)")
    id_like = [c for c in df.columns if df[c].nunique() == len(df) and df[c].dtype == object]
    if id_like:
        issues.append(f"疑似ID列（全唯一）: {id_like}，勿用于分组聚合")
    const = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    if const:
        issues.append(f"常数列（无信息量，可删）: {const}")
    hi_card = [c for c in df.select_dtypes('object').columns
               if 0 < df[c].nunique() < len(df) * 0.02]
    dup = int(df.duplicated().sum())
    if dup:
        issues.append(f"完全重复行 {dup} 行")
    return {"ok": True, "data": {"issues": issues, "重复行": dup}}


def outliers(path: str | Path, col: str, method: str = "iqr") -> dict:
    """单列异常检测：iqr（偏态稳健）或 zscore（近正态）。50课口径。"""
    df = _load(path)
    if col not in df.columns:
        return {"ok": False, "error": f"列不存在: {col}，可用: {list(df.columns)[:20]}"}
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if method == "iqr":
        q1, q3 = s.quantile([.25, .75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    else:
        lo, hi = s.mean() - 3 * s.std(), s.mean() + 3 * s.std()
    bad = s[(s < lo) | (s > hi)]
    return {"ok": True, "data": {
        "列": col, "方法": method, "下界": round(lo, 2), "上界": round(hi, 2),
        "异常数": int(len(bad)), "异常占比%": round(len(bad) / len(s) * 100, 2),
        "越界样本": [round(v, 2) for v in bad.head(5)],
    }}


def suggest_clean(path: str | Path) -> dict:
    """清洗建议：只建议不执行（诊断不越权）。"""
    df = _load(path)
    sug = []
    for c in df.columns:
        s = df[c]
        if s.isna().mean() > 0.5:
            sug.append(f"`{c}` 缺失过半 → 与业务确认是否该列失效，别急着删/填")
        elif s.isna().any() and pd.api.types.is_numeric_dtype(s):
            sug.append(f"`{c}` 数值列有缺失 → 先查缺失机制（随机?系统性?），再定填中位/均值/标记")
    num = df.select_dtypes("number")
    for c in num.columns:
        if (num[c] <= 0).any() and "价" in c or "price" in c.lower():
            sug.append(f"`{c}` 含非正值 → 查业务含义（退货/赠品/错误），不能默默删")
    dup = int(df.duplicated().sum())
    if dup:
        sug.append(f"重复行 {dup} → 查是否真重复（同key不同批次?），再决定去重")
    return {"ok": True, "data": {"建议数": len(sug), "建议": sug}}


def full_check(path: str | Path) -> dict:
    """一键全检：画像+质量+建议+总体健康分。"""
    p = profile(path)["data"]
    q = quality_report(path)["data"]
    s = suggest_clean(path)["data"]
    # 健康分：满分100，问题扣分
    score = 100
    for i in q["issues"]:
        if "缺失率" in i: score -= 15
        elif "重复行" in i: score -= 10
        elif "常数列" in i: score -= 5
    score = max(0, score)
    return {"ok": True, "data": {
        "画像": p, "质量问题": q, "清洗建议": s, "健康分": score,
    }}


def _fmt(r: dict) -> str:
    import json
    return json.dumps(r, ensure_ascii=False, indent=1, default=str)

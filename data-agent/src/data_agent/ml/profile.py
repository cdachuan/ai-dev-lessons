# -*- coding: utf-8 -*-
"""数据质量画像：给 profile 卡加质量层——缺失率/异常值/疑似脏列。

真实数据接入时，第一眼照亮脏的地方，不等训练完才发现。
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

from data_agent.dictionary import dataset_file, get_dataset_entry
from data_agent.jsonable import _to_jsonable


def profile_quality(dataset: str, dict_file: str = "dictionary.yaml") -> dict:
    """质量画像：每列缺失率、数值列异常值(IQR)、类别列可疑值。"""
    from data_agent.dictionary import get_root
    ROOT = get_root()
    import yaml
    with open(ROOT / dict_file, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    entry = d[dataset]
    df = pd.read_csv(ROOT / entry["file"])

    report = {"dataset": dataset, "n_rows": int(len(df)), "columns": {}, "suspects": []}

    for c in df.columns:
        col_info = {
            "missing_pct": round(float(df[c].isna().mean()) * 100, 2),
        }
        if pd.api.types.is_numeric_dtype(df[c]):
            s = df[c].dropna()
            if len(s):
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                iqr = q3 - q1
                lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outliers = int(((s < lo) | (s > hi)).sum())
                col_info["outliers_iqr"] = outliers
                col_info["outlier_pct"] = round(outliers / len(s) * 100, 2)
                col_info["min"] = float(s.min())
                col_info["max"] = float(s.max())
                if outliers / max(len(s), 1) > 0.1:
                    report["suspects"].append(f"数值列 '{c}' 异常值占比 {col_info['outlier_pct']}% (>10%)")
        else:
            vc = df[c].value_counts()
            col_info["nunique"] = int(len(vc))
            # 类别列疑似脏：超多唯一值 / 混合大小写疑似同义
            if 2 < len(vc) <= 50:
                lowers = {str(v).strip().lower() for v in vc.index}
                if len(lowers) < len(vc):
                    report["suspects"].append(f"类别列 '{c}' 存在仅大小写/空格不同的值，疑似同义脏数据")
            if len(vc) > len(df) * 0.9 and c not in entry.get("columns", {}):
                report["suspects"].append(f"列 '{c}' 唯一值接近行数，疑似 ID 列却没在字典标注主键")
        report["columns"][c] = col_info

    if entry.get("target") and entry["target"] in df.columns:
        report["target_balance"] = _to_jsonable(df[entry["target"]].value_counts().to_dict())

    return _to_jsonable(report)

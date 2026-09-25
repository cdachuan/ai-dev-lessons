# -*- coding: utf-8 -*-
"""ML 核验层：不信任 AI 代码报的指标，从预测落盘文件独立复算。

铁律2的 ML 版：
- 双路径复算指标 → 抓执行层错误（代码写错/算错）
- 泄漏检查 → 抓目标列进特征（概念层最常见的自欺）
- 边界：口径对不对（任务定义/特征选择合理性）仍归人
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

from data_agent.dictionary import load_dictionary

from data_agent.project import get_project_root

# 让 dictionary.py 支持多字典文件：这里手动合并读
def load_ml_dictionary() -> dict:
    import yaml
    with open(ROOT / "dictionary_ml.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def verify_ml_run(pred_path: str, dataset: str, feature_cols: list) -> dict:
    """从预测文件独立复算指标 + 泄漏检查。这是核验卡口。"""
    result = {"pass": True, "checks": {}, "metrics": {}}

    # --- 1. 泄漏检查：目标列/主键不得出现在特征里 ---
    ml_dict = load_ml_dictionary()
    entry = ml_dict.get(dataset, {})
    target = entry.get("target")
    leaks = []
    if target and target in feature_cols:
        leaks.append(f"目标列 '{target}' 出现在特征矩阵——这是自欺指标，报告作废")
    id_cols = [c for c, meta in entry.get("columns", {}).items()
               if "主键" in str(meta.get("desc", ""))]
    for c in id_cols:
        if c in feature_cols:
            leaks.append(f"主键列 '{c}' 作特征——过拟合噪音，剔除")
    result["checks"]["leakage"] = {"pass": not leaks, "problems": leaks}
    if leaks:
        result["pass"] = False

    # --- 2. 预测文件完整性 ---
    pred_file = Path(pred_path)
    if not pred_file.exists():
        result["pass"] = False
        result["checks"]["pred_file"] = {"pass": False, "problems": ["预测文件不存在"]}
        return result
    df = pd.read_csv(pred_file)
    if not {"y_true", "y_pred"}.issubset(df.columns):
        result["pass"] = False
        result["checks"]["pred_file"] = {"pass": False, "problems": [f"预测文件缺列，现有: {list(df.columns)}"]}
        return result
    result["checks"]["pred_file"] = {"pass": True, "n": int(len(df))}

    # --- 3. 独立复算指标（sklearn 路径 + 手写公式路径 双路径） ---
    y_true = df["y_true"].values
    y_pred = df["y_pred"].values

    # 路径A：sklearn
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    metrics_a = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }

    # 路径B：手写公式
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    metrics_b = {
        "accuracy": (tp + tn) / len(y_true) if len(y_true) else 0.0,
        "precision": tp / (tp + fp) if (tp + fp) else 0.0,
        "recall": tp / (tp + fn) if (tp + fn) else 0.0,
        "f1": (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else 0.0,
    }

    mismatches = {k: {"sklearn": round(v, 6), "manual": round(metrics_b[k], 6)}
                  for k in metrics_a
                  if abs(metrics_a[k] - metrics_b[k]) > 0.005}
    result["metrics"] = {**metrics_a, "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn}}
    result["checks"]["dual_path"] = {"pass": not mismatches, "mismatches": mismatches}
    if mismatches:
        result["pass"] = False

    # --- 4. 类别塌缩检查：预测全是同一类 = 模型没学到东西，提醒而非拦截 ---
    unique_pred = np.unique(y_pred)
    result["checks"]["collapsed"] = {
        "pass": len(unique_pred) > 1,
        "detail": "预测只输出单一类别，模型退化" if len(unique_pred) <= 1 else f"预测类别: {unique_pred.tolist()}",
    }

    return result

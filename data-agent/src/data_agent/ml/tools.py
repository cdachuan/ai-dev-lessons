# -*- coding: utf-8 -*-
"""ML 工具层：注册给 agent 的三个工具。

- run_experiment: AI 写 sklearn 代码 → 白名单子进程跑 → 核验
- plot_diagnostics: 固定模板出图（不 let AI 自由发挥）
- ml 指标对照已知答案（验收考题）
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

from data_agent.ml.runner import run_ml_code, check_imports
from data_agent.ml.verifier import verify_ml_run, load_ml_dictionary
from data_agent.jsonable import _to_jsonable

from data_agent.dictionary import get_root as _get_root
from data_agent.project import get_project_root

def _plots_dir() -> Path:
    """plots 目录：运行时按项目根解析。"""
    return get_project_root() / "steps" / "plots"

RUN_PROMPT_RULES = """写 sklearn 实验代码时必须遵守：
1. 变量名固定：特征矩阵 X，目标 y，测试集真实值 y_test，预测值 y_pred
2. 代码最后必须调用: emit(y_test, y_pred, {"feature_cols": [...], "model_name": "...", "params": {...}})
3. 只允许 import: pandas, numpy, sklearn（plotly 图另用工具出，代码里不用画图）
4. 特征列不含目标列、不含主键列
5. 分类任务用 train_test_split(random_state=42, stratify=y)，回归任务不用 stratify
6. 类别列用 pd.get_dummies 编码
7. 数据加载：pd.read_csv("data/ml_orders.csv") —— 子进程工作目录就是项目根，数据永远在 data/ 下，禁止 import os/glob 探测路径
8. 预测必须覆盖整个测试集（几百行量级），emit 的 extra 里 model_name 写真实模型名"""


def run_experiment(code: str, dataset: str) -> dict:
    """跑一轮 ML 实验：白名单执行 → 独立核验。指标未过核验一律标记不可信。"""
    import sys
    sys.path.insert(0, str(ROOT))
    exec_result = run_ml_code(code, run_tag=f"exp_{pd.Timestamp.now().strftime('%H%M%S%f')[:-3]}")
    if not exec_result.get("ok"):
        return _to_jsonable({"ok": False, "stage": "execute", "error": exec_result.get("error")})

    # 从 extra 里拿 feature_cols 做泄漏检查
    feature_cols = []
    if exec_result.get("extra_path"):
        with open(exec_result["extra_path"], encoding="utf-8") as f:
            extra = json.load(f)
        feature_cols = extra.get("feature_cols", [])

    verdict = verify_ml_run(exec_result["pred_path"], dataset, feature_cols)
    return _to_jsonable({
        "ok": True,
        "verified_pass": verdict["pass"],
        "metrics": verdict["metrics"],
        "checks": verdict["checks"],
        "pred_path": exec_result["pred_path"],
        "note": "指标为核验层独立复算值。verified_pass=false 时不得作为结论。" if verdict["pass"]
                else "核验未过：存在泄漏或指标不一致，必须修复后重跑，不得采信当前指标。",
    })


def plot_diagnostics(pred_path: str, dataset: str, plots: list) -> dict:
    """固定模板出图。plots 从混淆矩阵/类别分布里选。返回图片路径列表。"""
    out = {}
    pred_file = Path(pred_path)
    if not pred_file.exists():
        return {"error": f"预测文件不存在: {pred_path}"}
    df = pd.read_csv(pred_file)
    tag = pred_file.stem.replace("_pred", "")

    if "confusion" in plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        y_true, y_pred = df["y_true"].values, df["y_pred"].values
        cm = np.zeros((2, 2), int)
        for t, p in zip(y_true, y_pred):
            cm[int(t), int(p)] += 1
        fig, ax = plt.subplots(figsize=(4, 3.5))
        ax.imshow(cm, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=14)
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        ax.set_xticklabels(["pred=0", "pred=1"]); ax.set_yticklabels(["true=0", "true=1"])
        ax.set_title("Confusion Matrix")
        p = _plots_dir() / f"{tag}_confusion.png"
        fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)
        out["confusion"] = str(p)

    if "pred_dist" in plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(4, 3))
        vc = df["y_pred"].value_counts().sort_index()
        ax.bar(vc.index.astype(str), vc.values, color=["#4C72B0", "#DD8452"])
        ax.set_title("Prediction Distribution")
        p = _plots_dir() / f"{tag}_pred_dist.png"
        fig.tight_layout(); fig.savefig(p, dpi=110); plt.close(fig)
        out["pred_dist"] = str(p)

    return _to_jsonable({"plots": out, "note": "图由固定模板生成，数字可核验，非 AI 自由绘制。"})


TOOL_SCHEMAS_ML = [
    {
        "type": "function",
        "function": {
            "name": "run_experiment",
            "description": "跑一轮 ML 实验Risk。你写完整的 sklearn 实验代码（遵守变量名约定：X/y/y_test/y_pred，最后调用 emit(y_test,y_pred,extra)），本工具在白名单子进程执行并独立核验指标。核验未过必须修复重跑。规则：\n" + RUN_PROMPT_RULES,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "完整 sklearn 实验代码"},
                    "dataset": {"type": "string", "description": "数据集名，须在 dictionary_ml.yaml 注册"},
                },
                "required": ["code", "dataset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_diagnostics",
            "description": "出诊断图（固定模板）。跑完实验后若指标可疑（如召回极低/类别塌缩）或用户要看图，用这个。plots 可选: confusion, pred_dist",
            "parameters": {
                "type": "object",
                "properties": {
                    "pred_path": {"type": "string"},
                    "dataset": {"type": "string"},
                    "plots": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["pred_path", "dataset", "plots"],
            },
        },
    },
]

ML_TOOL_REGISTRY = {
    "run_experiment": run_experiment,
    "plot_diagnostics": plot_diagnostics,
}

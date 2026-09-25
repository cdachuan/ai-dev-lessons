# -*- coding: utf-8 -*-
"""子进程执行器：AI 写 sklearn 代码，白名单 + 超时 + 预测结果落盘约定。

约定（AI 生成代码必须遵守，写进 prompt）：
- 特征矩阵 X / 目标 y / 拆分后 y_test, y_pred 必须用固定变量名
- 代码结束时调用 emit(y_test, y_pred, metrics_dict) —— 执行器注入此函数
- 指标由核验层独立复算，代码里的 metrics 仅作对照
"""
import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path

from data_agent.dictionary import get_root as _get_root
from data_agent.project import get_project_root

def _runs_dir() -> Path:
    """ml_runs 目录：运行时按项目根解析。"""
    return get_project_root() / "steps" / "ml_runs"

# 白名单：只能 import 这些顶层模块
WHITELIST = {"pandas", "numpy", "sklearn", "plotly"}

PRELUDE = '''
import json as _json

def emit(y_test, y_pred, extra=None):
    """把预测结果写盘，核验层从这里独立复算。"""
    import pandas as pd
    pd.DataFrame({"y_true": list(y_test), "y_pred": list(y_pred)}).to_csv(
        __PRED_PATH__, index=False)
    if extra:
        with open(__EXTRA_PATH__, "w", encoding="utf-8") as f:
            _json.dump(extra, f, ensure_ascii=False, default=str)
'''


def check_imports(code: str) -> list:
    """静态 AST 检查 import 白名单。违规直接拒绝执行。"""
    import ast
    bad = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                if top not in WHITELIST and top not in {"json"}:
                    bad.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top and top not in WHITELIST and top not in {"json"}:
                bad.append(node.module)
    return bad


def run_ml_code(code: str, run_tag: str = None, timeout: int = 120) -> dict:
    """在子进程跑 AI 生成的 ML 代码。返回 {pred_path, extra, stdout, ok}。"""
    run_tag = run_tag or f"run_{os.getpid()}_{len(list(_runs_dir().glob('*')))}"
    pred_path = _runs_dir() / f"{run_tag}_pred.csv"
    extra_path = _runs_dir() / f"{run_tag}_extra.json"

    bad = check_imports(code)
    if bad:
        return {"ok": False, "error": f"import 白名单违规: {bad}。只允许 {sorted(WHITELIST)}"}

    full_code = (PRELUDE
                 .replace("__PRED_PATH__", repr(str(pred_path)))
                 .replace("__EXTRA_PATH__", repr(str(extra_path)))
                 + "\n" + code)

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8", dir=str(_runs_dir())) as f:
        f.write(full_code)
        script = f.name

    try:
        proc = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"执行超时（>{timeout}s），检查是否有死循环/大数据全量拟合"}
    finally:
        try:
            os.unlink(script)
        except OSError:
            pass

    if rc != 0:
        tail = (stderr or "")[-1500:]
        return {"ok": False, "error": f"执行失败 rc={rc}\n{tail}", "stdout": stdout[-500:]}

    if not pred_path.exists():
        return {"ok": False, "error": "代码没有调用 emit(y_test, y_pred)——预测结果未落盘，无法核验，拒绝采信。"}

    # 最小规模检查：预测样本数过少 = 不是真实实验（探测/玩具输出），拒绝采信
    import csv
    with open(pred_path, encoding="utf-8") as f:
        n_rows = sum(1 for _ in f) - 1
    if n_rows < 20:
        return {"ok": False, "error": f"预测样本仅 {n_rows} 行（<20）——这不是真实实验产出（可能是路径探测或玩具数据），拒绝采信。数据文件用相对路径 data/<数据集>.csv 加载，工作目录已是项目根。"}

    return {
        "ok": True,
        "pred_path": str(pred_path),
        "extra_path": str(extra_path) if extra_path.exists() else None,
        "stdout": stdout[-2000:],
    }

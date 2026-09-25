# -*- coding: utf-8 -*-
"""报告生成器：把 steps/ml_runs 的实验链编译成 md 报告，pandoc 一键转 docx。

报告数字全部有出处（预测落盘文件+核验层复算），不采信 AI 口头报数。
"""
import json
import time
from pathlib import Path

from data_agent.ml.verifier import verify_ml_run

from data_agent.project import get_project_root

def _reports_dir() -> Path:
    """reports 目录：运行时按项目根解析。"""
    return get_project_root() / "reports"


def generate_report(dataset: str, title: str, question: str, decisions: list = None, pred_paths: list = None) -> dict:
    """编译报告。pred_paths 缺省取 steps/ml_runs 下最新 N 个 *_pred.csv。"""
    runs_dir = ROOT / "steps" / "ml_runs"
    if not pred_paths:
        pred_paths = sorted(runs_dir.glob("*_pred.csv"), key=lambda p: p.stat().st_mtime)[-5:]
    if not pred_paths:
        return {"error": "没有实验产出（steps/ml_runs 下无 *_pred.csv），先跑实验再出报告"}

    lines = [
        f"---\ntitle: \"{title}\"\ndate: {time.strftime('%Y-%m-%d %H:%M')}\n---",
        f"# {title}",
        f"\n## 分析问题\n\n{question}",
        "\n## 口径声明\n",
        f"- 数据集：`{dataset}`（dictionary_ml.yaml 定义，目标列/口径以字典为准）",
        "- 指标均为核验层独立复算（sklearn 与手写公式双路径一致），非模型口头报数",
        "- 特征矩阵不含目标列与主键列（核验层泄漏检查通过后才可采信）",
    ]

    if decisions:
        lines.append("\n## 策略决策链\n")
        for d in decisions:
            lines.append(f"- {d}")

    lines.append("\n## 实验记录\n")
    lines.append("| 实验 | 模型 | accuracy | precision | recall | f1 | 核验 |")
    lines.append("|---|---|---|---|---|---|---|")

    for i, pp in enumerate(pred_paths, 1):
        extra_file = Path(str(pp).replace("_pred.csv", "_extra.json"))
        model_name, params = "未知", ""
        if extra_file.exists():
            with open(extra_file, encoding="utf-8") as f:
                extra = json.load(f)
            model_name = extra.get("model_name", "未知")
            params = json.dumps(extra.get("params", {}), ensure_ascii=False)
            feature_note = f"特征数 {len(extra.get('feature_cols', []))}"
        else:
            feature_note = "-"
        v = verify_ml_run(str(pp), dataset, [])
        m = v["metrics"]
        flag = "✅" if v["pass"] else "❌未过核验"
        lines.append(f"| #{i} {feature_note} | {model_name} {params} | {m['accuracy']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {flag} |")

    # 图引用
    plots = sorted((ROOT / "steps" / "plots").glob("*.png"), key=lambda p: p.stat().st_mtime)
    if plots:
        lines.append("\n## 诊断图（固定模板生成）\n")
        for p in plots[-4:]:
            rel = Path("..") / p.relative_to(_reports_dir().parent)
            lines.append(f"![{p.stem}]({rel.as_posix()})\n")

    lines += [
        "\n## 边界与免责\n",
        "- 核验保证执行自洽（指标复算一致、无泄漏、无塌缩），不保证业务口径正确",
        "- 已知答案对照（mock 阶段）：金额>500 增险、数码最高、家居最低——若挖出的规律与此矛盾，优先怀疑流程而非规律本身",
    ]

    md_path = _reports_dir() / f"report_{time.strftime('%Y%m%d_%H%M%S')}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"md": str(md_path), "n_experiments": len(pred_paths)}


def to_docx(md_path: str) -> dict:
    """pandoc 转 docx。pandoc 不在则报错提示。"""
    import subprocess, shutil, os
    md = Path(md_path)
    out = md.with_suffix(".docx")
    pandoc = shutil.which("pandoc")
    if not pandoc:
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/pandoc/pandoc-3.6.3/pandoc.exe"
        pandoc = str(local) if local.exists() else None
    if not pandoc:
        return {"error": "pandoc 未安装——winget install JohnMacFarlane.Pandoc 或 choco install pandoc 后重试"}
    try:
        r = subprocess.run([pandoc, str(md), "-o", str(out),
                            "--resource-path", str(_reports_dir().parent)],
                           capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    except FileNotFoundError:
        return {"error": "pandoc 未安装——winget install JohnMacFarlane.Pandoc 或 choco install pandoc 后重试"}
    if r.returncode != 0:
        return {"error": f"pandoc 失败: {r.stderr[:300]}"}
    return {"docx": str(out)}

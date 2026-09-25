# -*- coding: utf-8 -*-
"""CLI 入口：da init/use/ask/serve/datasets/board。

项目制运行时：所有状态（dictionary/黑板/资产库/sessions/steps/reports）按项目根解析。
"""
import argparse
import os
import sys
import shutil
import pandas as pd
import yaml
from pathlib import Path

from data_agent.project import get_project_root, set_current_project


def _ensure_project_dirs(root: Path) -> None:
    """生成项目骨架目录。"""
    for d in ("data", "sessions", "steps", "reports", "library/pending", "library/approved"):
        (root / d).mkdir(parents=True, exist_ok=True)


def _profile_csv(path: Path) -> dict:
    """对 CSV 做简单画像，返回列名、类型、描述占位。"""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, nrows=5)
    else:
        df = pd.read_excel(path, nrows=5)
    cols = {}
    for c in df.columns:
        dtype = str(df[c].dtype)
        cols[c] = {
            "desc": "TODO：填写列描述",
            "type": "number" if "int" in dtype or "float" in dtype else "string",
        }
        if df[c].dtype == "object" and df[c].nunique() <= 10:
            vals = df[c].dropna().unique().tolist()
            cols[c]["valid_values"] = [str(v) for v in vals]
    return cols


def _merge_dictionaries(root: Path, target_name: str = "dictionary.yaml") -> dict:
    """合并所有 dictionary*.yaml 为单一字典。"""
    merged = {}
    for f in root.glob("dictionary*.yaml"):
        with open(f, encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        for k, v in d.items():
            v["_dict_file"] = f.name
            merged[k] = v
    return merged


def cmd_init(args):
    """da init <项目目录>：生成项目骨架，引导式导入 CSV。"""
    root = Path(args.project_dir).resolve()
    if root.exists() and any(root.iterdir()) and not args.force:
        print(f"错误：目录 {root} 已存在且非空，使用 --force 覆盖")
        sys.exit(1)
    _ensure_project_dirs(root)
    print(f"✅ 项目骨架已生成: {root}")

    # 生成空 blackboard.md
    bb = root / "blackboard.md"
    if not bb.exists():
        bb.write_text(
            "# 黑板 · 项目决策留痕\n\n"
            "> Agent 只写「待确认」；人确认改「已定」。\n\n",
            encoding="utf-8",
        )

    # 导入 CSV
    csv_files = args.csv_files or []
    if not csv_files:
        print("提示：未指定 CSV 文件，可用 da init <目录> file1.csv file2.csv 导入")
    else:
        merged_dict = {}
        for csv_path in csv_files:
            src = Path(csv_path).resolve()
            if not src.exists():
                print(f"⚠️  文件不存在，跳过: {src}")
                continue
            dst = root / "data" / src.name
            shutil.copy2(src, dst)
            print(f"  已拷贝: {src.name} -> data/")
            # 画像
            cols = _profile_csv(dst)
            ds_name = src.stem  # 用文件名作数据集名
            merged_dict[ds_name] = {
                "file": f"data/{src.name}",
                "desc": "TODO：填写数据集描述",
                "columns": cols,
            }
        # 写 dictionary.yaml
        dict_path = root / "dictionary.yaml"
        with open(dict_path, "w", encoding="utf-8") as f:
            f.write("# 数据字典（口径权威源）\n\n")
            yaml.dump(merged_dict, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"✅ 已生成 dictionary.yaml，包含 {len(merged_dict)} 个数据集")

    # 设置为当前项目
    set_current_project(root)
    print(f"✅ 当前项目已设为: {root}")


def cmd_use(args):
    """da use <项目目录>：设置当前项目指针。"""
    root = Path(args.project_dir).resolve()
    if not root.exists():
        print(f"错误：项目目录不存在: {root}")
        sys.exit(1)
    set_current_project(root)
    print(f"✅ 当前项目已设为: {root}")


def cmd_ask(args):
    """da ask "问题" [--project 路径] [--mode analyst|bi]"""
    from data_agent import DataAgent
    try:
        project_root = get_project_root(args.project)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    # 临时设置环境变量，确保子模块读对项目根
    os.environ["DATA_AGENT_ROOT"] = str(project_root)

    mode = args.mode or "analyst"
    dataset = args.dataset or "dash_orders"
    agent = DataAgent(mode=mode, dataset=dataset)
    result = agent.ask(args.question)
    print(result.get("reply", "（无回复）"))


def cmd_serve(args):
    """da serve [--project 路径] [--port 8000]"""
    try:
        project_root = get_project_root(args.project)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    os.environ["DATA_AGENT_ROOT"] = str(project_root)
    port = args.port or 8000
    print(f"启动 API 服务，项目根: {project_root}，端口: {port}")

    import uvicorn
    # api/ 在仓库不在包内：把仓库根加进 sys.path 后直接传 app 对象（reload 需要字符串，故关掉）
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    from api.server import app
    uvicorn.run(app, host="0.0.0.0", port=port)


def cmd_datasets(args):
    """da datasets：列出当前项目数据集。"""
    try:
        project_root = get_project_root(args.project)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    from data_agent.dictionary import load_dictionary
    os.environ["DATA_AGENT_ROOT"] = str(project_root)
    dicts = load_dictionary(force_reload=True)
    if not dicts:
        print("（项目中无数据集）")
        return
    print(f"数据集列表（项目: {project_root.name}）：")
    for name, entry in dicts.items():
        desc = entry.get("desc", "")
        cols = list(entry.get("columns", {}).keys())
        print(f"  - {name}: {desc}")
        print(f"    列: {', '.join(cols)}")


def cmd_board(args):
    """da board：打印当前项目黑板。"""
    try:
        project_root = get_project_root(args.project)
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    bb = project_root / "blackboard.md"
    if not bb.exists():
        print("黑板为空")
        return
    print(bb.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(
        prog="da",
        description="data-agent CLI：项目制数据分析工具",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # init
    p_init = sub.add_parser("init", help="初始化项目骨架")
    p_init.add_argument("project_dir", help="项目目录路径")
    p_init.add_argument("csv_files", nargs="*", help="要导入的 CSV 文件")
    p_init.add_argument("--force", action="store_true", help="覆盖已有目录")
    p_init.set_defaults(func=cmd_init)

    # use
    p_use = sub.add_parser("use", help="设置当前项目")
    p_use.add_argument("project_dir", help="项目目录路径")
    p_use.set_defaults(func=cmd_use)

    # ask
    p_ask = sub.add_parser("ask", help="向数据分析 Agent 提问")
    p_ask.add_argument("question", help="问题文本")
    p_ask.add_argument("--project", "-p", help="项目目录（可选，覆盖当前项目）")
    p_ask.add_argument("--mode", "-m", choices=["analyst", "bi"], default="analyst", help="模式")
    p_ask.add_argument("--dataset", "-d", help="数据集名称（bi 模式用）")
    p_ask.set_defaults(func=cmd_ask)

    # serve
    p_serve = sub.add_parser("serve", help="启动 API 服务")
    p_serve.add_argument("--project", "-p", help="项目目录（可选）")
    p_serve.add_argument("--port", type=int, default=8000, help="端口号")
    p_serve.set_defaults(func=cmd_serve)

    # datasets
    p_ds = sub.add_parser("datasets", help="列出当前项目数据集")
    p_ds.add_argument("--project", "-p", help="项目目录（可选）")
    p_ds.set_defaults(func=cmd_datasets)

    # board
    p_bb = sub.add_parser("board", help="打印当前项目黑板")
    p_bb.add_argument("--project", "-p", help="项目目录（可选）")
    p_bb.set_defaults(func=cmd_board)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()

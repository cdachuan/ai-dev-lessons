# -*- coding: utf-8 -*-
"""治理层：黑板（决策留痕）+ 审批门（提案→人审→入库）。

设计原则（0034 共识）：
- 黑板 = 项目级决策记录，每条挂 why，人可读可改（markdown 持久化）
- LLM 输出只是提案，跨审批门才成事实
- 入库资产带三件套：口径声明 / 参数定义 / 来源 step 路径
- 原数据物理只读，入库的都是衍生品
"""
import json
import time
from pathlib import Path

from data_agent.project import get_project_root

LIBRARY_DIR = "library"


def _library_root() -> Path:
    root = get_project_root() / LIBRARY_DIR
    (root / "pending").mkdir(parents=True, exist_ok=True)
    (root / "approved").mkdir(parents=True, exist_ok=True)
    return root


# ============================================================
# 黑板：结构化决策条目（决策 + why + 状态 + 关联）
# ============================================================

def bb_add(title: str, decision: str, why: str, related: list = None, status: str = "待确认", entry_id: str = None) -> dict:
    """写一条黑板条目。Agent 只能写「待确认」，人通过 bb_confirm 改状态。"""
    entry_id = entry_id or time.strftime("%Y%m%d_%H%M%S")
    entry = {
        "id": entry_id,
        "time": time.strftime("%Y-%m-%d %H:%M"),
        "status": status,          # 待确认 / 已定 / 已废弃
        "title": title,
        "decision": decision,      # 决策内容（确定性、可执行）
        "why": why,                # 决策理由——黑板区别于普通记忆的核心
        "related": related or [],  # 关联的 step/实验/资产路径
    }
    path = _library_root() / f"entry_{entry_id}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    _render_blackboard()
    return entry


def bb_confirm(entry_id: str, status: str = "已定") -> dict:
    """人操作：把条目置为已定/已废弃。"""
    path = _library_root() / f"entry_{entry_id}.json"
    entry = json.loads(path.read_text(encoding="utf-8"))
    entry["status"] = status
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    _render_blackboard()
    return entry


def bb_list(status: str = None) -> list:
    entries = []
    for p in sorted(_library_root().glob("entry_*.json")):
        e = json.loads(p.read_text(encoding="utf-8"))
        if status is None or e["status"] == status:
            entries.append(e)
    return entries


def _render_blackboard():
    """黑板 markdown 渲染：人可读可改的主界面。json 是真源，md 是视图。"""
    bb = get_project_root() / "blackboard.md"
    lines = ["# 黑板 · 项目决策留痕", "",
             "> Agent 只写「待确认」；人确认改「已定」。json 真源在 library/entry_*.json。", ""]
    for e in reversed(bb_list()):  # 新的在上
        icon = {"待确认": "🟡", "已定": "🟢", "已废弃": "⚫"}.get(e["status"], "·")
        lines.append(f"## {icon} {e['title']}  `{e['id']}`")
        lines.append(f"- **决策**：{e['decision']}")
        lines.append(f"- **why**：{e['why']}")
        if e["related"]:
            lines.append(f"- **关联**：{'、'.join(e['related'])}")
        lines.append(f"- *{e['time']} · {e['status']}*")
        lines.append("")
    bb.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# 审批门：提案 → 人审 → 入库（三件套）
# ============================================================

def propose_asset(name: str, kind: str, description: str,
                  caliber: str, params: dict, source_steps: list) -> dict:
    """Agent 侧：提交入库提案。只有过审批的资产才能进 approved/。

    三件套（0034 定稿）：
    - caliber: 口径声明——这个资产算的是什么、按什么口径
    - params: 参数定义——可复用的参数化接口
    - source_steps: 来源——哪些 step/实验产出的，可回溯
    """
    prop_id = time.strftime("%Y%m%d_%H%M%S")
    prop = {
        "id": prop_id,
        "name": name,
        "kind": kind,              # result_table / step_template / insight
        "description": description,
        "caliber": caliber,
        "params": params,
        "source_steps": source_steps,
        "status": "pending",
        "submitted": time.strftime("%Y-%m-%d %H:%M"),
    }
    path = _library_root() / "pending" / f"{prop_id}_{name}.json"
    path.write_text(json.dumps(prop, ensure_ascii=False, indent=1), encoding="utf-8")
    return prop


def list_pending() -> list:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((_library_root() / "pending").glob("*.json"))]


def approve(prop_id: str, name: str) -> dict:
    """人操作：批准入库。资产落到 approved/ 带三件套，从此快问可命中。"""
    src = _library_root() / "pending" / f"{prop_id}_{name}.json"
    if not src.exists():
        raise FileNotFoundError(f"提案不存在: {src}")
    prop = json.loads(src.read_text(encoding="utf-8"))
    prop["status"] = "approved"
    prop["approved_at"] = time.strftime("%Y-%m-%d %H:%M")
    dst = _library_root() / "approved" / f"{prop_id}_{name}.json"
    dst.write_text(json.dumps(prop, ensure_ascii=False, indent=1), encoding="utf-8")
    src.unlink()
    return prop


def reject(prop_id: str, name: str, reason: str = "") -> dict:
    """人操作：拒绝。提案标记废弃留档（不进 approved）。"""
    src = _library_root() / "pending" / f"{prop_id}_{name}.json"
    if not src.exists():
        raise FileNotFoundError(f"提案不存在: {src}")
    prop = json.loads(src.read_text(encoding="utf-8"))
    prop["status"] = "rejected"
    prop["reject_reason"] = reason
    rej_dir = _library_root() / "rejected"
    rej_dir.mkdir(parents=True, exist_ok=True)
    (rej_dir / f"{prop_id}_{name}.json").write_text(json.dumps(prop, ensure_ascii=False, indent=1), encoding="utf-8")
    src.unlink()
    return prop


def lookup_library(query: str) -> list:
    """快问短链的查找入口：在 approved 库里按关键词匹配资产。"""
    query_lower = query.lower()
    hits = []
    for p in (_library_root() / "approved").glob("*.json"):
        prop = json.loads(p.read_text(encoding="utf-8"))
        hay = " ".join([prop["name"], prop["description"], prop["caliber"],
                        " ".join(prop.get("params", {}).keys())]).lower()
        score = sum(1 for kw in query_lower.replace("？", " ").replace("？", " ").split() if kw in hay)
        if score > 0:
            hits.append({"score": score, **prop})
    hits.sort(key=lambda h: -h["score"])
    return hits

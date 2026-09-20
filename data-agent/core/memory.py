# -*- coding: utf-8 -*-
"""会话记忆落盘 + steps 留痕 + 黑板。三层里先做对话记忆和执行留痕。"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT / "data" / "sessions"
STEPS_DIR = ROOT / "steps"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
STEPS_DIR.mkdir(parents=True, exist_ok=True)


def save_session(agent, name: str = None):
    """会话级记忆：messages + trace 落盘，重启不丢。"""
    name = name or time.strftime("%Y%m%d_%H%M%S")
    path = SESSIONS_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "messages": [m if isinstance(m, dict) else m for m in agent.messages],
            "trace": agent.trace,
        }, f, ensure_ascii=False, indent=1, default=str)
    return path


def save_step(trace_entry: dict, answer: str, tag: str = None) -> Path:
    """执行留痕：一格=决策+代码(工具调用)+产出。下游可回溯。"""
    tag = tag or time.strftime("%Y%m%d_%H%M%S")
    path = STEPS_DIR / f"step_{tag}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"entry": trace_entry, "answer": answer}, f, ensure_ascii=False, indent=1, default=str)
    return path


def append_blackboard(title: str, body: str, status: str = "待确认"):
    """黑板：Agent 只能写「待确认区」，人改成「已定区」——写权限设计。"""
    bb = ROOT / "blackboard.md"
    line = f"| {time.strftime('%Y-%m-%d %H:%M')} | {status} | {title} | {body} |\n"
    if not bb.exists():
        bb.write_text(
            "# 黑板 · 项目决策留痕\n\n"
            "| 时间 | 状态 | 标题 | 内容 |\n|---|---|---|---|\n",
            encoding="utf-8",
        )
    with open(bb, "a", encoding="utf-8") as f:
        f.write(line)
    return bb


def read_blackboard() -> str:
    bb = ROOT / "blackboard.md"
    return bb.read_text(encoding="utf-8") if bb.exists() else "（黑板为空）"

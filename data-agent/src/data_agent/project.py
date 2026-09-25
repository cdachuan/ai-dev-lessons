# -*- coding: utf-8 -*-
"""项目根解析：统一收口，优先级 = 显式参数 > DATA_AGENT_ROOT > use 指针 > 报错。
所有需要定位项目目录的模块都调 get_project_root()。
"""
import os
from pathlib import Path

_USER_CONFIG_DIR = Path.home() / ".data_agent"
_CURRENT_PROJECT_FILE = _USER_CONFIG_DIR / "current_project"


def set_current_project(path: Path) -> None:
    """把当前项目指针写到用户级配置。"""
    _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CURRENT_PROJECT_FILE.write_text(str(path.resolve()), encoding="utf-8")


def get_current_project() -> Path | None:
    """读取当前项目指针，不存在或无效返回 None。"""
    if not _CURRENT_PROJECT_FILE.exists():
        return None
    p = Path(_CURRENT_PROJECT_FILE.read_text(encoding="utf-8").strip())
    return p if p.exists() else None


def get_project_root(explicit: str | Path | None = None) -> Path:
    """项目根解析：优先级 = 显式参数 > DATA_AGENT_ROOT 环境变量 > use 指针。

    都没有时抛 ValueError，提示用户先 da use。
    """
    # 1. 显式参数
    if explicit is not None:
        p = Path(explicit)
        if not p.exists():
            raise ValueError(f"指定的项目目录不存在: {p}")
        return p.resolve()

    # 2. 环境变量（兼容老用法）
    env = os.environ.get("DATA_AGENT_ROOT")
    if env:
        p = Path(env)
        if p.exists():
            return p.resolve()

    # 3. use 指针
    cur = get_current_project()
    if cur is not None:
        return cur

    # 4. 报错
    raise ValueError(
        "未指定项目根。请先运行 da use <项目目录> 设置当前项目，"
        "或用 --project 参数，或设置 DATA_AGENT_ROOT 环境变量。"
    )

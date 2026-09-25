# -*- coding: utf-8 -*-
"""数据字典读取：口径权威源。工具不写死列名/取值，全从这里查。

包化后字典/数据是「项目资产」不在包内——统一用 get_project_root() 解析项目根。
兼容老用法：设了 DATA_AGENT_ROOT 环境变量的依然有效。
"""
from pathlib import Path

import yaml


def get_root() -> Path:
    """项目根：兼容接口，内部委托 get_project_root()。"""
    from data_agent.project import get_project_root
    return get_project_root()


_ALL_DICTS: dict = {}

def load_dictionary(force_reload: bool = False) -> dict:
    """合并主字典与 ML 字典——单一权威源，避免 agent 在两份字典间迷路。"""
    global _ALL_DICTS
    if not _ALL_DICTS or force_reload:
        _ALL_DICTS = {}
        for name in ("dictionary.yaml", "dictionary_ml.yaml", "dictionary_dash.yaml"):
            p = get_root() / name
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    d = yaml.safe_load(f) or {}
                for k, v in d.items():
                    v["_dict_file"] = name
                    _ALL_DICTS[k] = v
    return _ALL_DICTS


def get_dataset_entry(dataset: str) -> dict:
    d = load_dictionary()
    if dataset not in d:
        raise KeyError(f"字典里没有数据集 '{dataset}'，可用: {list(d.keys())}。口径不清就不动数据——敢说不知道。")
    return d[dataset]


def col(dataset: str, logical_name: str) -> str:
    """逻辑列名 -> 物理列名。当前一对一，留映射扩展位。"""
    entry = get_dataset_entry(dataset)
    cols = entry.get("columns", {})
    if logical_name in cols:
        return logical_name
    raise KeyError(f"数据集 {dataset} 字典里没有列 '{logical_name}'，现有: {list(cols)}")


def valid_values(dataset: str, logical_name: str) -> list:
    entry = get_dataset_entry(dataset)
    return entry.get("columns", {}).get(logical_name, {}).get("valid_values", [])


def dataset_file(dataset: str) -> Path:
    entry = get_dataset_entry(dataset)
    return get_root() / entry["file"]

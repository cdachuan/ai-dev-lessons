# -*- coding: utf-8 -*-
"""数据字典读取：口径权威源。工具不写死列名/取值，全从这里查。"""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dictionary() -> dict:
    with open(ROOT / "dictionary.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    return ROOT / entry["file"]

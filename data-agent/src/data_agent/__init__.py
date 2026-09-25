# -*- coding: utf-8 -*-
"""data_agent：数分 Agent 工具包。

分层暴露：
- 高层：DataAgent —— 一行上手全流程（聊天/数分/ML/核验/报告）
- 低层：每个模块可单独 import 复用（verifier/runner/dictionary/...）
"""
from data_agent.agent import DataAgent
from data_agent.dictionary import (
    load_dictionary,
    get_dataset_entry,
    col,
    valid_values,
    dataset_file,
)
from data_agent.jsonable import _to_jsonable
from data_agent.memory import save_session, save_step, append_blackboard, read_blackboard
from data_agent.governance import bb_add, bb_confirm, bb_list

__version__ = "0.3.0"

__all__ = [
    "DataAgent",
    "load_dictionary", "get_dataset_entry", "col", "valid_values", "dataset_file",
    "_to_jsonable",
    "save_session", "save_step", "append_blackboard", "read_blackboard",
    "bb_add", "bb_confirm", "bb_list",
]

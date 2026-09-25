# -*- coding: utf-8 -*-
"""治理工具：注册给 agent 的黑板/提案/资产查询工具。

写权限设计：agent 只能「提案」，approve/reject 归人（不注册为工具）。
"""
import json

from data_agent.governance import bb_add, propose_asset, lookup_library, list_pending
from data_agent.jsonable import _to_jsonable

from data_agent.ml.tools import run_experiment  # noqa: F401  (re-export 保持注册面)

GOV_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "blackboard_entry",
            "description": "在黑板写一条决策记录（待确认状态，用户确认后成已定）。完成一个重要决策（如选定模型/口径/策略转向）时调用。why 必须写实——黑板的价值在决策理由可回溯。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "decision": {"type": "string", "description": "决策内容，确定性、可执行"},
                    "why": {"type": "string", "description": "决策理由，含关键数字"},
                    "related": {"type": "array", "items": {"type": "string"}, "description": "关联的实验/文件路径"},
                },
                "required": ["title", "decision", "why"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_asset",
            "description": "提交入库提案。跑完有复用价值的分析后调用（分组统计/实验结论/固化流程）。带三件套：口径声明+参数定义+来源。用户审批后才入库生效，你无权直接入库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "资产名，英文蛇形命名"},
                    "kind": {"type": "string", "enum": ["result_table", "step_template", "insight"]},
                    "description": {"type": "string"},
                    "caliber": {"type": "string", "description": "口径声明：算的是什么、按什么口径、排除什么"},
                    "params": {"type": "object", "description": "参数定义（可复用的参数化接口）"},
                    "source_steps": {"type": "array", "items": {"type": "string"}, "description": "来源 step/实验 id"},
                },
                "required": ["name", "kind", "description", "caliber", "params", "source_steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_library",
            "description": "查询已审批入库的资产库。回答问题前若怀疑可能有现成资产（如「品类退款率」已被入库过），先查这里，命中即复用并注明出处。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def blackboard_entry(title: str, decision: str, why: str, related: list = None) -> str:
    entry = bb_add(title, decision, why, related=related)
    return json.dumps({"ok": True, "entry_id": entry["id"], "status": entry["status"],
                       "note": "已写入黑板待确认区，等用户确认"}, ensure_ascii=False)


def _propose_asset(name, kind, description, caliber, params, source_steps) -> str:
    prop = propose_asset(name, kind, description, caliber, params, source_steps)
    return json.dumps({"ok": True, "proposal_id": prop["id"], "status": prop["status"],
                       "note": "提案已提交，用户在审批队列里勾选后才入库生效"}, ensure_ascii=False)


def _lookup_library(query: str) -> str:
    return json.dumps(_to_jsonable({"hits": lookup_library(query)}), ensure_ascii=False, default=str)

GOV_TOOL_REGISTRY = {
    "blackboard_entry": blackboard_entry,
    "propose_asset": _propose_asset,
    "lookup_library": _lookup_library,
}

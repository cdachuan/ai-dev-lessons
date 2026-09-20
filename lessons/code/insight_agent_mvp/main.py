# -*- coding: utf-8 -*-
"""命令行入口：python main.py "问题" 或 python main.py --selftest"""
import argparse
import sys
import json


def main():
    parser = argparse.ArgumentParser(description="数据洞察Agent MVP")
    parser.add_argument("query", nargs="?", help="要分析的问题")
    parser.add_argument("--selftest", action="store_true", help="离线自测（不调LLM）")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
    elif args.query:
        run_query(args.query)
    else:
        parser.print_help()


def run_query(user_query: str):
    """调用LLM执行分析。"""
    from agent.core import run_agent, save_trace

    print(f"问题: {user_query}")
    print("-" * 60)

    answer, trace = run_agent(user_query, verbose=True)
    path = save_trace(user_query, answer, trace)

    print("-" * 60)
    print("答案:")
    print(answer)
    print("-" * 60)
    print(f"运行记录已保存: {path}")


def run_selftest():
    """离线自测：不调LLM，固定问题集核对工具口径。"""
    from tests.eval import run_eval
    success = run_eval()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

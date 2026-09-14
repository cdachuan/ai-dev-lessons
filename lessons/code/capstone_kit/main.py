# -*- coding: utf-8 -*-
"""毕业项目入口（36 课：入口明确）。

用法：
  python main.py --selftest                  离线自测，无需 key
  python main.py "各品类销售额（剔除退款）"    向 Agent 提问
"""
import os
import sys
from pathlib import Path

# 允许从项目根目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _load_dotenv():
    """极简 .env 读取（不引第三方库）：存在就注入环境变量，不覆盖已有值。"""
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0

    if args[0] == "--selftest":
        from tests.eval import run_selftest
        return run_selftest()

    _load_dotenv()
    from agent.core import run_agent, save_trace

    question = " ".join(args)
    print(f"提问：{question}\n")
    try:
        answer, trace = run_agent(question)
    except RuntimeError as e:
        print(f"⚠️ {e}")
        return 1
    path = save_trace(question, answer, trace)
    print("\n" + "=" * 50)
    print(answer)
    print("=" * 50)
    print(f"过程留痕：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

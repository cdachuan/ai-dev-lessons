# -*- coding: utf-8 -*-
"""自研 ReAct 循环：决策归 AI，执行归代码。max_steps 兜底防死循环。

messages.append(msg) 先于遍历 msg.tool_calls；每个结果以 role=tool 塞回。
"""
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from core.tools import TOOL_REGISTRY, TOOL_SCHEMAS, execute_tool

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SYSTEM_PROMPT = """你是数分 Agent，专注数据分析，不是通用助手。工作守则：

1. 任何分析前先 profile_data 了解数据全貌，不直接臆测列含义。
2. 列名和过滤取值必须来自数据字典（工具会校验），字典里查不到、口径不清时，明确说不知道并停下问人——敢说不知道是产品要求，不是丢脸。
3. groupby_sum 的结果必须用 verify_groupby_sum 核验，pass=false 不得作为结论输出。
4. 你知道 verify 只能保证执行自洽，不能保证口径正确。给结论时声明用的口径（如「completed 口径不含退款」）。
5. 输出结论用中文，给数字时附口径声明。"""


class DataAgent:
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置——请把 key 写入 .env（该文件已 gitignore）")
        self.client = OpenAI(api_key=api_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.messages: list = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.trace: list = []  # 每步留痕，供 steps/ 落盘与前端展示

    def ask(self, user_input: str) -> dict:
        """跑一轮 ReAct。返回最终回复 + 完整 trace。"""
        self.messages.append({"role": "user", "content": user_input})
        final_reply = None

        for step in range(self.max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
            )
            msg = resp.choices[0].message

            # 先 append 再遍历——ReAct 铁律
            self.messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                final_reply = msg.content
                self.trace.append({"step": step, "type": "answer", "content": msg.content})
                break

            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = execute_tool(call.function.name, args)
                self.trace.append({"step": step, "type": "tool", "name": call.function.name, "args": args, "result": result})
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                })
        else:
            final_reply = "达到步数上限仍未收敛，中止。已执行的步骤见 trace。"
            self.trace.append({"type": "max_steps_hit"})

        return {"reply": final_reply, "trace": self.trace}

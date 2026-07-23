# 0010 · Function Calling / Tool Use

**日期**：2026-07-14
**课程**：0010 · Function Calling / Tool Use
**状态**：已确认完成

## 关键洞察

1. **Function Calling 是 AI 从「聊天」到「干活」的分水岭** —— 没有 Function Calling 时，AI 只能说话（生成文本）。有了 Function Calling，AI 可以：查数据库、发请求、读写文件、调其他 API。模型输出结构化指令（函数名+参数），由框架（如 Hermes）代为执行。

2. **模型返回的不是执行结果，而是执行指令** —— LLM 作为概率模型输出精确的 JSON 结构（`{"function": {"name": "web_search", "arguments": "{\"query\": \"...\"}"}}`）。这不是「随机」，而是训练数据中大量 JSON+API 调用示例让有效路径上的 Token 概率被训练得极高。框架负责解析 JSON→执行函数→返回结果。

3. **每轮对话框架都会传递可用工具列表** —— 不是只在启动时告诉 LLM 一次，而是每一轮推理都重新发送工具列表。用户理解了这个机制就理解了为什么工具 schema 本身也会消耗 Token。

4. **用户每天都在使用 Function Calling 的产物** —— Hermes 的每个工具（web_search、read_file、terminal 等）都是 Function Calling 的实例。用户的操作流程就是：发出需求 → Hermes（模型）决定调什么工具 → 框架执行 → 返回结果给模型 → 模型组织回答。

5. **Skill、MCP、Tool 都是「特地训练」的结果** —— 不是模型天然会输出 JSON 格式的 tool_calls，而是 OpenAI 在 GPT-3.5/4 时代开始专门做了指令微调训练，让模型学会了「在对话中插播结构化函数调用」的能力。

## 待观察

- 用户是否能区分「框架负责的部分」和「模型负责的部分」
- 用户是否尝试自己定义一个简单的 tool（Python 函数 + schema）
- 用户是否理解了 agent 循环（LLM 决策→框架执行→结果回传→LLM 继续）

## 关联课程

- ← 0002：API（Function Calling 是 API 参数中的一个特殊结构）
- ← 0005：读文件（工具调用是「把本地能力接入 AI」的标准化方式）
- ← 0009：RAG（RAG 可以看作一种「检索」工具的 Function Calling）
- → Phase2 项目：自己写工具脚本

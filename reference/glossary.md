# 术语表 (Glossary)

按首次出现顺序排列。每课新增术语追加到本表。

| 术语 | 英文 | 定义 | 首次课程 |
|------|------|------|----------|
| AI 模型 | AI Model | 被训练来从输入预测输出的程序；LLM 特指预测下一个词的模型 | 0001 |
| LLM | Large Language Model | 大语言模型，参数量达数十亿以上，能理解和生成自然语言 | 0001 |
| 训练 | Training | 给模型喂海量数据，让它调整内部参数以学习规律 | 0001 |
| 推理 | Inference | 训练完成后，模型根据输入实时生成输出的过程 | 0001 |
| 上下文窗口 | Context Window | 模型一次能「看到」的最大文字量上限 | 0001 |
| API | Application Programming Interface | 应用程序接口，让两个程序互相通信的约定 | 0002 |
| API Key | API Key | API 密钥，调用 API 时用来验证身份的「密码」，必须保密 | 0003 |
| SDK | Software Development Kit | 软件开发工具包，把 API 调用封装成更方便的代码库（如 `pip install openai`） | 0003 |
| pip | — | Python 的包管理工具，用来安装第三方代码库（运行 `pip install 包名`） | 0003 |
| Client | 客户端 | 代码中创建的一个「连接对象」，负责和 API 服务器通信 | 0003 |
| JSON | JavaScript Object Notation | 一种结构化数据格式，用 `{}` 表示对象、`[]` 表示列表、`key: value` 表示键值对 | 0003 |
| model | 模型参数 | API 调用中指定用哪个模型的名字参数（如 `deepseek-chat`） | 0003 |
| messages | 消息列表 | 发给 API 的对话内容，是一个 JSON 列表，每条消息包含 role（角色）和 content（内容） | 0003 |
| Prompt | — | 给 AI 模型的输入指令，告诉它你想要什么 | 0004 |
| Token | — | 模型读取文本的最小单位，约 0.75 个英文单词或 1-2 个汉字 | 0005 |
| Agent | — | 能自主使用工具、规划步骤、执行多步任务的 AI 系统 | 0006 |
| Tool Calling | 工具调用 | AI 模型输出结构化 JSON 指令来描述「要调什么工具、传什么参数」，由程序负责执行 | 0007 |
| RAG | Retrieval-Augmented Generation | 检索增强生成：先搜索相关文档，再让模型基于文档回答 | 0009 |
| Function Calling | 函数调用 | 让 AI 模型决定调用哪个函数并填入参数的能力 | 0010 |
| f-string | 格式化字符串 | Python 中用 `f"文本{变量}"` 语法把变量值嵌入到字符串中的写法 | 0008 |
| open() | — | Python 内置函数，用来打开文件；常用模式 `open("路径", "r", encoding="utf-8")` | 0008 |

> 创建于 2026-06-22。随课程推进更新。

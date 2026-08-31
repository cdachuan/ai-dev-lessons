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
| sys.argv | — | Python 系统参数列表；`sys.argv[0]` 是脚本名，`sys.argv[1]` 是第一个命令行参数，用于让脚本接受外部输入 | 0011 |
| openpyxl | — | Python 第三方库，专门用来读写 `.xlsx` 格式的 Excel 文件；需先 `pip install openpyxl` 安装 | 0012 |
| Workbook | 工作簿 | Excel 文件本身，包含一个或多个工作表（sheet），在 openpyxl 中用 `load_workbook("文件名")` 加载 | 0012 |
| Worksheet | 工作表 | Excel 文件中的一个标签页（默认用 `.active` 获取当前打开的那个） | 0012 |
| for 循环 | for loop | Python 中「对每个元素做同一件事」的写法；`for row in rows:` 表示「对 rows 里的每一行，执行下面的代码」 | 0012 |
| join() | 拼接 | Python 字符串方法，`"分隔符".join(列表)` 把列表里的元素用分隔符拼成一个长字符串 | 0012 || pandas | — | Python 数据分析库，用表格（DataFrame）处理数据； 读文件、 分组聚合 | 0031 |
| DataFrame | — | pandas 里的二维表格数据结构，类似 Excel 表，有行和列 | 0031 |
| groupby() | 分组聚合 | pandas 方法：按某列分组后对目标列做统计（sum/count/mean），口诀「按谁分+对哪列+怎么算」 | 0031 |
| merge() | 合并 | pandas 方法：按连接键（on=）把两张表拼起来； 表示以左表为主 | 0031 |
| pivot_table | 透视表 | pandas 方法：二维交叉汇总（行=类别，列=月份，值=指标），groupby 的二维版 | 0031 |
| nunique() | 去重计数 | pandas 方法：数「有几种不同的值」；「客户数」必须用它，「订单数」用 count() | 0031 |
| 指标口径 | — | 一个数字「到底怎么算的」的约定；口径不定，数字没有意义 | 0031 |
| 缺失值 | 缺失值 | 表格里空着的单元格（NaN）；用 isna() 查看、dropna() 删行、fillna() 填默认值 | 0031 |

> 创建于 2026-06-22。随课程推进更新。

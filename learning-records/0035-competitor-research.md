# 数分 Agent 竞品全景研究（2026-09-02）

> 背景：与「自我批判 → 自建数分 Agent」设计探讨（0034）配套的市场验证。
> 调研方式：web_extract（直接抓官网）+ curl 直连 GitHub API（绕过 Exa 对 GitHub 的 CRAWL 失败），未用 web_search（后端 Exa 缺 key，已决定不修）。

## 一、商业化产品（Chat-with-Data）—— 我们刻意跳过它们

### PandasAI → Annie（pandas-ai.com）
- 定位：AI Business Intelligence Agent / AI Data Analyst，主打「聊自然语言 → 即时洞察 + 可视化 + 自动发现」
- 能力：30+ 数据源连接器（PostgreSQL/MySQL/Snowflake/BigQuery/GSheets/SaaS）、Anomaly detection / Root cause analysis / Growth opportunities、Executive summaries / PDF exports、Ad-hoc queries / Trend / Forecasting
- 定价：Plus €29.99/mo（100 credits）、Pro €99.99/mo（500 credits）
- **与我们的分歧点（恰是批判对象）**：无审批门、无原数据只读保护、无流程化的黑板决策层。「自动化发现」是它的差异化，但错误的自信心和 pandasai 一个病根——LLM 生成，无人把关。

## 二、开源可复用组件（Agent 底座/数据工具）—— 可借鉴部件，但不绑定底座

| 组件 | Stars | 定位 | 可借鉴到我们架构 | 为何不当底座 |
|---|---|---|---|---|
| **huggingface/smolagents** | 29119 | 极简 code-thinking Agent 骨架 | 我们 28 课自研 ReAct 就是它的手写版；是路线正确的旁证 | 用语自己骨架，面试讲得清每行为何在 |
| **vanna-ai/vanna** | 23817 | Chat-with-SQL，精确 Text2SQL | 画像→SQL生成→核验，与感知/核验层理念相通 | 只做 SQL 层，无审批/黑板 |
| **e2b-dev/E2B** | 13650 | 安全沙箱跑代码 | 原数据隔离/衍生品模式的成熟参考 | 沙箱非核心，且依赖重 |
| **thepipe** | 1525 | 文档→结构化数据（VLM） | 感知层「画像」的文档侧参考 | 单点组件非全流程 |
| langchain / autogen | 145k/60k | Agent 工程平台/框架 | 过重，与自研 ReAct 理念冲突 | 不采用 |

## 三、空白结论（最值钱的洞察）

扫遍现有「数分 Agent」：要么是**无流程的自动化容器**（Annie/pandasai），要么是**无专精的通用骨架**（langchain/smolagents）。

**没有人把「审批门 + 黑板决策层 + 原数据只读 + 快问报表飞轮」这套数据人专属流程做成产品。**
本项目不是做重复，是填一个真实的市场空白——直接支撑求职叙事与「先做再评估」的决策。

## 附：调研基础设施的稳定组合（已可用）
- **web_extract** 抓官网/文档正文（已验证，Exa 后端但可用）
- **curl 直连 GitHub API**（`api.github.com/repos/<owner>/<repo>`，可拿 stars/description；匿名会 401 限流，少量够用）
- 浏览器工具需 Chrome「Allow remote debugging」手动授权，未用
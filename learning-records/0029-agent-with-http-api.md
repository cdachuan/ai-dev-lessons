# 0029 · 接入真实 HTTP API 作为工具

- **日期**：2026-08-26
- **课号**：29（P5 实战篇）
- **类型**：实操课
- **状态**：done（用户答对小测 B 正解确认学完）
- **GitHub Pages**：https://cdachuan.github.io/ai-dev-lessons/lessons/0029-agent-with-http-api.html

## 核心内容

1. **HTTP API 工具的本质**：和 mock 工具没区别，区别只在「函数内部怎么拿数据」——从 `dict.get()` 变成 `requests.get()`
2. **必加的 3 个工程项**：`timeout=10` / `raise_for_status()` / `try-except`，防止网络卡死
3. **字段清洗**：外部 API 原始 JSON 经常上百行，只挑 4-5 个关键字段喂给 AI——省 token、减干扰
4. **复用 28 课 ReAct 骨架**：主循环代码 100% 不变，只改 3 行（导入 registry、tools 列表、TOOL_REGISTRY 调用）
5. **mock + HTTP 工具混用**：用 `{**MOCK_REGISTRY, "get_weather": get_weather}` 合并 registry，Agent 自己调度多种数据源

## 小测

在 HTTP API 工具函数里，下面哪项是**必须**加的？
- A. 把整个 API 返回的 JSON 完整喂给 AI
- B. 用 `requests.get()` 时加 `timeout=10` ✓
- C. 让 AI 决定超时时长
- D. 用 POST 请求（GET 太简单）

正确答案 **B**。`timeout=10` 是调 HTTP API 的**安全底线**——没有它，对方服务器卡住时程序会无限等待，整个 Agent 直接死锁。

A 错：原始 JSON 经常上百行，完整喂给 AI 既烧 token 又干扰推理；正确做法是**在工具函数里挑字段**，只返回 4-5 个关键字段。
C 错：超时时长是**工程参数**，跟 AI 决策无关，AI 只决定「调不调工具」，不决定「底层怎么调」。
D 错：HTTP 方法由 API 设计决定，不是「越复杂越好」——`wttr.in` 就是 GET。

## 教学设计

- **API 选 wttr.in**：免费、无需注册、中英文城市都支持、开浏览器直接看 JSON
- **30 课预告**：工具参数校验、JSON Schema、工具返回统一格式——从「能跑」到「稳定可控」
- **35 课预演**：timeout + 异常处理是评估与安全的入门基础

## 与 28 课的衔接

- 28 课：4 个 mock 工具（查字典）
- 29 课：把其中一个替换成 HTTP API 工具（发网络请求）
- 共同点：ReAct 主循环、TOOL_REGISTRY 字典、工具说明书三件套全部不变
- 新增点：HTTP 调用的安全保护（timeout/raise_for_status/try-except）、字段清洗

## 下一课

0030 · 工具设计与结构化输出：参数校验、JSON Schema、工具返回统一格式、何时该调用工具。从能跑到稳定可控的关键

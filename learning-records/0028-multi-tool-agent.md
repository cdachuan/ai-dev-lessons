# 0028 · 多工具 Agent：ReAct 循环的代码实现

## 元信息

- 课号：0028
- 状态：pushed（2026-08-24 08:00 推送）
- 阶段：P5 实战篇
- 主题：从 1 工具 1 调用升级到多工具 ReAct 循环
- 类型：实操课

## 核心内容

1. **从单工具到多工具的真正变化**：真实工作问题往往需要多步（查两次 + 算一次 + 对比），1 工具 1 调用搞不定
2. **设计 4 个工具**：query_taigu_kwh / query_line_loss_rate / compare_taigus / calculate_pct_change，覆盖一组真实业务问题
3. **TOOL_REGISTRY 字典**：把工具名映射到 Python 函数，新增工具只改两处
4. **ReAct 循环核心 30 行**：`for step in range(max_steps)`，AI 每步 Thought→Action→Observation
5. **max_steps 兜底**：限制最多 6 轮，防止死循环烧光 API 额度
6. **try/except 包装**：工具执行出错也能塞回给 AI 继续推理

## 关键设计点

- **ReAct 是什么**：Reasoning（思考）+ Acting（行动）。AI 看完工具结果，自己推理下一步做什么
- **AI 自主决定**：调几次、调哪些、什么时候停——你完全不写 if-else
- **兜底保护必加**：max_steps + try/except，否则生产环境必出事
- **description 仍是命门**：4 个工具 description 写得好不好，决定 AI 会不会选对工具、组合对顺序

## 与 27 课的衔接

- 27 课是 1 工具 1 调用：本课是 27 课代码加 `for` 循环 + `TOOL_REGISTRY`
- 27 课没有 max_steps：本课补上这个工程化必加项
- 27 课 try/except 没引入：本课自然补全（处理工具执行错误）

## 用户的认知负荷

- 用户 pandas 扎实，编程底子够
- 选择「台区电量+百分比变化」作为问题，贴近用户实际工作
- 4 个工具不多不少，刚好演示「AI 自己调度」的动态性
- 不引入 MCP、JSON Schema 校验、token 计数等，留给 29-30 课

## 下一课预告

0029 · 接入真实 HTTP API 作为工具：把 HTTP API 封装成工具，Agent 调真实数据，不再 mock

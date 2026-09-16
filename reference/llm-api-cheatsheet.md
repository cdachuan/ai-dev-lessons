# LLM API 调用必知必会（速查卡）

> 整理自 2026-09-16 手写 ReAct 时踩过的全部坑。配合 `lessons/code/data_verify_copy.py` 看。
> 原则：**网络上只有文字**。LLM 给你的、你发给 LLM 的，本质都是字符串。所有"对象感"都是 SDK 解析出来的。

---

## 一、一次调用长什么样

```python
resp = client.chat.completions.create(
    model="deepseek-chat",        # 模型名不能编（deepseek-chat / deepseek-reasoner）
    messages=messages,            # 完整对话历史（见第三节）
    tools=tools,                  # 工具说明书，每轮全发
    temperature=0.5,              # 可选，0最稳，越高越发散
)
msg = resp.choices[0].message     # ← 核心对象
```

## 二、返回对象的层级（必背）

```
resp
├─ .choices[0]
│  ├─ .finish_reason        "stop"=答完了  "tool_calls"=要调工具
│  └─ .message = msg
│     ├─ .content           str | None   —— AI说的人话
│     └─ .tool_calls        list | None  —— 工具请求条列表
│        └─ 每张条 tc:
│           ├─ .id                         条的编号（回寄必须带上）
│           └─ .function
│              ├─ .name                    函数名 str
│              └─ .arguments               ⚠️ JSON字符串，不是字典！
└─ .usage                   token账单
```

**四个高频错（全踩过）：**

| 错 | 对 |
|---|---|
| `mag = msg.content` 再找 `.tool_calls` | `mag = msg`，content 和 tool_calls 都在 msg 上 |
| 把 arguments 当字典用 | `args = json.loads(tc.function.arguments)` 先解析 |
| 假设只有一张条 | 永远 `for tc in msg.tool_calls:`，一轮可能多张（并行调用） |
| 看 content 有没有字判断结束 | 只看 `if not msg.tool_calls:` |

## 三、messages：无状态的假象

- LLM **每轮都是失忆的**。它"记得"上一步，是因为你每轮把整个 messages 列表重发一遍。
- 每转一圈，列表多两条：

```
[system, user]
  → append(msg)              # AI的请求条，必须是整个对象！
  → append(工具结果)          # role="tool"
= [system, user, assistant(带tool_calls), tool, ...]
```

**致命错：** `{"role":"assistant","content":msg.content}` —— tool_calls 丢了，
下一轮 API 报 400（assistant 没说要调工具，后面却跟着 tool 结果）。
**正解：直接 `messages.append(msg)`。**

工具结果的固定包法：
```python
{"role": "tool",
 "tool_call_id": tc.id,                    # ← 是条的id，不是函数名！
 "content": json.dumps(result, ensure_ascii=False)}
```

## 四、tools 说明书：固定 JSON Schema

```python
tools = [{"type": "function", "function": {
    "name": "groupby_sum",
    "description": "按列分组求和。算销售额时注意是否要排除已退款订单。",  # ← AI靠这句选工具
    "parameters": {
        "type": "object",
        "properties": {
            "group_col": {"type": "string", "description": "分组列名"},
            "value_col": {"type": "string", "description": "求和列名"},
            "filter_status": {"type": "string", "description": "可选，过滤状态"}},
        "required": ["group_col", "value_col"]}}}]
```
- parameters **不是列表**，是 `{"type":"object","properties":{...},"required":[...]}`
- 无参工具：`"parameters": {"type": "object", "properties": {}}`
- `returns`/`example` 字段 API 不认（写了被忽略），别依赖
- description 写得好坏直接决定 AI 选得对不对——这是39课的功夫

## 五、执行三件套

```python
args = json.loads(tc.function.arguments)          # 字符串→字典
fn = TOOL_REGISTRY[tc.function.name]              # 字典查到函数本身（不执行）
result = fn(**args)                               # 括号=执行；**把字典拆成关键字参数
```

## 六、key 与环境

```python
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com")
```
key 永不写进代码/git。Windows 持久设置：`setx DEEPSEEK_API_KEY "sk-..."`，**重开终端生效**。

---

# 附：今晚暴露的 Python 基础补丁

1. **函数是对象，可以存字典**：`REGISTRY = {"add": add}`。取出不带括号 `f = REGISTRY["add"]` 只是拿到函数；**加括号 `f()` 才执行**。
2. **`**args` 拆字典**：`f(**{"a":3,"b":5})` = `f(a=3,b=5)`。不加 `**` 整个字典被当成第一个参数。
3. **缩进决定归属**：工具结果的 append 必须在 `for tc` 循环体内，否则调3个工具只回寄1个结果。
4. **别用内置名当变量**：`input = input(...)` 会覆盖 input 函数，第二次调用崩。同理 list/str/df 等。
5. **pandas：`df.info()` 返回 None**，它只往屏幕打印；要拿信息用 `df.dtypes`、`df.shape`、`df.isna().sum()`。
6. **`df.describe().to_dict()`** 直接转即可，它不是记录列表，不用 `"records"`。
7. **try/except 包工具执行**：AI 给的参数可能错，崩了也要把错误信息回寄给 AI，让它重试，别让整个 Agent 挂。

---

## 还没填上的课（见同目录坑清单）
工具间状态传递（df 不能当参数给 AI）、verify 正确设计（eval 独立路径）、并行多工具条——见 `lessons/code/REACT复刻_坑清单_20260916.md`。

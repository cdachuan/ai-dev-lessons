# 电商订单分析 Agent（P5 毕业项目脚手架）

一个「会读数据、会算数、出结论前自己复核」的数据分析 Agent。
自然语言提问 → Agent 自己选工具、算指标、独立复算 → 给出带口径说明的结论。

> 本项目是学习脚手架：每一块对应课程里亲手做过的零件（见 [ARCHITECTURE.md](ARCHITECTURE.md)）。
> 你的毕业任务不是「读懂代码」，而是**跑通 → 改造 → 换成你自己的数据 → 发布**。

## 三步跑起来

```bash
# 1. 装依赖（只需 pandas 和 openai）
pip install -r requirements.txt

# 2. 配置 key（二选一）
#    Windows bash:  export DEEPSEEK_API_KEY=你的key
#    或复制 .env.example 为 .env 填入（.env 不会进 git）
cp .env.example .env

# 3a. 不需要 key 就能跑：离线自测（用固定问题集核对数据口径）
python main.py --selftest

# 3b. 配好 key 后：向 Agent 提问
python main.py "各品类销售额是多少（剔除退款）？"
```

## 目录说明

| 路径 | 作用 | 对应课程 |
|---|---|---|
| `main.py` | 入口：提问 / `--selftest` 离线自测 | 36 入口明确 |
| `agent/tools.py` | 五个数据工具（画像/分组求和/分组计数/去重计数/核验） | 34 |
| `agent/core.py` | ReAct 循环 + 步数预算 + 每次运行落盘留痕 | 28/34/35 |
| `tests/eval.py` | 固定测试问题集 + 标准答案（pandas 离线算） | 35 |
| `data/orders.csv` | 示例电商订单（60 行，可换成你自己的） | — |
| `runs/` | 每次提问的完整过程记录（工具、参数、结果、答案） | 35 留痕 |
| `ARCHITECTURE.md` | 架构图 + 设计决策 | 24 |
| `SHOWCASE.md` | 效果展示：真实运行输出（自测/工具层结果/面试可讲点） | 37 |

## 换自己的数据

1. 把你的 CSV 放到 `data/` ，修改 `agent/tools.py` 顶部的 `DATA_FILE`
2. 列名不同没关系，但要同步改 `tests/eval.py` 里的问题和标准答案
3. 先跑 `--selftest` 确认口径，再向 Agent 提问

## 安全约定

- key 只从环境变量读，代码里没有任何 key（35 课安全闸①）
- `.env`、`runs/`、真实数据已在 `.gitignore` 中
- Agent 只有读数据和写 `runs/` 的权限，**永远不能修改原数据**

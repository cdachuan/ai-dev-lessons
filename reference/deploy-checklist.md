# 部署检查清单（Deploy Checklist）

把「只在我电脑上跑」变成「别人也能跑」——交出去之前逐条过一遍。
配套课程：[0036 部署与上线](../lessons/0036-deploy-and-launch.html)

## 一、六条硬检查

| # | 检查项 | 判断标准 | 常见报错信号 |
|---|--------|----------|--------------|
| 1 | 依赖写全 | `requirements.txt` 列出了脚本真正 import 的每个第三方库 | `ModuleNotFoundError: No module named 'xxx'` |
| 2 | key 不写死 | 代码里只有 `os.environ.get("XXX_KEY")`；值在本地 `.env`（不提交），仓库里给 `.env.example` | `KeyError` / 401 / 代码里能搜到 `sk-...` |
| 3 | 无绝对路径 | 全用相对路径或 `Path(__file__).parent` | `FileNotFoundError: D:\学习\...` |
| 4 | 示例数据随仓库 | `data/sample.csv` 之类小样本已提交；真实业务数据在 `.gitignore` 里 | 对方跑起来找不到输入文件 |
| 5 | README 第一行是启动命令 | `pip install -r requirements.txt` → 配 key → `python main.py` | 对方问「怎么跑」 |
| 6 | 干净目录实测 | 换目录（或换机器）clone 下来，严格照 README 走通一遍 | 报的每个错＝漏掉的检查项 |

## 二、仓库标准结构（阶梯 0）

```
my-agent/
├── README.md            # 怎么装、怎么配 key、怎么跑
├── requirements.txt     # 依赖清单
├── .env.example         # 配置模板：只有键名，没有真值
├── .gitignore           # 挡住 .env 和真实数据
├── main.py              # 入口：一条命令能起
├── agent/               # 你的工具/主循环代码
└── data/
    └── sample.csv       # 示例数据（可提交）
```

## 三、`.gitignore` 最小内容

```
.env
*.key
__pycache__/
*.pyc
data/real_*        # 真实业务数据一律不进仓库
```

## 四、配置读取的标准写法

```python
import os
api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit("未找到 DEEPSEEK_API_KEY，请复制 .env.example 为 .env 并填入")
```

`.env.example`（提交进仓库）：

```
DEEPSEEK_API_KEY=your_key_here
```

`.env`（**不提交**，本地真实值）：`DEEPSEEK_API_KEY=sk-xxxx`

## 五、三级阶梯速查

| 阶梯 | 方案 | 成本 | 适用 | key 放哪 |
|------|------|------|------|----------|
| 0 | git 仓库（README + requirements + .env.example） | 0 | 交付代码、求职作品、同事试用 | 对方本地 `.env` |
| 1 | Streamlit Community Cloud | 0 | 要「给个链接点开看」 | 平台 Secrets，代码用 `st.secrets` |
| 2 | 阿里云函数计算 FC（Web 函数）／腾讯云 Serverless HTTP／轻量服务器 | 按量付费 | 连数据库、内网访问、长期在线 | 平台环境变量配置 |

> 顺序原则：**先用 0 元方案跑通全流程，缺什么再补什么**，别一上来就买服务器。

## 六、容易忘的三个细节

- **路径**：`Path(__file__).parent / "data" / "sample.csv"`，比 `"data/sample.csv"` 更稳（不怕别人从别的目录启动）。
- **编码**：读文件一律写 `encoding="utf-8"`，Windows 默认编码会让中文标题乱码。
- **入口**：入口脚本只做「解析参数 → 调函数 → 打印结果」，别把业务逻辑堆在入口里——别人读 README 三行就能跑，你日后也好改。

> 创建于 2026-09-11（配套 0036 课）。

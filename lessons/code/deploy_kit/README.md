# 我的 AI 分析工具（交付模板）

> 这是模板，照着改即可。README 的第一行必须是**别人拿到就能照做的启动命令**。

把 Agent 从「只在我电脑上跑」变成「别人也能跑」——本模板配合课程 0036《部署与上线》。

## 怎么跑（别人照这三步走）

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 配密钥：复制模板，填入自己的 key
cp .env.example .env      # Windows: copy .env.example .env

# 3. 启动
python main.py
```

## 这个工具做什么

用一句话说清：读入 `data/sample.csv`，按品类汇总销售额并打印排名。
（示例数据是假的，真实数据不会进仓库。）

## 目录说明

```
├── README.md          # ← 你正在看的这份：装／配／跑
├── requirements.txt   # 依赖清单
├── .env.example       # 配置模板（只有键名，没有真值）
├── .gitignore         # 挡住 .env 和真实数据
├── main.py            # 入口
└── data/
    └── sample.csv     # 示例数据
```

## 换成自己的项目时要改哪几处

1. `requirements.txt`：把你真正 `import` 的库列上（例如 pandas、openai）。
2. `main.py`：把示例逻辑换成你自己的工具／Agent 主循环。
3. `data/sample.csv`：换成**脱敏的小样本**，真实业务数据留在本地。
4. 本 README 的「这个工具做什么」和「怎么跑」两节。

## 交付前自检

按 `reference/deploy-checklist.html` 六条逐项过一遍，最后**换个干净目录 clone 下来走一遍**——
报的每一个错，都是你漏掉的检查项。

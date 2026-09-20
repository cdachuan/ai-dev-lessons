# 数据洞察Agent MVP

**定位**: 上传数据 → 自然语言提问 → 自主分析 → 图表报告 → 数据依据

## 架构简图

```
用户提问
    ↓
┌─────────────────────────────────────────┐
│  agent/core.py (ReAct循环)              │
│  LLM决策 → 调工具 → 观察 → 循环        │
│  最多10步，每步落盘runs/留痕           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  agent/tools.py (工具层)                │
│  ┌──────────┬──────────┬──────────┐     │
│  │ profile  │groupby_agg│monthly_trend│  │
│  └──────────┴──────────┴──────────┘     │
│  ┌──────────┬──────────┬──────────┐     │
│  │rfm_table │bar_chart │line_chart│     │
│  └──────────┴──────────┴──────────┘     │
│  ┌──────────┐                           │
│  │  verify  │ (结果自检)               │
│  └──────────┘                           │
└─────────────────────────────────────────┘
    ↓
图表报告 + 数据依据
```

## 工具清单

| 工具 | 功能 | 说明 |
|------|------|------|
| profile | 数据画像 | 返回表结构、行数、列信息 |
| groupby_agg | 分组聚合 | 按列分组，支持sum/mean/count/nunique |
| monthly_trend | 月度趋势 | 按月聚合，自动标注不完整月份 |
| rfm_table | RFM客户分层 | 按Recency/Frequency/Monetary评分 |
| bar_chart | 柱状图 | 生成横向柱状图HTML |
| line_chart | 折线图 | 生成折线图HTML，支持多条线 |
| verify | 结果自检 | 用独立pandas代码复算结论 |

## 运行方法

### 1. 安装依赖

```bash
cd insight_agent_mvp
pip install -r requirements.txt
```

### 2. 配置API Key（可选）

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

### 3. 命令行提问

```bash
python main.py "各月销售额趋势如何？"
python main.py "哪些国家销售额最高？"
python main.py "RFM客户分层情况如何？"
```

### 4. 离线自测（无需API Key）

```bash
python main.py --selftest
```

## 与capstone_kit的演进关系

| 特性 | capstone_kit | insight_agent_mvp |
|------|--------------|-------------------|
| 数据 | 60行示例数据 | 54万行真实电商数据 |
| 工具数量 | 5个 | 7个（新增图表、月度趋势） |
| 图表 | 无 | pyecharts生成HTML |
| 可视化 | 无 | 柱状图、折线图 |
| 客户分析 | 无 | RFM客户分层 |
| 最大步数 | 8步 | 10步 |
| 数据源 | 订单数据 | 零售交易数据 |

## 实跑记录

### 自测通过记录

```
============================================================
数据洞察Agent MVP - 离线自测
============================================================

[TEST] 数据画像... PASS
[TEST] 国家销售总额Top3... PASS
[TEST] 月度趋势... PASS
[TEST] RFM客户分层... PASS
[TEST] 结果自检verify... PASS
[TEST] 销售额一致性检查... PASS
[TEST] 客户数量统计... PASS

============================================================
测试结果: 7 PASS, 0 FAIL
============================================================

全部测试通过!
```

### 实际提问示例（需配置DEEPSEEK_API_KEY）

```bash
$ python main.py "各月销售额趋势如何？"
问题: 各月销售额趋势如何？
------------------------------------------------------------
  [step 1] -> profile({})
  [step 2] -> monthly_trend({'metric': 'revenue'})
  [step 3] -> line_chart({'x_items': [...], 'series_dict': {...}, 'title': '月度销售额趋势', 'out_html': 'output/monthly_trend.html'})
------------------------------------------------------------
答案:
根据分析，各月销售额趋势如下：
- 2010年12月: 短暂运营期，销售额约57.26万
- 2011年1月: 约56.12万
- 2011年2月: 约44.45万
- 2011年3月: 约59.26万
...
2011年12月数据不完整（仅包含部分日期）

图表已保存: output/monthly_trend.html

运行记录已保存: runs/20260920-143025.json
```

### 实际提问示例

```bash
$ python main.py "各月销售额趋势如何？"
问题: 各月销售额趋势如何？
------------------------------------------------------------
  [step 1] -> profile({})
  [step 2] -> monthly_trend({'metric': 'revenue'})
  [step 3] -> line_chart({'x_items': [...], 'series_dict': {...}, 'title': '月度销售额趋势', 'out_html': 'output/monthly_trend.html'})
------------------------------------------------------------
答案:
根据分析，各月销售额趋势如下：
- 2010年12月: 短暂运营期，销售额约57.26万
- 2011年1月: 约56.12万
- 2011年2月: 约44.45万
- 2011年3月: 约59.26万
...
2011年12月数据不完整（仅包含部分日期）

图表已保存: output/monthly_trend.html

运行记录已保存: runs/20260920-143025.json
```

## 项目结构

```
insight_agent_mvp/
├── agent/
│   ├── __init__.py
│   ├── core.py          # ReAct循环
│   └── tools.py         # 工具层
├── tests/
│   ├── __init__.py
│   └── eval.py          # 评估问题集
├── runs/                # 运行记录（gitignore）
├── main.py              # 命令行入口
├── requirements.txt     # 依赖
├── .gitignore           # git忽略
├── README.md            # 本文件
└── app.py               # Streamlit界面（44课参考实现）

## Streamlit 界面（参考实现，44课）

```bash
pip install streamlit pyecharts openai
streamlit run app.py
```

- 侧边栏：CSV上传（不传则用内置54万行演示数据）+ API key 输入（**只存内存 session_state，不落盘**）
- 主区：数据画像页 + 对话式提问（Agent 选工具→算数→自检），每轮可展开看工具调用留痕
- 会话历史 + 一键下载 Markdown 报告
- 冒烟验证：`streamlit run` 启动后 `curl localhost:8599` 返回 HTTP 200（2026-09-20 实测）

# 电商数据分析工具箱

P6第39课配套代码，可复用的规范工具集。数据来源：UK电商在线零售数据（54万行）。

## 工具清单

| 函数 | 功能 | 参数 |
|------|------|------|
| `read_orders` | 读取CSV，自动转换日期 | `path`, `usecols=None` |
| `clean_orders` | 清洗：去空CustomerID、拆退货、去异常、加revenue | `df`, `drop_customer_na=True` |
| `kpi_summary` | 计算KPI：GMV/订单数/客单价/客户数/退货率 | `df`, `start=None`, `end=None` |
| `groupby_agg` | 通用分组聚合 | `df`, `group_col`, `value_col`, `agg`, `top_n` |
| `monthly_trend` | 月度趋势（标注不完整月份） | `df`, `metric` |
| `country_top` | 国家GMV排名 | `df`, `n=10` |
| `rfm_table` | RFM客户分层（R/F/M打分1-5） | `df` |
| `bar_chart` | pyecharts横向柱状图存HTML | `items`, `values`, `title`, `out_html` |
| `line_chart` | pyecharts折线图存HTML | `x_items`, `series_dict`, `title`, `out_html` |

## 参数说明

### read_orders(path, usecols=None)
- `path`: CSV文件路径（str或Path）
- `usecols`: 要读取的列名列表，None读全部
- 返回: `{"ok": bool, "data": DataFrame}`

### clean_orders(df, drop_customer_na=True)
- `df`: 原始订单DataFrame
- `drop_customer_na`: 是否剔除CustomerID缺失行（默认True）
- 清洗逻辑:
  - CustomerID缺失 → 剔除（无法归因客户）
  - InvoiceNo以C开头或Quantity<0 → 退货，revenue记负数
  - UnitPrice<=0 → 剔除异常数据

### kpi_summary(df, start=None, end=None)
- `start`/`end`: 日期过滤，格式"2011-01-01"
- 返回: 总GMV、订单数、客单价、购买客户数、退货率、时间范围

### groupby_agg(df, group_col, value_col, agg, top_n)
- `agg`: sum/mean/count/nunique
- `top_n`: 取前N名

### monthly_trend(df, metric)
- `metric`: 统计列名，默认revenue
- 自动标注2011-12不完整月份

### rfm_table(df)
- 按CustomerID计算R/F/M，各打分1-5
- 标签: 高价值(>=12)、中价值(>=8)、低价值(<8)

### bar_chart / line_chart
- `bar_chart(items, values, title, out_html)`
- `line_chart(x_items, series_dict, title, out_html)`
- 输出: 交互式HTML文件

## Demo运行方法

```bash
cd lessons/code/ecommerce_toolkit
python demo.py
```

无需API Key，直接运行。输出文件在 `output/` 子目录。

## 实跑记录

**运行时间**: 2026-09-20  
**数据文件**: online_retail_2010_2011.csv（541,909行原始数据）

```
原始行数: 541,909
清洗后行数: 406,789
```

**KPI摘要**（2026-09-20 由 Hermes 独立复算修正口径后重跑）:
| 指标 | 数值 | 口径说明 |
|------|------|---------|
| 总GMV | 8,300,065.81 | 净销售额（退货记负收入） |
| 订单数 | 18,532 | 只数有购买行为的发票，退货单不计 |
| 购买客户数 | 4,371 | CustomerID 去重 |
| 客单价 | 447.88 | 净GMV ÷ 订单数 |
| 人均消费ARPU | 1,898.89 | 净GMV ÷ 客户数（原版误标为客单价，已修正） |
| 退货率 | 6.42% | 退货金额绝对值 ÷ 总流水绝对值 |
| 时间范围 | 2010-12-01 ~ 2011-12-09 | |

**输出文件**:
- `output/kpi_summary.txt` — KPI摘要
- `output/monthly_trend.csv` — 月度趋势
- `output/top10_country.html` — Top10国家GMV柱状图

**验证状态**: ✅ 全部通过

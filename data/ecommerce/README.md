# 电商数据集档案（39-45课贯穿素材）

## 来源
- UCI Machine Learning Repository — Online Retail（ID 352）
- 下载: https://archive.ics.uci.edu/static/public/352/online+retail.zip
- 引用: Chen, Sain, Guo (2012), "Online retail: a data mining framework for enhancing business intelligence"

## 本地文件（D:\学习\ai-dev\data\ecommerce\）
| 文件 | 说明 |
|---|---|
| online_retail_2010_2011.csv | 主数据，utf-8-sig，54万行（xlsx/zip原始件已清理，需要可从UCI重新下载） |

## 数据概览（2026-09-20 实测）
- 541,909 行 × 8 列；2010-12-01 → 2011-12-09（约13个月）
- 字段: InvoiceNo(发票号,含C开头=退货), StockCode(商品码), Description(品名),
  Quantity(数量,可为负=退货), InvoiceDate, UnitPrice(单价), CustomerID(客户ID,约25%缺失), Country(38国)
- 天然脏数据（41/42课容错练习现成素材）:
  - 缺 CustomerID: 135,080 行（25%）
  - 退货负数量: 10,624 行
  - 2011-12月数据不完整（截到12-09），做月度趋势要剔除或标注

## 与 P6 规划的对应
- 39 课: 封装读取/清洗/聚合/图表工具 → 用此数据
- 40 课: GMV/客单价/复购/RFM/漏斗 → 用此数据
- 43 课: 数据洞察 Agent MVP 的默认演示数据集
- 真实 UK 电商，非合成数据，面试可讲来源

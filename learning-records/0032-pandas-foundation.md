# 0032 · pandas 基础夯实 + 数据分析实战素材

- **日期**：2026-08-31
- **课号**：31（P5 实战篇）
- **类型**：基础夯实课（概念+实践）
- **状态**：pushed（08-31 cron 推送，待用户确认）
- **GitHub Pages**：https://cdachuan.github.io/ai-dev-lessons/lessons/0031-pandas-foundation.html

## 背景

- 第30课（工具设计与结构化输出）08-27 推送后 4 天未确认（08-28、08-29 两次提醒无响应），按 19/20 课先例（多轮提醒无响应后兜底标记 done），08-31 兜底标记 30 为 done，推进第 31 课。
- 31 课 HTML 此前是占位符（「待生成」），本次生成完整版。

## 核心内容

1. **为什么夯实 pandas**：34 课要做 Agent+数据分析，Agent 负责「想」、pandas 负责「算」。用户必须能读懂并核验 Agent 写的 pandas 代码
2. **四件套挂业务问题**：
   - 读数据：read_csv / read_excel，head()/info() 先摸底
   - 布尔筛选：df[条件]，多条件用 & | 且每条件加括号
   - groupby 分组：口诀「groupby(按谁分)+[对哪列]+怎么算」
   - merge 合并：on= 连接键，how="left" 以左表为主
3. **进阶三件套**：pivot_table 透视（groupby 二维版）、to_datetime 日期处理、清洗三板斧（isna/dropna/fillna、drop_duplicates、describe 找异常）
4. **核心心法：指标口径先于代码**——算谁 / 怎么算 / 要不要排除。清洗铁律：删之前先想清楚，动作要有理由写进注释

## 关键设计点

- **业务问题 → 操作映射**：每个 pandas 操作都配真实业务问题（电商订单表），不只讲语法
- **「Pandas 会写 ≠ 能回答业务问题」**：本课主线，为 34 课 Agent 核验打底
- **指标口径**：新术语，数据分析最值钱的词。以后 Agent 输出分析结果，用户第一句要问「这个数的口径是什么？」
- **实战素材 = 电商订单表**：orders.csv（order_id/customer_id/date/category/amount/status），衔接 39-40 课电商项目

## 小测

订单表 10 条记录，C01 下 3 单、C02 下 2 单、其余 5 客户各 1 单。「这个月一共有多少客户下单？」用哪个操作？

- A. `len(df)`
- B. `df["customer_id"].nunique()` ✓
- C. `df["customer_id"].count()`
- D. `df.groupby("customer_id").sum()`

正确答案 **B**。nunique()=去重计数，答案 7。A 是订单数 10；C 含重复=10；D 是求和。教训：「数客户」和「数订单」是两个问题，拿「数 XX」先问要不要去重。

## 教学设计

- **承接**：30 课讲工具工程化，31 课转回数据层，概念与实践交替
- **衔接**：32 课 pandasai 体验课（不替代 pandas）、34 课 Agent+数分、39-40 课电商实战
- **用户基础**：pandas 语法已过关（07-29 摸底），本课重点是把语法挂到业务问题上 + 补齐 pivot_table/日期/清洗

## 备注

- 顺手修复：28-30 课 HTML 一直未推上 gh-pages（链接 404），本次一并提交推送
- 用户回复「看完了」→ 标 31 done → 推 32 课（pandasai 体验课）

# 简历项目段（英文版）

> 与中文版（作品集README.md）对应。投外企/外贸/跨境岗用。
> 使用规则同中文版：如实写个人项目；面试时业务结论先行。

## Project 1: Data Insight Agent (AI Application)

> **Data Insight Agent** — Independent Project
> Built a natural-language data analysis agent on a real-world e-commerce dataset (540K orders): users ask questions in plain language; the agent autonomously selects analysis tools, runs pandas computations, independently verifies every result, then delivers conclusions with data tables and visualizations.
>
> - Designed 8 tool functions (data profiling, aggregation, trend, RFM, charting) with unified structured returns and error feedback for reliable LLM function calling
> - Implemented a verify mechanism: every conclusion is recomputed via an independent code path before output — catching model arithmetic errors by design, not by luck; full tool-call traces are logged for auditability
> - Built a 15-question regression suite with ground-truth answers computed offline via an independent implementation
> - Shipped a Streamlit UI: CSV upload, conversational analysis, session history, one-click Markdown report export
>
> **Stack**: Python / pandas / Function Calling / pyecharts / Streamlit

## Project 2: E-commerce Operations Analysis (Business Case)

> **E-commerce Operations Analysis: Customer Segmentation & Growth Decomposition** — Independent Project
> End-to-end analysis of 540K real e-commerce orders (UCI Online Retail): from data cleaning to business recommendations.
>
> - Made data-cleaning logic explicit and auditable: identified return orders (negative quantities / "C"-prefixed invoices), 25% missing customer IDs, and incomplete months — every metric reported with its exact definition
> - RFM segmentation revealed that 26% of customers generate 69% of revenue; identified the "at-risk" segment (~£480K revenue exposure) as the highest-ROI retention target
> - Decomposed growth structure: seasonal rhythm (Sep–Nov peak), order-count-driven growth (stable AOV), and overseas markets (Netherlands / Ireland / Germany) as the second growth curve
> - Proactively documented data pitfalls: missing Saturdays in the dataset, postage items in product rankings, mean skewed by whale customers — validating data before drawing conclusions
>
> **Stack**: pandas / RFM / pyecharts

## One-liner (interview opener)

> "I do data analysis, but differently from pure business analysts: I've packaged my daily analysis workflow into an agent that understands plain language — with the rigor of analytics (metric definitions, independent verification, regression suites) built into the tool layer. On the business side, I've done full customer segmentation and growth decomposition on real e-commerce data."

## 关键术语中英对照（面试实战用）

| 中文 | 英文 |
|---|---|
| 口径 | metric definition / caliber |
| 核验/复算 | independent verification / cross-check |
| 留存 | retention |
| 复购率 | repeat purchase rate |
| 客单价 | average order value (AOV) |
| 客单价（人均） | ARPU (average revenue per user) |
| 漏斗 | conversion funnel |
| 自选择偏差 | self-selection bias |
| 辛普森悖论 | Simpson's paradox |
| 幸存者偏差 | survivorship bias |
| 置换检验 | permutation test |
| 置信区间 | confidence interval |
| 最小权限 | least privilege |
| 审计留痕 | audit trail |

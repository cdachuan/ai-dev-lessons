# 黑板 · 项目决策留痕

> Agent 只写「待确认」；人确认改「已定」。json 真源在 library/entry_*.json。

## 🟡 品类销售额口径：仅取 completed 订单  `20260921_121524`
- **决策**：orders 数据集「各品类销售额」统一采用 status=completed 过滤口径，仅对 completed 订单的 amount 求和；refunded/pending 等其他状态订单不计入。
- **why**：应业务要求以 completed 为完成口径；核验通过（groupby vs 布尔索引双路径复算 pass=true，无 mismatch）。结果：食品 46667.27、服饰 38714.26、数码 35335.61、家居 32187.08。注意该口径不含退款扣减，不等于净收入；若需净口径需另立 refunded 处理规则。status 列 valid_values 已由字典注册，取值合法。
- **关联**：category_sales_completed、groupby_sum:orders/category/amount/status=completed
- *2026-09-21 12:15 · 待确认*

## 🟢 退款预测采用 balanced 版  `20260921_121008`
- **决策**：RF + class_weight=balanced 作为退款预测生产配置
- **why**：recall 0.39→0.50 且 precision 持平；业务宁可误召不可漏召
- **关联**：steps/ml_runs/exp_095703681_pred.csv
- *2026-09-21 12:10 · 已定*

# metric_guard · 指标口径字典与校验器

> 一处声明口径，处处校验数字。「把口径做进工具层」的可复用实现。

## 为什么需要它

LLM/人/不同脚本算同一个指标，最容易出的错不是算术，是**口径漂移**：
客单价用含退货单的订单数、GMV删了退货行、ARPU和客单价混着叫。
本工具把口径写成YAML声明，任何数字进来都按声明独立重算核对。

## 用法

```python
from metric_dict import MetricDict
md = MetricDict("metrics.yaml")
r = md.check("aov", computed_value=374.11, df=df)   # 传别人算的数进来
# r = {"ok": False, "expected(按口径重算)": 447.88, ...}
```

```bash
python metric_dict.py   # 演示：正确的GMV通过校验，故意传错的AOV被拦截
```

## 演示实跑（2026-09-20，54万行真实数据）

```
== 指标口径校验演示 ==
  gmv: ✓一致  口径重算=8300065.81 vs 传入=8300065.814
  aov: ✗不一致  口径重算=447.88 vs 传入=374.1128   ← 故意用含退货单订单数算，被拦截
```

## 口径字典（metrics.yaml）

| 指标 | 定义 |
|---|---|
| gmv | 净GMV，退货记负收入不删行 |
| aov | 净GMV ÷ 有购买行为的发票数（退货单不算单） |
| arpu | 净GMV ÷ 客户数（与aov严格区分） |
| return_amount / return_rate | 退货金额 / 退货率 |
| customer_count / order_count | 客户数 / 有购买行为的订单数 |

支持 `requires` 依赖（aov依赖gmv，自动递归计算注入）。

## 接到Agent里

MVP的verify工具可加载此字典：Agent报出结论前，先对涉及指标跑 `md.check`，
不一致直接拒绝输出——这是「评估集之外」的第二道口径防线。

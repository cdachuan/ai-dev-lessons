# -*- coding: utf-8 -*-
"""变式1生成器：从 tools.py 程序化生成埋错版。

埋 8 处 bug，全部是真实数据分析里会踩的口径/逻辑错。
用户任务：修到「变式验收_check.py」对埋错版全部 PASS（与原版行为一致）。
"""
from pathlib import Path

SRC = Path(__file__).parent.parent / "tools.py"
DST = Path(__file__).parent / "变式1_tools_埋错版.py"

# (旧串, 新串, bug说明) —— 每条必须在原文件恰好出现1次
MUTATIONS = [
    ('df = pd.read_csv(path, usecols=usecols, encoding="utf-8-sig")',
     'df = pd.read_csv(path, usecols=usecols, encoding="gbk")',
     "编码错误：UTF-8文件按GBK读，中文/特殊字符变乱码"),
    ('df = df[df["UnitPrice"] > 0]',
     'df = df[df["UnitPrice"] >= 0]',
     "边界错：免费单(UnitPrice=0)混进来，口径说明写的是>0剔除"),
    ("""        ] = df.loc[
            df["InvoiceNo"].astype(str).str.startswith("C") | (df["Quantity"] < 0),
            "revenue",
        ].abs() * -1""",
     """        ] = df.loc[
            df["InvoiceNo"].astype(str).str.startswith("C") | (df["Quantity"] < 0),
            "revenue",
        ].abs()""",
     "符号错：退货该记负数，丢了*-1，退货变正收入，GMV虚增"),
    ('pos_orders = int(tmp.loc[tmp["Quantity"] > 0, "InvoiceNo"].nunique())',
     'pos_orders = int(tmp.loc[tmp["Quantity"] >= 0, "InvoiceNo"].nunique())',
     "口径错：Quantity=0的单也被数进订单数"),
    ('return_revenue = abs(tmp.loc[is_return, "revenue"].sum())',
     'return_revenue = tmp.loc[is_return, "revenue"].sum()',
     "符号错：退货revenue和为负，忘了abs，退货率算出负数"),
    ('result = getattr(df.groupby(group_col)[value_col], agg)().sort_values(ascending=False)',
     'result = getattr(df.groupby(group_col)[value_col], agg)().sort_values(ascending=True)',
     "排序错：升序+head(top_n)拿到的是倒数N名"),
    ('if max_period.month < 12:',
     'if max_period.month < 0:',
     "逻辑死代码：不完整月份警告永不触发"),
    ('6 - pd.qcut(rfm[col], 5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)',
     'pd.qcut(rfm[col], 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)',
     "方向错：RFM打分方向反了（天数越多分越高），高价值客户被判成低价值"),
]

text = SRC.read_text(encoding="utf-8")
applied = []
for old, new, why in MUTATIONS:
    n = text.count(old)
    assert n == 1, f"锚点出现{n}次（应为1）: {old[:50]}..."
    text = text.replace(old, new)
    applied.append(why)

header = '# -*- coding: utf-8 -*-\n'
# 只保留 coding 行打头；变式说明注入原 docstring 第一行之后（docstring 内不算语句，from __future__ 合法）
lines = text.split("\n")
assert lines[0].startswith("# -*- coding"), "原文件第一行应为 coding 声明"
assert lines[1].startswith('"""'), "第二行应为 docstring 开头"
note = '\n【变式1 · 埋错版（8处bug）】逐个找出并修复，验收 = 变式验收_check.py 对本文件全 PASS。\n【规则】禁止 diff 对照原版偷看——先跑 check 看哪个函数挂，自己读代码定位。\n'
text = header + lines[1] + note + "\n".join(lines[2:])

DST.write_text(text, encoding="utf-8")
print(f"已生成 {DST.name}，埋入 {len(applied)} 处 bug:")
for i, w in enumerate(applied, 1):
    print(f"  {i}. {w}")

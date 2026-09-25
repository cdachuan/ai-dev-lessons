# -*- coding: utf-8 -*-
"""数分工具集：动作固化、数据外置。所有工具返回前过 _to_jsonable。

verify 边界（铁律2）：核验只用独立算法路径复算同一口径，保证自洽不保证正确。
口径对不对，字典说了算（人写）；执行忠实度，verify 说了算。
"""
import json
import pandas as pd
from pathlib import Path

from data_agent.dictionary import col, valid_values, dataset_file, get_dataset_entry
from data_agent.jsonable import _to_jsonable

from data_agent.project import get_project_root  # 运行时解析，禁止模块级调用

_DATA_CACHE: dict = {}


def _load(dataset: str) -> pd.DataFrame:
    """原数据物理只读：加载后只做派生，绝不写回原文件。支持 CSV 和 Excel。"""
    if dataset not in _DATA_CACHE:
        path = dataset_file(dataset)
        if path.suffix.lower() == ".csv":
            _DATA_CACHE[dataset] = pd.read_csv(path)
        else:
            _DATA_CACHE[dataset] = pd.read_excel(path)
    return _DATA_CACHE[dataset].copy()  # 永远给副本，原表不可变


# ---------- 工具 1：机械画像 ----------
def profile_data(dataset: str) -> dict:
    """机械画像：shape/列类型/缺失/nunique/describe。LLM 读卡片不读原始数据。"""
    import yaml
    entry_full = get_dataset_entry(dataset)
    df = _load(dataset)
    card = {
        "dataset": dataset,
        "dict_file": entry_full.get("_dict_file"),
        "desc": entry_full.get("desc"),
        "target": entry_full.get("target"),
        "shape": list(df.shape),
        "columns": {},
    }
    for c in df.columns:
        card["columns"][c] = {
            "dtype": str(df[c].dtype),
            "missing": int(df[c].isna().sum()),
            "nunique": int(df[c].nunique()),
            "sample": _to_jsonable(df[c].dropna().head(3).tolist()),
        }
    num_cols = df.select_dtypes("number").columns.tolist()
    if num_cols:
        card["describe"] = _to_jsonable(df[num_cols].describe().round(3).to_dict())
    return _to_jsonable(card)


# ---------- 工具 2：分组聚合（列名/取值从字典查，不写死） ----------
def groupby_sum(dataset: str, group_col: str, value_col: str, filter_col: str = None, filter_value: str = None) -> dict:
    """按 group_col 聚合 value_col 求和，可选先按 filter_col=filter_value 过滤。"""
    df = _load(dataset)
    g = col(dataset, group_col)
    v = col(dataset, value_col)
    if filter_col is not None:
        f = col(dataset, filter_col)
        if filter_value is None:
            raise ValueError("给了 filter_col 就必须给 filter_value")
        vv = valid_values(dataset, filter_col)
        if vv and filter_value not in vv:
            raise ValueError(f"'{filter_value}' 不在 {filter_col} 的有效值里: {vv}。口径不清就停下问人。")
        df = df[df[f] == filter_value]
    result = df.groupby(g)[v].sum().sort_values(ascending=False)
    return _to_jsonable({"group_col": g, "value_col": v, "filter": f"{f}=={filter_value}" if filter_col else None, "result": result})


# ---------- 工具 2b：泛化聚合（2026-09-22 覆盖率评测驱动：35%→60%） ----------
_AGG_WHITELIST = {"sum", "mean", "count", "nunique", "std", "min", "max"}

def _prepare_agg_df(dataset: str, date_grain: str | None):
    """日期粒度派生列：给 _load 出的 df 加 _period 分组列。非侵入，原表只读。"""
    df = _load(dataset)
    if date_grain:
        if date_grain not in {"day", "month", "week"}:
            raise ValueError(f"date_grain 只支持 day/month/week，收到: {date_grain}")
        date_col = None
        for c in df.columns:
            if c.lower() in {"order_date", "date", "created_at", "invoice_date"} or "日期" in str(c):
                date_col = c
                break
        if date_col is None:
            raise ValueError("date_grain 需要日期列（order_date/date/created_at），数据集里没找到")
        dt = pd.to_datetime(df[date_col], errors="coerce")
        if date_grain == "day":
            df["_period"] = dt.dt.strftime("%Y-%m-%d")
        elif date_grain == "month":
            df["_period"] = dt.dt.strftime("%Y-%m")
        else:
            df["_period"] = dt.dt.strftime("%G-W%V")  # ISO 周
    return df


def _nan_aware_diff(expected_val, manual_val) -> bool:
    """NaN-aware 比较：任一侧为 NaN/None → 视为 mismatch（绝不静默 pass）。"""
    import math
    if expected_val is None or manual_val is None:
        return True
    try:
        e, m = float(expected_val), float(manual_val)
    except (TypeError, ValueError):
        return True
    if math.isnan(e) or math.isnan(m) or math.isinf(e) or math.isinf(m):
        return True
    return abs(e - m) > 0.01


def _apply_filter(df: pd.DataFrame, dataset: str, col_name: str, value, op: str):
    """统一过滤：eq 走字典 valid_values 口径拦截；数值比较不查 valid_values。"""
    if op not in {"eq", "gt", "lt", "gte", "lte"}:
        raise ValueError(f"filter_op 只支持 eq/gt/lt/gte/lte，收到: {op}")
    c = col(dataset, col_name)
    if op == "eq":
        vv = valid_values(dataset, col_name)
        if vv and value not in vv:
            raise ValueError(f"'{value}' 不在 {col_name} 的有效值里: {vv}。口径不清就停下问人。")
        return df[df[c] == value]
    # 数值比较：目标列必须可数值化，否则显式报错（不静默 coerce）
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"filter_op={op} 需要数值型 filter_value，收到: {value}")
    import math
    if math.isnan(num) or math.isinf(num):
        raise ValueError(f"filter_value 非法（nan/inf）: {value}")
    s = pd.to_numeric(df[c], errors="coerce")
    if s.isna().all() and not df[c].isna().all():
        raise ValueError(
            f"过滤列 '{c}' 不是数值列（to_numeric 全部失败），对文本列做 {op} 比较是口径错误。"
            f"请确认列名或改用 eq+valid_values。")
    mask = {"gt": s > num, "lt": s < num, "gte": s >= num, "lte": s <= num}[op]
    filtered = df[mask.fillna(False)]
    if len(filtered) == 0 and len(df) > 0:
        raise ValueError(
            f"过滤条件 '{c} {op} {value}' 把全部 {len(df)} 行都过滤掉了——大概率是阈值或列名错误，"
            f"拒绝返回空结果。若确属正常无数据，请调整条件。")
    return filtered


def groupby_agg(dataset: str, group_col: str = None, value_col: str = None,
                agg: str = "sum", top_n: int = None,
                date_grain: str = None,
                filter_col: str = None, filter_value: str = None, filter_op: str = "eq",
                filter2_col: str = None, filter2_value=None, filter2_op: str = "eq") -> dict:
    """泛化分组聚合：agg ∈ sum/mean/count/nunique/std/min/max，可选 TopN 与日期粒度。

    口径拦截与 groupby_sum 同源：列名/过滤值查字典，不合法直接拒。
    count 不需要 value_col；date_grain 给了就以时间桶为分组列（group_col 可省）。
    """
    if agg not in _AGG_WHITELIST:
        raise ValueError(f"agg 只支持 {sorted(_AGG_WHITELIST)}，收到: {agg}")
    if date_grain is None and group_col is None:
        raise ValueError("group_col 与 date_grain 至少给一个")
    df = _prepare_agg_df(dataset, date_grain)

    if date_grain:
        g = "_period"
    else:
        g = col(dataset, group_col)

    # 过滤对全部 agg 生效（含 count）——放在聚合分支之前
    if filter_col is not None:
        if filter_value is None:
            raise ValueError("给了 filter_col 就必须给 filter_value")
        df = _apply_filter(df, dataset, filter_col, filter_value, filter_op)
    if filter2_col is not None:
        if filter2_value is None:
            raise ValueError("给了 filter2_col 就必须给 filter2_value")
        df = _apply_filter(df, dataset, filter2_col, filter2_value, filter2_op)

    if agg == "count":
        result = df.groupby(g).size()
    else:
        if value_col is None:
            raise ValueError(f"agg={agg} 需要 value_col")
        v = col(dataset, value_col)
        result = getattr(df.groupby(g)[v], agg)()

    result = result.sort_values(ascending=False)
    if top_n:
        result = result.head(int(top_n))
    return _to_jsonable({
        "group_col": g,
        "value_col": value_col,
        "agg": agg,
        "top_n": top_n,
        "date_grain": date_grain,
        "filter": f"{filter_col}=={filter_value}" if filter_col else None,
        "result": result,
    })


# ---------- 工具 3：verify 双路径核验（泛化版，覆盖 sum/mean/count） ----------
def verify_groupby_sum(dataset: str, group_col: str, value_col: str, expected: dict, filter_col: str = None, filter_value: str = None) -> dict:
    """独立算法路径复算：布尔索引+手动分组 vs groupby。一致才放行。"""
    df = _load(dataset)
    g = col(dataset, group_col)
    v = col(dataset, value_col)
    if filter_col is not None:
        f = col(dataset, filter_col)
        df = df[df[f] == filter_value]

    # 路径 B：不用 groupby，用 dict 手动累加
    manual = {}
    for _, row in df.iterrows():
        k = row[g]
        manual[k] = manual.get(k, 0) + float(row[v])
    manual = {k: round(x, 6) for k, x in manual.items()}

    mismatches = {k: {"groupby": expected.get(k), "manual": manual.get(k)}
                  for k in set(expected) | set(manual)
                  if abs((expected.get(k) or 0) - manual.get(k, 0)) > 0.01}
    return _to_jsonable({
        "pass": len(mismatches) == 0,
        "method": "groupby vs 布尔索引+dict累加（独立路径）",
        "mismatches": mismatches,
    })


def verify_groupby_agg(dataset: str, group_col: str = None, value_col: str = None, agg: str = "sum", expected: dict = None,
                       date_grain: str = None, top_n: int = None,
                       filter_col: str = None, filter_value: str = None, filter_op: str = "eq",
                       filter2_col: str = None, filter2_value=None, filter2_op: str = "eq") -> dict:
    """泛化核验卡口：独立路径复算全部 agg（与 groupby_agg 同参数）。

    独立性设计：不复用 groupby 的任何聚合接口——
    - count：手动按行计数（不用 .size()）
    - sum/mean：手动逐行累加/相除
    - min/max：逐行比较维护当前极值
    - nunique：手动集合去重
    - std：手动 Σ(x-μ)²/(n-1) 开方（样本标准差，与 pandas 默认 ddof=1 对齐）
    - NaN 行为：sum/mean 跳过 NaN（与 pandas skipna 对齐），但该组有效计数为 0 时
      该组判 mismatch（数据不完整不能当正常通过）
    - 组键统一转 str，避免数值分组列 str vs numpy int 假警报
    """
    df = _prepare_agg_df(dataset, date_grain)
    g = "_period" if date_grain else col(dataset, group_col)

    # 核验层过滤复用 _apply_filter（口径拦截逻辑同源，但不复用聚合结果）
    if filter_col is not None:
        df = _apply_filter(df, dataset, filter_col, filter_value, filter_op)
    if filter2_col is not None:
        df = _apply_filter(df, dataset, filter2_col, filter2_value, filter2_op)

    import math
    manual = {}
    if agg == "count":
        for k in df[g]:
            manual[str(k)] = manual.get(str(k), 0) + 1
    elif agg in ("sum", "mean"):
        sums, cnts, nan_groups = {}, {}, set()
        for _, row in df.iterrows():
            k = str(row[g])
            raw = row[value_col]
            try:
                val = float(raw)
            except (TypeError, ValueError):
                val = math.nan
            if math.isnan(val):
                nan_groups.add(k)  # NaN 不计入 sum/mean（与 pandas skipna 对齐），但留痕
                continue
            sums[k] = sums.get(k, 0) + val
            cnts[k] = cnts.get(k, 0) + 1
        manual = sums if agg == "sum" else {k: sums[k] / cnts[k] for k in sums}
        # 组内全部是 NaN → 该组数据不完整，直接判 mismatch（不给错误数字盖 pass）
        all_keys = set(str(k) for k in df[g].unique())
        for k in all_keys:
            if k in nan_groups and k not in sums:
                manual[k] = math.nan  # 强制 NaN → 比较时必 mismatch
    elif agg in ("min", "max"):
        cmp = (lambda a, b: a < b) if agg == "min" else (lambda a, b: a > b)
        for _, row in df.iterrows():
            k = str(row[g])
            try:
                val = float(row[value_col])
            except (TypeError, ValueError):
                continue  # NaN 不参与极值（与 pandas skipna 对齐）
            if math.isnan(val):
                continue
            if k not in manual or cmp(val, manual[k]):
                manual[k] = val
    elif agg == "nunique":
        seen = {}
        for _, row in df.iterrows():
            k = str(row[g])
            seen.setdefault(k, set()).add(str(row[value_col]))
        manual = {k: float(len(v)) for k, v in seen.items()}
    elif agg == "std":
        buckets = {}
        for _, row in df.iterrows():
            k = str(row[g])
            try:
                val = float(row[value_col])
            except (TypeError, ValueError):
                continue
            if math.isnan(val):
                continue
            buckets.setdefault(k, []).append(val)
        for k, vals in buckets.items():
            n = len(vals)
            if n < 2:
                manual[k] = 0.0  # pandas 对单值组返回 NaN；核验侧判 0 并标 note
            else:
                mu = sum(vals) / n
                manual[k] = math.sqrt(sum((x - mu) ** 2 for x in vals) / (n - 1))
    else:
        raise ValueError(f"verify 不支持 agg={agg}（白名单外），拒绝复算")

    manual = {k: round(x, 6) if not (isinstance(x, float) and math.isnan(x)) else x
              for k, x in manual.items()}
    if not isinstance(expected, dict):
        raise ValueError("expected 必填（传 groupby_agg 返回的 result 字典）")
    # TopN 语义：核验永远在全量口径上做；expected 是截断视图，只核对其中出现的组
    mismatches = {}
    for k in set(expected):
        mv = manual.get(k)
        if _nan_aware_diff(expected.get(k), mv):
            mismatches[k] = {"groupby": expected.get(k), "manual": mv}

    # top_n 语义一致性：expected 组数不得超过 top_n
    if top_n and len(expected) > int(top_n):
        mismatches["_top_n_semantics"] = {"groupby": f"{len(expected)}组", "manual": f"应≤{top_n}组"}

    return _to_jsonable({
        "pass": len(mismatches) == 0,
        "method": f"groupby.{agg} vs 手动{'计数' if agg=='count' else '累加' if agg=='sum' else '相除' if agg=='mean' else '极值维护' if agg in ('min','max') else '集合去重' if agg=='nunique' else 'Σ(x-μ)²公式'}（独立路径）",
        "agg": agg,
        "mismatches": mismatches,
    })


# ---------- 工具 2c：透视表（v3 覆盖率驱动：透视3题缺口） ----------
def pivot_table(dataset: str, index_col: str, columns_col: str, value_col: str,
                agg: str = "sum", date_grain: str = None,
                filter_col: str = None, filter_value: str = None) -> dict:
    """二维交叉透视：index_col 行 × columns_col 列，值=agg 聚合。

    列名/过滤值查字典拦截；date_grain 可让行维度为时间桶（如每月各品类对比）。
    返回 table（嵌套字典）+ row_totals/col_totals 供图表联动。
    """
    if agg not in _AGG_WHITELIST:
        raise ValueError(f"agg 只支持 {sorted(_AGG_WHITELIST)}，收到: {agg}")
    df = _prepare_agg_df(dataset, date_grain)

    # 行维度：date_grain 给了就以时间桶为行，否则查字典
    idx = "_period" if date_grain else col(dataset, index_col)
    cols_name = col(dataset, columns_col)
    v = col(dataset, value_col)

    if filter_col is not None:
        f = col(dataset, filter_col)
        if filter_value is None:
            raise ValueError("给了 filter_col 就必须给 filter_value")
        vv = valid_values(dataset, filter_col)
        if vv and filter_value not in vv:
            raise ValueError(f"'{filter_value}' 不在 {filter_col} 的有效值里: {vv}。口径不清就停下问人。")
        df = df[df[f] == filter_value]

    if agg == "count":
        pt = df.pivot_table(index=idx, columns=cols_name, values=v, aggfunc="size", fill_value=0)
    else:
        # 不用 fill_value=0：稀疏组合的空格保持 NaN → 序列化为 None，
        # 语义是"该组合无数据"，不让它伪装成"0 元"的伪结论
        pt = df.pivot_table(index=idx, columns=cols_name, values=v, aggfunc=agg)

    pt = pt.sort_index()
    table = {}
    for i, row in pt.iterrows():
        table[str(i)] = {str(c): (None if pd.isna(x) else round(float(x), 2)) for c, x in row.items()}
    row_totals = {str(i): (None if pd.isna(row.sum()) else round(float(row.sum()), 2)) for i, row in pt.iterrows()}
    col_totals = {str(c): (None if pd.isna(pt[c].sum()) else round(float(pt[c].sum()), 2)) for c in pt.columns}
    return _to_jsonable({
        "index": idx, "columns": cols_name, "value_col": v, "agg": agg,
        "filter": f"{filter_col}=={filter_value}" if filter_col else None,
        "table": table, "row_totals": row_totals, "col_totals": col_totals,
    })


def verify_pivot_table(dataset: str, index_col: str, columns_col: str, value_col: str,
                       agg: str = "sum", date_grain: str = None,
                       filter_col: str = None, filter_value: str = None, expected: dict = None) -> dict:
    """透视核验：独立路径 = 手动双重分组，按 agg 语义分别复算。

    - sum/count：累加
    - mean：sum/cnt 相除
    - min/max：极值维护
    - nunique：集合去重
    空格子（expected 值为 None）语义 = 无数据，核验侧确认 manual 也没有该格 → 一致，不报错。
    """
    import math
    df = _prepare_agg_df(dataset, date_grain)
    idx = "_period" if date_grain else col(dataset, index_col)
    cols_name = col(dataset, columns_col)
    if filter_col is not None:
        f = col(dataset, filter_col)
        df = df[df[f] == filter_value]

    # 路径 B：手动双重分组（agg 语义各自实现，不调 pivot_table/groupby 接口）
    cells, row_totals, cell_lists = {}, {}, {}
    for _, row in df.iterrows():
        k, c = str(row[idx]), str(row[cols_name])
        cells.setdefault((k, c), []).append(row)
        cell_lists.setdefault((k, c), []).append(row)

    def _agg_vals(rows):
        if agg == "count":
            return float(len(rows))
        vals = []
        for r in rows:
            try:
                x = float(r[value_col])
                if not math.isnan(x):
                    vals.append(x)
            except (TypeError, ValueError):
                pass
        if agg == "sum":
            return sum(vals) if vals else math.nan
        if agg == "mean":
            return sum(vals) / len(vals) if vals else math.nan
        if agg == "min":
            return min(vals) if vals else math.nan
        if agg == "max":
            return max(vals) if vals else math.nan
        if agg == "nunique":
            return float(len({str(r[value_col]) for r in rows
                              if not (lambda v: v is None or (isinstance(v, float) and math.isnan(v)))( _try_float(r[value_col]))}))
        raise ValueError(f"verify_pivot_table 不支持 agg={agg}")

    def _try_float(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    mismatches = {}
    exp_table = expected.get("table", {}) if expected else None
    if exp_table is None:
        raise ValueError("expected 必填（传 pivot_table 的返回整体）")
    for i, colrow in exp_table.items():
        for c, val in colrow.items():
            rows = cells.get((str(i), str(c)))
            if val is None:
                # expected 声明无数据 → manual 也应无数据
                if rows:
                    mismatches[f"{i}|{c}"] = {"groupby": None, "manual": round(_agg_vals(rows), 6)}
                continue
            if not rows:
                mismatches[f"{i}|{c}"] = {"groupby": val, "manual": None}
                continue
            mv = _agg_vals(rows)
            if _nan_aware_diff(val, mv):
                mismatches[f"{i}|{c}"] = {"groupby": val, "manual": None if (isinstance(mv, float) and math.isnan(mv)) else round(mv, 6)}

    # 行总计核对（sum/count）
    if agg in ("sum", "count"):
        for i, tv in (expected.get("row_totals") or {}).items():
            if tv is None:
                continue
            keys = [k for k in cells if k[0] == str(i)]
            if not keys:
                mismatches[f"row_total|{i}"] = {"groupby": tv, "manual": None}
                continue
            all_rows = [r for k in keys for r in cells[k]]
            mv = _agg_vals(all_rows)
            if _nan_aware_diff(tv, mv):
                mismatches[f"row_total|{i}"] = {"groupby": tv, "manual": round(mv, 6)}

    return _to_jsonable({
        "pass": len(mismatches) == 0,
        "method": f"pivot_table vs 手动双重分组·{_agg_vals.__name__ and agg}语义（独立路径）",
        "agg": agg,
        "mismatches": mismatches,
    })


# ---------- 工具 2d：双期对比（环比缺口4题） ----------
def trend_compare(dataset: str, value_col: str, agg: str = "sum",
                  date_grain: str = "month", periods: int = 2,
                  filter_col: str = None, filter_value: str = None) -> dict:
    """时间双期对比：最近 periods 个时间桶的指标值+相邻期变化率。

    返回 series（各期值）+ change（最近一期 vs 上一期的绝对差和百分比）。
    独立于 groupby_agg 的点：change 计算在核验层复算，且各期值本身走 verify。
    """
    if date_grain not in {"day", "month", "week"}:
        raise ValueError(f"date_grain 只支持 day/month/week，收到: {date_grain}")
    r = groupby_agg(dataset, value_col=value_col, agg=agg, date_grain=date_grain,
                    filter_col=filter_col, filter_value=filter_value)
    series = r["result"]  # 已降序，按时间正序排列供对比
    ordered = dict(sorted(series.items()))
    latest = list(ordered.items())[-periods:]
    if len(latest) < 2:
        return _to_jsonable({"series": ordered, "change": None,
                             "note": "时间桶不足2个，无法计算环比"})

    (p1_name, p1_val), (p2_name, p2_val) = latest[-1], latest[-2]
    diff = round(p1_val - p2_val, 2)
    pct = round((p1_val - p2_val) / abs(p2_val) * 100, 2) if p2_val else None
    return _to_jsonable({
        "series": ordered,
        "change": {"prev_period": p2_name, "prev_value": p2_val,
                   "latest_period": p1_name, "latest_value": p1_val,
                   "diff": diff, "pct": pct, "direction": "up" if diff > 0 else "down" if diff < 0 else "flat"},
    })


def verify_trend_compare(dataset: str, value_col: str, agg: str = "sum",
                         date_grain: str = "month", periods: int = 2,
                         filter_col: str = None, filter_value: str = None, expected: dict = None) -> dict:
    """双期核验：各期值独立复算 + change 百分比手写公式复算。"""
    df = _prepare_agg_df(dataset, date_grain)
    if filter_col is not None:
        f = col(dataset, filter_col)
        df = df[df[f] == filter_value]
    g = "_period"
    if agg == "count":
        # count 路径：只按行计数，不触碰 value 列
        cnts = {}
        for k in df[g]:
            k = str(k)
            cnts[k] = cnts.get(k, 0) + 1
        manual = cnts
    else:
        v = col(dataset, value_col)
        sums, cnts = {}, {}
        for _, row in df.iterrows():
            k = str(row[g])
            sums[k] = sums.get(k, 0) + float(row[v])
            cnts[k] = cnts.get(k, 0) + 1
        if agg == "sum":
            manual = sums
        elif agg == "mean":
            manual = {k: sums[k] / cnts[k] for k in sums}
        else:
            manual = {k: sums[k] for k in sums}  # 其余 agg 的环比不支持（见 schema 白名单）

    mismatches = {}
    exp_series = (expected or {}).get("series")
    if exp_series is None:
        raise ValueError("expected 必填（传 trend_compare 的返回整体）")
    for k, val in exp_series.items():
        mv = manual.get(k)
        if _nan_aware_diff(val, mv):
            mismatches[k] = {"groupby": val, "manual": mv}

    # change 全面核验：期名不存在=报错（不是跳过）；diff/pct/direction 全复算
    ch = (expected or {}).get("change")
    if ch is None:
        # 单期数据返回 change=None 是合法的；但数据明明≥2个桶却缺 change = 异常
        if len(manual) >= 2 and (expected or {}).get("note") is None:
            mismatches["_change_missing"] = {"groupby": None, "manual": "数据≥2期但返回缺 change"}
    else:
        p2_name, p1_name = ch.get("prev_period"), ch.get("latest_period")
        p2, p1 = manual.get(p2_name), manual.get(p1_name)
        if p2 is None:
            mismatches["_change_prev_period"] = {"groupby": p2_name, "manual": f"复算结果中不存在该期，现有: {sorted(manual)[-3:]}"}
        elif p1 is None:
            mismatches["_change_latest_period"] = {"groupby": p1_name, "manual": f"复算结果中不存在该期，现有: {sorted(manual)[-3:]}"}
        else:
            man_diff = round(p1 - p2, 2)
            if _nan_aware_diff(ch.get("diff"), man_diff):
                mismatches["_change_diff"] = {"groupby": ch.get("diff"), "manual": man_diff}
            man_pct = round((p1 - p2) / abs(p2) * 100, 2) if p2 else None
            if _nan_aware_diff(ch.get("pct"), man_pct):
                mismatches["_change_pct"] = {"groupby": ch.get("pct"), "manual": man_pct}
            exp_dir = ch.get("direction")
            man_dir = "up" if man_diff > 0 else "down" if man_diff < 0 else "flat"
            if exp_dir != man_dir:
                mismatches["_change_direction"] = {"groupby": exp_dir, "manual": man_dir}
            # 期值本身也要对上 change 里记录的值
            if _nan_aware_diff(ch.get("prev_value"), p2):
                mismatches["_change_prev_value"] = {"groupby": ch.get("prev_value"), "manual": p2}
            if _nan_aware_diff(ch.get("latest_value"), p1):
                mismatches["_change_latest_value"] = {"groupby": ch.get("latest_value"), "manual": p1}

    return _to_jsonable({
        "pass": len(mismatches) == 0,
        "method": "trend_compare vs 手动累加+diff/pct/direction全复算（独立路径）",
        "mismatches": mismatches,
    })

TOOL_REGISTRY = {
    "profile_data": profile_data,
    "groupby_sum": groupby_sum,
    "groupby_agg": groupby_agg,
    "pivot_table": pivot_table,
    "trend_compare": trend_compare,
    "verify_groupby_sum": verify_groupby_sum,
    "verify_groupby_agg": verify_groupby_agg,
    "verify_pivot_table": verify_pivot_table,
    "verify_trend_compare": verify_trend_compare,
}

# 给 LLM 看的说明书：description 写「什么时候用」，不只写功能
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "profile_data",
            "description": "对数据集做机械画像，返回 shape/列类型/缺失/基数/数值分布。任何分析开始前必须先调用它了解全貌，不要直接读原始数据。",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string", "description": "数据集名，必须在 dictionary.yaml 里注册"}},
                "required": ["dataset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "groupby_sum",
            "description": "分组求和。当问题形如「按X分组统计Y之和/总额」时用。列名用字典里的逻辑名，不要自己猜物理列名；过滤取值必须用字典 valid_values 里的值，口径不清就拒绝回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "group_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "filter_col": {"type": "string", "description": "可选，过滤列"},
                    "filter_value": {"type": "string", "description": "可选，过滤值，必须来自字典 valid_values"},
                },
                "required": ["dataset", "group_col", "value_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "groupby_agg",
            "description": "泛化分组聚合。当问题涉及求平均(mean)/计数(count)/去重数(nunique)/波动(std)/最值(min/max)、要TopN（最高/最低N个）、或按时间粒度分组（每天/每月/每周）时用——groupby_sum 只能求和，这些一律走本工具。列名用字典逻辑名；过滤取值必须来自字典 valid_values。count 时 value_col 可省略；date_grain 给了就不用再传 group_col 的时间列。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "group_col": {"type": "string", "description": "分组列（date_grain 给出时可不传）"},
                    "value_col": {"type": "string", "description": "聚合值列，agg=count 时可省略"},
                    "agg": {"type": "string", "enum": ["sum", "mean", "count", "nunique", "std", "min", "max"], "description": "聚合方式，默认 sum"},
                    "top_n": {"type": "integer", "description": "取前N名（结果已按值降序），如'最高的5个省份'传5"},
                    "date_grain": {"type": "string", "enum": ["day", "month", "week"], "description": "按时间粒度分组（每天/每月/每周），给了则以时间桶为分组列"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                    "filter_op": {"type": "string", "enum": ["eq", "gt", "lt", "gte", "lte"], "description": "过滤方式：eq等于(默认)/gt大于/lt小于/gte大于等于/lte小于等于。数值区间过滤时用gt/lt"},
                    "filter2_col": {"type": "string", "description": "第二过滤列（双条件AND）"},
                    "filter2_value": {"type": "string"},
                    "filter2_op": {"type": "string", "enum": ["eq", "gt", "lt", "gte", "lte"]},
                },
                "required": ["dataset", "agg"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_groupby_sum",
            "description": "核验卡口：对 groupby_sum 的结果做双路径复算，必须核对。每次调用 groupby_sum 后必须紧接着用它的结果调用本工具，pass=false 时不得把结果当作结论输出。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "group_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "expected": {"type": "object", "description": "groupby_sum 返回的 result 字典原样传入"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                },
                "required": ["dataset", "group_col", "value_col", "expected"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_trend_compare",
            "description": "核验卡口（双期对比）：对 trend_compare 的结果做独立复算。每次调用 trend_compare 后必须紧接着用相同参数+其返回整体调本工具（expected=返回的dict原样），pass=true 才能输出结论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "value_col": {"type": "string"},
                    "agg": {"type": "string", "enum": ["sum", "mean", "count"]},
                    "date_grain": {"type": "string", "enum": ["day", "month", "week"]},
                    "expected": {"type": "object", "description": "trend_compare 返回的 dict 原样传入"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                },
                "required": ["dataset", "value_col", "expected"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pivot_table",
            "description": "二维交叉透视表。当问题形如「各X在各Y的Z分布/对比/矩阵」时用（如各品类在各渠道的销售额）。date_grain 可让行维度为时间桶（每月各品类对比）。算完必须调 verify_pivot_table 核验。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "index_col": {"type": "string", "description": "行维度列"},
                    "columns_col": {"type": "string", "description": "列维度列"},
                    "value_col": {"type": "string"},
                    "agg": {"type": "string", "enum": ["sum", "mean", "count", "nunique", "min", "max"]},
                    "date_grain": {"type": "string", "enum": ["day", "month", "week"], "description": "给了则以时间桶为行维度"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                },
                "required": ["dataset", "index_col", "columns_col", "value_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_pivot_table",
            "description": "核验卡口（透视表）：对 pivot_table 的结果做手动双重分组复算。每次调用 pivot_table 后必须紧接着用相同参数+其返回整体调本工具（expected=返回的dict原样），pass=true 才能输出结论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "index_col": {"type": "string"},
                    "columns_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "agg": {"type": "string", "enum": ["sum", "mean", "count", "nunique", "min", "max"]},
                    "date_grain": {"type": "string", "enum": ["day", "month", "week"]},
                    "expected": {"type": "object"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                },
                "required": ["dataset", "index_col", "columns_col", "value_col", "expected"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trend_compare",
            "description": "时间双期对比/环比。当问题形如「这个月比上个月增长了多少」「销售额环比怎么样」时用。返回最近几期的值+变化方向和百分比。算完必须调 verify_trend_compare 核验。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "value_col": {"type": "string"},
                    "agg": {"type": "string", "enum": ["sum", "mean", "count"]},
                    "date_grain": {"type": "string", "enum": ["day", "month", "week"], "description": "对比粒度：月环比month、周环比week，默认month"},
                    "periods": {"type": "integer", "description": "对比期数，默认2（本期vs上期）"},
                    "filter_col": {"type": "string"},
                    "filter_value": {"type": "string"},
                },
                "required": ["dataset", "value_col"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    """执行工具，错误也返回给 AI 继续推理，不炸循环。"""
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": f"未知工具 {name}，可用: {list(TOOL_REGISTRY)}"}, ensure_ascii=False)
    try:
        return json.dumps(TOOL_REGISTRY[name](**args), ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

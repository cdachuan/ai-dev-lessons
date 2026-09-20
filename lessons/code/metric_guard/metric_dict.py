# -*- coding: utf-8 -*-
"""指标口径字典 + 校验器（可复用工具）

思想：口径用YAML声明一次，计算与校验都从同一份定义出发——
「把口径做进工具层」的产品化。

用法：
    from metric_dict import MetricDict
    md = MetricDict('metrics.yaml')
    result = md.check('gmv', computed_value=8300065.81, df=df)
"""
from pathlib import Path
import pandas as pd
import yaml


class MetricDict:
    def __init__(self, yaml_path: str | Path):
        p = Path(yaml_path)
        if not p.exists():
            raise FileNotFoundError(f"口径字典不存在: {p}")
        self.defs = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("metrics", {})

    def list_metrics(self) -> list[str]:
        return list(self.defs.keys())

    def get(self, name: str) -> dict:
        if name not in self.defs:
            raise KeyError(f"口径字典中没有指标: {name}，可用: {self.list_metrics()}")
        return self.defs[name]

    def compute(self, name: str, df: pd.DataFrame) -> float:
        """按字典定义的公式计算指标（公式=python表达式，变量为df和列名）。

        依赖指标（requires）先递归算出并注入公式环境。
        """
        d = self.get(name)
        env = {"df": df, "pd": pd, "abs": abs, "round": round, "len": len}
        for dep in d.get("requires", []):
            env[dep] = self.compute(dep, df)
        return float(eval(d["formula"], {"__builtins__": {}}, env))  # noqa: S307 口径字典受控

    def check(self, name: str, computed_value: float, df: pd.DataFrame,
              tol: float = 0.01) -> dict:
        """校验：独立重算 vs 传入值。verify思想的口径化。"""
        d = self.get(name)
        try:
            expect = self.compute(name, df)
        except Exception as e:
            return {"ok": False, "metric": name, "error": f"按口径重算失败: {e}"}
        diff = abs(expect - computed_value)
        rel = diff / abs(expect) if expect else diff
        return {
            "ok": rel <= tol,
            "metric": name,
            "definition": d.get("desc", ""),
            "expected(按口径重算)": round(expect, 4),
            "got(传入值)": round(float(computed_value), 4),
            "relative_diff": round(rel, 6),
            "tolerance": tol,
        }

    def check_many(self, computed: dict[str, float], df: pd.DataFrame,
                   tol: float = 0.01) -> dict[str, dict]:
        return {k: self.check(k, v, df, tol) for k, v in computed.items()}


if __name__ == "__main__":
    df = pd.read_csv("D:/学习/ai-dev/data/ecommerce/online_retail_2010_2011.csv",
                     parse_dates=["InvoiceDate"])
    here = Path(__file__).parent
    md = MetricDict(here / "metrics.yaml")
    # 模拟"别人算出来的数"来演示校验：一个对、一个错
    clean = df[df.CustomerID.notna() & (df.UnitPrice > 0)].copy()
    clean["rev"] = clean.Quantity * clean.UnitPrice
    gmv_right = clean.rev.sum()
    aov_wrong = gmv_right / 22186  # 用含退货单的订单数（曾犯过的口径错误）
    print("== 指标口径校验演示 ==")
    for name, val in {"gmv": gmv_right, "aov": aov_wrong}.items():
        r = md.check(name, val, clean)
        flag = "✓一致" if r["ok"] else "✗不一致"
        print(f"  {name}: {flag}  口径重算={r['expected(按口径重算)']} vs 传入={r['got(传入值)']}")

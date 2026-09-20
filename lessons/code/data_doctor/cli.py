# -*- coding: utf-8 -*-
"""data_doctor 命令行入口: python cli.py <csv> [--full|--outliers col --method iqr]"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from doctor import profile, quality_report, outliers, suggest_clean, full_check, _fmt


def main():
    ap = argparse.ArgumentParser(description="数据体检器 · 任意CSV一键诊断")
    ap.add_argument("csv", help="CSV 文件路径")
    ap.add_argument("--full", action="store_true", help="一键全检（默认）")
    ap.add_argument("--outliers", metavar="COL", help="对指定列做异常检测")
    ap.add_argument("--method", default="iqr", choices=["iqr", "zscore"])
    args = ap.parse_args()

    if args.outliers:
        print(_fmt(outliers(args.csv, args.outliers, args.method)))
    else:
        r = full_check(args.csv)["data"]
        print("=" * 50)
        print("数据体检报告")
        print("=" * 50)
        p = r["画像"]
        print(f"\n[画像] {p['行数']:,} 行 × {p['列数']} 列, {p['内存MB']} MB")
        print("\n[质量问题]")
        for i in r["质量问题"]["issues"] or ["未见明显问题"]:
            print("  -", i)
        print("\n[清洗建议]")
        for s in r["清洗建议"]["建议"]:
            print("  -", s)
        print(f"\n[健康分] {r['健康分']}/100")


if __name__ == "__main__":
    main()

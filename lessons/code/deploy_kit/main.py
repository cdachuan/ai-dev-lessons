"""
入口脚本 —— 交付模板示例

本文件只做三件事：读配置 → 跑逻辑 → 打印结果。
业务逻辑（读数据、汇总、结论）都放在函数里，入口保持干净。

配合课程 0036《部署与上线》：这是「可复现仓库」的最小完整形态。
"""

import os
from pathlib import Path

import pandas as pd

# 路径一律用 Path(__file__).parent 定位脚本所在目录，
# 这样别人从任何目录启动都不会找不到数据文件。
BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "sample.csv"


def load_api_key() -> str | None:
    """从环境变量读密钥 —— 永不写死在代码里（课程 35 安全闸①）。

    读不到就返回 None，让调用方决定是提示还是中断。
    真实项目里：把返回 None 视为「配置缺失」，直接报错退出。
    """
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key.strip()
    # 本地开发时允许从 .env 读（.env 不进仓库，见 .gitignore）
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def analyze(path: Path) -> pd.DataFrame:
    """读数据并汇总：按品类统计『已完成』口径的销售额，降序排列。"""
    # 读文件一律写 encoding="utf-8"，否则 Windows 默认编码会让中文变成乱码
    df = pd.read_csv(path, encoding="utf-8")

    done = df[df["状态"] == "已完成"]          # 口径：只看已完成订单
    result = (
        done.groupby("品类")["金额"]
        .sum()
        .sort_values(ascending=False)
        .to_frame("已完成销售额")
    )
    return result


def main() -> None:
    key = load_api_key()
    if key:
        print("[配置] DEEPSEEK_API_KEY 已就绪（值不打印、不回显）")
    else:
        print("[配置] 未找到 DEEPSEEK_API_KEY，跳过 AI 部分（纯数据分析不受影响）")
        print("       修复：copy .env.example .env，填入自己的 key")

    print(f"\n[数据] {DATA_FILE.name}（口径：状态 == 已完成）")
    result = analyze(DATA_FILE)
    print(result.to_string())
    print(f"\n[结论] 已完成销售额最高的是：{result.index[0]}")


if __name__ == "__main__":
    main()

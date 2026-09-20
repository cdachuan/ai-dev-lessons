# -*- coding: utf-8 -*-
"""场景1：HTTP重试与降级 — Agent面对不稳定的外部API。

演示：
  1. timeout 设置（防止无限等待）
  2. raise_for_status（主动发现HTTP错误）
  3. 指数退避重试（最多3次，间隔递增）
  4. 最终失败时优雅降级（返回缓存或None）
"""
from __future__ import annotations

import time
import json
import requests

# ---- 缓存：降级时返回最近一次成功的结果 ----
_cache: dict[str, dict] = {}

# ---- 配置 ----
API_URL = "https://wttr.in/Beijing?format=j1"
TIMEOUT = 5          # 秒
MAX_RETRIES = 3
BACKOFF_BASE = 2     # 指数退避基数（2, 4, 8 ... 秒）


def _log(msg: str) -> None:
    print(f"  [LOG] {msg}")


def fetch_weather() -> dict | None:
    """调用 wttr.in 天气API，带超时/重试/降级。"""
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        _log(f"第 {attempt} 次请求 → {API_URL}")
        try:
            resp = requests.get(API_URL, timeout=TIMEOUT)
            resp.raise_for_status()           # 4xx/5xx 会抛异常
            data = resp.json()
            _cache[API_URL] = data            # 更新缓存
            _log(f"成功！HTTP {resp.status_code}")
            return data

        except requests.exceptions.Timeout:
            _log("超时！服务器响应太慢")
            last_error = TimeoutError("请求超时")
        except requests.exceptions.HTTPError as e:
            _log(f"HTTP错误 {resp.status_code}: {e}")
            last_error = e
        except requests.exceptions.ConnectionError:
            _log("连接失败，网络不可达")
            last_error = ConnectionError("网络不通")
        except requests.exceptions.RequestException as e:
            _log(f"其他请求异常: {e}")
            last_error = e

        # 指数退避等待
        wait = BACKOFF_BASE ** attempt
        _log(f"等待 {wait}s 后重试...")
        time.sleep(wait)

    # ---- 全部失败 → 优雅降级 ----
    _log(f"重试 {MAX_RETRIES} 次均失败，进入降级逻辑")
    if API_URL in _cache:
        _log("返回缓存中的旧数据")
        return _cache[API_URL]
    _log("无缓存可用，返回 None")
    return None


def run_demo() -> None:
    print("=" * 60)
    print("Demo 1: HTTP重试与降级")
    print("=" * 60)

    result = fetch_weather()

    if result:
        # 只展示关键信息
        cur = result.get("current_condition", [{}])[0]
        print(f"\n[结果] 北京当前天气: {cur.get('temp_C', '?')}°C, "
              f"湿度 {cur.get('humidity', '?')}%, "
              f"风速 {cur.get('windspeedKmph', '?')} km/h")
        desc_list = cur.get("lang_zh", cur.get("weather", [{}]))
        if isinstance(desc_list, list) and desc_list:
            print(f"       描述: {desc_list[0].get('value', desc_list[0].get('weatherDesc', [{}])[0].get('value', '未知'))}")
    else:
        print("\n[结果] 降级：返回 None（无缓存、无数据）")

    # ---- 演示：故意请求一个不存在的URL，触发完整重试+降级 ----
    print("\n" + "-" * 60)
    print("演示：请求一个不存在的URL（模拟脏接口）")
    print("-" * 60)
    global API_URL, TIMEOUT
    _orig = API_URL
    API_URL = "https://wttr.in/INVALID_CITY_12345?format=j1&timeout=1"  # 可能返回404或空
    TIMEOUT = 2
    result2 = fetch_weather()
    print(f"\n[结果] 降级返回: {type(result2)}")
    API_URL = _orig  # 恢复


if __name__ == "__main__":
    run_demo()

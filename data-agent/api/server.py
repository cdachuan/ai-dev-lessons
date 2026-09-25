# -*- coding: utf-8 -*-
"""问数 API 网关：大屏/数字人的唯一后端入口。

- POST /ask        同步问数（含 chart_spec 提取）
- POST /ask/stream SSE 流式（预留，数字人边生成边播）
- GET  /summary    大屏指标卡数据（事前/事中/事后三栏）
"""
import json
import re
import time
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from dotenv import load_dotenv

# 项目根：优先 DATA_AGENT_ROOT 环境变量，回退仓库根
import os  # noqa: E402
_REPO_ROOT = Path(__file__).resolve().parent.parent
_root_env = os.environ.get("DATA_AGENT_ROOT")
ROOT = Path(_root_env) if _root_env else _REPO_ROOT
load_dotenv(ROOT / ".env")

from data_agent import DataAgent  # noqa: E402
from data_agent.governance import lookup_library  # noqa: E402

app = FastAPI(title="数分大屏问数 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# BI agent 进程内复用：按 dataset 缓存（不同数据集不同 prompt）
_bi_lock = threading.Lock()
_bi_cache: dict = {}


def _get_bi(dataset: str) -> DataAgent:
    with _bi_lock:
        if dataset not in _bi_cache:
            _bi_cache[dataset] = DataAgent(mode="bi", max_steps=4, dataset=dataset)
        return _bi_cache[dataset]


@app.get("/datasets")
def datasets():
    """大屏数据源下拉：字典里登记的全部数据集。"""
    from data_agent import load_dictionary
    out = [{"name": n, "desc": e.get("desc", ""), "columns": list(e.get("columns", {}).keys())}
           for n, e in load_dictionary().items()]
    return {"datasets": out}


class AskRequest(BaseModel):
    question: str
    dataset: str = "dash_orders"


CHART_RE = re.compile(r"CHART_SPEC:\s*(\{.*\})", re.S)


def _split_answer(reply: str) -> dict:
    """把 BI 三段式回答拆成 answer / caliber / chart_spec。"""
    if not reply:
        return {"answer": "", "caliber": "", "chart_spec": None}
    chart_spec = None
    m = CHART_RE.search(reply)
    if m:
        try:
            chart_spec = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    text = CHART_RE.sub("", reply).strip()
    answer, caliber = text, ""
    m_ans = re.search(r"【答】(.*?)(?=【口径】|$)", text, re.S)
    m_cal = re.search(r"【口径】(.*?)$", text, re.S)
    if m_ans:
        answer = m_ans.group(1).strip()
    if m_cal:
        caliber = m_cal.group(1).strip()
    return {"answer": answer, "caliber": caliber, "chart_spec": chart_spec}


@app.post("/ask")
def ask(req: AskRequest):
    t0 = time.time()
    agent = _get_bi(req.dataset)
    try:
        result = agent.ask(req.question)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "latency": round(time.time() - t0, 2)}
    payload = _split_answer(result.get("reply") or "")
    # 核验徽章：从 trace 提取 verify_groupby_sum 的真实 pass 状态（双路径复算）
    # trace 里 tool result 是 JSON 字符串（execute_tool 返回 str），需先解析
    def _tool_result(name: str):
        for t in reversed(result.get("trace", [])):
            if t.get("name") == name:
                raw = t.get("result")
                if isinstance(raw, str):
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        return None
                return raw if isinstance(raw, dict) else None
        return None

    _verify = _tool_result("verify_groupby_sum")
    verified = _verify.get("pass") if isinstance(_verify, dict) else None
    # 资产复用标记：本次回答是否命中已入库资产（lookup_library 返回 list）
    reused = any(t.get("name") == "lookup_library" and isinstance(t.get("result"), str)
                 and json.loads(t["result"]) for t in result.get("trace", []))
    return {"ok": True, "latency": round(time.time() - t0, 2), "dataset": req.dataset,
            "verified": verified, "asset_hit": reused, **payload}


@app.get("/summary")
def summary():
    """大屏三栏指标卡：直接查资产库+宽表预聚合（离线口径，亚秒）。"""
    import pandas as pd
    from data_agent.dictionary import dataset_file
    df = pd.read_csv(dataset_file("dash_orders"))
    df["order_date"] = pd.to_datetime(df["order_date"])
    today = df["order_date"].max()
    last7 = df[df["order_date"] > today - pd.Timedelta(days=7)]
    prev7 = df[(df["order_date"] > today - pd.Timedelta(days=14)) & (df["order_date"] <= today - pd.Timedelta(days=7))]

    def wow(cur: pd.DataFrame, prev: pd.DataFrame) -> float:
        s_cur, s_prev = cur["amount"].sum(), prev["amount"].sum()
        return round((s_cur - s_prev) / s_prev * 100, 1) if s_prev else 0.0

    by_prov = last7.groupby("province")["amount"].sum().sort_values(ascending=False)
    by_cat = last7.groupby("category")["amount"].sum().sort_values(ascending=False)
    daily = last7.groupby(last7["order_date"].dt.strftime("%m-%d"))["amount"].sum()
    return {
        "kpi": {
            "total_7d": round(float(last7["amount"].sum()), 0),
            "orders_7d": int(len(last7)),
            "wow_pct": wow(last7, prev7),
            "avg_order": round(float(last7["amount"].mean()), 0),
        },
        "region_top": [{"name": k, "value": round(float(v), 0)} for k, v in by_prov.head(8).items()],
        "category": [{"name": k, "value": round(float(v), 0)} for k, v in by_cat.items()],
        "daily_trend": [{"name": k, "value": round(float(v), 0)} for k, v in daily.items()],
    }


class TTSRequest(BaseModel):
    text: str


@app.post("/tts")
def tts(req: TTSRequest):
    """数字人语音层：edge-tts 合成 mp3 返回。失败返回 500，前端降级为纯文本。"""
    import edge_tts
    import asyncio

    async def _syn():
        communicate = edge_tts.Communicate(req.text, voice="zh-CN-XiaoxiaoNeural")
        buf = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf += chunk["data"]
        return buf

    try:
        audio_bytes = asyncio.run(_syn())
        from fastapi import Response
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(500, f"TTS failed: {e}")


# ---- 静态大屏：da serve 后同源直开（作品集独立窗口，免 CORS/改地址） ----
# 注意：必须在 uvicorn.run() 之前注册，否则阻塞后永不执行（2026-09-22 验证实测 404）
_DASH_DIR = _REPO_ROOT / "dashboard"
if _DASH_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_DASH_DIR)), name="dashboard")

    @app.get("/")
    def dashboard():
        """根路径直接回大屏。"""
        return FileResponse(str(_DASH_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8636)

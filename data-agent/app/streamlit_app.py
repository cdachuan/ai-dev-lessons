# -*- coding: utf-8 -*-
"""数分 Agent 前端：纯载体。所有能力来自 data_agent 包，前端只做「看得见、点得动」。"""
import json
from pathlib import Path

import streamlit as st

from data_agent import DataAgent, read_blackboard, bb_confirm, bb_list
from data_agent.governance import list_pending, approve, reject, _library_root

st.set_page_config(page_title="数分 Agent", layout="wide")
st.title("数分 Agent · 口径优先")

# ---------- 侧栏：审批队列 + 黑板 ----------
with st.sidebar:
    st.header("审批队列")
    st.caption("Agent 的入库提案（带口径声明）在这里等你勾选。批准才入库生效。")
    pending = list_pending()
    if not pending:
        st.caption("（队列为空）")
    for p in pending:
        with st.expander(f"🟡 {p['name']}"):
            st.markdown(f"**类型**：{p['kind']}　**提交**：{p['submitted']}")
            st.markdown(f"**描述**：{p['description']}")
            st.markdown(f"**口径**：{p['caliber']}")
            st.json(p.get("params", {}))
            st.markdown(f"**来源**：{', '.join(p.get('source_steps', [])) or '-'}")
            c1, c2 = st.columns(2)
            if c1.button("✅ 批准入库", key=f"ok_{p['id']}"):
                approve(p["id"], p["name"])
                st.rerun()
            if c2.button("❌ 拒绝", key=f"no_{p['id']}"):
                reject(p["id"], p["name"], reason="用户拒绝")
                st.rerun()

    st.divider()
    st.header("黑板")
    for e in bb_list()[:8]:
        icon = {"待确认": "🟡", "已定": "🟢", "已废弃": "⚫"}.get(e["status"], "·")
        with st.expander(f"{icon} {e['title']}"):
            st.markdown(f"**决策**：{e['decision']}")
            st.markdown(f"**why**：{e['why']}")
            if e["status"] == "待确认":
                c1, c2 = st.columns(2)
                if c1.button("✅ 确认", key=f"bbok_{e['id']}"):
                    bb_confirm(e["id"], "已定")
                    st.rerun()
                if c2.button("⚫ 废弃", key=f"bbno_{e['id']}"):
                    bb_confirm(e["id"], "已废弃")
                    st.rerun()

    st.divider()
    reports_dir = _library_root().parent / "reports"
    reports = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if reports:
        st.subheader("报告")
        for r in reports[:3]:
            st.markdown(f"[{r.stem}]({r.as_uri()})")
            docx = r.with_suffix(".docx")
            if docx.exists():
                with open(docx, "rb") as f:
                    st.download_button("下载 docx", f, file_name=docx.name, key=f"dl_{docx.name}")

# ---------- 会话状态 ----------
if "agent" not in st.session_state:
    try:
        st.session_state.agent = DataAgent()
    except RuntimeError as e:
        st.session_state.agent = None
        st.session_state.init_error = str(e)

if st.session_state.agent is None:
    st.error(f"Agent 未就绪：{st.session_state.get('init_error', '')}")
    st.stop()

# 渲染已有消息
for m in st.session_state.agent.messages:
    if m.get("role") not in ("user", "assistant"):
        continue
    content = m.get("content") or "（调用工具中…）"
    with st.chat_message(m["role"]):
        st.markdown(content)

# ---------- 输入 ----------
if prompt := st.chat_input("问点什么（数分/建模/报表）"):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("推理中…"):
            try:
                result = st.session_state.agent.ask(prompt)
            except Exception as e:
                st.error(f"出错: {e}")
                st.stop()
        placeholder.markdown(result["reply"])

        tool_steps = [t for t in result["trace"] if t.get("type") == "tool"]
        if tool_steps:
            with st.expander(f"执行过程（{len(tool_steps)} 次工具调用）", expanded=False):
                for t in tool_steps:
                    st.markdown(f"**`{t['name']}`**  参数: `{json.dumps(t.get('args', {}), ensure_ascii=False)}`")
                    try:
                        payload = json.loads(t["result"])
                        if isinstance(payload, dict) and payload.get("__type__") == "dataframe":
                            import pandas as pd
                            st.dataframe(pd.DataFrame(payload["records"]))
                        elif isinstance(payload, dict) and "plots" in payload:
                            for name, path in payload["plots"].items():
                                p = Path(path)
                                if p.exists():
                                    st.image(str(p), caption=name, width=360)
                        elif isinstance(payload, dict):
                            st.json(payload)
                        else:
                            st.text(str(payload)[:2000])
                    except Exception:
                        st.text(str(t["result"])[:2000])

# -*- coding: utf-8 -*-
"""数分 Agent 前端：聊天 + 工具过程可见 + 结果表格渲染 + 黑板侧栏。"""
import sys, json
from pathlib import Path

import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.agent import DataAgent  # noqa: E402
from core.memory import save_session, append_blackboard, read_blackboard  # noqa: E402

st.set_page_config(page_title="数分 Agent", layout="wide")
st.title("数分 Agent · 口径优先")

# ---------- 侧栏：黑板 ----------
with st.sidebar:
    st.header("黑板")
    st.caption("Agent 只写待确认区，你确认后改状态。决策挂 why。")
    st.markdown(read_blackboard())
    st.divider()
    st.caption("数据字典 dictionary.yaml = 口径权威源，工具不写死列名。")

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

# 渲染已有消息（只显示 user/assistant 文本，工具过程折叠在 trace 里）
display = [m for m in st.session_state.agent.messages
           if m.get("role") in ("user",) or (m.get("role") == "assistant")]
for m in display:
    role = m["role"]
    content = m.get("content") or "（调用工具中…）"
    with st.chat_message(role):
        st.markdown(content)

# ---------- 输入 ----------
if prompt := st.chat_input("问点什么（分析类问题）"):
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

        # 工具过程可见：中间产物留痕是产品要求
        tool_steps = [t for t in result["trace"] if t.get("type") == "tool"]
        if tool_steps:
            with st.expander(f"执行过程（{len(tool_steps)} 次工具调用）", expanded=False):
                for t in tool_steps:
                    st.markdown(f"**`{t['name']}`**  参数: `{json.dumps(t.get('args', {}), ensure_ascii=False)}`")
                    try:
                        payload = json.loads(t["result"])
                        if isinstance(payload, dict) and payload.get("__type__") == "dataframe":
                            st.dataframe(pd.DataFrame(payload["records"]))
                        elif isinstance(payload, dict):
                            st.json(payload)
                        else:
                            st.text(str(payload)[:2000])
                    except Exception:
                        st.text(str(t["result"])[:2000])

    # 落盘：会话 + 黑板提案（Agent 写待确认区）
    save_session(st.session_state.agent)
    last_tool = [t for t in result["trace"] if t.get("type") == "tool"]
    if last_tool:
        append_blackboard(prompt[:40], f"调用了 {len(last_tool)} 次工具，结论已输出", status="待确认")

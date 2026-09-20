# -*- coding: utf-8 -*-
"""数据洞察 Agent · Streamlit 界面（44课参考实现）

运行: streamlit run app.py
说明: 命令行 main.py 的界面化包装。API key 只存 session_state（内存），
不写任何文件；不填 key 时可用 --selftest 思路离线体验工具层。
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from agent import tools
from agent.core import run_agent, save_trace

st.set_page_config(page_title="数据洞察 Agent", page_icon="📊", layout="wide")

DATA_FILE = Path("D:/学习/ai-dev/data/ecommerce/online_retail_2010_2011.csv")

# ---------- 会话状态 ----------
if "history" not in st.session_state:
    st.session_state.history = []  # [(question, answer, trace)]

# ---------- 侧边栏 ----------
with st.sidebar:
    st.title("📊 数据洞察 Agent")
    st.caption("上传数据 → 自然语言提问 → 自主分析 → 图表报告")

    api_key = st.text_input("DeepSeek API Key（仅存内存，不落盘）", type="password")
    if api_key:
        import os
        os.environ["DEEPSEEK_API_KEY"] = api_key
        st.success("Key 已加载（本次会话有效）")
    else:
        st.info("未填 key：可看数据画像，提问需 key")

    st.divider()
    upload = st.file_uploader("上传你的 CSV（可选）", type=["csv"])
    if upload is not None:
        # 用户数据存临时位置供 agent 工具读取（会话结束即弃）
        tmp = Path("_uploaded.csv")
        tmp.write_bytes(upload.getvalue())
        st.session_state["upload_path"] = str(tmp)
        st.success(f"已加载: {upload.name}")
    else:
        st.session_state.pop("upload_path", None)
        st.caption(f"未上传时使用内置演示数据\n`{DATA_FILE.name}`（54万行UK电商）")

    st.divider()
    st.subheader("会话历史")
    for i, (q, _a, _t) in enumerate(reversed(st.session_state.history)):
        st.markdown(f"**{len(st.session_state.history)-i}.** {q[:30]}")

    # 报告下载
    if st.session_state.history:
        report = "\n\n---\n\n".join(
            f"## Q{i+1}: {q}\n\n{a}" for i, (q, a, _t) in enumerate(st.session_state.history)
        )
        st.download_button("下载本次会话报告 (Markdown)", report, file_name="insight_report.md")


# ---------- 主区 ----------
tab_ask, tab_data = st.tabs(["💬 提问", "📁 数据画像"])

with tab_data:
    try:
        profile = tools.profile()
        st.json(profile, expanded=False)
    except Exception as e:
        st.error(f"数据画像加载失败: {e}")

with tab_ask:
    st.subheader("试试这些问题")
    st.caption("各月销售额趋势如何？ / 哪些国家贡献最大？ / 客户价值怎么分层（RFM）？")
    question = st.chat_input("向数据提问…")
    if question:
        if not (api_key or os.environ.get("DEEPSEEK_API_KEY")):
            st.warning("请先在左侧填入 API Key（只存内存，不落盘）")
        else:
            with st.spinner("Agent 分析中…（选工具→算数→自检）"):
                try:
                    answer, trace = run_agent(question, verbose=False)
                    save_trace(question, answer, trace)
                    st.session_state.history.append((question, answer, trace))
                except Exception as e:
                    answer, trace = None, []
                    st.error(f"Agent 运行失败: {e}")

    # 渲染历史（最新在后）
    for i, (q, a, trace) in enumerate(st.session_state.history):
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            st.markdown(a)
            if trace:
                with st.expander("🔍 查看推理过程（工具调用留痕）"):
                    st.json(trace, expanded=False)

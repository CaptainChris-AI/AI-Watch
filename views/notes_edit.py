"""views/notes_edit.py — 鉴定说明维护（全站公用，逐条编辑）"""
from __future__ import annotations

import streamlit as st

import watch_db as db
from styles import BRAND_TITLE, ENG_SUBTITLE


def _head():
    st.markdown(
        f'<div class="hgstc-admin-head"><div>'
        f'<div class="t1">{BRAND_TITLE} · 鉴定说明维护</div>'
        f'<div class="t2">{ENG_SUBTITLE}</div></div></div>',
        unsafe_allow_html=True,
    )


def render():
    _head()
    st.info("鉴定说明为全站公用，会显示在手机端「鉴定结论」Tab 及报告卡 PDF 中。")

    notes = db.get_inspection_notes()
    if "notes_draft" not in st.session_state:
        st.session_state["notes_draft"] = list(notes)
    draft = st.session_state["notes_draft"]

    for i in range(len(draft)):
        c1, c2 = st.columns([10, 1])
        draft[i] = c1.text_area(f"第 {i+1} 条", value=draft[i], key=f"note_{i}",
                                height=80, label_visibility="visible")
        if c2.button("🗑", key=f"noted_{i}"):
            draft.pop(i)
            st.rerun()

    cc1, cc2, _ = st.columns([1, 1, 3])
    if cc1.button("➕ 新增一条"):
        draft.append("")
        st.rerun()
    if cc2.button("💾 保存全部", type="primary"):
        db.set_inspection_notes(draft)
        st.session_state["notes_draft"] = db.get_inspection_notes()
        st.success("已保存")
        st.rerun()

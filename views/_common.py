"""views/_common.py — 后台共享辅助"""
from __future__ import annotations

import streamlit as st
import watch_db as db


def get_base_url() -> str:
    """二维码站点地址：优先 settings，其次 secrets，最后占位。"""
    val = db.get_setting("base_url")
    if val:
        return val
    try:
        return st.secrets.get("base_url", "https://hgstc-watch.streamlit.app")
    except Exception:
        return "https://hgstc-watch.streamlit.app"


def read_upload(uploaded) -> tuple[bytes, str]:
    """Streamlit UploadedFile → (bytes, mime)。"""
    data = uploaded.getvalue()
    mime = uploaded.type or "image/jpeg"
    return data, mime

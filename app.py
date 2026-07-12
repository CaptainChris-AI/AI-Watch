"""
app.py — HGSTC 名表国检中心 入口
路由：?cert=检测编号 → 手机端查看页（免登录）；否则 → 管理后台（登录 + 侧边栏导航）。
架构与 AI Bot Underwriting 一致：Streamlit + st.navigation + SQLite。
"""
import streamlit as st
from packaging.version import Version

if Version(st.__version__) < Version("1.36.0"):
    st.error("Streamlit 版本过低，请运行 `pip install --upgrade streamlit` 升级至 1.36+。")
    st.stop()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import watch_db as db
from styles import ADMIN_CSS, BRAND_TITLE, ENG_SUBTITLE

st.set_page_config(page_title=BRAND_TITLE, page_icon="⌚", layout="wide")
db.init_db()

_LOGO = Path(__file__).parent / "assets" / "logo.jpg"


# ─────────────────────────────────────────────────────────────────────────────
# 路由 1：手机扫码查看页（公开）
# ─────────────────────────────────────────────────────────────────────────────
cert_no = st.query_params.get("cert")
if cert_no:
    import mobile_view
    mobile_view.render(cert_no)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 路由 2：管理后台（登录守卫）
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(ADMIN_CSS, unsafe_allow_html=True)


def _creds():
    try:
        u = st.secrets.get("admin_username", "admin")
        p = st.secrets.get("admin_password", "hgstc2026")
    except Exception:
        u, p = "admin", "hgstc2026"
    return u, p


def _login_gate():
    if st.session_state.get("hg_authed"):
        return True
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(f'<div class="hgstc-login-title">{BRAND_TITLE}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="hgstc-login-sub">{ENG_SUBTITLE}</div>',
                    unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("账号")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True, type="primary"):
                cu, cp = _creds()
                if u == cu and p == cp:
                    st.session_state["hg_authed"] = True
                    st.rerun()
                else:
                    st.error("账号或密码错误")
    return False


if not _login_gate():
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 已登录：侧边栏导航
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    if _LOGO.exists():
        st.image(str(_LOGO), use_container_width=True)
    st.markdown(f"**{BRAND_TITLE}**")
    st.caption(ENG_SUBTITLE)
    st.divider()
    if st.button("退出登录", use_container_width=True):
        st.session_state.pop("hg_authed", None)
        st.rerun()

from views import cert_list, cert_new, notes_edit, company_edit

pg = st.navigation([
    st.Page(cert_list.render, title="证书列表", icon="📋", url_path="certs", default=True),
    st.Page(cert_new.render, title="新建证书", icon="➕", url_path="new"),
    st.Page(notes_edit.render, title="鉴定说明维护", icon="📝", url_path="notes"),
    st.Page(company_edit.render, title="公司介绍维护", icon="🏢", url_path="company"),
])
pg.run()

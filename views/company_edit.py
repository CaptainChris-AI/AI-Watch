"""views/company_edit.py — 公司介绍维护（简介 + 鉴定师增删改）"""
from __future__ import annotations

import streamlit as st

import watch_db as db
from views._common import read_upload
from styles import BRAND_TITLE, ENG_SUBTITLE


def _head():
    st.markdown(
        f'<div class="hgstc-admin-head"><div>'
        f'<div class="t1">{BRAND_TITLE} · 公司介绍维护</div>'
        f'<div class="t2">{ENG_SUBTITLE}</div></div></div>',
        unsafe_allow_html=True,
    )


def render():
    _head()
    st.info("公司介绍显示在手机端「公司信息」Tab。")

    # 公司简介
    st.subheader("公司简介")
    intro = st.text_area("简介文本", value=db.get_setting("company_intro", ""),
                         height=140)
    if st.button("💾 保存简介", type="primary"):
        db.set_setting("company_intro", intro)
        st.success("已保存")

    st.divider()

    # 报告卡设置：检验师 / 复检师 签名、印章、地址
    st.subheader("报告卡设置（检验师 / 复检师 / 印章 / 地址）")
    st.caption("以下内容用于报告卡 PDF 的签名、盖章与底部地址。")

    def _sig_block(key, label, name_key):
        col1, col2 = st.columns([2, 1])
        with col1:
            name = st.text_input(f"{label} 姓名", value=db.get_setting(name_key, ""),
                                 key=f"name_{name_key}")
            up = st.file_uploader(f"{label} 签名图（PNG，建议透明背景）",
                                  type=["png", "jpg", "jpeg"], key=f"up_{key}")
            b1, b2 = st.columns(2)
            if b1.button(f"保存{label}", key=f"save_{key}"):
                db.set_setting(name_key, name)
                if up:
                    blob, mime = read_upload(up)
                    db.set_asset(key, blob, mime)
                st.success("已保存")
                st.rerun()
            if b2.button(f"删除{label}签名", key=f"del_{key}"):
                db.delete_asset(key)
                st.rerun()
        with col2:
            cur = db.get_asset(key)
            if cur:
                st.image(cur[0], caption="当前签名", use_container_width=True)
            else:
                st.caption("无签名图")

    _sig_block("inspector_signature", "检验师", "inspector_name")
    st.markdown("---")
    _sig_block("reviewer_signature", "复检师", "reviewer_name")

    st.markdown("---")
    st.markdown("**印章**")
    sc1, sc2 = st.columns([2, 1])
    with sc1:
        stamp_up = st.file_uploader("印章图（PNG，建议透明背景）",
                                    type=["png", "jpg", "jpeg"], key="up_stamp")
        b1, b2 = st.columns(2)
        if b1.button("保存印章"):
            if stamp_up:
                blob, mime = read_upload(stamp_up)
                db.set_asset("stamp", blob, mime)
                st.success("已保存")
                st.rerun()
            else:
                st.warning("请先选择印章图片")
        if b2.button("删除印章"):
            db.delete_asset("stamp")
            st.rerun()
    with sc2:
        cur = db.get_asset("stamp")
        if cur:
            st.image(cur[0], caption="当前印章", use_container_width=True)
        else:
            st.caption("无印章")

    st.markdown("---")
    st.markdown("**底部地址（报告卡下方）**")
    addr_l = st.text_input("地址一（左）", value=db.get_setting("address_left", ""))
    addr_r = st.text_input("地址二（右）", value=db.get_setting("address_right", ""))
    if st.button("💾 保存地址"):
        db.set_setting("address_left", addr_l)
        db.set_setting("address_right", addr_r)
        st.success("已保存")

    st.divider()

    # 鉴定师列表
    st.subheader("鉴定师")
    members = db.list_company_members()
    for m in members:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                nm = st.text_input("姓名", value=m["name"], key=f"nm_{m['id']}")
                cr = st.text_area("资历", value=m["credentials"],
                                  key=f"cr_{m['id']}", height=100)
                newphoto = st.file_uploader("更换头像", type=["jpg", "jpeg", "png"],
                                            key=f"ph_{m['id']}")
            with c2:
                if m["photo"]:
                    st.image(m["photo"], use_container_width=True)
                else:
                    st.caption("无头像")
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("保存", key=f"save_{m['id']}"):
                if newphoto:
                    blob, mime = read_upload(newphoto)
                    db.update_company_member(m["id"], nm, cr, blob, mime)
                else:
                    db.update_company_member(m["id"], nm, cr)
                st.success("已保存")
                st.rerun()
            if b2.button("🗑 删除", key=f"del_{m['id']}"):
                db.delete_company_member(m["id"])
                st.rerun()

    st.divider()
    st.subheader("➕ 新增鉴定师")
    with st.form("add_member", clear_on_submit=True):
        nm = st.text_input("姓名 *")
        cr = st.text_area("资历", height=100)
        photo = st.file_uploader("头像", type=["jpg", "jpeg", "png"])
        if st.form_submit_button("新增", type="primary"):
            if not nm.strip():
                st.error("姓名必填")
            else:
                blob, mime = (read_upload(photo) if photo else (None, "image/jpeg"))
                db.add_company_member(nm.strip(), cr, blob, mime)
                st.success("已新增")
                st.rerun()

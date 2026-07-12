"""views/cert_list.py — 证书列表：查看 / 下载报告卡PDF / 二维码 / 删除"""
from __future__ import annotations

import streamlit as st

import watch_db as db
import qr_util
import pdf_report
from views._common import get_base_url
from styles import BRAND_TITLE, ENG_SUBTITLE
from pathlib import Path

_LOGO = str(Path(__file__).parent.parent / "assets" / "logo.jpg")


def _head():
    st.markdown(
        f'<div class="hgstc-admin-head"><div>'
        f'<div class="t1">{BRAND_TITLE} · 证书列表</div>'
        f'<div class="t2">{ENG_SUBTITLE}</div></div></div>',
        unsafe_allow_html=True,
    )


def _settings_expander():
    with st.expander("⚙️ 站点设置（二维码地址）", expanded=False):
        cur = get_base_url()
        new = st.text_input(
            "站点地址 base_url（部署到 Streamlit 后填你的 https://xxx.streamlit.app）",
            value=cur)
        if st.button("保存地址"):
            db.set_setting("base_url", new.strip())
            st.success("已保存")
            st.rerun()


@st.dialog("证书详情", width="large")
def _detail_dialog(cid):
    cert = db.get_certificate(cid)
    if not cert:
        st.warning("证书不存在")
        return
    base = get_base_url()
    url = qr_util.build_cert_url(base, cert["cert_no"])

    st.markdown(f"### {cert['brand']} {cert['model']}")
    st.caption(f"检测编号 {cert['cert_no']}｜鉴定 {cert['inspect_date']}"
               f"｜有效期至 {cert['valid_until']}")

    imgs = db.get_certificate_images(cid)
    if imgs:
        cols = st.columns(min(len(imgs), 4))
        for i, (b, _m) in enumerate(imgs):
            cols[i % 4].image(b, use_container_width=True)

    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.markdown("**基本信息**")
        st.write({
            "品牌": cert["brand"], "型号": cert["model"], "尺寸": cert["size"],
            "表壳编号": cert["case_no"], "机芯编号": cert["movement_no"],
            "表壳材质": cert["case_material"], "备注": cert["remark"],
        })
        st.markdown(f"**样品结论**：{cert['sample_conclusion'] or '-'}")
        st.markdown("**鉴定内容**")
        st.write(cert["inspect_content"] or "-")
    with c2:
        qr = qr_util.make_cert_qr(base, cert["cert_no"])
        st.image(qr, caption="扫码查看电子报告", use_container_width=True)
        st.caption(url)

    # PDF 下载
    pdf = pdf_report.generate_report_pdf(
        cert, imgs, db.get_inspection_notes(),
        qr_png=qr_util.make_cert_qr(base, cert["cert_no"], box_size=6),
        logo_path=_LOGO)
    st.download_button("📄 下载报告卡 PDF（A5 横版）", data=pdf,
                       file_name=f"HGSTC_{cert['cert_no']}.pdf",
                       mime="application/pdf", type="primary",
                       use_container_width=True)


def render():
    _head()
    _settings_expander()

    kw = st.text_input("搜索（检测编号 / 品牌 / 型号）", placeholder="留空显示全部")
    rows = db.list_certificates(kw.strip())

    st.caption(f"共 {len(rows)} 条")
    if not rows:
        st.info("暂无证书，去「新建证书」创建。")
        return

    base = get_base_url()
    # 表头
    h = st.columns([2, 2, 2.6, 1.6, 1.2, 1.2, 1])
    for col, t in zip(h, ["检测编号", "品牌", "型号", "鉴定日期",
                          "查看", "PDF", "删除"]):
        col.markdown(f"**{t}**")

    for r in rows:
        c = st.columns([2, 2, 2.6, 1.6, 1.2, 1.2, 1])
        c[0].write(r["cert_no"])
        c[1].write(r["brand"] or "-")
        c[2].write(r["model"] or "-")
        c[3].write(r["inspect_date"] or "-")
        if c[4].button("查看", key=f"v_{r['id']}"):
            _detail_dialog(r["id"])
        pdf = pdf_report.generate_report_pdf(
            r, db.get_certificate_images(r["id"]), db.get_inspection_notes(),
            qr_png=qr_util.make_cert_qr(base, r["cert_no"], box_size=6),
            logo_path=_LOGO)
        c[5].download_button("PDF", data=pdf, key=f"p_{r['id']}",
                             file_name=f"HGSTC_{r['cert_no']}.pdf",
                             mime="application/pdf")
        if c[6].button("🗑", key=f"d_{r['id']}"):
            st.session_state["_del_id"] = r["id"]
            st.session_state["_del_no"] = r["cert_no"]

    # 删除确认
    if st.session_state.get("_del_id"):
        no = st.session_state.get("_del_no")
        st.warning(f"确认删除证书「{no}」？此操作不可恢复。")
        cc1, cc2, _ = st.columns([1, 1, 4])
        if cc1.button("确认删除", type="primary"):
            db.delete_certificate(st.session_state["_del_id"])
            st.session_state.pop("_del_id", None)
            st.session_state.pop("_del_no", None)
            st.rerun()
        if cc2.button("取消"):
            st.session_state.pop("_del_id", None)
            st.session_state.pop("_del_no", None)
            st.rerun()

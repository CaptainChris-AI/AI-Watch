"""views/cert_new.py — 新建证书"""
from __future__ import annotations

import datetime

import streamlit as st

import watch_db as db
from views._common import read_upload
from styles import BRAND_TITLE, ENG_SUBTITLE


def _head():
    st.markdown(
        f'<div class="hgstc-admin-head"><div>'
        f'<div class="t1">{BRAND_TITLE} · 新建证书</div>'
        f'<div class="t2">{ENG_SUBTITLE}</div></div></div>',
        unsafe_allow_html=True,
    )


def render():
    _head()

    st.subheader("① 上传细节图片")
    uploads = st.file_uploader(
        "支持多张（JPG/PNG），按上传顺序在手机端轮播/PDF平铺",
        type=["jpg", "jpeg", "png"], accept_multiple_files=True,
    )
    if uploads:
        cols = st.columns(min(len(uploads), 5))
        for i, f in enumerate(uploads):
            cols[i % 5].image(f, use_container_width=True)

    with st.form("new_cert", clear_on_submit=False):
        st.subheader("② 基本情况")
        c1, c2 = st.columns(2)
        cert_no = c1.text_input("检测编号 *", placeholder="如 2619170707")
        brand = c2.text_input("品牌", placeholder="如 理查米尔")
        model = c1.text_input("型号", placeholder="如 RM11-03 CA ATZ")
        status = c2.text_input("状态", placeholder="如 已使用品 / 全新")
        case_no = c1.text_input("表身号", placeholder="表身/表壳编号")
        movement_no = c2.text_input("机芯号")
        origin = c1.text_input("产地", placeholder="如 瑞士")
        warranty_card_info = c2.text_input("保卡资讯", placeholder="如 销售日期 2020年10月")
        d1, d2 = st.columns(2)
        inspect_date = d1.date_input("鉴定日期", value=datetime.date.today())
        valid_until = d2.date_input(
            "有效期至", value=datetime.date.today() + datetime.timedelta(days=180))

        st.subheader("③ 功能参数")
        f1, f2 = st.columns(2)
        case_material = f1.text_input("材质", placeholder="如 白色陶瓷+TPT")
        strap = f2.text_input("表带", placeholder="如 橡胶带+钛质折叠扣")
        size = f1.text_input("直径 / 尺寸", placeholder="如 44.5×49.94mm")
        water_resistance = f2.text_input("防水")
        functions = f1.text_input("功能", placeholder="如 计时/日期")
        accessories = f2.text_input("附件", placeholder="如 保卡、说明书、表盒")
        amplitude = f1.text_input("摆幅")
        data_metrics = f2.text_input("数据", placeholder="如 走时误差 -2s/d 至 0s/d")
        remark = st.text_input("备注")

        st.subheader("④ 鉴定结论")
        sample_conclusion = st.text_input("样品结论（结论）", placeholder="如 正品")

        st.subheader("⑤ 鉴定内容")
        inspect_content = st.text_area("鉴定内容", height=200,
                                       placeholder="详细描述外观、机芯、功能检测情况等")

        submitted = st.form_submit_button("保存证书", type="primary",
                                          use_container_width=True)

    if submitted:
        if not cert_no.strip():
            st.error("检测编号必填")
            return
        if db.cert_no_exists(cert_no.strip()):
            st.error(f"检测编号「{cert_no}」已存在，请更换")
            return
        images = [read_upload(f) for f in uploads] if uploads else []
        data = {
            "cert_no": cert_no.strip(), "brand": brand, "model": model,
            "size": size, "case_no": case_no, "movement_no": movement_no,
            "case_material": case_material, "remark": remark,
            "inspect_date": inspect_date.strftime("%Y-%m-%d"),
            "valid_until": valid_until.strftime("%Y-%m-%d"),
            "sample_conclusion": sample_conclusion,
            "inspect_content": inspect_content,
            "status": status, "warranty_card_info": warranty_card_info,
            "origin": origin, "strap": strap, "water_resistance": water_resistance,
            "functions": functions, "accessories": accessories,
            "amplitude": amplitude, "data_metrics": data_metrics,
        }
        db.create_certificate(data, images)
        st.success(f"✅ 证书「{cert_no}」已创建（{len(images)} 张图片）。"
                   "可到「证书列表」下载报告卡PDF / 查看二维码。")
        st.balloons()

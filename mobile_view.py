"""
mobile_view.py — 手机扫码查看页（公开，免登录）
布局参考站截图：品牌头 + 图片轮播 + 摘要卡（编号/日期/有效期）+ 3个Tab。
用 Streamlit 原生 st.tabs（可靠）+ CSS 定制外观；轮播用 components.html(scroll-snap+JS圆点)。
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import watch_db as db
from styles import NAVY, GOLD, TEXT_MUTED, BRAND_TITLE, ENG_SUBTITLE

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.jpg"


def _b64(blob: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(blob).decode()}"


def _logo_data_uri() -> str:
    try:
        return _b64(_LOGO_PATH.read_bytes(), "image/jpeg")
    except Exception:
        return ""


def _mobile_css():
    st.markdown(f"""
    <style>
    #MainMenu, footer, header[data-testid="stHeader"] {{visibility:hidden; height:0;}}
    [data-testid="stSidebar"] {{display:none;}}
    .block-container {{max-width:540px; padding:0 12px 40px; margin:auto;}}
    body {{background:#F0F0F2;}}

    .hg-head {{display:flex; align-items:center; gap:12px; background:{NAVY};
        padding:16px 16px; border-radius:0 0 14px 14px; margin:-4px -12px 14px;}}
    .hg-head img {{height:46px; border-radius:6px;}}
    .hg-head .t1 {{color:#fff; font-size:19px; font-weight:700; line-height:1.25;}}
    .hg-head .t2 {{color:{GOLD}; font-size:11px; letter-spacing:.3px; margin-top:2px;}}

    .hg-summary {{display:flex; background:#fff; border-radius:14px;
        padding:16px 8px; margin:12px 0 16px; box-shadow:0 2px 10px rgba(0,0,0,.04);}}
    .hg-summary .col {{flex:1; text-align:center; position:relative;}}
    .hg-summary .col + .col {{border-left:1px solid #ECECEF;}}
    .hg-summary .lb {{color:{TEXT_MUTED}; font-size:12px;}}
    .hg-summary .vl {{color:{NAVY}; font-size:16px; font-weight:700; margin-top:6px;}}

    .hg-card {{background:#fff; border-radius:14px; padding:16px 16px;
        box-shadow:0 2px 10px rgba(0,0,0,.04);}}
    .hg-row {{display:flex; justify-content:space-between; align-items:flex-start;
        padding:13px 0; border-bottom:1px dashed #E6E6EA; gap:16px;}}
    .hg-row:last-child {{border-bottom:none;}}
    .hg-row .k {{color:{TEXT_MUTED}; font-size:15px; white-space:nowrap;}}
    .hg-row .v {{color:{NAVY}; font-size:15px; font-weight:600; text-align:right;
        word-break:break-all;}}
    .hg-sec-title {{color:{GOLD}; font-size:16px; font-weight:700;
        border-bottom:2px solid {GOLD}; padding-bottom:8px; margin:4px 0 14px;}}
    .hg-sec-title.mt {{margin-top:22px;}}
    .hg-concl {{color:{NAVY}; font-size:16px; font-weight:600;}}
    .hg-content {{color:#2C3444; font-size:15px; line-height:1.85; white-space:pre-wrap;}}
    .hg-note {{color:#2C3444; font-size:14px; line-height:1.7; margin-bottom:12px;
        display:flex; gap:8px;}}
    .hg-note .n {{color:{GOLD}; font-weight:700; flex-shrink:0;}}
    .hg-intro {{color:#2C3444; font-size:15px; line-height:1.8; margin-bottom:18px;}}
    .hg-member {{display:flex; gap:14px; padding:14px 0; border-bottom:1px solid #EEE;}}
    .hg-member:last-child {{border-bottom:none;}}
    .hg-member .info {{flex:1;}}
    .hg-member .nm {{color:{NAVY}; font-size:16px; font-weight:700; margin-bottom:6px;}}
    .hg-member .nm span {{color:{GOLD}; margin-left:6px;}}
    .hg-member .cr {{color:#4A5160; font-size:13px; line-height:1.7;}}
    .hg-member img {{width:92px; height:112px; object-fit:cover; border-radius:8px;}}

    /* 原生 tabs 改造成藏青/金色分段控件 */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{gap:0; background:#E9EAEE;
        border-radius:10px; padding:4px;}}
    [data-testid="stTabs"] [data-baseweb="tab-highlight"],
    [data-testid="stTabs"] [data-baseweb="tab-border"] {{display:none;}}
    [data-testid="stTabs"] button[data-baseweb="tab"] {{flex:1; justify-content:center;
        border-radius:8px; color:{TEXT_MUTED}; font-weight:600; padding:10px 4px;}}
    [data-testid="stTabs"] button[data-baseweb="tab"] p {{font-size:15px;}}
    [data-testid="stTabs"] button[aria-selected="true"] {{background:{NAVY};}}
    [data-testid="stTabs"] button[aria-selected="true"] p {{color:{GOLD};}}
    </style>
    """, unsafe_allow_html=True)


def _render_header():
    logo = _logo_data_uri()
    img = f'<img src="{logo}"/>' if logo else ""
    st.markdown(
        f'<div class="hg-head">{img}<div>'
        f'<div class="t1">{BRAND_TITLE}</div>'
        f'<div class="t2">{ENG_SUBTITLE}</div></div></div>',
        unsafe_allow_html=True,
    )


def _render_carousel(images):
    if not images:
        st.markdown(
            '<div class="hg-card" style="text-align:center;color:#8A8F99;'
            'padding:40px 0;">暂无细节图片</div>', unsafe_allow_html=True)
        return
    slides = "".join(
        f'<div class="slide"><img src="{_b64(b, m)}"/></div>' for b, m in images
    )
    dots = "".join(f'<span class="dot{" on" if i==0 else ""}"></span>'
                   for i in range(len(images)))
    html = f"""
    <style>
      * {{box-sizing:border-box;}} body{{margin:0;font-family:-apple-system,sans-serif;}}
      .wrap{{position:relative;}}
      .track{{display:flex; overflow-x:auto; scroll-snap-type:x mandatory;
        border-radius:14px; background:#fff; -webkit-overflow-scrolling:touch;
        scrollbar-width:none;}}
      .track::-webkit-scrollbar{{display:none;}}
      .slide{{flex:0 0 100%; scroll-snap-align:center; height:300px;
        display:flex; align-items:center; justify-content:center;}}
      .slide img{{max-width:100%; max-height:300px; object-fit:contain;}}
      .dots{{display:flex; gap:6px; justify-content:center; margin-top:10px;}}
      .dot{{width:7px; height:7px; border-radius:50%; background:#CFCFD6;}}
      .dot.on{{background:{GOLD}; width:18px; border-radius:4px;}}
      .arrow{{position:absolute; top:50%; transform:translateY(-50%);
        width:38px; height:38px; border-radius:50%; background:rgba(120,120,130,.45);
        color:#fff; border:none; font-size:18px; cursor:pointer;}}
      .arrow.l{{left:8px;}} .arrow.r{{right:8px;}}
    </style>
    <div class="wrap">
      <div class="track" id="tk">{slides}</div>
      <button class="arrow l" onclick="mv(-1)">‹</button>
      <button class="arrow r" onclick="mv(1)">›</button>
      <div class="dots" id="dt">{dots}</div>
    </div>
    <script>
      const tk=document.getElementById('tk');
      const dots=document.querySelectorAll('#dt .dot');
      function upd(){{
        const i=Math.round(tk.scrollLeft/tk.clientWidth);
        dots.forEach((d,k)=>d.classList.toggle('on',k===i));
      }}
      function mv(d){{
        const i=Math.round(tk.scrollLeft/tk.clientWidth)+d;
        tk.scrollTo({{left:Math.max(0,i)*tk.clientWidth,behavior:'smooth'}});
      }}
      tk.addEventListener('scroll',()=>window.requestAnimationFrame(upd));
    </script>
    """
    components.html(html, height=345)


def _render_summary(cert):
    st.markdown(f"""
    <div class="hg-summary">
      <div class="col"><div class="lb">检测编号</div>
        <div class="vl">{cert['cert_no']}</div></div>
      <div class="col"><div class="lb">鉴定日期</div>
        <div class="vl">{cert['inspect_date'] or '-'}</div></div>
      <div class="col"><div class="lb">有效期至</div>
        <div class="vl">{cert['valid_until'] or '-'}</div></div>
    </div>""", unsafe_allow_html=True)


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _tab_basic(cert):
    def cv(k):
        try:
            return cert[k] if k in cert.keys() else ""
        except Exception:
            return ""
    fields = [
        ("品牌", cv("brand")), ("型号", cv("model")), ("状态", cv("status")),
        ("机芯号", cv("movement_no")), ("表身号", cv("case_no")),
        ("产地", cv("origin")), ("保卡资讯", cv("warranty_card_info")),
        ("材质", cv("case_material")), ("表带", cv("strap")),
        ("直径", cv("size")), ("防水", cv("water_resistance")),
        ("功能", cv("functions")), ("附件", cv("accessories")),
        ("摆幅", cv("amplitude")), ("数据", cv("data_metrics")),
        ("备注", cv("remark")),
    ]
    rows = "".join(
        f'<div class="hg-row"><div class="k">{k}</div>'
        f'<div class="v">{_esc(v) or "-"}</div></div>' for k, v in fields
    )
    st.markdown(f'<div class="hg-card">{rows}</div>', unsafe_allow_html=True)


def _tab_conclusion(cert, notes):
    note_html = "".join(
        f'<div class="hg-note"><span class="n">{i}.</span>'
        f'<span>{_esc(n)}</span></div>' for i, n in enumerate(notes, 1)
    )
    st.markdown(f"""
    <div class="hg-card">
      <div class="hg-sec-title">样品结论</div>
      <div class="hg-concl">{_esc(cert['sample_conclusion']) or '-'}</div>
      <div class="hg-sec-title mt">鉴定内容</div>
      <div class="hg-content">{_esc(cert['inspect_content']) or '-'}</div>
      <div class="hg-sec-title mt">鉴定说明</div>
      {note_html}
    </div>""", unsafe_allow_html=True)


def _tab_company(intro, members):
    cards = ""
    for m in members:
        photo = ""
        if m["photo"]:
            photo = f'<img src="{_b64(m["photo"], m["mime"])}"/>'
        cards += (
            f'<div class="hg-member"><div class="info">'
            f'<div class="nm">{_esc(m["name"])}<span>——</span></div>'
            f'<div class="cr">{_esc(m["credentials"])}</div></div>{photo}</div>'
        )
    st.markdown(f"""
    <div class="hg-card">
      <div class="hg-intro">{_esc(intro)}</div>
      {cards if cards else '<div style="color:#8A8F99;">暂无鉴定师信息</div>'}
    </div>""", unsafe_allow_html=True)


def render(cert_no: str):
    _mobile_css()
    _render_header()
    cert = db.get_certificate_by_no(cert_no)
    if not cert:
        st.markdown(
            '<div class="hg-card" style="text-align:center;padding:48px 0;">'
            '<div style="font-size:40px;">🔍</div>'
            '<div style="color:#2B3A52;font-weight:700;font-size:18px;margin-top:12px;">'
            '未找到该鉴定报告</div>'
            f'<div style="color:#8A8F99;margin-top:8px;">编号：{_esc(cert_no)}</div>'
            '</div>', unsafe_allow_html=True)
        return

    _render_carousel(db.get_certificate_images(cert["id"]))
    _render_summary(cert)

    notes = db.get_inspection_notes()
    intro = db.get_setting("company_intro", "")
    members = db.list_company_members()

    t1, t2, t3 = st.tabs(["基本信息", "鉴定结论", "公司信息"])
    with t1:
        _tab_basic(cert)
    with t2:
        _tab_conclusion(cert, notes)
    with t3:
        _tab_company(intro, members)

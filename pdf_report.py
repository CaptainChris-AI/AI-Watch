"""
pdf_report.py — A5 横版 鉴定报告卡 PDF（PyMuPDF / fitz）
样式参考 Report Test.pdf：米色底 + 金色描边、CX logo、双栏「基本資訊 / 功能參數」、
右侧 QR + 印章 + 检验师/复检师签名、底部金色地址栏。
第 2 页起为 鑑定內容 + 鑑定說明（长文本自动分页）。

中文（含繁体）使用 PyMuPDF 内置 CJK 字体 "china-s"。
"""
from __future__ import annotations

import io
import fitz  # PyMuPDF
from pathlib import Path

import watch_db as db
from styles import BRAND_TITLE, ENG_SUBTITLE

PAGE_W = 595.28
PAGE_H = 419.53
CJK = "china-s"


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


CREAM = _hex("#F7F1E2")
BORDER = _hex("#4A3A28")
GOLD = _hex("#B4924E")
GOLD_UL = _hex("#CBB37C")
GOLD_BAR = _hex("#C2A468")
DARK = _hex("#2E2618")
GREY = _hex("#8B8371")
WHITE = (1, 1, 1)
LINE = _hex("#E3D9C2")


# ── helpers ──────────────────────────────────────────────────────────────────
def _cv(cert, key) -> str:
    try:
        keys = cert.keys()
    except Exception:
        keys = cert
    val = cert[key] if key in keys else ""
    return "" if val is None else str(val)


def _ctext(page, cx, y, text, color, size, font=CJK):
    w = fitz.get_text_length(text, fontname=font, fontsize=size)
    page.insert_text((cx - w / 2, y), text, fontname=font, fontsize=size, color=color)


def _wrap(text: str, size: float, max_w: float, max_lines: int | None = None) -> list[str]:
    lines: list[str] = []
    for para in (text or "").split("\n"):
        if para == "":
            lines.append("")
            continue
        cur = ""
        for ch in para:
            if fitz.get_text_length(cur + ch, fontname=CJK, fontsize=size) <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1][:-1] + "…"
    return lines


def _bg_and_border(page):
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=CREAM)
    page.draw_rect(fitz.Rect(9, 9, PAGE_W - 9, PAGE_H - 9),
                   color=BORDER, width=3.2, radius=0.03)
    page.draw_rect(fitz.Rect(15, 15, PAGE_W - 15, PAGE_H - 15),
                   color=GOLD, width=1, radius=0.03)


def _img(page, rect, asset, keep=True):
    """asset = (bytes, mime) or None."""
    if not asset:
        return
    try:
        page.insert_image(rect, stream=asset[0], keep_proportion=keep)
    except Exception:
        pass


# ── field columns ────────────────────────────────────────────────────────────
def _draw_col(page, x, w, heading, rows, y0, label_w=46):
    page.insert_text((x, y0), heading, fontname=CJK, fontsize=12, color=GOLD)
    page.draw_line((x, y0 + 5), (x + w, y0 + 5), color=GOLD_UL, width=1.2)
    val_x = x + label_w
    val_w = w - label_w
    y = y0 + 20
    for label, value in rows:
        page.insert_text((x, y + 8), label, fontname=CJK, fontsize=9, color=GOLD)
        vlines = _wrap(str(value) or "—", 9, val_w, max_lines=2)
        vy = y + 8
        for ln in vlines:
            page.insert_text((val_x, vy), ln, fontname=CJK, fontsize=9, color=DARK)
            vy += 11
        y += max(21, len(vlines) * 11 + 6)
    return y


# ── page 1 ───────────────────────────────────────────────────────────────────
def _page1(page, cert, images, qr_png, logo_path, assets):
    _bg_and_border(page)

    # header
    if logo_path and Path(logo_path).exists():
        _img(page, fitz.Rect(26, 24, 104, 66), (Path(logo_path).read_bytes(), "image/jpeg"))
    page.insert_text((114, 47), BRAND_TITLE, fontname=CJK, fontsize=18, color=DARK)
    page.insert_text((115, 63), ENG_SUBTITLE, fontname="helv", fontsize=9, color=GOLD)

    page.insert_text((378, 40), "檢測報告編號", fontname=CJK, fontsize=8, color=GOLD)
    page.insert_text((378, 57), cert["cert_no"], fontname=CJK, fontsize=10, color=DARK)
    page.insert_text((480, 40), "報告日期", fontname=CJK, fontsize=8, color=GOLD)
    page.insert_text((480, 57), _cv(cert, "inspect_date") or "—",
                     fontname=CJK, fontsize=10, color=DARK)
    page.draw_line((24, 70), (PAGE_W - 24, 70), color=GOLD_UL, width=0.9)

    # photos (big + 2x2 grid)
    page.draw_rect(fitz.Rect(22, 78, 180, 186), color=LINE, width=0.6)
    if images:
        _img(page, fitz.Rect(22, 78, 180, 186), images[0])
    grid = images[1:5]
    gx, gy, gw, gh, gap = 22, 192, 158, 158, 5
    cw = (gw - gap) / 2
    ch = (gh - gap) / 2
    for i in range(4):
        r, c = divmod(i, 2)
        cell = fitz.Rect(gx + c * (cw + gap), gy + r * (ch + gap),
                         gx + c * (cw + gap) + cw, gy + r * (ch + gap) + ch)
        page.draw_rect(cell, color=LINE, width=0.6)
        if i < len(grid):
            _img(page, cell, grid[i])

    # field columns
    basic = [
        ("品牌", _cv(cert, "brand")), ("型號", _cv(cert, "model")),
        ("結論", _cv(cert, "sample_conclusion")), ("狀態", _cv(cert, "status")),
        ("機芯號", _cv(cert, "movement_no")), ("表身號", _cv(cert, "case_no")),
        ("保卡資訊", _cv(cert, "warranty_card_info")), ("產地", _cv(cert, "origin")),
    ]
    func = [
        ("材質", _cv(cert, "case_material")), ("錶帶", _cv(cert, "strap")),
        ("直徑", _cv(cert, "size")), ("防水", _cv(cert, "water_resistance")),
        ("功能", _cv(cert, "functions")), ("附件", _cv(cert, "accessories")),
        ("擺幅", _cv(cert, "amplitude")), ("數據", _cv(cert, "data_metrics")),
    ]
    _draw_col(page, 192, 150, "基本資訊", basic, 92)
    _draw_col(page, 352, 124, "功能參數", func, 92)

    # right zone: QR + stamp + signatures
    if qr_png:
        _img(page, fitz.Rect(484, 80, 542, 138), (qr_png, "image/png"))
    if assets.get("stamp"):
        _img(page, fitz.Rect(482, 144, 544, 206), assets["stamp"])

    def _sig(label, name, sig, y):
        page.insert_text((480, y), label, fontname=CJK, fontsize=9.5, color=GOLD)
        if sig:
            _img(page, fitz.Rect(478, y + 4, 572, y + 30), sig)
        if name:
            _ctext(page, 525, y + 46, name, DARK, 9.5)

    _sig("檢驗師", db.get_setting("inspector_name", ""),
         assets.get("inspector_signature"), 224)
    _sig("複檢師", db.get_setting("reviewer_name", ""),
         assets.get("reviewer_signature"), 286)

    # disclaimer
    disc = f"鑑定結果或結論僅對送檢樣品負責，{BRAND_TITLE}保留最終決定權。"
    page.insert_text((192, 358), _wrap(disc, 7.5, 278, max_lines=1)[0],
                     fontname=CJK, fontsize=7.5, color=GREY)

    # bottom address bar
    page.draw_rect(fitz.Rect(15, 372, PAGE_W - 15, 402), color=None, fill=GOLD_BAR)
    mid = PAGE_W / 2

    def _addr(text, x0, x1):
        if not text:
            return
        center = (x0 + x1) / 2
        w = fitz.get_text_length(text, fontname=CJK, fontsize=7)
        sx = center - w / 2
        page.draw_circle((sx - 8, 388), 2.2, color=None, fill=WHITE)
        page.insert_text((sx, 391), text, fontname=CJK, fontsize=7, color=WHITE)

    _addr(assets.get("address_left", ""), 40, mid - 6)
    _addr(assets.get("address_right", ""), mid + 6, PAGE_W - 24)


# ── flow pages (content + notes) ─────────────────────────────────────────────
def _flow_section(doc, state, title, paragraphs):
    size = 9.5
    leading = size + 4.5
    margin = 30
    max_w = PAGE_W - 2 * margin
    bottom = PAGE_H - 28

    def new_page():
        p = doc.new_page(width=PAGE_W, height=PAGE_H)
        _bg_and_border(p)
        p.insert_text((margin, 40), BRAND_TITLE, fontname=CJK, fontsize=13, color=GOLD)
        p.draw_line((margin, 46), (PAGE_W - margin, 46), color=GOLD_UL, width=0.9)
        return p, 66

    page, y = state
    if page is None:
        page, y = new_page()
    if y + 20 > bottom:
        page, y = new_page()
    page.insert_text((margin, y + 11), title, fontname=CJK, fontsize=12, color=GOLD)
    page.draw_line((margin, y + 16), (PAGE_W - margin, y + 16), color=GOLD_UL, width=0.7)
    y += 26
    for para in paragraphs:
        for ln in _wrap(para, size, max_w):
            if y + leading > bottom:
                page, y = new_page()
            page.insert_text((margin, y + size), ln, fontname=CJK, fontsize=size, color=DARK)
            y += leading
        y += 3
    state[0], state[1] = page, y


# ── entry ────────────────────────────────────────────────────────────────────
def generate_report_pdf(cert, images, notes, qr_png=None, logo_path=None) -> bytes:
    assets = {
        "inspector_signature": db.get_asset("inspector_signature"),
        "reviewer_signature": db.get_asset("reviewer_signature"),
        "stamp": db.get_asset("stamp"),
        "address_left": db.get_setting("address_left", ""),
        "address_right": db.get_setting("address_right", ""),
    }

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    _page1(page, cert, images, qr_png, logo_path, assets)

    state = [None, 0]
    content = _cv(cert, "inspect_content")
    if content.strip():
        _flow_section(doc, state, "鑑定內容", content.split("\n"))
    if notes:
        numbered = [f"{i}. {n}" for i, n in enumerate(notes, 1)]
        _flow_section(doc, state, "鑑定說明", numbered)

    out = io.BytesIO()
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    return out.getvalue()

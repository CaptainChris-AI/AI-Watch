"""
pdf_report.py — A5 横版 鉴定报告卡 PDF 生成（PyMuPDF / fitz）
图文平铺，可打印。内嵌该证书二维码。

页1：品牌头 + 检测编号/日期/有效期 + 细节图平铺 + 基本信息 + 样品结论 + 二维码
页2+：鉴定内容 + 鉴定说明（长文本自动分页平铺）

中文使用 PyMuPDF 内置 CJK 字体 "china-s"。
"""
from __future__ import annotations

import io
import fitz  # PyMuPDF
from pathlib import Path

from styles import BRAND_TITLE, ENG_SUBTITLE

# A5 横版（points）
PAGE_W = 595.28
PAGE_H = 419.53
MARGIN = 22
HEADER_H = 66

CJK = "china-s"


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


NAVY = _hex("#2B3A52")
GOLD = _hex("#C0A16B")
WHITE = (1, 1, 1)
DARK = _hex("#1E2B45")
GREY = _hex("#8A8F99")
LINE = _hex("#E2E2E6")


def _ctext(page, cx, y, text, font, size, color):
    """以 cx 为水平中心，用 insert_text 绘制（短框不丢字）。"""
    w = fitz.get_text_length(text, fontname=font, fontsize=size)
    page.insert_text((cx - w / 2, y), text, fontname=font, fontsize=size, color=color)


def _wrap(text: str, size: float, max_w: float) -> list[str]:
    """按字符贪心换行（适合中英混排/CJK 无空格）。"""
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
    return lines


def _draw_header(page, cert, logo_path: str | None, slim: bool = False):
    h = 40 if slim else HEADER_H
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, h), color=None, fill=NAVY)
    x = MARGIN
    if logo_path and Path(logo_path).exists():
        try:
            lh = 26 if slim else 40
            page.insert_image(
                fitz.Rect(x, (h - lh) / 2, x + lh, (h - lh) / 2 + lh),
                filename=logo_path, keep_proportion=True,
            )
            x += lh + 12
        except Exception:
            pass
    ty = 22 if slim else 28
    page.insert_text((x, ty), BRAND_TITLE, fontname=CJK,
                     fontsize=15 if slim else 18, color=WHITE)
    if not slim:
        page.insert_text((x, 48), ENG_SUBTITLE, fontname="helv",
                         fontsize=8, color=GOLD)


def _draw_summary_strip(page, cert, y):
    """检测编号 / 鉴定日期 / 有效期至 三列。"""
    box = fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 40)
    page.draw_rect(box, color=LINE, fill=(0.98, 0.98, 0.99), width=0.5)
    cols = [
        ("检测编号", cert["cert_no"]),
        ("鉴定日期", cert["inspect_date"] or "-"),
        ("有效期至", cert["valid_until"] or "-"),
    ]
    cw = (box.width) / 3
    for i, (label, val) in enumerate(cols):
        cx = box.x0 + i * cw + cw / 2
        _ctext(page, cx, y + 15, label, CJK, 8, GREY)
        _ctext(page, cx, y + 31, str(val), CJK, 11, DARK)
        if i > 0:
            page.draw_line((box.x0 + i * cw, y + 8),
                           (box.x0 + i * cw, y + 32), color=LINE, width=0.5)
    return box.y1


def _draw_images(page, images, rect):
    """在 rect 内 2 列网格平铺所有细节图。"""
    page.insert_text((rect.x0, rect.y0 + 9), "细节图片",
                     fontname=CJK, fontsize=9, color=GOLD)
    grid = fitz.Rect(rect.x0, rect.y0 + 16, rect.x1, rect.y1)
    n = len(images)
    if n == 0:
        _ctext(page, (grid.x0 + grid.x1) / 2, grid.y0 + 30, "（无图片）",
               CJK, 9, GREY)
        return
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    gap = 6
    cw = (grid.width - (cols - 1) * gap) / cols
    ch = (grid.height - (rows - 1) * gap) / rows
    for idx, (blob, _mime) in enumerate(images):
        r = idx // cols
        c = idx % cols
        cell = fitz.Rect(
            grid.x0 + c * (cw + gap), grid.y0 + r * (ch + gap),
            grid.x0 + c * (cw + gap) + cw, grid.y0 + r * (ch + gap) + ch,
        )
        page.draw_rect(cell, color=LINE, width=0.5)
        try:
            page.insert_image(cell, stream=blob, keep_proportion=True)
        except Exception:
            pass


def _draw_info(page, cert, rect, qr_png: bytes | None):
    """右侧：样品结论 + 基本信息 + 二维码。"""
    y = rect.y0
    # 样品结论
    page.insert_text((rect.x0, y + 9), "样品结论", fontname=CJK, fontsize=9, color=GOLD)
    y += 15
    concl = cert["sample_conclusion"] or "-"
    page.insert_text((rect.x0, y + 14), concl, fontname=CJK, fontsize=14, color=DARK)
    y += 26
    # 基本信息
    page.insert_text((rect.x0, y + 9), "基本信息", fontname=CJK, fontsize=9, color=GOLD)
    y += 16
    fields = [
        ("品牌", cert["brand"]), ("型号", cert["model"]),
        ("尺寸", cert["size"]), ("表壳编号", cert["case_no"]),
        ("机芯编号", cert["movement_no"]), ("表壳材质", cert["case_material"]),
        ("备注", cert["remark"]),
    ]
    label_w = 56
    val_w = rect.width - label_w - 6
    size = 9
    for label, val in fields:
        val = (val or "-")
        vlines = _wrap(val, size, val_w)
        row_h = max(14, len(vlines) * (size + 3) + 3)
        page.insert_text((rect.x0, y + size), label, fontname=CJK,
                         fontsize=size, color=GREY)
        vy = y + size
        for ln in vlines:
            page.insert_text((rect.x0 + label_w, vy), ln, fontname=CJK,
                             fontsize=size, color=DARK)
            vy += size + 3
        y += row_h
        page.draw_line((rect.x0, y - 3), (rect.x1, y - 3), color=LINE, width=0.4)

    # 二维码（右下角）
    if qr_png:
        qs = 74
        qr_rect = fitz.Rect(rect.x1 - qs, rect.y1 - qs, rect.x1, rect.y1)
        try:
            page.insert_image(qr_rect, stream=qr_png)
            page.insert_textbox(
                fitz.Rect(rect.x1 - qs - 90, rect.y1 - qs, rect.x1 - qs - 4, rect.y1),
                "扫码查看\n电子报告", fontname=CJK, fontsize=8, color=GREY,
                align=fitz.TEXT_ALIGN_RIGHT,
            )
        except Exception:
            pass


def _flow_section(doc, state, title, paragraphs, cert, logo_path):
    """把标题+段落平铺流式写入，越界自动新建页。state=[page,y]。"""
    size = 9
    leading = size + 4
    max_w = PAGE_W - 2 * MARGIN
    bottom = PAGE_H - MARGIN

    def new_page():
        p = doc.new_page(width=PAGE_W, height=PAGE_H)
        _draw_header(p, cert, logo_path, slim=True)
        return p, 40 + 16

    page, y = state
    if page is None:
        page, y = new_page()

    # 标题
    if y + 18 > bottom:
        page, y = new_page()
    page.insert_text((MARGIN, y + 11), title, fontname=CJK, fontsize=11, color=GOLD)
    page.draw_line((MARGIN, y + 16), (PAGE_W - MARGIN, y + 16), color=GOLD, width=0.6)
    y += 24

    for para in paragraphs:
        for ln in _wrap(para, size, max_w):
            if y + leading > bottom:
                page, y = new_page()
            page.insert_text((MARGIN, y + size), ln, fontname=CJK,
                             fontsize=size, color=DARK)
            y += leading
        y += 3  # 段间距
    state[0], state[1] = page, y


def generate_report_pdf(cert, images, notes, qr_png=None,
                        logo_path=None) -> bytes:
    """
    cert: sqlite3.Row / dict（含 CERT_FIELDS）
    images: [(bytes, mime), ...]
    notes: list[str] 鉴定说明
    qr_png: bytes 二维码 PNG
    logo_path: 品牌 logo 路径
    返回 PDF 字节。
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    _draw_header(page, cert, logo_path)

    y = _draw_summary_strip(page, cert, HEADER_H + 8)
    body_top = y + 10
    body_bottom = PAGE_H - MARGIN

    # 左：图片；右：信息
    mid = MARGIN + (PAGE_W - 2 * MARGIN) * 0.46
    img_rect = fitz.Rect(MARGIN, body_top, mid - 8, body_bottom)
    info_rect = fitz.Rect(mid + 8, body_top, PAGE_W - MARGIN, body_bottom)
    _draw_images(page, images, img_rect)
    _draw_info(page, cert, info_rect, qr_png)

    # 页2+：鉴定内容 + 鉴定说明
    state = [None, 0]
    content = cert["inspect_content"] or ""
    if content.strip():
        _flow_section(doc, state, "鉴定内容", content.split("\n"), cert, logo_path)
    if notes:
        numbered = [f"{i}. {n}" for i, n in enumerate(notes, 1)]
        _flow_section(doc, state, "鉴定说明", numbered, cert, logo_path)

    out = io.BytesIO()
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    return out.getvalue()

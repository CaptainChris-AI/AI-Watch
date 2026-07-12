"""
watch_db.py — HGSTC 名表国检中心 数据层
独立 SQLite 数据库 watch_cert.db，sqlite3 + Row factory + WAL（与 v2_db.py 同风格）。

表：
  certificates       证书主表
  certificate_images 细节图片（BLOB，一对多，做轮播/平铺）
  company_members    公司介绍-鉴定师（一对多）
  settings           全局公用配置（key-value）：鉴定说明 / 公司简介抬头 / 公司横幅 / base_url
"""
from __future__ import annotations

import sqlite3
import uuid
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "watch_cert.db"


# ─────────────────────────────────────────────────────────────────────────────
# 连接
# ─────────────────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ─────────────────────────────────────────────────────────────────────────────
# 初始化
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_NOTES = [
    "本报告结论以品牌方公示信息，及本中心成熟数据作为鉴定依据，如结论和品牌官方有差异，以品牌方为准。",
    "检测只对送检样品的检测内容负责，不涉及样品来源追溯，如出现法务争议，我司概不负责。",
    "本检测报告只针对送检样品做表况判定。附件品类及数量以我司收到的物品为准，不以整套或全套定义。保卡销售日期及官方保修情况以品牌售后确认的日期为准。",
    "不开盖前提下，壳内信息(如机芯、部分品牌壳号等)不在检测范围内。机芯及固定结构仅做可见面观察，如无委托人授权，不对手表做任何拆解。",
    "软质表带（皮质，橡胶，尼龙，等材料）、软质胶圈属消耗品，不在检测范围内。",
    "若手表有后覆膜且未撕开进行验视的，则覆膜处成色及翻新不在检测范围内，不做全面检测报告。",
    "功能检测中，机测反映为瞬时数据，动力时长有效性及自动上链效果不在检测范围内。有动力显示功能的腕表，仅测试手动上链与动力显示的联动状态。因检测时效有限，计时功能测试仅测试计时秒针与计时分针联动，计时功能长时间联动不在检测范围内。",
    "送检样品离开我司后,如发生任何拆解、改动，与该样品送检时特征不符，本鉴定报告失效。",
    "若对报告的内容和结论持有异议，请在报告签发15日内提出，逾期不予受理。",
    "检测报告查询有效期为180天。",
]

DEFAULT_COMPANY_INTRO = "HGSTC 名表国检中心，专注于名贵钟表鉴定检测，提供权威、专业、可追溯的第三方鉴定服务。"

DEFAULT_ADDRESS_LEFT = "香港尖沙咀赫德道6号好德商業大廈10楼A室"
DEFAULT_ADDRESS_RIGHT = "深圳市羅湖區寶安南路1036號鼎豐大廈16樓1623室"


def init_db():
    """初始化所有表，并写入默认的鉴定说明 / 公司简介。幂等。"""
    with get_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS certificates (
            id                TEXT PRIMARY KEY,
            cert_no           TEXT NOT NULL UNIQUE,      -- 检测编号
            brand             TEXT DEFAULT '',           -- 品牌
            model             TEXT DEFAULT '',           -- 型号
            size              TEXT DEFAULT '',           -- 尺寸
            case_no           TEXT DEFAULT '',           -- 表壳编号
            movement_no       TEXT DEFAULT '',           -- 机芯编号
            case_material     TEXT DEFAULT '',           -- 表壳材质
            remark            TEXT DEFAULT '',           -- 备注
            inspect_date      TEXT DEFAULT '',           -- 鉴定日期 YYYY-MM-DD
            valid_until       TEXT DEFAULT '',           -- 有效期至 YYYY-MM-DD
            sample_conclusion TEXT DEFAULT '',           -- 样品结论（如 正品）
            inspect_content   TEXT DEFAULT '',           -- 鉴定内容（长文本）
            status            TEXT DEFAULT '',           -- 状态（如 已使用品/全新）
            warranty_card_info TEXT DEFAULT '',          -- 保卡资讯
            origin            TEXT DEFAULT '',           -- 产地
            strap             TEXT DEFAULT '',           -- 表带
            water_resistance  TEXT DEFAULT '',           -- 防水
            functions         TEXT DEFAULT '',           -- 功能
            accessories       TEXT DEFAULT '',           -- 附件
            amplitude         TEXT DEFAULT '',           -- 摆幅
            data_metrics      TEXT DEFAULT '',           -- 数据（走时等）
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS certificate_images (
            id          TEXT PRIMARY KEY,
            cert_id     TEXT NOT NULL REFERENCES certificates(id) ON DELETE CASCADE,
            image       BLOB NOT NULL,
            mime        TEXT DEFAULT 'image/jpeg',
            sort_order  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS company_members (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            credentials  TEXT DEFAULT '',
            photo        BLOB,
            mime         TEXT DEFAULT 'image/jpeg',
            sort_order   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS report_assets (
            key   TEXT PRIMARY KEY,
            image BLOB,
            mime  TEXT DEFAULT 'image/png'
        );

        CREATE TABLE IF NOT EXISTS masters (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            signature  BLOB,
            mime       TEXT DEFAULT 'image/png',
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        """)

    # 迁移：给已有的 certificates 表补齐新列（幂等）
    _migrate_cert_columns()

    # 默认设置
    if get_setting("inspection_notes") is None:
        set_setting("inspection_notes", json.dumps(DEFAULT_NOTES, ensure_ascii=False))
    if get_setting("company_intro") is None:
        set_setting("company_intro", DEFAULT_COMPANY_INTRO)
    if get_setting("address_left") is None:
        set_setting("address_left", DEFAULT_ADDRESS_LEFT)
    if get_setting("address_right") is None:
        set_setting("address_right", DEFAULT_ADDRESS_RIGHT)

    # 预置两位师傅（仅当没有任何师傅时）
    if not list_masters():
        add_master("蔡新", _gen_signature("蔡新-inspector"))
        add_master("蔡新新", _gen_signature("蔡新新-reviewer"))


_MIGRATE_COLUMNS = [
    ("status", "TEXT DEFAULT ''"),
    ("warranty_card_info", "TEXT DEFAULT ''"),
    ("origin", "TEXT DEFAULT ''"),
    ("strap", "TEXT DEFAULT ''"),
    ("water_resistance", "TEXT DEFAULT ''"),
    ("functions", "TEXT DEFAULT ''"),
    ("accessories", "TEXT DEFAULT ''"),
    ("amplitude", "TEXT DEFAULT ''"),
    ("data_metrics", "TEXT DEFAULT ''"),
    ("inspector_master", "TEXT DEFAULT ''"),
    ("reviewer_master", "TEXT DEFAULT ''"),
]


def _migrate_cert_columns():
    with get_conn() as c:
        existing = {r["name"] for r in c.execute("PRAGMA table_info(certificates)")}
        for col, decl in _MIGRATE_COLUMNS:
            if col not in existing:
                c.execute(f"ALTER TABLE certificates ADD COLUMN {col} {decl}")


# ─────────────────────────────────────────────────────────────────────────────
# settings (key-value)
# ─────────────────────────────────────────────────────────────────────────────
def get_setting(key: str, default=None):
    with get_conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as c:
        c.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_inspection_notes() -> list[str]:
    raw = get_setting("inspection_notes")
    if not raw:
        return list(DEFAULT_NOTES)
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else list(DEFAULT_NOTES)
    except Exception:
        return list(DEFAULT_NOTES)


def set_inspection_notes(notes: list[str]):
    clean = [n.strip() for n in notes if n and n.strip()]
    set_setting("inspection_notes", json.dumps(clean, ensure_ascii=False))


# ─────────────────────────────────────────────────────────────────────────────
# certificates
# ─────────────────────────────────────────────────────────────────────────────
CERT_FIELDS = [
    "cert_no", "brand", "model", "size", "case_no", "movement_no",
    "case_material", "remark", "inspect_date", "valid_until",
    "sample_conclusion", "inspect_content",
    "status", "warranty_card_info", "origin", "strap", "water_resistance",
    "functions", "accessories", "amplitude", "data_metrics",
    "inspector_master", "reviewer_master",
]


def create_certificate(data: dict, images: list[tuple[bytes, str]] | None = None) -> str:
    """新建证书。images = [(bytes, mime), ...]。返回 cert id。"""
    cid = _new_id()
    cols = ["id"] + CERT_FIELDS
    vals = [cid] + [data.get(f, "") for f in CERT_FIELDS]
    placeholders = ",".join("?" for _ in cols)
    with get_conn() as c:
        c.execute(
            f"INSERT INTO certificates ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        if images:
            for i, (blob, mime) in enumerate(images):
                c.execute(
                    "INSERT INTO certificate_images(id,cert_id,image,mime,sort_order) "
                    "VALUES(?,?,?,?,?)",
                    (_new_id(), cid, blob, mime or "image/jpeg", i),
                )
    return cid


def update_certificate(cid: str, data: dict):
    sets = ",".join(f"{f}=?" for f in CERT_FIELDS)
    vals = [data.get(f, "") for f in CERT_FIELDS] + [cid]
    with get_conn() as c:
        c.execute(f"UPDATE certificates SET {sets} WHERE id=?", vals)


def replace_certificate_images(cid: str, images: list[tuple[bytes, str]]):
    with get_conn() as c:
        c.execute("DELETE FROM certificate_images WHERE cert_id=?", (cid,))
        for i, (blob, mime) in enumerate(images):
            c.execute(
                "INSERT INTO certificate_images(id,cert_id,image,mime,sort_order) "
                "VALUES(?,?,?,?,?)",
                (_new_id(), cid, blob, mime or "image/jpeg", i),
            )


def delete_certificate(cid: str):
    with get_conn() as c:
        c.execute("DELETE FROM certificates WHERE id=?", (cid,))


def get_certificate(cid: str):
    with get_conn() as c:
        return c.execute("SELECT * FROM certificates WHERE id=?", (cid,)).fetchone()


def get_certificate_by_no(cert_no: str):
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM certificates WHERE cert_no=?", (cert_no,)
        ).fetchone()


def list_certificates(keyword: str = "") -> list:
    with get_conn() as c:
        if keyword:
            kw = f"%{keyword}%"
            return c.execute(
                "SELECT * FROM certificates WHERE cert_no LIKE ? OR brand LIKE ? "
                "OR model LIKE ? ORDER BY created_at DESC",
                (kw, kw, kw),
            ).fetchall()
        return c.execute(
            "SELECT * FROM certificates ORDER BY created_at DESC"
        ).fetchall()


def cert_no_exists(cert_no: str) -> bool:
    with get_conn() as c:
        return c.execute(
            "SELECT 1 FROM certificates WHERE cert_no=?", (cert_no,)
        ).fetchone() is not None


def get_certificate_images(cid: str) -> list:
    """返回 [(bytes, mime), ...] 按 sort_order。"""
    with get_conn() as c:
        rows = c.execute(
            "SELECT image, mime FROM certificate_images WHERE cert_id=? "
            "ORDER BY sort_order",
            (cid,),
        ).fetchall()
    return [(r["image"], r["mime"]) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# company_members
# ─────────────────────────────────────────────────────────────────────────────
def add_company_member(name: str, credentials: str,
                       photo: bytes | None = None, mime: str = "image/jpeg") -> str:
    mid = _new_id()
    with get_conn() as c:
        nxt = c.execute(
            "SELECT COALESCE(MAX(sort_order),-1)+1 AS n FROM company_members"
        ).fetchone()["n"]
        c.execute(
            "INSERT INTO company_members(id,name,credentials,photo,mime,sort_order) "
            "VALUES(?,?,?,?,?,?)",
            (mid, name, credentials, photo, mime, nxt),
        )
    return mid


def update_company_member(mid: str, name: str, credentials: str,
                          photo: bytes | None = None, mime: str | None = None):
    with get_conn() as c:
        if photo is not None:
            c.execute(
                "UPDATE company_members SET name=?,credentials=?,photo=?,mime=? WHERE id=?",
                (name, credentials, photo, mime or "image/jpeg", mid),
            )
        else:
            c.execute(
                "UPDATE company_members SET name=?,credentials=? WHERE id=?",
                (name, credentials, mid),
            )


def delete_company_member(mid: str):
    with get_conn() as c:
        c.execute("DELETE FROM company_members WHERE id=?", (mid,))


def list_company_members() -> list:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM company_members ORDER BY sort_order"
        ).fetchall()


# ─────────────────────────────────────────────────────────────────────────────
# report_assets（检验师/复检师 签名图、印章）
# ─────────────────────────────────────────────────────────────────────────────
def get_asset(key: str):
    """返回 (bytes, mime) 或 None。"""
    with get_conn() as c:
        row = c.execute(
            "SELECT image, mime FROM report_assets WHERE key=?", (key,)
        ).fetchone()
    if row and row["image"]:
        return row["image"], row["mime"]
    return None


def set_asset(key: str, image: bytes, mime: str = "image/png"):
    with get_conn() as c:
        c.execute(
            "INSERT INTO report_assets(key,image,mime) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET image=excluded.image, mime=excluded.mime",
            (key, image, mime),
        )


def delete_asset(key: str):
    with get_conn() as c:
        c.execute("DELETE FROM report_assets WHERE key=?", (key,))


# ─────────────────────────────────────────────────────────────────────────────
# masters（鉴定师 / 师傅：检验师、复检师可下拉选择）
# ─────────────────────────────────────────────────────────────────────────────
def list_masters() -> list:
    with get_conn() as c:
        return c.execute("SELECT * FROM masters ORDER BY sort_order").fetchall()


def get_master(mid: str):
    if not mid:
        return None
    with get_conn() as c:
        return c.execute("SELECT * FROM masters WHERE id=?", (mid,)).fetchone()


def add_master(name: str, signature: bytes | None = None, mime: str = "image/png") -> str:
    mid = _new_id()
    with get_conn() as c:
        nxt = c.execute(
            "SELECT COALESCE(MAX(sort_order),-1)+1 AS n FROM masters"
        ).fetchone()["n"]
        c.execute(
            "INSERT INTO masters(id,name,signature,mime,sort_order) VALUES(?,?,?,?,?)",
            (mid, name, signature, mime, nxt),
        )
    return mid


def update_master(mid: str, name: str,
                  signature: bytes | None = None, mime: str | None = None):
    with get_conn() as c:
        if signature is not None:
            c.execute(
                "UPDATE masters SET name=?,signature=?,mime=? WHERE id=?",
                (name, signature, mime or "image/png", mid),
            )
        else:
            c.execute("UPDATE masters SET name=? WHERE id=?", (name, mid))


def delete_master(mid: str):
    with get_conn() as c:
        c.execute("DELETE FROM masters WHERE id=?", (mid,))


def _gen_signature(seed: str) -> bytes:
    """用 PIL 生成一个随机手写风格的签名 PNG（透明背景）。seed 决定形状，稳定可复现。"""
    import io as _io
    import math
    import random
    from PIL import Image, ImageDraw

    rnd = random.Random(seed)
    W, H = 360, 120
    im = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    ink = (25, 30, 60, 255)
    y0 = H * 0.58
    freq = rnd.uniform(5.5, 9.5)
    phase = rnd.uniform(0, 3.14)
    amp = rnd.uniform(16, 28)
    tilt = rnd.uniform(-0.10, 0.10)
    steps = 160
    path = []
    for s in range(steps + 1):
        t = s / steps
        px = 24 + t * (W - 60)
        env = math.sin(t * math.pi)  # 两端收窄
        py = y0 + math.sin(t * freq * math.pi + phase) * amp * env + (t - 0.5) * (W * tilt)
        path.append((px, py))
    d.line(path, fill=ink, width=4, joint="curve")
    # 末尾一个上挑的花体
    ex, ey = path[-1]
    flourish = [(ex, ey)]
    for k in range(24):
        a = k / 24
        flourish.append((ex + a * 46, ey - math.sin(a * math.pi) * rnd.uniform(28, 40)))
    d.line(flourish, fill=ink, width=3, joint="curve")
    # 一条底部横划
    d.line([(28, y0 + amp * 0.7), (W - 46, y0 + amp * 0.7 + rnd.uniform(-4, 4))],
           fill=ink, width=2)
    buf = _io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()

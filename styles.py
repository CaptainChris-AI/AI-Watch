"""
styles.py — 全局样式与配色常量
配色取自参考站截图。
"""

# ── 品牌配色 ──────────────────────────────────────────────────────────────
NAVY = "#2B3A52"       # 深藏青（头部/激活tab）
NAVY_DARK = "#1E2B45"  # 更深藏青（文字）
GOLD = "#C0A16B"       # 金色（主色/标题/激活文字）
GOLD_LIGHT = "#D8BE8C"
PAGE_BG = "#F0F0F2"    # 浅灰页面底
CARD_BG = "#FFFFFF"
TEXT_MUTED = "#8A8F99"
LINE = "#ECECEF"

ENG_SUBTITLE = "HGSTC Luxury Watch Inspection Center"
BRAND_TITLE = "HGSTC 名表国检中心"

# ── 管理后台 CSS：隐藏 Streamlit 默认水印/部署按钮 ─────────────────────────
ADMIN_CSS = """
<style>
#MainMenu {visibility: hidden;}
[data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stDeployButton"] {display: none !important;}
.stAppDeployButton {display: none !important;}
footer {visibility: hidden;}

/* 后台品牌头 */
.hgstc-admin-head {
    display:flex; align-items:center; gap:14px;
    background: #2B3A52; padding:14px 20px; border-radius:12px;
    margin-bottom:18px;
}
.hgstc-admin-head img { height:44px; border-radius:6px; }
.hgstc-admin-head .t1 { color:#fff; font-size:20px; font-weight:700; line-height:1.2; }
.hgstc-admin-head .t2 { color:#C0A16B; font-size:12px; letter-spacing:.5px; }

/* 登录卡片 */
.hgstc-login-title { text-align:center; color:#2B3A52; font-weight:700;
    font-size:22px; margin:8px 0 2px; }
.hgstc-login-sub { text-align:center; color:#C0A16B; font-size:12px;
    letter-spacing:1px; margin-bottom:18px; }
</style>
"""

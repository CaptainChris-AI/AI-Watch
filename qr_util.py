"""
qr_util.py — 二维码生成
二维码内容 = {base_url}/?cert={检测编号}，用户扫码进入手机端查看页。
"""
import io
import qrcode


def build_cert_url(base_url: str, cert_no: str) -> str:
    base = (base_url or "").rstrip("/")
    return f"{base}/?cert={cert_no}"


def make_qr_png(data: str, box_size: int = 10, border: int = 2) -> bytes:
    """生成二维码 PNG 字节。"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E2B45", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_cert_qr(base_url: str, cert_no: str, box_size: int = 10) -> bytes:
    return make_qr_png(build_cert_url(base_url, cert_no), box_size=box_size)

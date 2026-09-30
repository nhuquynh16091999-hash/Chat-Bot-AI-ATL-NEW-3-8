"""Vá 19/09 — page còn gói nằm ở shop POS riêng → gắn vào thị trường theo TIỀN TỆ page báo giá.

Chủ shop 19/09: *"mà rõ ràng tôi bảo theo đơn vị tiền tệ mà gắn rồi còn gì"*. Ca Angaray Wazir · Gilded Grace
(AED): khách "I need one gram gold" 14:46 VN, AI không trông page này nên im, sale Nguyễn Duyên xem 14:51.
File state/chung/page_gan_them.json {tt: {pid: ghi chú}}; _pages_cua_shop cộng thêm các page đó. Page không có
token page thì _pages_khong_quyen đưa vào kênh tài khoản như mọi page khác; kịch bản tự kéo (_keo_kich_ban_thieu).
Chạy: python3 va_gan_theo_tien_te.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_page_gan_them" in src:
    sys.exit("đã vá rồi (có _page_gan_them) — không làm gì")

VA = [
    ("def _pages_cua_shop(mkey):\n",
     '''def _page_gan_them(mkey):
    """19/09 (chủ shop: "rõ ràng tôi bảo theo đơn vị tiền tệ mà gắn rồi còn gì"): page còn gói nhưng thuộc shop POS
    RIÊNG (không có trong markets.json) → gắn vào thị trường theo tiền tệ page báo giá (AED→uae, NT$/TWD→taiwan…).
    Nguồn: state/chung/page_gan_them.json {tt: {pid: ghi chú}}. Đọc lại mỗi lần gọi → sửa file không cần restart
    (vòng dò tra lại danh sách page 10 phút/lần). Hỏng/thiếu file → không gắn thêm gì."""
    try:
        d = json.load(open(os.path.join(SCRIPT_DIR, "state", "chung", "page_gan_them.json"), encoding="utf-8"))
        return {str(p) for p in (d.get(mkey) or {})}
    except Exception:                                    # noqa: BLE001
        return set()


def _pages_cua_shop(mkey):
'''),
    ('''            return {str(x.get("id")) for x in (sh.get("pages") or []) if x.get("id")}
    return set()
''',
     '''            return {str(x.get("id")) for x in (sh.get("pages") or []) if x.get("id")} | _page_gan_them(mkey)
    return _page_gan_them(mkey)
'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:160]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá 2 chỗ")

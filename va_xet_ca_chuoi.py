"""Vá 19/09 — xét CẢ CHUỖI tin khách chưa được đáp, không chỉ tin cuối.

Ca محمد حامد محمد المحسي · Nature's Daily Care in Saudi: AI báo giá 14:01, khách 14:03:08 "اريد علبه واحده"
(muốn 1 hộp) + 14:03:14 "للتجربه" (để dùng thử). ai_co_vao_cuoc chỉ nhìn tin cuối, 1 chữ → vo_nghia → treo,
sale Từ Trang rep 14:11. Sửa: còn MỘT tin trong chuỗi có nội dung là không treo / không im.
Chạy: python3 va_xet_ca_chuoi.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_chuoi_kh" in src:
    sys.exit("đã vá rồi (có _chuoi_kh) — không làm gì")
if "_tu_go" not in src:
    sys.exit("thiếu vá _tu_go (va_hoi_gia_tu_go.py) — vá cái đó trước")

VA = [
    ('''                  and 5 <= _cach_ <= 6 * 3600)
''',
     '''                  and 5 <= _cach_ <= 6 * 3600)
    # 19/09 (ca محمد حامد المحسي · Nature's Daily Care in Saudi): khách gửi liền "اريد علبه واحده" (muốn 1 hộp) +
    # "للتجربه" (để dùng thử) — hàm chỉ nhìn tin CUỐI (1 chữ) → treo, sale rep sau 8 phút. Mọi cửa "không có gì để
    # trả lời" giờ xét CẢ chuỗi tin khách liền nhau chưa được đáp: còn một tin có nội dung là phải trả lời.
    _chuoi_kh = msgs[i - len(_lien) + 1:i + 1]
    _chuoi_co_nd = any(_tin_co_noi_dung(lam_sach(m.get("text") or "").strip()) for m in _chuoi_kh)
'''),
    ('''        if len(bot_sau) >= 2 and not _tin_co_noi_dung(chu_cuoi):''',
     '''        if len(bot_sau) >= 2 and not _chuoi_co_nd:'''),
    ('''        if not _tin_co_noi_dung(chu_cuoi):
            return "im", "khách chỉ chào/đáp ngắn — Botcake đã rep là đủ, không cần đọc lại"''',
     '''        if not _chuoi_co_nd:
            return "im", "khách chỉ chào/đáp ngắn — Botcake đã rep là đủ, không cần đọc lại"'''),
    ('''    if vo_nghia(cuoi["text"], cuoi.get("co_dinh_kem")) and not (
            _tu_go and HOI_GIA.search(lam_sach(cuoi["text"]).lower())):''',
     '''    if all(vo_nghia(m["text"], m.get("co_dinh_kem")) and not (
            _tu_go and HOI_GIA.search(lam_sach(m["text"]).lower())) for m in _chuoi_kh):'''),
]
# Glamora Jewelry 19/09: nút QC "Magkanu po" (gõ u thay o) không khớp tin mẫu → khi xét cả chuỗi thành "có nội dung"
VA += [
    (r'''    r"|mag\s*ka+no|mag\s*kno|mg\s*ka?no|mgkno|pila|presyo"''',
     r'''    r"|mag\s*ka+n[ou]|mag\s*kno|mg\s*ka?n[ou]|mgkno|pila|presyo"'''),
    (r"|magkano|m[ae]?g\s*k[ae]?no|", r"|magkano|m[ae]?g\s*k[ae]?n[ou]|"),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:160]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ")

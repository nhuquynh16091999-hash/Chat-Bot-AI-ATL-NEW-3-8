"""Vá 19/09 — khách CHỌN GÓI bằng câu ngắn ("One", "2 sets", "isa") không phải "không có gì để trả lời".

Ca Fatima Miftah · ChunHo Golden Jewerly (Saudi): Botcake gửi bảng giá "159 SAR - 1 Necklace / 259 SAR - 2 Necklaces…",
16:18:31 VN khách trả lời thẳng vào tin đó "One" → ai_co_vao_cuoc: 1 chữ → vo_nghia → treo "Botcake im mà tin khách không
có gì để trả lời"; sale Từ Trang rep 16:23 ("159 SAR - 1 Necklace" + xin thông tin). *"sao b k rep"*.
Hàm khach_vua_chon_goi (luật "khách chọn gói thì xin thông tin") có sẵn nhưng chỉ chạy SAU khi quyet đã là tra_loi.
Sửa: ngay sau ai_co_vao_cuoc trong cmd_chay, treo-vì-vô-nghĩa mà khach_vua_chon_goi bắt được → tra_loi.
Chạy: python3 va_chon_goi_ngan.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "ca Fatima Miftah" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = [
    ('''            quyet, ly_do = ai_co_vao_cuoc(msgs)
            khach = [m for m in msgs if m["boi"] == "khach"]
''',
     '''            quyet, ly_do = ai_co_vao_cuoc(msgs)
            # 19/09 (ca Fatima Miftah · ChunHo Golden Jewerly): Botcake gửi bảng giá, khách đáp "One" (chọn 1 dây
            # chuyền) → 1 chữ nên vo_nghia → treo, sale rep sau 5 phút. Câu CHỌN GÓI ngắn là việc của AI: xác nhận
            # gói + xin thông tin (luật "khách chọn gói thì xin thông tin"; cửa _goi_ bên dưới lo phần soạn).
            # Số trơn "1"/"2" (hay "وحده") ngay sau tin có bảng giá cũng là chọn gói — hàm kia không bắt số trơn.
            if quyet == "treo" and ly_do.startswith("Botcake im mà tin khách không có gì để trả lời"):
                _tr_ = next((m for m in reversed(msgs) if m["boi"] in ("botcake", "nguoi", "ai")), None)
                _kh_ = next((lam_sach(m.get("text") or "").strip() for m in reversed(msgs) if m["boi"] == "khach"), "")
                if khach_vua_chon_goi(msgs, mkey, gia) or (
                        re.match(r"^\W*(?:[1-6]|[١-٦]|وحده|وحدة|واحده|واحدة|ثنتين|اثنين|اثنتين)\W*$", _kh_)
                        and _tr_ is not None and CG.tien_trong(_tr_.get("text"))):
                    quyet, ly_do = "tra_loi", "khách chọn gói/số lượng bằng câu ngắn — xác nhận gói + xin thông tin"
            khach = [m for m in msgs if m["boi"] == "khach"]
'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:200]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ")

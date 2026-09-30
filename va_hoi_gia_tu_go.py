"""Vá 19/09 — khách TỰ GÕ hỏi giá sau khi Botcake/page đã rep thì AI phải rep, không coi là tin mẫu quảng cáo.

Chủ shop 19/09, ca Hujat Khan · Golden Grace PH (Saudi): khách bấm quảng cáo ("Start" ×3 cùng giây với
"replied to an ad"), Botcake chào + 2 ảnh, 28 giây sau khách tự gõ "قیمت" (Urdu: giá). AI treo "không có gì để
trả lời" (1 chữ → vo_nghia), sale Nguyễn Duyên phải rep sau 2 phút. *"nhưng đâu có bấm đâu, nhắn sau đó nữa r mà"*
· *"ý là trước đó nhấp, xong botcake đã rep, sau đó khách nhắn tới tiếp hỏi giá"*.

Luật 14/09 (tin mẫu quảng cáo → sale) chỉ dành cho tin do NÚT quảng cáo sinh ra: tới trước khi page rep gì.
Tin khách nằm ngay sau một tin Botcake/sale/AI (trong 6 giờ) là khách tự gõ → không phải tin mẫu, và câu hỏi giá
một chữ ("قیمت", "price") không còn bị coi là "không có gì để trả lời".
Chạy: python3 va_hoi_gia_tu_go.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_tu_go" in src:
    sys.exit("đã vá rồi (có _tu_go) — không làm gì")

VA = [
    # 1. "giá" tiếng Urdu/Ba Tư vào danh sách tin mẫu (bấm nút QC rồi gõ trơn "قیمت" = như "price")
    ('|多少錢|多少|價格|价格"\n    r")(?:\\W+(?:po+h?|',
     '|多少錢|多少|價格|价格|قیمت|قيمت"\n    r")(?:\\W+(?:po+h?|'),
    # 2. tin mẫu chỉ khi CHƯA có page rep ngay trước
    ('''    if any(_lien) and all(not t or TIN_MAU_QC.match(t) for t in _lien):
        if "botcake" in sau:''',
     '''    # 19/09 (chủ shop, ca Hujat Khan · Golden Grace PH): luật 14/09 chỉ dành cho tin do NÚT quảng cáo sinh ra —
    # tới cùng lúc "replied to an ad"/câu chào tự động, TRƯỚC khi page rep gì. Khách bấm quảng cáo, Botcake chào
    # xong rồi khách TỰ GÕ hỏi giá ("قیمت" 28s sau) là câu hỏi thật → AI rep. Tin ngay trước chuỗi tin khách là
    # Botcake/sale/AI, cách ≥5 giây (tin nút QC tới dính sát tin Botcake 0-2s — ca Cloves Tea 19/09 cách 1s)
    # và trong 6 giờ ⇒ khách tự gõ.
    _truoc_lien = msgs[i - len(_lien)] if i - len(_lien) >= 0 else None
    _cach_ = (_giay_tu(_truoc_lien.get("luc")) - _giay_tu(msgs[i - len(_lien) + 1].get("luc"))
              if _truoc_lien is not None else -1)
    _tu_go = bool(_truoc_lien is not None and _truoc_lien["boi"] in ("botcake", "nguoi", "ai")
                  and 5 <= _cach_ <= 6 * 3600)
    if any(_lien) and not _tu_go and all(not t or TIN_MAU_QC.match(t) for t in _lien):
        if "botcake" in sau:'''),
    # 3. câu hỏi giá 1 chữ khách tự gõ không phải "vô nghĩa"
    ('''    if vo_nghia(cuoi["text"], cuoi.get("co_dinh_kem")):
        return "treo", "Botcake im mà tin khách không có gì để trả lời — ghi chú 'sale check tin nhắn'"''',
     '''    if vo_nghia(cuoi["text"], cuoi.get("co_dinh_kem")) and not (
            _tu_go and HOI_GIA.search(lam_sach(cuoi["text"]).lower())):
        return "treo", "Botcake im mà tin khách không có gì để trả lời — ghi chú 'sale check tin nhắn'"'''),
    # 4. HOI_GIA biết "قيمت" gõ bằng bàn phím Ả Rập (ي thay ی)
    ('r"|كم|بكم|السعر|سعر|كام|قیمت|قيمة|کتنے|کتنی|کتنا"',
     'r"|كم|بكم|السعر|سعر|كام|قیمت|قيمت|قيمة|کتنے|کتنی|کتنا"'),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:160]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá 4 chỗ")

"""Vá 19/09 — khách CHƯA AI TRẢ LỜI thì AI vẫn rep tới 60 phút, và khởi động lại nhìn lại 60 phút cho hội thoại khách nhắn cuối.

Chủ shop 19/09: *"nhưng b vẫn trả lời dc đây thây"*. Khung AI mù 14:53-15:16 VN (12 page kênh tài khoản Saudi vắng):
Faizal Marohom (ClearVision Saudi) "Coll me / What time u delevery" 15:00 → sale rep sau 63 phút; Nobasac Artz (Veloura Lip
Beauty Saudi) "Sunday morning please" 15:01 → sale rep sau 49 phút. 15:16 AI khởi động lại, page về, nhưng lượt mồi chỉ nhìn
lại 10 phút → 2 hội thoại (15-16 phút) bị ghi là "đã thấy", KHÔNG BAO GIỜ được xử; và dù được xử thì luật tin cũ 10 phút cũng im.

Sửa (chỉ cho khách CHƯA AI trả lời — sau tin khách không có tin Botcake/sale/AI nào):
- `tin_khach_cu(cuoi, chua_ai_rep)`: ngưỡng nới lên AI_TIN_CHUA_REP_PHUT (60). Ca gốc luật tin cũ (Mine Peralta, 6,5 tiếng,
  Botcake đã follow-up sau tin khách) vẫn im như cũ.
- Lượt mồi sau khởi động lại: hội thoại khách gửi cuối, đổi trong AI_TIN_CHUA_REP_PHUT phút → vẫn đưa vào xử.
Chạy: python3 va_tin_chua_ai_rep.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "AI_TIN_CHUA_REP_PHUT" in src:
    sys.exit("đã vá rồi (có AI_TIN_CHUA_REP_PHUT) — không làm gì")

VA = [
    ("def tin_khach_cu(cuoi):\n", "def tin_khach_cu(cuoi, chua_ai_rep=False):\n"),
    ('''    phut = _so_env("AI_TIN_CU_PHUT", 10)
    if not cuoi or phut <= 0:''',
     '''    phut = _so_env("AI_TIN_CU_PHUT", 10)
    # 19/09 (chủ shop: "nhưng b vẫn trả lời dc đây thây" — ca Faizal Marohom / Nobasac Artz, AI mù 23 phút rồi sale
    # rep sau 49-63 phút): khách CHƯA AI trả lời (sau tin khách không có Botcake/sale/AI) thì còn rep tới
    # AI_TIN_CHUA_REP_PHUT (60). Ca gốc Mine Peralta có Botcake follow-up sau tin khách → vẫn im.
    if chua_ai_rep and phut > 0:
        phut = max(phut, _so_env("AI_TIN_CHUA_REP_PHUT", 60))
    if not cuoi or phut <= 0:'''),
    ('''            _cu = tin_khach_cu(cuoi) if quyet in ("tra_loi", "xet") else None''',
     '''            _cu = tin_khach_cu(cuoi, chua_ai_rep=bool(cuoi) and not any(
                m.get("boi") in ("botcake", "nguoi", "ai") and (m.get("luc") or "") > (cuoi.get("luc") or "")
                for m in msgs)) if quyet in ("tra_loi", "xet") else None'''),
    ('''                    if ai_g != "nguoi" and moc and _giay_tu(moc) < 600:
                        moi.add(cid)
                    continue''',
     '''                    if ai_g != "nguoi" and moc and _giay_tu(moc) < 600:
                        moi.add(cid)
                    # 19/09 (ca Faizal Marohom / Nobasac Artz): khởi động lại sau lúc AI mù → khách nhắn cuối, chưa ai
                    # trả lời, trong AI_TIN_CHUA_REP_PHUT phút cũng xử (trước: chỉ 10 phút → bị ghi "đã thấy" rồi bỏ luôn).
                    elif ai_g == "khach" and moc and _giay_tu(moc) < _so_env("AI_TIN_CHUA_REP_PHUT", 60) * 60:
                        moi.add(cid)
                    continue'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:200]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ")

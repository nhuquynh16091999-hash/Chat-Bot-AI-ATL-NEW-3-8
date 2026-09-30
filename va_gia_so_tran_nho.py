"""Vá 19/09 — số trần (không ký hiệu tiền) quá nhỏ so với giá có ký hiệu trong cùng mẫu KHÔNG phải giá.

Ca ChunHo Golden Jewerly (Saudi): mẫu /giá viết "LAST FINAL 10 SLOTS with 50% SALE OFF only TODAY : 199 SAR - 1 Necklace…"
→ _so_tien nhặt số trần 10 → mức bán [10, 199, 249…], SÀN THẤP NHẤT 9 SAR (log "mức bán [10, …] · sàn thấp nhất 9").
Khách trả "10 riyal" là lọt cửa "≥ sàn nhận luôn". Luật loại trừ theo danh từ đơn vị (days/pcs/years…) không có "slots".
Sửa chung: bỏ số trần < 30% mức CÓ ký hiệu tiền thấp nhất trong cùng đoạn (số có ký hiệu thì giữ nguyên).
Chạy: python3 va_gia_so_tran_nho.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "LAST FINAL 10 SLOTS" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = [
    ('''            t, flags=re.I)]
    return ra


def bo_gia(kb_page, mkey=None):
''',
     '''            t, flags=re.I)]
        # 19/09 (ChunHo Golden Jewerly: "LAST FINAL 10 SLOTS with 50% SALE OFF : 199 SAR…" → mức giá 10, sàn 9 SAR):
        # số TRẦN nhỏ hơn 30% mức CÓ ký hiệu tiền thấp nhất trong cùng đoạn là số marketing (suất, năm, %), không phải giá.
        _ky_hieu_ = CG.tien_trong(t)
        if _ky_hieu_:
            ra = [x for x in ra if x in _ky_hieu_ or x >= 0.3 * min(_ky_hieu_)]
    return ra


def bo_gia(kb_page, mkey=None):
'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:220]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ")

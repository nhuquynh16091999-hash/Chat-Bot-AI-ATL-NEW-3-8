"""Hai hàm cùng tên gia_page_da_bao (bản 642 trả set cho cửa từ chối; bản ~2021 trả (set, câu) cho ca Aruna)
→ bản sau đè bản trước → tinh_huong_tu_choi trả tuple → lượt văng TypeError. Đổi tên bản đầu."""
import sys
f = "ai_sale.py"; s = open(f, encoding="utf-8").read()
if s.count("def gia_page_da_bao(msgs):") != 2:
    sys.exit(f"✖ số định nghĩa gia_page_da_bao = {s.count('def gia_page_da_bao(msgs):')} (cần 2) — không ghi")
cap = [
    ('def gia_page_da_bao(msgs):\n    """Mọi con số tiền phía page (bot/sale/AI/hệ thống) đã nói trong hội thoại."""\n',
     'def tien_page_da_noi(msgs):\n    """Mọi con số tiền phía page (bot/sale/AI/hệ thống) đã nói trong hội thoại.\n\n'
     '    Đổi tên 14/09: trùng tên với gia_page_da_bao (ca Aruna, trả (tập, câu)) → bản sau đè bản này,\n'
     '    cửa từ chối nhận tuple → cả lượt văng TypeError. Hai hàm khác nghĩa, đừng gộp tên lại.\n    """\n'),
    ('    return lam_sach(kh[-1]["text"])[:120], min(lan, 3), gia_page_da_bao(msgs)\n',
     '    return lam_sach(kh[-1]["text"])[:120], min(lan, 3), tien_page_da_noi(msgs)\n'),
]
for a, b in cap:
    if s.count(a) != 1:
        sys.exit(f"✖ khớp {s.count(a)} lần: {a[:60]!r}")
    s = s.replace(a, b)
open(f, "w", encoding="utf-8").write(s)
print("✔ đổi tên → tien_page_da_noi")

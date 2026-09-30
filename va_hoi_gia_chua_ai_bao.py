"""Vá 20/09 — khách CHỈ hỏi giá mà CHƯA ai báo giá con số → AI báo giá, không treo/im nữa.

Chủ shop 20/09 (ngay sau ca Jahoir Islam · Nature's Daily Care in Saudi), chọn giữa ba cách xử câu
chỉ-hỏi-giá: **"Chỉ báo khi Botcake chưa báo giá"**. Luật 19/09 chiều (tiết kiệm tiền model) để nguyên
cho trường hợp page/Botcake ĐÃ gửi con số — lúc đó AI im như cũ; còn chưa ai báo giá thì để khách chờ
là mất khách, AI phải báo.

Chỉ đổi nhánh "giá". Nhánh "mấy ngày giao" giữ nguyên im/treo như 19/09.
Chạy: python3 va_hoi_gia_chua_ai_bao.py ai_sale.py   (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "chưa ai báo con số nào" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''        _ten = "giá" if "gia" in _loai_gg else "mấy ngày giao"
        if "botcake" in sau:
'''
MOI = '''        _ten = "giá" if "gia" in _loai_gg else "mấy ngày giao"
        # 20/09 — chủ shop chọn "chỉ báo khi Botcake chưa báo giá": luật tiết kiệm 19/09 chỉ đúng khi
        # khách ĐÃ có con số trong tay (Botcake/sale/AI đã gửi). Chưa ai báo giá mà AI cũng im thì khách
        # hỏi xong ngồi chờ — mất khách còn đắt hơn một lượt model. Nhánh "mấy ngày giao" giữ nguyên.
        if _ten == "giá" and not tien_page_da_noi(msgs):
            return "tra_loi", "khách hỏi giá mà page chưa ai báo con số nào — AI báo giá (chủ shop 20/09)"
        if "botcake" in sau:
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

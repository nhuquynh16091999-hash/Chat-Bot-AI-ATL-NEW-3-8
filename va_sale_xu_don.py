"""Vá 20/09 (đi kèm va_sale_du_y) — SALE ĐANG XỬ ĐƠN/GIAO HÀNG thì AI không chen, khỏi tốn model.

Đo sau va_sale_du_y (24h, 173 page): 788 hội thoại sale đã rep → im 527, xet 222, treo 37, tra_loi 2.
Soi 222 ca "xet": phần lớn là sale đang xử ĐƠN CŨ — "your order has been created", "I checked the delivery
system", "Has any staff contacted you for delivery?", "Your order is currently moving through transit hubs",
"still waiting for your confirmation of your order so that we can ship". Tin KHÁCH ở những ca đó lại không
có từ khoá đơn cũ ("This one ok", "I really very sorry", "i will make a payment") nên cửa DON_CU không bắt.

Mục 7.4 đã là luật: chuyện đơn cũ / giao hàng để SALE xử, AI không chen. Nay đọc thêm phía TIN SALE để
nhận ra tình huống đó — im bằng luật, 0 đồng. Khách nói ý MUA MỚI trong chuỗi thì vẫn vào cửa xét như thường.

Chạy: python3 va_sale_xu_don.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_SALE_XU_DON" in src:
    sys.exit("đã vá rồi — không làm gì")

CU_RE = '''DON_CU_CHU = re.compile(r"\\bmy\\s+order\\b|\\breceived?\\b|\\bdeliver(?:ed|y)\\b|\\bparcel\\b", re.I)
'''
MOI_RE = '''DON_CU_CHU = re.compile(r"\\bmy\\s+order\\b|\\breceived?\\b|\\bdeliver(?:ed|y)\\b|\\bparcel\\b", re.I)
# TIN CỦA SALE nói chuyện ĐƠN ĐÃ CÓ / GIAO HÀNG — sale đang xử đơn thì AI không chen (mục 7.4). Đọc phía
# sale vì tin khách ở những ca này thường trống nghĩa ("This one ok", "i will make a payment") nên DON_CU mù.
_SALE_XU_DON = re.compile(
    r"\\byour\\s+order\\b|\\border\\s+(?:has\\s+been|is|was)\\s+(?:created|placed|confirmed|shipped|dispatched|out)"
    r"|\\bdelivery\\s+(?:system|team|staff|man|guy|date|time|address|company)|\\bout\\s+for\\s+delivery\\b"
    r"|\\btransit\\b|\\btracking\\b|\\bcourier\\b|\\bshipping\\s+company\\b|\\bre-?deliver|\\bre-?schedul"
    r"|\\bwaiting\\s+for\\s+your\\s+confirmation\\b|\\bstaff\\s+contacted\\b|\\bkeep\\s+your\\s+phone\\b"
    r"|طلبك|شحنة|الشحن|المندوب|التوصيل", re.I | re.U)
'''

CU = '''        if not xet_botcake_bat():
            return "im", "Botcake đã trả lời — AI không đọc lại (AI_XET_BOTCAKE=0)"
'''
MOI = '''        # SALE ĐANG XỬ ĐƠN / GIAO HÀNG — mục 7.4: chuyện đơn cũ để sale, AI không chen (và khỏi tốn một
        # lượt model để rồi phán "im"). Khách nói ý MUA MỚI thì vẫn vào cửa xét như thường.
        if "nguoi" in sau and not any(MUON_MUA.search(lam_sach(m.get("text") or "")) for m in _chuoi_kh) \\
                and any(_SALE_XU_DON.search(lam_sach(m.get("text") or ""))
                        for m in msgs[i + 1:] if m["boi"] == "nguoi"):
            return "im", "sale đang xử chuyện đơn / giao hàng của khách — AI không chen (mục 7.4)"
        if not xet_botcake_bat():
            return "im", "Botcake đã trả lời — AI không đọc lại (AI_XET_BOTCAKE=0)"
'''
for cu, moi in ((CU_RE, MOI_RE), (CU, MOI)):
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:120]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

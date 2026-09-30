"""Vá 20/09 (đi kèm va_sale_du_y) — vòng dò phải ĐỌC hội thoại mà sale vừa rep.

Luật mới "sale rep xong, đủ ý thì thôi, chưa đủ thì bổ sung" nằm trong `ai_co_vao_cuoc`, nhưng vòng dò
có cửa 14/09 (ca EsOr Adz) bỏ HẲN hội thoại khi *chỉ có tin sale mới* (message_count nhích ≤1, người gửi
cuối là sale) → những hội thoại cần xét "sale đủ ý chưa" không bao giờ tới được luật mới.

Bỏ cửa đó. KHÔNG đụng xếp hàng: hội thoại sale gửi cuối vẫn thuộc hàng "xa" (tối đa AI_XA_MOI_LUOT=8 mỗi
lượt, 25 lúc vắng khách) nên khách mới vẫn được ưu tiên — chỉ là AI không còn ngoảnh mặt luôn. Nếu vòng dò
chậm lại thấy rõ thì hạ AI_XA_MOI_LUOT chứ đừng bật lại cửa này.

Chạy: python3 va_doc_khi_sale_rep.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "20/09: BỎ cửa này" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''                if (ai_g == "nguoi" and isinstance(n_tin, int) and isinstance(n_truoc, int)
                        and n_tin - n_truoc <= 1):
                    bo_sale += 1
                    continue
'''
MOI = '''                # 20/09: BỎ cửa này (chủ shop: *"sale rep xong, đủ ý rồi thì thôi, nếu chưa đủ ý thì bạn
                # bổ sung"*). Hội thoại "chỉ có tin sale mới" chính là ca phải đọc để xét câu sale đủ ý chưa.
                # Vẫn nằm hàng "xa" (AI_XA_MOI_LUOT mỗi lượt) nên khách mới vẫn được ưu tiên như cũ.
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

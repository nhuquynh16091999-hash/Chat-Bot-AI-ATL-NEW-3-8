"""Vá luat_model.md: chốt 2 bắt buộc sau xác nhận nhà + cọc $50 MoneyGram/WU/Money Order (14/09 tối).
Chạy: python3 va_luat_coc.py luat_model.md — mỗi chỗ khớp đúng 1 lần mới ghi."""
import sys

f = sys.argv[1]
s = open(f, encoding="utf-8").read()
if "CỌC — chủ shop chốt 2026-09-14" in s:
    sys.exit("đã vá rồi — không làm gì")

VA = [
("""CHỐT 2 — PHƯƠNG THỨC THANH TOÁN. Chỉ làm SAU khi khách đã xác nhận đúng nhà. Gửi mẫu liệt kê
phương thức shop nhận (thường /thanhtoan hoặc /PTTT_L2). Khách chọn một phương thức CÓ trong
kịch bản -> gửi đúng mẫu hướng dẫn của phương thức đó rồi chốt đơn. Khách nêu phương thức KHÔNG
có trong kịch bản -> không bịa, đưa lại danh sách; khách ép -> treo.
""",
"""CHỐT 2 — PHƯƠNG THỨC THANH TOÁN. Chỉ làm SAU khi khách đã xác nhận đúng nhà — và PHẢI làm, không
bỏ qua: khách vừa xác nhận nhà là lượt đó hỏi thanh toán luôn. Gửi mẫu liệt kê
phương thức shop nhận (thường /thanhtoan hoặc /PTTT_L2). Khách chọn một phương thức CÓ trong
kịch bản -> gửi đúng mẫu hướng dẫn của phương thức đó rồi chốt đơn. Khách nêu phương thức KHÔNG
có trong kịch bản -> không bịa, đưa lại danh sách; khách ép -> treo. Khách hỏi lại về thanh toán
("gửi tiền trước khi nhận hàng à?") thì trả lời đúng câu đó — đừng gửi mẫu tư vấn/khó khăn tài chính.

CỌC — chủ shop chốt 2026-09-14 (ca Philip Gutib): khách chọn MONEYGRAM, WESTERN UNION hoặc MONEY
ORDER -> PHẢI CỌC $50 TRƯỚC (mọi đơn, mọi page Mỹ), phần còn lại trả khi nhận hàng. Lượt đó: gửi
mẫu hướng dẫn của phương thức (/MoneyGram+WesternUnion, /MONEY_ORDER, /MoneyOrder — đặt vào
"anh_mau") + nói rõ cọc $50 để giữ đơn, còn lại trả khi nhận + nhờ khách chuyển xong gửi MTCN / ảnh
biên lai. Khách chưa gửi MTCN/biên lai -> CHƯA "len_don", chỉ nhắc. Khách không muốn cọc -> mời chọn
cách trả SAU khi nhận hàng (Zelle, Cash App, Venmo, PayPal, Check… theo /thanhtoan). Các phương thức
đó KHÔNG cọc. Kịch bản Mỹ có ghi "COD" thì nghĩa là nhận hàng rồi mới trả — đừng nói "trả tiền
mặt cho shipper/rider" ở Mỹ/Úc.
"""),
("""CHỐT 3 — LÊN ĐƠN. Khách đã chọn xong phương thức thanh toán""",
"""CHỐT 3 — LÊN ĐƠN. Khách đã chọn xong phương thức thanh toán (MoneyGram/Western Union/Money Order:
đã báo chuyển cọc $50 — đơn có cọc thì câu xác nhận ghi tổng, đã cọc $50, còn lại trả khi nhận; chưa
đủ thì CẤM gửi câu xác nhận đơn "Kumpirmado na po ang inyong paraan…" dù không chọn "len_don")"""),
("""- Mỹ và Úc: phương thức thanh toán theo đúng mẫu trong kịch bản (chốt 2 ở trên), không tự thêm.
""",
"""- Mỹ và Úc: phương thức thanh toán theo đúng mẫu trong kịch bản (chốt 2 ở trên), không tự thêm.
  "COD" ở đây = nhận hàng rồi mới trả qua phương thức trong kịch bản, KHÔNG trả tiền mặt cho
  shipper/rider. MoneyGram / Western Union / Money Order phải cọc $50 trước (mục CỌC ở trên).
"""),
]
for cu, moi in VA:
    n = s.count(cu)
    if n != 1:
        sys.exit(f"❌ chỗ vá khớp {n} lần (phải đúng 1): {cu[:70]!r} — KHÔNG ghi gì")
    s = s.replace(cu, moi)
open(f, "w", encoding="utf-8").write(s)
print(f"✅ đã vá {len(VA)} chỗ vào {f}")

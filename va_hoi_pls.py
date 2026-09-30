"""Vá 20/09 — "Length pls" là CÂU HỎI, và cấm AI thay thông số khách hỏi bằng thông số khác.

Ca Neethu Anil · Oman Gold Lucky Jewelry (chủ shop 20/09): khách "Length pls" (13:01 VN) → AI đáp
*"The necklace is 2.2 grams, the ring 1 gram, and the 2 earrings 2 grams…"* — khách hỏi ĐỘ DÀI, AI đọc
TRỌNG LƯỢNG. 40 giây sau sale Nguyễn Duyên phải vào gõ "The length is 16 to 22 inches, ma'am."
*"sao b k rep gì"*.

Hai lỗi chồng nhau:
  1. `khach_hoi_trong_tam` trả None vì `HS.la_cau_hoi("Length pls")` = False (không có "?", không có từ
     để hỏi) → prompt THIẾU dòng "🎯 KHÁCH VỪA HỎI: …" nên model không bị neo vào câu hỏi.
  2. Kịch bản page KHÔNG có chữ length/inch/size nào (chỉ có gram) → model lấy đại thông số gần nhất.
     Prompt chưa cấm việc này.

Sửa: `_XIN_TT_PLS` — "<danh từ thông tin> + pls/please" tính là câu hỏi (mẫu CHẶT, phải có danh từ:
length/size/color/weight/karat/material/detail/info/photo/video/location/address/whatsapp/number/stock).
Đo 100.824 dòng sổ: 251 lượt khớp kiểu "<thứ> pls", nhưng phải loại "Yes please" (32), "1 set pls",
"order please", "Wait pls", "Opo pls" — chúng là ĐỒNG Ý/CHỌN GÓI, không phải câu hỏi; mẫu chặt chỉ lấy
nhóm hỏi thông tin thật (Size available pls · Length pls · Location please · More info please · WhatsApp
number please · address please…). KHÔNG dùng "po" làm dấu hiệu — đó là từ đệm lịch sự Tagalog, đứng cuối
mọi câu ("Yes po", "Salamat po").
Và prompt trọng tâm: kịch bản không có thông tin khách hỏi → nói thật sẽ kiểm tra rồi báo lại, CẤM đưa
thông số khác thay thế.

Chạy: python3 va_hoi_pls.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_XIN_TT_PLS" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = [(
    '''def khach_hoi_trong_tam(msgs):
''',
    '''# "Length pls" / "Size available pls" / "More info please" — XIN THÔNG TIN, không có dấu "?" nên
# `HS.la_cau_hoi` mù (ca Neethu Anil 20/09, Oman Gold Lucky Jewelry). Mẫu CHẶT: phải có danh từ thông tin,
# vì "<gì đó> pls" chung chung bắt oan "Yes please" / "1 set pls" / "order please" (đồng ý, chọn gói).
_XIN_TT_PLS = re.compile(
    r"\\b(?:length|long|size|sizes|color|colour|weight|gram|grams|karat|carat|material|detail|details|"
    r"info|infos|information|picture|pictures|photo|photos|pic|pics|video|location|address|whatsapp|"
    r"number|stock|available|availability)\\b[^?]{0,25}\\b(?:pls|plz|plss|pleas|please)\\b", re.I)


def khach_hoi_trong_tam(msgs):
'''), (
    '''    hoi = [x for x in sau if HS.la_cau_hoi(x) or HOI_SP.search(x) or (_HOI_BENH.search(x) and _DAU_HOI_SP.search(x))]
''',
    '''    hoi = [x for x in sau if HS.la_cau_hoi(x) or HOI_SP.search(x) or _XIN_TT_PLS.search(x)
           or (_HOI_BENH.search(x) and _DAU_HOI_SP.search(x))]
'''), (
    '''                      + "Câu ĐẦU trả lời đúng trọng tâm câu này theo kịch bản (giao hàng, size, chất liệu, cách đặt…), "
                      "ngắn, đúng tiếng khách. ⛔ KHÔNG nêu giá, KHÔNG liệt kê combo; COD / thanh toán chỉ nói khi khách hỏi "
''',
    '''                      + "Câu ĐẦU trả lời đúng trọng tâm câu này theo kịch bản (giao hàng, size, chất liệu, cách đặt…), "
                      "ngắn, đúng tiếng khách. ⛔ ĐÚNG THỨ KHÁCH HỎI: kịch bản / tin page KHÔNG có thông tin đó thì nói thật "
                      "là bạn kiểm tra rồi báo lại ngay — CẤM đưa thông số khác thay vào (khách hỏi ĐỘ DÀI mà đáp TRỌNG LƯỢNG "
                      "là sai; ca Neethu Anil 20/09). "
                      "⛔ KHÔNG nêu giá, KHÔNG liệt kê combo; COD / thanh toán chỉ nói khi khách hỏi "
''')]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:140]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

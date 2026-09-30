"""Vá 14/09 tối — ca Remy Campos Baylor (Gold Charm Bracelet US): Botcake báo "BUY 1 GET 1 FREE — $199",
khách "Gusto yang na sa picture" (tôi muốn cái trong hình) → AI khen sản phẩm + giảng thanh toán + "Gusto ninyo
bang subukan muna ngayon?" (có muốn thử không). Chủ shop: *"khách đã bảo lấy 1 cái thì xin thông tin khách chứ ai
lại hỏi có mua k vậy"*. Gốc: khach_vua_chon_goi chỉ nhận câu có SỐ LƯỢNG. Mỗi chỗ thay đúng 1 lần."""
import sys

F = sys.argv[1] if len(sys.argv) > 1 else "ai_sale.py"
src = open(F, encoding="utf-8").read()
if "MUON_MUA" in src:
    sys.exit("đã vá rồi — bỏ qua")


def thay(cu, moi):
    global src
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần: {cu[:80]!r}"
    src = src.replace(cu, moi)


thay('''def khach_vua_chon_goi(msgs, mkey, gia=None):
''', '''DON_CU_CHU = re.compile(r"\\bmy\\s+order\\b|\\breceived?\\b|\\bdeliver(?:ed|y)\\b|\\bparcel\\b", re.I)
# KHÁCH NÓI MUỐN MUA mà không nêu số lượng ("Gusto yang na sa picture", "I want this", "I'll take it") — chủ shop
# 14/09 tối, ca Remy Campos Baylor: *"khách đã bảo lấy 1 cái thì xin thông tin khách chứ ai lại hỏi có mua k"*.
MUON_MUA = re.compile(
    r"\\bgusto\\s+(?:(?:ko|nako|na\\s+ko|po)\\s+)?(?:po\\s+)?(?:ito|nito|this|that|yan|yang|yung|nasa|na\\s+sa|isa|one|1"
    r"|(?:ang\\s+)?(?:bracelet|ring|necklace|set|cream|kwintas|singsing|buy\\s*1|b1g1)|(?:bumili|mag-?order|i-?order|order|buy))\\b"
    r"|\\b(?:yes|opo|ok(?:ay)?)\\s+(?:po\\s+)?gusto\\s+(?:ko|nako)(?:\\s+po)?\\s*[.!]*\\s*$"
    r"|\\b(?:kukunin|kunin|kuhanin|kuha)\\s+(?:ko|nako|po|ako)\\b|\\b(?:bibili|bumili|magpa-?order|mag-?order)\\s+(?:po\\s+)?(?:ako|ko|nako)\\b"
    r"|\\bi['’]?\\s*ll\\s+(?:take|get|order|buy)\\b|\\bi\\s+will\\s+(?:take|get|order|buy)\\s+(?:it|this|that|one|1|the|now|po)\\b"
    r"|\\bi\\s+(?:want|wanna|would\\s+like|need)\\s+(?:to\\s+(?:order|buy|get|avail|reserve)|this|that|it\\b|one\\b|1\\b|the\\s+one"
    r"|the\\s+(?:bracelet|ring|necklace|set|cream|product|item)|in\\s+the\\s+(?:picture|photo))"
    r"|\\b(?:i\\s+)?(?:order|reserve)\\s+(?:now|this|that|one|po|for\\s+me)\\b|\\bi\\s*(?:'m|am)\\s+(?:ordering|buying|taking)\\b"
    r"|\\byes\\s+i\\s+(?:want|order|buy|take)\\b|\\b(?:ok(?:ay)?|yes)\\s+(?:i\\s+)?(?:order|buy|take)\\b"
    r"|أبغى|ابغى|ابغي|أبي\\s+(?:اطلب|أطلب|واحد)|أريد|اريد|ودي\\s+اطلب|我要|要訂|想買|想要", re.I | re.U)


def khach_vua_chon_goi(msgs, mkey, gia=None):
''')

thay('''    chon = [x for x in sau if len(x.split()) <= 8
            and HS.trich([{"boi": "khach", "text": x}], mkey, gia).get("so_luong")]
    return " / ".join(sau)[:160] if chon else None
''', '''    chon = [x for x in sau if len(x.split()) <= 8
            and HS.trich([{"boi": "khach", "text": x}], mkey, gia).get("so_luong")]
    # Nói MUỐN MUA mà không kèm số lượng cũng là chốt (ca Remy 14/09) — câu ≤ 12 từ.
    chon = chon or [x for x in sau if len(x.split()) <= 12 and MUON_MUA.search(x)
                     and not re.search(r"\\b(?:if|kung|where|when|next|later|soon|month|buwan)\\b|next\\s*(?:month|week|time)|month", x, re.I)
                     and not (TU_CHOI.search(x) or DOI_LUONG.search(x) or NGAY_HEN.search(x) or DON_CU_CHU.search(x))]
    return " / ".join(sau)[:160] if chon else None
''')

# prompt: nói thẳng ngay lần soạn đầu (đỡ tốn lượt soạn lại)
thay('''    _tc = tinh_huong_tu_choi(rec["msgs"]) if quyet == "tra_loi" else None
''', '''    _tc = tinh_huong_tu_choi(rec["msgs"]) if quyet == "tra_loi" else None
    _chon = khach_vua_chon_goi(rec["msgs"], rec.get("thi_truong"), gia) if quyet == "tra_loi" and not _tc else None
    if _chon:
        tinh_huong = (f"📦 KHÁCH ĐÃ CHỐT MUA: \\"{_chon}\\" — khách KHÔNG hỏi gì, khách muốn lấy hàng. ⛔ CẤM hỏi lại "
                      "'có muốn mua/thử không', CẤM khen sản phẩm, chào lại khuyến mãi, giảng thanh toán/COD. ✅ Tối đa 2 "
                      "câu, đúng tiếng khách: (1) xác nhận gói — khách nói 1 cái / cái trong hình mà page chỉ bán gói "
                      "BUY 1 GET 1 thì là gói đó, kèm giá page đã báo; page có nhiều mức mà khách chưa chọn thì hỏi "
                      "gói trong CÙNG câu; (2) xin phần CÒN THIẾU để giao hàng (tên, số điện thoại, địa chỉ đầy đủ).\\n"
                      + tinh_huong)
''')

open(F, "w", encoding="utf-8").write(src)
print("đã vá", F)

"""Vá 14/09 tối — ca Bebe Garcia Vlogs (Elora Cosmetics UAE): khách "Soon i order thank you" (hoãn mua)
mà AI đáp "No problem, Take your time! Whenever you're ready…". Chủ shop: khách từ chối/hoãn → dùng câu giữ
ưu đãi "Would you like me to reserve this special promotion for you? … until 11 PM today …" để chốt.
Mỗi chỗ thay đúng 1 lần; lệch là thoát không ghi."""
import sys

F = sys.argv[1] if len(sys.argv) > 1 else "ai_sale.py"
src = open(F, encoding="utf-8").read()
if "CAU_GIU_UU_DAI" in src:
    sys.exit("đã vá rồi — bỏ qua")


def thay(cu, moi):
    global src
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần: {cu[:80]!r}"
    src = src.replace(cu, moi)


# 1) Lời HOÃN MUA vào bộ từ chối
thay('''    r"|only have|i only have|laman ng (?:account|wallet|bank|gcash)|lang laman)\\b"
''', '''    r"|only have|i only have|laman ng (?:account|wallet|bank|gcash)|lang laman)\\b"
    # 14/09 tối, ca Bebe Garcia Vlogs ("Soon i order thank you") — lời HOÃN mua, AI tưởng đồng ý nên "Take your time".
    r"|\\b(?:soon\\s+(?:i\\s+|i'?ll\\s+|will\\s+)?(?:order|buy|purchase)|(?:i'?ll|i\\s+will|will)\\s+(?:order|buy|purchase)"
    r"\\s+(?:it\\s+|this\\s+)?(?:soon|later|next|tomorrow|another\\s+time|some\\s*time)|order\\s+(?:it\\s+)?(?:soon|later)"
    r"|let\\s+me\\s+think|i'?ll\\s+think|think\\s+about\\s+it|not\\s+yet(?!\\s+(?:\\w+\\s+)?(?:receiv|deliver|arriv|recieve|recived|come|came|here))|maybe\\s+(?:next|tomorrow|soon)"
    r"|i'?ll\\s+(?:decide|consider)|mamaya|pag[- ]?isipan|isipin)\\b"
''')

# 2) "I'll message you" = hoãn → níu (không im nữa). "no thank you" sau câu "còn câu hỏi nào không?" vẫn im.
thay('''    if HEN_SAU.search(chu) and not DOI_LUONG.search(chu):
        return "im", "khách hẹn sẽ nhắn lại — không đeo bám"
''', '''    # 14/09 tối (ca Bebe Garcia): chủ shop cần chốt nhanh — hẹn nhắn lại cũng là HOÃN, phải níu bằng câu giữ ưu đãi.
    if HEN_SAU.search(chu) and "botcake" not in sau:
        return "tra_loi", "khách hẹn nhắn lại / hoãn mua — níu bằng câu giữ ưu đãi, không để khách đi"
''')
thay('''    if DAP_KET.match(t) and re.search(r"thank|salamat|\\bno\\b|nope|شكرا|لا", t, re.I | re.U):
''', '''    if HEN_SAU.search(t):
        return True               # "I'll message you" — hoãn mua (14/09 tối)
    if DAP_KET.match(t) and re.search(r"thank|salamat|\\bno\\b|nope|شكرا|لا", t, re.I | re.U):
''')

# 3) Câu giữ ưu đãi của chủ shop + bộ dò câu thả khách
thay('''def tinh_huong_tu_choi(msgs):
''', '''# CÂU GIỮ ƯU ĐÃI — chủ shop đưa 14/09 tối, dùng khi khách từ chối / hoãn (ca Bebe Garcia Vlogs).
CAU_GIU_UU_DAI = ("Would you like me to reserve this special promotion for you? 😊 The offer is only available "
                  "until 11 PM today. Don't worry—you can choose the delivery date that is most convenient for you. ❤️")
# Câu THẢ khách đi — cấm khi khách đang từ chối/hoãn.
THA_KHACH = re.compile(
    r"take\\s+your\\s+time|no\\s+rush|whenever\\s+you(?:'?re|\\s+are)\\s+ready|when(?:ever)?\\s+you\\s+(?:decide|are\\s+free)"
    r"|just\\s+(?:let\\s+me\\s+know|message\\s+me|send\\s+(?:me\\s+)?your\\s+details\\s+(?:when|whenever))"
    r"|message\\s+me\\s+(?:back|anytime|when)|i'?ll\\s+(?:be\\s+)?(?:here|wait)|feel\\s+free\\s+to\\s+(?:message|come\\s+back)"
    r"|i'?ll\\s+keep\\s+the\\s+promo|anytime\\s+you\\s+want", re.I)


def tinh_huong_tu_choi(msgs):
''')

# 4) Prompt tình huống từ chối: bắt buộc câu giữ ưu đãi (trừ nhánh chê đắt đã có luật chứng minh giá)
thay('''                         "Hỏi nhẹ lý do khách chưa lấy (giá? chưa cần? chưa tin chất lượng?) kèm MỘT lý lẽ có "
                         "trong kịch bản (COD nhận hàng kiểm rồi mới trả tiền / chất lượng / ưu đãi có hạn), kết "
                         "bằng MỘT câu hỏi mở. Ngắn, ấm, không ép." if _lan < 3 else''', '''                         ("⛔ CẤM thả khách đi: 'take your time', 'no rush', 'whenever you're ready', 'just send your "
                          "details when…', 'message me back'. ✅ Viết 2-3 câu, đúng tiếng khách: 1 câu ngắn đáp đúng "
                          "điều khách nói (lượt 2 thêm MỘT lý lẽ khác lượt trước, vd COD kiểm hàng rồi mới trả tiền), "
                          "rồi KẾT BẰNG ĐÚNG câu giữ ưu đãi của chủ shop (dịch sát nghĩa nếu khách không dùng tiếng "
                          "Anh, giữ 😊 ❤️): \\"" + CAU_GIU_UU_DAI + "\\"") if _lan < 3 else''')

# 5) Luật cứng ở vòng soạn: khách từ chối/hoãn mà tin AI thả khách hoặc thiếu câu giữ ưu đãi → soạn lại 1 lần
thay('''                # KHÁCH VỪA CHỌN GÓI MÀ MODEL CHÀO HÀNG LẠI (chủ shop 14/09, KHACH_VUA_CHON_GOI) — chưa đủ
''', '''                # KHÁCH TỪ CHỐI / HOÃN MÀ MODEL THẢ KHÁCH ĐI (chủ shop 14/09 tối, ca Bebe Garcia Vlogs: "Soon i order
                # thank you" → "Take your time! Whenever you're ready…"). Bắt soạn lại 1 lần với câu giữ ưu đãi; soạn
                # lại vẫn thả khách thì gửi bản mới nếu ít nhất nó không còn câu thả khách.
                _tin_tc_ = ((qd or {}).get("tin_nhan") or "").strip()
                if (not err_m and qd and _tc_ and not hen_giao_theo_luong(msgs) and not la_che_dat(_tc_[0] or "")
                        and _tc_[1] < 3 and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo")
                        and _tin_tc_ and THA_KHACH.search(_tin_tc_)):
                    print(f"{nhan} 🎁 khách từ chối/hoãn mà model thả khách đi — bắt soạn lại với câu giữ ưu đãi")
                    dem["tha_khach"] = dem.get("tha_khach", 0) + 1
                    qd2, e2 = soan_bang_model(
                        noi_dung + "\\n\\nSAI: khách đang TỪ CHỐI / HOÃN mua mà bạn lại thả khách đi ('take your time', "
                        "'whenever you're ready'…). Chủ shop cần chốt đơn NGAY. Viết lại tin_nhan 2-3 câu, KHÔNG con số "
                        "giá: 1 câu đáp ngắn điều khách nói, rồi KẾT BẰNG ĐÚNG câu giữ ưu đãi (dịch sát nghĩa nếu khách "
                        "không dùng tiếng Anh): \\"" + CAU_GIU_UU_DAI + "\\"", on_dinh)
                    _t2_ = ((qd2 or {}).get("tin_nhan") or "").strip()
                    if not e2 and _t2_ and not THA_KHACH.search(_t2_):
                        qd = qd2
                # KHÁCH VỪA CHỌN GÓI MÀ MODEL CHÀO HÀNG LẠI (chủ shop 14/09, KHACH_VUA_CHON_GOI) — chưa đủ
''')

# 6) Bản soạn lại "nhắc giá" (đúng chỗ ca Bebe lọt): khách từ chối thì kết bằng câu giữ ưu đãi, không lời mời mềm
thay('''                        "khách vừa nói (lo lắng/nghi ngờ/kể chuyện), 1 lý lẽ nhẹ (COD kiểm hàng rồi mới trả tiền…), kết "
                        "bằng lời mời mềm kiểu 'Bạn có muốn thử sản phẩm bên mình một lần xem sao không? Mình tin bạn sẽ "
                        "hài lòng 😊'. Ngắn, thoải mái, đúng tiếng khách.", on_dinh)''', '''                        "khách vừa nói (lo lắng/nghi ngờ/kể chuyện), 1 lý lẽ nhẹ (COD kiểm hàng rồi mới trả tiền…), kết "
                        + ("bằng ĐÚNG câu giữ ưu đãi (khách đang từ chối/hoãn — CẤM 'take your time/whenever you're ready'): \\""
                           + CAU_GIU_UU_DAI + "\\"" if _tc_ and not hen_giao_theo_luong(msgs) and _tc_[1] < 3 else
                           "bằng lời mời mềm kiểu 'Bạn có muốn thử sản phẩm bên mình một lần xem sao không? Mình tin bạn sẽ "
                           "hài lòng 😊'") + ". Ngắn, thoải mái, đúng tiếng khách.", on_dinh)''')

open(F, "w", encoding="utf-8").write(src)
print("đã vá", F)

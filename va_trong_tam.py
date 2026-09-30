"""Vá 14/09 tối (sau va_hoi_sp.py) — chủ shop: *"trả lời đúng mục tiêu câu hỏi khách hàng muốn hỏi, chứ k phải
cái nào cũng spam giá … ưu tiên trả lời cái khách đang quan tâm, đúng trọng tâm, sau đó đặt câu hỏi tương tác
mua hàng như: bạn có muốn dùng thử, bạn có muốn đặt hàng ngay bây giờ"*. Mở rộng khối ❓ từ câu hỏi SẢN PHẨM ra
MỌI câu hỏi không phải giá; kết bằng câu mời mua. assert từng chỗ khớp đúng 1 lần."""
import sys, shutil, time

def va(path, cap):
    s = open(path, encoding="utf-8").read()
    for cu, moi in cap:
        n = s.count(cu)
        if n != 1:
            sys.exit(f"✘ {path}: khớp {n} lần (cần 1): {cu[:90]!r}")
        s = s.replace(cu, moi)
    return s

CTA = ("Kết bằng MỘT câu hỏi tương tác mua hàng, đúng tiếng khách — vd 'Bạn có muốn dùng thử sản phẩm 1 lần không? "
       "Mình tin bạn sẽ hài lòng 😊' / 'Bạn có muốn đặt hàng ngay bây giờ không?'.")

LUAT_CAP = [
("""CÁCH VIẾT (bắt buộc mọi tin):
1. Ngắn gọn nhưng ĐỦ Ý — trả lời trúng câu khách hỏi.
2. LUÔN kết bằng một câu hỏi hướng tới việc mua hàng. Không để tin nhắn kết thúc trống.""",
"""CÁCH VIẾT (bắt buộc mọi tin):
1. TRẢ LỜI ĐÚNG TRỌNG TÂM TRƯỚC (chủ shop nhắc lại 2026-09-14 tối, ca Noel — khách hỏi "có hạ huyết áp không",
   AI đọc giá 89 SAR + COD + xin SĐT): câu ĐẦU TIÊN trả lời đúng điều khách vừa hỏi / đang quan tâm (công dụng,
   bệnh, cách dùng, giao hàng, size, chất liệu…). KHÔNG mở bằng giá, combo, COD hay xin SĐT khi khách không hỏi
   mấy thứ đó. Giá CHỈ nêu khi khách hỏi giá, chọn gói, hoặc xác nhận đơn.
2. LUÔN kết bằng MỘT câu hỏi tương tác mua hàng: "Bạn có muốn dùng thử sản phẩm 1 lần không?", "Bạn có muốn
   đặt hàng ngay bây giờ không?" (viết đúng tiếng khách). Khách đã chốt mua thì thay bằng xin thông tin còn thiếu.
   Không để tin nhắn kết thúc trống."""),
]

AI_CAP = [
("""    sau.reverse()
    if not sau or any(HOI_GIA.search(x.lower()) or HOI_MUA.search(x) or khach_hoi_thanh_toan(x)
                      or _HOI_GIAO.search(x) or re.search(DON_CU, x.lower()) for x in sau):
        return None
    hoi = [x for x in sau if HOI_SP.search(x) or (_HOI_BENH.search(x) and _DAU_HOI_SP.search(x))]""",
"""    sau.reverse()
    if not sau or any(_khong_phai_hoi_thuong(x) or _HOI_GIAO.search(x) for x in sau):
        return None
    hoi = [x for x in sau if HOI_SP.search(x) or (_HOI_BENH.search(x) and _DAU_HOI_SP.search(x))]"""),
("""def khach_vua_chon_goi(msgs, mkey, gia=None):""",
"""# Đo khach_hoi_trong_tam trên 1.752 tin khách UAE (14/09): HOI_GIA/HOI_MUA sót giá gõ sai ("mgkno", "Maam mag Kano po",
# "cek harga/hwo much", "How Mac many", "Ano to na 79?"), muốn đặt ("Can I oder now", "how to get this"), khiếu nại
# ("Why did you sent me the small size"). Mấy loại đó KHÔNG được vào khối cấm giá / mời mua.
_GIA_GO_SAI = re.compile(
    r"\\b(?:m[ae]?g\\s*k[ae]?no|mgkno|mgkano|magkno|harga|hwo\\s*much|how\\s*m\\w{0,3}\\s*(?:much|many)|price|prize|presyo"
    r"|kitna|kitne|cost|rate|how\\W{0,2}s?\\s*m[auie](?:ch|tch|ss|ck|h)|hm+|berapa|brp|hrga)\\b"
    r"|\\d{2,}|\\d[.,]\\d|\\b\\d+\\s*(?:pcs?|set|box|bottle|pack)|بكم|سعر|多少|價", re.I | re.U)
_MUON_DAT = re.compile(r"\\b(?:order|oder|ordr|buy|purchase|how\\s+(?:to|can\\s+i)\\s+get|reserve|book|pesen|can\\s+i\\s+have\\s+one)\\b",
                       re.I)
_KHIEU_NAI = re.compile(r"\\b(?:sent\\s+me|received|confirmed\\s+an\\s+order|too\\s+(?:small|big)|wrong|refund|return"
                        r"|didn'?t|call(?:ed)?|my\\s+address|waiting|till\\s+now|update|not\\s+com\\w*|why\\s+not"
                        r"|my\\s+(?:delivery|order|parcel)|how\\s+many\\s+(?:times|messages)|i\\s+(?:send|sent|give|gave)|already\\s+told"
                        r"|pera|shod)\\b", re.I)


def _khong_phai_hoi_thuong(x):
    \"\"\"Tin khách là hỏi giá / muốn đặt / thanh toán / đơn cũ-khiếu nại / từ chối / tin mẫu quảng cáo.\"\"\"
    low = x.lower()
    return bool(HOI_GIA.search(low) or HOI_MUA.search(x) or _GIA_GO_SAI.search(x) or _MUON_DAT.search(x)
                or _KHIEU_NAI.search(x) or khach_hoi_thanh_toan(x) or re.search(DON_CU, low)
                or TU_CHOI.search(x) or DOI_LUONG.search(x) or TIN_MAU_QC.match(x.strip()))


def khach_hoi_trong_tam(msgs):
    \"\"\"Câu HỎI khách vừa gửi (sau tin cuối phía shop) mà KHÔNG phải hỏi giá — giao hàng, size, chất liệu, công dụng…

    Chủ shop 14/09 tối: trả lời đúng trọng tâm câu khách hỏi rồi mới mời mua, không phải câu nào cũng đọc giá.
    Hỏi giá / muốn mua / thanh toán / đơn cũ → None (cửa khác lo). Trả câu hỏi (≤200 ký tự).
    \"\"\"
    sau = []
    for m in reversed(msgs or []):
        if m.get("boi") == "khach":
            if lam_sach(m.get("text")).strip():
                sau.append(lam_sach(m["text"]))
        elif m.get("boi") != "hethong":
            break
    sau.reverse()
    if not sau or any(_khong_phai_hoi_thuong(x) for x in sau):
        return None
    hoi = [x for x in sau if HS.la_cau_hoi(x) or HOI_SP.search(x) or (_HOI_BENH.search(x) and _DAU_HOI_SP.search(x))]
    return " / ".join(hoi)[-200:] if hoi else None


def khach_vua_chon_goi(msgs, mkey, gia=None):"""),
("""    _hoi_sp = (khach_hoi_san_pham(rec["msgs"]) if quyet in ("tra_loi", "xet")
               and not (_tc or _chon or _hua_sdt or dang_tu_van or _xin_anh) else None)
    if _hoi_sp:""",
"""    _mo_cua_hoi = quyet in ("tra_loi", "xet") and not (_tc or _chon or _hua_sdt or dang_tu_van or _xin_anh)
    _hoi_sp = khach_hoi_san_pham(rec["msgs"]) if _mo_cua_hoi else None
    _hoi_tt = khach_hoi_trong_tam(rec["msgs"]) if _mo_cua_hoi and not _hoi_sp else None
    if _hoi_tt:
        tinh_huong = (f"🎯 KHÁCH VỪA HỎI: \\"{_hoi_tt}\\" — khách KHÔNG hỏi giá. "
                      + ("Tin bot không đụng tới điều này là LẠC → trả lời theo luật dưới; bot đã trả lời đúng thì 'im'. "
                         if quyet == "xet" else "")
                      + "Câu ĐẦU trả lời đúng trọng tâm câu này theo kịch bản (giao hàng, size, chất liệu, cách đặt…), "
                      "ngắn, đúng tiếng khách. ⛔ KHÔNG nêu giá, KHÔNG liệt kê combo; COD / thanh toán chỉ nói khi khách hỏi "
                      "về nó. " + """ + repr(CTA) + """ + "\\n" + tinh_huong)
    if _hoi_sp:"""),
("""                      "KHÔNG giảng COD / đợi lương, KHÔNG xin SĐT/địa chỉ trong tin này — khách không hỏi mấy thứ đó. Kết "
                      "bằng MỘT câu hỏi mềm về nhu cầu của khách (đang gặp vấn đề gì / có muốn thử không).\\n" + tinh_huong)""",
"""                      "KHÔNG giảng COD / đợi lương, KHÔNG xin SĐT/địa chỉ trong tin này — khách không hỏi mấy thứ đó. "
                      + """ + repr(CTA) + """ + "\\n" + tinh_huong)"""),
("""                _hoi_sp_ = khach_hoi_san_pham(msgs)""",
"""                _hoi_sp_ = khach_hoi_san_pham(msgs) or khach_hoi_trong_tam(msgs)"""),
("""                        noi_dung + ((f"\\n\\nSAI: khách đang HỎI VỀ SẢN PHẨM (\\"{_hoi_sp_}\\") mà bạn lại nhắc giá. Câu ĐẦU phải \"""",
"""                        noi_dung + ((f"\\n\\nSAI: khách đang HỎI (\\"{_hoi_sp_}\\") mà bạn lại nhắc giá. Câu ĐẦU phải \""""),
("""                           "bằng lời mời mềm kiểu 'Bạn có muốn thử sản phẩm bên mình một lần xem sao không? Mình tin bạn sẽ "
                           "hài lòng 😊'")""",
"""                           "bằng lời mời mềm kiểu 'Bạn có muốn thử sản phẩm bên mình một lần xem sao không? Mình tin bạn sẽ "
                           "hài lòng 😊' / 'Bạn có muốn đặt hàng ngay bây giờ không?'")"""),
]

if __name__ == "__main__":
    goc = sys.argv[1] if len(sys.argv) > 1 else "/opt/pancake-tool/"
    ra = sys.argv[2] if len(sys.argv) > 2 else goc
    ai = va(goc + "ai_sale.py", AI_CAP)
    lu = va(goc + "luat_model.md", LUAT_CAP)
    if ra == goc:
        st = time.strftime("%Y%m%d-%H%M")
        for f in ("ai_sale.py", "luat_model.md"):
            shutil.copy2(goc + f, f"{goc}{f}.bak-{st}-truoc-trong-tam")
    open(ra + "ai_sale.py", "w", encoding="utf-8").write(ai)
    open(ra + "luat_model.md", "w", encoding="utf-8").write(lu)
    print("✔ ghi", ra)

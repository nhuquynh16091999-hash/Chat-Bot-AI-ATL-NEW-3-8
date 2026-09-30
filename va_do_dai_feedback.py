"""Vá 20/09 — (1) độ dài dây chuyền 16–22 inches cho page thiếu; (2) khách xin FEEDBACK thì AI gửi ảnh.

Chủ shop 20/09:
  *"B CỨ LẤY 16-22 INCHES NẾU PAGE NÀO THIẾU NHÉ"*  → page bán trang sức mà kịch bản không ghi độ dài
     (đo: 139 page trang sức có kịch bản, 137 page THIẾU) thì AI trả lời 16–22 inches, không "để em kiểm tra".
  *"KHÁCH HỎI FEEDBACK THÌ B PHẢI GỬI CHO KHÁCH CHỨ"* → khách xin feedback/review (gõ hoặc bấm nút
     "Feedback") thì AI kèm ảnh mẫu /Feedback của page, không chỉ ở lượt níu 2 như trước.

Ba chỗ sửa:
  a. `vo_nghia` + `_tin_co_noi_dung`: tin khách "Feedback" (1 chữ, thường do bấm nút) KHÔNG phải tin rỗng —
     nó là yêu cầu rõ ràng. Cùng kiểu vá với tên tiếng đứng trơ sáng nay.
  b. Vòng soạn: khách xin feedback + page gửi được ảnh + kịch bản có mẫu feedback → ép `anh_mau`.
  c. Prompt: dòng 📏 ĐỘ DÀI khi khách hỏi độ dài mà kịch bản page thiếu.

Chạy: python3 va_do_dai_feedback.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "XIN_FEEDBACK" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = [
    # ── regex mới, đặt cạnh _SALE_XU_DON ──────────────────────────────────────
    ('''DON_CU_CHU = re.compile(r"\\bmy\\s+order\\b|\\breceived?\\b|\\bdeliver(?:ed|y)\\b|\\bparcel\\b", re.I)
''',
     '''DON_CU_CHU = re.compile(r"\\bmy\\s+order\\b|\\breceived?\\b|\\bdeliver(?:ed|y)\\b|\\bparcel\\b", re.I)
# KHÁCH XIN FEEDBACK (chủ shop 20/09: *"khách hỏi feedback thì b phải gửi cho khách chứ"*). Tin thường là
# đúng một chữ "Feedback" do khách BẤM NÚT của Botcake (ca Neethu Anil · Oman Gold Lucky Jewelry).
XIN_FEEDBACK = re.compile(
    r"\\bfeed\\s*backs?\\b|\\bfeedbacks?\\b|\\bfeedbck\\b|\\bfeedbak\\b|\\bfidback\\b|\\breviews?\\b|\\btestimonial"
    r"|\\bproofs?\\b|\\b(?:customers?|real|actual)\\s+(?:photos?|pictures?|pics?|feedbacks?|reviews?)"
    r"|\\bpatunay\\b|\\bpatotoo\\b|تقييم|مراجع|تجارب|آراء", re.I | re.U)
# ĐỘ DÀI DÂY CHUYỀN — chủ shop 20/09: page trang sức nào kịch bản không ghi thì lấy 16–22 inches.
_HOI_DO_DAI = re.compile(r"\\b(?:length|lenght|lenth)\\b|\\b\\d{1,2}\\s*(?:inch|inches)\\b|\\binch(?:es)?\\b"
                         r"|how\\s+many\\s+inch|الطول|كم\\s*طول", re.I | re.U)
_KB_CO_DO_DAI = re.compile(r"\\b\\d{1,2}\\s*(?:-|–|to)\\s*\\d{1,2}\\s*(?:inch|inches|cm)\\b"
                           r"|\\b\\d{1,2}\\s*(?:inch|inches)\\b|\\blength\\b|طول", re.I | re.U)
_LA_TRANG_SUC = re.compile(r"\\b(?:necklace|chain|pendant|bracelet|earrings?)\\b|سلسلة|قلادة", re.I | re.U)
DO_DAI_MAC_DINH = "16–22 inches"


def khach_xin_feedback(msgs, so_tin=3):
    """Khách vừa xin feedback / ảnh khách thật trong các tin chưa được đáp."""
    kh = []
    for m in reversed(msgs or []):
        if m.get("boi") == "khach":
            t = lam_sach(m.get("text") or "").strip()
            if t:
                kh.append(t)
        elif m.get("boi") != "hethong":
            break
    return any(XIN_FEEDBACK.search(t) for t in kh[:so_tin])
'''),
    # ── a. "Feedback" không phải tin rỗng ─────────────────────────────────────
    ('''    if CG.ten_tieng_tron(t):
        return False
    return len(low.split()) <= 1
''',
     '''    if CG.ten_tieng_tron(t):
        return False
    if XIN_FEEDBACK.search(t):
        return False                     # "Feedback" (bấm nút) là yêu cầu rõ ràng, không phải tin trơ
    return len(low.split()) <= 1
'''),
    ('''    if CG.ten_tieng_tron(t):
        return True                                  # khách xin đổi tiếng — Botcake rep tiếng cũ là chưa đủ
''',
     '''    if CG.ten_tieng_tron(t):
        return True                                  # khách xin đổi tiếng — Botcake rep tiếng cũ là chưa đủ
    if XIN_FEEDBACK.search(t):
        return True                                  # khách xin feedback — phải gửi ảnh, không bỏ qua
'''),
    # ── b. ép ảnh feedback khi khách xin ──────────────────────────────────────
    ('''                    qd = dict(qd, anh_mau=_fb_["tu_khoa"].strip())
                    print(f"{nhan} 🖼  lượt níu 2 — kèm ảnh feedback /{qd['anh_mau']}")
''',
     '''                    qd = dict(qd, anh_mau=_fb_["tu_khoa"].strip())
                    print(f"{nhan} 🖼  lượt níu 2 — kèm ảnh feedback /{qd['anh_mau']}")
                # KHÁCH XIN FEEDBACK (chủ shop 20/09) — gửi ảnh mẫu /Feedback bất kể đang ở lượt nào.
                _fbx_ = (mau_feedback(kb_page, msgs) if (not err_m and qd and not _fb_
                                                         and khach_xin_feedback(msgs)
                                                         and anh_gui_duoc(mkey, pid)) else None)
                if _fbx_ and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo", "len_don") \\
                        and (qd.get("tin_nhan") or "").strip() and not (qd.get("anh_mau") or "").strip():
                    qd = dict(qd, anh_mau=(_fbx_.get("tu_khoa") or "").strip())
                    print(f"{nhan} 🖼  khách xin feedback — kèm ảnh /{qd['anh_mau']}")
'''),
    # ── c. dòng ĐỘ DÀI trong prompt ───────────────────────────────────────────
    ('''    _mo_cua_hoi = quyet in ("tra_loi", "xet") and not (_tc or _tg or _chon or _hua_sdt or dang_tu_van or _xin_anh)
''',
     '''    # 📏 ĐỘ DÀI DÂY CHUYỀN (chủ shop 20/09: *"b cứ lấy 16-22 inches nếu page nào thiếu nhé"*) — ca Neethu Anil
    # 20/09: khách "Length pls", kịch bản page không có chữ length/inch nào nên model đáp bằng TRỌNG LƯỢNG.
    # Đo: 139 page trang sức có kịch bản, 137 page thiếu thông tin này.
    try:
        _kb_chu = json.dumps(kb_page, ensure_ascii=False) if kb_page else ""
        _kh_gan = " ".join(lam_sach(m.get("text") or "") for m in (rec["msgs"] or [])[-6:]
                           if m.get("boi") == "khach")
        if (_HOI_DO_DAI.search(_kh_gan) and _LA_TRANG_SUC.search(_kb_chu)
                and not _KB_CO_DO_DAI.search(_kb_chu)):
            tinh_huong = (f"📏 ĐỘ DÀI: dây chuyền dài {DO_DAI_MAC_DINH} (chủ shop cấp — kịch bản page này không ghi). "
                          "Khách hỏi độ dài thì trả lời đúng con số này, KHÔNG nói 'để em kiểm tra', KHÔNG thay bằng "
                          "trọng lượng hay thông số khác.\\n" + tinh_huong)
    except Exception:                                  # noqa: BLE001 — thiếu dòng nhắc thì soạn như cũ
        pass
    _mo_cua_hoi = quyet in ("tra_loi", "xet") and not (_tc or _tg or _chon or _hua_sdt or dang_tu_van or _xin_anh)
'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:150]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ trong {f}")

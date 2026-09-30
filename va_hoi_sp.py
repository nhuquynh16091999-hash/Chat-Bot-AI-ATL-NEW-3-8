"""Vá 14/09 tối — ca Noel B Mendoza (Wellora Wellness Saudi): khách hỏi "Nakaka bawas ba ng bp yan
bukod pang detox" (có hạ huyết áp không), AI đáp nguyên bài giá 89 SAR + COD + đợi lương + xin SĐT.
Hai gốc: (1) giá Botcake viết chữ toán in đậm "𝟖𝟗 𝐒𝐀𝐑" → tien_trong không đọc được → luật nhac_gia
tưởng page chưa báo giá; mức bán page = []. (2) không có khối nào bảo model trả lời câu hỏi sản phẩm.
Chạy: python3 va_hoi_sp.py  (assert từng chỗ khớp đúng 1 lần, khác thì thoát không ghi)."""
import sys, shutil, time

def va(path, cap):
    s = open(path, encoding="utf-8").read()
    for cu, moi in cap:
        n = s.count(cu)
        if n != 1:
            sys.exit(f"✘ {path}: khớp {n} lần (cần 1): {cu[:90]!r}")
        s = s.replace(cu, moi)
    return s

CG_CAP = [
("""def _chuan(s):
    return re.sub(r"[^\\w\\s]", " ", str(s or "").lower(), flags=re.UNICODE)
""",
"""_CHU_TOAN = re.compile("[\\U0001D400-\\U0001D7FF]")


def bo_chu_toan(t):
    \"\"\"Chữ in đậm/nghiêng kiểu Unicode toán học → chữ thường: "𝐁𝐎𝐗 - 𝟖𝟗 𝐒𝐀𝐑" → "BOX - 89 SAR".

    Ca Noel B Mendoza 14/09 (Wellora Wellness Saudi): Botcake báo giá bằng chữ số in đậm, tien_trong
    không đọc ra → luật "không nhắc giá" tưởng page chưa báo giá, mức bán của page = []. Đo kịch bản
    12 nước: 6 page mất giá vì kiểu chữ này. Chỉ đổi dải U+1D400–1D7FF (thuần kiểu chữ), không đụng gì khác.
    \"\"\"
    return _CHU_TOAN.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), str(t or ""))


def _chuan(s):
    return re.sub(r"[^\\w\\s]", " ", bo_chu_toan(s).lower(), flags=re.UNICODE)
"""),
("""    ra = []
    for a, b in rg.findall(str(t or "")):""",
"""    ra = []
    for a, b in rg.findall(bo_chu_toan(t)):"""),
("""    for a, b in SO_TIEN.findall(str(t or "")):""",
"""    for a, b in SO_TIEN.findall(bo_chu_toan(t)):"""),
("""    c = re.sub(r"\\s+", " ", str(cum or "").lower()).strip()
    if not c:
        return False
    for m in kb_page.get("mau") or []:
        for tin in m.get("tin") or []:
            if c in re.sub(r"\\s+", " ", tin.lower()):""",
"""    c = re.sub(r"\\s+", " ", bo_chu_toan(cum).lower()).strip()
    if not c:
        return False
    for m in kb_page.get("mau") or []:
        for tin in m.get("tin") or []:
            if c in re.sub(r"\\s+", " ", bo_chu_toan(tin).lower()):"""),
]

AI_CAP = [
("""def lam_sach(t):
    t = re.sub(r"<[^>]+>", " ", str(t or ""))""",
"""def lam_sach(t):
    # Chữ in đậm kiểu Unicode toán học (𝟖𝟗 𝐒𝐀𝐑) → chữ thường — mọi bộ dò đọc được (ca Noel 14/09).
    t = re.sub(r"<[^>]+>", " ", CG.bo_chu_toan(t))"""),
("""    t = str(txt or "")
    ra = CG.so_tien_cua(t, mkey) if (chat and mkey) else CG.tien_trong(t)""",
"""    t = CG.bo_chu_toan(txt)
    ra = CG.so_tien_cua(t, mkey) if (chat and mkey) else CG.tien_trong(t)"""),
("""def khach_vua_chon_goi(msgs, mkey, gia=None):""",
"""# KHÁCH HỎI VỀ SẢN PHẨM (công dụng / bệnh / cách dùng / an toàn / thật-giả) — chủ shop 14/09 tối, ca Noel B
# Mendoza (Wellora Wellness Saudi, TRUSO STOMACH): khách "Nakaka bawas ba ng bp yan bukod pang detox" (ngoài
# detox có hạ huyết áp không), AI đáp "1 box 89 SAR, COD, giao ngày lương, gửi SĐT" — không một chữ về huyết áp.
# *"lại spam giá rồi, trong khi khách hỏi tác dụng cơ mà"*. Đo trên 5.184 tin khách thật trước khi chốt regex:
# bỏ "how long/how many days" (hỏi giao hàng), "safe" trơn ("parcel is safe"), "for men/women", "results" trơn.
HOI_SP = re.compile(
    r"\\b(?:effective|effectiv\\w*|efective|side\\s*effects?|good\\s+for|works?\\s+(?:for|on)|helps?\\s+(?:with|for)"
    r"|how\\s+(?:to|do\\s+i|do\\s+you|can\\s+i)\\s+use|how\\s+does\\s+(?:it|this)\\s+work|ingredients?"
    r"|is\\s+(?:it|this|thi\\w)\\s+(?:good|safe|effective|original|legit|real)|safe\\s+(?:for|to\\s+use|ba)"
    r"|can\\s+(?:i|it)\\s+(?:use|be\\s+used)|does\\s+(?:it|this)\\s+(?:work|help|treat|cure|remove|lower|reduce|have)"
    r"|nakaka\\w+\\b.*\\bba|mabisa|epekti\\w*|epikti\\w*|efekti\\w*|hiyang|sangkap|gamitin|paggamit"
    r"|paano\\s+(?:gamit\\w*|inumin|ipahid)|legit\\s+ba|original\\s+ba|tumatalab|gumagana\\s+ba"
    r"|efek\\w*|ampuh|manjur|cocok\\s+(?:gak|ga|untuk|buat)|aman\\s+(?:gak|ga|tidak|nggak))\\b"
    r"|فعال|يفيد|آمن|مكونات|طريقة\\s+الاستخدام", re.I | re.U)
_HOI_BENH = re.compile(
    r"\\b(?:bp|high\\s*blood|blood\\s*pressure|hypertension|presyon|diabetes|diabetic|buntis|pregnan\\w*"
    r"|breast\\s*feed\\w*|nagpapasuso|maintenance|allerg\\w*|ulcer|kidney|eczema|cholesterol|asthma)\\b|ضغط|سكري",
    re.I | re.U)
_DAU_HOI_SP = re.compile(r"[?؟]|\\b(?:ba|pwede|can|does|is\\s+(?:it|this)|good\\s+for|ok(?:ay)?\\s+ba|bisa|boleh)\\b|هل",
                         re.I | re.U)
_HOI_GIAO = re.compile(r"\\b(?:deliver\\w*|shipping|ship|parcel|arrive\\w*|rider|courier|refund|return)\\b", re.I)


def khach_hoi_san_pham(msgs):
    \"\"\"Câu khách vừa hỏi về sản phẩm (tin khách SAU tin cuối phía shop), không thì None.

    Có hỏi giá / thanh toán / giao hàng trong cùng lượt thì None — cửa khác trả lời, khối này cấm nêu giá.
    \"\"\"
    sau = []
    for m in reversed(msgs or []):
        if m.get("boi") == "khach":
            if lam_sach(m.get("text")).strip():
                sau.append(lam_sach(m["text"]))
        elif m.get("boi") != "hethong":
            break
    sau.reverse()
    if not sau or any(HOI_GIA.search(x.lower()) or HOI_MUA.search(x) or khach_hoi_thanh_toan(x)
                      or _HOI_GIAO.search(x) or re.search(DON_CU, x.lower()) for x in sau):
        return None
    hoi = [x for x in sau if HOI_SP.search(x) or (_HOI_BENH.search(x) and _DAU_HOI_SP.search(x))]
    return " / ".join(hoi)[-200:] if hoi else None


def khach_vua_chon_goi(msgs, mkey, gia=None):"""),
("""    _so_bao, _cau_bao = gia_page_da_bao(rec["msgs"])
    if _cau_bao and not dang_tu_van:""",
"""    _hoi_sp = (khach_hoi_san_pham(rec["msgs"]) if quyet in ("tra_loi", "xet")
               and not (_tc or _chon or _hua_sdt or dang_tu_van or _xin_anh) else None)
    if _hoi_sp:
        # Ca Noel B Mendoza 14/09: hỏi "có hạ huyết áp không" → AI đọc giá + COD + đợi lương + xin SĐT.
        tinh_huong = (f"❓ KHÁCH VỪA HỎI VỀ SẢN PHẨM: \\"{_hoi_sp}\\" (công dụng / bệnh / cách dùng / an toàn / thật-giả). "
                      + ("Tin bot chỉ báo giá/chào hàng mà không đụng tới điều này là LẠC → trả lời theo luật dưới; bot đã "
                         "trả lời đúng điều này thì 'im'. " if quyet == "xet" else "")
                      + "Tin của bạn PHẢI trả lời THẲNG câu này ngay câu đầu, đúng tiếng khách, 2-3 câu, dưới 300 ký tự. "
                      "Chỉ nói điều CÓ trong kịch bản / tin page: sản phẩm dùng cho gì, dùng thế nào. Khách hỏi một bệnh / "
                      "tác dụng mà kịch bản KHÔNG nói (vd huyết áp, tiểu đường) → nói thật sản phẩm dành cho <công dụng trong "
                      "kịch bản>, không phải thuốc chữa bệnh đó, KHÔNG hứa chữa/giảm; khách có bệnh nền / đang uống thuốc duy "
                      "trì → khuyên hỏi bác sĩ trước (dùng câu của kịch bản nếu có). ⛔ KHÔNG nêu giá, KHÔNG liệt kê combo, "
                      "KHÔNG giảng COD / đợi lương, KHÔNG xin SĐT/địa chỉ trong tin này — khách không hỏi mấy thứ đó. Kết "
                      "bằng MỘT câu hỏi mềm về nhu cầu của khách (đang gặp vấn đề gì / có muốn thử không).\\n" + tinh_huong)
    _so_bao, _cau_bao = gia_page_da_bao(rec["msgs"])
    if _cau_bao and not dang_tu_van:"""),
("""                _da_noi_ = tien_page_da_noi(msgs)
                _tin_gia_ = qd.get("tin_nhan") or "" if qd else ""
                if (not err_m and qd and _da_noi_ and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo")""",
"""                _da_noi_ = tien_page_da_noi(msgs)
                _tin_gia_ = qd.get("tin_nhan") or "" if qd else ""
                # Khách hỏi về SẢN PHẨM thì nhắc giá là lạc đề kể cả khi page chưa báo giá (ca Noel 14/09).
                _hoi_sp_ = khach_hoi_san_pham(msgs)
                if (not err_m and qd and (_da_noi_ or _hoi_sp_) and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo")"""),
("""                        noi_dung + "\\n\\nSAI: khách KHÔNG hỏi giá, giá page đã báo rồi mà bạn lại nhắc giá — khách thấy bị dí. \"""",
"""                        noi_dung + ((f"\\n\\nSAI: khách đang HỎI VỀ SẢN PHẨM (\\"{_hoi_sp_}\\") mà bạn lại nhắc giá. Câu ĐẦU phải "
                                     "trả lời thẳng câu đó theo kịch bản (không có trong kịch bản thì nói thật, không hứa "
                                     "chữa bệnh). ") if _hoi_sp_ else "")
                        + "\\n\\nSAI: khách KHÔNG hỏi giá, giá page đã báo rồi mà bạn lại nhắc giá — khách thấy bị dí. \""""),
]

if __name__ == "__main__":
    goc = "/opt/pancake-tool/"
    cg = va(goc + "chan_gui.py", CG_CAP)
    ai = va(goc + "ai_sale.py", AI_CAP)
    st = time.strftime("%Y%m%d-%H%M")
    for f in ("chan_gui.py", "ai_sale.py"):
        shutil.copy2(goc + f, f"{goc}{f}.bak-{st}-truoc-hoi-san-pham")
    open(goc + "chan_gui.py", "w", encoding="utf-8").write(cg)
    open(goc + "ai_sale.py", "w", encoding="utf-8").write(ai)
    print("✔ đã vá chan_gui.py + ai_sale.py, bak", st)

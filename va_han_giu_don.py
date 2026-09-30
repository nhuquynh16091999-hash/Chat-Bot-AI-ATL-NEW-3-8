"""Vá HẠN GIỮ ĐƠN 1 THÁNG (chủ shop 14/09/2026, ca Jessica Dongon — Meco Jewelry Kuwait).

Chạy: python3 va_han_giu_don.py <thư mục pancake-tool>
Mỗi chỗ thay đúng 1 lần (assert count == 1) — khớp khác thì thoát, KHÔNG ghi file nào.
"""
import os
import sys

D = sys.argv[1]


def doc(ten):
    with open(os.path.join(D, ten), encoding="utf-8") as f:
        return f.read()


MOI = {}


def thay(ten, cu, moi):
    s = MOI.get(ten) or doc(ten)
    if "HẠN GIỮ ĐƠN" in s and ten not in MOI:
        sys.exit(f"❌ {ten} đã có vá HẠN GIỮ ĐƠN — không vá lại")
    n = s.count(cu)
    if n != 1:
        sys.exit(f"❌ {ten}: chuỗi neo khớp {n} lần (cần 1): {cu[:70]!r} — KHÔNG ghi gì")
    MOI[ten] = s.replace(cu, moi)


# ─────────────────────────── chan_gui.py ───────────────────────────
thay("chan_gui.py", "import unicodedata\n", "import unicodedata\nfrom datetime import date, timedelta\n")

thay("chan_gui.py", '''# ══════════════════════════════════════════════════════════════════════════════
# Tự kiểm — chạy `python3 chan_gui.py tu_kiem`''', r'''# HẠN GIỮ ĐƠN 1 THÁNG — chủ shop 2026-09-14, ca Jessica Dongon (Meco Jewelry Kuwait): khách "February
# po sir" (đợi lương tháng 2 NĂM SAU), AI đáp "I-schedule ko na po ang delivery sa February 24" và lên
# đơn. *"khách hẹn tận tháng 2 năm sau bạn cũng ok à, như vậy tôi lấy đâu ra đơn hàng … bảo khách chỉ
# nhận giữ đơn hàng trong vòng 1 tháng kể từ ngày chốt đơn, ví dụ đến hết tháng 10"* (nói ngày 14/09).
# Hạn = NGÀY CUỐI của tháng liền sau tháng chốt (14/09 → 31/10) — theo đúng ví dụ của chủ shop.
# Bộ đọc ngày dùng chung cho ai_sale (khách hẹn ngày nào) và cổng chặn (AI hứa giao ngày nào).
_THANG_TEN = [
    (1, r"january|jan|enero|يناير|كانون الثاني"), (2, r"february|feb|pebrero|febrero|فبراير|شباط"),
    (3, r"march|marso|مارس|آذار"), (4, r"april|apr|abril|أبريل|ابريل|إبريل|نيسان"),
    (5, r"mayo|مايو|أيار"), (6, r"june|hunyo|junio|يونيو|يونيه|حزيران"),
    (7, r"july|hulyo|julio|يوليو|يوليه|تموز"), (8, r"august|aug|agosto|أغسطس|اغسطس|آب"),
    (9, r"september|sept|sep|setyembre|septyembre|septiembre|سبتمبر|أيلول"),
    (10, r"october|oct|oktubre|octubre|أكتوبر|اكتوبر|تشرين الأول"),
    (11, r"november|nov|nobyembre|noviembre|نوفمبر|تشرين الثاني"),
    (12, r"december|dec|disyembre|diciembre|ديسمبر|كانون الأول"),
]
# Chữ ngắn dễ trùng từ thường CHỈ tính khi dính số ngày ("jun 5"). KHÔNG có "may": tiếng Tagalog
# "may 3-digit combination", "May 4 beautiful colors" (= có) — quét 6.520 mẫu kịch bản 14/09 bắt oan 9 mẫu.
_THANG_CAN_SO = [(3, r"mar"), (6, r"jun"), (7, r"jul")]


def _ten_thang(ds, tien_to):
    return "|".join(f"(?P<{tien_to}{m}_{i}>{p})" for i, (m, p) in enumerate(ds))


_KHONG_PHAI_NGAY = r"(?!\s*-?\s*(?:birth\s*-?\s*stones?|stones?|sets?|collection|edition)\b)"   # "July Birthstone Set"
_B = r"(?<![A-Za-z؀-ۿ])"   # biên chữ chạy được cả tiếng Ả Rập (\b không ổn với Unicode ghép)
_E = r"(?![A-Za-z؀-ۿ])"
_THANG_RE = re.compile(
    r"(?:(?P<d1>\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+|ng\s+|de\s+)?" + _B + "(?:" + _ten_thang(_THANG_TEN + _THANG_CAN_SO, "a") + ")" + _E + _KHONG_PHAI_NGAY +
    r"|" + _B + "(?:" + _ten_thang(_THANG_TEN, "b") + ")" + _E + _KHONG_PHAI_NGAY + r"\.?\s*(?P<d2>\d{1,2})?(?:st|nd|rd|th)?(?!\d)"
    r"|" + _B + "(?:" + _ten_thang(_THANG_CAN_SO, "c") + r")\.?\s+(?P<d3>\d{1,2})(?:st|nd|rd|th)?(?!\d))", re.I | re.U)
_THANG_ZH = re.compile(r"(\d{1,2})\s*月(?:\s*(\d{1,2})\s*[日号號])?")
# Số dd/mm CHỈ tính khi có năm (24/02/2027): "1/3 ang presyo", "24/7" trong kịch bản không phải ngày.
_NGAY_SO = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(\d{2,4})(?![\d/])")
_NAM = re.compile(r"(?<!\d)(20\d\d)(?!\d)")
_NAM_SAU = re.compile(r"\bnext\s+year\b|susunod\s+na\s+taon|sa\s+sunod\s+na\s+tuig|السنة\s+(?:الجاية|الجاي|القادمة)|"
                      r"العام\s+(?:القادم|الجاي)|明年", re.I | re.U)
_SO_CHU = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "dalawa": 2, "tatlo": 3, "apat": 4, "lima": 5}
_NHIEU_THANG = re.compile(r"\b(?:after|in)\s+(\d+|two|three|four|five|six)\s+months?\b|"
                          r"\b(\d+|dalawa|tatlo|apat|lima)\s*(?:na\s+)?(?:months?|buwan)\b|"
                          r"بعد\s+(?:شهرين|ثلاث(?:ة)?\s+(?:شهور|اشهر|أشهر))", re.I | re.U)


def han_giu_don(hom_nay=None):
    """Ngày cuối cùng shop còn giữ đơn: ngày cuối tháng liền sau tháng chốt (14/09 → 31/10)."""
    d = hom_nay or date.today()
    dau_thang_sau_nua = date(d.year + (d.month >= 11), (d.month + 1) % 12 + 1, 1)
    return dau_thang_sau_nua - timedelta(days=1)


def _ngay_hop_le(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


# Tháng KHÔNG kèm ngày trong câu AI chỉ tính khi có giới từ đứng trước ("sa February", "in February",
# "until February") — "Hi Febrero" (tên khách), "Hi June", "August Peridot" không phải lịch giao.
_GIOI_TU_THANG = re.compile(r"(?:\b(?:sa|in|on|until|till|by|before|after|this|next|come|ng|hanggang|pagdating\s+ng|"
                            r"bago|early|mid|late|end\s+of)|في|بعد|قبل|حتى|شهر)\s*$", re.I | re.U)


def ngay_trong_cau(t, hom_nay=None, can_gioi_tu=False):
    """Mọi ngày (date) đọc được trong câu, đã suy năm. Tháng không kèm ngày → ngày 1 của tháng đó
    (sớm nhất có thể: tháng 1 đã quá hạn thì cả tháng quá hạn). Tháng nhỏ hơn tháng hiện tại, không
    ghi năm → năm sau ("February" nói ngày 14/09 = 02/2027). Không đọc số trơn ("on the 25th") vì
    ngày trong tháng này/tháng sau luôn còn trong hạn.
    can_gioi_tu — cổng soi câu AI: tháng trơn phải có giới từ đứng trước mới tính (khách thì cứ tính)."""
    t = str(t or "")
    hn = hom_nay or date.today()
    nam = _NAM.search(t)
    nam = int(nam.group(1)) if nam else None
    ra = []

    def _them(m, d):
        y = nam or (hn.year + 1 if m < hn.month else hn.year)
        v = _ngay_hop_le(y, m, d or 1)
        if v:
            ra.append(v)

    for mo in _THANG_RE.finditer(t):
        thang = next(int(k[1:].split("_")[0]) for k, v in mo.groupdict().items() if v and k[0] in "abc")
        ngay = mo.group("d1") or mo.group("d2") or mo.group("d3")
        if can_gioi_tu and not ngay and not _GIOI_TU_THANG.search(t[:mo.start()]):
            continue
        _them(thang, int(ngay) if ngay else None)
    for mo in _THANG_ZH.finditer(t):
        if 1 <= int(mo.group(1)) <= 12:
            _them(int(mo.group(1)), int(mo.group(2)) if mo.group(2) else None)
    for mo in _NGAY_SO.finditer(t):   # dd/mm — Philippines, vùng Vịnh, Đài Loan viết ngày trước
        d, m = int(mo.group(1)), int(mo.group(2))
        y = int(mo.group(3))
        v = _ngay_hop_le(y + 2000 if y < 100 else y, m, d)
        if v:
            ra.append(v)
    if _NAM_SAU.search(t):
        ra.append(date(hn.year + 1, 1, 1))
    for mo in _NHIEU_THANG.finditer(t):
        g = (mo.group(1) or mo.group(2) or "").lower()
        so = int(g) if g.isdigit() else _SO_CHU.get(g, 2 if not g else 0)
        if so >= 2:
            ra.append(hn + timedelta(days=31 * so))
    return ra


def ngay_qua_han(t, hom_nay=None):
    """Ngày muộn nhất trong câu nếu nó QUÁ hạn giữ đơn, không thì None."""
    ds = ngay_trong_cau(t, hom_nay)
    han = han_giu_don(hom_nay)
    muon = max(ds) if ds else None
    return muon if muon and muon > han else None


# Câu có nói chuyện GIAO/HẸN — cổng chỉ soi ngày trong những câu này: kịch bản page đá tháng sinh
# ("Month of January set ang aming best-seller"), "after 3 months" trong quảng cáo giảm cân không phải lịch giao.
_GIAO = re.compile(
    r"\b(deliver\w*|schedul\w*|i-?schedule|book\w*|ship\w*|arriv\w*|rider|courier|hatid\w*|ihatid|dating|"
    r"padala|reserv\w*|hold|receive|matanggap|tanggap\w*|wait|payday|salary|sweldo|suweldo|sahod)\b|"
    r"توصيل|نوصل|يوصل|يوصلك|موعد|راتب|送達|到貨|配送|寄出", re.I | re.U)


def hua_giao_qua_han(t, hom_nay=None, kb_page=None):
    """Câu AI có HẸN GIAO vào ngày quá hạn giữ đơn không? Trả ngày đó hoặc None.

    Chỉ ngày nằm trong câu nói chuyện giao/hẹn. Câu có kèm bất kỳ ngày nào TRONG hạn thì coi là đang
    từ chối đúng luật ("can't wait until February — we hold it only until October 31") → None.
    Chép nguyên mẫu của shop thì không đụng."""
    t = str(t or "")
    if not t or (kb_page and _la_mau_cua_shop(t, kb_page)):
        return None
    han = han_giu_don(hom_nay)
    if any(d <= han for d in ngay_trong_cau(t, hom_nay, True)):
        return None
    ds = [d for c in re.split(r"(?<=[.!?。！？])\s+|\n+", t) if _GIAO.search(c) for d in ngay_trong_cau(c, hom_nay, True)]
    return max(ds) if ds and max(ds) > han else None


# ══════════════════════════════════════════════════════════════════════════════
# Tự kiểm — chạy `python3 chan_gui.py tu_kiem`''')

thay("chan_gui.py", '''         gia_page_da_bao=None, khach_chua_gui_anh=False):''',
     '''         gia_page_da_bao=None, khach_chua_gui_anh=False, hom_nay=None):''')

thay("chan_gui.py", '''    khach_chua_gui_anh — page vừa xin khách gửi ảnh mà khách chưa gửi (ai_sale tính)
    """''', '''    khach_chua_gui_anh — page vừa xin khách gửi ảnh mà khách chưa gửi (ai_sale tính)
    hom_nay    — ngày chốt để tính HẠN GIỮ ĐƠN (mặc định hôm nay; tự kiểm truyền cố định)
    """''')

thay("chan_gui.py", '''    bia_tt = _bia_thanh_toan(t, mkey)
    if bia_tt:''', '''    # ── 7c. hứa giao QUÁ HẠN GIỮ ĐƠN 1 tháng (chủ shop 14/09, ca Jessica "February 24") ──
    # Câu nói ngày quá hạn mà KHÔNG kèm ngày nào trong hạn = nhận lời khách. Câu từ chối đúng luật
    # ("we can't wait until February — we hold it only until October 31") có ngày trong hạn → qua.
    qh = hua_giao_qua_han(t, hom_nay, kb_page)
    if qh:
        pq.them(NANG, "hen_qua_han",
                f"nhận giao ngày {qh:%d/%m/%Y} — quá hạn giữ đơn (hết {han_giu_don(hom_nay):%d/%m/%Y}); shop chỉ "
                f"giữ đơn 1 tháng từ ngày chốt, phải xin khách chọn ngày trong hạn")
    bia_tt = _bia_thanh_toan(t, mkey)
    if bia_tt:''')

thay("chan_gui.py", '''CA_KIEM = [
    # (mô tả, tin, kwargs, kết mong đợi, mã lỗi bắt buộc phải có)
''', '''CA_KIEM = [
    # (mô tả, tin, kwargs, kết mong đợi, mã lỗi bắt buộc phải có)
    ("nhận giao tháng 2 năm sau (ca Jessica 14/09) — chặn",
     "Noted po Jessica 😊 1 Couple Ring Set — 12.9 KWD, free delivery, schedule sa February 24. COD po — "
     "wala kayong babayaran ngayon 💛", {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "chan", "hen_qua_han"),
    ("từ chối tháng 2, xin ngày trước 31 October — qua",
     "Pasensya po Jessica 😊 Ang order ay pwedeng i-hold hanggang October 31 lang. Kailan po ang sweldo "
     "niyo bago October 31? COD po, wala kayong babayaran ngayon 💛", {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("hẹn 30 October — trong hạn, qua",
     "Noted po! Delivery on October 30, COD — you pay the rider then 😊 Ano pong complete address niyo?", {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("\\"May 4 colors\\" tiếng Tagalog không phải tháng 5 — qua",
     "May 4 beautiful colors po tayo ngayon, free delivery 💚 Which one do you like?", {"mkey": "usa", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("tên bộ \\"1 July Birthstone Set\\" + delivery — qua",
     "Noted ma'am — 1 July Birthstone Set at 149 AED, free delivery 💎 May I have your contact number?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("tên khách Febrero — qua",
     "Hi Febrero 😊 1 Set is 149 AED, free shipping and Cash on Delivery. Which one would you like?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("\\"sa February\\" không kèm ngày (ca Jessica) — chặn",
     "Pwede ko na po i-book ngayon at ischedule ang delivery sa February pag may sweldo 😊 Okay po ba?",
     {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "chan", "hen_qua_han"),
    ("page tháng sinh nói January không phải lịch giao — qua",
     "Sa ngayon, ang Month of January set ang aming best-seller! ✨ Gusto niyo po bang i-process ang order niyo ngayon?",
     {"mkey": "usa", "hom_nay": date(2026, 9, 14)}, "qua", None),
''')

thay("chan_gui.py", '''    print(f"\\n  {tong - sai}/{tong} ca đúng." + ("" if sai else "  Cổng dùng được."))''',
     '''    hn = date(2026, 9, 14)
    for cau, mong in [("February po sir", date(2027, 2, 1)), ("feb 24 sweldo", date(2027, 2, 24)),
                      ("24 de febrero", date(2027, 2, 24)), ("sa 30 october po", None), ("next year", date(2027, 1, 1)),
                      ("after 3 months", hn + timedelta(days=93)), ("12/12", None), ("24/02/2027", date(2027, 2, 24)), ("15/10/2026", None),
                      ("December po", date(2026, 12, 1)), ("may 5", None), ("jun 5", date(2027, 6, 5)), ("may pera sa 15", None),
                      ("بعد شهرين", hn + timedelta(days=62)), ("فبراير", date(2027, 2, 1)), ("2月", date(2027, 2, 1)),
                      ("1/3 ang presyo", None), ("24/7 po", None), ("12.9 KWD", None)]:
        tong += 1
        ra = ngay_qua_han(cau, hn)
        ok = ra == mong
        sai += not ok
        print(f"  {'✅' if ok else '❌'} ngày quá hạn {cau!r:28s} → {ra}")
    print(f"\\n  {tong - sai}/{tong} ca đúng." + ("" if sai else "  Cổng dùng được."))''')

# ─────────────────────────── ai_sale.py ───────────────────────────
thay("ai_sale.py", '''def page_vua_hoi(msgs, i):''', '''# HẠN GIỮ ĐƠN 1 THÁNG — chủ shop 2026-09-14, ca Jessica Dongon (Meco Kuwait): khách "February po sir"
# (đợi lương tháng 2 năm sau), AI "I-schedule ko na po ang delivery sa February 24" và lên đơn.
# *"như vậy tôi lấy đâu ra đơn hàng … bảo khách chỉ nhận giữ đơn hàng trong vòng 1 tháng kể từ ngày
# chốt đơn, ví dụ đến hết tháng 10"*. Hạn và bộ đọc ngày ở chan_gui (CG.han_giu_don / CG.ngay_qua_han).
# Chỉ xét câu khách nói TRONG NGỮ CẢNH hẹn giao: đang nói lương/tiền, hoặc nhắc giao/nhận, hoặc page
# vừa hỏi ngày — "I bought it in March" không phải hẹn giao.
_NGU_CANH_HEN = re.compile(
    r"\\b(deliver\\w*|receive|send|ship\\w*|schedule|date|when|kailan|petsa|hatid|padala|dating|tanggap\\w*|"
    r"sweldo|suweldo|sahod|salary|payday|paid|money|pera|cash|book)\\b|توصيل|توصل|متى|موعد|تاريخ|راتب|送|到貨|薪",
    re.I | re.U)


def khach_hen_qua_han(msgs, hom_nay=None, so_tin=4):
    """Khách có hẹn giao / đợi tới một ngày QUÁ hạn giữ đơn không?

    Trả (câu khách nói ≤120 ký tự, ngày date đọc được) hoặc None. Quét `so_tin` tin khách gần nhất từ
    MỚI về CŨ: gặp tin có ngày TRONG hạn trước (khách đã đổi ý "ok October 30") thì thôi, không kéo lại.
    """
    msgs = msgs or []
    co_luong = any(m.get("boi") == "khach" and DOI_LUONG.search(lam_sach(m.get("text") or "")) for m in msgs)
    dem = 0
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        if m.get("boi") != "khach":
            continue
        dem += 1
        if dem > so_tin:
            break
        t = lam_sach(m.get("text") or "")
        ds = CG.ngay_trong_cau(t, hom_nay)
        if not ds:
            continue
        truoc = next((lam_sach(x.get("text") or "") for x in reversed(msgs[:i]) if x.get("boi") != "khach"), "")
        if not (co_luong or _NGU_CANH_HEN.search(t) or _NGU_CANH_HEN.search(truoc)):
            continue
        qh = CG.ngay_qua_han(t, hom_nay)
        return (t[:120], qh) if qh else None
    return None


def dong_han_giu_don(msgs, hom_nay=None):
    """Khối nhắc model khi khách hẹn quá hạn giữ đơn; None nếu không có."""
    qh = khach_hen_qua_han(msgs, hom_nay)
    if not qh:
        return None
    han = CG.han_giu_don(hom_nay)
    han_en = f"{han:%B} {han.day}"
    return (f'⛔ KHÁCH HẸN NGÀY QUÁ HẠN GIỮ ĐƠN: "{qh[0]}" (≈ {qh[1]:%d/%m/%Y}). Hôm nay {(hom_nay or date.today()):%d/%m/%Y}; '
            f"shop CHỈ giữ đơn trong vòng 1 tháng từ ngày chốt — hạn chót giao: {han:%d/%m/%Y} ({han_en}). "
            f"KHÔNG nhận ngày đó, KHÔNG 'schedule/book/deliver on' ngày đó, KHÔNG lên lịch giao sau {han_en}. "
            f"Áp luật HẠN GIỮ ĐƠN: nói rõ (đúng tiếng khách, nhẹ nhàng) đơn và giá khuyến mãi chỉ giữ được tới "
            f"{han_en}; COD hôm nay không trả gì; mời khách chọn một ngày giao TRƯỚC {han_en} (vd. ngày lương "
            f"gần nhất 15 hoặc 30) + xin phần còn thiếu. Níu đủ 3 lượt; sau lượt 3 khách vẫn chỉ nhận sau "
            f"{han_en} → 'treo', ghi_chu 'khách chỉ nhận hàng {qh[1]:%m/%Y} — quá hạn giữ đơn 1 tháng, sale quyết'.")


def page_vua_hoi(msgs, i):''')

thay("ai_sale.py", "import urllib.request\n", "import urllib.request\nfrom datetime import date\n")

thay("ai_sale.py", '''    hen = hen_giao_theo_luong(msgs)
    if not hen:
        return None
    cau, ngay = hen
    return (f'HẸN GIAO NGÀY LƯƠNG — khách nói: "{cau}"'
            + (f' · ngày hẹn: "{ngay}"' if ngay and ngay != cau
               else (' (câu này có ngày)' if ngay else ' · CHƯA rõ ngày — sale hỏi khách'))
            + " → giao đúng ngày đó, gọi xác nhận trước khi giao")''',
     '''    hen = hen_giao_theo_luong(msgs)
    qh = khach_hen_qua_han(msgs)
    canh_bao = (f" · ⚠️ QUÁ HẠN GIỮ ĐƠN 1 THÁNG (khách nói ≈{qh[1]:%d/%m/%Y}, hạn {CG.han_giu_don():%d/%m/%Y})"
                f" — sale gọi chốt ngày trong hạn hoặc hủy") if qh else ""
    if not hen:
        return (f'KHÁCH HẸN GIAO: "{qh[0]}"' + canh_bao) if qh else None
    cau, ngay = hen
    return (f'HẸN GIAO NGÀY LƯƠNG — khách nói: "{cau}"'
            + (f' · ngày hẹn: "{ngay}"' if ngay and ngay != cau
               else (' (câu này có ngày)' if ngay else ' · CHƯA rõ ngày — sale hỏi khách'))
            + (canh_bao or " → giao đúng ngày đó, gọi xác nhận trước khi giao"))''')

thay("ai_sale.py", '''                         "Xin ngày nhận lương (nếu chưa có) + các mục CÒN THIẾU ở trên trong MỘT tin, "
                         "chốt đơn giao ĐÚNG ngày đó, nhắc COD hôm nay không trả gì.")''',
     '''                         "Xin ngày nhận lương (nếu chưa có) + các mục CÒN THIẾU ở trên trong MỘT tin, "
                         "chốt đơn giao ĐÚNG ngày đó, nhắc COD hôm nay không trả gì. "
                         f"HẠN GIỮ ĐƠN: ngày giao phải TRƯỚC {CG.han_giu_don():%B} {CG.han_giu_don().day} "
                         f"({CG.han_giu_don():%d/%m/%Y}) — shop chỉ giữ đơn 1 tháng từ ngày chốt.")
    _qh_ = dong_han_giu_don(rec["msgs"]) if not dang_tu_van else None
    if _qh_:
        khoi_ho_so += "\\n\\n" + _qh_''')

thay("ai_sale.py", '''                # GIÁ LẠ (ca Aruna 14/09, Meco Kuwait): model tự nhân 12,9×2 = 25,8''',
     '''                # HẠN GIỮ ĐƠN (chủ shop 14/09, ca Jessica "February 24") — câu nhận giao quá hạn 1 tháng mà
                # không kèm ngày nào trong hạn → bắt soạn lại 1 lần; vẫn nhận → treo cho sale. Cổng
                # `hen_qua_han` là rào cuối.
                def _nhan_qua_han(t):
                    return bool(CG.hua_giao_qua_han(t, kb_page=kb_page))
                if (not err_m and qd and qd.get("hanh_dong") in ("tra_loi", "len_don", "tra_loi_treo")
                        and _nhan_qua_han(qd.get("tin_nhan") or "")):
                    _han_ = CG.han_giu_don()
                    print(f"{nhan} 📅 model nhận giao quá hạn giữ đơn (hết {_han_:%d/%m}) — bắt soạn lại")
                    dem["hen_qua_han"] = dem.get("hen_qua_han", 0) + 1
                    qd2, e2 = soan_bang_model(
                        noi_dung + f"\\n\\nSAI: bạn nhận giao vào ngày QUÁ hạn giữ đơn. Shop chỉ giữ đơn 1 tháng từ ngày "
                        f"chốt — hạn chót {_han_:%B} {_han_.day}. Viết lại tin_nhan đúng tiếng khách: nói nhẹ nhàng đơn "
                        f"chỉ giữ được tới {_han_:%B} {_han_.day}, COD hôm nay không trả gì, mời khách chọn ngày giao "
                        f"trước {_han_:%B} {_han_.day}. KHÔNG nhắc lại ngày quá hạn như một lịch đã hẹn.", on_dinh)
                    if not e2 and qd2 and not _nhan_qua_han(qd2.get("tin_nhan") or ""):
                        qd = qd2
                    else:
                        qd = {"hanh_dong": "treo", "tin_nhan": "",
                              "ly_do": "khách hẹn giao quá hạn giữ đơn 1 tháng",
                              "ghi_chu": f"Khách hẹn giao sau {_han_:%d/%m/%Y} — quá hạn giữ đơn 1 tháng, sale chốt ngày trong hạn"}
                # GIÁ LẠ (ca Aruna 14/09, Meco Kuwait): model tự nhân 12,9×2 = 25,8''')

# ─────────────────────────── luat_model.md ───────────────────────────
thay("luat_model.md", '''KHÁCH NÓI "ĐÃ MUA TỪ MÌNH" MÀ HỆ THỐNG KHÔNG CÓ ĐƠN (chủ shop chốt 2026-09-14):''',
     '''HẠN GIỮ ĐƠN 1 THÁNG (chủ shop chốt 2026-09-14 — MỌI thị trường):
Ca mẫu: khách "February po sir" (đợi lương tháng 2 năm sau) → SAI: "Noted po Jessica 😊 I-schedule ko
na po ang delivery sa February 24". Chủ shop: *"khách hẹn tận tháng 2 năm sau bạn cũng ok à, như vậy
tôi lấy đâu ra đơn hàng — bảo khách chỉ nhận giữ đơn hàng trong vòng 1 tháng kể từ ngày chốt đơn"*.
  HẠN = ngày cuối của tháng liền sau tháng chốt (chốt 14/09 → giao muộn nhất 31/10). Hệ thống ghi sẵn
  ngày hạn chót trong khối hồ sơ — dùng đúng ngày đó, đừng tự tính.
  ⛔ CẤM nhận / xác nhận / "schedule, book, deliver on" bất kỳ ngày nào sau hạn (tháng sau nữa, năm
     sau, "after 3 months"). Cổng chặn sẽ chặn.
  ✅ Nói nhẹ nhàng, đúng tiếng khách: đơn và giá khuyến mãi chỉ giữ được tới <hạn>; COD hôm nay không
     trả gì; mời khách chọn ngày giao TRƯỚC hạn (ngày lương gần nhất — 15 hoặc 30 — hoặc lúc có tiền
     mặt) + xin phần còn thiếu. Mẫu: "Pasensya po Jessica 😊 We can only hold the order and promo price
     until October 31. COD po — nothing to pay today. Which date before October 31 works for you?"
  ✅ Níu đủ 3 lượt như luật ĐỢI LƯƠNG. CHỈ sau lượt 3 khách vẫn chỉ nhận sau hạn → "treo", ghi_chu
     "khách chỉ nhận hàng <tháng> — quá hạn giữ đơn 1 tháng, sale quyết".

KHÁCH NÓI "ĐÃ MUA TỪ MÌNH" MÀ HỆ THỐNG KHÔNG CÓ ĐƠN (chủ shop chốt 2026-09-14):''')

thay("luat_model.md", '''  ✅ Khách cho ngày → xác nhận rõ "we'll deliver on <ngày>, pay the rider then" và đi tiếp luồng''',
     '''  ✅ Khách cho ngày TRONG HẠN GIỮ ĐƠN (xem mục HẠN GIỮ ĐƠN 1 THÁNG) → xác nhận rõ "we'll deliver on <ngày>, pay the rider then" và đi tiếp luồng''')

for ten, s in MOI.items():
    with open(os.path.join(D, ten), "w", encoding="utf-8") as f:
        f.write(s)
    print(f"✅ đã vá {ten}")

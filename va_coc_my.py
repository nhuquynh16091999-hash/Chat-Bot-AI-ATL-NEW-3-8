"""Vá ai_sale.py: Mỹ/Úc hỏi PTTT sau xác nhận nhà + MoneyGram/Western Union/Money Order phải cọc $50.

Chủ shop 14/09 tối, ca Philip Gutib (Madam Mystic Fengshui Expert USA). Chạy: python3 va_coc_my.py ai_sale.py
Mỗi chỗ thay phải khớp đúng 1 lần — khớp khác thì thoát, KHÔNG ghi (nhiều phiên cùng sửa file).
"""
import sys

f = sys.argv[1]
s = open(f, encoding="utf-8").read()
if "def buoc_thu_tien_sau" in s:
    sys.exit("đã vá rồi — không làm gì")

VA = []

# ── 1. hàm đo bước chốt 2 + cọc ──────────────────────────────────────────────
VA.append(("XIN_THONG_TIN_MAU = re.compile(", r'''# ─────────── Mỹ/Úc: CHỐT 2 (phương thức thanh toán) + CỌC — chủ shop 14/09 tối ───────────
# Ca Philip Gutib (Madam Mystic Fengshui Expert USA): sale gửi /XN_NHÀ → khách "Yes po" → sale gửi /thanhtoan →
# khách "Money gram or palawan … gửi luôn dù chưa nhận hàng?". AI không trả lời câu thanh toán (cửa CHỐT_SOM
# tưởng còn đang tư vấn nên ép về mẫu "khó khăn tài chính"), rồi lên đơn "Kumpirmado na po ang inyong paraan ng
# pagbabayad" — không gửi hướng dẫn chuyển, không đòi cọc; sale phải vào gửi /MoneyGram+WesternUnion + cọc $50.
# *"ở mỹ bạn k hỏi khách PTTT, sau chỗ xác nhận nhà à, đối với moneygram, money order phải cọc mà"*.
# Chủ shop chốt: cọc $50 MỌI đơn, CHỈ MoneyGram / Western Union / Money Order. Check, Zelle… vẫn trả sau khi nhận.
TIEN_COC_USD = 50
TEN_XN_NHA = re.compile(r"XN_?NH[ÀA]|NH[ÀA]_?L[ẦA]N", re.I)
NOI_DUNG_XN_NHA = re.compile(
    r"ito\s+ba\s+ang\s+address|is\s+this\s+(?:the|your)\s+(?:correct\s+)?(?:address|house|home)"
    r"|confirm\s+(?:your|the)\s+(?:address|house|home)", re.I)
TEN_MAU_PTTT = re.compile(r"^\s*(?:thanh_?toan|PTTT(?:_L\d)?)\s*$", re.I)
R_PTTT_KHACH = re.compile(
    r"\b(zelle|venmo|cash\s?app|paypal|pay\s?pal|check|cheque|tseke|money\s?order|money\s?gram"
    r"|western\s?union|palawan|cash\s?deposit|debit\s?card|credit\s?card)\b", re.I)
PTTT_CAN_COC = re.compile(r"money\s?gram|western\s?union|money\s?order", re.I)
# Câu ĐÒI CỌC của page. "deposit" trơn không tính: /CHECK_ có "mobile/remote deposit", /MoneyGram có "DEPOSIT TO BANK".
DOI_COC = re.compile(
    r"(?:small|\$\s?\d+)\s+deposit|deposit\s+(?:of|first|to\s+(?:secure|reserve))|down\s?payment"
    r"|reservation\s+fee|paunang\s+bayad|secure\s+your\s+order", re.I)
BAO_DA_CHUYEN = re.compile(
    r"\b(mtcn|reference|ref\.?\s*(?:no|number|#)|receipt|resibo|sent|paid|done|nagpadala|ipinadala"
    r"|pinadala|nabayaran|nagbayad|transferred)\b", re.I)
KHANG_DINH_DON = re.compile(
    r"kumpirmado\s+na\s+po\s+ang\s+inyong\s+paraan|payment\s+method\s+(?:is\s+|has\s+been\s+)?confirmed"
    r"|your\s+order\s+(?:is|has\s+been)\s+confirmed", re.I)
KHACH_CHE_NHA = re.compile(r"\b(no|not|hindi|wrong|mali|maling)\b", re.I)


def buoc_thu_tien_sau(msgs, kb_page):
    """Hội thoại Mỹ/Úc đang ở đâu trong chốt 1 (xác nhận nhà) → chốt 2 (PTTT) → cọc (mục 9b)."""
    mau = [m for m in (kb_page or {}).get("mau") or [] if m.get("tin")]
    m_nha = [m for m in mau if TEN_XN_NHA.search(m.get("tu_khoa") or "")]
    m_pttt = [m for m in mau if TEN_MAU_PTTT.match(m.get("tu_khoa") or "")]
    i_nha = i_pttt = i_coc = None
    for i, m in enumerate(msgs):
        t = m.get("text") or ""
        if m["boi"] not in ("nguoi", "ai", "botcake") or not t.strip() or "AI SALE" in t:
            continue
        if NOI_DUNG_XN_NHA.search(t) or any(_khop_mau(t, x) >= 0.5 for x in m_nha):
            i_nha = i
        if (any(_khop_mau(t, x) >= 0.5 for x in m_pttt)
                or len({re.sub(r"\W", "", x.lower()) for x in R_PTTT_KHACH.findall(t)}) >= 3):
            i_pttt = i
        if DOI_COC.search(t):
            i_coc = i
    kh = lambda tu: [(i, m) for i, m in enumerate(msgs) if i > tu and m["boi"] == "khach"]
    nha_ok = (i_pttt is not None and (i_nha is None or i_pttt > i_nha)) or (
        i_nha is not None and any(lam_sach(m.get("text") or "").strip()
                                  and not KHACH_CHE_NHA.search(lam_sach(m.get("text") or ""))
                                  for _, m in kh(i_nha)))
    pttt = cau = nhac = None
    for m in msgs:
        if m["boi"] == "khach":
            t = lam_sach(m.get("text") or "")
            # "check" hay là động từ ("can I check the item first") — chỉ tính khi câu ngắn / "by check"
            g = [x for x in R_PTTT_KHACH.findall(t)
                 if x.lower() != "check" or len(t.split()) <= 5
                 or re.search(r"(?:by|with|via|thru|through|sa|pay)\s+check|check\s+(?:payment|po\b)", t, re.I)]
            if not g:
                continue
            ten = " / ".join(dict.fromkeys(x.lower() for x in g))
            nhac = ten
            # Đo 72h Mỹ 14/09: "Do you have zelle?" không phải đã chọn; "I will pay you by Check, your name?" thì là chọn.
            if HS.la_cau_hoi(t) and not re.search(r"\b(i\s*will|i'?ll|i\s*can|i\s*want|by|via|thru|through|using)\b", t, re.I):
                continue
            pttt, cau = ten, t[:120]
    can_coc = bool(nhac and PTTT_CAN_COC.search(nhac))
    da_coc = i_coc is not None and any(
        (m.get("co_dinh_kem") and not m.get("voice"))
        or (BAO_DA_CHUYEN.search(lam_sach(m.get("text") or "")) and not HS.la_cau_hoi(lam_sach(m.get("text") or "")))
        for _, m in kh(i_coc))
    return {"hoi_nha": i_nha is not None, "nha_ok": nha_ok, "hoi_pttt": i_pttt is not None,
            "pttt": pttt, "cau_pttt": cau, "nhac": nhac, "can_coc": can_coc, "doi_coc": i_coc is not None, "da_coc": da_coc}


def chua_du_9b(b):
    """None nếu đã đủ để len_don; còn thiếu thì (lý do, việc phải làm lượt này)."""
    if not b["nha_ok"]:
        return ("khách CHƯA xác nhận đúng nhà",
                "chốt 1: khách vừa cho địa chỉ mà chưa ai hỏi xác nhận nhà → hanh_dong 'xac_minh_nha'; đã hỏi mà khách "
                "chưa trả lời → trả lời đúng điều khách hỏi, không xác nhận đơn")
    if b["can_coc"] and not b["doi_coc"]:
        return (f"khách nói tới {b['nhac']} — phải CỌC ${TIEN_COC_USD} trước mà chưa đòi cọc",
                f"gửi mẫu hướng dẫn của phương thức đó trong kịch bản (đặt tên mẫu vào anh_mau) + nói rõ cần cọc "
                f"${TIEN_COC_USD} trước để giữ đơn, phần còn lại trả khi nhận hàng; nhờ khách chuyển xong gửi MTCN / "
                f"ảnh biên lai")
    if not b["pttt"]:
        return ("khách CHƯA chọn phương thức thanh toán"
                + (f" (mới hỏi về {b['nhac']})" if b["nhac"] else ""),
                "hỏi phương thức thanh toán theo NGUYÊN VĂN mẫu /thanhtoan hoặc /PTTT_L2 của kịch bản (page đã gửi danh "
                "sách rồi hoặc khách đang hỏi về một phương thức thì trả lời đúng câu khách hỏi + hỏi khách chốt cách nào)")
    if b["can_coc"] and not b["da_coc"]:
        return (f"đã đòi cọc ${TIEN_COC_USD} nhưng khách CHƯA gửi MTCN / biên lai",
                f"trả lời đúng điều khách hỏi + nhắc khách chuyển cọc ${TIEN_COC_USD} rồi gửi MTCN / ảnh biên lai")
    return None


def dong_thu_tien_sau(msgs, kb_page):
    """Dòng nhắc bước 9b chèn cạnh khối hồ sơ (Mỹ/Úc) — model biết lượt này phải làm đúng việc gì."""
    b = buoc_thu_tien_sau(msgs, kb_page)
    # Chỉ nhắc khi PAGE đã tới chốt (đã hỏi nhà / đã gửi danh sách PTTT). Khách cũ nhắc "I already zelle" mà page
    # chưa đi bước nào (đo 72h Mỹ 14/09: ~15 hội thoại kiểu này) → không đẩy model đi xác minh nhà; luật cứng vẫn chặn len_don.
    if not (b["hoi_nha"] or b["hoi_pttt"]):
        return None
    thieu = chua_du_9b(b)
    dau = ("⚠️ BƯỚC THANH TOÁN (Mỹ/Úc — mục 9b): "
           + ("khách ĐÃ xác nhận đúng nhà. " if b["nha_ok"] else "")
           + (f"khách đã nói phương thức: \"{b['cau_pttt']}\" → {b['pttt']}. " if b["pttt"] else ""))
    if thieu:
        return (dau + f"CHƯA ĐỦ để lên đơn ({thieu[0]}). Việc lượt này: {thieu[1]}. CẤM chọn 'len_don', CẤM gửi "
                "câu xác nhận đơn (/XÁC_NHẬN_ĐƠN, \"Kumpirmado…\", \"payment method confirmed\"). MoneyGram / Western "
                f"Union / Money Order LUÔN phải cọc ${TIEN_COC_USD} trước, còn lại trả khi nhận; khách không muốn cọc → "
                "mời chọn cách trả SAU khi nhận hàng khác trong /thanhtoan. Phương thức không có mẫu hướng dẫn trong "
                "kịch bản (vd Palawan) → không nhận, đưa lại danh sách.")
    return (dau + ("khách đã báo chuyển cọc → " if b["can_coc"] else "")
            + "ĐỦ chốt 1 + 2: chọn 'len_don'. tin_nhan = mẫu hướng dẫn phương thức đó (anh_mau) nếu page CHƯA gửi, "
            "rồi câu xác nhận đơn theo /XÁC_NHẬN_ĐƠN với đúng tổng tiền"
            + (f"; ghi rõ đã cọc ${TIEN_COC_USD}, còn lại trả khi nhận hàng. ghi_chu: 'khách báo đã cọc "
               f"${TIEN_COC_USD} qua {b['pttt']} — sale kiểm tiền về'" if b["can_coc"] else "") + ".")


XIN_THONG_TIN_MAU = re.compile('''))

# ── 2. kịch bản theo bước: mẫu sau-chốt (xác nhận nhà, PTTT, hướng dẫn chuyển, cọc) cũng là PHẦN CHỐT ──
VA.append(('''    if sum(1 for m in buoc if NOI_DUNG_TAM_LINH.search("\\n".join(m["tin"]))) < 2:
        return None
    return buoc, chot''', '''    if sum(1 for m in buoc if NOI_DUNG_TAM_LINH.search("\\n".join(m["tin"]))) < 2:
        return None
    # Mẫu SAU CHỐT nằm rải cuối kịch bản (/XN_NHÀ, /thanhtoan, /PTTT_L2, /MoneyGram…, /Care_cọc) — trước 14/09
    # không tính nên page đã hỏi nhà + PTTT mà vẫn bị coi là "đang tư vấn": cửa CHỐT_SOM ép AI gửi mẫu khó khăn
    # tài chính thay cho câu trả lời MoneyGram (ca Philip Gutib, Madam Mystic USA).
    chot += [m for m in ds if m not in buoc and m not in chot
             and (TEN_XN_NHA.search(m.get("tu_khoa") or "") or TEN_MAU_PTTT.match(m.get("tu_khoa") or "")
                  or re.search(r"money|western|zelle|venmo|cash_?app|paypal|check_|x[áa]c_?nh[ậa]n_?đ|c[ọo]c",
                               m.get("tu_khoa") or "", re.I))]
    return buoc, chot'''))

# ── 3. nhắc bước 9b trong gói soạn ───────────────────────────────────────────
VA.append(('''        khoi_ho_so += "\\n\\n" + _tg_''', '''        khoi_ho_so += "\\n\\n" + _tg_
    _9b_ = (dong_thu_tien_sau(rec["msgs"], kb_page)
            if rec.get("thi_truong") in HS.THU_TIEN_SAU and not dang_tu_van else None)
    if _9b_:
        khoi_ho_so += "\\n\\n" + _9b_'''))

# ── 4. luật cứng: Mỹ/Úc chưa đủ chốt 1 + 2 (+ cọc) thì không lên đơn, không xác nhận đơn ──
VA.append(('''                # GIÁ LẠ (ca Aruna 14/09, Meco Kuwait)''', '''                # MỸ/ÚC LÊN ĐƠN KHI CHƯA HỎI PTTT / CHƯA CỌC (chủ shop 14/09 tối, ca Philip Gutib) — luật cứng,
                # không tin prompt: len_don hoặc câu xác nhận đơn khi chưa xác nhận nhà / chưa chọn PTTT / MoneyGram-
                # Western Union-Money Order chưa cọc $50 → bắt soạn lại 1 lần đúng việc còn thiếu; vẫn sai → treo.
                if not err_m and qd and mkey in HS.THU_TIEN_SAU and qd.get("hanh_dong") in ("tra_loi", "len_don", "tra_loi_treo"):
                    _b9_ = buoc_thu_tien_sau(msgs, kb_page)
                    _th9_ = chua_du_9b(_b9_)
                    _xn_don = [m for m in (kb_page or {}).get("mau") or []
                               if re.search(r"x[áa]c_?nh[ậa]n_?đ", m.get("tu_khoa") or "", re.I)]

                    def _sai9(q):
                        t = (q or {}).get("tin_nhan") or ""
                        return (q or {}).get("hanh_dong") == "len_don" or bool(KHANG_DINH_DON.search(t)) \\
                            or any(_khop_mau(t, x) >= 0.5 for x in _xn_don)
                    if _th9_ and _sai9(qd):
                        print(f"{nhan} 💳 Mỹ/Úc: model định chốt đơn khi {_th9_[0]} — bắt soạn lại")
                        dem["chua_du_9b"] = dem.get("chua_du_9b", 0) + 1
                        qd2, e2 = soan_bang_model(
                            noi_dung + f"\\n\\nSAI BƯỚC (Mỹ/Úc, mục 9b): {_th9_[0]}. KHÔNG được chọn 'len_don', KHÔNG "
                            f"gửi câu xác nhận đơn. Viết lại — việc lượt này: {_th9_[1]}. Đúng tiếng khách, trả lời "
                            f"luôn điều khách vừa hỏi.", on_dinh)
                        if not e2 and qd2 and (qd2.get("hanh_dong") in ("tra_loi", "tra_loi_treo", "xac_minh_nha", "treo")) \\
                                and not _sai9(qd2):
                            qd = qd2
                        else:
                            print(f"{nhan} 💳 soạn lại vẫn chốt — treo cho sale")
                            qd = {"hanh_dong": "treo", "tin_nhan": "",
                                  "ly_do": f"Mỹ/Úc chưa đủ bước: {_th9_[0]}"[:60],
                                  "ghi_chu": f"AI không chốt được: {_th9_[0]} — sale {_th9_[1][:80]}"}
                # GIÁ LẠ (ca Aruna 14/09, Meco Kuwait)'''))

for cu, moi in VA:
    n = s.count(cu)
    if n != 1:
        sys.exit(f"❌ chỗ vá khớp {n} lần (phải đúng 1): {cu[:70]!r} — KHÔNG ghi gì")
    s = s.replace(cu, moi)
open(f, "w", encoding="utf-8").write(s)
print(f"✅ đã vá {len(VA)} chỗ vào {f}")

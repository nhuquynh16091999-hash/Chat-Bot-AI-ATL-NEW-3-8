#!/usr/bin/env python3
"""Vá 14/09 tối — ca Lucy JJ (Madam Mystic Fengshui Expert USA). Chủ shop: "níu khách thêm vài câu + gửi feedback".

1. chan_gui.tieng_yeu_cau: "Hindi lang muna po" (Tagalog: chưa đâu) KHÔNG phải lời xin tiếng Hindi.
2. ai_sale.khach_dang_tu_choi: "Hindi ko naintidihan ang mga letra ito" (không đọc được chữ) KHÔNG phải từ chối.
3. Níu 5 lượt (trước 3): L1 giữ ưu đãi · L2 gửi FEEDBACK kèm ảnh mẫu page · L3 hạ giá (chê giá) · L4-5 góc khác · sau 5 → treo.
4. Khách chào/cảm ơn ("Salamat, have a great day, God bless") SAU KHI đã từ chối = từ chối mềm → níu tiếp.

Cách chạy: python3 va_niu_5_luot.py <thư mục pancake-tool>. Mỗi chỗ thay phải khớp đúng 1 lần, không thì thoát, KHÔNG ghi.
"""
import os
import sys

D = sys.argv[1] if len(sys.argv) > 1 else "."


def va(ten, cap):
    p = os.path.join(D, ten)
    s = open(p, encoding="utf-8").read()
    for cu, moi in cap:
        n = s.count(cu)
        if n != 1:
            sys.exit(f"✖ {ten}: đoạn cần thay khớp {n} lần (phải 1) — KHÔNG ghi gì:\n{cu[:200]}")
        s = s.replace(cu, moi)
    return p, s


# ───────────── chan_gui.py ─────────────
CG = [(
    '''def tieng_yeu_cau(t):
    """Khách XIN nói tiếng gì? -> mã tiếng ('hi', 'ur', 'ar'…), '?' = khách chỉ nói không biết
    tiếng Anh, None = câu này không phải yêu cầu về ngôn ngữ."""
    t = str(t or "").strip()
    if not t:
        return None
    ma = None
    for rx in _YEU_CAU:
        m = rx.search(t)
        if m:
''',
    '''# "HINDI" TAGALOG ≠ TIẾNG HINDI (chủ shop 14/09 tối, ca Lucy JJ — Madam Mystic Fengshui Expert USA): khách "Hindi
# lang muna po .at maraming salamat" (= chưa đâu, cảm ơn) khớp mẫu "<tên> lang" → AI viết nguyên tin bằng chữ
# Devanagari, khách đáp "Hindi ko naintidihan ang mga letra ito" (không đọc được chữ này) — mất trắng một lượt níu.
# "hindi" = "không" trong Tagalog: câu có từ Tagalog đi kèm, không có chữ "language", không phải Hinglish → bỏ qua.
_TL_KEM_HINDI = re.compile(
    r"\\b(?:po|opo|muna|lang|ko|ako|akong|kami|ang|ng|mga|sa|salamat|naman|kayo|ito|dito|wala|pero|kasi)\\b", re.I)


def tieng_yeu_cau(t):
    """Khách XIN nói tiếng gì? -> mã tiếng ('hi', 'ur', 'ar'…), '?' = khách chỉ nói không biết
    tiếng Anh, None = câu này không phải yêu cầu về ngôn ngữ."""
    t = str(t or "").strip()
    if not t:
        return None
    ma = None
    for rx in _YEU_CAU:
        m = rx.search(t)
        if m and m.group("ten").lower() == "hindi" and not re.search(r"\\blanguage\\b", t, re.I) \\
                and _TL_KEM_HINDI.search(t) and not la_hinglish(t):
            continue                  # "Hindi lang muna po" — Tagalog (ca Lucy JJ 14/09)
        if m:
'''),
]

# ───────────── ai_sale.py ─────────────
AI = [
    # 2. không hiểu chữ ≠ từ chối
    ('''_TU_CHOI_YEU = re.compile(r"w(a)?la(ng)?(\\s+pa)?|hindi|no|wait|later", re.I)
''',
     '''_TU_CHOI_YEU = re.compile(r"w(a)?la(ng)?(\\s+pa)?|hindi|no|wait|later", re.I)
# Khách kêu KHÔNG ĐỌC / KHÔNG HIỂU tin page (ca Lucy JJ 14/09 tối: AI lỡ viết chữ Hindi, khách "Hindi ko naintidihan
# ang mga letra ito") — "hindi" ở đây là "không hiểu", tính là từ chối thì mất một lượt níu và treo sớm.
KHONG_HIEU = re.compile(
    r"\\b(?:hindi|di|not|don'?t|dont|can'?t|cant|cannot|no)\\s+(?:\\w+\\s+){0,2}"
    r"(?:\\w*int[ie]{1,2}ndi\\w*|\\w*intidihan|understand|understood|read|nababasa|mabasa|basahin)\\b"
    r"|\\b(?:letra|letters|language|lengg?u?wahe)\\b", re.I)
# Chào / cảm ơn kết thúc — SAU một lời từ chối là từ chối mềm, vẫn phải níu (ca Lucy JJ 14/09 tối:
# "Maraming Salamat Madam Mystic .Have a great day po .God bless us all." → AI im).
CHAO_TAM_BIET = re.compile(
    r"\\b(have\\s+a\\s+(?:great|good|nice|blessed|wonderful)\\s+(?:day|night|evening|weekend)|god\\s+bless|take\\s+care"
    r"|good\\s*bye|bye|good\\s*night|see\\s+you|thank\\s*(?:s|you|u)?|thanks?|salamat|ingat|pagpalain|شكرا|مع\\s+السلامة)\\b"
    r"|謝謝|多謝", re.I | re.U)
LUOT_NIU = 5          # chủ shop 14/09 tối: níu 5 lượt (trước là 3), lượt 2 gửi feedback khách thật
'''),
    ('''    if (_ms and all(_TU_CHOI_YEU.fullmatch(m) for m in _ms) and len(re.findall(r"\\w+", t)) >= 6
            and _hoi and not THIEU_TIEN.search(t) and not la_che_dat(t)):
        return False
    return True
''',
     '''    if (_ms and all(_TU_CHOI_YEU.fullmatch(m) for m in _ms) and len(re.findall(r"\\w+", t)) >= 6
            and _hoi and not THIEU_TIEN.search(t) and not la_che_dat(t)):
        return False
    if _ms and all(_TU_CHOI_YEU.fullmatch(m) for m in _ms) and KHONG_HIEU.search(t) \\
            and not THIEU_TIEN.search(t) and not la_che_dat(t):
        return False              # "Hindi ko naintidihan…" — kêu không hiểu chữ (ca Lucy JJ 14/09)
    return True


# Chữ đệm được phép đứng quanh lời chào ("Maraming Salamat Madam Mystic .Have a great day po .God bless us all.").
_CHAO_DEM = re.compile(
    r"\\b(po|opo|madam|madame|mam|maam|ma'?am|sir|dear|sis|miss|kuya|ate|bro|ok|okay|okey|oky|maraming|marami|many|much"
    r"|so|very|you|u|too|all|us|everyone|for|the|your|time|again|also|and|to|a|nga|sa|inyo|ninyo|ang|ng|na|lord|always|have|great|good|nice|happy|day|night|blessed)\\b",
    re.I)


def _la_chao_sau_tu_choi(kh, j):
    """Tin khách kh[j] CHỈ là lời chào/cảm ơn kết thúc (bỏ chữ chào + chữ đệm còn ≤ 2 từ), đứng sau một lời từ chối
    THẬT (không tính "ok thanks" trơn) trong 3 tin khách trước đó.

    Đo so_chi_phi mọi nước 14/09: bản đầu (chỉ cần có chữ thanks/salamat) bắt 26 câu, phần lớn oan — "Thanks i received
    now my order", "Please arrange my shipment delivery ASAP thanks", tin "Thank you" trước đó bị tính là từ chối."""
    t = lam_sach(kh[j].get("text")).strip()
    if not t or not CHAO_TAM_BIET.search(t) or khach_dang_tu_choi(t) or "?" in t or len(t.split()) > 20 \\
            or re.search(r"\\d", t) or HOI_MUA.search(t) or MUON_MUA.search(t) \\
            or re.search(r"\\b(yes|yeah|opo|sure|receiv\\w*|reciev\\w*|arriv\\w*|order\\w*|deliver\\w*|rider|cancel\\w*|wait"
                         r"|aantay\\w*|pray\\w*|dasal|recover\\w*)\\b", t, re.I):
        return False
    if len(re.findall(r"[^\\W\\d_]+", _CHAO_DEM.sub(" ", CHAO_TAM_BIET.sub(" ", t)), re.U)) > 2:
        return False
    # Tin khách GẦN NHẤT trước đó (bỏ qua lời chào / "ok thanks" / kêu không hiểu chữ) phải là lời từ chối THẬT —
    # khách đã cho SĐT/địa chỉ hay hỏi chuyện khác sau lời từ chối thì "thank you" không còn là từ chối.
    for x in range(j - 1, max(-1, j - 4), -1):
        u = lam_sach(kh[x].get("text")).strip()
        if not u or DAP_KET.match(u) or (CHAO_TAM_BIET.search(u) and not khach_dang_tu_choi(u)) or KHONG_HIEU.search(u):
            continue
        return khach_dang_tu_choi(u)
    return False


def khach_chao_sau_tu_choi(msgs):
    """Tin khách CUỐI là lời chào/cảm ơn sau khi đã từ chối, page vừa níu (AI/Botcake — không phải sale thật, không
    phải câu 'còn câu hỏi nào không?') → trả câu đó; không thì None."""
    idx = [k for k, m in enumerate(msgs or []) if m.get("boi") == "khach" and lam_sach(m.get("text")).strip()]
    if not idx:
        return None
    i = idx[-1]
    truoc = next((m for m in reversed(msgs[:i]) if m.get("boi") != "khach" and m.get("boi") != "hethong"
                  and (m.get("text") or "").strip()), None)
    if not truoc or truoc.get("boi") not in ("ai", "botcake") or HOI_KET.search(lam_sach(truoc.get("text") or "")):
        return None
    kh = [msgs[k] for k in idx]
    return lam_sach(kh[-1]["text"])[:120] if _la_chao_sau_tu_choi(kh, len(kh) - 1) else None
'''),
    # 3+4. tinh_huong_tu_choi: 5 lượt + chào sau từ chối
    ('''def tinh_huong_tu_choi(msgs):
    """(câu khách, lượt níu 1-3, tập giá đã báo) nếu tin cuối của khách là lời từ chối; không thì None."""
    kh = [m for m in (msgs or []) if m.get("boi") == "khach" and lam_sach(m.get("text")).strip()]
    if not kh or not khach_dang_tu_choi(kh[-1]["text"]):
        return None
    lan = sum(1 for m in kh if khach_dang_tu_choi(m["text"]))
    return lam_sach(kh[-1]["text"])[:120], min(lan, 3), tien_page_da_noi(msgs)
''',
     '''def tinh_huong_tu_choi(msgs):
    """(câu khách, lượt níu 1..LUOT_NIU+1, tập giá đã báo) nếu tin cuối của khách là lời từ chối — hoặc lời chào/cảm
    ơn ngay sau lời từ chối (ca Lucy JJ 14/09); không thì None. Lượt LUOT_NIU+1 = đã níu đủ, treo cho sale."""
    kh = [m for m in (msgs or []) if m.get("boi") == "khach" and lam_sach(m.get("text")).strip()]
    if not kh or not (khach_dang_tu_choi(kh[-1]["text"]) or khach_chao_sau_tu_choi(msgs)):
        return None
    # Đếm trong PHIÊN hiện tại (sau mốc mở phiên mới, ≤ LUONG_HIEU_LUC_GIAY) — trần 5 lượt thì một câu "ok thanks"
    # tuần trước cũng đủ đẩy khách sang treo sớm.
    dau = max([k for k, m in enumerate(msgs) if m.get("boi") == "hethong" and _MO_PHIEN_MOI.search(m.get("text") or "")]
              or [0])
    moi = _moc_giay(kh[-1].get("luc"))
    kh_p = [m for m in msgs[dau:] if m.get("boi") == "khach" and lam_sach(m.get("text")).strip()
            and (moi is None or (_moc_giay(m.get("luc")) or moi) >= moi - LUONG_HIEU_LUC_GIAY)] or kh[-1:]
    lan = sum(1 for j, m in enumerate(kh_p) if khach_dang_tu_choi(m["text"]) or _la_chao_sau_tu_choi(kh_p, j))
    return lam_sach(kh[-1]["text"])[:120], min(max(lan, 1), LUOT_NIU + 1), tien_page_da_noi(msgs)


# FEEDBACK KHÁCH THẬT Ở LƯỢT NÍU 2 (chủ shop 14/09 tối, ca Lucy JJ): 131/290 page có mẫu tên "Feedback…" kèm ảnh.
MAU_FEEDBACK = re.compile(r"feed\\s*back|testimon|review|phản\\s*hồi|đánh\\s*giá", re.I)


def mau_feedback(kb_page, msgs):
    """Mẫu feedback CÓ ẢNH của page mà hội thoại chưa gửi (nhiều ảnh nhất trước), không có thì None."""
    ds = [m for m in (kb_page or {}).get("mau") or []
          if MAU_FEEDBACK.search(m.get("tu_khoa") or "") and m.get("anh") and (m.get("tu_khoa") or "").strip()]
    ds = [m for m in ds if not da_gui_huong_dan(msgs or [], m)]
    return max(ds, key=lambda m: len(m["anh"]), default=None)


def feedback_luot_niu(msgs, kb_page, pid):
    """Mẫu feedback phải gửi kèm lượt này (lượt níu 2, kênh ảnh bật, page không bị FB chặn), không thì None."""
    tc = tinh_huong_tu_choi(msgs)
    if not tc or tc[1] != 2 or not gui_anh_bat() or str(pid) in _FB_CHAN or hen_giao_theo_luong(msgs):
        return None
    return mau_feedback(kb_page, msgs)
'''),
    # ai_co_vao_cuoc: đủ lượt → treo; chào sau từ chối → trả lời
    ('''    if HEN_SAU.search(chu) and "botcake" not in sau:
        return "tra_loi", "khách hẹn nhắn lại / hoãn mua — níu bằng câu giữ ưu đãi, không để khách đi"
''',
     '''    _tc0 = tinh_huong_tu_choi(msgs) if "botcake" not in sau else None
    if _tc0 and _tc0[1] > LUOT_NIU:
        return "treo", f"khách từ chối lần {_tc0[1]}+ — AI đã níu đủ {LUOT_NIU} lượt, sale quyết"
    if HEN_SAU.search(chu) and "botcake" not in sau:
        return "tra_loi", "khách hẹn nhắn lại / hoãn mua — níu bằng câu giữ ưu đãi, không để khách đi"
    if _tc0 and khach_chao_sau_tu_choi(msgs):
        return "tra_loi", "khách chào/cảm ơn sau khi đã từ chối — từ chối mềm, níu tiếp (ca Lucy JJ 14/09)"
'''),
    # rec có pid để goi_soan biết page bị FB chặn
    ('''            rec = {"msgs": msgs, "ten_khach": ten_khach, "thi_truong": mkey,
''',
     '''            rec = {"msgs": msgs, "ten_khach": ten_khach, "thi_truong": mkey, "pid": str(pid),
'''),
    # prompt hệ thống trong code
    ('''- NÍU KHÁCH ĐỦ 3 LẦN (chủ shop chốt 2026-09-14): mọi lời từ chối/trì hoãn → thuyết phục 3 lượt,
  mỗi lượt một góc khác, lượt 3 dùng cửa hạ giá; chỉ khi khách từ chối cả 3 lượt mới treo.
''',
     '''- NÍU KHÁCH ĐỦ 5 LẦN (chủ shop chốt 2026-09-14, nâng 3 → 5 tối 14/09): mọi lời từ chối/trì hoãn → thuyết phục 5 lượt,
  mỗi lượt một góc khác, lượt 2 gửi feedback khách thật, lượt 3 dùng cửa hạ giá; chỉ khi khách từ chối cả 5 lượt mới treo.
'''),
    ('''Níu đủ 3 lượt; sau lượt 3 khách vẫn chỉ nhận sau "''',
     '''Níu đủ {LUOT_NIU} lượt; sau lượt {LUOT_NIU} khách vẫn chỉ nhận sau "'''),
    # goi_soan: tình huống từ chối
    ('''        _bang_chung = chung_minh_gia(rec["msgs"], kb_page, rec.get("thi_truong"))[0] if _che_dat else []
''',
     '''        _bang_chung = chung_minh_gia(rec["msgs"], kb_page, rec.get("thi_truong"))[0] if _che_dat else []
        _fb = feedback_luot_niu(rec["msgs"], kb_page, rec.get("pid"))
        _dong_fb = (f"\\n🖼 LƯỢT NÍU 2 — GỬI FEEDBACK KHÁCH THẬT: hệ thống gửi kèm ảnh feedback của mẫu /{_fb['tu_khoa'].strip()} "
                    f"(đặt \\"anh_mau\\": \\"{_fb['tu_khoa'].strip()}\\"). Trong tin, MỘT câu giới thiệu đây là ảnh/phản hồi của "
                    "khách thật đã nhận hàng, dựa đúng nội dung mẫu: «"
                    + lam_sach(" ".join(_fb.get("tin") or []))[:300] + "» — KHÔNG bịa số khách, tên khách, kết quả cụ thể "
                    "không có trong mẫu. Viết đúng tiếng khách, KHÔNG chép nguyên mẫu nếu mẫu khác tiếng khách.") if _fb else ""
'''),
    ('''                      + f"✅ Áp luật NÍU KHÁCH ĐỦ 3 LẦN — đây là lượt níu thứ {_lan}. "
''',
     '''                      + (f"✅ ĐÃ NÍU ĐỦ {LUOT_NIU} LƯỢT mà khách vẫn từ chối → hanh_dong 'treo', ghi_chu 'khách từ chối "
                         f"{LUOT_NIU} lần — sale quyết'. " if _lan > LUOT_NIU else
                         f"✅ Áp luật NÍU KHÁCH ĐỦ {LUOT_NIU} LẦN — đây là lượt níu thứ {_lan}/{LUOT_NIU}. ⛔ CHƯA được "
                         "'im' hay 'treo' vì khách từ chối/cảm ơn chào — phải 'tra_loi' níu tiếp. ")
'''),
    ('''                         "Anh, giữ 😊 ❤️): \\"" + CAU_GIU_UU_DAI + "\\"") if _lan < 3 else
                         "Lượt 3 (CHỈ khi khách chê giá / thiếu tiền): được dùng cửa hạ giá của luật GIÁ (không dưới sàn) hoặc quà/gói nhỏ CÓ trong "
                         "kịch bản — nêu MỨC MỚI thấp hơn, không nhắc lại mức cũ; kết bằng một câu hỏi chốt nhẹ. "
                         "Khách vẫn từ chối sau lượt này thì lượt sau mới 'treo'."))
''',
     '''                         "Anh, giữ 😊 ❤️): \\"" + CAU_GIU_UU_DAI + "\\"") if _lan < 3 else
                         "Lượt 3 (CHỈ khi khách chê giá / thiếu tiền): được dùng cửa hạ giá của luật GIÁ (không dưới sàn) hoặc quà/gói nhỏ CÓ trong "
                         "kịch bản — nêu MỨC MỚI thấp hơn, không nhắc lại mức cũ; kết bằng một câu hỏi chốt nhẹ. "
                         "Khách vẫn từ chối thì còn lượt 4-5 níu tiếp." if _lan == 3 else
                         ("⛔ CẤM thả khách đi ('take your time', 'whenever you're ready', 'message me back'), KHÔNG lặp lại "
                          "lý lẽ/câu của các lượt trước, KHÔNG nhắc giá (mức giảm lượt 3 đã nói thì chỉ được nhắc lại đúng "
                          "mức đó, không giảm thêm). ✅ 2-3 câu, đúng tiếng khách. "
                          + ("Lượt 4: góc MỚI lấy từ các mẫu níu/kẹt tiền của page (vd /NÍU_KHÁCH, /No_MONEY: giao tận "
                             "nhà miễn phí, khuyến mãi chỉ hôm nay, đặt hôm nay giao đúng ngày khách muốn / ngày có tiền) "
                             if _lan == 4 else
                             "Lượt 5 (lượt CUỐI): hỏi thật lòng điều gì khiến khách còn chưa yên tâm, trấn an bằng một cam "
                             "kết page đã nói (kiểm hàng rồi mới trả tiền…), mời thử một lần ")
                          + "rồi KẾT BẰNG ĐÚNG câu giữ ưu đãi (dịch sát nghĩa, giữ 😊 ❤️): \\"" + CAU_GIU_UU_DAI + "\\"")
                         if _lan <= LUOT_NIU else "")
                      + _dong_fb)
'''),
    # _soan_viec: nhắc giá + thả khách áp cho mọi lượt trừ 3
    ('''                           + CAU_GIU_UU_DAI + "\\"" if _tc_ and not hen_giao_theo_luong(msgs) and _tc_[1] < 3 else''',
     '''                           + CAU_GIU_UU_DAI + "\\"" if _tc_ and not hen_giao_theo_luong(msgs) and _tc_[1] != 3 and _tc_[1] <= LUOT_NIU else'''),
    ('''                        and _tc_[1] < 3 and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo")
                        and _tin_tc_ and THA_KHACH.search(_tin_tc_)):''',
     '''                        and _tc_[1] <= LUOT_NIU and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo")
                        and _tin_tc_ and THA_KHACH.search(_tin_tc_)):'''),
    # _soan_viec: luật cứng — chưa đủ lượt mà model im/treo vì từ chối → soạn lại; lượt 2 ép ảnh feedback
    ('''                # CÂU CẢN KHÁCH MUA (chủ shop 14/09 tối, ca Lucy JJ: "Hindi po basta bili lang…" = "đừng vội mua").
''',
     '''                # CHƯA ĐỦ 5 LƯỢT NÍU MÀ MODEL IM / TREO (chủ shop 14/09 tối, ca Lucy JJ: khách "Maraming Salamat… God bless"
                # sau 2 lời từ chối, model phán "khách từ chối 3 lần, cảm ơn chào tạm biệt" rồi treo). Treo vì lý do KHÁC
                # (khiếu nại, dưới giá sàn, đơn cũ, nước khác, quá hạn…) thì để nguyên.
                _ld_niu_ = f"{(qd or {}).get('ly_do') or ''} {(qd or {}).get('ghi_chu') or ''}"
                if (not err_m and qd and _tc_ and _tc_[1] <= LUOT_NIU and not hen_giao_theo_luong(msgs)
                        and qd.get("hanh_dong") in ("im", "treo")
                        and not re.search(r"khiếu|giá sàn|sỉ|buôn|đơn cũ|nước khác|quá hạn|hoàn tiền|voice|ảnh|thẻ|tiền mặt"
                                          r"|complain|refund|wholesale", _ld_niu_, re.I)):
                    print(f"{nhan} 🪝 khách từ chối lượt {_tc_[1]}/{LUOT_NIU} mà model {qd.get('hanh_dong')} — bắt soạn lại để níu")
                    dem["niu_tiep"] = dem.get("niu_tiep", 0) + 1
                    qd2, e2 = soan_bang_model(
                        noi_dung + f"\\n\\nSAI: khách mới từ chối / cảm ơn chào ở lượt {_tc_[1]}/{LUOT_NIU} — chủ shop muốn níu đủ "
                        f"{LUOT_NIU} lượt, CHƯA được im hay treo. hanh_dong 'tra_loi', viết tin níu đúng tình huống lượt "
                        f"{_tc_[1]} ở trên, đúng tiếng khách, KHÔNG nhắc lại giá cũ, kết bằng câu giữ ưu đãi.", on_dinh)
                    if not e2 and qd2 and qd2.get("hanh_dong") in ("tra_loi", "tra_loi_treo") and (qd2.get("tin_nhan") or "").strip():
                        qd = qd2
                _fb_ = feedback_luot_niu(msgs, kb_page, pid) if (not err_m and qd and _tc_) else None
                if _fb_ and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo") and (qd.get("tin_nhan") or "").strip() \\
                        and not (qd.get("anh_mau") or "").strip():
                    qd = dict(qd, anh_mau=_fb_["tu_khoa"].strip())
                    print(f"{nhan} 🖼  lượt níu 2 — kèm ảnh feedback /{qd['anh_mau']}")
                # CÂU CẢN KHÁCH MUA (chủ shop 14/09 tối, ca Lucy JJ: "Hindi po basta bili lang…" = "đừng vội mua").
'''),
]

LM = [
    ('''- NÍU KHÁCH ĐỦ 3 LẦN (chủ shop chốt 2026-09-14): với MỌI lời từ chối/trì hoãn (đắt, hỏi chồng, chưa có
  tiền, để sau, đợi lương…) bạn thuyết phục đủ 3 lượt, mỗi lượt một góc khác, lượt 3 dùng cửa hạ giá
  ở trên. Chỉ khi khách từ chối cả 3 lượt mới treo.''',
     '''- NÍU KHÁCH ĐỦ 5 LẦN (chủ shop chốt 2026-09-14, nâng 3 → 5 tối 14/09): với MỌI lời từ chối/trì hoãn (đắt, hỏi
  chồng, chưa có tiền, để sau, đợi lương…) bạn thuyết phục đủ 5 lượt, mỗi lượt một góc khác: lượt 1 đáp + giữ ưu
  đãi, lượt 2 gửi FEEDBACK khách thật (ảnh mẫu Feedback của page — hệ thống ghi rõ mẫu nào), lượt 3 dùng cửa hạ giá
  ở trên, lượt 4-5 góc mới (giao miễn phí, khuyến mãi hôm nay, hỏi điều khách còn lo). Chỉ khi khách từ chối cả 5
  lượt mới treo. Khách đã từ chối rồi nhắn "Salamat, have a great day, God bless" cũng là từ chối — níu tiếp,
  KHÔNG im.'''),
    ('''  ✅ NÍU ĐỦ 3 LẦN (chủ shop nhắc lại 14/09: *"níu khách đến lần thứ 3 để khách mua hàng"*):''',
     '''  ✅ NÍU ĐỦ 5 LẦN (chủ shop 14/09: *"níu khách đến lần thứ 3"*, nâng lên 5 tối 14/09 — lượt 4-5 góc mới, xem luật GIÁ):'''),
    ('''     · CHỈ SAU lần 3 khách vẫn không → hành động "treo"''',
     '''     · Lần 4-5: góc mới (giao miễn phí, giữ giá hôm nay, hỏi điều khách còn lo) — vẫn xin ngày + thông tin.
     · CHỈ SAU lần 5 khách vẫn không → hành động "treo"'''),
    ('''  ✅ Níu đủ 3 lượt như luật ĐỢI LƯƠNG. CHỈ sau lượt 3 khách''',
     '''  ✅ Níu đủ 5 lượt như luật ĐỢI LƯƠNG. CHỈ sau lượt 5 khách'''),
    ('''IM (hành động "im") khi: Botcake đã trả lời TRÚNG câu khách hỏi rồi (đừng nhắn đè), hoặc khách
chỉ chào hỏi/cảm ơn/gửi emoji, không có gì để trả lời.''',
     '''IM (hành động "im") khi: Botcake đã trả lời TRÚNG câu khách hỏi rồi (đừng nhắn đè), hoặc khách
chỉ chào hỏi/cảm ơn/gửi emoji, không có gì để trả lời. NGOẠI LỆ: khách cảm ơn / chào tạm biệt NGAY SAU lời từ chối
(hệ thống ghi "KHÁCH ĐANG TỪ CHỐI") là từ chối mềm — còn lượt níu thì phải níu, không im.'''),
]

ra = [va("chan_gui.py", CG), va("ai_sale.py", AI), va("luat_model.md", LM)]
for p, s in ra:
    open(p, "w", encoding="utf-8").write(s)
    print("✔ đã vá", p)

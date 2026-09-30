"""Vá 'khách vừa chọn gói → xin thông tin, không chào hàng lại' (ca Gha Cabilin Plaza 14/09).
Chạy trong thư mục pancake-tool. Mỗi chỗ thay phải khớp ĐÚNG 1 lần, không thì thoát không ghi."""
import sys

DAU = "KHACH_VUA_CHON_GOI"


def doc(f):
    return open(f, encoding="utf-8").read()


viec = {}  # file -> nội dung mới


def thay(f, cu, moi):
    s = viec.get(f) or doc(f)
    n = s.count(cu)
    if n != 1:
        sys.exit(f"✖ {f}: chuỗi neo khớp {n} lần (cần 1) — KHÔNG ghi gì: {cu[:70]!r}")
    viec[f] = s.replace(cu, moi)


for f in ("ai_sale.py", "ho_so.py", "chan_gui.py", "luat_model.md"):
    if DAU in doc(f) or "ca Gha Cabilin" in doc(f):
        sys.exit(f"✖ {f} đã có vá này rồi — bỏ qua")

# ── 1. ho_so.py: nhận "1 items", "only 1", "1+1", "b1g1" là khách đã chọn số lượng ──────────────
thay("ho_so.py",
     'R_SL_RO = re.compile(r"\\b\\d+\\s*(?:pc|pcs|piece|pieces|set|sets|box|boxes|bottle|bottles"\n',
     'R_SL_RO = re.compile(r"\\b\\d+\\s*(?:pc|pcs|piece|pieces|item|items|unit|units|tube|tubes"\n'
     '                     r"|set|sets|box|boxes|bottle|bottles"\n')
thay("ho_so.py",
     'R_SL_NGAN = re.compile(r"\\b(one|two|three|both)\\b", re.I)\n',
     'R_SL_NGAN = re.compile(r"\\b(one|two|three|both)\\b", re.I)\n'
     '# KHACH_VUA_CHON_GOI (chủ shop 14/09, ca Gha Cabilin Plaza): "Only 1 items to try" không bị bắt nên\n'
     '# AI tưởng khách chưa chọn gói → chào hàng lại. Thêm "only/just 1", "1 only", "1+1", "b1g1".\n'
     '# "only one" chỉ tính khi câu ngắn (≤ 8 từ) và không phải câu hỏi — "I have only one question?" loại.\n'
     '# Sau "only/just 1" phải là HẾT CÂU hoặc chữ chỉ món/thử — "only one question", "only 1 week" không tính.\n'
     'R_SL_CHI = re.compile(r"\\b(?:only|just)\\s*(?:1|one)\\s*(?:$|po\\b|pls\\b|please\\b|to\\s+try|first|for\\s+now"\n'
     '                      r"|item|pc|piece|set|box|bottle|tube|pack)|^\\s*(?:1|one)\\s*only\\b|\\b[1-4]\\s*\\+\\s*[1-4]\\b"\n'
     '                      r"|\\bb[1-4]\\s*[gt][1-4]\\b", re.I)\n')
thay("ho_so.py",
     '            elif (R_SL_RO.search(t) or R_SL_LUON.search(t)\n'
     '                  or (R_SL_NGAN.search(t) and len(t.split()) <= 8)):\n',
     '            elif (R_SL_RO.search(t) or R_SL_LUON.search(t)\n'
     '                  or ((R_SL_NGAN.search(t) or R_SL_CHI.search(t))\n'
     '                      and len(t.split()) <= 8 and not la_cau_hoi(t))):\n')

# ── 2. ai_sale.py: bộ dò + luật cứng soạn lại + thay chữ "SĐT" lọt ra ────────────────────────────
thay("ai_sale.py",
     '    return lam_sach(kh[-1]["text"])[:120], min(lan, 3), gia_page_da_bao(msgs)\n',
     '    return lam_sach(kh[-1]["text"])[:120], min(lan, 3), gia_page_da_bao(msgs)\n'
     '\n\n'
     '# KHACH_VUA_CHON_GOI — chủ shop 2026-09-14, ca Gha Cabilin Plaza (Kreain Nature PH - Ksa): page hỏi\n'
     '# "buy 1 get 1 hay buy 2 get 2?", khách "Only 1 items to try / If good and true i order more", AI đáp\n'
     '# 430 ký tự chào lại B1G1 + giảng COD + "thử trước rồi mua thêm", câu cuối mới xin SĐT (còn lọt chữ\n'
     '# "SĐT"). *"khách đã chốt số lượng 1, thì bạn rep xin thông tin để gửi hàng, chứ rep cái gì vậy"*.\n'
     '# Gốc: HS.trich không nhận "1 items" nên hồ sơ ghi "còn thiếu số lượng". Luật cứng ở vòng soạn:\n'
     '# khách vừa chọn gói mà tin AI dài / không xin thông tin giao hàng → bắt soạn lại đúng một lần.\n'
     'XIN_THONG_TIN = re.compile(\n'
     '    r"contact|phone|mobile|whatsapp|\\bnumber\\b|\\bno\\.|address|location|\\bname\\b|tirahan|numero"\n'
     '    r"|رقم|عنوان|اسم|موقع|電話|地址|姓名", re.I | re.U)\n'
     'TIN_CHOT_GOI_TOI_DA = 300\n'
     '\n\n'
     'def khach_vua_chon_goi(msgs, gia=None):\n'
     '    """Lời khách vừa chọn gói/số lượng (các tin khách SAU tin cuối phía shop), không thì None.\n'
     '\n'
     '    Câu hỏi ("1 item how much?") và lời từ chối không tính — đó là việc của cửa khác.\n'
     '    """\n'
     '    sau = []\n'
     '    for m in reversed(msgs or []):\n'
     '        if m.get("boi") == "khach":\n'
     '            if lam_sach(m.get("text")).strip():\n'
     '                sau.append(lam_sach(m["text"]))\n'
     '        elif m.get("boi") != "hethong":\n'
     '            break\n'
     '    sau.reverse()\n'
     '    if not sau or any(HS.la_cau_hoi(x) or khach_dang_tu_choi(x) for x in sau):\n'
     '        return None\n'
     '    co = HS.trich([{"boi": "khach", "text": x} for x in sau], None, gia)\n'
     '    return " / ".join(sau)[:160] if co.get("so_luong") else None\n')

thay("ai_sale.py",
     '                    if not e2 and qd2 and not (set(CG.tien_trong(qd2.get("tin_nhan") or "")) & _tc_[2]):\n'
     '                        qd = qd2\n',
     '                    if not e2 and qd2 and not (set(CG.tien_trong(qd2.get("tin_nhan") or "")) & _tc_[2]):\n'
     '                        qd = qd2\n'
     '                # KHÁCH VỪA CHỌN GÓI MÀ MODEL CHÀO HÀNG LẠI (chủ shop 14/09, KHACH_VUA_CHON_GOI) — chưa đủ\n'
     '                # SĐT + địa chỉ mà tin dài hoặc không xin thông tin giao hàng → bắt soạn lại 1 lần.\n'
     '                # Chép nguyên mẫu của shop ("Please provide the information below…") thì không đụng.\n'
     '                _goi_ = khach_vua_chon_goi(msgs, gia) if quyet == "tra_loi" and not _tc_ else None\n'
     '                _tin_ = ((qd or {}).get("tin_nhan") or "").strip()\n'
     '                if (not err_m and qd and _goi_ and _tin_\n'
     '                        and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo")\n'
     '                        and not (ho_so_khach.get("sdt") and ho_so_khach.get("dia_chi"))\n'
     '                        and not CG._la_mau_cua_shop(_tin_, kb_page)\n'
     '                        and (len(_tin_) > TIN_CHOT_GOI_TOI_DA or not XIN_THONG_TIN.search(_tin_))):\n'
     '                    print(f"{nhan} 📦 khách vừa chọn gói ({_goi_[:50]!r}) mà model chào hàng lại — bắt soạn lại")\n'
     '                    dem["chao_lai_goi"] = dem.get("chao_lai_goi", 0) + 1\n'
     '                    qd2, e2 = soan_bang_model(\n'
     '                        noi_dung + f"\\n\\nSAI: khách VỪA CHỌN gói/số lượng (khách nói: \\"{_goi_}\\"). Viết lại "\n'
     '                        "tin_nhan tối đa 2 câu, đúng tiếng khách: (1) MỘT câu xác nhận gói khách chọn kèm số "\n'
     '                        "lượng nhận được + giá đúng bảng — khách nói 1 món mà page chỉ bán từ gói BUY 1 GET 1 thì "\n'
     '                        "là gói BUY 1 GET 1; (2) xin phần CÒN THIẾU để giao hàng (tên, số điện thoại, địa chỉ "\n'
     '                        "đầy đủ). KHÔNG chào lại khuyến mãi, KHÔNG giảng COD/free delivery, KHÔNG khen sản "\n'
     '                        "phẩm, KHÔNG khuyên thử trước rồi mua thêm.", on_dinh)\n'
     '                    _t2_ = ((qd2 or {}).get("tin_nhan") or "").strip()\n'
     '                    if not e2 and _t2_ and XIN_THONG_TIN.search(_t2_) and len(_t2_) < len(_tin_):\n'
     '                        qd = qd2\n'
     '                    else:\n'
     '                        print(f"{nhan} 📦 soạn lại vẫn chưa gọn — vẫn gửi bản đầu")\n')

thay("ai_sale.py",
     '    tin = dien_cho_trong(tin, ten_khach, nhan=nhan)\n',
     '    tin = dien_cho_trong(tin, ten_khach, nhan=nhan)\n'
     '    # Chữ "SĐT" của luật tiếng Việt lọt vào câu gửi khách (ca Gha Cabilin Plaza 14/09: "Ano pong SĐT at\n'
     '    # complete address") — nhãn nội bộ, thay thẳng bằng tiếng Anh thay vì để cổng chặn cả tin.\n'
     '    if tin:\n'
     '        tin = re.sub(r"\\bSĐT\\b", "contact number", tin, flags=re.I)\n')

# ── 3. chan_gui.py: "SĐT" tính là lọt tiếng Việt ────────────────────────────────────────────────
thay("chan_gui.py",
     '    r"|vòng\\s*tay|dây\\s*chuyền|răng\\s*giả)\\b", re.I | re.U)\n',
     '    r"|vòng\\s*tay|dây\\s*chuyền|răng\\s*giả|sđt)\\b", re.I | re.U)\n')
thay("chan_gui.py",
     '     {}, "chan", "lot_tieng_viet"),\n'
     '    ("tiếng Tây Ban Nha KHÔNG bị chặn oan",\n',
     '     {}, "chan", "lot_tieng_viet"),\n'
     '    ("lọt chữ SĐT (ca Gha Cabilin Plaza 14/09)",\n'
     '     "Ano pong SĐT at complete address niyo sa Jeddah?",\n'
     '     {}, "chan", "lot_tieng_viet"),\n'
     '    ("tiếng Tây Ban Nha KHÔNG bị chặn oan",\n')

# ── 4. luat_model.md ─────────────────────────────────────────────────────────────────────────────
thay("luat_model.md",
     'Mỗi lần báo tiền, nói kèm SỐ LƯỢNG khách nhận được, để khách tự đối chiếu được với bảng giá.\n',
     'Mỗi lần báo tiền, nói kèm SỐ LƯỢNG khách nhận được, để khách tự đối chiếu được với bảng giá.\n'
     '\n'
     'KHÁCH ĐÃ CHỌN GÓI → XIN THÔNG TIN GIAO HÀNG NGAY (chủ shop chốt 2026-09-14, ca Gha Cabilin Plaza):\n'
     'Page vừa hỏi chọn gói mà khách đáp một mức ("Only 1 items to try", "1 only", "just one", "buy 1 get 1",\n'
     '"1+1", "2 pcs", "the cheaper one") là khách ĐÃ CHỌN. Tin trả lời CHỈ gồm hai phần, tối đa 2 câu:\n'
     '  1) MỘT câu xác nhận gói khách chọn, kèm số lượng nhận được + giá đúng bảng;\n'
     '  2) xin ĐÚNG phần còn thiếu để giao hàng (tên, số điện thoại, địa chỉ đầy đủ).\n'
     'TUYỆT ĐỐI KHÔNG: chào lại khuyến mãi, giảng lại COD / free delivery, khen sản phẩm, khuyên "thử trước rồi\n'
     'mua thêm". Khách nói 1 món mà page chỉ bán từ gói nhỏ nhất BUY 1 GET 1 -> hiểu là gói BUY 1 GET 1, KHÔNG\n'
     'bịa giá lẻ 1 món. "If good I will order more" là khách hứa mua thêm, KHÔNG phải lời từ chối.\n'
     'Ví dụ đúng: "Noted Gha 😊 Buy 1 Get 1 Free — 2 items for 109 SAR. Please send your full name, contact\n'
     'number and complete address so I can book your order."\n'
     'Viết cho khách thì luôn nói "contact number"/"phone number" — chữ "SĐT" là tiếng Việt nội bộ.\n')

for f, s in viec.items():
    open(f, "w", encoding="utf-8").write(s)
    print("✔ đã vá", f)

"""Vá 19/09 (đơn #75351 Lyn Omar Tahil · Hitana Store in Saudi): CÂU HỎI của khách không bao giờ được
vào ô địa chỉ đơn; địa chỉ thật khách gõ (không tên tỉnh) thì GHI vào ô địa chỉ thay vì chỉ note.
Chạy: python3 va_dc_cau_hoi.py            → chỉ kiểm từng chỗ khớp đúng 1 lần, không ghi
      python3 va_dc_cau_hoi.py --that     → .bak rồi ghi
"""
import sys, shutil, time

THAT = "--that" in sys.argv
DAU = "_dc_la_cau_hoi"          # dấu vết: có rồi thì từ chối vá lại

VA = {"auto_len_don.py": [], "ai_sale.py": []}

# ── P1: hàm _dc_la_cau_hoi ngay sau dia_chi_du_giao ─────────────────────────────────────────
VA["auto_len_don.py"].append((
'''    if not re.search(r"\\d", loi) and not TU_DIA_CHI_GIAO.search(loi):
        return "thiếu đường/số nhà/toà nhà"
    return ""
''',
'''    if not re.search(r"\\d", loi) and not TU_DIA_CHI_GIAO.search(loi):
        return "thiếu đường/số nhà/toà nhà"
    return ""


def _dc_la_cau_hoi(dc):
    """Tin khách có tên tỉnh mà là CÂU HỎI / câu nói / tin mẫu shop → KHÔNG phải ứng viên địa chỉ.

    19/09 (đơn #75351, Lyn Omar Tahil · Hitana Store in Saudi): khách hỏi "How many day in Riyadh" →
    extract() chọn làm địa chỉ → ghi THẲNG vào ô địa chỉ đơn. Cửa xác nhận (dia_chi_du_giao) chặn được,
    nhưng ô địa chỉ vẫn mang câu hỏi, còn địa chỉ thật khách gửi sau (không có tên tỉnh) chỉ nằm trong
    note. Chủ shop: *"sao lại thêm chữ how many day vào địa chỉ, nó có phải địa chỉ đâu"*.
    Câu hỏi mà có SỐ + từ khoá địa chỉ ("ito ang address Dubai merdep st 13 b villa 1 A ?") vẫn là địa chỉ.
    Đo tin khách thật 6 nước (so_chi_phi.jsonl): bỏ 79 Saudi / 30 UAE / 4 Oman ứng viên — đều là câu hỏi."""
    import ho_so as HS
    c = str(dc or "")
    if dia_chi_rac(c):
        return True
    c2 = re.sub(r"\\bd2\\b", "dito", c, flags=re.I)
    if not (HS.la_cau_hoi_dia_chi(c2) or R_KHONG_PHAI_3_CAP.search(c2)):
        return False
    return not (re.search(r"\\d", c) and HS.TU_DIA_CHI.search(c))
'''))

# ── P2: extract() bỏ ứng viên là câu hỏi ─────────────────────────────────────────────────────
VA["auto_len_don.py"].append((
'''    ung = [i for i in range(len(khach_msgs) - 1, max(-1, len(khach_msgs) - 7), -1)
           if P.detect_emirate(khach_msgs[i]["noi_dung"])]
''',
'''    ung = [i for i in range(len(khach_msgs) - 1, max(-1, len(khach_msgs) - 7), -1)
           if P.detect_emirate(khach_msgs[i]["noi_dung"])]
    # Câu HỎI có tên tỉnh không bao giờ vào ô địa chỉ (19/09, #75351 "How many day in Riyadh") — xem _dc_la_cau_hoi
    cau_hoi_dc = [i for i in ung
                  if _dc_la_cau_hoi(PHONE_RE.sub("", chon_dia_chi(khach_msgs[i]["noi_dung"])).strip(" ,.-"))]
    ung = [i for i in ung if i not in cau_hoi_dc]
'''))

# ── P3: địa chỉ AI Sale đọc từ lời khách (không tên tỉnh) → ghi vào ô; thiếu thì nói rõ khách mới HỎI ───
VA["auto_len_don.py"].append((
'''    if not diachi:
        thieu.append("địa chỉ (phải có tên tỉnh/bang)")
''',
'''    if not diachi and record.get("dia_chi_ai"):
        # AI Sale thấy khách đã gõ địa chỉ mà KHÔNG có tên tỉnh ("Wadi side building jamaa park Khalid bin udday,
        # al jaradiya" — #75351, 19/09): bộ trích ở trên chỉ nhặt tin có tên tỉnh nên ô địa chỉ bỏ trống, chữ
        # khách chỉ nằm trong note. Nay ghi vào ô địa chỉ; không có tên tỉnh thì THIẾU → không tự xác nhận.
        diachi = record["dia_chi_ai"]
        canh_bao.append("địa chỉ AI Sale đọc từ lời khách — sale kiểm lại")
        if not P.detect_emirate(diachi):
            thieu.append("tỉnh/thành (địa chỉ khách gõ không có tên tỉnh — sale chọn tỉnh trên đơn)")
    if not diachi:
        thieu.append("địa chỉ (phải có tên tỉnh/bang)" + (
            f" — khách mới HỎI, chưa cho địa chỉ: {khach_msgs[cau_hoi_dc[0]]['noi_dung'][:80]}"
            if cau_hoi_dc else ""))
'''))

# ── P4: nháp của tool đang mang câu hỏi trong ô địa chỉ → cho phép thay bằng địa chỉ thật ────────
VA["auto_len_don.py"].append((
'''        so_sai = len(re.sub(r"\\d+", "", dc_cu).split()) < 3
''',
'''        so_sai = len(re.sub(r"\\d+", "", dc_cu).split()) < 3 or _dc_la_cau_hoi(dc_cu)
'''))

# ── P5: hoàn thiện đơn: không có tỉnh trên đơn thì không tự xác nhận ────────────────────────────
VA["auto_len_don.py"].append((
'''            if _li_dc:
                du = False
            ghi = f"[Tự động] Khách nhắn thêm — đã bổ sung: {', '.join(them)}."
''',
'''            # Ô tỉnh của đơn trống (địa chỉ AI Sale ghi từ lời khách không có tên tỉnh — 19/09) thì
            # dia_chi_3_cap còn đoán tỉnh từ tên khu, có thể SAI tỉnh ("Khalid" → Yanbu) → không tự xác nhận.
            if not _li_dc and not ((body.get("shipping_address") or {}).get("province_id") or addr.get("province_id")):
                _li_dc = "đơn chưa có tỉnh/thành"
            if _li_dc:
                du = False
            ghi = f"[Tự động] Khách nhắn thêm — đã bổ sung: {', '.join(them)}."
'''))

# ── P6: ai_sale helper ─────────────────────────────────────────────────────────────────────
VA["ai_sale.py"].append((
'''def len_don_som(mkey, pid, ten_page, conv_id, msgs, token, ho_so_khach, that=False, nhan=""):
''',
'''# Tin mẫu xin thông tin của shop mà khách chép lại rồi điền — cả khối dài, chỉ để trong note.
R_MAU_SHOP_KHACH_DIEN = re.compile(
    r"please\\s+provide|to\\s+ensure|providing\\s+the\\s+following|information\\s+below", re.I)


def _dia_chi_ai_ghi_duoc(D, dc, mkey):
    """Địa chỉ hồ sơ (AI đọc từ lời khách) đủ ra dáng để GHI vào ô địa chỉ đơn? Trả chuỗi sẽ ghi, "" nếu không.

    19/09 (#75351, Lyn Omar Tahil · Hitana Store in Saudi): khách gửi "Wadi side building jamaa park Khalid
    bin udday, al jaradiya" (không có chữ Riyadh) → bộ trích daemon không nhặt, ô địa chỉ mang câu hỏi
    "How many day in Riyadh", địa chỉ thật chỉ nằm trong note. Chỉ nhận khi có số + từ khoá địa chỉ hoặc
    đủ 3 cấp; câu hỏi / "chưa có địa chỉ" / địa danh Philippines / tin mẫu shop thì vẫn chỉ ghi note.
    Đo hồ sơ 6 nước: ghi được ~50 địa chỉ thật (UAE 23, Kuwait 10…) trước đây chỉ nằm trong note."""
    s = re.sub(r"\\s*\\(model đọc ra từ lời khách\\)\\s*$", "", str(dc or "")).strip()
    if not s or R_MAU_SHOP_KHACH_DIEN.search(s) or D.dia_chi_rac(s):
        return ""
    if HS.la_cau_hoi_dia_chi(s) or HS.khong_phai_dia_chi(s, mkey):
        return ""
    ok, vi = HS.dia_chi_du_tin(s, mkey)
    if vi == "địa danh Philippines":
        return ""
    if not ((ok and vi in ("số + từ khoá địa chỉ", "có tên tỉnh", "đường/zip Mỹ")) or D.dia_chi_3_cap(s)[0]):
        return ""
    return D.PHONE_RE.sub("", D.chon_dia_chi(s)).strip(" ,.-")[:250]


def len_don_som(mkey, pid, ten_page, conv_id, msgs, token, ho_so_khach, that=False, nhan=""):
'''))

# ── P7: len_don_som truyền địa chỉ hồ sơ cho extract() ghi vào ô ─────────────────────────────
VA["ai_sale.py"].append((
'''    them = []
    if not ex.get("sdt") and hs.get("sdt"):
        them.append(f"SĐT khách gõ: {hs['sdt']} (không đúng khuôn {mkey.upper()} — hỏi lại khách)")
    if not ex.get("diachi") and hs.get("dia_chi"):
''',
'''    # Bộ trích không có địa chỉ (chỉ nhặt tin có tên tỉnh, bỏ câu hỏi) mà hồ sơ có địa chỉ khách gõ → GHI vào
    # ô địa chỉ đơn, không chỉ note (19/09, #75351). extract() để THIẾU tỉnh nếu chữ không có tên tỉnh.
    if not ex.get("diachi"):
        record["dia_chi_ai"] = _dia_chi_ai_ghi_duoc(D, hs.get("dia_chi"), mkey)
    them = []
    if not ex.get("sdt") and hs.get("sdt"):
        them.append(f"SĐT khách gõ: {hs['sdt']} (không đúng khuôn {mkey.upper()} — hỏi lại khách)")
    if not ex.get("diachi") and hs.get("dia_chi") and not record.get("dia_chi_ai"):
'''))

loi = 0
moi = {}
for f, ds in VA.items():
    s = open(f, encoding="utf-8").read()
    if f == "auto_len_don.py" and "def _dc_la_cau_hoi" in s or f == "ai_sale.py" and "def _dia_chi_ai_ghi_duoc" in s:
        print(f"✖ {f}: đã có bản vá — từ chối vá lại"); loi += 1; continue
    for k, (cu, mo) in enumerate(ds, 1):
        n = s.count(cu)
        print(f"  {f} chỗ {k}: khớp {n} lần")
        if n != 1:
            loi += 1; continue
        s = s.replace(cu, mo)
    moi[f] = s
if loi:
    sys.exit(f"✖ {loi} chỗ không khớp đúng 1 lần — KHÔNG ghi gì")
for f, s in moi.items():
    compile(s, f, "exec")
print("✔ mọi chỗ khớp đúng 1 lần, biên dịch được")
if THAT:
    moc = time.strftime("%Y%m%d-%H%M")
    for f, s in moi.items():
        shutil.copy2(f, f"{f}.bak-{moc}-truoc-dc-cau-hoi")
        open(f, "w", encoding="utf-8").write(s)
        print(f"✔ đã ghi {f} (bak {f}.bak-{moc}-truoc-dc-cau-hoi)")

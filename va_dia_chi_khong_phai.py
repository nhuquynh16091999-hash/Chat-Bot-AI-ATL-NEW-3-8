"""Vá 'chưa có địa chỉ / ở nước khác / tự lấy hàng' không phải địa chỉ (15/09/2026).

    python3 va_dia_chi_khong_phai.py <thư mục>          # chỉ kiểm: mọi chỗ khớp đúng 1 lần, không ghi
    python3 va_dia_chi_khong_phai.py <thư mục> --that   # ghi (tạo .bak trước)
"""
import os, sys, shutil, time

THU_MUC = sys.argv[1]
THAT = "--that" in sys.argv

HAM = r'''

# ── "CHƯA CÓ ĐỊA CHỈ / Ở NƯỚC KHÁC / TỰ LẤY HÀNG" KHÔNG PHẢI ĐỊA CHỈ (vá 15/09/2026) ──────────
# Ca Cucu Ella (Golden Youth Beauty KSA): model đọc "belum ada, tanya majikan besok" làm địa chỉ →
# len_don_som định tạo đơn nháp không SĐT. Cùng loại: "Nsa pinas ako now", "Nepal" (#49589),
# "Malayo po ako ma'am sa ibang bansa hindi ko na alam anu address dito", địa chỉ quê Philippines
# "Purok 3 ... Zamboanga del sur 7920" (#49563). `gop` không ghi đè nên câu rác lưu một lần là khoá
# luôn ô địa chỉ — khách cho địa chỉ thật sau cũng không vào hồ sơ. Chặn ở cả trich, loc_model,
# len_don_som. KHÔNG chặn khi có tên tỉnh/thành của thị trường (chủ shop: "Riyadh" trơn vẫn tạo
# nháp) hoặc có số + từ khoá địa chỉ (trừ khi có dấu hiệu địa chỉ Philippines: brgy/purok/pinas).
# Đo 15/09 trên 221 địa chỉ hồ sơ 8 nước: chặn 13, cả 13 là rác, 0 địa chỉ thật; trên 7427 tin
# khách (so_chi_phi + hieu_suat_luot): trich nhận 331 địa chỉ, chặn thêm 7, cả 7 là địa chỉ ở PH.
_DC_TU = r"(?:address|adress|addres|adres|addrs|alamat|almt|location|lokasyon|lokasi|pata|عنوان|العنوان)"
R_KHONG_PHAI_DC = (
    ("chua_co", re.compile(
        r"\b(?:belum|blm|blum)\s+(?:ada|tau|tahu|punya|dapat|dpt)\b"
        r"|\btanya\s+(?:ke\s+|sama\s+)?(?:majikan|bos|boss|madam|nyonya|sir|mama)\b"
        r"|\bask(?:ing)?\s+(?:to\s+)?(?:my\s+)?(?:madam|mam|maam|ma'am|employer|boss|sir|amo|sponsor|kafeel|kafil)\b"
        r"|\b(?:tanong|tanungin|tanongin|tatanong)\w*\s+(?:(?:sa|kay|ang|ko)\s+)*(?:amo|madam|mam|maam|boss|sir)\b"
        r"|\bpata\s+(?:nahi|nahin|nhi|ni)\b"
        rf"|\bno\s+(?:(?:complete|exact|full|proper|correct)\s+)?{_DC_TU}"
        r"|\b(?:dont|don'?t|do\s+not|didn'?t|not\s+sure|not\s+yet|walang|wala|hindi|di\s+ko|dko|diko|belum|blm"
        rf"|tidak|tdk|gak|nggak|ngga|nahi|nahin)\b(?:\s+[^\s\d]+){{0,5}}?\s+{_DC_TU}"
        rf"|{_DC_TU}\s+(?:[^\s\d]+\s+){{0,3}}?(?:later|tomorrow|mamaya|bukas|nanti|besok|not\s+yet|unknown)\b"
        r"|ما\s*(?:عندي|اعرف|أعرف)\s*(?:ال)?عنوان", re.I | re.U)),
    ("nuoc_khac", re.compile(
        r"\b(?:pinas|pilipinas|philippines?|phil+ipines?|philipines?|ibang\s+bansa|out\s+of\s+(?:the\s+)?country"
        r"|outside\s+(?:the\s+)?country|abroad|bakasyon|vacation"
        r"|nepal|india|pakistan|bangladesh|sri\s*lanka|indonesia|kenya|uganda|ethiopia|nigeria|ghana"
        r"|barangay|brgy|purok|sitio|manila|pasig|cebu|davao|zamboanga|baguio|rizal|romblon|cavite"
        r"|bulacan|pampanga|batangas|iloilo|negros|pangasinan|mindanao|luzon|visayas|quezon\s+city)\b", re.I)),
    ("tu_lay", re.compile(
        r"\b(?:pick\s*-?\s*up|pickup|pick\s+it\s+up|self\s*-?\s*pick\w*|collect\s+(?:it\s+)?(?:my\s*self|personally)"
        r"|ambil\s+sendiri|(?:saya|aku)\s+(?:yang\s+)?ambil"
        r"|come\s+to\s+(?:your|ur)\s+(?:shop|store|office)|where\s+(?:is\s+)?(?:your|ur)\s+(?:shop|store|office))\b",
        re.I)),
)
TEN_KHONG_PHAI_DC = {"chua_co": "khách chưa có/chưa biết địa chỉ", "nuoc_khac": "khách đang ở nước khác",
                     "tu_lay": "khách muốn tự đến lấy"}
R_DC_PHILIPPINES = re.compile(r"\b(?:philippines?|pilipinas|pinas|barangay|brgy|purok|sitio)\b", re.I)


def khong_phai_dia_chi(t, mkey):
    """Trả mã ('chua_co' / 'nuoc_khac' / 'tu_lay') nếu câu này KHÔNG phải địa chỉ, '' nếu vẫn tính."""
    t = re.sub(r"\s*\(model đọc ra từ lời khách\)\s*$", "", str(t or "")).strip()
    if not t or _co_ten_tinh(t, mkey):
        return ""
    if re.search(r"\d", t) and TU_DIA_CHI.search(t) and not R_DC_PHILIPPINES.search(t):
        return ""
    for ma, r in R_KHONG_PHAI_DC:
        if ma == "tu_lay" and mkey == "taiwan":      # Đài Loan có nhận hàng ở cửa hàng tiện lợi
            continue
        if r.search(t):
            return ma
    return ""
'''

VA = [
    ("ho_so.py", "hàm khong_phai_dia_chi",
     '''def la_cau_hoi(t):
    t = str(t or "")
    return "?" in t or "؟" in t or (bool(R_HOI.search(t)) and not R_DAY_SO.search(t))
''',
     '''def la_cau_hoi(t):
    t = str(t or "")
    return "?" in t or "؟" in t or (bool(R_HOI.search(t)) and not R_DAY_SO.search(t))
''' + HAM),
    ("ho_so.py", "trich bỏ câu không phải địa chỉ",
     "            if co_my or co_tinh or (_co_tu_dia_chi_manh(t) and not la_hoi) or (co_so and co_tu):\n",
     "            if (co_my or co_tinh or (_co_tu_dia_chi_manh(t) and not la_hoi) or (co_so and co_tu)) \\\n"
     "                    and not khong_phai_dia_chi(t, mkey):\n"),
    ("ho_so.py", "loc_model từ chối địa chỉ không phải địa chỉ",
     "        elif not _co_trong_loi_khach(gt, loi_khach):\n",
     "        elif k == \"dia_chi\" and khong_phai_dia_chi(gt, mkey):\n"
     "            bo[k] = f\"không phải địa chỉ — {TEN_KHONG_PHAI_DC[khong_phai_dia_chi(gt, mkey)]}\"\n"
     "            continue\n"
     "        elif not _co_trong_loi_khach(gt, loi_khach):\n"),
    ("ai_sale.py", "len_don_som bỏ địa chỉ hồ sơ không phải địa chỉ",
     '''    if _dia_chi_la_cau_hoi(hs.get("dia_chi")):
        hs["dia_chi"] = None
''',
     r'''    if _dia_chi_la_cau_hoi(hs.get("dia_chi")):
        hs["dia_chi"] = None
    # "Chưa có địa chỉ / đang ở nước khác / tự đến lấy" không phải địa chỉ (vá 15/09/2026, ca Cucu Ella
    # "belum ada, tanya majikan besok"). Chỉ xét hồ sơ: mọi nhánh địa chỉ của daemon đều đòi tên tỉnh,
    # mà có tên tỉnh thì HS.khong_phai_dia_chi luôn cho qua. Có SĐT thì đơn vẫn tạo, câu khách vào note.
    loi_dc = HS.khong_phai_dia_chi(hs.get("dia_chi"), mkey)
    if loi_dc:
        cau = re.sub(r"\s*\(model đọc ra từ lời khách\)\s*$", "", str(hs["dia_chi"]))[:120]
        loi_dc = f"khách nói về địa chỉ: {cau} ({HS.TEN_KHONG_PHAI_DC[loi_dc]} — chưa phải địa chỉ, sale hỏi lại)"
        hs["dia_chi"] = None
'''),
    ("ai_sale.py", "note đơn mang câu khách nói về địa chỉ",
     '''        them.append(f"địa chỉ khách gõ: {str(hs['dia_chi'])[:160]} (chưa nhận ra tỉnh/thành — sale soát)")
''',
     '''        them.append(f"địa chỉ khách gõ: {str(hs['dia_chi'])[:160]} (chưa nhận ra tỉnh/thành — sale soát)")
    if loi_dc and not ex.get("diachi"):
        them.append(loi_dc)
'''),
]

noi_dung = {}
for f, ten, cu, moi in VA:
    p = os.path.join(THU_MUC, f)
    s = noi_dung.setdefault(f, open(p, encoding="utf-8").read())
    n = s.count(cu)
    if "khong_phai_dia_chi" in s and ten == "hàm khong_phai_dia_chi":
        sys.exit(f"✖ {f}: đã có khong_phai_dia_chi — đã vá rồi, không ghi")
    if n != 1:
        sys.exit(f"✖ {f} [{ten}]: khớp {n} lần (phải đúng 1) — KHÔNG ghi file nào")
    noi_dung[f] = s.replace(cu, moi)
    print(f"✔ {f} [{ten}]: khớp 1")

if not THAT:
    for f, s in noi_dung.items():
        open(os.path.join(THU_MUC, f + ".thu"), "w", encoding="utf-8").write(s)
    print("CHẠY THỬ — đã ghi bản vá ra *.thu cạnh file gốc, file gốc không đổi")
    sys.exit(0)

moc = time.strftime("%Y%m%d-%H%M")
for f, s in noi_dung.items():
    p = os.path.join(THU_MUC, f)
    shutil.copy2(p, f"{p}.bak-{moc}-truoc-dia-chi-khong-phai")
    open(p, "w", encoding="utf-8").write(s)
    print(f"✔ đã ghi {p} (bak {p}.bak-{moc}-truoc-dia-chi-khong-phai)")

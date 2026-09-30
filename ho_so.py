#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HỒ SƠ KHÁCH — trí nhớ bền của AI Sale, thay cho việc quét lại toàn bộ hội thoại mỗi vòng.

Hai việc trong một file, vì chúng chỉ có nghĩa khi đi cùng nhau:

  ① LUẬT TRÍCH XUẤT ĐA THỊ TRƯỜNG  (`trich`)
     Đọc lời khách, rút ra 5 trường của mục 1. Bản cũ trong `ai_sale.da_biet_gi` chỉ chạy
     đúng cho MỸ: `R_SDT` chỉ có khoá "usa", địa chỉ bắt theo street/ave/ZIP kiểu Mỹ, phương
     thức thanh toán là Zelle/Venmo/CashApp. Mở UAE hay Kuwait thì khối "KHÁCH ĐÃ CHO RỒI"
     gần như rỗng → AI hỏi lại đúng cái khách vừa nói, tức lỗi chủ shop gọi là nặng nhất.
     Nay: SĐT lấy `sdt_regex` từ markets.json (có đủ 12 thị trường, sẵn từ đầu mà chưa ai
     dùng); địa chỉ nhận cả kiểu vùng Vịnh (Block/Area/Jadda + tiếng Ả Rập) và dò tên
     tỉnh/tiểu vương quốc bằng bảng POS; thanh toán khai theo thị trường.

  ② KHO HỒ SƠ SQLite  (`mo`, `doc`, `gop`, `ghi`)
     Một file `state/<tt>/ho_so.db`. Giữ những gì khách đã cho, kèm MỐC NƯỚC `tin_da_doc` —
     vòng sau chỉ đọc tin MỚI hơn mốc đó.

     Vì sao đáng làm — đo thật trên page Gold Charm Bracelet US, Kimi K2:
        khối ổn định (kịch bản + luật, ĐƯỢC ĐỆM) ~7.400 token → $0,00119/lượt
        hội thoại  5 tin  →  382 token  → chiếm 23% tiền một lượt
        hội thoại 40 tin  → 4.912 token → chiếm 80% tiền một lượt
     Tức thứ đắt KHÔNG phải kịch bản (đã đệm) mà là hội thoại gửi lại từ đầu mỗi lượt — và
     nó đắt nhất đúng ở hội thoại dài, tức hội thoại sắp ra đơn.

     Nhưng cái được lớn hơn tiền là ĐÚNG: API chat trả tối đa 60 hội thoại/lần và tool chưa
     lật trang, prompt chỉ mang 40 tin cuối. Khách cho địa chỉ ở tin thứ 60, hoặc cho từ hôm
     kia, là MẤT. Có hồ sơ thì nhớ xuyên cửa sổ 24h của Facebook, xuyên nhiều ngày, và xuyên
     cả sang hội thoại mới của cùng khách.

  python3 ho_so.py xem <thị trường> [<conv_id>]     # xem hồ sơ đang lưu
  python3 ho_so.py thu <thị trường>                 # chạy luật trích xuất trên ca mẫu
"""

import json
import os
import re
import sqlite3
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 5 trường của mục 1. `thanh_toan` chỉ bắt buộc ở thị trường thu tiền SAU khi nhận hàng.
TRUONG = ("ten", "sdt", "dia_chi", "so_luong", "thanh_toan")
R_DINH_VI = re.compile(r"https?://(?:maps\.app\.goo\.gl|goo\.gl/maps|(?:www\.)?google\.[a-z.]+/maps|maps\.google\.[a-z.]+)\S*", re.I)
TEN_TRUONG = {"ten": "Tên", "sdt": "SĐT", "dia_chi": "Địa chỉ",
              "so_luong": "Số lượng / combo", "thanh_toan": "Phương thức thanh toán"}
THU_TIEN_SAU = ("usa", "australia")          # mục 9b — hai thị trường này mới cần chốt 2

BUOC = ("moi", "tu_van", "cho_xac_minh_nha", "cho_thanh_toan",
        "du_dieu_kien", "da_len_don", "treo")


# ═════════════════════════════════════════════════════════════════════════════
# ① LUẬT TRÍCH XUẤT — THEO THỊ TRƯỜNG
# ═════════════════════════════════════════════════════════════════════════════

def _markets():
    try:
        return json.load(open(os.path.join(SCRIPT_DIR, "markets.json"), encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return {}


# ── Địa chỉ ──────────────────────────────────────────────────────────────────
# Vùng Vịnh không có "số nhà + tên đường" như Mỹ. Địa chỉ Kuwait/Bahrain điển hình là
# "Block 4, Street 12, Jadda 5, House 20, Salmiya" — nên bắt theo TỪ KHOÁ CẤP HÀNH CHÍNH
# chứ không theo khuôn số-nhà-tên-đường. Xem memory `luat-dia-chi-block-area-vinh`:
# nước ba ranh kiểu Bahrain dùng chung một trường cho Block và Area.
TU_DIA_CHI = re.compile(
    r"\b(block|blk|area|street|st|str|road|rd|avenue|ave|jadda|jaddah|building|bldg|villa"
    r"|flat|apt|apartment|house|floor|near|behind|opposite|landmark|compound|tower|zone"
    r"|district|sector|city|province|barangay|brgy|purok|subdivision|subd|zip|po\s*box)\b"
    r"|شارع|منطقة|قطعة|مجمع|قسيمة|بناية|شقة|فيلا|بلوك|جادة|بجانب|خلف|مقابل"
    r"|區|路|街|號|巷|弄|丁目|番地", re.I | re.U)
# Mỹ: số nhà + tên đường vẫn là dấu hiệu mạnh nhất, giữ lại.
# Chữ viết tắt đường phố trùng từ thường / lỗi gõ: "st" (gõ nhầm "at"), "rd", "ave", "str".
# Đứng MỘT MÌNH (không có số, không tên tỉnh) thì không tính là địa chỉ — ca Geraldine Rosales
# Dayoan 14/09/2026 (Madam Mystic Fengshui Expert USA): khách chọn phương án 4 của Botcake
# "Proteksyon laban sa malas ingit st bad energy poh" → nhận là địa chỉ → tạo đơn nháp #7379
# không SĐT không địa chỉ. Có số ("12 st", "Street 5") vẫn nhận như cũ.
TU_VIET_TAT_DUONG = {"st", "str", "rd", "ave"}


# Câu KỂ LỂ / PHỦ ĐỊNH / HẸN LÚC KHÁC có từ house/building/flat/area không phải địa chỉ (vá tiếp
# 14/09/2026): "i dont have house number..sorry", "not now or tomorrow im not here in my house",
# "No now iam change my building", "i keep in house coz I go outside ..will sent u later", và vùng
# cơ thể "Bikini area using". Đo trên 1752 tin khách UAE + 126 địa chỉ đã lưu: địa chỉ thật đi nhánh
# này ("Near lulu market al hazazna sharjha", "Yas island … Near yas mall", "Hameem Road Asab…",
# "Name villa dibaa") không có từ nào dưới đây. CHỈ áp cho nhánh không số — "No 12 street" có số
# nên vẫn là địa chỉ.
R_KE_LE_KHONG_PHAI_DC = re.compile(
    r"\b(not|no|dont|don'?t|didn'?t|do\s+not|haven'?t|cannot|can'?t|sorry|will|later|now|today"
    r"|tomorrow|coz|cause|because|hindi|wala|walang|mamaya|bukas|tidak|gak|nggak|belum|nanti)\b"
    r"|\b(bikini|underarm|under\s*arm|armpit|private|intimate|face|skin|body|neck|knee|elbow)\s+area\b",
    re.I)


def _co_tu_dia_chi_manh(t):
    if R_KE_LE_KHONG_PHAI_DC.search(t):
        return False
    return any(g.group(0).lower() not in TU_VIET_TAT_DUONG for g in TU_DIA_CHI.finditer(t))


R_DUONG_MY = re.compile(
    r"\d+\s+[A-Za-z].{3,40}?\b(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|blvd|ct"
    r"|court|way|pl|place|circle|cir|hwy|highway|apt|unit)\b", re.I)
R_ZIP_MY = re.compile(r"\b\d{5}(?:-\d{4})?\b")

# ── Câu HỎI có nhắc tên thành phố KHÔNG phải địa chỉ (vá 14/09/2026) ──────────
# Chạy thử Saudi 14/09 trước khi mở AI Sale toàn thị trường: "How many days for shipping jeddah",
# "DO YOU DELIVER HERE IN RIYADH SAUDI ARABIA", "Free dilivery riyadh area" đều bị nhận là địa chỉ
# → lên đơn sớm tạo đơn nháp rác. UAE dính y hệt ("Can deliver to Al Ain", "magkano po dito sa
# Dubai po"). Khách hiếm khi gõ dấu "?", nên nhận câu hỏi theo TỪ HỎI đầu câu / cụm hỏi (Anh,
# Tagalog, Indonesia, Hindi, Ả Rập). Đo trên 117 địa chỉ đã lưu ở ho_so UAE: chặn 16, cả 16 là
# câu hỏi; không câu nào có SĐT/số nhà bị chặn. Câu có dãy số dài (SĐT) thì không coi là hỏi.
R_HOI = re.compile(
    r"^\s*(?:how|hm|hmm|hw|what|when|where|which|why|do|does|did|can|could|is|are|will|would"
    r"|may\s+i|any|available|pick\s*up|free\s+d[ei]l[ie]v\w*|magkano|ilang|pwede|berapa|bisa)\b"
    r"|\b(?:do|does|can|could|will)\s+(?:you|u|ya|we)\b"
    r"|\bhow\s+(?:much|many|long|about)\b|\bh(?:m|w)\s+much\b"
    r"|\b(?:magkano|mag\s*kano|mgkno|magkno|ilang\s+araw|pwede\s+ba|meron|mayroon\s+(?:po\s+)?ba"
    r"|berapa|bisa\s+(?:kirim|pesen|antar)|pengiriman|harga|hrga|gimana|gimna|caranya|kitna|kitne)\b"
    r"|(?:^|\s)(?:هل|كم|متى|كيف|وين|فين|ايش|وش)(?:\s|$)", re.I | re.U)
R_DAY_SO = re.compile(r"\d[\d\s\-]{6,}\d")


def la_cau_hoi(t):
    t = str(t or "")
    return "?" in t or "؟" in t or (bool(R_HOI.search(t)) and not R_DAY_SO.search(t))


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

# ── CHỮ KHÁCH GÕ CHƯA CHẮC LÀ ĐỊA CHỈ (vá 17/09/2026) ────────────────────────────────────────
# Chủ shop 17/09: *"tại sao khách chưa cho sdt và chưa cho địa chỉ mà đã tạo đơn hàng rồi"*.
# Đo 10-17/09: 64 đơn được mở ra mà ô SĐT lẫn ô địa chỉ đều trống (16/09: 27/229 đơn = 12%).
# Nguồn: `trich` nhận địa chỉ khi câu có MỘT từ trong TU_DIA_CHI — không cần số nhà, không cần
# tên tỉnh — còn model thì viết thẳng vào ô địa chỉ. Kết quả đọc nhầm (đơn thật):
#   "Block color" (#74634, page BellaColor Hair — khách hỏi MÀU tóc, dính chữ "block")
#   "Magknu po block color" (#74546 — câu hỏi giá, gõ sai "magkano" nên không nhận ra là hỏi)
#   "Ok maam i cht u if come in my house" (#74604) · "May buss come my house I sent number" (#74788)
#   "Koronadal city" (#14524) · "Cotavato city" (#74698) · "Bohol" (#74514) — quê Philippines
#   "saudi" (#74785) · "Al shifa denture addras" (#74608) · "Am jeddah where are you located" (#74818)
# `dia_chi_du_tin` KHÔNG đổi luật chủ shop ("có SĐT HOẶC địa chỉ là tạo nháp ngay", 11/09) — nó chỉ
# trả lời câu "thế nào mới TÍNH là địa chỉ": phải có tên tỉnh POS, hoặc số + từ khoá địa chỉ, hoặc
# từ khoá VÙNG đứng riêng (area/district/near/tower...). Tên tỉnh trơn ("Riyadh") vẫn mở đơn.
# ĐO HAI CHIỀU trên 315 địa chỉ đang lưu ở 8 nước: chặn 69, trong đó 34 ca khách CÓ SĐT nên đơn
# vẫn tạo như cũ → chỉ 35 ca đổi kết cục, 29 ca là rác/câu hỏi thật. 6 ca chặn oan đều là TÊN
# ĐỊA DANH TRƠN mà bảng tỉnh POS không biết hoặc khách gõ sai ("Sarjah", "I'm jaddah",
# "Hafar Albatin", "Samakkah", "AL RAFIAH", "hautat sudair") — cả 6 đều KHÔNG có SĐT nên đơn mở
# ra cũng rỗng; khách cho SĐT hoặc gõ thêm số nhà là đơn lên ngay lượt sau.
R_HOI_GIUA = re.compile(
    r"\b(?:where|what|when|which|how)\s+(?:are|is|am|do|does|did|can|could|will|would|much|many|long|about)\b"
    r"|\bare\s+(?:you|u|ya)\b|\bcan\s+(?:i|we|you|u)\b|\b(?:you|u)\s+deliver\b"
    r"|\bwhere\s+(?:r|ur)\b|\blocated\b", re.I)
# Tỉnh/thành Philippines hay bị khách gõ ra khi đang ở vùng Vịnh (quê, nơi gửi tiền về).
# Chỉ thêm tên KHÔNG trùng địa danh thị trường mình bán.
R_PH_TINH = re.compile(
    r"\b(?:bohol|koronadal|cotabato|kidapawan|tacloban|butuan|surigao|dumaguete|bacolod"
    r"|general\s*santos|gensan|sultan\s*kudarat|maguindanao|misamis|agusan|sarangani"
    r"|catanduanes|marinduque|sorsogon|camarines|ilocos|tarlac|benguet|ozamiz|pagadian"
    r"|iligan|malaybalay|tagum|panabo|digos|leyte|bicol)\b", re.I)
# Từ khoá VÙNG đứng riêng (không cần số) cũng đủ mở đơn: "Qurum Area", "Near lulu market al
# hazazna sharjha", "Lana tower, sport city" đều là địa chỉ thật chưa đủ. CỐ Ý BỎ "city"/"province":
# "Koronadal city", "Saudi were city" là rác. "block/street/villa/house/flat" thì PHẢI có số.
R_VUNG_RIENG = re.compile(
    r"\b(?:area|district|near|opposite|behind|landmark|compound|tower|zone|subdivision|subd"
    r"|sector|barangay|brgy)\b|منطقة|مجمع|بجانب|خلف|مقابل", re.I | re.U)
# "near my salary", "near me" — near + đại từ không phải mốc địa chỉ (ca Mhely Alames #14519).
R_VUNG_GIA = re.compile(r"\b(?:near|opposite|behind)\s+(?:my|me|our|your|ur|salary)\b", re.I)


def la_cau_hoi_dia_chi(t):
    """Như `la_cau_hoi` nhưng bắt thêm cụm hỏi NẰM GIỮA câu — khách hiếm khi gõ dấu '?'.

    Ca Manyara Loise (#74818, 17/09): "Am jeddah where are you located" → R_HOI neo đầu câu nên
    trượt, chuỗi có "jeddah" nên thành địa chỉ → mở đơn rỗng. Chỉ dùng cho ô ĐỊA CHỈ.
    """
    t = str(t or "")
    return la_cau_hoi(t) or (bool(R_HOI_GIUA.search(t)) and not R_DAY_SO.search(t))


def dia_chi_du_tin(t, mkey):
    """Chuỗi này đủ tin để MỞ một đơn nháp chưa? Trả (True/False, lý do) — lý do để ghi note."""
    t = re.sub(r"\s*\(model đọc ra từ lời khách\)\s*$", "", str(t or "")).strip()
    if not t:
        return False, "trống"
    if la_cau_hoi_dia_chi(t):
        return False, "là câu hỏi"
    if (R_PH_TINH.search(t) or R_DC_PHILIPPINES.search(t)) and not _co_ten_tinh(t, mkey):
        return False, "địa danh Philippines"
    if mkey == "usa" and (R_DUONG_MY.search(t) or (R_ZIP_MY.search(t) and len(t) > 40)):
        return True, "đường/zip Mỹ"
    if _co_ten_tinh(t, mkey):
        return True, "có tên tỉnh"
    if re.search(r"\d", t) and TU_DIA_CHI.search(t):
        return True, "số + từ khoá địa chỉ"
    if R_VUNG_RIENG.search(t) and not R_VUNG_GIA.search(t) and not R_KE_LE_KHONG_PHAI_DC.search(t):
        return True, "từ khoá vùng"
    return False, "không tên tỉnh, không số nhà"


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

# ── SĐT: SỐ NƯỚC NGOÀI VẪN NHẬN ─────────────────────────────────────────────
# Chủ shop chốt 2026-09-08: khách đang ở UAE mà cho số Saudi thì VẪN LÊN ĐƠN — chỉ phải hỏi
# lại "bạn có dùng WhatsApp số này không?", vì bưu tá liên hệ qua WhatsApp khi số không phải
# nội địa. Nên bắt SĐT theo khuôn bản địa RỒI DỪNG là sai: hồ sơ sẽ trống trong khi khách đã
# cho số, và AI đi hỏi lại số — đúng lỗi mục 1 cấm.
# NGOẠI LỆ: Kuwait và Bahrain BẮT BUỘC số bản địa (markets.json → sdt_bat_buoc_ban_dia),
# số ngoại ở hai nước đó không giao được nên không tính là đã có SĐT.
R_SDT_CHUNG = re.compile(r"(?<!\d)(\+?\d[\d\s.\-()]{6,16}\d)(?!\d)")


def _tach_so_nha(uv, r_sdt):
    """Ứng viên dính SỐ NHÀ vào SĐT → trả phần SĐT bản địa, không thì None.

    Ca Rose Bulauan (Leg Glow Lab UAE, 14/09): khách gõ "Villa 23" xuống dòng "0556322399";
    R_SDT_CHUNG cho khoảng trắng/xuống dòng nằm giữa số nên nuốt thành "23 0556322399" (12 chữ
    số) → không khớp khuôn UAE → coi là SỐ NƯỚC NGOÀI → AI hỏi "is 0556322399 reachable on
    WhatsApp?". Chủ shop: *"SAO CÁI NÀY LẠI HỎI LẠI KHÁCH CÓ DÙNG SỐ WHATSAPP K LÀ SAO"*.
    Chỉ bỏ MỘT cụm ≤4 chữ số, không có dấu '+', đứng đầu hoặc cuối (số villa/flat/block) — để
    "+63 9 5555 1234" không bị cắt ra thành số Kuwait "5555 1234" (xem ghi chú bên dưới).
    """
    cum = re.split(r"\s+", uv.strip())
    if len(cum) < 2:
        return None
    # 23/09: thêm bỏ HAI cụm ở CUỐI — "0582949134 0 7", "0569033207 2677 5 St. Olaya" (số nhà/đường dính sau SĐT);
    # và bỏ ngoặc mồ côi — "Room 101 ( 0526553269)". Đầu thì vẫn chỉ bỏ MỘT cụm (giữ chốt "+63 9 5555 1234").
    for dau, cuoi in ((1, 0), (0, 1), (0, 2)):
        if dau + cuoi >= len(cum):
            continue
        bo = cum[:dau] + cum[len(cum) - cuoi:]
        if any("+" in b or not re.fullmatch(r"[\d()]{1,4}", b) for b in bo):
            continue
        phan = " ".join(cum[dau:len(cum) - cuoi]).strip(" ()")
        if re.fullmatch(rf"\s*{r_sdt}\s*", phan):
            return phan
    return None


# Ngày tháng khách gõ ("2026-09-30", "30/09/2026", "9/30/26") có đủ 7-15 chữ số nên lọt cửa
# ứng viên; ở Kuwait "20260930" còn khớp khuôn bản địa [24569]\d{3}\d{4}. Chặn ở đây để AI không
# đi hỏi "số 2026-09-30 của bạn có dùng WhatsApp không".
R_NGAY_SO = re.compile(r"^\s*(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\s*$")


# Ngày tháng gõ lẫn dấu cách: "12.29 1990" (ngày sinh), "09 -11-2026" — R_NGAY_SO đòi dấu -/. liền số nên
# trượt, rồi thành "SĐT hỏng" và AI đi bảo khách "số của bạn thiếu chữ số". Dấu đầu phải là -/. (không nhận
# "69 39 1082" = số Kuwait gõ cách), năm phải 19xx/20xx, ngày/tháng ≤ 31.
R_NGAY_CACH = re.compile(r"^\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.\s]\s*((?:19|20)\d{2})\s*$")


def _la_ngay_cach(t):
    m = R_NGAY_CACH.match(str(t or ""))
    return bool(m) and 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 31


def _la_sdt(t):
    """Chuỗi này trông có phải số điện thoại không (7-15 chữ số, không phải năm/giá/ngày)."""
    if R_NGAY_SO.match(str(t or "")) or _la_ngay_cach(t):
        return False
    d = re.sub(r"\D", "", str(t or ""))
    return 7 <= len(d) <= 15


# ── SĐT HỎNG ≠ SỐ NƯỚC NGOÀI ─────────────────────────────────────────────────
# Ca Uti Zahra 22/09 (Kreain Nature Legs Saudi): khách gõ "055216147" — số Saudi THIẾU MỘT CHỮ SỐ. Bản cũ
# thấy không khớp khuôn Saudi là coi luôn "số nước ngoài" → hồ sơ đủ SĐT → model chốt đơn ("is this number
# on WhatsApp? … Your order total is 159 SAR, arrive within 3-7 days") hai lần, trong khi máy lên đơn
# (auto_len_don.phan_loai_sdt) đọc đúng là 'hong' → "chưa có SĐT → KHÔNG tạo đơn". Sale phải tự nhắn
# "One digit is missing". Cùng lỗi ca Iis Sunita 11/09 ("+97158815211" thiếu 1 số).
# Đo 23/09 trên kho hồ sơ: 26/1232 hồ sơ đang giữ số HỎNG như số ngoại (Saudi 13, UAE 13); thêm 41 số
# Saudi/UAE gõ kiểu "00966…"/"0966…" bị coi là số ngoại (AI hỏi WhatsApp thừa) dù là số bản địa đúng.
# Hàm dưới đi ĐÚNG luật phan_loai_sdt, nhưng theo `mkey` truyền vào — không dựa MK toàn cục của
# auto_len_don (trong daemon bản đó có thể kẹt nước khác, xem memory daemon-hai-ban-auto-len-don).
_DAI_THAN = {}


def _than_ban_dia(mkey, r):
    """(số chữ số phần thân, tiền tố gõ trong nước ví dụ '05') — cùng cách auto_len_don.dai_sdt_ban_dia."""
    if mkey not in _DAI_THAN:
        ra = (None, "")
        pr = re.compile(r)
        for tien in ("0", ""):
            for than in range(6, 13):
                for d in "56789234":
                    if pr.fullmatch(tien + d + "1234567890"[:than]):
                        ra = (than + 1, tien + d)
                        break
                if ra[0]:
                    break
            if ra[0]:
                break
        _DAI_THAN[mkey] = ra
    return _DAI_THAN[mkey]


def _loi_ban_dia(so, m):
    """Chữ số khách gõ → dạng chuẩn bản địa (bóc xen kẽ '0'/mã nước) — y hệt auto_len_don._chuan_hoa_ban_dia."""
    d, cc = so, str(m.get("country_code") or "")
    while True:
        truoc = d
        d = d.lstrip("0")
        if cc and d.startswith(cc) and len(d) > len(cc) + 6:
            d = d[len(cc):]
        if d == truoc:
            break
    return d


def loai_sdt(goc, mkey):
    """Số khách gõ → ('ban_dia' | 'ngoai' | 'hong' | 'khong', lý do cho 'hong').

    Luật y như auto_len_don.phan_loai_sdt (máy lên đơn) để hai bên cùng một kết luận: bên lên đơn nói
    "chưa có SĐT" thì bên chat không được coi là đủ SĐT rồi chốt. Hai chỗ khác:
      · số có '+'/'00' mà mã nước nằm ngoài bảng MA_QUOC_TE (Ghana +233…) vẫn là 'ngoai' như bản cũ;
      · dãy số KHÔNG '0' đầu, KHÔNG mã nước, dài không sát khuôn bản địa (số toà "4301 4302", mã bưu chính
        "13313-7217", mã địa chỉ "6542 328") → 'khong' = không phải SĐT, bỏ qua — đừng bảo khách "số của bạn
        thiếu chữ số" về một thứ không phải số điện thoại (đo 23/09 trên kho hồ sơ).
    """
    m = _markets().get(mkey) or {}
    r, cc = m.get("sdt_regex"), str(m.get("country_code") or "")
    goc = so_latin(goc)
    so = re.sub(r"\D", "", goc)
    if not so or not r or not cc:
        return "ngoai", ""                               # thiếu dữ kiện → giữ hành vi cũ
    loi = _loi_ban_dia(so, m)
    chuan = ("0" + loi) if (m.get("sdt_them_0") and loi) else loi
    if re.fullmatch(r, chuan):
        return "ban_dia", ""
    if re.fullmatch(r"09\d{9}", so):
        return "ngoai", ""                               # Philippines gõ kiểu bản địa 09…
    try:
        import auto_len_don as D
        ma_qt, lech = D.MA_QUOC_TE, D._lech_mot_chu_so
    except Exception:                                    # noqa: BLE001 — không nạp được bảng mã nước → hành vi cũ
        return "ngoai", ""
    dai, tien = _than_ban_dia(mkey, r)
    ten = m.get("ten") or mkey.upper()
    khuon = ((f"số {ten} đủ {dai + len(tien) - 1} chữ số" + (f", dạng {tien}…" if tien.startswith("0") else ""))
             if dai else f"khuôn số {ten}")

    def _lech_do_dai():
        """'THIẾU/THỪA k chữ số — …' nếu thêm/bớt 1-2 chữ số cuối là thành số bản địa, không thì ''."""
        if dai and loi and 1 <= abs(len(loi) - dai) <= 2:
            thu = (loi + "0" * (dai - len(loi))) if len(loi) < dai else loi[:dai]
            if re.fullmatch(r, ("0" + thu) if m.get("sdt_them_0") else thu):
                k = abs(dai - len(loi))
                return f"{'THIẾU' if len(loi) < dai else 'THỪA'} {k} chữ số — {khuon}"
        return ""

    def _hong():
        return "hong", (_lech_do_dai() or f"không đúng {khuon}, cũng không có mã nước (+…)")
    nhan = so.lstrip("0")
    ro_qt = goc.strip().startswith("+") or so.startswith("00")
    if nhan.startswith(cc):
        return _hong()                                   # mã nước của chính thị trường mà thân số sai
    if not ro_qt and so.startswith("0"):
        return _hong()                                   # '0' đầu = gõ kiểu trong nước, không phải mã nước
    for n in (3, 2, 1):
        ma = nhan[:n]
        if ma not in ma_qt:
            continue
        than = nhan[n:].lstrip("0")
        if not ((len(than) == 10) if n == 1 else (7 <= len(than) <= 11)):
            continue
        if not ro_qt and len(nhan) < (dai or 0) + 2:
            break
        if lech(ma, cc):
            lt = _loi_ban_dia(than, m)
            if re.fullmatch(r, ("0" + lt) if m.get("sdt_them_0") else lt):
                return "hong", f"nghi GÕ NHẦM mã nước +{ma} (đúng là +{cc})"
        return "ngoai", ""
    if ro_qt:
        return "ngoai", ""
    ly = _lech_do_dai()                                  # "55216147": thân số Saudi thiếu 1, chỉ quên số 0
    return ("hong", ly) if ly else ("khong", "")


# ── SĐT TÁCH BẰNG DẤU PHẨY ───────────────────────────────────────────────────
# Ca Dawoodkhan (UAE 21/09): "My mobile number 055,9138041 055,6654243". R_SDT_CHUNG và SDT_UNG_VIEN_RE (auto_len_don)
# cố ý không nhận "," để khỏi nuốt giá "1,599" / "159,00" → cả AI lẫn máy lên đơn mù số này. Chủ shop 23/09: "bỏ dấu
# phẩy là dc mà". Chỉ bỏ phẩy khi nối lại ra SĐT bản địa đúng khuôn, hoặc số bản địa THIẾU/THỪA 1-2 chữ số (để AI xin
# lại đúng chỗ); giá tiền / "villa 12, 055…" nối lại không thành số bản địa nên giữ nguyên. Số nối xong bọc "; … ;"
# để R_SDT_CHUNG (cho phép dấu cách GIỮA số) không dính hai số đứng cạnh nhau thành một chuỗi 20 chữ số.
R_PHAY_SDT = re.compile(r"(?<![\d,.،])(\+?\d{2,5})\s?[,،]\s?(\d[\d \-]{2,11}\d)(?![\d,،])")


def noi_phay_sdt(t, mkey):
    """Chữ để DÒ SĐT: '055,9138041' → '; 0559138041 ;'. Dùng chung cho ho_so.trich và auto_len_don (_van_sdt)."""
    t = str(t or "")
    m = (_markets().get(mkey) or {}) if mkey else {}
    if not m.get("sdt_regex") or not re.search(r"\d\s?[,،]\s?\d", t):
        return t

    def _thay(x):
        so = x.group(1) + re.sub(r"\D", "", x.group(2))
        loai, ly = loai_sdt(so, mkey)
        if loai == "ban_dia" or (loai == "hong" and ly.startswith(("THIẾU", "THỪA"))):
            return f"; {so} ;"
        return x.group(0)
    return R_PHAY_SDT.sub(_thay, t)


# ── Phương thức thanh toán ───────────────────────────────────────────────────
# Chỉ có nghĩa ở thị trường thu tiền SAU. Nơi khác là COD tại cửa — không có gì để chọn,
# nên trường này coi như KHÔNG BẮT BUỘC (xem `thieu`), đừng bắt AI đi hỏi cho có.
PTTT = {
    "usa": re.compile(r"\b(zelle|venmo|cash\s?app|cashapp|paypal|check|cheque|cheq"
                      r"|money\s?order|money\s?gram|moneygram|western\s?union|debit|credit"
                      r"|bank\s?transfer)\b", re.I),
    "australia": re.compile(r"\b(payid|osko|bank\s?transfer|paypal|card|bpay)\b", re.I),
}
# PTTT_KHONG_BIET_2709 (ca Lourdes Canezo · Madam Mystic USA): "Hinde po alam ito check, CashApp, Venmo…" = KHÔNG BIẾT, không phải chọn.
_PTTT_KHONG_BIET = re.compile(
    r"(?i)\b(?:hindi|hinde|hnd|di|ndi|dko)\s+(?:ko\s+|q\s+|po\s+|ku\s+)*(?:alam|kabisado|marunong|gamay)\b"
    r"|\b(?:don'?t|dont|do\s+not|didn'?t)\s+(?:know|understand)\b|\bno\s+idea\b|\bnot\s+familiar\b"
    r"|\b(?:don'?t|dont|do\s+not)\s+have\s+(?:a\s+|any\s+)?(?:zelle|venmo|cash\s?app|cashapp|paypal|bank|card|account)\b"
    r"|\bwala\s*(?:akong|ako|kong|po\s+akong|pa\s+akong)\s+(?:zelle|venmo|cash\s?app|cashapp|paypal|bank|card|account)\b")

# ── Số lượng / combo ─────────────────────────────────────────────────────────
R_SL_RO = re.compile(r"\b\d+\s*(?:pc|pcs|piece|pieces|item|items|unit|units|tube|tubes"
                     r"|set|sets|box|boxes|bottle|bottles"
                     # khách gõ sai (24/09 ca Tajul Islam "I.want.by.1pes" → AI hỏi lại "Buy 1 or Buy 2?")
                     r"|pes|pis|pics?|pices?|peices?|peace|pcz|botles?|batle|botel|bote"
                     r"|pack|packs|jar|jars|bracelet|bracelets|wallet|قطعة|علبة|طقم)\b", re.I | re.U)
# Từ đếm Tagalog + "combo"/"buy N" gần như không bao giờ là chữ đệm -> tính ở mọi độ dài.
# 14/09 ca Rizki "aku pesan 1 gratis 1": máy dò không bắt, model đề xuất "Buy 1 Get 1" bị loc_model
# bỏ vì không trùng chữ nào → thêm cách nói Indo (beli/pesan N, N gratis/free/bonus N).
R_SL_LUON = re.compile(r"\b(isa|dalawa|tatlo|apat|lima|combo|bundle|buy\s*\d|set\s*\d"
                       r"|beli\s*\d|pesan\s*\d|pesen\s*\d|[1-4]\s*(?:gratis|free|bonus)\s*[1-4]"
                       r"|واحد|وحدة|حبة|حبتين|اثنين|ثلاثة|طقم)\b", re.I | re.U)
# Còn one/two/three/both tiếng Anh rất hay là chữ đệm nên CHỈ tính khi câu ngắn
# (đo thật: "im not the one checking the mailbox" không phải chốt số lượng).
R_SL_NGAN = re.compile(r"\b(one|two|three|both)\b", re.I)
# KHACH_VUA_CHON_GOI (chủ shop 14/09, ca Gha Cabilin Plaza): "Only 1 items to try" không bị bắt nên
# AI tưởng khách chưa chọn gói → chào hàng lại. Thêm "only/just 1", "1 only", "1+1", "b1g1".
# "only one" chỉ tính khi câu ngắn (≤ 8 từ) và không phải câu hỏi — "I have only one question?" loại.
# Sau "only/just 1" phải là HẾT CÂU hoặc chữ chỉ món/thử — "only one question", "only 1 week" không tính.
R_SL_CHI = re.compile(r"\b(?:only|just)\s*(?:1|one)\s*(?:$|po\b|pls\b|please\b|to\s+try|first|for\s+now"
                      r"|item|pc|piece|set|box|bottle|tube|pack)|^\s*(?:1|one)\s*only\b|\b[1-4]\s*\+\s*[1-4]\b"
                      r"|\bb[1-4]\s*[gt][1-4]\b|^\s*[1-4]\s*(?:get|take)\s*[1-4]\b", re.I)


# ── CHỮ SỐ Ả RẬP-ẤN / BA TƯ ─────────────────────────────────────────────────
# Bàn phím Ả Rập mặc định gõ ra ٠١٢٣…, khách vùng Vịnh dùng rất tự nhiên. `\d` của Python
# khớp cả những chữ số đó nên chúng lọt qua mọi bộ dò "trông như số", NHƯNG khuôn SĐT trong
# markets.json viết bằng chữ số Latin ('0', '5', '966') nên fullmatch trượt sạch — số hợp lệ
# bị đọc thành 'hong'. Ca Ibrahim (Minty Fresh Smile KSA, 20/09/2026): khách cho
# ٠٥٠٠٠٩٤٦٩٥ = 0500094695 (số Saudi đúng khuôn) → đơn #75631 mở ra KHÔNG có SĐT, lại còn
# bị coi là số nước ngoài nên AI đi hỏi thừa "số này có WhatsApp không?".
# Đổi về Latin ngay ở CỬA ĐỌC lời khách; chữ khách gõ vẫn được chép nguyên văn vào note.
SO_LATIN = {ord(c): str(i % 10) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹")}


def so_latin(t):
    """Chữ số Ả Rập-Ấn (٠١٢…) / Ba Tư (۰۱۲…) -> chữ số Latin. Chữ khác giữ nguyên."""
    return str(t or "").translate(SO_LATIN)


def _sach(t):
    t = re.sub(r"<[^>]+>", " ", str(t or ""))
    return so_latin(re.sub(r"\s+", " ", t).strip())


_TINH_DA_NAP = {"mkey": None}


def _co_ten_tinh(t, mkey):
    """Địa chỉ có nhắc tên tỉnh / bang / tiểu vương quốc của thị trường này không?

    Dùng lại bảng tỉnh mà `auto_len_don` tải từ POS (có nhớ đệm ở state/<tt>/provinces.json),
    chứ không tự chép danh sách — chép là sớm muộn lệch với POS.
    """
    try:
        import pancake_order as P
        if _TINH_DA_NAP["mkey"] != mkey:
            import auto_len_don as D
            D.set_market(mkey)
            _TINH_DA_NAP["mkey"] = mkey
        return bool(P.detect_emirate(t))
    except Exception:                                    # noqa: BLE001 — không tra được thì bỏ qua
        return False


# Khách hay GỘP số lượng + SĐT + địa chỉ vào MỘT tin, đúng như mẫu page xin ("✔️ Contact Number:
# ✔️ Complete Address:") — ca Menskie Trazares Bayonla 2026-09-20 (Nature's Daily Care in Saudi):
# "only 1 / 0554318991 / Exit 12 Rawdah 12 Riyadh Saudi Arabia". `_sach` gộp xuống dòng thành dấu cách
# nên "only 1" hết đứng cuối câu (R_SL_CHI đòi hết câu) và cả tin dài 10 từ nên cửa ≤8 từ cũng đóng
# → đơn #75773 ra "thiếu giá chốt (khách chưa chọn combo nào)" và AI đi hỏi lại đúng cái khách vừa
# trả lời: "how many boxes — 1, 2, or 3?". Nay cắt tin theo SĐT / xuống dòng / dấu phẩy rồi dò từng khúc.
# Chỉ nhận ba khuôn MẠNH (R_SL_RO "1 box", R_SL_LUON "combo/buy 1", R_SL_CHI "only 1") — R_SL_NGAN
# (one/two/both) cố ý để ngoài vì một khúc ngắn chỉ có chữ "one" quá dễ oan.
# Đo 99.518 tin khách (state/*/so_chi_phi.jsonl): bắt thêm 8 tin / 5 câu, tất cả là chốt số lượng thật, 0 oan.
# ⚠️ Cắt SĐT phải cắt theo TỪ. Bản đầu dùng khuôn SĐT quen thuộc `\d[\d\s\-().]{6,}\d` — `\s` nuốt cả dấu
# xuống dòng nên "1\n0554318991" thành MỘT khuôn SĐT, con số số lượng biến mất cùng nó (đúng họ với bẫy
# "số dính số villa" ở _tach_so_nha). Nay chỉ coi là SĐT khi CẢ TỪ dài ≥6 ký tự toàn chữ số/()+-.
_SO_DAI = re.compile(r"(?<!\S)[\d()+\-.]{6,}(?!\S)")
_TACH_KHUC = re.compile(r"[\n\r,;|]|\s{2,}")


def sl_trong_khuc(tho):
    """Khúc ngắn nào trong tin khách (nguyên văn, CHƯA gộp dòng) là lời chốt số lượng — không thì None.

    Chỉ cắt ở chỗ khách TỰ ngắt: xuống dòng, dấu phẩy/chấm phẩy, khoảng trắng đôi, hoặc một từ toàn số
    (SĐT). CỐ Ý không thử "mấy từ đầu câu": R_SL_CHI chặn "only 1 question" bằng cách đòi hết câu sau
    "only 1" — cắt bừa theo số từ là phá đúng cái chặn đó.
    """
    for d in _TACH_KHUC.split(_SO_DAI.sub("\n", str(tho or ""))):
        d = _sach(d)
        if not d or len(d.split()) > 8 or la_cau_hoi(d):
            continue
        if R_SL_RO.search(d) or R_SL_LUON.search(d) or R_SL_CHI.search(d):
            return d
    return None


def trich(msgs, mkey, gia=None, ten_khach=None, dung_tinh=True):
    """Đọc lời KHÁCH, trả {trường: nguyên văn câu khách đã nói}. Chỉ quét tin của khách.

    `msgs`: list tin, mỗi tin {'boi': 'khach'|..., 'text': ...} — đúng khuôn ai_sale.
    """
    m = (_markets().get(mkey) or {})
    r_sdt = m.get("sdt_regex")
    bat_ban_dia = bool(m.get("sdt_bat_buoc_ban_dia"))
    r_pttt = PTTT.get(mkey)
    gia = gia or {}
    loi = [(_sach(x["text"]), x.get("text") or "") for x in msgs if x.get("boi") == "khach"]
    co = {}
    # Mục 1: tên Facebook đã tính là ĐỦ — hỏi lại tên khi đã thấy tên là thừa và gây khó chịu.
    if ten_khach:
        co["ten"] = f"{ten_khach} (tên Facebook — mục 1 coi là đã đủ)"

    for t, tho in loi:
        if not t:
            continue
        # ── SĐT — bản địa trước, không có thì nhận số nước ngoài ─────────────
        # ⚠️ Phải TÁCH ỨNG VIÊN TRƯỚC rồi mới thử khuôn bản địa lên TRỌN ứng viên.
        # Dò regex bản địa thẳng trên câu là bắt nhầm một khúc GIỮA số ngoại: khuôn Kuwait
        # `[24569]\d{3}[\s.-]?\d{4}` khớp "63917123" nằm trong "+639171234567" của khách
        # Philippines — rồi Kuwait (nước BẮT BUỘC số bản địa) tưởng đã có số hợp lệ.
        # Số BẢN ĐỊA MỚI NHẤT thắng — khách gõ sai rồi gửi lại số đúng là chuyện thường (ca Iis
        # Sunita 11/09: "+97158815211" thiếu một số, rồi "+971588915211"; bản cũ khoá số đầu, coi
        # là số ngoại → AI đi hỏi WhatsApp và không lên đơn). Số ngoại chỉ nhận khi chưa có gì,
        # không thay được số bản địa đã có.
        for uv in (x.group(1).strip() for x in R_SDT_CHUNG.finditer(noi_phay_sdt(t, mkey))):
            if not _la_sdt(uv):
                continue
            ban_dia = bool(r_sdt and re.fullmatch(rf"\s*{r_sdt}\s*", uv))
            if r_sdt and not ban_dia:
                tach = _tach_so_nha(uv, r_sdt)
                if tach:
                    uv, ban_dia = tach, True
            loai, ly_do = ("ban_dia", "") if ban_dia else loai_sdt(uv, mkey)
            if loai == "khong":
                # "O85. 058660295" — số nhà dính trước SĐT: xét riêng từng cụm đủ dài
                for _cum in re.split(r"\s+", uv):
                    if len(re.sub(r"\D", "", _cum)) >= 7:
                        _l2, _ly2 = loai_sdt(_cum, mkey)
                        if _l2 != "khong":
                            uv, loai, ly_do = _cum.strip(" .,()"), _l2, _ly2
                            break
            if loai == "khong":
                continue                                 # số toà / mã bưu chính… — không phải SĐT
            if ban_dia or loai == "ban_dia":
                co["sdt"] = uv
                co["sdt_ngoai"] = False
                co.pop("sdt_hong", None)
            elif "sdt" not in co and not bat_ban_dia:
                if loai == "hong":
                    # Số HỎNG (thiếu/thừa chữ số…) — KHÔNG phải số nước ngoài. Không nhận vào "sdt", giữ để
                    # khối prompt bảo AI chỉ ra chỗ sai và xin lại số (ca Uti Zahra 22/09).
                    co["sdt_hong"] = f"{uv} ({ly_do})" if ly_do else uv
                else:
                    co["sdt"] = uv
                    co["sdt_ngoai"] = True
            elif bat_ban_dia:
                # Kuwait / Bahrain: số nước khác KHÔNG giao được, nên không nhận vào "sdt".
                # Nhưng im lặng bỏ qua là AI mù: nó thấy "CÒN THIẾU: SĐT" rồi đi xin số như thể
                # khách chưa cho gì (ca Lyn Amsiugal 19/09: AI còn "Noted your number" với số
                # Philippines, đơn nằm Mới). Giữ lại để khối prompt bảo AI xin ĐÚNG số bản địa.
                co["sdt_sai_nuoc"] = uv

        # ── Địa chỉ — CÓ GÌ NHẬN NẤY, thiếu phần nào thì ghi ra để đi xin ────
        # Chủ shop chốt 2026-09-08: "thiếu thì xin thêm mục thiếu, nhưng khách cho những gì
        # rồi thì lên đơn trước những mục đó." Nên KHÔNG chặn đơn vì địa chỉ chưa hoàn hảo —
        # nhận phần khách đã cho, đồng thời nói rõ còn thiếu phần nào để AI xin đúng phần đó.
        # Ngưỡng độ dài chỉ để loại tin rác. Không đặt cao được: "Block 338" (9 ký tự) và
        # "Salmiya area" (12) là địa chỉ thật khách gửi, chỉ chưa đủ.
        # Link định vị Google Maps = khách ĐÃ cho địa chỉ (chủ shop 15/09: khách không biết địa chỉ thì xin gửi
        # định vị để ra đơn luôn). Ghi nguyên link để đơn nháp mang theo, sale mở link là thấy chỗ giao.
        if "dia_chi" not in co and R_DINH_VI.search(t):
            co["dia_chi"] = "định vị: " + R_DINH_VI.search(t).group(0)[:150]
            co["dia_chi_thieu"] = ["tên khu/toà nhà nếu link không rõ"]
        if "dia_chi" not in co and len(t) >= 7:
            co_tu = bool(TU_DIA_CHI.search(t))
            co_so = bool(re.search(r"\d", t))
            co_my = mkey == "usa" and (R_DUONG_MY.search(t)
                                       or (R_ZIP_MY.search(t) and len(t) > 40))
            # Tên tỉnh/tiểu vương quốc đứng MỘT MÌNH cũng tính là đã cho địa chỉ —
            # "I live in Al Barsha, Dubai" là địa chỉ chưa đủ, không phải là chưa có địa chỉ.
            # Chủ shop chốt: nhận phần khách đã cho, xin thêm phần thiếu, đừng hoãn đơn.
            # Loại câu hỏi ("are you in Dubai?") và câu quá ngắn để khỏi nhặt nhầm.
            la_hoi = la_cau_hoi_dia_chi(t)      # 17/09: bắt cả cụm hỏi giữa câu
            co_tinh = bool(dung_tinh and not la_hoi and len(t.split()) >= 3
                           and _co_ten_tinh(t, mkey))
            # Từ khoá địa chỉ đứng một mình ("Salmiya area", "Block 4") cũng tính là ĐÃ CHO
            # địa chỉ. Bảng tỉnh của POS chỉ có cấp tỉnh/tiểu vương quốc, không có tên khu —
            # "Salmiya" là khu thuộc Hawalli nên `_co_ten_tinh` không thấy, nhưng khách đã cho
            # thật. Loại câu hỏi để khỏi nhặt "what area do you deliver to?".
            if (co_my or co_tinh or (_co_tu_dia_chi_manh(t) and not la_hoi) or (co_so and co_tu)) \
                    and not khong_phai_dia_chi(t, mkey):
                co["dia_chi"] = t[:180]
                con = []
                if not (co_tinh or co_my):
                    con.append("tên tỉnh/thành/tiểu vương quốc")
                if not (co_so or co_my):
                    con.append("số nhà / toà nhà / block")
                if con:
                    co["dia_chi_thieu"] = con

        # ── Phương thức thanh toán (chỉ thị trường thu tiền sau) ─────────────
        if "thanh_toan" not in co and r_pttt:
            g = r_pttt.search(t)
            # PTTT_KHONG_BIET_2709 — câu phủ định / không biết, hoặc liệt kê ≥3 cách (chép lại danh sách page) không phải lời CHỌN
            if g and (_PTTT_KHONG_BIET.search(t) or len({x.lower() for x in r_pttt.findall(t)}) >= 3):
                g = None
            if g:
                co["thanh_toan"] = f'{g.group(0)}  (khách nói: "{t[:90]}")'

        # ── Số lượng / combo ─────────────────────────────────────────────────
        if "so_luong" not in co:
            muc = [g for g in (list(gia.get("gia_ban") or []) + list(gia.get("gia_chao") or []))
                   if g and re.search(rf"\b{g}\b", t)]
            if muc:
                co["so_luong"] = f'khách nhắc mức {muc[0]} (khách nói: "{t[:90]}")'
            elif (R_SL_RO.search(t) or R_SL_LUON.search(t)
                  or ((R_SL_NGAN.search(t) or R_SL_CHI.search(t))
                      and len(t.split()) <= 8 and not la_cau_hoi(t))):
                co["so_luong"] = f'khách nói: "{t[:90]}"'
            else:
                _khuc = sl_trong_khuc(tho)          # tin gộp số lượng + SĐT + địa chỉ
                if _khuc:
                    co["so_luong"] = f'khách nói: "{_khuc[:90]}"'
    return co


# ═════════════════════════════════════════════════════════════════════════════
# MODEL ĐỀ XUẤT — LUẬT THẨM ĐỊNH
# ═════════════════════════════════════════════════════════════════════════════
# Máy dò (`trich`) chạy theo khuôn cứng nên không bịa, nhưng bí khi khách viết kiểu lạ:
# địa chỉ Ả Rập viết tự do, "cho tôi cái rẻ hơn" thay vì "combo 1"… Model ĐỌC HIỂU được
# những câu đó. Nên cho model điền vào chỗ máy dò bỏ trống — nhưng KHÔNG cho nó nói gì cũng
# được, vì tiền và địa chỉ là chỗ không được đoán.
#
# BA RÀNG BUỘC, cái nào hỏng thì BỎ đề xuất đó chứ không sửa nửa vời:
#   1. Máy dò đã có -> giữ máy dò. Model chỉ vá chỗ TRỐNG, không được sửa chỗ đã biết.
#   2. SĐT phải khớp `sdt_regex` của thị trường; thanh toán phải nằm trong danh sách shop nhận.
#   3. Địa chỉ / số lượng phải TÌM THẤY TRONG LỜI KHÁCH — model không được nghĩ ra chữ mới.

def _chu(t):
    return set(re.findall(r"[\w\u0600-\u06FF\u4e00-\u9fff]{2,}", str(t or "").lower()))


def _co_trong_loi_khach(gt, loi_khach, nguong=0.6):
    """Phần lớn chữ trong đề xuất có thật sự xuất hiện trong lời khách không?

    Đây là hàng rào chống bịa. Model tóm tắt lại lời khách thì các chữ chính vẫn trùng;
    model nghĩ ra một địa chỉ mới thì gần như không trùng chữ nào.
    """
    c = _chu(gt)
    if not c:
        return False
    kho = _chu(" ".join(loi_khach))
    return len(c & kho) / len(c) >= nguong


def loc_model(de_xuat, msgs, mkey, da_co=None):
    """Lọc phần `da_biet` model trả về. Trả (những trường ĐƯỢC NHẬN, những trường BỊ TỪ CHỐI).

    Từ chối có nêu lý do để còn đo được model hay bịa chỗ nào — im lặng bỏ qua là mất tín hiệu.
    """
    if not isinstance(de_xuat, dict):
        return {}, {}
    m = (_markets().get(mkey) or {})
    r_sdt, r_pttt = m.get("sdt_regex"), PTTT.get(mkey)
    loi_khach = [_sach(x["text"]) for x in msgs if x.get("boi") == "khach"]
    nhan, bo = {}, {}
    for k in TRUONG:
        gt = so_latin(str(de_xuat.get(k) or "").strip())
        if not gt or k == "ten":            # tên đã lấy từ Facebook, không cần model
            continue
        if (da_co or {}).get(k):
            bo[k] = "máy dò đã có — không cho model sửa đè"
            continue
        if k == "sdt":
            # KHÔNG ép khuôn bản địa: số nước ngoài vẫn nhận (chủ shop chốt 2026-09-08).
            # Chỉ đòi nó trông như một số điện thoại thật, và có mặt trong lời khách.
            if not _la_sdt(gt) or not _co_trong_loi_khach(re.sub(r"\D", "", gt), loi_khach, 0.0) \
                    and not any(re.sub(r"\D", "", gt) in re.sub(r"\D", "", x) for x in loi_khach):
                bo[k] = "không phải số điện thoại, hoặc không có trong lời khách"
                continue
            _co = trich([{"boi": "khach", "text": gt}], mkey, dung_tinh=False)
            if not _co.get("sdt"):
                if _co.get("sdt_hong"):
                    bo[k] = f"số hỏng — {_co['sdt_hong']} (máy lên đơn cũng không nhận)"
                elif _co.get("sdt_sai_nuoc"):
                    bo[k] = "số nước ngoài — nước này bắt buộc số bản địa"
                else:
                    bo[k] = "không phải SĐT dùng được (máy lên đơn cũng không nhận)"
                continue
        elif k == "thanh_toan":
            if not (r_pttt and r_pttt.search(gt)):
                bo[k] = "không nằm trong danh sách phương thức shop nhận"
                continue
        elif k == "dia_chi" and khong_phai_dia_chi(gt, mkey):
            bo[k] = f"không phải địa chỉ — {TEN_KHONG_PHAI_DC[khong_phai_dia_chi(gt, mkey)]}"
            continue
        elif not _co_trong_loi_khach(gt, loi_khach):
            bo[k] = "chữ không có trong lời khách — nghi model tự nghĩ ra"
            continue
        nhan[k] = f"{gt[:180]}  (model đọc ra từ lời khách)"
    return nhan, bo


def thieu(co, mkey):
    """Trường nào CÒN THIẾU để được lên đơn (mục 1 + 9).

    `thanh_toan` chỉ tính là bắt buộc ở thị trường thu tiền SAU khi nhận hàng (mục 9b).
    Nơi khác là COD tại cửa — bắt AI đi hỏi "anh muốn trả bằng gì" là hỏi thừa.
    """
    can = [k for k in TRUONG if k != "thanh_toan" or mkey in THU_TIEN_SAU]
    return [k for k in can if not (co or {}).get(k)]


def du_dieu_kien(co, mkey):
    return not thieu(co, mkey)


def khoi_prompt(co, mkey):
    """Hai khối chèn vào đầu bài cho model — thay cho việc để model tự nhớ.

    Kèm hai lời nhắc SINH RA TỪ DỮ LIỆU, không phải câu chữ chung chung:
      · số nước ngoài  -> phải hỏi khách có dùng WhatsApp số đó không (bưu tá liên hệ qua đó)
      · địa chỉ thiếu  -> xin đúng phần còn thiếu, nhưng KHÔNG chặn việc lên đơn
    """
    co = co or {}
    con = thieu(co, mkey)
    da = "\n".join(f"- {TEN_TRUONG.get(k, k).upper()}: {v}"
                   for k, v in co.items() if v and k in TEN_TRUONG) \
        or "(khách chưa cho thông tin nào)"
    nhac = []
    _m = _markets().get(mkey) or {}
    _ten_nuoc = _m.get("ten") or mkey.upper()
    if _m.get("sdt_bat_buoc_ban_dia"):
        _khuon = _m.get("sdt_mo_ta") or "số nội địa"
        if co.get("sdt_sai_nuoc") and not co.get("sdt"):
            nhac.append(f"⚠️ Khách ĐÃ cho số {co['sdt_sai_nuoc']} nhưng đó KHÔNG phải số {_ten_nuoc} — "
                        f"bưu tá {_ten_nuoc} chỉ gọi và giao được số nội địa ({_khuon}). Cảm ơn số đó, nói "
                        f"NGẮN lý do rồi xin số {_ten_nuoc} để giao hàng; đừng hỏi như thể khách chưa cho "
                        f"số nào, đừng đọc lại số cũ. Khách nói không có số {_ten_nuoc} → 'tra_loi_treo', "
                        f"ghi chú cho sale.")
        elif co.get("sdt"):
            nhac.append(f"✅ SĐT {co['sdt']} máy ĐÃ kiểm đúng khuôn số {_ten_nuoc}. Không nghi ngờ, không "
                        f"hỏi lại, không treo vì số này, không nói với khách rằng số sai.")
    if co.get("sdt_hong") and not co.get("sdt"):
        nhac.append(f"⚠️ Khách CÓ gửi số {co['sdt_hong']} nhưng máy đã kiểm: đây KHÔNG phải SĐT hợp lệ — "
                    f"bưu tá không gọi được nên ĐƠN CHƯA ĐI ĐƯỢC. Cảm ơn khách, nói NGẮN số chưa đúng ở đâu "
                    f"(vd 'số này mới có 9 chữ số'), xin gửi lại số ĐẦY ĐỦ (số nước ngoài thì kèm mã nước +…). "
                    f"CẤM chốt đơn / báo tổng tiền + ngày giao như đơn đã xong; CẤM hỏi số này có WhatsApp "
                    f"không; CẤM tự đoán thêm/bớt chữ số.")
    if co.get("sdt") and co.get("sdt_ngoai"):
        nhac.append("⚠️ SĐT khách cho KHÔNG PHẢI số nội địa của thị trường này. Vẫn lên đơn "
                    "bình thường, nhưng PHẢI hỏi khách một câu: số này có dùng WhatsApp không? "
                    "— bưu tá sẽ liên hệ giao hàng qua WhatsApp vì đây là số nước ngoài.")
    if co.get("dia_chi_thieu") and not co.get("dia_chi_chua_giao"):
        nhac.append("Địa chỉ khách cho còn thiếu: " + ", ".join(co["dia_chi_thieu"])
                    + ". Xin thêm ĐÚNG phần đó, một câu ngắn. KHÔNG được vì thế mà hoãn "
                      "lên đơn — cứ chốt những gì khách đã cho.")
    if co.get("dia_chi_chua_giao"):
        # 23/09 (ca Riesalyn Galvez Dela Cruz · Hitana Store in Saudi, #76709): hồ sơ CÓ địa chỉ ("Al faysaliyah dist.")
        # → khối dưới in "(không thiếu gì — chuyển sang chốt đơn)" → AI: "Since you already gave me everything, I can
        # book your 2 Sets now". Chủ shop: *"ở đây bạn chỉ tạo đơn được thôi, còn chốt đơn với khách thì chưa được,
        # phải xin thêm những cái còn thiếu để giao được thị trường đó"*. ai_sale.nhac_dia_chi_chua_giao dò 3 cấp
        # (cùng thước với cửa tự xác nhận đơn) và soạn sẵn đoạn nhắc; ở đây chỉ chèn + đưa "Địa chỉ" trở lại CÒN THIẾU.
        nhac.append(co["dia_chi_chua_giao"])
        if "dia_chi" not in con:
            con = con + ["dia_chi"]
    return (f"=== KHÁCH ĐÃ CHO RỒI — TUYỆT ĐỐI KHÔNG HỎI LẠI ===\n{da}\n\n"
            + ("\n".join(nhac) + "\n\n" if nhac else "")
            + f"=== CÒN THIẾU — CHỈ ĐƯỢC HỎI NHỮNG MỤC NÀY ===\n"
            + (", ".join(TEN_TRUONG.get(k, k) for k in con) if con
               else "(không thiếu gì — chuyển sang chốt đơn)"))


# ═════════════════════════════════════════════════════════════════════════════
# ② KHO HỒ SƠ — SQLite
# ═════════════════════════════════════════════════════════════════════════════

LUOC_DO = """
CREATE TABLE IF NOT EXISTS ho_so (
  conv_id       TEXT PRIMARY KEY,
  page_id       TEXT,
  ten_khach     TEXT,
  ten           TEXT,
  sdt           TEXT,
  dia_chi       TEXT,
  so_luong      TEXT,
  thanh_toan    TEXT,
  buoc          TEXT DEFAULT 'moi',
  tin_da_doc    TEXT,          -- mốc nước: thời điểm tin cuối ĐÃ quét (chuỗi ISO của API)
  so_tin        INTEGER DEFAULT 0,
  tom_tat       TEXT,
  cap_nhat      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_page ON ho_so(page_id);
CREATE INDEX IF NOT EXISTS idx_buoc ON ho_so(buoc);

-- Ghi chú thuộc loại "chỉ ghi MỘT LẦN cho mỗi hội thoại" mà hội thoại này đã nhận rồi.
-- Danh sách loại nằm ở ai_sale.GHI_CHU_MOT_LAN.
-- Để BẢNG RIÊNG chứ không thêm cột vào ho_so: `mo()` chỉ chạy CREATE TABLE IF NOT EXISTS,
-- thêm cột vào bảng cũ sẽ không có tác dụng trên máy đang chạy (kho cũ đã tồn tại), còn
-- bảng mới thì tự sinh ở lần mở đầu tiên — không phải vá tay trên VPS.
-- Số khách ĐÃ cho nhưng không phải số bản địa ở nước bắt buộc số bản địa (Kuwait/Bahrain).
-- Bảng riêng vì `mo()` chỉ chạy CREATE TABLE IF NOT EXISTS — thêm cột vào ho_so không ăn trên kho cũ.
CREATE TABLE IF NOT EXISTS sdt_sai_nuoc (
  conv_id  TEXT PRIMARY KEY,
  so       TEXT,
  luc      INTEGER
);

-- Số khách ĐÃ gửi nhưng HỎNG (thiếu/thừa chữ số, sai khuôn) — ca Uti Zahra 22/09. Bảng riêng, cùng lý do trên.
CREATE TABLE IF NOT EXISTS sdt_hong (
  conv_id  TEXT PRIMARY KEY,
  so       TEXT,
  luc      INTEGER
);

CREATE TABLE IF NOT EXISTS ghi_chu_da_ghi (
  conv_id  TEXT,
  loai     TEXT,
  luc      INTEGER,
  PRIMARY KEY (conv_id, loai)
);

-- Con số (giá, SĐT) đã từng đi vào ghi chú của hội thoại. Ghi chú sau trùng VIỆC nhưng mang
-- con số mới thì vẫn ghi — đó là tin mới cho sale, không phải lời nhờ lặp lại (chủ shop 21/09).
-- Bảng riêng vì `mo()` chỉ chạy CREATE TABLE IF NOT EXISTS: thêm cột không ăn trên kho cũ.
CREATE TABLE IF NOT EXISTS ghi_chu_so (
  conv_id  TEXT,
  so       TEXT,
  luc      INTEGER,
  PRIMARY KEY (conv_id, so)
);
"""


def duong_db(mkey):
    return os.path.join(SCRIPT_DIR, "state", mkey, "ho_so.db")


def mo(mkey):
    """Mở (và tạo nếu chưa có) kho hồ sơ của một thị trường.

    WAL để vòng chạy và giao diện web đọc/ghi cùng lúc không chặn nhau.
    """
    f = duong_db(mkey)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    cn = sqlite3.connect(f, timeout=10)
    cn.row_factory = sqlite3.Row
    cn.execute("PRAGMA journal_mode=WAL")
    cn.executescript(LUOC_DO)
    return cn


def doc(cn, conv_id):
    r = cn.execute("SELECT * FROM ho_so WHERE conv_id=?", (str(conv_id),)).fetchone()
    return dict(r) if r else None


def da_ghi_chu(cn, conv_id, loai):
    """Hội thoại này đã nhận ghi chú loại `loai` chưa? — chống ghi lặp cùng một lời nhờ."""
    if cn is None or not loai:
        return False
    return cn.execute("SELECT 1 FROM ghi_chu_da_ghi WHERE conv_id=? AND loai=?",
                      (str(conv_id), loai)).fetchone() is not None


def nho_ghi_chu(cn, conv_id, loai):
    """Đánh dấu: hội thoại này đã có ghi chú loại `loai`, lần sau khỏi ghi lại."""
    if cn is None or not loai:
        return
    cn.execute("INSERT OR IGNORE INTO ghi_chu_da_ghi (conv_id, loai, luc) VALUES (?,?,?)",
               (str(conv_id), loai, int(time.time())))
    cn.commit()


def so_da_ghi_chu(cn, conv_id):
    """Những con số (giá, SĐT) đã từng nằm trong ghi chú của hội thoại này."""
    if cn is None:
        return set()
    return {r[0] for r in cn.execute("SELECT so FROM ghi_chu_so WHERE conv_id=?", (str(conv_id),))}


def nho_so_ghi_chu(cn, conv_id, so):
    """Nhớ các con số vừa đi vào ghi chú — lần sau biết ghi chú mới có tin mới hay chỉ nhắc lại."""
    if cn is None or not so:
        return
    luc = int(time.time())
    cn.executemany("INSERT OR IGNORE INTO ghi_chu_so (conv_id, so, luc) VALUES (?,?,?)",
                   [(str(conv_id), str(s), luc) for s in so])
    cn.commit()


def gop(cu, moi):
    """Gộp hồ sơ cũ với thứ vừa trích được. Trả (hồ sơ mới, có đổi gì không).

    LUẬT: trường ĐÃ BIẾT không bao giờ bị ghi đè bằng rỗng, và cũng không bị ghi đè bằng
    giá trị mới trừ khi trường đó đang trống. Khách sửa lại địa chỉ thì model phải nói ra
    (mục 9b chốt 1: "cho địa chỉ khác -> quay lại thì 1"), chứ luật regex quét lướt qua một
    câu có chữ "street" không đủ tư cách xoá địa chỉ khách đã xác nhận.
    """
    ra = dict(cu or {})
    doi = False
    for k in ("sdt_ngoai", "dia_chi_thieu", "sdt_sai_nuoc", "sdt_hong"):   # cờ phụ: luôn lấy bản mới nhất
        if (moi or {}).get(k) is not None:
            ra[k] = moi[k]
    for k in TRUONG:
        v = (moi or {}).get(k)
        if v and not ra.get(k):
            ra[k] = v
            doi = True
        elif (v and k == "sdt" and v != ra.get(k)
              and (moi or {}).get("sdt_ngoai") is False):
            # NGOẠI LỆ DUY NHẤT của luật không-ghi-đè (2026-09-11): khách gửi lại một số BẢN ĐỊA
            # khác số đang lưu = khách sửa số (ca Iis Sunita: số đầu thiếu một chữ số, hồ sơ
            # khoá số sai cả buổi). Số bản địa mới thay số cũ; số ngoại thì không được thay.
            ra[k] = v
            doi = True
    if ra.get("sdt"):
        ra.pop("sdt_sai_nuoc", None)   # đã có số bản địa thì số sai nước hết ý nghĩa
        ra.pop("sdt_hong", None)       # đã có số dùng được thì số hỏng cũ hết ý nghĩa
    return ra, doi


def ghi(cn, conv_id, page_id, hs, tin_da_doc=None, so_tin=None, buoc=None,
        ten_khach=None, tom_tat=None):
    cu = doc(cn, conv_id) or {}
    ban = {
        "conv_id": str(conv_id),
        "page_id": str(page_id or cu.get("page_id") or ""),
        "ten_khach": ten_khach or cu.get("ten_khach"),
        "buoc": buoc or cu.get("buoc") or "moi",
        "tin_da_doc": tin_da_doc if tin_da_doc is not None else cu.get("tin_da_doc"),
        "so_tin": so_tin if so_tin is not None else (cu.get("so_tin") or 0),
        "tom_tat": tom_tat if tom_tat is not None else cu.get("tom_tat"),
        "cap_nhat": int(time.time()),
    }
    for k in TRUONG:
        ban[k] = (hs or {}).get(k) or cu.get(k)
    cot = list(ban)
    cn.execute(f"INSERT INTO ho_so ({','.join(cot)}) VALUES ({','.join('?' * len(cot))}) "
               f"ON CONFLICT(conv_id) DO UPDATE SET "
               + ",".join(f"{c}=excluded.{c}" for c in cot if c != "conv_id"),
               [ban[c] for c in cot])
    cn.commit()
    return ban


def nho_sdt_sai_nuoc(cn, conv_id, hs, co_moi):
    """Nhớ BỀN số khách đã cho mà nước này không giao được (Kuwait/Bahrain).

    Cờ `sdt_sai_nuoc` chỉ sinh ra ở lượt khách vừa gõ số; lượt sau `trich` chạy trên tin MỚI nên
    cờ biến mất và AI lại đi xin "số điện thoại" trống trơn. Giữ trong bảng riêng tới khi có số
    bản địa thật. Trả lại chính `hs` (đã gắn cờ nếu còn nợ số).
    """
    so = (co_moi or {}).get("sdt_sai_nuoc")
    if (hs or {}).get("sdt"):
        cn.execute("DELETE FROM sdt_sai_nuoc WHERE conv_id=?", (str(conv_id),))
        cn.commit()
        hs.pop("sdt_sai_nuoc", None)
        return hs
    if so:
        cn.execute("INSERT INTO sdt_sai_nuoc (conv_id, so, luc) VALUES (?,?,?) "
                   "ON CONFLICT(conv_id) DO UPDATE SET so=excluded.so, luc=excluded.luc",
                   (str(conv_id), so, int(time.time())))
        cn.commit()
    else:
        r = cn.execute("SELECT so FROM sdt_sai_nuoc WHERE conv_id=?", (str(conv_id),)).fetchone()
        if r and r[0]:
            hs["sdt_sai_nuoc"] = r[0]
    return hs


def nho_sdt_hong(cn, conv_id, hs, co_moi):
    """Nhớ BỀN số khách đã gửi mà HỎNG (thiếu/thừa chữ số) — như nho_sdt_sai_nuoc.

    Cờ `sdt_hong` chỉ sinh ở lượt khách vừa gõ số; không nhớ thì lượt sau AI quên là khách đã gửi số (sai)
    và xin "số điện thoại" như thể chưa cho gì. Xoá khi hồ sơ đã có SĐT dùng được. Trả lại chính `hs`.
    """
    so = (co_moi or {}).get("sdt_hong")
    if (hs or {}).get("sdt"):
        cn.execute("DELETE FROM sdt_hong WHERE conv_id=?", (str(conv_id),))
        cn.commit()
        hs.pop("sdt_hong", None)
        return hs
    if so:
        cn.execute("INSERT INTO sdt_hong (conv_id, so, luc) VALUES (?,?,?) "
                   "ON CONFLICT(conv_id) DO UPDATE SET so=excluded.so, luc=excluded.luc",
                   (str(conv_id), so, int(time.time())))
        cn.commit()
    else:
        r = cn.execute("SELECT so FROM sdt_hong WHERE conv_id=?", (str(conv_id),)).fetchone()
        if r and r[0]:
            hs["sdt_hong"] = r[0]
    return hs


def chi_truong(hs):
    """Chỉ lấy 5 trường (bỏ cột kỹ thuật) — dạng dùng cho `khoi_prompt` / `thieu`."""
    return {k: (hs or {}).get(k) for k in TRUONG if (hs or {}).get(k)}


def tin_moi(msgs, tin_da_doc):
    """Chỉ những tin MỚI hơn mốc nước. Không có mốc thì trả nguyên (lần đầu gặp hội thoại)."""
    if not tin_da_doc:
        return msgs
    return [m for m in msgs if str(m.get("luc") or "") > str(tin_da_doc)]


# ═════════════════════════════════════════════════════════════════════════════
# Bản in ra terminal
# ═════════════════════════════════════════════════════════════════════════════

CA_THU = {
    "usa": [("Maria Santos", [
        "hi how much po",
        "ok po sige, 2 sets na lang",
        "Maria Santos, 4015248356",
        "35 Crescent Avenue Cranston Rhode Island 02910",
        "i will pay by zelle po"])],
    "uae": [("Fatima", [
        "كم السعر",
        "ابغى وحدة",
        "0501234567",
        "Villa 12, Street 4, Al Barsha 1, Dubai, near Lulu"])],
    "kuwait": [("Josie", [
        "magkano po", "2 pcs po", "97712345",
        "Block 4, Street 12, Jadda 5, House 20, Salmiya"])],
    "bahrain": [("Ahmed", [
        "price?", "one set", "36123456",
        "Building 210, Road 15, Block 338, Adliya"])],
}


def _thu(mkey):
    ca = CA_THU.get(mkey)
    if not ca:
        return print(f"Chưa dựng ca mẫu cho {mkey}. Có: {', '.join(CA_THU)}")
    print(f"\n═══ Luật trích xuất — {mkey} ═══\n")
    for ten, tin in ca:
        msgs = [{"boi": "khach", "text": t, "luc": f"2026-09-08T0{i}:00:00"}
                for i, t in enumerate(tin)]
        co = trich(msgs, mkey, ten_khach=ten)
        print(f"  Khách: {ten}")
        for k in TRUONG:
            v = co.get(k)
            print(f"    {'✅' if v else '✖ '} {TEN_TRUONG[k]:24s} {(v or '(không thấy)')[:70]}")
        t = thieu(co, mkey)
        print(f"    → {'ĐỦ ĐIỀU KIỆN LÊN ĐƠN' if not t else 'còn thiếu: ' + ', '.join(t)}\n")


def _xem(mkey, conv=None):
    if not os.path.exists(duong_db(mkey)):
        return print(f"Chưa có hồ sơ nào cho {mkey} ({duong_db(mkey)}).")
    cn = mo(mkey)
    if conv:
        hs = doc(cn, conv)
        return print(json.dumps(hs, ensure_ascii=False, indent=1) if hs else "không thấy")
    rs = cn.execute("SELECT * FROM ho_so ORDER BY cap_nhat DESC LIMIT 40").fetchall()
    n = cn.execute("SELECT COUNT(*) c FROM ho_so").fetchone()["c"]
    print(f"\n═══ {n} hồ sơ trong {mkey} ═══\n")
    for r in rs:
        t = thieu(chi_truong(dict(r)), mkey)
        print(f"  {(r['ten_khach'] or '?')[:20]:22s} {r['buoc']:18s} "
              f"{'ĐỦ' if not t else 'thiếu ' + ','.join(t)}")


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "thu":
        _thu(a[1])
    elif len(a) >= 2 and a[0] == "xem":
        _xem(a[1], a[2] if len(a) > 2 else None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

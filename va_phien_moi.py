#!/usr/bin/env python3
"""Vá PHIÊN MỚI cho giá page đã báo — ca Najo Oiretuel · She Jewelry UAE 21/09/2026.

Khách nhắn page hồi 19/06–06/07 (quảng cáo VÒNG TAY, page báo "89 AED – 1 Bracelet / 139 AED – 2 Bracelets"),
21/09 bấm quảng cáo NHẪN mới hỏi "How much?" → AI: "89 AED for 1 bracelet, or 139 AED for 2 bracelets".
Kịch bản nhẫn đã về máy 21 giây trước đó; lỗi ở khối "GIÁ PAGE ĐÃ TỰ BÁO" (lục cả lịch sử, dặn "bảng mới
nhất thắng cả kịch bản") + bản ghi đưa model còn nguyên tin phiên cũ.

Cách dùng:  python3 va_phien_moi.py /opt/pancake-tool/ai_sale.py
Mỗi chỗ thay phải khớp ĐÚNG 1 lần, lệch là thoát KHÔNG ghi (phiên khác vừa sửa vùng đó → vá tay).
Chạy lại trên file đã vá thì tự từ chối.
"""
import os
import shutil
import sys
import time

f = sys.argv[1] if len(sys.argv) > 1 else "/opt/pancake-tool/ai_sale.py"
src = open(f, encoding="utf-8").read()
if "def dau_phien(msgs):" in src:
    sys.exit("đã vá rồi (có def dau_phien) — không làm gì")

THAY = []

# 1. Hàm mốc phiên — đặt ngay trước _tin_khach_con_hieu_luc (sau _moc_giay, _MO_PHIEN_MOI).
THAY.append(("\n\ndef _tin_khach_con_hieu_luc(msgs):\n", '''

# PHIÊN MỚI = khách bấm quảng cáo lại sau ≥ PHIEN_IM_GIAY im lặng — chủ shop 21/09, ca Najo Oiretuel · She
# Jewelry UAE (*"page này đã sửa kịch bản, bạn fix lại nhé"*): khách nhắn page hồi 19/06–06/07 (quảng cáo VÒNG
# TAY, page báo "89 AED – 1 Bracelet / 139 AED – 2 Bracelets"), 21/09 bấm quảng cáo NHẪN mới hỏi "How much?" →
# AI: "89 AED for 1 bracelet, or 139 AED for 2 bracelets". Kịch bản nhẫn đã về máy 21 GIÂY trước đó — lỗi ở khối
# "GIÁ PAGE ĐÃ TỰ BÁO" lục cả lịch sử, nhặt bảng vòng tay 3 tháng trước và dặn "bảng mới nhất thắng cả kịch bản";
# bản ghi đưa model cũng còn nguyên tin sale báo giá vòng tay. Đo 1.345 hội thoại 72 giờ (6 nước): 45 hội
# thoại mang bảng giá phiên cũ có con số KHÔNG có trong kịch bản hiện tại (Cloves Tea 2 set 169 — nay 159;
# Hair Repair KSA báo AED; Veloura còn là cái ví; Oman Gold "199 OMR"…). Ngưỡng 6 giờ: khách bấm lại quảng
# cáo trong vài giờ vẫn là một lần mua (đo: bấm lại < 6 giờ không có ca nào mang giá ngoài kịch bản).
PHIEN_IM_GIAY = 6 * 3600


def dau_phien(msgs):
    """Vị trí tin đầu của PHIÊN hiện tại trong msgs — 0 = cả đoạn là một phiên.

    Mốc = tin hệ thống "đã trả lời một quảng cáo" mà trước cụm tin của lần bấm đó (ad_click rỗng, câu chào
    tự động — cách mốc ≤ 120 giây) hội thoại đã im ≥ PHIEN_IM_GIAY. Phiên bắt đầu từ chính cụm tin ấy.
    """
    msgs = msgs or []
    dau = 0
    for i, m in enumerate(msgs):
        if m.get("boi") != "hethong" or not _MO_PHIEN_MOI.search(m.get("text") or ""):
            continue
        t0 = _moc_giay(m.get("luc"))
        if t0 is None:
            continue
        j = i - 1
        while j >= 0 and msgs[j].get("boi") == "hethong" and t0 - (_moc_giay(msgs[j].get("luc")) or t0) <= 120:
            j -= 1
        tj = _moc_giay(msgs[j].get("luc")) if j >= 0 else None
        if tj is not None and t0 - tj >= PHIEN_IM_GIAY:
            dau = j + 1
    return dau


def _tin_khach_con_hieu_luc(msgs):
'''))

# 2. gia_page_da_bao chỉ xét tin page trong PHIÊN hiện tại.
THAY.append(('''    so, cau = set(), []
    for m in msgs:
        t = m.get("text") or ""
        # 'hethong' = tin gửi hàng loạt''', '''    so, cau = set(), []
    for m in msgs[dau_phien(msgs):]:       # bảng giá phiên CŨ không tính (ca Najo 21/09 — xem dau_phien)
        t = m.get("text") or ""
        # 'hethong' = tin gửi hàng loạt'''))

# 3. goi_gia_page (bằng chứng giá) + ten_goi_km (tên ưu đãi mua-tặng) — tin báo giá gần nhất cũng phải trong phiên này.
THAY.append(('''    nguon = [m.get("text") or "" for m in reversed(msgs or []) if m.get("boi") in ("botcake", "nguoi")
             and "AI SALE" not in''',
             '''    nguon = [m.get("text") or "" for m in reversed((msgs or [])[dau_phien(msgs):]) if m.get("boi") in ("botcake", "nguoi")
             and "AI SALE" not in'''))
THAY.append(('''    nguon = [m.get("text") or "" for m in reversed(msgs or []) if m.get("boi") in ("botcake", "nguoi")]
''', '''    nguon = [m.get("text") or "" for m in reversed((msgs or [])[dau_phien(msgs):]) if m.get("boi") in ("botcake", "nguoi")]
'''))

# 4. Bản ghi đưa model: lược tin phiên cũ, thay bằng một dòng nhắc.
THAY.append(('''    dua = rec.get("msgs_prompt") or rec["msgs"][-40:]
''', '''    dua = rec.get("msgs_prompt") or rec["msgs"][-40:]
    # Tin PHIÊN CŨ không vào bản ghi (ca Najo Oiretuel 21/09 — xem dau_phien): khách quay lại bằng quảng cáo mới
    # sau ≥ 6 giờ im lặng thì sản phẩm / bảng giá phiên trước chỉ làm model lạc sang hàng cũ.
    _dp_ = dau_phien(dua)
    _cu_phien_ = [m for m in dua[:_dp_] if m["boi"] != "hethong"]
    dua = dua[_dp_:]
'''))
THAY.append(('''    hoi_thoai = "\\n".join(dong)
''', '''    hoi_thoai = "\\n".join(dong)
    if _cu_phien_:
        hoi_thoai = (f"(khách từng nhắn page — {len(_cu_phien_)} tin PHIÊN CŨ, tin cuối ngày "
                     f"{str(_cu_phien_[-1].get('luc') or '')[:10]}, đã lược: khách vừa bấm QUẢNG CÁO MỚI, sản phẩm / "
                     "giá / ưu đãi phiên cũ có thể đã đổi → sản phẩm và giá CHỈ theo KỊCH BẢN hiện tại và tin page "
                     "trong phiên này)\\n" + hoi_thoai)
'''))

# 5. Cổng gói/giá (luật 3b) — câu page/khách hợp thức hoá gói cũng chỉ trong phiên này.
THAY.append(('''                     cau_page=CG.cau_trong_hoi_thoai(msgs_luc_soan)[0] if msgs_luc_soan else None,
                     cau_khach=CG.cau_trong_hoi_thoai(msgs_luc_soan)[1] if msgs_luc_soan else None)''',
             '''                     cau_page=(CG.cau_trong_hoi_thoai(msgs_luc_soan[dau_phien(msgs_luc_soan):])[0]
                               if msgs_luc_soan else None),
                     cau_khach=(CG.cau_trong_hoi_thoai(msgs_luc_soan[dau_phien(msgs_luc_soan):])[1]
                                if msgs_luc_soan else None))'''))
THAY.append(('''                    _pg_g, _kh_g = CG.cau_trong_hoi_thoai(msgs)
''', '''                    _pg_g, _kh_g = CG.cau_trong_hoi_thoai(msgs[dau_phien(msgs):])
'''))
THAY.append(('''    pg, _ = CG.cau_trong_hoi_thoai(msgs)
''', '''    pg, _ = CG.cau_trong_hoi_thoai((msgs or [])[dau_phien(msgs):])
'''))

moi = src
for i, (a, b) in enumerate(THAY, 1):
    n = moi.count(a)
    if n != 1:
        sys.exit(f"❌ chỗ {i}: khớp {n} lần (cần đúng 1) — KHÔNG ghi gì. Đoạn: {a[:90]!r}")
    moi = moi.replace(a, b)

compile(moi, f, "exec")
bak = f"{f}.bak-{time.strftime('%Y%m%d-%H%M')}-truoc-phien-moi"
shutil.copy2(f, bak)
tam = f"{f}.tam-{os.getpid()}"
open(tam, "w", encoding="utf-8").write(moi)
os.replace(tam, f)
print(f"✅ đã vá {len(THAY)} chỗ · bak: {bak}")

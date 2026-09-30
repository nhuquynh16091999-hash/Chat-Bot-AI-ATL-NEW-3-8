#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm tra luật SĐT (phan_loai_sdt) — chạy: python3 test_sdt.py

Ca kiểm lấy từ ĐƠN THẬT trên POS (số hiệu đơn ghi ngay cạnh) nên đừng sửa cho "đẹp":
mỗi dòng là một cách khách gõ số đã từng làm treo/lọt đơn. Thêm ca mới khi gặp
kiểu gõ lạ, và chạy lại file này mỗi lần đụng vào luật SĐT."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_len_don as A


def dat(key):
    A.MK = dict(A.MARKETS[key], key=key)
    A.PHONE_RE = re.compile(A.MK["sdt_regex"])
    A._DAI_BAN_DIA.clear()


# (thị trường, số gõ vào, loại mong đợi, số chuẩn mong đợi hoặc None = không kiểm)
CA = [
    # --- UAE: số bản địa mọi kiểu gõ
    ("uae", "0501234567", "ban_dia", "0501234567"),
    ("uae", "+971 50 123 4567", "ban_dia", "0501234567"),
    ("uae", "00971501234567", "ban_dia", "0501234567"),
    ("uae", "971501234567", "ban_dia", "0501234567"),
    # --- UAE: số Philippines (luật mới) — mọi cách gõ về cùng một số có mã nước
    ("uae", "+639171234567", "ngoai", "+639171234567"),
    ("uae", "09171234567", "ngoai", "+639171234567"),
    ("uae", "639171234567", "ngoai", "+639171234567"),
    ("uae", "0063 917 123 4567", "ngoai", "+639171234567"),
    ("uae", "+63 917 123 4567", "ngoai", "+639171234567"),
    # --- UAE: số nước khác có mã nước rõ ràng
    ("uae", "+201528787263", "ngoai", "+201528787263"),
    ("uae", "+919876543210", "ngoai", "+919876543210"),
    # --- UAE: ca hỏng THẬT trên POS (phải TIẾP TỤC bị giữ, đừng nhận bừa)
    ("uae", "05093076604", "hong", None),          # #47484 thừa 1 số
    ("uae", "056590326", "hong", None),            # #47452 thiếu 1 số
    ("uae", "01528787263", "hong", None),          # #47417 số Ai Cập gõ kiểu bản địa, không có mã nước
    ("uae", "056311892", "hong", None),            # #47370 thiếu 1 số
    # --- SAUDI: bẫy gõ nhầm mã nước (ca thật) — KHÔNG được đọc thành khách nước ngoài
    ("saudi", "996506990937", "hong", None),       # #69031: 996 <-> 966
    ("saudi", "09630556838034", "hong", None),     # #69367: 963 <-> 966
    ("saudi", "0386685425", "hong", None),         # #68700
    ("saudi", "056399107", "hong", None),          # #68724 thiếu 1 số
    ("saudi", "0501234567", "ban_dia", "0501234567"),
    ("saudi", "+971501234567", "ngoai", "+971501234567"),   # khách UAE thật, không phải gõ nhầm
    ("saudi", "+639171234567", "ngoai", "+639171234567"),
    # --- KUWAIT: dải 41xxxxxx là số Kuwait THẬT (14 đơn/90 ngày, 8 đơn đã giao)
    ("kuwait", "41170224", "ban_dia", "41170224"),
    ("kuwait", "41030110", "ban_dia", "41030110"),
    ("kuwait", "60425184", "ban_dia", "60425184"),
    ("kuwait", "96599433139", "ban_dia", "99433139"),
    ("kuwait", "22203032", "ban_dia", "22203032"),
    ("kuwait", "639544632639", "ngoai", "+639544632639"),   # #13489 số Philippines
    ("kuwait", "09163497868", "ngoai", "+639163497868"),    # #13443
    ("kuwait", "9651643416", "hong", None),                 # #13864 thiếu 1 số
    ("kuwait", "9901033869", "hong", None),                 # #13861 rác
    ("kuwait", "9655680636", "hong", None),                 # #13262 thiếu 1 số
    # --- SPAIN: điện thoại BÀN Tây Ban Nha, không phải +98 Iran
    ("spain", "981299245", "hong", None),          # #1586/#1554
    ("spain", "0392450555", "hong", None),         # số Việt Nam gõ kiểu bản địa -> không đoán bừa
    ("spain", "+84392450555", "ngoai", "+84392450555"),
    ("spain", "655357145", "ban_dia", "655357145"),
    ("spain", "+34655357145", "ban_dia", "655357145"),
    ("spain", "60170197", "hong", None),           # #1677 thiếu số
    # --- ROMANIA
    ("romania", "0721234567", "ban_dia", "0721234567"),
    ("romania", "0964170123", "hong", None),       # #523
    ("romania", "072667956", "hong", None),        # #573 thiếu 1 số
    # --- ĐÀI LOAN / NHẬT: số bản địa 09… KHÔNG được đọc thành số Philippines
    ("taiwan", "0912345678", "ban_dia", "0912345678"),
    ("taiwan", "+88662716476", "hong", None),      # #248
    ("japan", "09012345678", "ban_dia", "09012345678"),
    ("japan", "08012345678", "ban_dia", "08012345678"),
    # --- MỸ
    ("usa", "2125551234", "ban_dia", "2125551234"),
    ("usa", "+12125551234", "ban_dia", "2125551234"),
    # GIỚI HẠN ĐÃ BIẾT: ở thị trường Mỹ, '09171234567' bỏ số 0 đi là '9171234567' — 917 là
    # mã vùng New York thật nên khuôn Mỹ khớp trước. Số bản địa luôn được ưu tiên, không
    # đọc thành số Philippines (đổi thứ tự sẽ phá đơn Mỹ thật).
    ("usa", "09171234567", "ban_dia", "9171234567"),
    # --- QATAR / OMAN / BAHRAIN (bahrain cũng BẮT BUỘC số bản địa như kuwait)
    ("qatar", "55123456", "ban_dia", "55123456"),
    ("qatar", "+639171234567", "ngoai", "+639171234567"),
    ("oman", "91234567", "ban_dia", "91234567"),
    ("bahrain", "36123456", "ban_dia", "36123456"),
    ("bahrain", "66991146", "ban_dia", "66991146"),          # #954 đã đặt hàng
    ("bahrain", "+97334309685", "ban_dia", "34309685"),      # #933 đã gửi hàng
    ("bahrain", "+639171234567", "ngoai", "+639171234567"),  # số ngoại -> doc_don sẽ treo đơn
    ("bahrain", "50192822", "hong", None),                   # #941 đầu 5, chưa từng giao xong
]

sai = 0
for mkt, so, mong, chuan_mong in CA:
    dat(mkt)
    loai, chuan, mo_ta = A.phan_loai_sdt(so)
    ok = loai == mong and (chuan_mong is None or chuan == chuan_mong)
    if not ok:
        sai += 1
    print(f"{'  ' if ok else '✖ '}{mkt:8s} {so!r:22s} -> {loai:8s} {chuan!r:16s} {mo_ta[:60]}"
          + ("" if ok else f"   ⟵ MONG ĐỢI {mong} {chuan_mong!r}"))

print(f"\n{len(CA) - sai}/{len(CA)} đúng")

# --- Bắt số nước ngoài trong tin nhắn chat (luồng đơn Facebook)
print("\n--- SDT_UNG_VIEN_RE + phan_loai_sdt trên tin chat ---")
dat("uae")
CHAT = [
    ("Hi po, my number is 0917 123 4567 thank you", "+639171234567"),
    ("+63 926 555 1234 send it here", "+639265551234"),
    ("my whatsapp 00639171234567", "+639171234567"),
    ("Order total 149 AED delivered on 12.03.2024 15:30", None),
    ("Tracking 1234567890123 arrived", None),
    ("call me 0501234567", None),          # số bản địa -> nhánh này không nhận (PHONE_RE lo)
]
for text, mong in CHAT:
    ra = [s for s in (A.phan_loai_sdt(u) for u in A.SDT_UNG_VIEN_RE.findall(text))
          if s[0] == "ngoai"]
    duoc = ra[-1][1] if ra else None
    print(f"{'  ' if duoc == mong else '✖ '}{text!r:55s} -> {duoc!r}")
    if duoc != mong:
        sai += 1

# --- Thị trường nào BẮT BUỘC số bản địa (số ngoại -> để 'Mới', không tự xác nhận)
# Ghim danh sách ở đây để sửa markets.json nhầm là lộ ngay: user chốt Kuwait (2026-08-23)
# và Bahrain (2026-08-24) — hãng vận chuyển hai nước này không nhận số nước khác.
print("\n--- Thị trường bắt buộc số bản địa ---")
CHAT_CHE = {"kuwait", "bahrain"}
dang_co = {k for k, m in A.MARKETS.items() if m.get("sdt_bat_buoc_ban_dia")}
print(f"{'  ' if dang_co == CHAT_CHE else '✖ '}markets.json: {sorted(dang_co)}"
      + ("" if dang_co == CHAT_CHE else f"   ⟵ MONG ĐỢI {sorted(CHAT_CHE)}"))
if dang_co != CHAT_CHE:
    sai += 1

sys.exit(1 if sai else 0)

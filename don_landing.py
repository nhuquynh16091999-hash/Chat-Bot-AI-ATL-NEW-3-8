#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TỰ ĐỘNG XỬ LÝ ĐƠN LANDING PAGE (Webcake) ĐỔ VỀ POS — thuần luật, không cần AI.

Đơn landing page về POS đã có sẵn: tên khách, SĐT, sản phẩm + số lượng, tiền COD.
Thứ DUY NHẤT còn thiếu là ĐỊA CHỈ: Webcake nhét toàn bộ form (địa chỉ + dòng ưu đãi)
vào phần GHI CHÚ, còn ô địa chỉ giao hàng để trống -> đơn không đẩy được sang vận chuyển,
nhân viên phải chép tay từng đơn.

Tool này làm đúng việc nhân viên đang làm tay:
  1. Đọc ghi chú -> tách các dòng địa chỉ (phần trước dòng ưu đãi có giá tiền)
  2. Dò tỉnh/thành (khớp tên -> viết tắt -> gần đúng) rồi điền ô địa chỉ giao hàng
  3. Chuẩn hóa SĐT (thêm số 0 / bỏ mã nước)
  4. Thiếu tiền COD thì lấy giá từ dòng ưu đãi; thiếu sản phẩm thì dò theo tên trên dòng ưu đãi
  5. Gắn đơn vị vận chuyển của thị trường; khớp hết thì tự "Đã xác nhận" rồi "Chờ in"
  6. Nghi trùng SĐT / thiếu dữ liệu / lệch số -> VẪN điền địa chỉ nhưng ĐỂ "Mới" + ghi chú rõ lý do

BẢNG QUYẾT ĐỊNH ĐƠN TRÙNG (chốt với user 2026-08-20 — đây là nguồn duy nhất, đừng
hỏi lại user những ca đã có ở đây). Nhóm trùng = cùng shop + (cùng SĐT HOẶC cùng
địa chỉ) + CÙNG MÃ SẢN PHẨM, gộp cả nguồn landing lẫn Facebook:

  Đơn đối chiếu cùng SĐT/địa chỉ ...        -> xử lý đơn landing đang xét
  ─────────────────────────────────────────────────────────────────────────────
  (đơn ĐANG XÉT bán hàng TEST)              -> chỉ chuyển 'Chờ hàng', không so trùng
  không có                                  -> LÊN ĐƠN, chuyển Chờ in
  khác mã SP                                -> LÊN ĐƠN, chỉ ghi chú
  là đơn SP TEST (la_don_test)              -> bỏ khỏi phép so, LÊN ĐƠN
  trống dòng SP nhưng ghi chú Webcake có
      mã ('217|Buy 1…', ma_tu_note) hoặc
      UTM có mã ('TinDV/256 - …', ma_sp_utm) -> so mã như thường (trùng thì HỦY)
  trống dòng SP, không đọc nổi mã           -> TREO 'Mới', KHÔNG hủy
  'Đã xác nhận' mà TRỐNG ô địa chỉ, chưa
      từng vào hàng in, nằm im >= 7 ngày
      (don_ket — nó không giao được)        -> KHÔNG tính là đơn đã đi: đơn đầy đủ
                                               ĐI THAY, bản chết bị HỦY (landing)
                                               / CHỈ GHI CHÚ, giữ nguyên trạng thái
                                                 (Facebook — user chốt 2026-08-30)
  Đã nhận/Đã thu tiền + đơn này tạo SAU
      mốc nhận hàng (moc_da_nhan)           -> ĐẶT LẠI THẬT, LÊN ĐƠN
  Đã nhận/Đã thu tiền + tạo TRƯỚC mốc đó    -> TRÙNG, HỦY
  Đã hoàn / Đang hoàn / Hoàn một phần       -> TRÙNG, HỦY
  trạng thái khác ngoài Mới/Chờ xác nhận    -> TRÙNG, HỦY
  cả nhóm còn 'Mới'                         -> giữ bản địa chỉ đầy đủ nhất; bản
                                               landing còn lại HỦY, bản Facebook
                                               CHỈ GHI CHÚ (để nguyên 'Mới')

  Đơn TỪNG vào hàng in (status_history có 12/13) VẪN HỦY như mọi đơn trùng khác
  (user chốt 2026-08-20, đảo lại chốt cũ), chỉ ghi chú to để kho rút phiếu đã in.
  LƯU Ý: POS KHÔNG khôi phục được đơn đã hủy qua API — sai thì phải bật tay trong UI.

LUẬT SĐT (user chốt 2026-09-04, ĐẢO luật 24/08): SĐT hỏng KHÔNG còn là lý do hủy đơn —
máy chỉ TREO 'Mới' + ghi lý do, để vận đơn/nhân viên kiểm rồi quyết. Luật 24/08 cho hủy
vì "gọi không được là hết đường hỏi lại khách", nhưng cái quyết định "gọi không được"
chỉ là khuôn regex của thị trường, mà khuôn đó CHỈ NHẬN DI ĐỘNG — số cố định hợp lệ và
số nước ngoài viết kiểu bản địa đều rơi vào ô "hỏng". Ca thật: #1754 (Spain) bị hủy vì
981299245 không khớp khuôn di động 6x/7x, trong khi CHÍNH SỐ ĐÓ đã nhận hàng ở #1554.

NGOẠI LỆ NGƯỢC LẠI — số 'hỏng' mà CHÍNH SỐ ĐÓ đã có đơn GIAO THÀNH CÔNG (don_da_giao_cua_sdt)
thì lên đơn BÌNH THƯỜNG, không treo: bằng chứng giao được tận tay thắng khuôn regex.
Đơn FACEBOOK vẫn như cũ (auto_len_don chỉ để 'Mới' + ghi lý do, không bao giờ hủy).

Đơn đủ dữ liệu chạy thẳng Mới -> Đã xác nhận -> Chờ in; đơn thiếu để "Mới" cho người xử lý.
Riêng đơn bán HÀNG TEST ('SP TEST', 'Test', 'N/A'…) chỉ đẩy lên 'Chờ hàng' — không xác
nhận, không vào 'Chờ in' (luật user 2026-08-21).

Lệnh:
  python3 don_landing.py chay [thị trường] [--thu] [--ngay 3] [--khong-xac-nhan] [--lam-lai]
        --thu             chỉ in ra sẽ làm gì, KHÔNG sửa đơn thật
        --ngay N          chỉ xử lý đơn về trong N ngày gần đây (mặc định 3)
        --khong-xac-nhan  chỉ điền địa chỉ/SĐT/COD, để nhân viên tự bấm xác nhận
        --lam-lai         xử lý lại cả đơn đã ghi trong state (dùng khi đổi luật)
  python3 don_landing.py xem <mã đơn> <thị trường>   # xem tool đọc ra gì từ 1 đơn, không sửa
  python3 don_landing.py mot <mã đơn> <thị trường>   # xử lý THẬT đúng 1 đơn (để kiểm chứng)
  python3 don_landing.py soat [thị trường] [--ngay 30] [--ghi-chu]
        --ghi-chu         gõ chuông 📪 ngay trên đơn thừa CÒN RÚT ĐƯỢC (chưa rời kho)
        --huy             HỦY luôn đơn thừa còn rút được (luật user: đơn cũ chưa giao xong
                          / chưa hoàn thì bản sau là trùng). Không đụng đơn đã rời kho,
                          không hủy khi bản GIỮ đang nằm chết, và không hủy khi bản thừa
                          ĐỨNG XA HƠN bản giữ trong luồng (BAC_LUONG). Lịch dùng cả 2 cờ.
        RÀ NGƯỢC, chỉ đọc: nhóm nào cùng khách + cùng mã SP mà >1 đơn ĐƯỢC ĐI thì hiện ra.
        Bắt chiều THẢ OAN (hàng đi thật, khách nhận 2 kiện) — chiều mà mọi đợt đo trước
        đây bỏ sót. Chạy sau mỗi lần đổi luật trùng, và nên chạy định kỳ.
  python3 don_landing.py daemon [--giay 60]          # chạy liên tục (auto_len_don daemon đã gọi sẵn)
"""

import calendar
import difflib
import json
import os
import re
import sys
import time
import unicodedata

import pancake_order as P
import quet_hoi_thoai as Q
import auto_len_don as A

# Webcake = trình tạo landing page của Pancake; đơn từ landing page có order_sources = "-7"
NGUON_LANDING = "-7"

# Luồng của shop: Mới -> Đã xác nhận -> Chờ in (nhân viên in rồi mới đóng hàng)
TT_XAC_NHAN = 1
TT_CHO_IN = 12
# Chỗ đậu của đơn HÀNG TEST — không phải đơn của khách nên không cho vào hàng in
TT_CHO_HANG = 11
# Đơn còn nằm im, chưa ai cho đi. Ngoài 2 nấc này coi như thương vụ ĐANG/ĐÃ đi.
TT_CHUA_DI = {0, 17}
TT_HUY = 6
# Thương vụ ĐÃ XONG — khách cầm hàng rồi. Đơn mới cùng sản phẩm sau đó là KHÁCH ĐẶT LẠI,
# không phải bản gửi lặp -> vẫn lên đơn bình thường (luật user).
TT_DA_GIAO_XONG = {3, 16}
# Thương vụ ĐÃ HOÀN — hàng đã quay về. Đơn mới cùng sản phẩm SAU mốc hoàn cũng là KHÁCH
# ĐẶT LẠI thật, không phải bản gửi lặp (luật user 2026-08-24, mở rộng ngoại lệ của
# TT_DA_GIAO_XONG sang cả ca hoàn hàng).
TT_DA_HOAN = {4, 5, 15}
# Đơn đậu ở các nấc này mà ô địa chỉ vẫn trống quá NGAY_KET ngày = nằm chết, xem don_ket().
# Chỉ hai nấc NGƯỜI bấm rồi bỏ dở, chưa giao cho kho: 'Đã xác nhận' và 'Chờ hàng'.
TT_CO_THE_KET = {TT_XAC_NHAN, TT_CHO_HANG}
NGAY_KET = 7

# BẬC TRONG LUỒNG — bản nào đứng CAO hơn là bản đang thật sự chạy về phía khách. Dùng để
# chọn BẢN GIỮ khi rà trùng (soat_thoat_luoi), KHÔNG dùng để quyết nhóm nào là trùng.
# Vì sao phải có (ca thật 09/09/2026, UAE 0521003473): máy tự tạo #49394 lúc 15:54 rồi
# dừng ở 'Đã xác nhận' (auto_len_don không bao giờ đẩy tiếp), sale Hiền Nguyễn tạo #49395
# lúc 15:55 và đưa thẳng lên 'Chờ in'. Bản rà cũ lấy nhom[0] = đơn TẠO SỚM NHẤT làm bản
# giữ nên nó HỦY đúng cái đơn đang chạy (#49395) và giữ lại bản kẹt (#49394) — job0 chỉ
# quét status 12 nên đơn giữ không bao giờ được đẩy: khách không nhận được gì, mà log thì
# báo "đã hủy 1 đơn trùng" nghe như vừa làm việc tốt.
# Cửa lên đơn (xet_nhom_trung) vốn đã theo đúng doctrine này — "đơn đã có người xử lý là
# bản được đi", "không quan tâm tạo trước hay sau" — chỉ bộ rà ngược là lệch.
# HOÀN xếp THẤP (dưới cả 'Đã xác nhận'): hàng đã quay về thì thương vụ đó chết, giữ nó mà
# hủy bản đang bay là khách chẳng nhận được gì (ca SAUDI #70060 'Đang hoàn' vs #70208 —
# lần đó thoát vì #70208 đã rời kho nên không nằm trong TT_CON_RUT).
BAC_LUONG = {
    0: 0, 17: 0,             # Mới / Chờ xác nhận — chưa ai cho đi
    4: 1, 15: 1, 5: 1,       # Đang hoàn / Hoàn một phần / Đã hoàn — hàng đã quay về
    TT_CHO_HANG: 2,          # Chờ hàng — chỗ đậu đơn test / đơn bỏ dở
    TT_XAC_NHAN: 3,          # Đã xác nhận — đã chốt nhưng CHƯA bàn giao cho vận đơn
    TT_CHO_IN: 4, 13: 5,     # Chờ in -> Đã in: vận đơn đã nhận
    8: 6, 9: 7,              # Đang đóng hàng -> Chờ chuyển hàng
    2: 8,                    # Đã gửi hàng — hàng rời kho
    3: 9, 16: 9,             # Đã nhận / Đã thu tiền — khách cầm hàng rồi
}


def bac_luong(k):
    """Bậc trong luồng của đơn `k` (xem BAC_LUONG). Trạng thái lạ coi như thấp nhất."""
    return BAC_LUONG.get(k.get("status"), 0)

# Số ngày mặc định chỉ xử lý đơn MỚI VỀ (đơn tồn lâu ngày để nhân viên quyết, xem --ngay)
NGAY_MAC_DINH = 3
# Cửa sổ quét đơn cũ để chống trùng SĐT
NGAY_CHONG_TRUNG = 14
# Hỏi thẳng POS theo SĐT thì rẻ nên soi xa hơn — khách gửi lặp có khi cách nhau cả tháng
NGAY_TIM_SDT = 30
# Cửa sổ tra LỊCH SỬ GIAO THÀNH CÔNG của một SĐT (don_da_giao_cua_sdt). Rộng hơn hẳn cửa sổ
# chống trùng: số giao được từ mấy tháng trước thì hôm nay vẫn gọi được.
NGAY_LICH_SU_GIAO = 180

# Dòng do hệ thống/tool khác nối thêm vào ghi chú — cắt từ đây trở đi, không phải địa chỉ
DONG_HE_THONG = re.compile(r"^(-{3,}|📋|🚚|✅|⚠|\[Tự động)")
# Ghi chú đã bị máy sàng lọc treo lại -> tuyệt đối không tự xác nhận
RE_TREO = re.compile(r"SÀNG LỌC|TREO", re.I)
# Hãng vận chuyển nối log giao hàng vào ghi chú ('delivery scan | [02Deira] has operated
# an abnormal parcel scan…'). Đọc mấy dòng này thành địa chỉ là dò ra TÊN KHO của J&T
# chứ không phải nhà khách (đơn #46651: kho '01International city' ở Dubai trong khi
# khách ở Abu Dhabi).
DONG_DVVC = re.compile(r"parcel scan|delivery scan|abnormal parcel|scheduled to \[|"
                       r"'s courier|courier\s+\w+.*\(\+?\d", re.I)
# Dòng khách điền cho có: 'N/A', '-', 'none'... — cả phần số nhà/đường mà toàn thế này
# thì đơn không giao được, phải để người gọi khách hỏi lại.
RAC_DONG = re.compile(r"^[\W_]*(n\s*/?\s*a|na|none|null|nil|no|x+|test)[\W_]*$", re.I)
# Tên HÀNG TEST trong POS: 'SP TEST', 'Test', 'San pham test', 'Test product'…
TEN_TEST = re.compile(r"[\W_]*(sp|san\s*pham|product|hang)?[\W_]*test[\W_]*"
                      r"(sp|san\s*pham|product|hang)?[\W_]*", re.I)
# LUẬT USER 2026-09-02: "có chữ test là chờ hàng" — nguyên TỪ 'test' ở BẤT KỲ ĐÂU trong
# phần khách điền (kể cả dòng mẫu mã 'Test Red|Red') là đủ để coi đơn là hàng test. Bản
# cũ chỉ khớp CẢ tên nên 'Test Red' trượt: #6291/#6299 Qatar chỉ thoát nhờ Webcake tình
# cờ gán kèm dòng hàng 'SP TEST' — bỏ dòng đó ra là tool coi như đơn khách thật rồi đem
# đi xác nhận. Giữ ranh giới từ (\b) để hàng bán thật lỡ mang chuỗi đó ('Latest',
# 'Protest', 'Testa') vẫn lên đơn bình thường — đo 4917 đơn/11 thị trường/30 ngày:
# bắt thêm đúng 4 đơn (3 đơn test nội bộ Tây Ban Nha + 1 đơn chat Bahrain), 0 đơn oan.
TU_TEST = re.compile(r"\btest\b", re.I)
# Từ đứng sau tên đường — cụm ngay trước nó là ĐƯỜNG chứ không phải quận/phường
TU_CHI_DUONG = {"road", "street", "st", "rd", "ave", "avenue", "way", "blvd", "boulevard",
                "strada", "calle", "carrer", "bulevardul", "aleea"}

# Viết tắt tỉnh/thành khách hay gõ trên form (chỉ nhận khi cả dòng đúng bằng viết tắt)
# Viết tắt tiểu vương quốc. Ngoài mấy mã sân bay/quen tay (dxb, auh, shj...), form
# Webcake còn đổ về MÃ ISO 3166-2:AE hai chữ ở dòng cuối — 'AZ', 'SH', 'RK'... Tool
# không biết mấy mã này nên đơn nằm lại 'Mới' với lý do THIẾU TỈNH/THÀNH dù địa chỉ
# thừa dữ liệu (đơn #47181, #47084, #47079, #47077, #47072...).
# Chỉ khớp khi CẢ DÒNG đúng bằng mã, nên 2 chữ cũng không đụng nhầm tên đường.
VIET_TAT = {
    "uae": {"du": "971_3", "dxb": "971_3", "auh": "971_1", "shj": "971_6",
            "ajm": "971_2", "rak": "971_5", "uaq": "971_7", "fuj": "971_4",
            "az": "971_1",     # AE-AZ Abu Dhabi
            "aj": "971_2",     # AE-AJ Ajman
            "fu": "971_4",     # AE-FU Fujairah
            "rk": "971_5",     # AE-RK Ras Al Khaimah
            "sh": "971_6",     # AE-SH Sharjah
            "uq": "971_7"},    # AE-UQ Umm Al Quwain
}

RE_TIEN = []          # regex bắt giá tiền của thị trường hiện tại
_MKEY = None


def _chuan_bi_regex(mkey):
    """Dựng regex tiền tệ theo thị trường (gọi sau A.set_market)."""
    global RE_TIEN, _MKEY
    words = A.MK.get("tu_tien_te") or ""
    RE_TIEN = [re.compile(r"(\d[\d.,]*)\s*(?:" + words + r")(?![a-z0-9])", re.I)]
    # Chữ tiền viết TRƯỚC số ("SAR 109Free shiping"). Landing `nail-repair-serum-sa`
    # đổi cách viết ưu đãi trong ngày 03/09/2026 (#71657 lúc 00:47 còn "109 SAR",
    # #71821 lúc 18:44 đã thành "SAR 109"): vế số-đứng-trước ở trên không đọc ra giá,
    # kéo theo tool KHÔNG dám sửa số lượng rác (SL = mã SP 252) và KHÔNG điền COD, đơn
    # nằm chết ở 'Mới'. Đây là cách viết bình thường của tiếng Anh nên phải đọc được ở
    # MỌI thị trường, không riêng Saudi.
    # Vì sao chặt hơn vế trên: mã tiền Ả Rập rất ngắn ('sr', 'bd', 'kd', 'qr') nên phải
    #  • (?<![a-z0-9]) — không dính vào giữa/cuối một từ khác;
    #  • \s{0,2} — số phải LIỀN sau chữ tiền (nhiều nhất 2 dấu cách; landing gõ cả
    #    "SAR 109" lẫn "SAR  159"), để dòng địa chỉ kiểu
    #    'Al Kadi sr, villa 12' không bị chấm nhầm thành dòng ưu đãi rồi nuốt luôn
    #    phần địa chỉ đứng sau nó.
    # Hồi quy 9.616 đơn thật/12 thị trường: đổi kết quả 25 đơn, TẤT CẢ đều theo hướng
    # 'cũ không đọc ra giá -> mới đọc ra ĐÚNG giá', KHÔNG đơn nào bị đổi giá hay bị
    # chấm nhầm dòng ưu đãi (cửa chặn: 0 đơn đổi theo hướng nguy hiểm). 19 đơn trong đó
    # có chữ 'test' và đã nằm ở 'Chờ hàng' (11) — la_don_test() đọc thẳng ghi chú, không
    # qua RE_TIEN, nên không đổi gì; tool cũng chỉ quét TT_CHUA_DI = {0, 17}. 4 đơn còn
    # sống là #71873, #71821 ("SAR 109") và #71820, #71785 ("SAR  159").
    RE_TIEN.append(re.compile(r"(?<![a-z0-9])(?:" + words + r")\s{0,2}(\d[\d.,]*)", re.I))
    if A.MK.get("ky_hieu_truoc"):
        sym = A.MK["ky_hieu_truoc"]
        RE_TIEN.append(re.compile(r"(?:" + sym + r")\s*(\d[\d.,]*)"))
        # Châu Âu viết ký hiệu SAU số ("29 €") — thiếu vế này là cả thị trường
        # Tây Ban Nha không đọc ra giá, kéo theo mất luôn dòng ưu đãi.
        RE_TIEN.append(re.compile(r"(\d[\d.,]*)\s*(?:" + sym + r")"))
    _MKEY = mkey


def state_file():
    return os.path.join(A.BASE_STATE, _MKEY, "landing_da_xu_ly.json")


# Đơn còn nằm 'Mới' được xét lại sau ngần này giờ. Trước đây xử lý một lần là đánh dấu
# VĨNH VIỄN, nên đơn treo vì thiếu dữ liệu / vì bản trùng chưa đi thì nằm chết ở đó —
# bản trùng đi rồi cũng không ai hủy nó, luật vá xong cũng không áp lại được, phải có
# người gõ --lam-lai. Đó là lý do user phải soi POS mỗi ngày.
GIO_XET_LAI = 6


# Người sửa đơn SAU lần tool xét cuối -> xét lại ngay, không đợi đủ GIO_XET_LAI. Ca thật
# SAUDI #74247/#74251 (15/09/2026): tool treo vì "không có số điện thoại" lúc 08:15 VN,
# nhân viên điền SĐT lúc 08:46 mà tới 14:15 đơn mới được xét lại. Chừa 120 giây vì chính
# lượt ghi của tool cũng đẩy updated_at (trước khi ghi 'luc') và đồng hồ POS/VPS lệch nhau.
GIAY_SUA_SAU = 120


# LUẬT CHỦ SHOP 29/09/2026 (XN_KHACH_2909): đơn landing CHỈ lên Chờ in khi khách đã xác
# nhận qua WhatsApp hoặc Messenger; chưa xác nhận thì đủ dữ liệu cũng để nguyên 'Mới'.
# Dấu hiệu xác nhận = thẻ đơn POS 'XN QUA WA' / 'XN QUA MESS' (the_nuoc_wa.py gắn) hoặc Ghi
# chú in 'CARE ĐƠN QUA MESS' (landing_vao_chat.py ghi). Shop chưa tạo 2 thẻ đó thì mọi đơn
# landing của shop nằm 'Mới' chờ nhân viên.
THE_KHACH_XN = {"XN QUA WA", "XN QUA MESS"}
KQ_CHO_XN = "để Mới — chờ khách xác nhận qua WhatsApp/Mess"


def khach_da_xn(o):
    ten = {str(t.get("name") or "").strip().upper()
           for t in (o.get("tags") or []) if isinstance(t, dict)}
    return bool(ten & THE_KHACH_XN) or "CARE ĐƠN QUA MESS" in str(o.get("note_print") or "").upper()


def _can_xet_lai(rec, o=None):
    """Có phải xử lý lại đơn này không (rec = bản ghi trong landing_da_xu_ly.json)."""
    if not rec:
        return True                                  # chưa đụng bao giờ
    if str(rec.get("ket_qua") or "").startswith(KQ_CHO_XN) and o and khach_da_xn(o):
        return True                                  # XN_KHACH_2909 — khách vừa xác nhận
    if str(rec.get("ket_qua") or "").startswith(("đã hủy", "đã xác nhận", "hàng test")):
        return False                                 # dứt điểm rồi, không đụng nữa
    try:
        luc = time.mktime(time.strptime(rec.get("luc") or "", "%Y-%m-%d %H:%M:%S"))
    except (ValueError, TypeError):
        return True
    try:
        # updated_at của POS là giờ UTC không kèm múi ('2026-09-15T01:46:26.557719'),
        # còn 'luc' ghi theo giờ máy chạy tool -> quy cả hai về epoch rồi mới so.
        sua = calendar.timegm(time.strptime(str((o or {}).get("updated_at"))[:19],
                                            "%Y-%m-%dT%H:%M:%S"))
        if sua > luc + GIAY_SUA_SAU:
            return True
    except (ValueError, TypeError):
        pass
    return time.time() - luc >= GIO_XET_LAI * 3600


# ---------------- Đọc ghi chú của Webcake ----------------

def tim_gia(text):
    for rx in RE_TIEN:
        m = rx.search(text)
        if m:
            return P.parse_money(m.group(1))
    return None


def tach_note(note):
    """Ghi chú Webcake = các dòng địa chỉ, rồi tới dòng ưu đãi (có giá tiền), rồi dòng mẫu mã.
    Trả (các dòng địa chỉ, dòng ưu đãi)."""
    lines = []
    for raw in re.split(r"[\r\n]+", note or ""):
        s = raw.strip()
        if not s:
            continue
        if DONG_HE_THONG.match(s):
            break                      # phần do hệ thống nối thêm, không còn là form khách điền
        lines.append(s)
    idx = next((i for i, s in enumerate(lines) if tim_gia(s) is not None), None)
    dia_chi = lines[:idx] if idx is not None else lines
    dia_chi = [d for d in (don_dep_dong(x) for x in dia_chi) if d]
    return dia_chi, (lines[idx] if idx is not None else None)


# Shopify (xophia-2.myshopify.com, đổ vào shop Romania từ 18/09/2026): ghi chú chỉ MỘT
# dòng "Shopify COD | Variant: BROWN | SKU: 221-3 | SL: 1 | URL: …" — không có dòng địa
# chỉ, không có dòng ưu đãi kèm giá. Địa chỉ khách gõ nằm sẵn ở ô địa chỉ giao (chưa có
# tỉnh/quận), tiền thu nằm ở ô `cod` chứ không ở phí chuyển. Khuôn Webcake trượt hết nên
# 4 đơn đầu (#704/#705/#707/#708) TÀNG HÌNH với tool: không log, không ghi chú, nằm 'Mới'.
RE_SHOPIFY = re.compile(r"^\s*Shopify\s+COD\b", re.I)


def la_shopify(o):
    return bool(RE_SHOPIFY.match(o.get("note") or ""))


def dong_dia_chi_shopify(o):
    """Ô địa chỉ giao của đơn Shopify tách theo dấu phẩy — 2 phần cuối là thành phố + hạt,
    đúng thứ tự dòng địa chỉ của form Webcake nên dùng chung được bộ dò tỉnh/quận.
    Đọc `address` chứ không đọc `full_address`: tool không bao giờ ghi đè `address`,
    còn `full_address` bị POS nối thêm tên tỉnh/quận sau khi mình điền."""
    dc = (o.get("shipping_address") or {}).get("address") or ""
    return [d for d in (don_dep_dong(x.strip()) for x in dc.split(",")) if d]


def don_dep_dong(s):
    """Bỏ dòng rác (chỉ có SĐT, email, log ĐVVC) và tiền tố mã tỉnh kiểu '1173:ABU DHABI'."""
    s = re.sub(r"^\d{3,6}\s*:\s*", "", s).strip()
    if DONG_DVVC.search(s):
        return ""                      # log của hãng vận chuyển, không phải khách điền

    if re.fullmatch(r"[\d\s+\-().]{7,}", s):
        return ""                      # cả dòng chỉ là số điện thoại
    if re.fullmatch(r"\S+@\S+\.\S+", s):
        return ""
    return s


_QUAN_HUYEN = {}         # {thị trường: [(province_id, [khóa tên quận/huyện])]}


def bang_quan_huyen():
    """Bảng tên quận/huyện -> tỉnh cha (tải 1 lần, cache ra state/<mkt>/districts.json).

    Có thị trường POS chỉ liệt kê cấp to: Tây Ban Nha 18 vùng tự trị, trong khi khách
    ghi tên tỉnh ('Castellón' thuộc vùng Valencia) -> phải tra xuống một cấp mới ra.
    """
    if _MKEY in _QUAN_HUYEN:
        return _QUAN_HUYEN[_MKEY]
    cache = os.path.join(A.BASE_STATE, _MKEY, "districts.json")
    data = Q.load_json(cache, None)
    if data is None or any("id" not in d for d in data):   # bản cache cũ chưa lưu id
        data = []
        for pid, _keys in (P.PROVINCES or []):
            res, err = Q.http_json("GET", "https://pos.pages.fm/api/v1/geo/districts",
                                   {"api_key": A.MK["api_key"], "province_id": pid})
            if err:
                A.log(f"⚠ Không tải được quận/huyện của {pid} ({err})")
            for d in ((res or {}).get("data") or []):
                data.append({"province_id": pid, "id": d.get("id"),
                             "name": d.get("name"), "name_en": d.get("name_en")})
            time.sleep(0.1)
        Q.save_json(cache, data)
    bang = []
    for d in data or []:
        keys = _khoa_ten(d)
        if keys:
            bang.append((d["province_id"], keys, d.get("id")))
    _QUAN_HUYEN[_MKEY] = bang
    return bang


def _khoa_ten(d):
    """Các cách viết của một địa danh: 'Castellón/Castelló' -> ['castello', 'castellon']."""
    keys = set()
    for name in (d.get("name"), d.get("name_en")):
        for phan in re.split(r"[/(),]", name or ""):
            k = P.norm_ascii(phan)
            if len(k) >= 4:
                keys.add(k)
    return sorted(keys)


_XA = {}                 # {thị trường: {district_id: [(commune_id, [khóa])]}}


def bang_xa(did):
    """Phường/xã của một quận/huyện — chỉ tải khi thật sự cần (UAE 295 khu/quận)."""
    bang = _XA.setdefault(_MKEY, {})
    if did in bang:
        return bang[did]
    cache = os.path.join(A.BASE_STATE, _MKEY, "communes.json")
    kho = Q.load_json(cache, {})
    if did not in kho:
        res, err = Q.http_json("GET", "https://pos.pages.fm/api/v1/geo/communes",
                               {"api_key": A.MK["api_key"], "district_id": did})
        if err:
            A.log(f"⚠ Không tải được phường/xã của {did} ({err})")
        kho[did] = [{"id": x.get("id"), "name": x.get("name"), "name_en": x.get("name_en")}
                    for x in ((res or {}).get("data") or [])]
        Q.save_json(cache, kho)
    bang[did] = [(x.get("id"), _khoa_ten(x)) for x in kho[did] if _khoa_ten(x)]
    return bang[did]


_KHU_TOAN = {}           # {thị trường: {khóa tên khu: (province_id, district_id, commune_id)}}
# Ngưỡng khớp gần đúng tên khu (so trên phần lõi, đã bỏ 'al'). Xem do_khu_toan.
NGUONG_KHU = 0.87


def bang_khu_toan():
    """Bảng TÊN KHU của cả thị trường -> (tỉnh, quận, khu). Dò NGƯỢC ra tỉnh.

    Khách UAE hay chỉ ghi tên khu ('Al Satwa', 'Emirates Hills', 'Al Muraqqabat') rồi
    gõ sai tên tiểu vương quốc ('Dibai') hoặc bỏ trống luôn -> mọi tầng dò tỉnh đều
    trượt, đơn nằm lại 'Mới' dù địa chỉ thừa dữ liệu để giao. Tên khu là duy nhất trong
    cả nước nên suy ngược ra tỉnh được.

    Tên nào xuất hiện ở HAI TỈNH trở lên thì BỎ HẲN (Al Nahda có ở cả Dubai lẫn Sharjah,
    Al Hamriyah ở Sharjah lẫn Ajman) — đoán bừa là giao sai tiểu vương quốc.
    """
    if _MKEY in _KHU_TOAN:
        return _KHU_TOAN[_MKEY]
    idx, mo_ho = {}, set()
    ds = [(pid, did) for pid, _keys, did in bang_quan_huyen() if did]
    # Có thị trường KHÔNG có cấp xã: Saudi 2277 quận/huyện mà không quận nào có xã ->
    # tải hết là 2277 lượt gọi API mỗi lần dựng cache, đổi lại con số 0. Thử 25 quận đầu,
    # không ra xã nào thì kết luận thị trường không có cấp này và thôi.
    THU_TRUOC = 25
    for i, (pid, did) in enumerate(ds):
        if i == THU_TRUOC and not idx:
            A.log(f"🗺  {A.MK['ten']} không có cấp phường/xã ({THU_TRUOC} quận đầu đều trống) "
                  f"— bỏ tầng suy tỉnh từ tên khu")
            break
        for cid, keys in bang_xa(did):
            for k in keys:
                if k in idx and idx[k][0] != pid:
                    mo_ho.add(k)
                idx.setdefault(k, (pid, did, cid))
    for k in mo_ho:
        idx.pop(k, None)
    if idx:
        A.log(f"🗺  Bảng khu {A.MK['ten']}: {len(idx)} tên dùng để dò ngược ra tỉnh "
              f"({len(mo_ho)} tên trùng ở nhiều tỉnh nên bỏ)")
    _KHU_TOAN[_MKEY] = idx
    return idx


def _loi_khu(k):
    """Phần LÕI của tên khu: bỏ mạo từ 'al/el' và khoảng trắng.

    Khách viết 'Jaffliya' cho 'Al Jafiliya', 'Itisalat' cho 'Etisalat' — so cả cụm thì
    chữ 'al' chung THỔI PHỒNG điểm giống nhau và kéo tên khác hẳn lại gần: 'al khail' vs
    'al ghail' được 0.875 (bằng đúng ca đúng!) trong khi lõi 'khail' vs 'ghail' chỉ 0.8.
    """
    return re.sub(r"\s+", "", re.sub(r"^(?:al|el)\s+", "", k))


def do_khu_toan(dia_chi_lines, trong_tinh=None):
    """Dò tên khu trong địa chỉ -> (province_id, district_id, commune_id, tên khớp).

    Khớp đúng tên trước; không có thì so gần đúng trên PHẦN LÕI với ba chốt chặn, vì
    sai một chữ ở đây là sai cả tiểu vương quốc:
      - ngưỡng NGUONG_KHU trên lõi (bỏ 'al'), lõi phải dài >= 6 ký tự
      - mọi ứng viên đạt ngưỡng phải cùng MỘT tỉnh, khác tỉnh là bỏ (không đoán bừa)
      - cụm đứng ngay trước từ chỉ đường thì bỏ (đó là tên đường, không phải khu)
    """
    idx = bang_khu_toan()
    if not idx:
        return None, None, None, ""
    ung = [((pid, did, cid), [k]) for k, (pid, did, cid) in idx.items()
           if trong_tinh is None or pid == trong_tinh]
    bo, ten = _do_dia_danh(dia_chi_lines, ung, gan_dung=False)
    if bo:
        return bo[0], bo[1], bo[2], ten

    w = P.norm_ascii(re.sub(r"[^\w\s]", " ", ", ".join(dia_chi_lines))).split()
    cum = set()
    for n in (1, 2, 3):
        for i in range(len(w) - n + 1):
            if i + n < len(w) and w[i + n] in TU_CHI_DUONG:
                continue
            c = _loi_khu(" ".join(w[i:i + n]))
            if len(c) >= 6:
                cum.add((c, " ".join(w[i:i + n])))
    dat = []                                   # [(ratio, bộ id, mô tả)]
    for k, (pid, did, cid) in idx.items():
        loi = _loi_khu(k)
        if len(loi) < 6:
            continue
        for c, goc in cum:
            r = difflib.SequenceMatcher(None, c, loi).ratio()
            if r >= NGUONG_KHU:
                dat.append((r, (pid, did, cid), f"{goc}≈{k}"))
    if not dat or len({d[1][0] for d in dat}) > 1:
        return None, None, None, ""            # không ai đạt, hoặc đạt ở nhiều tỉnh -> chịu
    r, bo, ten = max(dat)
    return bo[0], bo[1], bo[2], ten


def _do_dia_danh(dia_chi_lines, ung_vien, gan_dung=True):
    """Dò một địa danh trong các dòng địa chỉ. Trả (id, tên khớp).

    Ưu tiên dòng khớp NGUYÊN VẸN (form Webcake mỗi cấp một dòng); không có thì tìm cụm
    từ trong cả địa chỉ và lấy tên DÀI NHẤT ('Al Barsha South' thắng 'Al Barsha').
    """
    for line in reversed(dia_chi_lines):
        khoa = P.norm_ascii(re.sub(r"[^\w\s]", " ", line))
        for _id, keys in ung_vien:
            if khoa in keys:
                return _id, khoa
    ca_dia_chi = P.norm_ascii(re.sub(r"[^\w\s]", " ", ", ".join(dia_chi_lines)))
    tot = None
    for _id, keys in ung_vien:
        for k in keys:
            if re.search(rf"\b{re.escape(k)}\b", ca_dia_chi) and (not tot or len(k) > len(tot[1])):
                tot = (_id, k)
    if tot or not gan_dung:
        return tot or (None, "")

    # Khớp gần đúng cho khách gõ sai chính tả ('Gubairah' = 'Ghubairah', 'Murabah' = 'Murabba').
    # NGƯỠNG 0.85 LÀ ĐO ĐƯỢC, ĐỪNG HẠ: 0.80 khớp bậy 'Matar'->'Mawta', 'Riyadh'->'Rimayah'.
    # Chỉ so từ dài >= 5 ký tự, từ ngắn quá dễ đụng nhau.
    w = ca_dia_chi.split()
    tu = set()
    for n in (1, 2, 3):                    # thử cả cụm nhiều từ ('sanatoriul agigea')
        for i in range(len(w) - n + 1):
            # 'King Fahad Road' là TÊN ĐƯỜNG, không phải quận King Fahd — bỏ cụm nào
            # ngay sau nó là từ chỉ đường (đã khớp bậy đơn Saudi #68617).
            if i + n < len(w) and w[i + n] in TU_CHI_DUONG:
                continue
            cum = " ".join(w[i:i + n])
            if len(cum) >= 5:
                tu.add(cum)
    gan = None
    for _id, keys in ung_vien:
        for k in keys:
            if len(k) < 5:
                continue
            for t in tu:
                r = difflib.SequenceMatcher(None, t, k).ratio()
                if r >= 0.85 and (not gan or r > gan[2]):
                    gan = (_id, f"{t}≈{k}", r)
    return (gan[0], gan[1]) if gan else (None, "")


def do_tinh(dia_chi_lines):
    """Dò tỉnh/thành: khớp tên chuẩn -> viết tắt cả dòng -> tên quận/huyện -> gần đúng.
    Trả (province_id, cách dò được)."""
    joined = ", ".join(dia_chi_lines)
    pid = P.detect_emirate(joined)
    if pid:
        return pid, "khớp tên"

    bang_tat = VIET_TAT.get(_MKEY, {})
    for line in reversed(dia_chi_lines):
        key = P.norm_ascii(re.sub(r"[^\w\s]", " ", line))
        if key in bang_tat:
            return bang_tat[key], f"viết tắt {key!r}"

    # Tên quận/huyện chỉ nhận khi ĐÚNG CẢ DÒNG, và duyệt từ dòng cuối lên (form Webcake
    # xếp thành phố/tỉnh/quốc gia ở cuối). Quét cả chuỗi thì tên đường nuốt mất tỉnh:
    # 'Carrer de fra Luis de leon 243' ở Barcelona từng bị đọc thành tỉnh León.
    qh = None
    for line in reversed(dia_chi_lines):
        khoa = P.norm_ascii(re.sub(r"[^\w\s]", " ", line))
        if len(khoa) < 4:
            continue
        if qh is None:
            qh = bang_quan_huyen()
        for pid, keys, _did in qh:
            if khoa in keys:
                return pid, f"quận/huyện {khoa!r}"

    # Gần đúng: so từng cụm 1-3 từ của 3 dòng cuối với tên tỉnh (khách hay gõ sai: Buraidah/Buraydah).
    # DÒNG GẦN CUỐI NHẤT THẮNG, không lấy điểm cao nhất toàn địa chỉ: form Webcake để tỉnh ở
    # dòng cuối, nên một chữ ở dòng trên vô tình giống tên tỉnh khác sẽ cướp mất
    # ('Aman building | Room 42 | Sharjja' -> 'aman'≈'ajman' 0.889 đè 'sharjja'≈'sharjah' 0.857,
    # đơn #44242 đi nhầm Ajman). Đo trên đơn có tỉnh do nhân viên chốt: cách này UAE 13 đúng
    # 0 sai (cũ 12 đúng 1 sai), Saudi 8 đúng 0 sai — không đơn nào xấu đi.
    provinces = P.PROVINCES or P.EMIRATES
    for line in reversed(dia_chi_lines[-3:]):
        tu = P.norm_ascii(re.sub(r"[^\w\s]", " ", line)).split()
        best, best_r, best_pair = None, 0.0, None
        for n in (1, 2, 3):
            for i in range(len(tu) - n + 1):
                cum = " ".join(tu[i:i + n])
                if len(cum) < 4:
                    continue
                for pid, keys in provinces:
                    for k in keys:
                        r = difflib.SequenceMatcher(None, cum, k).ratio()
                        if r > best_r:
                            best, best_r, best_pair = pid, r, (cum, k)
        # NGƯỠNG 0.85 GIỮ NGUYÊN, ĐỪNG HẠ: 0.80 làm 4 đơn 'Al Ahsa' của Saudi nhảy sang
        # 'Al Bahah' (r=0.80) — hai tỉnh cách nhau 900km.
        if best_r >= 0.85:
            return best, f"gần đúng {best_pair[0]!r}≈{best_pair[1]!r}"
    return None, ("THIẾU TỈNH/THÀNH — sale chọn tỉnh tay rồi xác nhận "
                  f"(khách ghi {', '.join(dia_chi_lines[-3:])!r}, không khớp danh mục POS)")


# Động từ "mua" trên dòng ưu đãi của từng thị trường. Landing page mỗi nước viết
# tiếng bản địa: chỉ bắt "buy" là Tây Ban Nha/Romania KHÔNG ra số lượng nào
# (đã lên nhầm đơn 1 cái cho khách mua 2 — xem đơn Spain #1597). Bulgaria viết bằng
# chữ Kirin ('Купи 2: 45 EURO') — thiếu nó thì đơn 'Купи 2' giữ nguyên số lượng 1 của
# landing mà vẫn thu 45 EUR (đơn Bulgaria #3, thị trường mở 01/09/2026).
MUA = r"(?:buy|compr[aá]|compre|cump[ăa]r[ăa]|cumpar|acheter|kaufen|köp|купи)"
TANG = r"(?:get|gratis|free|llev[aá]te|primesti|prime[șs]ti|вземи|безплатно)"


def tim_ma_buu_chinh(dia_chi_lines):
    """Mã bưu chính đứng RIÊNG MỘT DÒNG trong form Webcake ('Габрово / 5400 / Севлиево').

    Chỉ bật cho thị trường khai `lay_ma_buu_chinh` (Bulgaria): ở đó Webcake điền sẵn tên
    đường vào ô địa chỉ nên ghi chú chỉ còn tỉnh/mã bưu chính/thành phố — không nhét được
    vào ô địa chỉ (cấm ghi đè) thì mã bưu chính mất luôn, ĐVVC phải tự tra thành phố.
    Đòi ĐỨNG RIÊNG CẢ DÒNG để không nhặt nhầm số nhà ('улица Витоша 11').
    """
    for line in dia_chi_lines:
        s = line.strip()
        if re.fullmatch(r"\d{4,6}", s):
            return s
    return None


def doc_so_luong(offer):
    """'Buy 1 get 1 (2pcs)' -> 2 ; 'Buy 2 Get 3 (Total 5 iteam)' -> 5 ;
    'Compra 2 – 45 €' -> 2 ; 'Cumpără 2: 199 Lei' -> 2 ; 'Compra 1 collar' -> 1."""
    if not offer:
        return None
    t = offer.lower()
    for rx in (r"total\s*[:\-]?\s*(\d+)\s*(?:ite?a?ms?|pcs?|pieces?)",
               r"\(\s*(\d+)\s*(?:pcs?|pieces?|ite?a?ms?)\s*\)"):
        m = re.search(rx, t)
        if m:
            return int(m.group(1))
    m = re.search(rf"{MUA}\s*(\d+)\s*{TANG}\s*(\d+)", t)
    if m:
        return int(m.group(1)) + int(m.group(2))
    # Viết tắt 'B1G1' / 'B2G2' — landing không đẩy số lượng thật về POS nên dòng ưu đãi là
    # NGUỒN DUY NHẤT đọc ra số lượng (user chốt 2026-09-02): đọc trượt = đơn đi thiếu hàng
    # mà không ai biết. Đo 30 ngày/12 thị trường: 882 đơn landing chỉ 1 dòng dạng này
    # (qatar #6047 '133 - Feng Shui 2 – Lucky Charm | B1G1 FreeShip 119 QAR').
    m = re.search(r"\bb(\d)\s*g(\d)\b", t)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.search(rf"{MUA}\s*(\d+)", t)
    if m:
        return int(m.group(1))
    return None


def ten_tren_uu_dai(offer):
    """Tên/mã sản phẩm ở ĐẦU dòng ưu đãi ('247\tTibetan...|Buy 2 : 99 AED' -> '247 Tibetan...',
    '217|Buy 1...' -> '217'). None = dòng ưu đãi không gọi tên sản phẩm nào."""
    if not offer or "|" not in offer:
        return None
    ten = offer.split("|")[0].strip(" -–:")
    if not ten or re.search(r"\bbuy\b|\bget\b", ten, re.I):
        return None
    return ten


def ma_sp_utm(o):
    """Mã SP marketer ghi ở đoạn THỨ HAI của utm_source ('TinDV/256 - Túi hút chân
    không/Saudi/Thắng Saudi/2109/VD4' -> '256'). None nếu đoạn đó không mở đầu bằng mã,
    hoặc UTM là chiến dịch test (để nguyên đường 'Chờ hàng' của hàng test).

    CHỈ là nguồn DỰ PHÒNG khi form Webcake không gọi tên SP. Ca thật saudi 22-23/09/2026:
    landing space-bag-2 (256) đổi form, dòng ưu đãi chỉ còn 'Buy 1 get 1 free: SAR 109 +
    Free shipping' — đơn nào Webcake không gắn dòng hàng thì rơi vào luật "landing không
    có SP là đơn test" (#76401, #76479 khách thật nằm 'Chờ hàng'), đơn nào Webcake gắn
    nhầm 'BOX' (móc từ 'P.O Box 519' trong ô địa chỉ) thì đi thẳng Chờ in (#76497).
    Đo 30 ngày/1272 đơn landing: đoạn này có mã ở 125 đơn, khớp mã trên form 116/116,
    khớp mã dòng hàng 114/114. CHỈ đọc đoạn thứ hai và đúng 3 chữ số: các đoạn sau có
    ngày 'ddmm' ('…/0809 - Bản sao') trông y hệt mã SP.
    """
    s = o.get("p_utm_source") or ""
    if TU_TEST.search(s):
        return None
    seg = s.split("/")
    m = re.match(r"\s*(\d{3})(?!\d)", seg[1]) if len(seg) > 1 else None
    return m.group(1) if m else None


# Số lượng THẬT của một dòng hàng không bao giờ tới ngưỡng này (ưu đãi to nhất đo được là
# 'Buy 1 Get 1 Set (20 pieces)'). Dưới ngưỡng thì mã SP nhỏ trùng số lượng thật là chuyện
# thường ('002 - Gold Ring' x2) — coi đó là rác thì sửa hỏng đơn đúng.
SL_KHONG_THAT = 30


def _ma_dau_ten(it):
    """Con số mã SP của dòng hàng ('247 - Tibetan Blessed Copper Bracelet' -> 247)."""
    vi = it.get("variation_info") or {}
    m = re.match(r"\s*(\d{2,5})\s*[-–]", vi.get("name") or "")
    if m:
        return int(m.group(1))
    ma = str(vi.get("display_id") or "").strip()
    return int(ma) if re.fullmatch(r"\d{2,5}", ma) else None


def sl_la_ma_sp(it):
    """Dòng hàng có SỐ LƯỢNG = đúng MÃ SP của chính nó -> landing nhét mã vào ô số lượng.

    Đo trên đơn thật UAE 16-29/08: 34 dòng dính đúng khuôn này, TẤT CẢ chỉ đến từ 2 landing
    page 'golden-turtle-wealth-charm' (x246) và 'tibetan-blessed-copper-bracelet' (x247);
    10 landing page còn lại không dính dòng nào. 33/34 đơn đó COD cũng rơi về 0 và là bản
    khách bấm gửi lần hai, NHƯNG #48169 COD đúng 99 AED mà số lượng vẫn rác — nên tuyệt
    đối không được lấy 'giá khớp' làm điều kiện để nhận ra ca này.
    """
    ma = _ma_dau_ten(it)
    sl = it.get("quantity") or 0
    return ma is not None and sl == ma and sl >= SL_KHONG_THAT


def _khoa_sp(s):
    """Chuẩn hóa tên sản phẩm để đem so: bỏ dấu, mọi ký tự không phải chữ/số thành khoảng trắng."""
    return re.sub(r"[^a-z0-9]+", " ", P.norm_ascii(s)).strip()


def khop_uu_dai(it, ten_uu_dai):
    """Dòng hàng này có đúng là sản phẩm mà dòng ưu đãi gọi tên không."""
    a, b = _khoa_sp((it.get("variation_info") or {}).get("name")), _khoa_sp(ten_uu_dai)
    if not a or not b:
        return False
    # Chỉ cho 'nằm trong nhau' khi vế ngắn đủ dài — 'box', 'set', 'ring' nằm trong tên nào chả được
    if (a in b or b in a) and min(len(a), len(b)) >= 6:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def dung_sp_uu_dai(it, ten_uu_dai):
    """khop_uu_dai, cộng thêm so MÃ: tên ưu đãi là mã trần ('256' lấy từ UTM) thì so chữ
    không bao giờ khớp (ngắn hơn ngưỡng 6 ký tự) — phải so mã đứng đầu tên dòng hàng."""
    ma = _ma_dau_chuoi(ten_uu_dai)
    if ma and _ma_dau_ten(it) == int(ma):
        return True
    return khop_uu_dai(it, ten_uu_dai)


def _ma_dau_chuoi(s):
    """Mã SP đứng đầu một chuỗi tên: '260 - MAXCURVE…' / '247<tab>Tibetan…' / '217' -> '260'/'247'/'217'."""
    m = re.match(r"\s*(\d{2,5})(?!\d)(?:\s*[-–:|]|\s|$)", s or "")
    return m.group(1) if m else None


def la_dung_sp(ten, v):
    """Mẫu mã POS `v` có đúng là sản phẩm dòng ưu đãi gọi tên (`ten`) không.

    Dòng ưu đãi có mã đứng đầu -> TÊN mẫu mã phải mang đúng mã đó. Không có mã -> so tên
    (bỏ mã đầu tên POS) như khop_uu_dai.
    Vì sao không được tin kết quả tìm kiếm của POS (ca thật SAUDI #74247, 15/09/2026):
    ô tìm kiếm khớp cả MÃ MẪU MÃ (display_id), mà mẫu mã '254 - Aminochondroitin Sulfate
    Ointment' bị ai đó gõ nhầm mã thành 'MAXCURVE Sculpting Bust Oil' lúc 08:09 VN. Tìm
    '260 - MAXCURVE Sculpting Bust Oil' ra đúng 1 kết quả là 254, bản cũ nhận luôn vì 'chỉ
    1 mẫu mã' -> đơn landing tinh dầu 260 bị gắn 254 x2. Hồi quy 162 đơn tool từng tự thêm
    SP (09/08-15/09): 151 vẫn nhận, #74247 bị chặn, 10 đơn UAE ghi chú đã bị hãng ghi đè
    nên không đo lại được (log cũ cho thấy dạng '247<tab>Tibetan…', khuôn mã vẫn nhận).
    """
    label = P.variation_label(v)
    ma = _ma_dau_chuoi(ten)
    if ma:
        return _ma_dau_chuoi(label) == ma
    a = _khoa_sp(re.sub(r"^\s*\d{2,5}\s*[-–:]\s*", "", label))
    b = _khoa_sp(ten)
    if not a or not b:
        return False
    if (a in b or b in a) and min(len(a), len(b)) >= 6:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def do_san_pham(offer, ten=None):
    """Đơn không có dòng hàng: lấy tên/mã sản phẩm ở đầu dòng ưu đãi
    ('220 - Nail Serum|Buy 1...' hoặc '217|Buy 1...') rồi tìm trong POS.
    Chỉ nhận khi ra DUY NHẤT 1 mẫu mã ĐÚNG sản phẩm đó (la_dung_sp) — kể cả khi POS chỉ
    trả về 1 kết quả, vẫn phải kiểm. `ten` truyền sẵn = tên đã đọc từ nguồn khác (mã UTM)."""
    ten = ten or ten_tren_uu_dai(offer)
    if not ten:
        return None, "dòng ưu đãi không có tên sản phẩm"
    ma = _ma_dau_chuoi(ten)
    if not ma and len(ten) < 4:
        return None, "dòng ưu đãi không có tên sản phẩm"
    try:
        items = P.search_variations(ten, page_size=20)
    except SystemExit as e:
        return None, f"lỗi tìm sản phẩm: {e}"
    if not items:
        return None, f"không tìm thấy sản phẩm {ten!r} trong POS"
    khop = [v for v in items if la_dung_sp(ten, v)]
    if not khop:
        return None, (f"tìm {ten!r} trong POS chỉ ra mẫu mã KHÁC ("
                      + ", ".join(P.variation_label(v) for v in items[:3])
                      + ") — không gắn bừa, người kiểm rồi thêm tay")
    if len(khop) > 1:
        return None, f"{ten!r} khớp {len(khop)} mẫu mã, không chắc chắn"
    return khop[0], f"dò theo {'mã' if ma else 'tên'} {ten!r}"


# ---------------- Đọc 1 đơn landing page ----------------

def chan_doan_sdt(goc, chuan):
    """Số không khớp định dạng thị trường -> (CÒN CÁCH LIÊN LẠC?, mô tả hỏng ở đâu).

    Nói RÕ hỏng ở đâu để nhân viên gọi khách hoặc sửa được ngay — 'không đúng định dạng'
    chung chung thì ai cũng phải soi lại.

    Từ 2026-09-04 vế False chỉ còn nghĩa là TREO chờ người kiểm, KHÔNG còn là lệnh hủy —
    nên câu chữ viết theo hướng "kiểm rồi sửa", đừng viết "không gọi được để hỏi lại" nữa
    (chính chỗ đó khiến người đọc tưởng số đã chết, trong khi khuôn regex chỉ nhận di động).

    Chỉ còn gọi cho số KHÔNG đọc ra được: số nước ngoài có mã nước rõ ràng nay do
    A.phan_loai_sdt nhận ('ngoai') và được chấp nhận theo luật user. Ba loại gặp thật:
    (a) số nước khác gõ theo kiểu bản địa nên không có mã nước để nhận ra,
    (b) khách gõ THIẾU/THỪA chữ số, (c) rác. Loại (b) tuyệt đối không tự đoán bù —
    thêm bừa một chữ số là gói hàng đi cho người lạ.

    VẾ ĐẦU QUYẾT ĐỊNH SỐ PHẬN ĐƠN LANDING (luật user 2026-08-24): thiếu/thừa/sai chữ số
    thì đơn landing bị HỦY luôn — không gọi được thì không có đường nào hỏi lại khách,
    để 'Mới' chỉ tồn đọng (đo 30 ngày: 14/22 đơn landing còn 'Mới' kẹt đúng vì lý do này,
    đơn cũ nhất nằm 23 ngày). Riêng loại (a) trả True: tool đã đọc ra MỘT SỐ CỤ THỂ để
    thử WhatsApp/gọi, còn liên lạc được thì không được hủy. Đơn Facebook không bao giờ
    đi qua đây — còn hội thoại nên nhân viên hỏi lại khách được.
    """
    so = re.sub(r"\D", "", str(goc or "")).lstrip("0")
    # Số này có MÃ NƯỚC của thị trường khác đứng đầu không?
    # BẮT BUỘC có mã nước thật trong chuỗi, không chỉ 'khớp regex nước đó': số 8 chữ số
    # nào cũng vừa khuôn Kuwait, số 10 chữ số nào cũng vừa khuôn Mỹ -> đoán theo khuôn là
    # gán bừa quốc tịch cho khách (đã thử: '03365031008' số Pakistan bị đọc thành số Mỹ).
    # Mã 1 chữ số (Mỹ/Canada) thì bỏ qua vì không có gì để phân biệt.
    for _mk, cfg in A.MARKETS.items():
        cc = str(cfg["country_code"])
        if cfg.get("ten") == A.MK.get("ten") or len(cc) < 2 or not so.startswith(cc):
            continue
        d = so[len(cc):].lstrip("0")
        if cfg.get("sdt_them_0") and d:
            d = "0" + d
        if d and re.fullmatch(cfg["sdt_regex"], d):
            return (True,
                    f"SĐT {chuan} trông như SỐ {cfg['ten']} (+{cc}) gõ thiếu mã nước — "
                    f"nhân viên xác minh rồi sửa thành +{cc}{d.lstrip('0')} để bên vận chuyển "
                    f"liên hệ được qua WhatsApp")
    # Số gõ RÕ kiểu quốc tế ('+' hoặc '00') mà A.phan_loai_sdt vẫn không đọc ra được = nhận
    # ra mã nước nhưng THÂN SỐ sai độ dài. Phải nói đúng như vậy, đừng đem so với độ dài số
    # bản địa: ghi chú hủy mà ghi 'thiếu 2 số so với số SAUDI' thì nhân viên tưởng khách gõ
    # nhầm số Saudi, trong khi đây là số nước ngoài gõ hụt (luật user 2026-08-24: số ngoại
    # thiếu/thừa/sai cũng hủy đơn landing y như số bản địa hỏng, Facebook thì treo).
    raw = re.sub(r"\D", "", str(goc or ""))
    if str(goc).strip().startswith("+") or raw.startswith("00"):
        quoc_te = raw[2:] if raw.startswith("00") else raw
        for n in (3, 2, 1):
            ma = quoc_te[:n]
            if ma in A.MA_QUOC_TE and ma != str(A.MK["country_code"]):
                than = quoc_te[n:].lstrip("0")
                return (False,
                        f"SĐT {goc} khai là số {A.MA_QUOC_TE[ma]} (+{ma}) nhưng thân số "
                        f"{than!r} chỉ có {len(than)} chữ số — không đúng khuôn số "
                        f"{A.MA_QUOC_TE[ma]}, người kiểm lại rồi sửa số")
    # Đếm xem lệch mấy chữ số so với một số hợp lệ điển hình của thị trường
    mau = _do_dai_chuan()
    n = len(re.sub(r"\D", "", chuan))
    if mau and n < mau:
        return (False,
                f"SĐT {chuan} chỉ có {n} chữ số, THIẾU {mau - n} số so với số {A.MK['ten']} "
                f"({mau} chữ số) — máy không tự bù được, người kiểm rồi sửa số")
    if mau and n > mau:
        return (False,
                f"SĐT {chuan} có {n} chữ số, THỪA {n - mau} số so với số {A.MK['ten']} "
                f"({mau} chữ số) — máy không biết bỏ số nào, người kiểm rồi sửa số")
    return (False,
            f"SĐT {chuan} không khớp khuôn số DI ĐỘNG {A.MK['ten']} (số cố định/số nước ngoài "
            f"viết kiểu bản địa cũng rơi vào đây) — thử gọi/WhatsApp số này xem có liên hệ "
            f"được không rồi quyết")


def _do_dai_chuan():
    """Số chữ số của một SĐT hợp lệ ở thị trường này, TÍNH CẢ số 0 dẫn đầu (vì `chuan`
    đem ra so là số đã chuẩn hóa kiểu bản địa)."""
    than = A.dai_sdt_ban_dia()
    return than and than + (1 if A.MK.get("sdt_them_0") else 0)


def doc_don(o):
    """Trích mọi thứ cần thiết từ 1 đơn landing page + liệt kê lý do KHÔNG được tự xác nhận."""
    note = o.get("note") or ""
    shopify = la_shopify(o)
    if shopify:
        dia_chi_lines, offer = dong_dia_chi_shopify(o), None
    else:
        dia_chi_lines, offer = tach_note(note)
    diachi = ", ".join(dia_chi_lines)
    tinh, cach = do_tinh(dia_chi_lines) if dia_chi_lines else (None, "ghi chú không có địa chỉ")

    # Mọi tầng dò tỉnh đều trượt -> thử suy NGƯỢC từ tên khu ('Al Satwa' chỉ có ở Dubai).
    # Được cả cụm tỉnh/quận/khu nên đơn không còn phải chờ nhân viên chọn tay.
    quan = xa = None
    if not tinh and dia_chi_lines:
        pid_k, did_k, cid_k, ten_k = do_khu_toan(dia_chi_lines)
        if pid_k:
            tinh, quan, xa = pid_k, did_k, cid_k
            cach = f"suy từ khu {ten_k!r}"

    # Có tỉnh rồi thì dò tiếp quận/huyện (rồi phường/xã) TRONG PHẠM VI tỉnh đó —
    # ĐVVC cần mấy cấp này, POS để trống thì nhân viên phải chọn tay từng đơn.
    if tinh and dia_chi_lines and not quan:
        quan, _ = _do_dia_danh(dia_chi_lines,
                               [(did, keys) for p, keys, did in bang_quan_huyen()
                                if p == tinh and did])
        if quan:
            xa, _ = _do_dia_danh(dia_chi_lines, bang_xa(quan))
        else:
            # Biết tỉnh mà không ra quận: tên khu cũng chỉ ngược lên được quận cha
            _p, did_k, cid_k, _t = do_khu_toan(dia_chi_lines, trong_tinh=tinh)
            quan, xa = did_k, cid_k
    ma_bc = tim_ma_buu_chinh(dia_chi_lines) if A.MK.get("lay_ma_buu_chinh") else None
    gia = tim_gia(offer) if offer else None
    so_luong = doc_so_luong(offer)
    if shopify:
        # Shopify ghi thẳng số lượng khách chọn ("SL: 2"). Tiền thu nó để ở ô PHỤ THU
        # (surcharge), phí chuyển để 0 — đã tính vào dang_thu bên dưới nên KHÔNG điền giá
        # sang phí chuyển (bản vá đầu 19/09 lấy `cod` điền sang phí chuyển: POS cộng dồn
        # thành COD 218 lei ở #705/#707/#708).
        m = re.search(r"\bSL:\s*(\d+)", note)
        so_luong = int(m.group(1)) if m else None

    sdt_goc = o.get("bill_phone_number") or (o.get("shipping_address") or {}).get("phone_number") or ""
    loai_sdt, sdt, mo_ta_sdt = A.phan_loai_sdt(sdt_goc)

    can_check, ghi_them, sp_moi = [], [], None
    if not diachi:
        can_check.append("THIẾU ĐỊA CHỈ — ghi chú Webcake không có dòng địa chỉ nào, "
                         "phải gọi khách hỏi lại")
    else:
        # 2 dòng cuối thường là thành phố + tỉnh/quốc gia; phần đầu mới là số nhà/đường
        dau = dia_chi_lines[:-2] or dia_chi_lines
        if all(RAC_DONG.fullmatch(d.strip()) for d in dau):
            can_check.append(f"THIẾU SỐ NHÀ/ĐƯỜNG — khách chỉ điền {', '.join(dau)!r}, "
                             f"không giao được, phải gọi hỏi lại")
    if not tinh and not (o.get("shipping_address") or {}).get("province_id"):
        # Nhân viên đã chọn tay tỉnh/thành vào POS rồi thì đơn KHÔNG còn thiếu gì — đọc ô
        # địa chỉ của đơn chứ đừng chỉ đọc ghi chú, không thì đơn nằm 'Mới' vĩnh viễn dù
        # người đã làm xong phần việc tool nhờ (ca #48169: người điền Sharjah lúc 01:20,
        # ghi chú in "đã thêm tỉnh thành", tool vẫn kêu THIẾU TỈNH/THÀNH ở mọi vòng sau).
        can_check.append(cach)

    items = o.get("items") or []
    # Form không gọi tên SP (landing đổi form, saudi space-bag-2 22/09/2026) -> lấy mã
    # marketer ghi trong UTM. Shopify có SKU sẵn trên dòng hàng nên không đụng.
    ten_uu_dai = ten_tren_uu_dai(offer)
    tu_utm = False
    if not ten_uu_dai and not shopify:
        ten_uu_dai = ma_sp_utm(o)
        tu_utm = bool(ten_uu_dai)
    if not items:
        v, vi_sao = do_san_pham(offer, ten_uu_dai)
        if v and so_luong and gia:
            sp_moi = {"variation": v, "quantity": so_luong, "gia": gia}
        elif v:
            can_check.append(f"đơn không có sản phẩm — dò ra {P.variation_label(v)} nhưng "
                             f"không đọc được số lượng/giá trên dòng ưu đãi, gọi khách hỏi lại")
        else:
            can_check.append(f"đơn không có sản phẩm ({vi_sao})")

    # Quy ước của shop: tiền hàng = 0, tiền thu khách nằm ở PHÍ CHUYỂN.
    # Phải xét shipping_fee chứ không phải money_to_collect: có đơn mang tiền ở chỗ khác,
    # POS tính lại money_to_collect = shipping_fee + total_price khi mình ghi địa chỉ
    # -> tưởng đơn đã có tiền nên không điền, hóa ra đơn về 0 (đã mất 7 đơn vì lỗi này).
    phi = o.get("shipping_fee") or 0
    tien_hang = o.get("total_price") or 0
    # Phụ thu cũng là tiền thu khách (POS: COD = phí chuyển + tiền hàng + phụ thu). Shopify
    # đổ tiền vào đúng ô này; bỏ qua nó là tool điền thêm phí chuyển -> COD gấp đôi. Đo
    # 30 ngày/12 nước: chỉ 4 đơn Shopify có phụ thu, đơn Webcake không đổi gì.
    dang_thu = phi + tien_hang + (o.get("surcharge") or 0)
    tien_moi = None
    if not dang_thu:
        if gia:
            tien_moi = gia
        else:
            can_check.append("đơn chưa có tiền COD và ghi chú không có giá")
    elif gia and gia != dang_thu:
        can_check.append(f"lệch giá: ghi chú {P.fmt_money(gia)} ≠ đơn {P.fmt_money(dang_thu)}")

    # ---------------- Dòng hàng ----------------
    hop_id = A.MK.get("hop_id") if A.MK.get("dung_hop", True) else None
    items_giu, bo_dong = items, []
    # Landing đẩy KÈM DÒNG HÀNG LẠ: #48169 về với 'FLOWER NECKLACE' x1 nằm cạnh đúng SP
    # khách đặt — SP đó ảnh từ 3/2025, không bán trên landing page nào, và xuất hiện đúng
    # 1 lần trong 1959 đơn/30 ngày. Dòng ưu đãi chỉ gọi tên MỘT sản phẩm nên dòng nào không
    # phải SP đó thì là rác. HỘP PHẢI CHỪA RA: 47 đơn landing/30 ngày kèm '008 - Necklace
    # box' hoàn toàn hợp lệ, gỡ nhầm là kho gói thiếu hộp.
    if items and ten_uu_dai:
        khop = {i for i, it in enumerate(items) if dung_sp_uu_dai(it, ten_uu_dai)}
        hop_i = {i for i, it in enumerate(items) if hop_id and it.get("variation_id") == hop_id}
        if khop and len(items) > 1:
            giu = khop | hop_i
            items_giu = [it for i, it in enumerate(items) if i in giu]
            bo_dong = [it for i, it in enumerate(items) if i not in giu]
        elif not khop and len(hop_i) < len(items) and not la_ten_test(ten_uu_dai):
            # KHÔNG dòng hàng nào là SP dòng ưu đãi gọi tên — kể cả đơn chỉ MỘT dòng. Bản
            # cũ chỉ lọc khi >1 dòng VÀ có dòng khớp, nên saudi #76497 (23/09/2026) về với
            # đúng 1 dòng 'BOX' x1 (Webcake móc chữ 'P.O Box 519' trong ô địa chỉ) mà vẫn
            # được sửa SL theo ưu đãi thành BOX x2 rồi vào Chờ in — kho sẽ gói 2 cái hộp
            # thay cho 2 túi 256. Dò ra ĐÚNG 1 mẫu mã thì thay cả dòng, không thì treo.
            # Đo 30 ngày/1272 đơn: ngoài đơn form 'Test' (đã rẽ sang Chờ hàng trước khi
            # tới đây) KHÔNG đơn nào dính nhánh này -> không đổi gì ở đơn đang chạy đúng.
            v, vi_sao = do_san_pham(offer, ten_uu_dai)
            if v and so_luong and gia:
                sp_moi = {"variation": v, "quantity": so_luong, "gia": gia}
                items_giu, bo_dong = [], list(items)
            else:
                lech = ", ".join(f"{(it.get('variation_info') or {}).get('name')} "
                                 f"x{it.get('quantity')}"
                                 for i, it in enumerate(items) if i not in hop_i)
                can_check.append(f"dòng hàng {lech} KHÔNG phải SP dòng ưu đãi gọi tên "
                                 f"({ten_uu_dai!r}) — "
                                 + (f"dò ra {P.variation_label(v)} nhưng không đọc được số "
                                    f"lượng/giá, người kiểm rồi thay tay" if v else vi_sao))

    # DÒNG HỘP KHÔNG PHẢI HÀNG KHÁCH ĐẶT nên phải đứng NGOÀI phép so số lượng, rồi chạy
    # THEO số lượng hàng (luật 1:1). Bỏ sót vế này thì tool tự bẫy mình qua hai vòng quét:
    # vòng trước nó kèm 'hộp x1' cạnh 'hàng x1', vòng sau tổng = 2 đúng bằng ưu đãi
    # 'Buy 1 Get 1' -> phép so tưởng đơn đã đủ, hàng nằm im ở x1 trong khi khách đã trả
    # tiền 2 chiếc. Ca thật: Saudi #71820, #71785 (04/09/2026, landing lắc tay 234) —
    # user chốt "buy 1 get 1 thì 2 hộp, 2 chiếc".
    la_hop = [bool(hop_id) and it.get("variation_id") == hop_id for it in items_giu]
    hang = [it for it, h in zip(items_giu, la_hop) if not h]
    sl_moi = None
    if hang and so_luong:
        cac_sl = [it.get("quantity") or 0 for it in hang]
        tong_sl = sum(cac_sl)
        gia_khop = not dang_thu or not gia or dang_thu == gia
        sl_hang = None
        if any(sl_la_ma_sp(it) for it in hang):
            # SL = đúng mã SP của chính nó là RÁC của landing, không phải khách đặt. Xét
            # TRƯỚC phép so 'so_luong not in cac_sl': đơn kèm hộp có dòng HỘP đúng số lượng
            # sẽ làm phép so đó tưởng đơn không lệch rồi bỏ qua luôn dòng SP rác.
            sl_hang = [so_luong if sl_la_ma_sp(it) else (it.get("quantity") or 0)
                       for it in hang]
        elif so_luong not in cac_sl and so_luong != tong_sl:
            if len(hang) == 1 and gia_khop:
                # Landing page bản cũ để số lượng 1 dù ưu đãi là "mua 1 tặng 1 (2pcs)" —
                # giá đã khớp nên sửa số lượng theo ưu đãi, đúng như nhân viên vẫn làm tay.
                sl_hang = [so_luong]
            elif (tong_sl and gia_khop and len(set(cac_sl)) == 1
                  and so_luong % tong_sl == 0):
                # Nhiều dòng NHƯNG đều cùng số lượng (vd 2 dòng x1) và ưu đãi đòi đúng
                # bội số của tổng hiện tại — landing lên thiếu ĐỀU từng dòng, nhân đều
                # lên theo hệ số, giống hệt nhân viên vẫn làm tay (đơn Saudi #69564:
                # 2 dòng x1, ưu đãi 'Buy 2 Get 2 Total 4 item' -> nhân 2 mỗi dòng
                # thành [2, 2]). Giá đã khớp riêng qua gia_khop nên không đụng tới tiền.
                he_so = so_luong // tong_sl
                sl_hang = [sl * he_so for sl in cac_sl]
            else:
                can_check.append(f"lệch số lượng: ghi chú {so_luong} ≠ đơn {cac_sl}")
        if sl_hang is not None:
            # Hộp SẴN CÓ trên đơn phải theo số lượng hàng trang sức mới (cùng luật 1:1 với
            # khối tự kèm hộp bên dưới). Không có dòng trang sức nào thì để yên dòng hộp —
            # hộp đó do người thêm tay, tool không đoán thay.
            sl_hop = sum(q for it, q in zip(hang, sl_hang)
                         if A.la_trang_suc((it.get("variation_info") or {}).get("name") or ""))
            con = iter(sl_hang)
            sl_moi = [(sl_hop or (it.get("quantity") or 0)) if h else next(con)
                      for it, h in zip(items_giu, la_hop)]
            if sl_moi == [it.get("quantity") or 0 for it in items_giu]:
                sl_moi = None          # tính ra y hệt số đang có thì khỏi ghi lại đơn

    # LUẬT USER 2026-08-30: mọi dòng hàng TRANG SỨC (vòng tay/vòng cổ/nhẫn/khuyên...) phải
    # kèm hộp 008. Landing page hầu như không đẩy hộp sang — đo 30 ngày: '247 - Tibetan
    # Blessed Copper Bracelet' 0/27 đơn có hộp, '246 - Golden Turtle Wealth Charm' 0/78,
    # '239 - Ring Of Faith' 0/29 — nên tool tự bù. Số lượng hộp = số lượng hàng (410/425
    # đơn có hộp trong 30 ngày đi đúng tỉ lệ 1:1). Chỉ 4 thị trường khai hộp: UAE, Saudi,
    # Kuwait, Đài Loan; Oman/Mỹ có hop_id nhưng dung_hop=false nên không đụng tới.
    if sp_moi:
        cuoi = [[sp_moi["variation"]["id"], sp_moi["quantity"], 0,
                 P.variation_label(sp_moi["variation"])]]
    else:
        sl = sl_moi or [it.get("quantity") or 0 for it in items_giu]
        cuoi = [[it.get("variation_id"), q,
                 (it.get("variation_info") or {}).get("retail_price") or 0,
                 (it.get("variation_info") or {}).get("name") or ""]
                for it, q in zip(items_giu, sl)]
    hop_them = 0
    if hop_id and cuoi and not any(c[0] == hop_id for c in cuoi):
        hop_them = sum(q for _v, q, _rp, ten in cuoi if A.la_trang_suc(ten))
        if hop_them:
            cuoi.append([hop_id, hop_them, 0, "hộp"])

    da_lam_hang = []
    if bo_dong:
        da_lam_hang.append("gỡ dòng hàng landing đẩy nhầm: " + ", ".join(
            f"{(it.get('variation_info') or {}).get('name')} x{it.get('quantity')}"
            for it in bo_dong))
    if sp_moi and tu_utm:
        da_lam_hang.append(f"mã SP {ten_uu_dai} lấy từ UTM quảng cáo "
                           f"(form landing không ghi tên SP)")
    if sl_moi:
        da_lam_hang.append(f"sửa số lượng {[it.get('quantity') for it in items_giu]}"
                           f"→{sl_moi} theo ưu đãi")
    if hop_them:
        da_lam_hang.append(f"kèm hộp 008 x{hop_them} (hàng trang sức)")
    items_moi = ([{"variation_id": c[0], "quantity": c[1],
                   "variation_info": {"retail_price": c[2]}} for c in cuoi]
                 if (da_lam_hang or sp_moi) else None)
    # != None -> TREO 'Mới' vì không còn cách nào liên lạc với khách. Từ 2026-09-04 đây CHỈ
    # là nhãn để ghi chú/log, KHÔNG còn là lệnh hủy (luật user đảo lại luật 24/08).
    sdt_hong = None
    if not sdt:
        can_check.append("đơn không có số điện thoại")
        sdt_hong = "đơn KHÔNG CÓ SỐ ĐIỆN THOẠI nào để liên hệ khách"
    elif loai_sdt == "ngoai":
        # LUẬT USER 2026-08-23: số nước ngoài (hay gặp: số Philippines) VẪN lên đơn được
        # ở mọi thị trường TRỪ nơi khai sdt_bat_buoc_ban_dia — điều kiện là số đó có
        # WhatsApp, do người chốt đơn bảo đảm chứ tool không kiểm được. Đơn giữ nguyên
        # mã nước để bên vận chuyển WhatsApp/gọi được.
        if A.MK.get("sdt_bat_buoc_ban_dia"):
            can_check.append(
                f"SĐT {sdt} là {mo_ta_sdt}, KHÔNG phải số {A.MK['ten']} — {A.MK['ten']} bắt buộc "
                f"số bản địa mới giao được đơn: gọi khách xin số {A.MK['ten']}")
        else:
            # Câu dặn riêng của thị trường (Saudi: cấm đẩy iMile) đứng TRƯỚC cho kho đọc
            # thấy ngay — nó quyết định đơn đi hãng nào, quan trọng hơn câu nhắc chung.
            if A.MK.get("ghi_chu_sdt_ngoai"):
                ghi_them.append(A.MK["ghi_chu_sdt_ngoai"])
            ghi_them.append(f"SĐT NƯỚC NGOÀI {sdt} ({mo_ta_sdt}) — bên vận chuyển liên hệ "
                            f"khách QUA WHATSAPP số này")
    elif loai_sdt == "hong":
        # BẰNG CHỨNG THẬT ĐỨNG TRƯỚC KHUÔN REGEX (luật user 2026-09-04): chính số này đã
        # giao tới tay khách thì nó gọi được, đừng bắt người kiểm lại lần nữa. Đặt trước cả
        # nhánh mo_ta_sdt: số đã giao được thì cũng không cần ai đi sửa mã nước cho nó.
        da_giao = don_da_giao_cua_sdt(sdt)
        if da_giao is not None:
            ghi_them.append(
                f"SĐT {sdt} không khớp khuôn số {A.MK['ten']} NHƯNG chính số này đã giao "
                f"thành công ở {_mo_ta_don(da_giao)} — số dùng được thật, lên đơn bình thường")
        elif mo_ta_sdt:
            # A.phan_loai_sdt chỉ kèm mô tả ở ca NGHI GÕ NHẦM MÃ NƯỚC — bỏ mã đi thì phần
            # còn lại là số bản địa hợp lệ, tức vẫn có số để thử gọi.
            can_check.append(mo_ta_sdt)
        else:
            lien_lac_duoc, vi_sao = chan_doan_sdt(sdt_goc, sdt)
            can_check.append(vi_sao)
            if not lien_lac_duoc:
                sdt_hong = vi_sao
    # CHỈ soi phần ghi chú của khách/nhân viên: ghi chú tool tự nối vào cũng có chữ "TREO",
    # soi cả chuỗi thì đơn nào bị treo 1 lần là khoá vĩnh viễn (đã kẹt 114 đơn vì lỗi này).
    if RE_TREO.search(re.split(r"\[Tự động", note)[0]):
        can_check.append("đơn đang bị sàng lọc/treo")

    return {"diachi": diachi, "tinh": tinh, "quan": quan, "xa": xa, "ma_bc": ma_bc,
            "cach_do_tinh": cach, "offer": offer,
            "gia": gia, "so_luong": so_luong, "sdt": sdt, "sdt_goc": sdt_goc, "loai_sdt": loai_sdt,
            "tien_moi": tien_moi, "sp_moi": sp_moi, "sl_moi": sl_moi, "sdt_hong": sdt_hong,
            "items_giu": items_giu, "bo_dong": bo_dong, "items_moi": items_moi,
            "da_lam_hang": da_lam_hang,
            "can_check": can_check, "ghi_them": ghi_them}


# ---------------- Chống trùng ----------------

_CACHE_SDT = {}          # {thị trường: (thời điểm, bảng)} — đỡ quét lại 400 đơn mỗi vòng daemon
# Dựng chỉ mục này tốn 20 trang × ~23 giây = ~8-11 PHÚT/thị trường (đo trên log server
# 2026-08-22: saudi 19:31:56 bắt đầu -> 19:43:22 mới xong, trong khi xử lý 7 đơn chỉ mất
# 29 giây). Để 5 phút thì vòng daemon nào cũng dựng lại từ đầu -> một vòng 11 thị trường
# mất gần 2 TIẾNG, đơn landing về lúc 15:51 tới 19:43 mới được lên.
# Để 1 tiếng AN TOÀN vì bảng này chỉ còn dùng cho chỉ mục ĐỊA CHỈ: phía SĐT đã hỏi thẳng
# POS qua tim_don_theo_sdt() mỗi lần xét nên luôn tươi. Trùng-khác-SĐT-cùng-địa-chỉ là ca
# hiếm (đo 14 ngày: uae 3 cặp, saudi 1) và chậm 1 tiếng vẫn bắt được ở vòng sau.
CACHE_GIAY = 3600

# Địa chỉ giống nhau tới mức này thì coi như một nhà (khách gõ lệch dấu phẩy/hoa thường).
# Để cao vì cùng một tòa nhà/con đường mà khác căn thì vẫn là hai khách khác nhau.
NGUONG_DIA_CHI = 0.95
# Địa chỉ quá ngắn ("1", "dubai") thì không đem so — dễ đụng nhầm nhà khác.
DAI_TOI_THIEU_DC = 20


def chuan_hoa_dia_chi(s):
    """Bỏ dấu, bỏ mọi ký tự không phải chữ/số — 'Al mizhar 3, Street 42' == 'AlMizhar3 street42'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def dia_chi_cua(o):
    """Địa chỉ để so trùng: ô giao hàng nếu đã có, không thì lấy từ ghi chú Webcake."""
    dc = ((o.get("shipping_address") or {}).get("address") or "").strip()
    if not dc:
        dong, _ = tach_note(o.get("note") or "")
        dc = ", ".join(dong)
    return chuan_hoa_dia_chi(dc)


def chi_muc_don(days=NGAY_CHONG_TRUNG):
    """Đơn gần đây (bỏ đơn đã hủy/xóa) lập chỉ mục 2 chiều: theo SĐT và theo địa chỉ.

    Khách bấm gửi form nhiều lần đôi khi gõ SĐT khác nhau (thiếu số, số người nhà),
    nên chỉ dò theo SĐT là lọt — dò thêm địa chỉ giống nhau.
    """
    luc, bang = _CACHE_SDT.get(_MKEY, (0, None))
    if bang is not None and time.time() - luc < CACHE_GIAY:
        return bang
    now = int(time.time())
    idx, dsdc = {}, []
    # PHẢI quét HẾT: UAE/Saudi có ~800 đơn/14 ngày, dừng ở 4 trang là mất một nửa bảng
    # đối chiếu -> đơn trùng lọt lưới và bị tự xác nhận (đã xảy ra: #68429, #68382, #68331).
    for pg in range(1, 21):
        data = P.fetch_orders({"startDateTime": now - days * 86400, "endDateTime": now,
                               "page_size": 100, "page_number": pg})
        for o in data:
            if o.get("status") in (6, 7):
                continue
            sdt = A.normalize_phone(o.get("bill_phone_number") or "")
            if sdt:
                idx.setdefault(sdt, []).append(o)
            dc = dia_chi_cua(o)
            if len(dc) >= DAI_TOI_THIEU_DC:
                dsdc.append((dc, o))
        if len(data) < 100:
            break
        time.sleep(0.2)
    bang = {"sdt": idx, "dc": dsdc}
    _CACHE_SDT[_MKEY] = (time.time(), bang)
    return bang


# {(thị trường, sđt, số ngày): [đơn]} — mỗi SĐT chỉ hỏi API 1 lần/VÒNG QUÉT, KHÔNG được
# sống qua vòng: cửa chống trùng đọc trạng thái đơn anh em từ đây, dữ liệu cũ một vòng là
# đọc ra "đơn kia vẫn Mới" trong khi nó đã đi rồi -> nhánh HỦY bản gửi lặp không bao giờ
# chạy. Xem xoa_dem_sdt() để biết ca thật đã tốn tiền vì chỗ này.
_CACHE_SDT_TIM = {}


def xoa_dem_sdt(sdt=None):
    """Vứt đệm tìm-đơn-theo-SĐT: cả đệm (sdt=None) hoặc mọi cửa sổ ngày của một số.

    🔴 CA THẬT 2026-09-07 (saudi, khách Mandy Callanan 0567491064) — hai lỗi chồng nhau
    làm cửa chống trùng câm hẳn, khách nhận 3 kiện cùng mã SP 246:

    1. Khoá đệm có BA phần `(thị trường, sđt, ngày)` nhưng chỗ xóa sau khi cho một đơn đi
       lại truyền khoá HAI phần -> `pop` không bao giờ trúng. #72502 được xác nhận lúc
       06:43:21, #72501 xử lý 4 GIÂY sau vẫn đọc danh sách chụp trước vòng nên không thấy
       anh em vừa đi -> cả hai cùng thắng phép "địa chỉ đầy đủ nhất" (65 / 66 / 71 điểm,
       mỗi bản chỉ so tay đôi với #72306) và cùng được đẩy.
    2. Đệm không có hạn dùng, mà daemon chạy liên tục nhiều ngày -> mục của số này đóng
       băng từ vòng HÔM TRƯỚC: #72306 đã "Đã gửi hàng"/COD 8900 vẫn hiện ra là "Mới, 0
       SAR", nên nhóm trùng rơi xuống nhánh "cả nhóm còn nằm im" thay vì nhánh "có đơn
       đang đi -> hủy bản gửi lặp". Gọi lại POS bằng đúng truy vấn đó cho ra `status 2`
       ngay: không phải API cũ, chỉ là mình đọc đồ hộp.

    Nên đệm này chỉ được sống TRONG một vòng quét: `chay_thi_truong` gọi `xoa_dem_sdt()`
    ở đầu vòng, và mỗi lần một đơn được cho đi thì xóa riêng số của nó.
    """
    for k in [k for k in _CACHE_SDT_TIM
              if sdt is None or (k[0] == _MKEY and k[1] == sdt)]:
        del _CACHE_SDT_TIM[k]


def tim_don_theo_sdt(sdt, ngay=NGAY_TIM_SDT):
    """Hỏi thẳng POS mọi đơn của số này (tham số `search`), cửa sổ `ngay` ngày.

    Chính xác hơn quét bảng: đơn trùng của khách có thể nằm ngoài 14 ngày gần nhất
    (ca thật #68331 — hai đơn cùng SP cách 18 ngày, quét bảng không thấy).
    """
    khoa = (_MKEY, sdt, ngay)
    if khoa in _CACHE_SDT_TIM:
        return _CACHE_SDT_TIM[khoa]
    now = int(time.time())
    ra = []
    # Số nước ngoài nay lưu dạng '+63917…' nhưng đơn cũ của CHÍNH khách đó có thể còn
    # lưu kiểu Webcake gửi lên ('09171234567') -> tìm bằng nguyên chuỗi là không thấy
    # bản trùng. Tìm bằng 9 chữ số cuối (nằm trong mọi cách viết), lọc chính xác ở dưới.
    tu_tim = re.sub(r"\D", "", sdt)[-9:] if sdt.startswith("+") else sdt
    try:
        for o in P.fetch_orders({"startDateTime": now - ngay * 86400, "endDateTime": now,
                                 "page_size": 100, "page_number": 1, "search": tu_tim}):
            if o.get("status") not in (6, 7) and A.normalize_phone(
                    o.get("bill_phone_number") or "") == sdt:
                ra.append(o)
    except (SystemExit, Exception) as e:   # noqa: BLE001 — lỗi tìm không được giết cả vòng
        A.log(f"⚠ Không tìm được đơn theo SĐT {sdt} ({e})")
    _CACHE_SDT_TIM[khoa] = ra
    return ra


def don_da_giao_cua_sdt(sdt):
    """Đơn GIAO THÀNH CÔNG gần nhất của chính số này, None nếu chưa từng có.

    LUẬT USER 2026-09-04: số bị khuôn regex thị trường chấm là "sai định dạng" mà chính
    số đó đã có đơn tới tay khách thì nó gọi được thật — bằng chứng thắng khuôn, đơn lên
    bình thường (không hủy, cũng không treo vì lý do SĐT). Nguyên văn: "nếu có lịch sử
    giao thành công thì đẩy đi bình thường, chứ số đó nước đó giao thành công, bạn lại
    hủy đơn vì sai số".

    Soi xa hơn cửa sổ chống trùng (NGAY_LICH_SU_GIAO) vì đây là câu hỏi KHÁC: chống trùng
    hỏi "khách vừa gửi lặp hả", còn ở đây hỏi "số này có thật không" — số đã giao được từ
    3 tháng trước thì hôm nay vẫn là số gọi được. Tra riêng nên không đụng phép chống trùng.
    """
    if not sdt:
        return None
    xong = [k for k in tim_don_theo_sdt(sdt, NGAY_LICH_SU_GIAO)
            if k.get("status") in TT_DA_GIAO_XONG]
    # Mốc giao gần nhất; POS thiếu status_history thì lùi về ngày tạo để vẫn xếp được thứ tự
    return max(xong, key=lambda k: (moc_da_nhan(k) or k.get("inserted_at") or "")) if xong else None


def trung_dia_chi(o, ds):
    """Các đơn khác có địa chỉ giống đơn này (so gần đúng, chịu được gõ lệch).

    Ngoài độ giống, bắt buộc TRÙNG CẢ CÁC CON SỐ trong địa chỉ: 'Villa 10' và 'Villa 16'
    cùng một con đường giống nhau tới 0.88 nhưng là hai nhà khác nhau (ca thật đã gặp).
    """
    dc = dia_chi_cua(o)
    if len(dc) < DAI_TOI_THIEU_DC:
        return []
    so = set(re.findall(r"\d+", dc))
    ra = []
    for dc_khac, k in ds:
        if k.get("id") == o.get("id") or set(re.findall(r"\d+", dc_khac)) != so:
            continue
        sm = difflib.SequenceMatcher(None, dc, dc_khac)
        if sm.real_quick_ratio() < NGUONG_DIA_CHI or sm.quick_ratio() < NGUONG_DIA_CHI:
            continue
        if sm.ratio() >= NGUONG_DIA_CHI:
            ra.append(k)
    return ra


def _mo_ta_don(k, ly_do=""):
    return (f"#{k.get('system_id') or k.get('id')} ({k.get('bill_full_name')}, "
            f"{P.STATUS_BY_CODE.get(k.get('status'), k.get('status'))}, "
            f"{P.fmt_money(k.get('money_to_collect'))}, "
            f"{(k.get('inserted_at') or '')[:16].replace('T', ' ')}"
            f"{', ' + ly_do if ly_do else ''})")


def _mo_ta_don_gon(k):
    """Mô tả đơn KHÔNG kèm trạng thái — dùng cho dòng ghi chú nói về bản CÒN ĐI TIẾP.

    ghi_chu_them() chống trùng bằng phép so nguyên văn, nên nhắc trạng thái của một đơn
    đang chạy là mỗi nấc nó đi qua (Chờ in -> Đã in -> Đang đóng -> Đã gửi -> Đã nhận)
    lại thành một dòng "mới" được nối thêm: ghi chú phình ra 5 lần cho cùng một việc.
    """
    return (f"#{k.get('system_id') or k.get('id')} ({k.get('bill_full_name')}, "
            f"{P.fmt_money(k.get('money_to_collect'))}, "
            f"{(k.get('inserted_at') or '')[:16].replace('T', ' ')})")


def _diem_dia_chi(k):
    """Điểm 'địa chỉ đầy đủ' của một bản trùng: (số dòng thật, có số nhà, tổng độ dài).

    Chấm từ GHI CHÚ GỐC khách điền, KHÔNG chấm từ ô địa chỉ giao hàng: ô đó bị tool
    sửa ngay trong lúc chạy nên bản lấy từ cache (dữ liệu cũ) và bản đang xử lý (dữ liệu
    mới) lệch nhau, mỗi đơn tự thấy mình hơn -> cả hai cùng được đi (đã lọt 7 nhóm).
    Ghi chú gốc thì bất biến nên hai chiều so sánh luôn cho cùng kết quả.
    """
    dong = dong_dia_chi_shopify(k) if la_shopify(k) else tach_note(k.get("note") or "")[0]
    that = [d for d in dong if not RAC_DONG.fullmatch(d.strip())]
    duong = that[:-2] or that              # 2 dòng cuối thường là thành phố + tỉnh
    return (len(that), 1 if any(re.search(r"\d", d) for d in duong) else 0,
            sum(len(d) for d in that))


def sdt_chet(k):
    """Đơn này có SĐT KHÔNG còn cách liên lạc không?

    Soi đúng bằng logic doc_don dùng để đặt `sdt_hong` — số 'hỏng' mà còn đọc ra được một
    số cụ thể để thử gọi thì KHÔNG tính là chết. Từ 2026-09-04 SĐT chết không còn làm đơn
    bị hủy; hàm này vẫn dùng để CHỌN BẢN ĐI trong nhóm trùng (bản gọi được đi trước).
    """
    goc = k.get("bill_phone_number") or (k.get("shipping_address") or {}).get("phone_number") or ""
    loai, sdt, mo_ta = A.phan_loai_sdt(goc)
    if loai != "hong":
        return False
    if not sdt:
        return True
    if mo_ta:                  # nghi gõ nhầm mã nước -> bỏ mã đi vẫn còn số hợp lệ để gọi
        return False
    return not chan_doan_sdt(goc, sdt)[0]


def _diem_ban_di(k):
    """Điểm chọn bản đại diện: SĐT gọi được ĐỨNG TRƯỚC địa chỉ đầy đủ.

    Nếu không xét SĐT trước thì bản địa chỉ đẹp mà SĐT chết vẫn thắng, rồi chính nó bị hủy
    vì SĐT — trong khi bản anh em còn gọi được đã bị hủy vì 'thua điểm địa chỉ', mất cả hai
    đơn của một khách. Chỉ xảy ra ở nhóm trùng THEO ĐỊA CHỈ (khác SĐT): hiếm nhưng có thật
    (đo 14 ngày: uae 3 cặp, saudi 1). Cả hai vế đều bất biến với chuẩn hóa SĐT/địa chỉ mà
    tool ghi đè trong lúc chạy nên bản cache và bản tươi vẫn chấm ra cùng điểm.
    """
    return (0 if sdt_chet(k) else 1,) + _diem_dia_chi(k)


def chon_ban_di(ds):
    """Bản được đi trong nhóm trùng: SĐT còn gọi được trước, rồi tới địa chỉ đầy đủ nhất;
    ngang điểm thì lấy bản tạo trước."""
    tot_nhat = max(_diem_ban_di(k) for k in ds)
    ngang = [k for k in ds if _diem_ban_di(k) == tot_nhat]
    return min(ngang, key=lambda k: (k.get("inserted_at") or "", str(k.get("id") or "")))


def ma_tu_note(o):
    """Mã SP đọc từ ô 'sản phẩm' của form Webcake ('217|Buy 1 Get 1: 109 SAR' -> '217').

    Dùng khi đơn KHÔNG có dòng hàng nào: sale tạo tay bỏ dở, hoặc landing khớp hụt tên SP
    nên POS chỉ có ghi chú. Ô tên trên form vẫn giữ nguyên thứ khách bấm, nên đối chiếu
    được mã — trước đây bỏ qua chỗ này nên đơn gửi lặp bị treo vô thời hạn (#69147 saudi
    treo vì đơn anh em #66552 trống dòng hàng, dù note ghi rõ cùng mã 217).

    CHỈ nhận MÃ SỐ đứng đầu ô tên — đúng chỗ do_san_pham() đọc, không đoán theo tên chữ.
    """
    for raw in re.split(r"[\r\n]+", o.get("note") or ""):
        s = raw.strip()
        if DONG_HE_THONG.match(s):
            break                      # hết phần khách điền, còn lại là máy nối thêm
        if "|" not in s:
            continue
        m = re.match(r"(\d{2,5})\b", s.split("|")[0].strip(" -–:"))
        if m:
            return {m.group(1)}
    # Form không gọi tên SP -> mã trong UTM (ma_sp_utm). Thiếu vế này thì đơn trống SP
    # của landing đổi form bị chấm "không đối chiếu được mã" và TREO luôn đơn thật khác
    # món của cùng khách — đúng kiểu kẹt #73385 mà luật 14/09 từng phải gỡ.
    ma = ma_sp_utm(o)
    return {ma} if ma else set()


def ma_cua_mau_ma(v):
    """Mã SP của một mẫu mã POS, đọc Y HỆT cách ma_san_pham() đọc dòng hàng trên đơn.

    Có hàm riêng vì hai bên phải ra CÙNG KIỂU MÃ mới so được: dòng hàng cho ra '217' còn
    mẫu mã vừa dò được mà lấy product_id thì ra id nội bộ -> so kiểu gì cũng lệch.
    """
    ten = (P.variation_label(v) or "").strip()
    m = re.match(r"(\d{2,5})\b", ten)
    return str(m.group(1) if m else (v.get("product_id") or v.get("id") or ten))


def ma_san_pham(o):
    """Mã sản phẩm trên đơn ('211 - Lockable Savings Binder' -> '211').

    Dùng để phân biệt khách GỬI LẶP một đơn với khách mua THÊM món khác.
    Tên không có mã thì lấy id mẫu mã làm khóa.
    Trống dòng hàng thì đọc tiếp ô sản phẩm trong ghi chú Webcake (ma_tu_note).

    🔴 HỘP KHÔNG PHẢI SẢN PHẨM — BỎ RA (user chốt 07/09/2026: "không check theo mã 008,
    vì đó là hộp đựng sản phẩm thôi"). Tool tự kèm hộp cho MỌI đơn trang sức (xem khối
    `hop_them` trong doc_don), nên để hộp trong phép so mã là hai đơn KHÁC HẲN SẢN PHẨM
    của cùng một khách vẫn "cùng mã SP" -> bị chấm trùng rồi hủy oan đơn thật. Đo 14 ngày
    07/09: 30 nhóm UAE + nhiều nhóm saudi bị dựng lên chỉ vì chung cái hộp (uae hiện ra
    là '008', saudi là UUID acef1e09… vì tên mẫu mã không có mã số đứng đầu — nhận diện
    bằng `variation_id` == hop_id nên đúng ở cả hai kiểu).
    Đơn CHỈ có hộp thì tập rỗng -> rơi xuống ma_tu_note rồi tới nhánh "không đối chiếu
    được mã SP" = treo cho người xem, không tự hủy. Đúng chiều an toàn.
    """
    hop_id = A.MK.get("hop_id") if A.MK else None
    ma = set()
    for it in (o.get("items") or []):
        if hop_id and it.get("variation_id") == hop_id:
            continue                   # hộp đựng, không phải món khách đặt
        vi = it.get("variation_info") or {}
        ten = (vi.get("name") or "").strip()
        m = re.match(r"(\d{2,5})\b", ten)
        ma.add(str(m.group(1) if m else (vi.get("product_id") or it.get("variation_id") or ten)))
    return {x for x in ma if x} or ma_tu_note(o)


def la_ten_test(ten):
    """Tên này là HÀNG TEST chứ không phải hàng bán thật?

    Bắt cả hàng test có thật trong POS ('SP TEST' — mọi thị trường đều có mẫu mã này)
    lẫn chữ rác khách gõ trên form ('test', 'N/A', 'none'…). Mã đứng đầu tên kiểu
    '000 - Test' cắt đi trước khi so. Từ 2026-09-02 chỉ cần CHỨA nguyên từ 'test'
    ('Test Red', 'Test Green' — dòng mẫu mã Webcake) là đã tính, xem TU_TEST.
    """
    s = re.sub(r"^\d{2,5}\s*[-–:]\s*", "", P.norm_ascii(ten)).strip()
    return bool(s) and bool(TU_TEST.search(s) or TEN_TEST.fullmatch(s)
                            or RAC_DONG.fullmatch(s))


def la_don_test(k):
    """Đơn SẢN PHẨM TEST: dòng hàng là hàng test ('SP TEST'…), HOẶC tên SP khách chọn
    trên form Webcake là chữ rác ('Test', 'N/A'…) — kể cả khi đơn CÓ dòng hàng.

    Vế "kể cả khi có dòng hàng" (user chốt 2026-09-01, qua #6265 Qatar): form ghi
    'Test|Buy 2: 109 QAR' nhưng Webcake vẫn gán dòng 'Mascara Sanzitang - 122' x310 —
    mã 122 và số lượng 310 đều móc từ Ô ĐỊA CHỈ khách gõ ('room 310', '1229'); #5909
    gõ '12'/'118' ra đúng '118 x12' chứng minh landing đó map ô địa chỉ vào mã SP/số
    lượng. Bản cũ chỉ đọc dòng form khi TRỐNG dòng hàng nên #6265 được xác nhận, in
    tem, tạo cả vận đơn IMILE. Đo 2000 đơn UAE/Saudi/Qatar/Kuwait: 0 đơn khách thật
    mang tên form 'Test' -> tin dòng form hơn dòng hàng, không chặn oan ai.

    LUẬT USER: đơn SP test KHÔNG được tính là đơn trùng — đơn thật của khách vẫn lên và
    chuyển 'Chờ in' bình thường (không hủy, cũng không treo lại chờ nhân viên). Còn khi
    CHÍNH đơn landing đang xét là hàng test thì chỉ đẩy nó lên 'Chờ hàng' (chuyen_cho_hang).

    Đọc thẳng dòng 'tên SP|ưu đãi' của form Webcake chứ không qua tach_note(): hàm đó
    cần regex tiền tệ của thị trường đang mở, mà đơn đem so có thể thuộc vòng quét khác.
    """
    items = k.get("items") or []
    # Đơn lẫn hàng test với hàng thật vẫn là thương vụ thật -> không kết luận theo dòng
    # hàng, nhưng dòng form bên dưới vẫn được quyền phán tiếp
    if items and all(la_ten_test((it.get("variation_info") or {}).get("name")) for it in items):
        return True
    if not items and not k.get("page_id") and not k.get("conversation_id"):
        # LUẬT USER 14/09/2026 ("đơn landing mà không có sản phẩm là đơn test"): form
        # landing về KHÔNG CÓ SẢN PHẨM — không dòng hàng và phần khách điền không có tên/mã
        # SP nào (không dòng 'tên SP|ưu đãi', hoặc dòng đó trống tên) -> là đơn TEST: chính
        # nó thì chuyển 'Chờ hàng', còn khi là đơn đối chiếu thì bỏ khỏi phép so trùng.
        # Trước đó kiểu này bị treo 'Mới' + "nhân viên xem tay" và chặn luôn đơn thật cùng
        # khách: saudi #73385 (0 SAR) treo #73386/#73389/#73551 (3 món khác nhau) 3 ngày.
        # Chỉ xét đơn KHÔNG gắn page/hội thoại — đơn chat trống SP là sale đang làm dở.
        khach = []
        for raw in re.split(r"[\r\n]+", k.get("note") or ""):
            s = raw.strip()
            if DONG_HE_THONG.match(s):
                break
            if s:
                khach.append(s)
        # NGOẠI LỆ 23/09/2026: UTM có mã SP (ma_sp_utm) thì khách đã đặt đúng một món cụ
        # thể, chỉ là landing đổi form bỏ mất tên SP — không phải đơn test. Ca thật saudi
        # #76401/#76479 (landing 256 space-bag-2) nằm 'Chờ hàng' vì thiếu vế này.
        if (not any(s.split("|")[0].strip(" -–:") for s in khach if "|" in s)
                and not ma_sp_utm(k)):
            return True
    for raw in re.split(r"[\r\n]+", k.get("note") or ""):
        s = raw.strip()
        if DONG_HE_THONG.match(s):
            break                      # hết phần khách điền, còn lại là máy nối thêm
        if TU_TEST.search(re.sub(r"https?://\S+", " ", s)):
            return True                # "có chữ test là chờ hàng" (user 2026-09-02)
        if "|" in s and la_ten_test(s.split("|")[0].strip(" -–:")):
            return True
    return False


def _im_lang_ngay(k):
    """Bao nhiêu ngày rồi không ai đụng vào đơn (theo updated_at POS trả về)."""
    moc = (k.get("updated_at") or k.get("inserted_at") or "")[:19]
    try:
        luc = time.mktime(time.strptime(moc, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return 0                       # không đọc được mốc thì coi như vừa đụng -> không kết luận
    return (time.time() - luc) / 86400.0


def don_ket(k):
    """Đơn đã rời 'Mới' nhưng NẰM CHẾT: ô địa chỉ giao hàng vẫn TRỐNG, chưa từng vào
    hàng in, cả tuần không ai đụng tới -> hãng không nhận đơn không có địa chỉ, nó không
    đi đâu cả.

    LUẬT USER 2026-08-22: đơn kiểu này KHÔNG được tính là 'đơn đã đi' để chặn bản landing
    phía sau. Hủy bản đầy đủ mà giữ bản chết thì khách chẳng nhận được gì — ca saudi
    #66552 (sale bấm xác nhận rồi bỏ dở, trống địa chỉ + trống dòng SP + không ĐVVC, nằm
    17 ngày) chặn mất #69147 đã đủ địa chỉ/SP/ĐVVC/COD; ca #65919 y hệt nhưng đậu ở
    'Chờ hàng' 20 ngày, chặn mất #65924. Bản đầy đủ được đi, bản chết bị hủy (nếu là
    landing) hoặc chỉ bị GHI CHÚ, giữ nguyên trạng thái (nếu là Facebook).

    BÓ HẸP: chỉ hai nấc NGƯỜI bấm rồi bỏ dở (TT_CO_THE_KET) — không đụng đơn đã vào hàng
    in, đã đóng gói hay đã gửi, vì mấy nấc đó kho đang cầm hàng thật. Đơn SP TEST cũng
    đậu ở 'Chờ hàng' nhưng la_don_test() đã lọc trước khi tới đây.

    USER MỞ RỘNG 30/08/2026: TRỐNG DÒNG HÀNG cũng là nằm chết, ngang với trống địa chỉ —
    kho không có gì để gói thì đơn không đi đâu được. Bằng chứng: 89/89 đơn Tây Ban Nha
    ĐÃ GỬI HÀNG đều có dòng hàng, chưa đơn trống nào từng đi. Ca gốc: saudi #67014 (người
    tạo tay từ chat 07/08, địa chỉ ĐẦY ĐỦ nên lọt lưới "trống địa chỉ", nhưng 0 dòng hàng
    và nằm im 23 ngày ở 'Chờ hàng') chặn mất #70453 đã đủ hàng/địa chỉ/COD — máy không đối
    chiếu được mã SP với đơn trống nên phải đẩy sang diện người xem tay.
    Đo 8 thị trường COD: 983 đơn ở hai nấc này, 447 đã bắt bằng vế địa chỉ, vế dòng hàng
    bắt thêm 64 đơn (Spain 43, Saudi 9, Qatar 8, Kuwait 2, Oman 1, Bahrain 1).
    """
    return (k.get("status") in TT_CO_THE_KET
            and (not ((k.get("shipping_address") or {}).get("address") or "").strip()
                 or not (k.get("items") or []))
            and not any(h.get("status") in (TT_CHO_IN, 13)
                        for h in (k.get("status_history") or []))
            and _im_lang_ngay(k) >= NGAY_KET)


def ly_do_ket(k):
    """Vì sao đơn này nằm chết — để ghi chú nói đúng chỗ hỏng thay vì một câu cứng."""
    thieu = []
    if not ((k.get("shipping_address") or {}).get("address") or "").strip():
        thieu.append("TRỐNG ô địa chỉ giao hàng")
    if not (k.get("items") or []):
        thieu.append("TRỐNG dòng sản phẩm")
    return " và ".join(thieu) or "thiếu dữ liệu để giao"


def _moc_trang_thai(k, cac_tt):
    """Mốc SỚM NHẤT đơn `k` chuyển vào một trong các trạng thái `cac_tt`.

    Trả None khi POS không kèm lịch sử: không biết mốc thì không kết luận gì được.
    """
    moc = [h.get("updated_at") for h in (k.get("status_history") or [])
           if h.get("status") in cac_tt and h.get("updated_at")]
    return min(moc) if moc else None


def moc_da_nhan(k):
    """Lúc đơn chuyển sang 'Đã nhận'/'Đã thu tiền' — mốc SỚM NHẤT trong lịch sử trạng thái."""
    return _moc_trang_thai(k, TT_DA_GIAO_XONG)


def moc_hoan(k):
    """Lúc đơn chuyển sang 'Đang hoàn'/'Đã hoàn'/'Hoàn một phần' — mốc SỚM NHẤT."""
    return _moc_trang_thai(k, TT_DA_HOAN)


def xet_nhom_trung(o, ex, idx):
    """Xét cả nhóm đơn CÙNG SĐT hoặc CÙNG ĐỊA CHỈ (14 ngày, đã bỏ đơn hủy/xóa).

    CHỈ tính là trùng khi CÙNG MÃ SẢN PHẨM — khách cùng địa chỉ/SĐT mà đặt món KHÁC
    là mua thêm thật, phải lên đơn bình thường (luật của user).

    Trả (bản_trùng, đơn_đã_có_người_xử_lý, bản_đại_diện, lý_do_trùng, đơn_khác_mã_SP,
         đơn_đã_nhận, đơn_không_đọc_được_mã, đơn_SP_test, đơn_nằm_chết):
      - đơn_nằm_chết: 'Đã xác nhận' mà trống địa chỉ cả tuần (don_ket) -> không chặn được
        bản landing phía sau; bản đầy đủ đi rồi thì hủy/treo nó (xu_ly_ban_ket).
      - đơn_đã_có_người_xử_lý: nhóm đã có đơn rời khỏi 'Mới' (đang đóng/đã gửi/đã xác nhận…)
        -> gần như chắc chắn là bản gửi lặp, KHÔNG được xác nhận thêm.
      - bản_đại_diện: khi cả nhóm còn 'Mới' (chưa giao thành công, chưa hoàn), chỉ bản
        đầy đủ nhất được xác nhận, các bản còn lại bị HỦY (user chốt 2026-08-24).
      - đơn_cần_xem_tay: không đủ dữ kiện để kết luận -> chỉ treo, tuyệt đối không tự hủy.
      - đơn_SP_test: loại hẳn khỏi phép so trùng, đơn thật đi tiếp bình thường.

    NGOẠI LỆ "KHÁCH ĐẶT LẠI" (luật user 2026-08-20, siết lại bản 19/08; mở rộng sang cả
    ca hoàn hàng 2026-08-24): đơn cũ đã 'Đã nhận'/'Đã thu tiền' hoặc 'Đã hoàn'/'Đang hoàn'/
    'Hoàn một phần' CHƯA đủ để kết luận mua lại — phải thêm điều kiện đơn mới được tạo
    SAU mốc đó (mốc nhận hàng hoặc mốc hàng hoàn về). Bản 19/08 chỉ xét trạng thái HIỆN
    TẠI nên đơn tồn càng lâu càng dễ lọt: khách bấm gửi form 2 lần cách nhau 2-4 phút, đơn
    đầu 3 ngày sau giao xong, tới lúc quét lại thì bản gửi lặp được thả lên Chờ in (#45213,
    #45497, #46640, #45177, #45659 — có ca #45659 còn được tạo TRƯỚC đơn kia 62 phút).
    """
    cung_nha, ly_do = {}, {}
    for k in (tim_don_theo_sdt(ex["sdt"]) if ex["sdt"] else []):
        if k.get("id") != o.get("id"):
            cung_nha[k["id"]], ly_do[k["id"]] = k, "cùng SĐT"
    for k in trung_dia_chi(o, idx["dc"]):
        if k["id"] not in cung_nha:
            # PHẢI đọc lại trạng thái: nhánh này lấy đơn từ bảng chỉ mục có đệm 1 tiếng
            # (CACHE_GIAY), tức là đơn anh em vừa được đẩy vẫn hiện ra là 'Mới' -> lại
            # đúng lỗi đã làm hỏng ca Mandy Callanan 07/09/2026, chỉ khác là cũ tối đa 1
            # tiếng thay vì cả ngày. Rẻ: nhánh trùng-khác-SĐT-cùng-địa-chỉ rất hiếm (đo
            # 14 ngày: uae 3 cặp, saudi 1) nên mỗi vòng thêm vài lượt GET là cùng.
            cung_nha[k["id"]], ly_do[k["id"]] = lam_tuoi_trang_thai(k), "cùng địa chỉ"

    # Đơn chưa có dòng hàng (tool vừa dò ra SP): phải quy mẫu mã về ĐÚNG KIỂU MÃ mà
    # ma_san_pham() đọc từ dòng hàng của đơn kia — lấy product_id thô là mã nội bộ POS,
    # đem so với '217' thì KHÔNG BAO GIỜ khớp nên mọi đơn kiểu này bị gán "khác mã SP"
    # rồi cho đi thẳng (ca saudi #69327 lên đơn dù #66243 cùng mã 217 đang trên đường giao).
    # sp_moi ĐỨNG TRƯỚC: từ 23/09 nó còn là SP THAY cho dòng hàng landing gắn nhầm (#76497
    # 'BOX'), khi đó ma_san_pham(o) đọc ra mã của dòng rác chứ không phải món khách đặt.
    ma_minh = ({ma_cua_mau_ma(ex["sp_moi"]["variation"])} if ex["sp_moi"] else set()) \
        or ma_san_pham(o)
    nhom, khac_ma, da_nhan, xem_tay, don_test, ket_som = {}, [], [], [], [], []
    tao_luc = o.get("inserted_at") or ""
    for kid, k in cung_nha.items():
        if la_don_test(k):
            don_test.append(k)           # SP test -> không phải thương vụ, bỏ khỏi phép so
            continue
        if k.get("status") in TT_DA_GIAO_XONG or k.get("status") in TT_DA_HOAN:
            da_hoan = k.get("status") in TT_DA_HOAN
            moc = moc_hoan(k) if da_hoan else moc_da_nhan(k)
            if not moc:
                xem_tay.append((k, f"đơn kia đã {'hoàn' if da_hoan else 'giao xong'} nhưng POS "
                                   f"không trả về mốc nên không biết đây là mua lại hay gửi lặp"))
                continue
            if tao_luc > moc:
                da_nhan.append(k)        # tạo SAU khi khách cầm hàng/hàng hoàn về -> mua lại thật
                continue
            # Tạo TRƯỚC mốc đó -> khách chưa cầm được gì (hoặc hàng còn chưa hoàn xong) để
            # mà mua lại, đây là bản gửi lặp. Cho rơi xuống phép so mã SP như trùng bình thường.
        ma_kia = ma_san_pham(k)
        if not ma_minh or not ma_kia:
            if don_ket(k):
                # NẰM CHẾT (trống địa chỉ hoặc trống dòng hàng, cả tuần không ai đụng,
                # chưa từng vào hàng in) -> nó không đi đâu được nên KHÔNG phải bản đang
                # cạnh tranh, đừng bắt người xem tay. Nhánh "không đối chiếu được mã SP"
                # bên dưới chặn TRƯỚC khi tới phép lọc `ket`, nên phải xét ở đây mới ăn —
                # ca gốc saudi #67014 (người tạo tay 07/08, địa chỉ ĐỦ nhưng 0 dòng hàng,
                # nằm im 23 ngày ở 'Chờ hàng') treo mất #70453 suốt 2 ngày.
                ket_som.append(k)
                continue
            # Còn lại là đơn trống sản phẩm nhưng KHÔNG phải SP test và VẪN CÒN SỐNG (sale
            # tạo tay bỏ dở, đơn landing khớp hụt tên SP). Không đọc được mã thì KHÔNG
            # chứng minh được trùng mã -> chỉ treo, không hủy. Thiếu chốt này đã hủy oan
            # #47112, #47146 (UAE) và #6090 (Qatar): đơn giữ lại trống SP, đơn bị hủy có
            # SP hẳn hoi.
            xem_tay.append((k, "đơn kia không có dòng sản phẩm nào nên không đối chiếu "
                               "được mã SP"))
            continue
        if not (ma_minh & ma_kia):
            khac_ma.append(k)            # mua món khác -> không phải đơn trùng
            continue
        nhom[kid] = k
        ly_do[kid] += f" + cùng mã SP {'/'.join(sorted(ma_minh & ma_kia))}"

    khac = list(nhom.values())
    # Đơn 'Đã xác nhận' mà nằm chết (trống địa chỉ, cả tuần không ai đụng) thì không giao
    # được -> KHÔNG tính là bản đang đi, cũng không được chọn làm bản đại diện.
    ket = [k for k in khac if don_ket(k)] + ket_som
    id_ket = {k["id"] for k in ket}
    # Đơn đã rời 'Mới'/'Chờ xác nhận' = thương vụ ĐANG/ĐÃ đi (kể cả đơn Facebook, kể cả
    # đơn đã hoàn) -> nó là bản được đi, đơn landing đang xét là bản thừa.
    dang_di = [k for k in khac if k.get("status") not in TT_CHUA_DI and k["id"] not in id_ket]
    # Cả nhóm còn nằm im -> LUẬT USER: bản có ĐỊA CHỈ ĐẦY ĐỦ NHẤT được đi, không
    # phân biệt nguồn landing/Facebook, không quan tâm tạo trước hay sau.
    ban_di = (chon_ban_di([k for k in khac if k["id"] not in id_ket] + [o])
              if not dang_di else None)
    return khac, dang_di, ban_di, ly_do, khac_ma, da_nhan, xem_tay, don_test, ket


# ---------------- Xử lý ----------------

def _giu_dia_chi(addr_cu, sdt_moi=None):
    """Chép lại NGUYÊN khối địa chỉ giao hàng đang có để gửi kèm khi PUT trường khác.

    POS coi shipping_address là một khối: thiếu khóa nào trong body là nó xóa khóa đó
    (đã mất district vì gửi thiếu district_id, mất cả ô địa chỉ vì chỉ gửi SĐT).
    """
    sa = {k: addr_cu.get(k) for k in ("full_name", "phone_number", "address",
                                      "province_id", "district_id", "commune_id", "post_code")
          if addr_cu.get(k)}
    if not sa:
        return None
    if sa.get("province_id"):
        sa["country_code"] = addr_cu.get("country_code") or P.COUNTRY_CODE
    # SĐT người nhận mà quy về cùng một số với SĐT khách thì chỉ là khác cách viết ->
    # ghi luôn bản chuẩn cho hai ô khỏi lệch (POS đồng bộ ngược lên bill, lệch là vòng
    # sau tool lại thấy "chưa chuẩn hóa" rồi PUT lại mãi). Khác số thật thì giữ nguyên:
    # có đơn nhân viên điền SĐT người nhận hộ khác SĐT đặt hàng.
    if sdt_moi and sa.get("phone_number") and A.normalize_phone(sa["phone_number"]) == sdt_moi:
        sa["phone_number"] = sdt_moi
    return sa


def chuyen_cho_hang(o, ma, dry):
    """Đơn landing bán HÀNG TEST -> chỉ đẩy lên 'Chờ hàng' (luật user 2026-08-21).

    KHÔNG xác nhận, KHÔNG chuyển 'Chờ in': vào hàng in là kho in phiếu rồi đóng gói gửi
    hàng test đi thật. Cũng không điền địa chỉ/ĐVVC và không đem so trùng — đơn này không
    phải thương vụ của khách nên chẳng đi đâu cả.
    """
    if dry:
        A.log(f"  [THỬ] #{ma}: HÀNG TEST → sẽ chuyển CHỜ HÀNG")
        return "(thử) hàng test → sẽ chuyển Chờ hàng"
    ghi_chu = ("[Tự động LP] đơn bán HÀNG TEST — chuyển CHỜ HÀNG, "
               "không xác nhận, không cho vào Chờ in.")
    items = o.get("items") or []
    if items and not all(la_ten_test((it.get("variation_info") or {}).get("name"))
                         for it in items):
        # Ca #6265: form ghi 'Test' nhưng Webcake vẫn gán dòng hàng thật (mã/số lượng
        # móc từ ô địa chỉ) — dòng hàng là rác, phải báo marketer sửa trang landing
        ghi_chu += (" ⚠ Form ghi tên SP 'Test' nhưng đơn có dòng hàng thật — nghi landing "
                    "map nhầm mã SP/số lượng từ ô địa chỉ, báo marketer kiểm tra lại trang.")
    note_cu = (o.get("note") or "").strip()
    body = {"status": TT_CHO_HANG}
    if ghi_chu not in note_cu:         # xử lý lại đơn cũ thì đừng nối thêm dòng y hệt
        body["note"] = (note_cu + "\n" + ghi_chu).strip()
    P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{o.get('id')}", body=body)
    A.log(f"  ⏸ #{ma} HÀNG TEST → CHỜ HÀNG")
    return "hàng test → đã chuyển Chờ hàng"


def xu_ly_mot(o, idx, dry, tu_xac_nhan=True):
    oid = o.get("id")
    ma = o.get("display_id") or o.get("system_id") or oid
    ex = doc_don(o)
    can_check = list(ex["can_check"])

    # LUẬT USER: mọi đơn landing bán HÀNG TEST chỉ được lên 'Chờ hàng'. Xét trước mọi
    # thứ khác — khỏi tốn lượt quét trùng, và cũng không được hủy nó như đơn trùng.
    # Vế sp_moi: form ghi tên hơi khác nhưng dò ra đúng mẫu mã 'SP TEST' trong POS.
    if la_don_test(o) or (ex["sp_moi"]
                          and la_ten_test(P.variation_label(ex["sp_moi"]["variation"]))):
        return chuyen_cho_hang(o, ma, dry)

    # Cảnh báo cho nhân viên, KHÔNG chặn xác nhận (doc_don đã bỏ sẵn cảnh báo SĐT nước
    # ngoài vào đây — đơn vẫn chạy, chỉ cần kho/ĐVVC biết mà WhatsApp cho khách).
    ghi_them = list(ex.get("ghi_them") or [])
    (khac, dang_di, ban_di, ly_do, khac_ma, da_nhan,
     xem_tay, don_test, ket) = xet_nhom_trung(o, ex, idx)
    # Luật user: trùng SĐT hoặc địa chỉ + CÙNG MÃ SẢN PHẨM, tính cả đơn Facebook lẫn
    # landing -> CHỈ MỘT đơn được đi, các bản còn lại treo kèm lý do cụ thể.
    # CHỈ CÒN 1 NHÓM LÝ DO được tự hủy thật — ngoài nhóm này KHÔNG được tự hủy, dù nghi ngờ
    # cỡ nào (nhóm (2) SĐT hỏng đã bị user gỡ ngày 2026-09-04, nay chỉ treo):
    #   (1) TRÙNG khách + trùng mã SP mà đơn đối chiếu CHƯA giao thành công, CHƯA hoàn
    #       (đơn kia đang Mới/Chờ xác nhận/Chờ in/đang giao/... hoặc đã hoàn/đang hoàn/hoàn
    #       một phần TẠO TRƯỚC mốc hoàn) -> rõ ràng bản gửi lặp của cùng một thương vụ.
    #       NGOẠI LỆ: đơn này được tạo SAU mốc khách nhận hàng / SAU mốc hàng hoàn về của
    #       đơn kia -> coi là ĐẶT LẠI THẬT, tuyệt đối không hủy, lên đơn bình thường
    #       (đã lọc sẵn ở xet_nhom_trung -> rơi vào da_nhan, không vào dang_di/khac).
    #   (2) ĐÃ GỠ 2026-09-04 — SĐT sai/thừa/thiếu chữ số nay chỉ TREO 'Mới' + ghi lý do.
    #       Cửa "sai định dạng" thực chất là khuôn regex chỉ nhận di động, nên số cố định
    #       và số nước ngoài viết kiểu bản địa đều bị chấm oan (#1754 Spain: hủy vì
    #       981299245 "sai định dạng", trong khi chính số đó đã nhận hàng ở #1554).
    huy_vi = None          # khác None = HỦY THẬT đơn này, kèm lý do cụ thể trong ghi chú
    nhan_huy = "TRÙNG"     # nhãn ngắn cho log + câu chốt ghi vào ghi chú đơn
    ket_huy = "Bản landing gửi lặp nên hủy luôn theo quy định."
    # Đơn TỪNG vào hàng in: vẫn hủy, nhưng ghi chú thật to để kho tự kiểm tra và rút phiếu —
    # hủy trong POS không tự rút phiếu ở kho về, không rút thì hàng vẫn bị đóng gói gửi đi.
    da_vao_hang_in = any(h.get("status") in (TT_CHO_IN, 13)
                         for h in (o.get("status_history") or []))
    if dang_di:
        huy_vi = ("trùng khách + trùng mã sản phẩm với đơn đã đi (chưa giao thành công/"
                  "chưa hoàn hoặc tạo TRƯỚC mốc giao/hoàn của đơn kia): "
                  + ", ".join(_mo_ta_don(k, ly_do.get(k["id"], "")) for k in dang_di[:3]))
    elif ban_di is not None and ban_di is not o:
        # Cả nhóm còn 'Mới' (chưa giao thành công, chưa hoàn) -> bản địa chỉ đầy đủ hơn
        # được đi, đơn landing này thiếu hơn nên hủy luôn.
        huy_vi = ("trùng khách + trùng mã sản phẩm, cả hai đều chưa giao/chưa hoàn — đơn kia "
                  "có địa chỉ đầy đủ hơn nên được đi: "
                  + _mo_ta_don(ban_di, ly_do.get(ban_di["id"], "")))
    elif khac:
        ghi_them.append("địa chỉ đầy đủ nhất trong nhóm trùng nên được đi; các bản trùng: "
                        + ", ".join(_mo_ta_don(k, ly_do.get(k["id"], "")) for k in khac[:3]))
    # SĐT hỏng: KHÔNG hủy nữa (luật user 2026-09-04) — lý do đã nằm sẵn trong can_check nên
    # đơn tự treo lại ở 'Mới' kèm câu chỉ rõ số hỏng ở đâu, người kiểm rồi quyết.
    if huy_vi and da_vao_hang_in:
        huy_vi += (". ⚠ ĐƠN NÀY ĐÃ TỪNG VÀO HÀNG IN — phiếu giao có thể đã in và đang ở kho, "
                   "nhân viên kho phải tìm rút phiếu của đơn này ra, đừng đóng gói gửi đi")
    if da_nhan:
        ghi_them.append("đặt lại THẬT (đơn trước đã nhận/hoàn), không hủy: "
                        + ", ".join(_mo_ta_don(k, ly_do.get(k["id"], "")) for k in da_nhan[:3]))
    if khac_ma:
        # Cùng khách nhưng MÃ SP KHÁC -> mua thêm thật, vẫn lên đơn, chỉ ghi chú cho biết
        ghi_them.append("khách còn đơn khác mã SP (không tính trùng, vẫn lên đơn): "
                        + ", ".join(_mo_ta_don(k, ly_do.get(k["id"], "")) for k in khac_ma[:3]))
    if xem_tay:
        # Không đủ căn cứ hủy nhưng cũng không dám tự xác nhận: để 'Mới' cho nhân viên
        # mở hai đơn ra so tay rồi quyết.
        can_check.append("NGHI TRÙNG nhưng chưa đủ căn cứ kết luận — nhân viên xem tay: "
                         + "; ".join(f"{_mo_ta_don(k, ly_do.get(k['id'], ''))} — {vi_sao}"
                                     for k, vi_sao in xem_tay[:3]))
    if don_test:
        # Chỉ ghi chú cho biết — KHÔNG chặn xác nhận (luật user: SP test không tính trùng)
        ghi_them.append("khách còn đơn SẢN PHẨM TEST (không tính trùng, vẫn lên đơn): "
                        + ", ".join(_mo_ta_don(k, ly_do.get(k["id"], "")) for k in don_test[:3]))
    if ket and not huy_vi:
        # Bản trùng 'Đã xác nhận' nhưng nằm chết (trống địa chỉ) -> đơn này đi thay,
        # bản chết sẽ bị hủy/treo ngay sau khi đơn này được cho đi (xu_ly_ban_ket).
        ghi_them.append("bản trùng nằm chết nên đơn này đi thay: "
                        + ", ".join(f"{_mo_ta_don(k, ly_do.get(k['id'], ''))} — {ly_do_ket(k)}"
                                    for k in ket[:3]))

    body = {}
    da_lam = []
    addr_cu = o.get("shipping_address") or {}
    dc_cu = (addr_cu.get("address") or "").strip()
    thieu_tinh = ex["tinh"] and not addr_cu.get("province_id")
    thieu_quan = ex["quan"] and not addr_cu.get("district_id")
    thieu_xa = ex["xa"] and not addr_cu.get("commune_id")
    thieu_ma_bc = ex["ma_bc"] and not addr_cu.get("post_code")
    if (ex["diachi"] and not dc_cu) or thieu_tinh or thieu_quan or thieu_xa or thieu_ma_bc:
        # TUYỆT ĐỐI KHÔNG ghi đè ô địa chỉ đã có: Webcake ở một số nước điền sẵn số nhà/
        # block/tầng vào đây trong khi ghi chú chỉ có tỉnh + xã. Ghi đè là mất địa chỉ giao
        # hàng thật (đã xóa nhầm đơn Romania #584: 'Ion Borcea Bloc C1 Etaj 4, Ap. 413').
        # Đơn đã có địa chỉ thì chỉ bổ sung tỉnh/thành.
        # Ô SĐT người nhận là chỗ ĐVVC đọc để gọi/WhatsApp: nếu số đang có chỉ là cách
        # viết khác của số chuẩn thì ghi bản chuẩn (số nước ngoài phải còn '+mã nước',
        # không thì shipper không liên hệ được). Khác số thật thì giữ nguyên — có đơn
        # nhân viên điền SĐT người nhận hộ.
        sdt_nn = addr_cu.get("phone_number") or ""
        if ex["sdt"] and (not sdt_nn or A.normalize_phone(sdt_nn) == ex["sdt"]):
            sdt_nn = ex["sdt"]
        sa = {"full_name": addr_cu.get("full_name") or o.get("bill_full_name") or "",
              "phone_number": sdt_nn,
              "address": dc_cu or ex["diachi"]}
        if ex["tinh"] or addr_cu.get("province_id"):
            sa["province_id"] = addr_cu.get("province_id") or ex["tinh"]
            sa["country_code"] = P.COUNTRY_CODE
        # ĐVVC cần tới cấp quận/huyện (và phường/xã nếu nước đó có) — để trống là
        # nhân viên phải mở từng đơn chọn tay.
        if addr_cu.get("district_id") or ex["quan"]:
            sa["district_id"] = addr_cu.get("district_id") or ex["quan"]
        if addr_cu.get("commune_id") or ex["xa"]:
            sa["commune_id"] = addr_cu.get("commune_id") or ex["xa"]
        if addr_cu.get("post_code") or ex["ma_bc"]:
            sa["post_code"] = addr_cu.get("post_code") or ex["ma_bc"]
        body["shipping_address"] = sa
        cap = [x for x in (("tỉnh" if thieu_tinh else ""), ("quận/huyện" if thieu_quan else ""),
                           ("phường/xã" if thieu_xa else ""),
                           (f"mã bưu chính {ex['ma_bc']}" if thieu_ma_bc else "")) if x]
        da_lam.append((f"bổ sung {'+'.join(cap)}" if dc_cu else "điền địa chỉ")
                      + (f" ({ex['cach_do_tinh']})" if ex["tinh"] else " (CHƯA có tỉnh)"))
    if ex["sdt"] and ex["sdt"] != (o.get("bill_phone_number") or ""):
        body["bill_phone_number"] = ex["sdt"]
        da_lam.append(f"chuẩn hóa SĐT {ex['sdt_goc']}→{ex['sdt']}")
        if "shipping_address" not in body:
            # ĐO ĐƯỢC TRÊN ĐƠN THẬT (qatar #6095, uae #46692, saudi #67605): POS PHẢN CHIẾU
            # bill_phone_number xuống ô địa chỉ giao — PUT chỉ mỗi SĐT là nó THAY nguyên khối
            # shipping_address bằng object rỗng chỉ có số điện thoại (bay số nhà + tỉnh +
            # quận) và tiện thể xóa luôn phí chuyển về 0. Đổi SĐT thì phải gửi kèm địa chỉ cũ.
            sa_giu = _giu_dia_chi(addr_cu, ex["sdt"])
            if sa_giu:
                body["shipping_address"] = sa_giu
    if not (o.get("partner") or {}).get("partner_id"):
        # ĐVVC lấy từ markets.json (uae J&T UAE, saudi VPN, romania/spain eushipments…);
        # Mỹ đổi theo sản phẩm nên vẫn đi qua chon_dvvc. Đơn đã có ĐVVC thì không đụng.
        # Dùng dòng hàng CÒN GIỮ: dòng landing đẩy nhầm mà lọt vào đây là chọn nhầm hãng
        # (thị trường Mỹ đổi ĐVVC theo tên sản phẩm).
        ten_sp = " ".join(((i.get("variation_info") or {}).get("name") or "")
                          for i in ex["items_giu"])
        if ex["sp_moi"]:
            ten_sp += " " + P.variation_label(ex["sp_moi"]["variation"])
        dvvc = A.chon_dvvc(ten_sp)
        if dvvc:
            body["partner"] = {"partner_id": dvvc["id"], "custom_partner_id": dvvc["id"],
                               "partner_name": dvvc["ten"]}
            da_lam.append(f"ĐVVC {dvvc['ten']}")
        else:
            can_check.append(f"thị trường {A.MK['ten']} chưa khai ĐVVC trong markets.json")
    # LUẬT USER 2026-08-26: đơn nước nào phải mang TIỀN TỆ nước đó — Webcake đổ đơn
    # landing UAE/Saudi về POS với order_currency=CNY (nhân dân tệ), COD 99 hóa ¥99.
    # Đo trên đơn thật #47721 (UAE): PUT order_currency đổi được CNY→AED, không đụng
    # phí chuyển/COD/trạng thái. Mã POS lưu có thể khác nhãn hiển thị (Đài Loan NT$
    # nhưng POS lưu TWD) nên ưu tiên ma_tien_te trong markets.json.
    ma_tien = A.MK.get("ma_tien_te") or A.MK.get("tien_te")
    if ma_tien and (o.get("order_currency") or "") != ma_tien:
        body["order_currency"] = ma_tien
        da_lam.append(f"sửa tiền tệ {o.get('order_currency') or '?'}→{ma_tien}")
    if ex["tien_moi"]:
        body["shipping_fee"] = ex["tien_moi"]
        da_lam.append(f"điền COD {P.fmt_money(ex['tien_moi'])}")
    elif (("shipping_address" in body or "partner" in body or "bill_phone_number" in body)
          and (o.get("shipping_fee") or 0)):
        # ĐO ĐƯỢC TRÊN ĐƠN THẬT: POS XÓA phí chuyển về 0 mỗi khi mình ghi lại ô địa chỉ
        # giao hàng — hoặc chỉ đổi SĐT (nó tự đụng vào địa chỉ). Không gửi kèm là đơn mất
        # sạch tiền thu khách (đã hỏng 10 đơn vì địa chỉ, thêm qatar #6095 vì SĐT).
        body["shipping_fee"] = o["shipping_fee"]
    if ex["items_moi"] is not None:
        # POS THAY cả mảng items, dòng nào không gửi kèm là bị gỡ khỏi đơn -> doc_don đã
        # dựng sẵn NGUYÊN danh sách cuối cùng (gỡ rác + sửa số lượng + kèm hộp), ở đây chỉ
        # gửi đi, không được ghép thêm mảnh nào nữa.
        body["items"] = ex["items_moi"]
        if ex["sp_moi"]:
            da_lam.append(f"thêm sản phẩm {P.variation_label(ex['sp_moi']['variation'])}"
                          f" x{ex['sp_moi']['quantity']}")
        da_lam += ex["da_lam_hang"]

    du = not can_check and not huy_vi and tu_xac_nhan
    cho_xn = du and not khach_da_xn(o)                # XN_KHACH_2909
    if cho_xn:
        du = False
    # Ghi chú cho NGƯỜI đọc (chủ shop 18/09: "đọc xong không biết lỗi không lên được đơn là
    # gì") -> câu đầu là KẾT LUẬN + LÝ DO, việc tool đã điền để sau, lưu ý để cuối.
    loi = "; ".join(can_check)
    if huy_vi:
        ghi_chu = f"[Tự động LP] ĐÃ HỦY ({nhan_huy}): {huy_vi}. {ket_huy}"
    elif du:
        ghi_chu = "[Tự động LP] ĐÃ XÁC NHẬN → CHỜ IN."
    elif cho_xn:
        ghi_chu = ("[Tự động LP] ĐỦ DỮ LIỆU — CHỜ KHÁCH XÁC NHẬN QUA WHATSAPP/MESS, chưa lên "
                   "Chờ in. Có thẻ XN QUA WA / XN QUA MESS thì máy tự lên Chờ in.")
    elif can_check:
        ghi_chu = f"[Tự động LP] ⚠ CHƯA XÁC NHẬN — {loi}."
    else:
        ghi_chu = "[Tự động LP] Đủ dữ liệu, chờ nhân viên bấm xác nhận."
    if da_lam:
        ghi_chu += " Đã điền: " + ", ".join(da_lam) + "."
    if ghi_them:
        ghi_chu += " Lưu ý: " + "; ".join(ghi_them) + "."
    # Đơn còn 'Mới' được xét lại mỗi GIO_XET_LAI giờ -> lần xét lại KHÔNG điền thêm gì và
    # lý do treo vẫn y cũ (đã nằm trong ghi chú) thì im, không nối dòng nữa. Trước đây chỉ
    # so nguyên câu: lần 1 "điền địa chỉ… — THIẾU TỈNH", lần 2 "không phải bổ sung gì —
    # THIẾU TỈNH" khác nhau nên đơn #50260/#50262 mỗi vòng thêm một dòng dài y hệt.
    note_cu = (o.get("note") or "").strip()
    lap_lai = ("[Tự động LP]" in note_cu and not da_lam
               and ((loi and loi in note_cu)
                    or note_cu.rsplit("[Tự động LP]", 1)[-1].strip()
                    == ghi_chu.split("[Tự động LP]", 1)[-1].strip()))
    if huy_vi or not lap_lai:          # đơn sắp hủy thì luôn ghi lý do, kể cả trùng lời
        body["note"] = (note_cu + "\n" + ghi_chu).strip()

    if dry:
        tom_tat = (f"{nhan_huy} → sẽ HỦY" if huy_vi else "ĐỦ → sẽ xác nhận" if du else
                   "ĐỦ → để Mới chờ khách XN WA/Mess" if cho_xn else
                   ("ĐỦ → chỉ điền, để nhân viên xác nhận" if not can_check else "THIẾU → để Mới"))
        A.log(f"  [THỬ] #{ma}: {tom_tat} | "
              f"{ex['sdt'] or '-'} | {ex['diachi'] or '(không có địa chỉ)'} | tỉnh {ex['tinh'] or '?'} "
              f"| {P.fmt_money(o.get('money_to_collect') or ex['tien_moi'] or 0)}"
              f"{' | ' + huy_vi if huy_vi else ''}"
              f"{' | ' + '; '.join(can_check) if can_check else ''}"
              f"{' | LƯU Ý: ' + '; '.join(ghi_them) if ghi_them else ''}")
        return f"(thử) {tom_tat}"

    if huy_vi:
        # Chỉ ghi ghi chú rồi hủy — không cần điền địa chỉ/ĐVVC cho đơn sắp hủy. Ghi chú
        # LUÔN nêu rõ lý do cụ thể (huy_vi) để nhân viên đối chiếu lại được nếu cần.
        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body={"note": body["note"]})
        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body={"status": TT_HUY})
        A.log(f"  ✖ #{ma} ĐÃ HỦY ({nhan_huy.lower()}): {huy_vi}")
        return f"đã hủy vì {nhan_huy.lower()}: {huy_vi}"

    if body:                           # xét lại mà không có gì mới thì khỏi gọi API
        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body=body)
    if du and ex["sdt"]:
        # Bản trùng xử lý sau phải thấy đơn này đã đi -> hỏi lại POS thay vì dùng đệm cũ.
        # PHẢI xóa qua xoa_dem_sdt(): khoá đệm có 3 phần, `pop` bằng khoá 2 phần trượt
        # sạch (ca #72501/#72502 ngày 07/09/2026 — hai đơn cùng khách cùng mã SP cách
        # nhau 4 giây đều được đẩy vì đơn sau vẫn đọc đệm cũ).
        xoa_dem_sdt(ex["sdt"])
    if du:
        # Mới -> Đã xác nhận -> Chờ in (đi từng nấc, POS ghi nhận đúng luồng của shop)
        for st in (TT_XAC_NHAN, TT_CHO_IN):
            P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body={"status": st})
        treo_ban_facebook(o, ex, khac, ly_do)
        xu_ly_ban_ket(o, ket)
    if cho_xn:
        A.log(f"  ⏸ #{ma} đủ dữ liệu, {KQ_CHO_XN}: {', '.join(da_lam) or 'chỉ ghi chú'}")
        return KQ_CHO_XN + (": " + ", ".join(da_lam) if da_lam else "")
    A.log(f"  ✔ #{ma} {'ĐÃ XÁC NHẬN → CHỜ IN' if du else 'để Mới'}: {', '.join(da_lam) or 'chỉ ghi chú'}"
          f"{' — cần kiểm tra: ' + '; '.join(can_check) if can_check else ''}")
    return ("đã xác nhận + chờ in: " + ", ".join(da_lam)) if du else ("để Mới — " + "; ".join(can_check))


def ghi_chu_them(k, dong):
    """Nối một dòng ghi chú vào đơn `k` — bỏ qua nếu dòng đó đã có sẵn.

    Đơn Facebook nay GIỮ NGUYÊN trạng thái (user chốt 2026-08-30) nên vòng sau vẫn gặp
    lại nó y như cũ; không chặn trùng lời thì mỗi lượt quét lại nối thêm một dòng giống
    hệt và ghi chú phình ra vô hạn.
    """
    cu = (k.get("note") or "").strip()
    if dong.strip() in cu:
        return False
    P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{k['id']}",
          body={"note": (cu + "\n" + dong).strip()})
    return True


def xu_ly_ban_ket(o, ket):
    """Đơn landing đầy đủ đã được cho đi -> dọn bản trùng NẰM CHẾT (don_ket).

    Bản chết mang trạng thái 'Đã xác nhận' nên vòng quét không bao giờ chạm tới nó
    (lay_don_cho chỉ lấy 'Mới'/'Chờ xác nhận') — không dọn ở đây là nó nằm đó mãi và
    khách có hai đơn cùng món trên hệ thống. Bản chết chưa giao thành công/chưa hoàn nên
    thuộc nhóm (1) trong luật hủy (user chốt 2026-08-24): landing thì HỦY THẬT.

    ĐƠN FACEBOOK: CHỈ GHI CHÚ, KHÔNG ĐỔI TRẠNG THÁI (user chốt 2026-08-30, đảo lại nấc
    treo 'Chờ xác nhận'(17) cũ). Lý do đo được: 17 là nấc CHẾT trong shop — 1400 đơn/30
    ngày ở Saudi+UAE không đơn nào từng đi qua, đơn duy nhất từng nằm đó là #67014 do
    chính tool đẩy vào. Đẩy đơn chat sang một nấc không ai mở ra xem = giấu luôn đơn:
    auto_len_don chỉ chạy theo hội thoại tag 'Lên đơn' + đơn 'Mới', còn lay_don_cho lấy
    nấc 17 nhưng lọc bỏ đơn Facebook, nên không vòng nào ngó lại nó nữa. Để nguyên nấc
    sale đang thấy + ghi chú rõ là cách duy nhất đơn còn tới được mắt người.
    """
    for k in ket:
        la_lp = la_don_landing(k)
        try:
            nhan = "HỦY bản nằm chết" if la_lp else "BẢN NẰM CHẾT — sale xem lại"
            dong = (f"[Tự động LP] {nhan}: đơn này ở "
                    f"'{P.STATUS_BY_CODE.get(k.get('status'), k.get('status'))}' nhưng "
                    f"{ly_do_ket(k)}, nằm im "
                    f"{int(_im_lang_ngay(k))} ngày nên không giao được. Bản đầy đủ "
                    f"#{o.get('system_id')} (cùng khách) đã được cho đi thay."
                    + ("" if la_lp else " Nếu khách đặt mua lại thật thì bổ sung dữ liệu "
                                        "còn thiếu rồi cho chạy tiếp, không thì hủy."))
            if la_lp:
                P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{k['id']}",
                      body={"note": ((k.get("note") or "").strip() + "\n" + dong).strip()})
                P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{k['id']}", body={"status": TT_HUY})
                A.log(f"    ↳ hủy bản nằm chết #{k.get('system_id')} "
                      f"({ly_do_ket(k)}, {int(_im_lang_ngay(k))} ngày)")
            elif ghi_chu_them(k, dong):
                A.log(f"    ↳ ghi chú bản nằm chết Facebook #{k.get('system_id')} "
                      f"({ly_do_ket(k)}, {int(_im_lang_ngay(k))} ngày) — GIỮ NGUYÊN "
                      f"'{P.STATUS_BY_CODE.get(k.get('status'), k.get('status'))}'")
            time.sleep(0.2)
        except (SystemExit, Exception) as e:   # noqa: BLE001 — dọn lỗi không giết cả vòng
            A.log(f"    ⚠ Không dọn được bản nằm chết #{k.get('system_id')}: {e}")


def treo_ban_facebook(o, ex, khac, ly_do):
    """Đơn landing đã được cho đi -> bản trùng nguồn FACEBOOK chỉ được GHI CHÚ.

    Không hủy như bản landing: đơn chat có thể là khách đặt mua lại thật, phải để người
    quyết (luật user). Cũng KHÔNG đẩy sang 'Chờ xác nhận'(17) nữa — xem xu_ly_ban_ket():
    17 là nấc không ai trong shop mở ra xem, đẩy vào đó là đơn biến mất khỏi tầm mắt sale
    (user chốt 2026-08-30). Đơn nằm im ở 'Mới' thì cứ để ở 'Mới', chỉ nối lý do vào ghi chú.
    """
    for k in khac:
        if k.get("status") not in TT_CHUA_DI or la_don_landing(k):
            continue
        try:
            if ghi_chu_them(k, f"[Tự động LP] TRÙNG với đơn landing #{o.get('system_id')} "
                               f"vừa được đi (cùng khách + cùng mã sản phẩm) — sale xem lại. "
                               f"Nếu khách đặt mua lại thật thì cho chạy tiếp, không thì hủy."):
                A.log(f"    ↳ ghi chú đơn Facebook #{k.get('system_id')} (trùng) — GIỮ NGUYÊN "
                      f"'{P.STATUS_BY_CODE.get(k.get('status'), k.get('status'))}'")
            time.sleep(0.2)
        except (SystemExit, Exception) as e:   # noqa: BLE001 — ghi chú lỗi không giết cả vòng
            A.log(f"    ⚠ Không ghi chú được đơn #{k.get('system_id')}: {e}")


def la_don_landing(o):
    """Đơn có phải từ landing page không — KHÔNG chỉ tin vào order_sources.

    Thị trường mới đổ đơn về với nguồn RỖNG (Tây Ban Nha: 210 đơn/30 ngày, order_sources
    = null) nên lọc cứng '-7' là bỏ sót nguyên một nước. Dấu hiệu chắc chắn còn lại:
    không gắn page/hội thoại (không phải đơn chat) + ghi chú đúng khuôn form Webcake
    (mấy dòng địa chỉ rồi tới dòng ưu đãi có giá tiền).
    """
    if str(o.get("order_sources")) == NGUON_LANDING:
        return True
    if o.get("page_id") or o.get("conversation_id"):
        return False
    if la_shopify(o):
        return True
    dong, offer = tach_note(o.get("note") or "")
    if offer is not None and len(dong) >= 2:
        return True
    # Form về THIẾU HẲN dòng ưu đãi (21 đơn/30 ngày), hoặc dòng ưu đãi ghi tiền tệ nước
    # khác vì landing trỏ nhầm shop (7 đơn: form Kuwait rơi vào shop UAE/Qatar, form
    # Romania rơi vào shop Tây Ban Nha), hoặc địa chỉ bị lọc rác còn <2 dòng — cả ba ca
    # đều trượt phép thử trên và đơn TÀNG HÌNH với tool: không log, không ghi chú, nằm
    # 'Mới' vô thời hạn (Qatar #6293/#6294/#6298/#6299, Kuwait 13 đơn, Saudi #71144 đủ
    # điều kiện lên mà kẹt từ 31/08 — nhân viên phải kéo tay từng đơn).
    # Dấu hiệu còn lại vẫn chắc: POS CHƯA có ô địa chỉ giao (đơn tạo tay và đơn đã đi
    # luôn có sẵn) + phần khách điền còn ≥2 dòng. Đo 30 ngày/11 thị trường trong ĐÚNG
    # phạm vi lay_don_cho lấy (Mới/Chờ xác nhận): hút thêm 14 đơn, cả 14 đều là form
    # landing thật, 0 đơn hút oan (note scan ĐVVC/đối soát COD đều có địa chỉ nên rớt).
    sa = o.get("shipping_address") or {}
    if any(sa.get(k) for k in ("full_address", "address", "province_id", "district_id")):
        return False
    raw = []
    for s in re.split(r"[\r\n]+", o.get("note") or ""):
        s = s.strip()
        if DONG_HE_THONG.match(s):
            break
        if s:
            raw.append(s)
    return len([x for x in (don_dep_dong(y) for y in raw) if x]) >= 2


def lay_don_cho(ngay):
    """Đơn landing page còn ở trạng thái 'Mới' trong N ngày gần đây."""
    now = int(time.time())
    out, day = [], False
    # Lấy cả 'Chờ xác nhận' — đó là nấc tool treo đơn trùng; khi bản trùng bị hủy thì
    # vòng sau đơn này phải được xét lại chứ không nằm chết ở đó.
    for st in sorted(TT_CHUA_DI):
        for pg in (1, 2, 3, 4, 5):
            data = P.fetch_orders({"startDateTime": now - ngay * 86400, "endDateTime": now,
                                   "page_size": 100, "page_number": pg, "status": st})
            out += [o for o in data if la_don_landing(o)]
            day = day or len(data) == 100
            if len(data) < 100:
                break
            time.sleep(0.2)
    if day:
        A.log(f"⚠ Còn hơn 500 đơn chờ xử lý trong {ngay} ngày — vòng này chỉ lấy 500 đơn mới nhất")
    return out


def chay_thi_truong(mkey, dry=False, ngay=NGAY_MAC_DINH, tu_xac_nhan=True, lam_lai=False):
    A.set_market(mkey)
    _chuan_bi_regex(mkey)
    don = lay_don_cho(ngay)
    da_xu_ly = Q.load_json(state_file(), {})
    con_lai = don if lam_lai else [o for o in don
                                   if _can_xet_lai(da_xu_ly.get(str(o.get("id"))), o)]
    if not con_lai:
        return 0
    A.log(f"🛬 Landing page: {len(con_lai)} đơn mới cần xử lý (tổng {len(don)} đơn 'Mới' {ngay} ngày)")
    # Đệm SĐT chỉ có giá trị trong MỘT vòng: giữ qua vòng là cửa chống trùng đọc trạng
    # thái cũ của đơn anh em (xem xoa_dem_sdt). Daemon chạy nhiều ngày liền nên không tự
    # xóa là đệm sống mãi.
    xoa_dem_sdt()
    idx = chi_muc_don()
    n = 0
    for o in con_lai:
        try:
            ket_qua = xu_ly_mot(o, idx, dry, tu_xac_nhan)
            n += 1
            if not dry:
                da_xu_ly[str(o.get("id"))] = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"),
                                              "ma": o.get("system_id"), "ket_qua": ket_qua}
                Q.save_json(state_file(), da_xu_ly)
        except (SystemExit, Exception) as e:  # noqa: BLE001 — 1 đơn lỗi không giết cả vòng
            A.log(f"  ✖ Lỗi đơn #{o.get('system_id') or o.get('id')}: {e}")
    return n


def lam_tuoi_trang_thai(k):
    """Đọc lại `status` + `status_history` của một đơn từ POS, giữ nguyên phần còn lại.

    Dùng cho đơn lấy ra từ bảng chỉ mục có đệm: mọi phép xử nhóm trùng đều quyết theo
    TRẠNG THÁI đơn anh em, mà trạng thái là thứ đổi nhanh nhất. Các trường khác (ghi chú,
    dòng hàng, SĐT) thì đứng yên nên giữ bản trong bảng, khỏi phải lo lệch tên trường
    giữa hai kiểu response. Hỏng mạng thì trả nguyên bản cũ — không làm chết cả vòng.
    """
    try:
        r = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{k.get('id')}")
        d = r.get("data") if isinstance(r, dict) and isinstance(r.get("data"), dict) else r
        if isinstance(d, dict) and d.get("status") is not None:
            k = dict(k)
            k["status"] = d["status"]
            if d.get("status_history") is not None:
                k["status_history"] = d["status_history"]
    except (SystemExit, Exception) as e:      # noqa: BLE001
        A.log(f"⚠ Không đọc lại được trạng thái đơn #{k.get('system_id') or k.get('id')} ({e})")
    return k


def truoc_do(nhom, o):
    """Các đơn trong nhóm được tạo TRƯỚC đơn `o`."""
    return [k for k in nhom if (k.get("inserted_at") or "") < (o.get("inserted_at") or "")]


def soat_thoat_luoi(mkey, ngay=NGAY_TIM_SDT):
    """RÀ NGƯỢC: có nhóm nào CÙNG KHÁCH + CÙNG MÃ SP mà >1 đơn được cho đi không?

    Vì sao phải có: mọi lần đo trước đây tôi chỉ đếm chiều TREO OAN (đơn bị giữ nhầm) —
    đó là chiều user nhìn thấy nên hay bị hỏi. Chiều ngược lại, THẢ OAN, mới là chiều tốn
    tiền: hàng đi thật, khách nhận hai kiện. Nó lọt suốt 8 đơn saudi mã 217 mà không ai
    biết cho tới khi user tự soi POS (2026-08-22) — nguyên nhân là phép so mã lấy nhầm
    product_id (UUID) đem so với mã '217', xem ma_cua_mau_ma().

    Cố ý KHÔNG đọc ghi chú của tool: bắt bệnh bằng dữ liệu đơn nên bẫy nào cũng lộ, kể
    cả bẫy chưa từng gặp. Đơn SP test và ca 'khách đặt lại sau khi đã nhận hàng' được
    loại đúng như luật trong bảng quyết định.
    """
    A.set_market(mkey)
    _chuan_bi_regex(mkey)
    now = int(time.time())
    theo_sdt = {}
    for pg in range(1, 31):
        # POScake hay trả HTTP 500 lẻ tẻ ở trang sâu (đo 08/09/2026: shop UAE 500 hai lượt
        # liền rồi lại bình thường), mà P.api() thì die() luôn -> cả lượt rà chết. Thử lại
        # 3 lượt; hết vẫn hỏng thì NÉM LỖI để cmd_soat kể tên thị trường, tuyệt đối không
        # trả về danh sách thiếu trang rồi để người đọc tưởng là sạch.
        ds = None
        for lan, doi in enumerate((5, 15, 30, 0), 1):
            try:
                ds = P.fetch_orders({"startDateTime": now - ngay * 86400, "endDateTime": now,
                                     "page_size": 100, "page_number": pg})
                break
            except (SystemExit, Exception) as e:   # noqa: BLE001
                if not doi:
                    raise RuntimeError(f"POScake lỗi ở trang {pg} sau {lan} lượt ({e})") from None
                # Nghỉ dài dần: đo 08/09/2026 shop UAE 500 liên tục ở trang 8 suốt vài phút
                # rồi TỰ khỏi (dò tay ngay sau đó: size 100/50/25 đều OK) -> là bóp tải chứ
                # không phải bản ghi hỏng. Nghỉ 3 giây là quá ngắn, chưa qua cơn đã bỏ cuộc.
                time.sleep(doi)
        if not ds:
            break
        for o in ds:
            if o.get("status") in (TT_HUY, 7):
                continue                      # đơn đã hủy/xóa không còn tính
            sdt = A.normalize_phone(o.get("bill_phone_number") or "")
            if sdt:
                theo_sdt.setdefault(sdt, []).append(o)
        if len(ds) < 100:
            break
        time.sleep(0.2)

    bao = []
    for sdt, ds in theo_sdt.items():
        di = [o for o in ds if o.get("status") not in TT_CHUA_DI and not la_don_test(o)]
        if len(di) < 2:
            continue
        theo_ma = {}
        for o in di:
            for m in ma_san_pham(o):
                theo_ma.setdefault(m, []).append(o)
        for m, nhom in theo_ma.items():
            if len(nhom) < 2:
                continue
            nhom.sort(key=lambda o: o.get("inserted_at") or "")
            cap = []          # (bản GIỮ, bản THỪA, bản thừa có đứng XA HƠN bản giữ không)
            for o in nhom[1:]:
                # NGOẠI LỆ của bảng (luật user, nguyên văn 07/09/2026): "cùng 1 khách,
                # cùng 1 mã SP, đặt TRƯỚC thời điểm đơn cũ nhận/hoàn được coi là trùng,
                # còn đặt SAU thời điểm nhận/hoàn là đặt lại". Phải xét CẢ HAI mốc —
                # bản cũ chỉ xét mốc NHẬN nên đơn đặt lại sau khi hàng đã hoàn về vẫn bị
                # báo là thoát lưới (ca Emma Alimansa #69836 hoàn -> #72498).
                # Xét TỪNG đơn cũ một, y hệt xet_nhom_trung: đơn này chỉ được tha khi
                # MỌI đơn cũ cùng mã SP đều đã nhận/hoàn xong TRƯỚC lúc nó được tạo. Lấy
                # mốc SỚM NHẤT của cả nhóm (bản cũ dùng min) là tha nhầm: một đơn giao
                # xong từ tuần trước sẽ che luôn một đơn khác đang bay.
                con_vuong = []
                for k in truoc_do(nhom, o):
                    moc = (moc_da_nhan(k) if k.get("status") in TT_DA_GIAO_XONG else
                           moc_hoan(k) if k.get("status") in TT_DA_HOAN else None)
                    if moc and (o.get("inserted_at") or "") > moc:
                        continue          # đặt SAU mốc nhận/hoàn của đơn này -> đặt lại
                    con_vuong.append(k)
                if not con_vuong:
                    continue
                # BẢN GIỮ không phải "đơn tạo sớm nhất" mà là đơn ĐỨNG XA NHẤT trong luồng
                # giữa các đơn cũ còn vướng (bằng bậc thì lấy đơn tạo sớm hơn) — xem BAC_LUONG.
                giu = sorted(con_vuong,
                             key=lambda k: (-bac_luong(k), k.get("inserted_at") or ""))[0]
                # Đơn thừa mà lại ĐỨNG XA HƠN bản giữ: hủy nó là giết bản đang chạy để giữ
                # bản kẹt. Máy KHÔNG tự chọn bỏ bản nào ở ca này (bản kẹt có thể là đơn
                # người tạo tay), chỉ gõ chuông lên CẢ HAI đơn cho người quyết.
                cap.append((giu, o, bac_luong(o) > bac_luong(giu)))
            if cap:
                bao.append((sdt, m, cap))
    return bao


# Đơn thừa còn nằm ở các nấc này thì hàng CHƯA rời kho -> còn rút lại được, đáng gõ chuông.
# Đã gửi/đã nhận rồi thì báo cũng không làm gì được nữa, chỉ để trong log.
TT_CON_RUT = {TT_XAC_NHAN, TT_CHO_HANG, TT_CHO_IN, 13, 8, 9}


def cmd_soat(only=None, ngay=NGAY_TIM_SDT, ghi_chu=False, huy=False):
    """Rà ngược nhóm trùng đã thoát lưới. `ghi_chu=True` thì gõ chuông ngay trên đơn.

    Vì sao phải có chuông (user chốt 07/09/2026): `soat` bắt đúng chiều THẢ OAN nhưng
    trước đó chỉ chạy khi có người gõ lệnh, nên ca Mandy Callanan (saudi #72501/#72502)
    im lặng nhiều ngày cho tới lúc user tự nhìn ra. Log thì không ai đọc — chuông phải
    kêu ở chỗ người làm việc, tức là NGAY TRÊN ĐƠN trong POScake, giống khối 📪 của AMI US.

    Chỉ ghi chú, TUYỆT ĐỐI KHÔNG tự hủy: `soat` cố ý không đọc ghi chú của tool nên nó
    không biết các ngoại lệ mà xet_nhom_trung đã cân nhắc (SP test, đơn nằm chết, đơn
    không đọc được mã). Nó là lưới hứng để người kiểm, không phải quan tòa.

    BẢN GIỮ = bản ĐỨNG XA NHẤT trong luồng, không phải bản tạo sớm nhất (xem BAC_LUONG).
    Bản thừa mà đứng XA HƠN bản giữ thì KHÔNG hủy bên nào: bản xa hơn đi bình thường, bản
    thấp hơn TREO nguyên trạng thái, chuông 📪 ghi rõ lên CẢ HAI đơn (luật user 10/09/2026,
    nguyên văn: "đơn chờ in dc đẩy đi, còn đơn đã xác nhận treo ở đó, k xử lý, và ghi rõ
    lên cả 2 đơn"). Ca gốc #49394/#49395 ngày 09/09/2026: bản rà cũ hủy bản 'Chờ in' để
    giữ bản 'Đã xác nhận' -> đóng băng đơn của khách, vì không luồng nào đẩy tiếp đơn đứng
    ở 'Đã xác nhận' (auto_len_don dừng ở đó, job0 chỉ quét status 12).
    """
    tong, da_go, da_huy, hong = 0, 0, 0, []
    for mkey in (only or A.enabled_markets()):
        # 🔴 08/09/2026: POScake trả HTTP 500 giữa chừng là chuyện thường. Bản cũ nuốt lỗi
        # rồi in "0 nhóm — 0 là sạch": BÁO SẠCH GIẢ, đúng cái bệnh mà bộ rà này sinh ra để
        # bắt. Nay thử lại 1 lượt, vẫn hỏng thì kể tên thị trường và trả mã lỗi để systemd
        # đánh dấu failed — "không kiểm được" phải khác hẳn "kiểm rồi, sạch".
        bao = None
        for lan in (1, 2):
            try:
                bao = soat_thoat_luoi(mkey, ngay)
                break
            except (SystemExit, Exception) as e:   # noqa: BLE001 — 1 thị trường lỗi không giết cả vòng
                A.log(f"[{mkey.upper()}] ⚠ soát lỗi (lượt {lan}): {e}")
                if lan == 1:
                    time.sleep(5)
        if bao is None:
            hong.append(mkey)
            continue
        A.log(f"[{mkey.upper()}] 🔎 soát {ngay} ngày: {len(bao)} nhóm THOÁT LƯỚI")
        for sdt, m, cap in bao:
            for dau, k, nguoc in cap:
                A.log(f"   SĐT {sdt} mã SP {m}: bản giữ {_mo_ta_don(dau)} — bản thừa "
                      f"{_mo_ta_don(k)}"
                      + (" ⚠ BẢN THỪA ĐỨNG XA HƠN TRONG LUỒNG: nó ĐI BÌNH THƯỜNG, bản "
                         "giữ bị TREO — máy không hủy bên nào" if nguoc else ""))
            if not (ghi_chu or huy):
                continue
            for dau, k, nguoc in cap:
                if k.get("status") not in TT_CON_RUT:
                    continue               # hàng đã rời kho, hủy trong POS cũng không rút được
                # Bản GIỮ nằm chết (trống địa chỉ/trống dòng hàng, cả tuần không ai đụng) thì nó
                # không giao được -> hủy bản sau là khách chẳng nhận được gì. Luật user 22/08,
                # cùng chốt chặn với don_ket() bên cửa lên đơn. Ca này chỉ gõ chuông, để người xử.
                giu_chet = don_ket(dau)
                if huy and not giu_chet and not nguoc:
                    dong = (f"[Máy rà trùng {time.strftime('%d/%m/%Y')}] ĐÃ HỦY (TRÙNG): cùng khách "
                            f"+ cùng mã SP {m} với {_mo_ta_don(dau)} — đơn kia CHƯA giao xong, CHƯA "
                            f"hoàn, và đơn này được tạo TRƯỚC mốc nhận/hoàn của nó nên là bản gửi "
                            f"lặp chứ không phải khách mua lại (luật user). Hàng chưa rời kho nên "
                            f"rút được.")
                    try:
                        ghi_chu_them(k, dong)
                        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{k['id']}", body={"status": TT_HUY})
                        da_huy += 1
                        A.log(f"   ✖ #{k.get('system_id') or k['id']} ĐÃ HỦY (trùng {m} với "
                              f"#{dau.get('system_id') or dau['id']})")
                    except (SystemExit, Exception) as e:   # noqa: BLE001
                        A.log(f"   ⚠ không hủy được #{k.get('system_id')}: {e}")
                    continue
                if not ghi_chu:
                    continue
                if nguoc:
                    # LUẬT USER 10/09/2026, nguyên văn: "bỏ bản trạng thái đã xác nhận ra
                    # khỏi luồng, ví dụ như có 2 đơn, 1 đơn chờ in, 1 đơn đã xác nhận thì
                    # đơn chờ in dc đẩy đi, còn đơn đã xác nhận treo ở đó, k xử lý, và ghi
                    # rõ lên cả 2 đơn". Nên: KHÔNG hủy bên nào, bản đứng xa hơn đi bình
                    # thường, bản thấp hơn nằm nguyên trạng thái của nó, và chuông kêu ở CẢ
                    # HAI đơn — chỉ ghi lên một bên thì bên kia im lặng nằm đó, đúng cái
                    # bệnh của ca #49394/#49395 ngày 09/09/2026.
                    dong = (f"📪 ĐƠN TRÙNG (máy rà {time.strftime('%d/%m')}): cùng khách + cùng "
                            f"mã SP {m} với {_mo_ta_don_gon(dau)} — bản kia đang đứng ở "
                            f"'{P.STATUS_BY_CODE.get(dau.get('status'), dau.get('status'))}', "
                            f"THẤP HƠN đơn này trong luồng, nên nó bị TREO và KHÔNG xử lý; "
                            f"ĐƠN NÀY ĐI BÌNH THƯỜNG (luật user 10/09/2026). Máy KHÔNG hủy "
                            f"bên nào.")
                    try:
                        if ghi_chu_them(k, dong):
                            da_go += 1
                    except (SystemExit, Exception) as e:   # noqa: BLE001
                        A.log(f"   ⚠ không ghi được chuông lên #{k.get('system_id')}: {e}")
                    dong_giu = (f"📪 ĐƠN TRÙNG (máy rà {time.strftime('%d/%m')}): cùng khách + "
                                f"cùng mã SP {m} với {_mo_ta_don_gon(k)} — bản kia đã bàn giao "
                                f"cho vận đơn và ĐƯỢC ĐI. Đơn này TREO ở "
                                f"'{P.STATUS_BY_CODE.get(dau.get('status'), dau.get('status'))}', "
                                f"KHÔNG xử lý (luật user 10/09/2026). Máy KHÔNG hủy: muốn bỏ đơn "
                                f"này hay đẩy tiếp thì người làm tay.")
                    try:
                        if ghi_chu_them(dau, dong_giu):
                            da_go += 1
                    except (SystemExit, Exception) as e:   # noqa: BLE001
                        A.log(f"   ⚠ không ghi được chuông lên #{dau.get('system_id')}: {e}")
                    continue
                if giu_chet:
                    vi_sao = ("bản giữ #%s đang NẰM CHẾT nên máy không dám hủy đơn này — người "
                              "kiểm rồi quyết" % (dau.get("system_id") or dau["id"]))
                else:
                    vi_sao = "người kiểm rồi quyết, máy KHÔNG tự hủy"
                dong = (f"📪 NGHI ĐƠN TRÙNG (máy rà {time.strftime('%d/%m')}): cùng khách + cùng "
                        f"mã SP {m} với {_mo_ta_don(dau)}, và đơn này tạo TRƯỚC mốc nhận/hoàn "
                        f"của đơn kia. Hàng chưa rời kho nên còn rút được — {vi_sao}.")
                try:
                    if ghi_chu_them(k, dong):
                        da_go += 1
                except (SystemExit, Exception) as e:   # noqa: BLE001
                    A.log(f"   ⚠ không ghi được chuông lên #{k.get('system_id')}: {e}")
        tong += len(bao)
    A.log(f"🔎 TỔNG: {tong} nhóm trùng đã thoát lưới"
          + (" — 0 là sạch" if not hong else "")
          + (f" | ĐÃ HỦY {da_huy} đơn còn rút được" if huy else "")
          + (f" | gõ chuông {da_go} đơn" if ghi_chu else ""))
    if hong:
        A.log(f"❌ KHÔNG KIỂM ĐƯỢC {len(hong)} thị trường: {', '.join(hong)} — con số trên "
              f"KHÔNG có nghĩa là sạch, phải chạy lại")
    return tong, hong


def chay_tat_ca(dry=False, ngay=NGAY_MAC_DINH, only=None, tu_xac_nhan=True, lam_lai=False):
    tong = 0
    for mkey in (only or A.enabled_markets()):
        try:
            tong += chay_thi_truong(mkey, dry, ngay, tu_xac_nhan, lam_lai)
        except (SystemExit, Exception) as e:  # noqa: BLE001
            A.log(f"✖ Lỗi landing page thị trường {mkey}: {e}")
        time.sleep(0.2)
    return tong


def cmd_xem(oid, mkey):
    """In ra tool đọc được gì từ 1 đơn — dùng để kiểm tra luật, không sửa gì cả."""
    A.set_market(mkey)
    _chuan_bi_regex(mkey)
    res = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
    o = res.get("data") if isinstance(res.get("data"), dict) else res
    ex = doc_don(o)
    print(f"\n🧾 Đơn #{o.get('system_id') or oid} — {P.STATUS_BY_CODE.get(o.get('status'), o.get('status'))} "
          f"— nguồn {o.get('order_sources')}")
    print(f"  Ghi chú gốc : {(o.get('note') or '')!r}")
    print(f"  Khách       : {o.get('bill_full_name')} | SĐT {ex['sdt_goc']} → {ex['sdt']}")
    print(f"  Địa chỉ đọc : {ex['diachi']}")
    print(f"  Tỉnh/thành  : {ex['tinh']} ({ex['cach_do_tinh']})")
    print(f"  Dòng ưu đãi : {ex['offer']!r}")
    print(f"  Giá / SL    : {P.fmt_money(ex['gia'])} / {ex['so_luong']}  "
          f"— đơn đang: {P.fmt_money(o.get('money_to_collect'))} / "
          f"{[i.get('quantity') for i in (o.get('items') or [])]}")
    print(f"  Loại SĐT    : {ex['loai_sdt']}"
          + (f"  ⚠ SĐT HỎNG (treo, KHÔNG hủy): {ex['sdt_hong']}" if ex["sdt_hong"] else ""))
    print(f"  Cần kiểm tra: {'; '.join(ex['can_check']) or 'không — đủ điều kiện tự xác nhận'}")
    print(f"  Ghi chú thêm: {'; '.join(ex['ghi_them']) or 'không'}")


def cmd_mot(oid, mkey, dry=False, tu_xac_nhan=True):
    """Xử lý THẬT đúng 1 đơn — dùng khi muốn kiểm chứng trước khi chạy hàng loạt."""
    A.set_market(mkey)
    _chuan_bi_regex(mkey)
    res = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
    o = res.get("data") if isinstance(res.get("data"), dict) else res
    if not la_don_landing(o):
        raise SystemExit(f"Đơn #{oid} không phải đơn landing page (nguồn {o.get('order_sources')})")
    if o.get("status") not in TT_CHUA_DI:
        raise SystemExit(f"Đơn #{oid} không còn ở 'Mới'/'Chờ xác nhận' "
                         f"({P.STATUS_BY_CODE.get(o.get('status'), o.get('status'))}) — bỏ qua cho an toàn")
    ket_qua = xu_ly_mot(o, chi_muc_don(), dry, tu_xac_nhan)
    if not dry:
        da_xu_ly = Q.load_json(state_file(), {})
        da_xu_ly[str(o.get("id"))] = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"),
                                      "ma": o.get("system_id"), "ket_qua": ket_qua}
        Q.save_json(state_file(), da_xu_ly)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1].lower(), sys.argv[2:]
    co_the_la_mkt = [a for a in args if not a.startswith("--") and not a.isdigit()]
    ngay = int(args[args.index("--ngay") + 1]) if "--ngay" in args else NGAY_MAC_DINH
    if cmd == "chay":
        chay_tat_ca(dry="--thu" in args, ngay=ngay, only=co_the_la_mkt or None,
                    tu_xac_nhan="--khong-xac-nhan" not in args,
                    lam_lai="--lam-lai" in args)
    elif cmd in ("xem", "mot"):
        so = [a for a in args if a.isdigit()]
        if not so or not co_the_la_mkt:
            raise SystemExit(f"Dùng: {cmd} <mã đơn> <thị trường>   (vd: {cmd} 46153 uae)")
        if cmd == "xem":
            cmd_xem(so[0], co_the_la_mkt[0])
        else:
            cmd_mot(so[0], co_the_la_mkt[0], dry="--thu" in args,
                    tu_xac_nhan="--khong-xac-nhan" not in args)
    elif cmd == "soat":
        _, hong = cmd_soat(only=co_the_la_mkt or None,
                           ngay=int(args[args.index("--ngay") + 1]) if "--ngay" in args else NGAY_TIM_SDT,
                           ghi_chu="--ghi-chu" in args, huy="--huy" in args)
        if hong:
            sys.exit(1)          # systemd đánh dấu failed -> lượt rà hỏng không im lặng
    elif cmd == "daemon":
        giay = int(args[args.index("--giay") + 1]) if "--giay" in args else 60
        A.log(f"🚀 Daemon landing page — chu kỳ {giay}s")
        while True:
            chay_tat_ca(ngay=ngay)
            time.sleep(giay)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

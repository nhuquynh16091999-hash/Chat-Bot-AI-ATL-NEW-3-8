#!/usr/bin/env python3
"""GIỜ LÀM CỦA SALE / VẬN ĐƠN — ghi sổ hoạt động Pancake + POS, báo WhatsApp nhóm CA NGÀY (chủ shop 23–24/09/2026).

Chủ shop 24/09 chốt đúng 3 loại tin mỗi ca:
  1. ⏸ sale/vận đơn quá 5 phút không hoạt động Pancake/POS → nhắc MỘT lần.
  2. ▶️ khi người đó hoạt động lại → MỘT tin: đã hoạt động lại, vắng mặt bao nhiêu phút.
  3. 📋 hết ca → báo cáo tổng: Thứ… ngày… · giờ vào ca từng người · phút vắng mặt (nếu có) · giờ tan ca.
Sale làm bình thường thì cả ca chỉ có tin 3.

Nguồn (CHỈ LIỆT KÊ, không mở tin, không lật cờ đọc — luật chi-doc-hoi-thoai-cu-khi-dieu-tra):
  · Pancake: `recent_seen_users` (fb_name, seen_at) trong API gộp hội thoại — lần sale mở hội thoại.
  · POS: `histories[].editor_id/updated_at` + `creator`/`last_editor` của đơn vừa cập nhật — lần sửa/tạo đơn (vận đơn làm ở đây).
  · WhatsApp (24/09, chỉ vận đơn): tin họ nhắn trong NHÓM mà số phụ tham gia — wa_nghe.mjs ghi giờ + người gửi, không nội dung.
  · Tin GỬI trên Pancake (24/09): statistics/user theo giờ, so lượt trước → ai vừa nhắn khách (bắt cả tin hiện tên page).
Bẫy đo 23/09: mỗi hội thoại chỉ giữ ĐÚNG 1 người xem cuối và xem KHÔNG đẩy updated_at → phải quét dày (timer 2 phút) + ghi sổ.
Lật trang API gộp đắt (143 page: phủ 3h = 30 lần gọi) → mỗi lượt chỉ hỏi 3 lần, trước báo ca vét 12 lần.

  python3 gio_lam_sale.py                     # 1 lượt (timer gọi): quét → ghi sổ → tin 1/2 → tin 3 nếu ca vừa hết
  python3 gio_lam_sale.py --xem [ngay|toi|dem] [dd/mm]   # in báo cáo ca, KHÔNG gửi
  python3 gio_lam_sale.py --nghi              # in ai đang vắng / vừa quay lại theo sổ, KHÔNG gửi, KHÔNG ghi sổ báo
  python3 gio_lam_sale.py --nap [số lần hỏi]  # quét Pancake sâu để nạp sổ (mặc định 12 lần)
  python3 gio_lam_sale.py --thu [ngay|toi|dem]   # gửi 1 tin thử vào nhóm của ca (mặc định mọi ca)

.env: GIO_LAM_CA (ngay,toi,dem) · GIO_LAM_NHOM_<NGAY|TOI|DEM> (…@g.us) — người + giờ làm sửa ở LICH trong file
      · GIO_LAM_NGHI_PHUT (5) · GIO_LAM_NGHI_VAN_DON_PHUT (15, người có "vận đơn" trong tên) · GIO_LAM_WA_CHO ("vận đơn" | "*" | "0")
      · GIO_LAM_BI_DANH ("tên tài khoản=Tên hiển thị;…") · GIO_LAM_POS=0 tắt POS. (GIO_LAM_WA_JID cũ không còn dùng.)
"""
import contextlib
import fcntl
import io
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, "/opt/pancake-tool")
os.chdir("/opt/pancake-tool")
import ai_sale as A  # noqa: E402

VN = ZoneInfo("Asia/Ho_Chi_Minh")
STATE = "/opt/pancake-tool/state/gio_lam"
F_PAGE = os.path.join(STATE, "page_con_goi.json")
F_SO = os.path.join(STATE, "so_bao.json")
F_POS_NGUOI = os.path.join(STATE, "pos_nguoi.json")
NODE_GUI = "/opt/aicloser/src/gui-canh-bao.js"   # 24/09: tự gửi qua cổng 127.0.0.1:8797 của wa_nghe.mjs nếu đang chạy
F_SDT = os.path.join(STATE, "nhan_vien_sdt.json")   # {sđt: tên POS} từ /shops/<id>/users, nhớ 6 giờ
F_LID = os.path.join(STATE, "wa_lid.json")           # {mã lid WhatsApp: sđt} học dần từ tin có cả hai
WA_CREDS = "/opt/aicloser/wa-auth/creds.json"
F_TK = os.path.join(STATE, "tk_tin.json")            # ảnh chụp số tin GỬI theo nhân viên × page × giờ ở lượt trước
# Tin nhân viên GỬI trên Pancake: 24/09 17:00 chủ shop chỉ ca Trang vận đơn nhắn khách 16:51 mà máy báo vắng — hội thoại đó
# `last_sent_by` = tên PAGE (không có admin_name) và `recent_seen_users` không có Trang (tài khoản vận đơn không để dấu đã xem).
# Nguồn đúng: POST pancake.vn/api/v1/statistics/user (page_ids="a,b,…", statistic_type=hour) — số tin mỗi người mỗi giờ, 141
# page một lần ~3s. Chỉ theo GIỜ nên so với lượt trước: số tăng → người đó vừa gửi tin trong 2' qua (ghi mốc = lúc quét).
# Tin nhóm WhatsApp (wa_nghe.mjs ghi) tính là hoạt động cho ai: chủ shop 24/09 chọn cho VẬN ĐƠN (họ làm với hãng ship qua
# nhóm, POS không ghi). GIO_LAM_WA_CHO: chữ phải có trong tên ("vận đơn"), "*" = mọi người, rỗng/"0" = tắt.
WA_CHO_MD = "vận đơn"
# sđt WhatsApp → tên, cho người mà POS KHÔNG ghi sđt (ghi đè danh bạ POS). Chủ shop xác nhận từng số.
WA_SO_TEN = {
    "84832430818": "Châu Anh Vận Đơn",     # WhatsApp "Chau Anh Tran" — chủ shop xác nhận 24/09 ~16:15 VN
    # WA_VD_2909 (chủ shop 29/09: "vận đơn có trúc và dương có làm việc qua whatsapp nữa"): POS ghi sđt khác số WhatsApp
    # → trước đây tin nhóm của 2 bạn không được tính, 26/09 06:48 Trúc bị báo vắng dù đang nhắn nhóm 06:39–06:48.
    "84988668239": "Trúc Vận đơn",         # WhatsApp "Nttruc" — nhắn 18–23h, nhóm Imile SAUDI / VẬN ĐƠN RIÊNG
    "84335311523": "Dương Vận đơn",        # WhatsApp "Nguyen Thuy Duong" — nhắn 0–7h, cùng các nhóm vận đơn
}
SO_GOI = 3              # mỗi lượt hỏi API gộp 3 lần (~600 hội thoại mới nhất, ~12s)
SO_GOI_NAP = 12         # --nap / trước báo ca: hỏi sâu hơn
POS_LUI_PHUT = 20       # lượt đầu / mất mốc: lấy đơn POS cập nhật trong 20 phút qua
F_POS_MOC = os.path.join(STATE, "pos_moc.json")   # {shop: giờ quét POS thành công gần nhất} → lượt sau lấy từ mốc −3'
# Đo 24/09 14:20 VN: Saudi 194 đơn cập nhật/10', 526/20' (hãng ship tự cập nhật), trang 1 KHÔNG xếp theo updated_at
# → bản cũ chỉ đọc trang 1 (100 đơn) sót gần hết thao tác POS của sale Saudi. Phải lật HẾT trang, cửa sổ ngắn.
# tên tài khoản POS/Pancake khác tên chủ shop gọi → bí danh (chữ thường) → tên hiển thị. Đo 24/09: POS ghi "Thùy linh vận đơn".
BI_DANH = {"thùy linh vận đơn": "Linh Vận Đơn", "chau anh vận đơn": "Châu Anh Vận Đơn",   # POS "Chau Anh vận đơn" (9b463dcd)
           "hiền nguyễn": "Hiền Nguyễn & Phương Anh CĐ", "phương anh cđ": "Hiền Nguyễn & Phương Anh CĐ"}   # CHUNG_NICK
# Vận đơn làm theo LÔ trên POS: sửa/gửi hãng hàng chục đơn một lượt rồi in vận đơn, đối chiếu ở cổng hãng — 5–10 phút không để
# dấu trên POS dù vẫn đang làm (24/09 12:30→12:38 Trang bị báo vắng 6' oan, chủ shop: "vẫn hoạt động ở POS là làm việc rồi mà").
# → người có chữ "vận đơn" trong tên dùng ngưỡng riêng GIO_LAM_NGHI_VAN_DON_PHUT. Chủ shop đổi qua lại 24/09: 15' → 5'
# (15:25) → CHỐT 15' (15:30, "vận đơn để 15 phút nhé"). Sale vẫn 5'.
NGHI_VAN_DON_MD = 15
# 3 CA = 3 NHÓM WhatsApp (chủ shop chốt 24/09 ~15:45 VN). "dau"–"het" (giờ VN, phút cuối TÍNH VÀO ca) là khung báo cáo:
# báo cáo gửi sau "het" 5 phút. Tin ⏸/▶️ của một người về nhóm ca của người đó.
CA = {
    "ngay": {"nhan": "CA NGÀY", "dau": (8, 0), "het": (17, 30), "nhom": "120363421812384927@g.us"},    # nhóm TEAM PHƯƠNG ANH
    "toi": {"nhan": "CA TỐI", "dau": (17, 30), "het": (23, 0), "nhom": "120363351821544514@g.us"},     # nhóm CA TỐI
    "dem": {"nhan": "CA ĐÊM", "dau": (22, 30), "het": (8, 0), "nhom": "120363401004990227@g.us"},      # nhóm CA ĐÊM_MỚI
}
# LỊCH LÀM THEO NGƯỜI (chủ shop 24/09 ~16:00 VN): tên → (ca, lịch). Lịch = các khúc "HH:MM-HH:MM" cách ";" (qua nửa đêm được,
# giữa các khúc là giờ nghỉ). Chỉ nhắc vắng TRONG khúc làm; về trễ sau giờ nghỉ (khúc thứ 2 trở đi) cũng tính vắng từ đầu khúc.
# Sale ca đêm LUÂN PHIÊN theo ngày: "ai vào ca trước thì làm ca đó" → hoạt động đầu tiên của đêm trước MOC_CA2 là ca 1, sau là ca 2.
DEM_LUAN_PHIEN = (("ca 1", "22:30-01:30;04:30-06:00"), ("ca 2", "01:30-04:30;06:00-08:00"))
MOC_CA2 = (1, 0)
# VAO_THAT_2909 (chủ shop 29/09: "hôm qua Thái làm ca 2 mà"): Thái sửa 1 đơn POS 00:11 rồi nghỉ, 01:32 mới làm thật → máy xếp ca 1.
# Giờ "vào ca" của sale luân phiên = lượt đầu tiên có ≥ VAO_THAT_MIN hoạt động trong VAO_THAT_PHUT phút (ghé lẻ không tính).
VAO_THAT_MIN, VAO_THAT_PHUT = 5, 10


def vao_that(ts, dau, cuoi):
    """Hoạt động đầu tiên trong [dau, cuoi) mở đầu 1 đợt làm thật (≥ VAO_THAT_MIN lượt trong VAO_THAT_PHUT phút) → epoch / None."""
    tr = sorted(t for t in ts if dau <= t < cuoi)
    for i, t in enumerate(tr):
        if len([x for x in tr[i:i + VAO_THAT_MIN] if x < t + VAO_THAT_PHUT * 60]) >= VAO_THAT_MIN:
            return t
    return None
LICH = {
    "Từ Trang": ("ngay", "08:00-17:30"), "Nguyễn Duyên": ("ngay", "08:00-17:30"), "Thu Hiền": ("ngay", "08:00-17:30"),
    # vận đơn ca ngày nghỉ trưa 12:00–13:30 (chủ shop 24/09 ~17:30 VN); Châu Anh thêm 24/09 ~16:10 VN
    "Trang Vận Đơn": ("ngay", "08:00-11:59;13:30-17:30"), "Linh Vận Đơn": ("ngay", "08:00-11:59;13:30-17:30"),
    "Châu Anh Vận Đơn": ("ngay", "08:00-11:59;13:30-17:30"),
    "Minh Thảo": ("toi", "17:30-22:30"), "Mai Linh": ("toi", "17:30-22:30"),
    "Trúc Vận đơn": ("toi", "18:00-23:00"),
    "Dương Vận đơn": ("dem", "00:00-03:00;05:00-07:00"),                     # off 03:00–05:00
    "An Thái": ("dem", DEM_LUAN_PHIEN), "Quỳnh Trang": ("dem", DEM_LUAN_PHIEN),
    "Hiền Nguyễn & Phương Anh CĐ": ("dem", DEM_LUAN_PHIEN),                 # CHUNG NICK chat, xem CHUNG_NICK
}
# CHUNG NICK (chủ shop 24/09 ~23:00 VN): Hiền Nguyễn + Phương Anh CĐ chat CÙNG LÚC trên 1 nick Pancake "Hiền Nguyễn"; sửa/xác
# nhận đơn thì mỗi bạn dùng nick POS riêng ("Hiền Nguyễn" / "Phương Anh CĐ"). Chat không tách được → chủ shop chọn GỘP 1 khối
# (vào/tan/vắng theo nick chung + POS cả hai) + dòng đơn POS riêng từng bạn. Trước đó máy tính hết chat cho Hiền → Phương Anh bị
# báo vắng oan (đêm 23/09: 202 phút). Khoá = tên khối → [tên POS từng người].
CHUNG_NICK = {"Hiền Nguyễn & Phương Anh CĐ": ["Hiền Nguyễn", "Phương Anh CĐ"]}
CHUNG_NICK_CHAT = {"Hiền Nguyễn & Phương Anh CĐ": "Hiền Nguyễn"}    # tên nick chat dùng chung
# NICK DÙNG CHUNG THEO GIỜ (chủ shop 25/09 11:30, ảnh Pancake "Trúc Vận đơn 11:24" nhắn khách ClearVision Saudi): Linh vận đơn
# (ca ngày) chat bằng nick "Trúc Vận đơn"; tối Trúc tự dùng. Lượt của nick này rơi vào khúc làm của ai (theo LICH) thì tính cho người
# đó; ngoài mọi khúc → giữ tên nick. Giải thích vụ "Trúc hoạt động gần cả ngày đêm" 24/09. Khoá = tên nick chuẩn → [người, theo thứ tự].
NICK_THEO_GIO = {"trúc vận đơn": ["Linh Vận Đơn", "Trúc Vận đơn"]}
# ĐỔI CA BÁO TRƯỚC (chủ shop 25/09 18:10: "nay trúc xuống ca đêm làm" — sau khi 18:06 đã lỡ gửi "⏰ Trúc Vận đơn chưa vào ca" vào
# CA TỐI): tự nhận đổi ca chỉ thấy SAU khi người đó làm được một phần ca mới → không cứu được tin ⏰ đầu ca. File
# state/gio_lam/doi_ca.json {"yyyy-mm-dd": {"tên chuẩn": "ngay|toi|dem"}} = ngày đó người ấy làm ca kia với giờ chuẩn (LICH_CHUAN):
# ca gốc hôm đó coi như bị thay, không ⏰/⏸ ở ca gốc, báo cáo ca gốc ghi "🔁 Đổi sang …", ca mới nhắc + báo cáo như người của ca đó.
F_DOI_CA = os.path.join(STATE, "doi_ca.json")
# LỆNH WHATSAPP (chủ shop chọn 25/09 18:20 "cả hai cách"): gõ vào nhóm "#doica Trúc đêm", "#doica Quỳnh Trang tối 26/09",
# "#off Thu Hiền", "#off Linh vận đơn 27/09" → wa_nghe.mjs lưu CHỈ tin bắt đầu "#" vào lenh.jsonl → mỗi lượt đọc, ghi doi_ca.json
# (giá trị ca hoặc "off"), trả lời ✅/❓ trong chính nhóm đó. Chỉ số trong LENH_SO được ra lệnh (chủ shop thêm trưởng ca sau).
F_LENH = os.path.join(STATE, "lenh.jsonl")
LENH_SO = {"84865140865"}               # số chính chủ shop (WhatsApp "Phương Anh Nguyễn")
# CHỐT MUỘN: ai không làm ca của mình mà còn ca sau (bắt đầu trong [hết ca −1h, hết ca +6h]) có thể đổi sang → báo cáo ghi ⏳;
# hết các ca đó +5' → 1 tin vào nhóm ca gốc: "🔁 … đã đổi sang CA …" hoặc "😴 … nghỉ (off) …". Sổ so_bao["cho_chot"].
# 23:10 chủ shop: "k cần ghi đơn, bạn tự nhận diện dc bạn nào ca nào chứ" → tach_chung_nick(): ca của từng bạn = khung (ca 1/ca 2)
# chứa nhiều thao tác POS RIÊNG của bạn đó nhất; khác ca → tách 2 khối, chat nick chung trong khung ca nào tính cho bạn ca đó.
# ĐỔI CA TỰ NHẬN (chủ shop 24/09 ~22:00 VN: "ngày Quỳnh Trang đổi ca xuống ca tối làm thì ghi nhận ở đâu" → chọn máy tự nhận):
# người có hoạt động NGOÀI giờ ca gốc mà nằm trong giờ chuẩn của ca khác, đủ DOI_CA_LUOT lượt trải ≥ DOI_CA_PHUT phút → tính là
# làm ca đó hôm đó ("🔁 đổi ca"): vào báo cáo + nhắc vắng của ca đó (nhóm của ca đó). Ca gốc ghi "🔁 Đổi sang …" thay vì ⚪.
LICH_CHUAN = {
    ("ngay", "sale"): "08:00-17:30", ("ngay", "van_don"): "08:00-11:59;13:30-17:30",
    ("toi", "sale"): "17:30-22:30", ("toi", "van_don"): "18:00-23:00",
    ("dem", "sale"): DEM_LUAN_PHIEN, ("dem", "van_don"): "00:00-03:00;05:00-07:00",
}
# Đổi ca = làm PHẦN LỚN ca kia, không phải ghé vài thao tác: hoạt động ở ≥ DOI_CA_O_MIN ô 10' và ≥ DOI_CA_TL số ô 10' của khúc
# làm ca kia (tính tới hiện tại). 24/09: bản "≥10 lượt trải ≥30'" nhận nhầm Quỳnh Trang (17 lượt lẻ 10h+17h) và Trúc (POS rải
# rác cả ngày) là đổi sang ca ngày.
DOI_CA_O, DOI_CA_O_MIN, DOI_CA_TL = 600, 4, 0.3
# KHÔNG tự nhận đổi ca cho tài khoản hoạt động gần như cả ngày đêm — không phân biệt được đổi ca với làm rải rác.
# 24/09: "Trúc Vận đơn" có hoạt động 00–03h, 06–08h, ban ngày (46% ô ca ngày ≈ vận đơn ca ngày) VÀ đủ ca tối 18–23h.
KHONG_DOI_CA = {"trúc vận đơn", "hiền nguyễn & phương anh cđ"}
BAO_SAU_PHUT = 5        # báo ca sau khi ca hết 5 phút
BAO_TRE_GIO = 3         # quá 3 giờ sau giờ báo mà chưa gửi được thì thôi
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def env():
    return A.env()


def _so(e, k, md):
    try:
        return float(e.get(k) or md)
    except ValueError:
        return md


def chuan(s):
    """Tên để so: gọn khoảng trắng + chữ thường (fb_name Pancake có khi 2 dấu cách, hoa/thường khác)."""
    return " ".join((s or "").split()).lower()


def ca_bat(e):
    """Các ca đang bật báo (GIO_LAM_CA, mặc định cả 3)."""
    ds = [x.strip() for x in (e.get("GIO_LAM_CA") or ",".join(CA)).split(",") if x.strip() in CA]
    return ds or list(CA)


def nhom_ca(e, loai):
    return (e.get(f"GIO_LAM_NHOM_{loai.upper()}") or CA[loai]["nhom"]).strip()


def ds_sale(e, loai=None):
    """{tên chuẩn: tên hiển thị} người của ca `loai` (None = mọi ca bật) + bí danh (GIO_LAM_BI_DANH="tên tài khoản=Tên;…")."""
    cac = [loai] if loai else ca_bat(e)
    ds = {chuan(ten): ten for ten, (lx, _) in LICH.items() if lx in cac}
    bd = dict(BI_DANH)
    for cap in (e.get("GIO_LAM_BI_DANH") or "").split(";"):
        if "=" in cap:
            a, b = cap.split("=", 1)
            bd[chuan(a)] = " ".join(b.split())
    for k, v in bd.items():
        if chuan(v) in ds:
            ds[k] = ds[chuan(v)]
    return ds


def nguong_nghi(e, ten):
    """Ngưỡng vắng (giây) theo người: vận đơn có ngưỡng riêng, còn lại GIO_LAM_NGHI_PHUT."""
    if "vận đơn" in chuan(ten) or "van don" in chuan(ten):
        return _so(e, "GIO_LAM_NGHI_VAN_DON_PHUT", NGHI_VAN_DON_MD) * 60
    return _so(e, "GIO_LAM_NGHI_PHUT", 5) * 60


def vn(t, dang="%H:%M"):
    return datetime.fromtimestamp(t, VN).strftime(dang)


def phut(s):
    return f"{int(round(s / 60))} phút"


def doc_json(f, md):
    try:
        with open(f, encoding="utf-8") as g:
            return json.load(g)
    except Exception:                                    # noqa: BLE001
        return md


def ghi_json(f, d):
    os.makedirs(STATE, exist_ok=True)
    tam = f"{f}.{os.getpid()}.tmp"
    with open(tam, "w", encoding="utf-8") as g:
        json.dump(d, g, ensure_ascii=False, indent=1)
    os.replace(tam, f)


def log(*a):
    print(f"[{vn(time.time(), '%d/%m %H:%M:%S')} VN]", *a, flush=True)


# ---------------------------------------------------------------- Pancake
def page_con_goi():
    """{pid: tên} page còn gói cước (luật chi-page-con-goi-pancake); nhớ 30 phút trên đĩa vì hỏi mất ~7s."""
    d = doc_json(F_PAGE, {})
    if d.get("pg") and time.time() - d.get("luc", 0) < 1800:
        return d["pg"]
    with contextlib.redirect_stdout(io.StringIO()):
        bang = A._bang_con_goi() or {}
        ps = A._ds_page_tai_khoan() or []
    pg = {str(p["id"]): p.get("name") for p in ps if bang.get(str(p["id"]))}
    if pg:
        ghi_json(F_PAGE, {"luc": time.time(), "pg": pg})
        return pg
    return d.get("pg") or {}


def quet(so_goi=SO_GOI):
    """Liệt kê hội thoại (API gộp, lật trang tối đa so_goi lần) → (lượt xem, số hội thoại chưa đọc, lỗi).
    Đo 23/09 (143 page): mỗi lần gọi ~450 hội thoại nhưng từ lần 6 chỉ còn ~40 cái MỚI/lần (con trỏ theo page,
    lô sau lặp lại lô trước) — phủ 3 giờ tốn 30 lần gọi/93s. Nên mỗi lượt chỉ hỏi vài lần: lấy phần mới nhất,
    lần xem trên hội thoại cũ sẽ được thấy khi hội thoại đó cập nhật (sale trả lời) mà chưa bị người sau đè."""
    pg = page_con_goi()
    xem, chua_doc, da, loi = [], 0, set(), None
    ids = list(pg)
    for i in range(0, len(ids), 200):                   # ~288 page/lô là trần độ dài URL
        dem, goi, bo = {x: 0 for x in ids[i:i + 200]}, 0, 0
        while goi < so_goi and bo < 3:
            prm = {("pages[%s]" % x): n for x, n in dem.items()}
            prm.update({"unread_first": "false", "mode": "NONE", "tags": '"ALL"', "except_tags": "[]",
                        "access_token": A._tok_user(), "cursor_mode": "true", "from_platform": "web"})
            res, e = A._get(f"{A.WEB_API}/conversations", prm)
            cs = (res or {}).get("conversations")
            hong = {str(x.get("page_id")) for x in ((res or {}).get("errors") or [])
                    if isinstance(x, dict) and x.get("page_id")}
            if not e and not isinstance(cs, list) and hong:     # một page chết làm hỏng cả lô → bỏ nó, hỏi lại
                for x in hong:
                    dem.pop(x, None)
                bo += 1
                continue
            goi += 1
            if e or not isinstance(cs, list):
                loi = e or str(res)[:160]
                break
            moi = [c for c in cs if c.get("id") not in da]
            if not moi:
                break
            for c in moi:
                da.add(c.get("id"))
                if c.get("type") != "INBOX":
                    continue
                if not c.get("seen"):
                    chua_doc += 1
                for u in c.get("recent_seen_users") or []:
                    t = A._giay_api(u.get("seen_at"))
                    if t and time.time() - t < 36 * 3600:
                        xem.append({"t": round(t, 3), "fb": str(u.get("fb_id") or ""),
                                    "ten": " ".join((u.get("fb_name") or "").split()),
                                    "pg": str(c.get("page_id")), "cid": c.get("id"), "loai": "pan"})
            for x, n in ((res or {}).get("pages_with_current_count") or {}).items():
                if str(x) in dem:
                    dem[str(x)] = n
    return xem, chua_doc, loi


# ---------------------------------------------------------------- POS
def _nguoi_pos(o, bang):
    """Nhặt {id: tên} từ các ô người của đơn (creator, last_editor, assigning_*, status_history)."""
    for k in ("creator", "last_editor", "assigning_seller", "assigning_care", "marketer"):
        v = o.get(k)
        if isinstance(v, dict) and v.get("id") and (v.get("name") or v.get("fb_name")):
            bang[str(v["id"])] = " ".join((v.get("name") or v.get("fb_name")).split())
    for h in o.get("status_history") or []:
        if isinstance(h, dict) and h.get("editor_id") and h.get("name"):
            bang[str(h["editor_id"])] = " ".join(h["name"].split())


def quet_pos(lui_phut=None):
    """Đơn POS vừa cập nhật ở mọi shop trong markets.json → lượt sửa/tạo đơn (editor_id, giờ). Lỗi shop nào chỉ ghi lỗi.
    lui_phut=None (timer): mỗi shop lấy từ mốc lượt trước −3 phút (trong khoảng 6–30 phút); có số → lấy đúng chừng ấy phút (nạp)."""
    import pancake_order as PO
    bang = doc_json(F_POS_NGUOI, {})
    n_bang = len(bang)
    moc = doc_json(F_POS_MOC, {})
    kq, loi, thieu_ten = [], [], 0
    bay_gio = int(time.time())
    for tt, m in json.load(open("markets.json", encoding="utf-8")).items():
        if tt.startswith("_") or not isinstance(m, dict) or not m.get("api_key") or not m.get("shop_id"):
            continue
        if lui_phut is None:
            tu = int(moc.get(tt) or bay_gio - POS_LUI_PHUT * 60) - 180
            tu = max(bay_gio - 30 * 60, min(tu, bay_gio - 6 * 60))
        else:
            tu = bay_gio - int(lui_phut * 60)
        ds, du = [], False
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                PO.set_shop(m["api_key"], m["shop_id"], scale=m.get("scale", 100), label=m.get("tien_te", ""),
                            country_code=m.get("country_code", ""))
                for trang in range(1, 81):               # lật HẾT (trang 1 không xếp theo updated_at)
                    lo = PO.fetch_orders({"startDateTime": tu, "endDateTime": bay_gio, "page_size": 100,
                                          "page_number": trang, "updateStatus": "updated_at"})
                    ds += lo or []
                    if len(lo or []) < 100:
                        du = True
                        break
        except BaseException as ex:                      # noqa: BLE001 — SystemExit của die() cũng phải nuốt
            loi.append(f"{tt}: {str(ex)[:80]}")
        if du and lui_phut is None:
            moc[tt] = bay_gio
        elif not du and ds:
            loi.append(f"{tt}: chưa lật hết trang ({len(ds)} đơn)")
        for o in ds or []:
            _nguoi_pos(o, bang)
            luot = []
            cr = o.get("creator")
            if isinstance(cr, dict) and cr.get("id"):
                luot.append((str(cr["id"]), o.get("inserted_at")))
            for h in (o.get("histories") or []) + (o.get("status_history") or []):
                if isinstance(h, dict) and h.get("editor_id") and h.get("updated_at"):
                    luot.append((str(h["editor_id"]), h["updated_at"]))
            for uid, luc in luot:
                t = A._giay_api(luc)
                if not t or time.time() - t > 36 * 3600:
                    continue
                ten = bang.get(uid)
                if not ten:
                    thieu_ten += 1
                    continue
                kq.append({"t": round(t, 3), "fb": uid, "ten": ten, "pg": tt, "cid": f"pos:{o.get('id')}", "loai": "pos"})
    if len(bang) != n_bang:
        ghi_json(F_POS_NGUOI, bang)
    if lui_phut is None:
        ghi_json(F_POS_MOC, moc)
    return kq, loi, thieu_ten


# ---------------------------------------------------------------- WhatsApp nhóm
def _sdt(x):
    so = "".join(ch for ch in str(x or "") if ch.isdigit())
    if so.startswith("0"):
        so = "84" + so[1:]
    return so


def bang_sdt():
    """{sđt: tên POS} của nhân viên, gom từ /shops/<id>/users mọi shop markets.json; nhớ 6 giờ."""
    d = doc_json(F_SDT, {})
    if d.get("bang") and time.time() - d.get("luc", 0) < 6 * 3600:
        return d["bang"]
    import urllib.parse
    import urllib.request
    bang = {}
    for tt, m in json.load(open("markets.json", encoding="utf-8")).items():
        if tt.startswith("_") or not isinstance(m, dict) or not m.get("api_key") or not m.get("shop_id"):
            continue
        u = f"https://pos.pages.fm/api/v1/shops/{m['shop_id']}/users?" + urllib.parse.urlencode({"api_key": m["api_key"]})
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                ds = json.loads(r.read().decode()).get("data") or []
        except Exception:                                # noqa: BLE001
            continue
        for x in ds:
            us = x.get("user") or {}
            if us.get("phone_number") and us.get("name"):
                bang[_sdt(us["phone_number"])] = " ".join(us["name"].split())
    if bang:
        ghi_json(F_SDT, {"luc": time.time(), "bang": bang})
        return bang
    return d.get("bang") or {}


NHOM_BAO = {c["nhom"] for c in CA.values()} | {"120363335173024949@g.us"}   # nhóm máy gửi báo cáo (+ CA NGÀY cũ)


def quet_wa(e, lui_phut=40):
    """Tin nhóm WhatsApp (sổ wa-*.jsonl của wa_nghe.mjs) trong lui_phut phút qua → lượt hoạt động theo tên nhân viên.
    Người gửi nhận qua SỐ ĐIỆN THOẠI khớp danh bạ nhân viên POS; tin của chính số phụ (minh) = số trong creds."""
    cho = (e.get("GIO_LAM_WA_CHO") if e.get("GIO_LAM_WA_CHO") is not None else WA_CHO_MD).strip().lower()
    if cho in ("", "0"):
        return [], 0
    ds = ds_sale(e)
    sdt_ten = {**bang_sdt(), **WA_SO_TEN}
    lid = doc_json(F_LID, {})
    n_lid = len(lid)
    try:
        so_minh = _sdt(str(json.load(open(WA_CREDS, encoding="utf-8"))["me"]["id"]).split(":")[0].split("@")[0])
    except Exception:                                    # noqa: BLE001
        so_minh = ""
    bay_gio = time.time()
    tu = bay_gio - lui_phut * 60
    kq, la = [], 0
    ngay = datetime.fromtimestamp(tu, VN).date()
    while ngay <= datetime.fromtimestamp(bay_gio, VN).date():
        try:
            dong = open(os.path.join(STATE, f"wa-{ngay:%Y-%m-%d}.jsonl"), encoding="utf-8").read().splitlines()
        except FileNotFoundError:
            dong = []
        ngay += timedelta(days=1)
        for d in dong:
            try:
                x = json.loads(d)
            except ValueError:
                continue
            if not (tu <= float(x.get("t") or 0) <= bay_gio + 60):
                continue
            so, ma_lid = "", ""
            for j in (x.get("ai"), x.get("ai2")):
                j = str(j or "")
                if j.endswith("@s.whatsapp.net"):
                    so = so or _sdt(j.split("@")[0].split(":")[0])
                elif j.endswith("@lid"):
                    ma_lid = ma_lid or j.split("@")[0].split(":")[0]
            if x.get("minh"):
                if x.get("nhom") in NHOM_BAO:                 # tin máy gửi vào nhóm báo cáo trước khi wa_nghe biết lọc (24/09)
                    continue
                so = so_minh
            if so and ma_lid:
                lid[ma_lid] = so
            so = so or lid.get(ma_lid, "")
            ten = sdt_ten.get(so)
            if not ten or chuan(ten) not in ds:
                la += 1
                continue
            hien = ds[chuan(ten)]
            if cho != "*" and cho not in chuan(hien):
                continue
            kq.append({"t": round(float(x["t"]), 3), "fb": f"wa:{so}", "ten": ten, "pg": x.get("nhom"),
                       "cid": f"wa:{x.get('id')}", "loai": "wa"})
    if len(lid) != n_lid:
        ghi_json(F_LID, lid)
    return kq, la


def quet_tin():
    """Số tin nhân viên gửi (statistics/user theo giờ) so với lượt trước → lượt hoạt động mới [(t, tên…)], lỗi."""
    import urllib.parse
    import urllib.request
    bay_gio = time.time()
    d = datetime.fromtimestamp(bay_gio, VN)
    q = {"access_token": A._tok_user(), "statistic_type": "hour",
         "date_range": f"{d:%d/%m/%Y} 00:00:00 - {d:%d/%m/%Y} 23:59:59"}
    rq = urllib.request.Request("https://pancake.vn/api/v1/statistics/user?" + urllib.parse.urlencode(q),
                                data=urllib.parse.urlencode({"page_ids": ",".join(page_con_goi())}).encode(),
                                method="POST", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(rq, timeout=60) as r:
            dd = (json.loads(r.read().decode()).get("data") or {})
    except Exception as ex:                              # noqa: BLE001
        return [], str(ex)[:100]
    ten = {uid: " ".join((u.get("user_name") or "").split()) for uid, u in (dd.get("users") or {}).items()}
    dem = {}
    for uid, ds in (dd.get("statistics") or {}).items():
        for x in ds or []:
            n = (x.get("inbox_count") or 0) + (x.get("comment_count") or 0) + (x.get("private_reply_count") or 0)
            if n:
                dem[f"{uid}|{x.get('page_id')}|{x.get('time')}"] = n
    cu = doc_json(F_TK, {})
    kq = []
    if cu.get("ngay") == f"{d:%Y-%m-%d}":                # lượt đầu trong ngày chỉ chụp mốc, chưa biết tin nào mới
        for k, n in dem.items():
            if n <= (cu.get("dem") or {}).get(k, 0):
                continue
            uid, pid, gio = k.split("|", 2)
            try:
                dau_gio = datetime.strptime(gio, "%H:%M %d/%m/%Y").replace(tzinfo=VN).timestamp()
            except ValueError:
                continue
            t = min(bay_gio, dau_gio + 3599)             # tin mới nằm trong (lượt trước, bây giờ] ∩ giờ đó
            if ten.get(uid):
                kq.append({"t": round(t, 3), "fb": f"tk:{uid}", "ten": ten[uid], "pg": pid, "cid": f"tk:{k}|{n}", "loai": "tin"})
    ghi_json(F_TK, {"ngay": f"{d:%Y-%m-%d}", "luc": bay_gio, "dem": dem})
    return kq, None


def wa_tinh(e, ten):
    """Người này có được tính tin nhóm WhatsApp không (để ghi đúng chữ trong tin nhắc)."""
    cho = (e.get("GIO_LAM_WA_CHO") if e.get("GIO_LAM_WA_CHO") is not None else WA_CHO_MD).strip().lower()
    return cho not in ("", "0") and (cho == "*" or cho in chuan(ten))


# ---------------------------------------------------------------- sổ
def f_ngay(t):
    return os.path.join(STATE, "xem-" + datetime.fromtimestamp(t, VN).strftime("%Y-%m-%d") + ".jsonl")


def doc_so(tu, den):
    """Mọi lượt hoạt động đã ghi trong [tu, den)."""
    kq, ngay = [], datetime.fromtimestamp(tu, VN).date()
    while ngay <= datetime.fromtimestamp(den, VN).date():
        try:
            with open(os.path.join(STATE, f"xem-{ngay:%Y-%m-%d}.jsonl"), encoding="utf-8") as g:
                for d in g:
                    try:
                        x = json.loads(d)
                    except ValueError:
                        continue
                    if tu <= x["t"] < den:
                        kq.append(x)
        except FileNotFoundError:
            pass
        ngay += timedelta(days=1)
    return kq


def ghi_so(xem):
    os.makedirs(STATE, exist_ok=True)
    co = {f"{x['cid']}|{x['fb']}|{x['t']}" for x in doc_so(time.time() - 40 * 3600, time.time() + 60)}
    moi = 0
    for x in sorted(xem, key=lambda x: x["t"]):
        k = f"{x['cid']}|{x['fb']}|{x['t']}"
        if k in co:
            continue
        co.add(k)
        with open(f_ngay(x["t"]), "a", encoding="utf-8") as g:
            g.write(json.dumps(x, ensure_ascii=False) + "\n")
        moi += 1
    return moi


def ca_cua(e):
    """{tên chuẩn hiển thị: ca} — người thuộc ca nào (theo LICH, chỉ ca đang bật)."""
    bat = ca_bat(e)
    return {chuan(ten): lx for ten, (lx, _) in LICH.items() if lx in bat}


def _chu_nick(k, t, nho):
    """Nick dùng chung theo giờ: lượt lúc t thuộc ai (tên LICH) — người có khúc làm chứa t; không ai → None."""
    d = datetime.fromtimestamp(t, VN).date()
    for ten in NICK_THEO_GIO[k]:
        for dd in (d, d - timedelta(days=1)):
            if (ten, dd) not in nho:
                nho[(ten, dd)] = lich_nguoi(chuan(ten), LICH[ten][0], dd, [])[1]
            if any(a <= t < b for a, b in nho[(ten, dd)]):
                return ten
    return None


def theo_nguoi(xem, e, loai=None):
    """{tên chuẩn: {ten: tên hiển thị, t: [giờ tăng dần]}} — chỉ người của ca `loai` (None = mọi ca), gộp Pancake + POS + WA.
    Nick dùng chung theo giờ (NICK_THEO_GIO) → chia lượt cho người đang trong khúc làm."""
    ds = ds_sale(e, loai)
    g = {}
    nho = {}
    for x in xem:
        k = chuan(x["ten"])
        if k in NICK_THEO_GIO:
            chu = _chu_nick(k, x["t"], nho)
            if chu:
                k = chuan(chu)
        if k in ds and x["ten"] not in A.TEN_GUI_CUA_AI:
            # khoá theo TÊN HIỂN THỊ để bí danh gộp chung (POS "Thùy linh vận đơn" + Pancake "Linh Vận Đơn" = 1 người)
            g.setdefault(chuan(ds[k]), {"ten": ds[k], "t": set()})["t"].add(x["t"])
    for v in g.values():
        v["t"] = sorted(v["t"])
    return g


# ---------------------------------------------------------------- ca
def _dat(moc_dau, hm):
    """Mốc HH:MM đầu tiên KHÔNG trước moc_dau (epoch) — dựng khúc giờ qua nửa đêm."""
    d = datetime.fromtimestamp(moc_dau, VN)
    t = datetime(d.year, d.month, d.day, hm[0], hm[1], tzinfo=VN).timestamp()
    return t + 86400 if t < moc_dau - 60 else t


def _khuc(chuoi):
    kq = []
    for k in chuoi.split(";"):
        a, b = k.strip().split("-")
        kq.append((tuple(int(x) for x in a.split(":")), tuple(int(x) for x in b.split(":"))))
    return kq


def khung_ca(loai, ngay):
    """(đầu, cuối) epoch khung báo cáo của ca `loai` bắt đầu ngày `ngay` (date VN); cuối = hết phút "het"."""
    h1, m1 = CA[loai]["dau"]
    dau = datetime(ngay.year, ngay.month, ngay.day, h1, m1, tzinfo=VN).timestamp()
    cuoi = _dat(dau + 60, CA[loai]["het"]) + 60
    return dau, cuoi


def lich_nguoi(k, loai, ngay, ts):
    """Khúc làm (epoch) của người k (tên chuẩn hiển thị) trong ca `loai` ngày `ngay` → (nhãn phụ, [(đầu, cuối)]).
    Lịch luân phiên: chọn theo hoạt động đầu tiên trong khung ca (trước MOC_CA2 → phương án 1); chưa hoạt động → ("", [])."""
    ten = next((t for t in LICH if chuan(t) == k), None)
    if not ten:
        return "", []
    return _ks_tu_lich(LICH[ten][1], loai, ngay, ts)


def vai(ten):
    return "van_don" if "vận đơn" in chuan(ten) or "van don" in chuan(ten) else "sale"


def _ks_tu_lich(lich, loai, ngay, ts):
    """Lịch (chuỗi khúc hoặc luân phiên) đặt vào khung ca `loai` ngày `ngay` → (nhãn phụ, [(đầu, cuối)])."""
    dau, cuoi = khung_ca(loai, ngay)
    nhan = ""
    if not isinstance(lich, str):
        dau_tien = vao_that(ts, dau, cuoi) if len(ts) > 1 else next((t for t in ts if dau <= t < cuoi), None)
        if dau_tien is None:
            return "", []
        nhan, lich = lich[0] if dau_tien < _dat(dau, MOC_CA2) else lich[1]
    kq = []
    for a, b in _khuc(lich):
        x = _dat(dau, a)
        kq.append((x, _dat(x + 60, b) + 60))
    return nhan, sorted(kq)


def doi_ca_bao(k, ngay):
    """Ca người k làm ngày `ngay` theo doi_ca.json (chủ shop báo trước), không có → None."""
    return (doc_json(F_DOI_CA, {}).get(f"{ngay:%Y-%m-%d}") or {}).get(k)


def khach_ca(k, loai, ngay, ts, den=None):
    """Người k (ca gốc KHÁC `loai`) có làm ca `loai` ngày `ngay` không (đổi ca) → (nhãn, [khúc]) hoặc None.
    Chủ shop báo trước (doi_ca.json) → có luôn, khỏi đoán. Không báo: chỉ đếm hoạt động NGOÀI khúc làm ca gốc (±1 ngày), trong
    giờ chuẩn ca `loai` theo vai; tính tới mốc `den` nếu có; đủ độ phủ ô 10' (DOI_CA_*) và không phải làm liền từ ca gốc sang."""
    ten = next((t for t in LICH if chuan(t) == k), None)
    if not ten or LICH[ten][0] == loai or (loai, vai(ten)) not in LICH_CHUAN:
        return None
    if doi_ca_bao(k, ngay) == loai:
        return _ks_tu_lich(LICH_CHUAN[(loai, vai(ten))], loai, ngay, ts)
    if k in KHONG_DOI_CA:
        return None
    nha = []
    for d in (ngay - timedelta(days=1), ngay, ngay + timedelta(days=1)):
        nha += lich_nguoi(k, LICH[ten][0], d, ts)[1]
    ngoai = [t for t in ts if (den is None or t <= den) and not any(a <= t < b for a, b in nha)]
    nhan, ks = _ks_tu_lich(LICH_CHUAN[(loai, vai(ten))], loai, ngay, ngoai)
    trong = [t for t in ngoai if any(a <= t < b for a, b in ks)]
    moc = den if den is not None else time.time()
    o_co = {int(t // DOI_CA_O) for t in trong}
    tong_o = sum(max(0, min(b, moc) - a) for a, b in ks) / DOI_CA_O
    if len(o_co) < DOI_CA_O_MIN or len(o_co) < DOI_CA_TL * tong_o:
        return None
    # đang làm ca gốc rồi làm LIỀN sang giờ ca kia (≥3 lượt ca gốc trong 2h ngay trước) → LÀM THÊM GIỜ, không phải đổi ca
    # (vd Minh Thảo quá 22:30). Không xét ±12h: ca đêm tan 06:00 rồi 17:30 lên ca tối vẫn là đổi ca (24/09 22:40).
    if sum(1 for t in ts if trong[0] - 7200 <= t < trong[0] and any(a <= t < b for a, b in nha)) >= 3:
        return None
    # (Bỏ luật "cùng ngày vẫn làm ca gốc thì không phải đổi ca" 24/09 ~00:05: Quỳnh Trang hết ca tối đổi, ở lại lên đơn
    # 23:19–23:50 = giờ ca đêm của bạn ấy → bị coi là làm ca đêm → hết đổi ca + ⏸ 23:56 sai. Chủ shop: "hết ca nhưng ở lại lên
    # đơn, k cần ghi nhận". Trúc làm rải rác cả ngày đêm → loại riêng bằng KHONG_DOI_CA.)
    return nhan, ks


def sau_doi_ca(e, k, ts, den=None):
    """Mốc hoạt động thuộc CA ĐÃ ĐỔI (trong giờ ca đổi + làm tiếp liền sau, mỗi bước ≤30') — không tính là
    vào ca gốc. Chủ shop 24/09 22:37: Quỳnh Trang đổi lên ca tối, 22:31 còn thao tác (giờ ca đêm của bạn ấy) → bị nhắc vắng ca đêm."""
    lx = ca_cua(e).get(k)
    bo = set()
    if not ts or not lx:
        return bo
    d0 = datetime.fromtimestamp(ts[0], VN).date() - timedelta(days=1)
    d1 = datetime.fromtimestamp(ts[-1], VN).date()
    for lx2 in ca_bat(e):
        if lx2 == lx:
            continue
        d = d0
        while d <= d1:
            r = khach_ca(k, lx2, d, ts, den=den)
            d += timedelta(days=1)
            if not r:
                continue
            gtr = [x for x in ts if (den is None or x <= den) and any(a <= x < b for a, b in r[1])]
            # ca gốc liền kề ca đổi (bắt đầu trong [đầu ca đổi −12h, cuối ca đổi +1h]) = ca bị THAY: lượt trong khung đó là ở lại
            # lên đơn / làm thêm, không phải vào ca gốc → bỏ hết (chủ shop 24/09: "hết ca nhưng ở lại lên đơn, k cần ghi nhận").
            # Làm cả khi ca đổi CHƯA có lượt nào (đổi ca báo trước: tối Trúc chưa vào ca đêm thì ca tối vẫn là ca bị thay).
            g_dau, g_cuoi = khung_ca(lx2, d - timedelta(days=1))
            for dd in (d - timedelta(days=2), d - timedelta(days=1), d):
                h_dau, h_cuoi = khung_ca(lx, dd)
                if g_dau - 12 * 3600 <= h_dau <= g_cuoi + 3600:
                    bo.update(x for x in ts if h_dau <= x < h_cuoi and (den is None or x <= den))
            if not gtr:
                continue
            bo.update(gtr)                               # lượt trong giờ ca đổi (kể cả đúng ranh giới 22:30) thuộc ca đổi
            truoc = gtr[-1]
            for x in ts:
                if x <= gtr[-1] or (den is not None and x > den):
                    continue
                if x - truoc > 1800:
                    break
                bo.add(x)
                truoc = x
    return bo


def khuc_hien(e, k, t, ts, ts_nha=None):
    """Khúc làm của người k chứa mốc t → (ca, ngày ca, chỉ số khúc, [khúc]); ngoài giờ làm → None.
    Xét ca đang đổi sang trước (khach_ca tính tới mốc t), rồi ca gốc với ts_nha (đã bỏ phần làm tiếp sau đổi ca)."""
    lx = ca_cua(e).get(k)
    if not lx:
        return None
    r_doi = _khuc_doi_ca(e, k, t, ts, lx)
    if r_doi:
        return r_doi
    for lui in (0, 1):
        ngay = datetime.fromtimestamp(t, VN).date() - timedelta(days=lui)
        _, ks = lich_nguoi(k, lx, ngay, ts if ts_nha is None else ts_nha)
        for i, (a, b) in enumerate(ks):
            if a <= t < b:
                return lx, ngay, i, ks
    return None


def _khuc_doi_ca(e, k, t, ts, lx):
    for lx2 in ca_bat(e):
        if lx2 == lx:
            continue
        for lui in (0, 1):
            ngay = datetime.fromtimestamp(t, VN).date() - timedelta(days=lui)
            r = khach_ca(k, lx2, ngay, ts, den=t)
            for i, (a, b) in enumerate(r[1] if r else []):
                if a <= t < b:
                    return lx2, ngay, i, r[1]
    return None


def ca_chua(t, cac_ca=None):
    """Ca (đang bật) chứa mốc t → (loai, ngày bắt đầu ca, đầu, cuối); ngoài giờ ca bật → None."""
    for lui in (0, 1):
        d0 = datetime.fromtimestamp(t, VN).date() - timedelta(days=lui)
        for lx in (cac_ca or ca_bat(env())):
            dau, cuoi = khung_ca(lx, d0)
            if dau <= t < cuoi:
                return lx, d0, dau, cuoi
    return None


def cac_ca_vua_het(bay_gio):
    """Mọi ca (đang bật) đã hết ≥BAO_SAU_PHUT phút mà chưa quá BAO_TRE_GIO: [(giờ hết, loai, ngày bắt đầu ca)]."""
    hom_nay = datetime.fromtimestamp(bay_gio, VN).date()
    ung = []
    for lui in (0, 1, 2):
        ngay = hom_nay - timedelta(days=lui)
        for loai in ca_bat(env()):
            dau, cuoi = khung_ca(loai, ngay)
            if cuoi + BAO_SAU_PHUT * 60 <= bay_gio <= cuoi + BAO_TRE_GIO * 3600:
                ung.append((cuoi, loai, ngay))
    return sorted(ung)


# ---------------------------------------------------------------- tin 1 + 2: vắng / quay lại
def _gop_khuc(ks):
    kq = []
    for a, b in sorted(ks):
        if kq and a <= kq[-1][1]:
            kq[-1] = (kq[-1][0], max(kq[-1][1], b))
        else:
            kq.append((a, b))
    return kq


def tach_chung_nick(xem, khoi, ngay, den=None):
    """Khối chung nick (ca luân phiên) đêm `ngay` → [{ten, nhan, ks, ts}]: tách 2 bạn nếu khác ca, không thì 1 khối.
    Ca của từng bạn = khung (ca 1 / ca 2) chứa nhiều thao tác POS RIÊNG nhất; 1 bạn đã rõ ca mà nick chung có làm đủ ở khung còn
    lại → bạn kia làm khung còn lại. Chưa rõ ai → 1 khối (ca theo nick chung, hoặc "ca 1 + ca 2" nếu nick chung làm cả 2 khung)."""
    lx = LICH[khoi][0]
    dau, cuoi = khung_ca(lx, ngay)
    moc = den if den is not None else time.time()
    ev = [x for x in xem if dau - 3600 <= x["t"] < cuoi + 3600 and x["t"] <= moc]
    nick = chuan(CHUNG_NICK_CHAT[khoi])
    seat = sorted(x["t"] for x in ev if chuan(x["ten"]) == nick and x.get("loai", "pan") != "pos")
    ban = CHUNG_NICK[khoi]
    pos = {b: sorted(x["t"] for x in ev if chuan(x["ten"]) == chuan(b) and x.get("loai") == "pos") for b in ban}
    kss = [_ks_tu_lich(l, lx, ngay, [])[1] for _, l in DEM_LUAN_PHIEN]
    nhans = [n for n, _ in DEM_LUAN_PHIEN]
    trong = lambda ts, ks: [t for t in ts if any(a <= t < b for a, b in ks)]   # noqa: E731

    def phu(ks):
        o = {int(t // DOI_CA_O) for t in trong(seat, ks)}
        tong = sum(max(0, min(b, moc) - a) for a, b in ks) / DOI_CA_O
        return len(o) >= DOI_CA_O_MIN and len(o) >= DOI_CA_TL * tong

    gan = {}
    for b in ban:
        n = [len(trong(pos[b], ks)) for ks in kss]
        gan[b] = None if not any(n) else n.index(max(n))
    a_, b_ = ban
    if gan[a_] is not None and gan[b_] is None and phu(kss[1 - gan[a_]]):
        gan[b_] = 1 - gan[a_]
    if gan[b_] is not None and gan[a_] is None and phu(kss[1 - gan[b_]]):
        gan[a_] = 1 - gan[b_]
    if gan[a_] is not None and gan[b_] is not None and gan[a_] != gan[b_]:
        return [{"ten": b, "nhan": nhans[gan[b]], "ks": kss[gan[b]], "ts": sorted(trong(seat, kss[gan[b]]) + pos[b])}
                for b in ban]
    ts_all = sorted(seat + pos[a_] + pos[b_])
    if not ts_all:
        return []
    c = gan[a_] if gan[a_] is not None else gan[b_]
    if c is None and phu(kss[0]) and phu(kss[1]):
        return [{"ten": khoi, "nhan": "ca 1 + ca 2", "ks": _gop_khuc(kss[0] + kss[1]), "ts": ts_all}]
    if c is None:
        nhan, ks = _ks_tu_lich(DEM_LUAN_PHIEN, lx, ngay, ts_all)
    else:
        nhan, ks = nhans[c], kss[c]
    return [{"ten": khoi, "nhan": nhan, "ks": ks, "ts": ts_all}]


def xet_vang(e, so, bay_gio=None):
    """Theo sổ 3 giờ qua: ai vừa vắng ≥ ngưỡng (tin 1), ai vừa quay lại (tin 2). Cập nhật so["nghi"] tại chỗ.
    Trả [(kieu, tên, tu, den, ca)] — kieu 'vang' hoặc 'lai'; ca = ca của người đó (để gửi đúng nhóm)."""
    bay_gio = bay_gio or time.time()
    xem = doc_so(bay_gio - 14 * 3600, bay_gio + 60)   # 14 giờ: cần hoạt động đầu đêm để biết ca 1/ca 2
    g = theo_nguoi(xem, e)
    mo = so.setdefault("nghi", {})
    kq = []
    ds = []                                              # (khoá, tên, ts, khúc hiện tại | None)
    chung = {chuan(x) for x in CHUNG_NICK}
    for k, v in g.items():
        if k in chung:
            continue
        ts = v["t"]
        bo = sau_doi_ca(e, k, ts, bay_gio)
        ts_nha = [t for t in ts if t not in bo]
        kh = khuc_hien(e, k, bay_gio, ts, ts_nha)
        if not kh or kh[0] == ca_cua(e).get(k):         # ca gốc / ngoài giờ → bỏ lượt thuộc ca đổi + ca bị thay
            ts = ts_nha
        ds.append((k, v["ten"], ts, kh))
    for khoi in CHUNG_NICK:                              # chung nick → tách theo ca 1/ca 2 như báo cáo
        lx = LICH[khoi][0]
        if lx not in ca_bat(e):
            continue
        for lui in (0, 1):
            ngay = datetime.fromtimestamp(bay_gio, VN).date() - timedelta(days=lui)
            dau, cuoi = khung_ca(lx, ngay)
            if not (dau <= bay_gio < cuoi):
                continue
            for v in tach_chung_nick(xem, khoi, ngay, den=bay_gio):
                kh = next(((lx, ngay, i, v["ks"]) for i, (a, b) in enumerate(v["ks"]) if a <= bay_gio < b), None)
                ds.append((chuan(v["ten"]), v["ten"], v["ts"], kh))
    for k, ten, ts, kh in ds:
        nghi = nguong_nghi(e, ten)
        ep = mo.get(k)
        if ep:
            sau = [t for t in ts if t > ep["tu"] + 1]
            het = ep.get("het") or 0
            if sau and sau[0] < het:                     # quay lại trong khúc làm → tin 2, đóng đợt
                kq.append(("lai", ten, ep["tu"], sau[0], ep.get("ca") or ca_cua(e).get(k)))
                mo.pop(k)
            elif sau or bay_gio >= het or bay_gio - ep["tu"] > 4 * 3600:
                mo.pop(k)                                # hết khúc làm / quá 4 giờ / quay lại sau giờ làm → đóng im
            continue
        if not kh:                                       # bây giờ không phải giờ làm của người này
            continue
        lx, ngay, i, ks = kh
        a, b = ks[i]
        trong = [t for t in ts if a <= t <= bay_gio]
        if trong:
            moc = trong[-1]
            if not any(moc - 3600 <= t < moc for t in ts):   # mới có đúng 1 lượt → chưa chắc đang làm
                continue
        elif i > 0 and any(ks[0][0] <= t < a for t in ts):   # khúc sau giờ nghỉ mà chưa quay lại → vắng từ đầu khúc
            moc = a
        else:
            continue                                     # chưa vào ca → không nhắc (giờ vào ca có trong báo cáo)
        if bay_gio - moc < nghi or bay_gio - moc > 3600:  # timer 2' bắt vắng ở phút 5–7; quá 1 giờ = đã về
            continue
        kq.append(("vang", ten, moc, bay_gio, lx))
        mo[k] = {"tu": moc, "het": b, "bao": bay_gio, "ten": ten, "ca": lx}
    # ⏰ VÀO CA TRỄ (chủ shop 25/09 09:45: "sáng nay Duyên vào ca muộn, k thấy báo" — Duyên vào 09:11, ca 08:00; chốt 10:00:
    # "sau 5 phút chưa vào ca ngày, ca đêm thì hiện ⏰ X chưa vào ca, đến khi bắt đầu làm: X đã vào ca lúc … — trễ N phút").
    # Ngưỡng 5' cho MỌI người (cả vận đơn). Sale ca đêm luân phiên / chung nick: chưa vào thì không biết ca 1 hay ca 2 → chỉ nhắc
    # khi quá giờ vào muộn nhất (ca 2 = 01:30) +5' mà cả đêm chưa hoạt động; vào ca thì trễ tính theo ca nhận được.
    # Người đang đổi sang ca khác (🔁) → không nhắc ở ca gốc.
    tre = so.setdefault("tre", {})
    for ten, (lx, lich) in LICH.items():
        if lx not in ca_bat(e):
            continue
        k = chuan(ten)
        ts = (g.get(k) or {}).get("t") or []
        for lui in (0, 1):
            ngay = datetime.fromtimestamp(bay_gio, VN).date() - timedelta(days=lui)
            f_dau, f_cuoi = khung_ca(lx, ngay)
            if isinstance(lich, str):
                _, ks = lich_nguoi(k, lx, ngay, [])
                moc_vao = ks[0][0] if ks else None                 # giờ phải vào
                het = ks[-1][1] if ks else None
            else:                                                  # luân phiên: ca 1 22:30 / ca 2 01:30
                moc_vao = _ks_tu_lich(lich[-1][1], lx, ngay, [])[1][0][0]   # vào muộn nhất = đầu ca cuối
                het, ks = f_cuoi, None
            if moc_vao is None or not (f_dau <= bay_gio < het):
                continue
            khoa = f"{ngay:%Y-%m-%d} {lx} {k}"
            dau_tien = next((t for t in ts if f_dau <= t < het), None) if ks is None else \
                next((t for t in ts if ks[0][0] <= t < het), None)
            if any(doi_ca_bao(k, d) not in (None, lx) for d in (ngay - timedelta(days=1), ngay)):
                continue                                           # chủ shop báo đổi sang ca khác → ca gốc không nhắc
            if khoa in tre:
                if dau_tien and not tre[khoa].get("vao"):
                    if ks is None:                                 # luân phiên: trễ theo ca nhận được
                        _, kn = _ks_tu_lich(lich, lx, ngay, [dau_tien])
                        goc = kn[0][0] if kn else moc_vao
                    else:
                        goc = moc_vao
                    kq.append(("vao", ten, goc, dau_tien, lx))
                    tre[khoa]["vao"] = dau_tien
            elif dau_tien is None and bay_gio - moc_vao >= TRE_VAO_PHUT * 60:
                if any(khach_ca(k, lx2, d, ts, den=bay_gio) for lx2 in ca_bat(e) if lx2 != lx
                       for d in (ngay - timedelta(days=1), ngay)):
                    continue                                       # đang đổi sang ca khác → không phải trễ
                kq.append(("tre", ten, moc_vao, bay_gio, lx))
                tre[khoa] = {"luc": bay_gio}
    for lui in (0, 1):                                   # người đổi ca BÁO TRƯỚC: nhắc vào ca trễ theo ca mới
        ngay = datetime.fromtimestamp(bay_gio, VN).date() - timedelta(days=lui)
        for k, lx in (doc_json(F_DOI_CA, {}).get(f"{ngay:%Y-%m-%d}") or {}).items():
            ten = next((t for t in LICH if chuan(t) == k), None)
            if not ten or lx not in ca_bat(e) or LICH[ten][0] == lx or (lx, vai(ten)) not in LICH_CHUAN:
                continue
            lich = LICH_CHUAN[(lx, vai(ten))]
            if not isinstance(lich, str):
                continue                                   # sale luân phiên: không biết ca 1/ca 2 trước khi vào
            ts = (g.get(k) or {}).get("t") or []
            _, ks = _ks_tu_lich(lich, lx, ngay, [])
            if not ks or not (ks[0][0] <= bay_gio < ks[-1][1]):
                continue
            khoa = f"{ngay:%Y-%m-%d} {lx} {k}"
            dau_tien = next((t for t in ts if ks[0][0] <= t < ks[-1][1]), None)
            if khoa in tre:
                if dau_tien and not tre[khoa].get("vao"):
                    kq.append(("vao", ten, ks[0][0], dau_tien, lx))
                    tre[khoa]["vao"] = dau_tien
            elif dau_tien is None and bay_gio - ks[0][0] >= TRE_VAO_PHUT * 60:
                kq.append(("tre", ten, ks[0][0], bay_gio, lx))
                tre[khoa] = {"luc": bay_gio}
    for x in [x for x in tre if x < f"{datetime.fromtimestamp(bay_gio, VN) - timedelta(days=2):%Y-%m-%d}"]:
        tre.pop(x)
    co = {d[0] for d in ds}
    for k in [k for k, ep in mo.items() if bay_gio - ep.get("tu", 0) > 86400
              or (k not in co and bay_gio >= (ep.get("het") or 0))]:   # đợt của tên đã đổi cách tách (chung nick) → đóng
        mo.pop(k)
    return kq


def tin_vang(ten, tu, bay_gio):
    # chủ shop 26/09 08:20: "đừng để chưa hoạt động pan/pos → sửa thành vắng mặt trong ca làm"
    return f"⏸ {ten} vắng mặt trong ca làm {phut(bay_gio - tu)} (từ {vn(tu)})."


def tin_lai(ten, tu, den):
    return f"▶️ {ten} đã hoạt động lại lúc {vn(den)} — vắng mặt {phut(den - tu)} ({vn(tu)}–{vn(den)})."


def tin_nhac(kieu, ten, tu, den):
    """kieu: vang (⏸) · lai (▶️ sau vắng) · tre (⏰ chưa vào ca) · vao (▶️ vào ca trễ)."""
    if kieu == "vang":
        return tin_vang(ten, tu, den)
    if kieu == "lai":
        return tin_lai(ten, tu, den)
    if kieu == "tre":
        return f"⏰ {ten} chưa vào ca"                    # đúng chữ chủ shop chốt 25/09 10:00
    return f"▶️ {ten} đã vào ca lúc {vn(den)} — trễ {int(((den // 60 * 60) - tu) // 60)} phút."


ICON_NHAC = {"vang": "⏸", "lai": "▶️", "tre": "⏰", "vao": "▶️ vào"}


# ---------------------------------------------------------------- tin 3: báo cáo ca
def bao_cao_ca(loai, ngay, e):
    dau, cuoi = khung_ca(loai, ngay)
    g = theo_nguoi(doc_so(dau - 3600, cuoi + 3600), e, loai)
    d_dau = datetime.fromtimestamp(dau, VN)
    # chủ shop 24/09 12:50: tiêu đề "BÁO CÁO HOẠT ĐỘNG SALE"
    dong = [f"📋 BÁO CÁO HOẠT ĐỘNG SALE — {CA[loai]['nhan']} {THU[d_dau.weekday()]}, ngày {d_dau:%d} tháng {d_dau:%m} năm {d_dau:%Y} "
            f"({vn(dau)}–{vn(cuoi - 60)})"]
    bay_gio = time.time()
    nguoi = []
    for k, v in g.items():
        nhan, ks = lich_nguoi(k, loai, ngay, v["t"])
        trong = [t for t in v["t"] if any(a <= t < b for a, b in ks)]
        if not trong:
            continue
        nghi = nguong_nghi(e, v["ten"])
        quang = []
        for i, (a, b) in enumerate(ks):
            tk = [t for t in trong if a <= t < b]
            if i > 0 and any(t < a for t in trong) and a < bay_gio:   # về trễ sau giờ nghỉ (hoặc không về) = vắng
                den = tk[0] if tk else min(b, bay_gio)
                if den - a >= nghi:
                    quang.append((a, den))
            quang += [(x, y) for x, y in zip(tk, tk[1:]) if y - x >= nghi]
        ten = v["ten"] + (f" ({nhan})" if nhan else "")
        nguoi.append({"ten": ten, "vao": trong[0], "tan": trong[-1], "quang": quang})
    if not nguoi:
        dong.append("Không thấy sale/vận đơn nào hoạt động trong ca.")
        return "\n".join(dong)
    nguoi.sort(key=lambda x: x["vao"])
    dong.append("Thời gian vào ca làm: " + ", ".join(f"{x['ten']} lúc {vn(x['vao'])}" for x in nguoi))
    vang = [f"{x['ten']} {phut(sum(b - a for a, b in x['quang']))}" + (f" ({len(x['quang'])} lần)" if len(x["quang"]) > 1 else "")
            for x in nguoi if x["quang"]]
    dong.append("Thời gian vắng mặt: " + (", ".join(vang) if vang else "không có"))
    dong.append("Thời gian tan ca làm: " + ", ".join(f"{x['ten']} lúc {vn(x['tan'])}" for x in nguoi))
    return "\n".join(dong)


# Mẫu báo cáo mới (chủ shop 24/09 21:15: "nhìn báo cáo có chán k, thiết kế logic và thêm icon cho đẹp") — khối riêng từng người.
# Màu theo tổng phút vắng: 🟢 ≤30' · 🟡 31–90' hoặc vào trễ/tan sớm ≥10' · 🔴 >90' · ⚪ không có hoạt động trong ca.
# 21:30 chủ shop sửa: bỏ dòng lịch, liệt kê mọi quãng vắng "(12:01 - 12:40), (… - …)", bỏ khối tổng cuối.
MAU_XANH, MAU_DO, TRE_PHUT = 30, 90, 5   # chủ shop 24/09 21:45: ghi (trễ/sớm) chỉ khi ≥5 phút
TRE_VAO_PHUT = 5        # ⏰ chưa vào ca sau 5' — mọi người, ca ngày + ca đêm (chủ shop 25/09 10:00)


def _hm(lich_khuc):
    return " + ".join(f"{vn(a)}–{vn(b - 60)}" for a, b in lich_khuc)


def bao_cao_ca_dep(loai, ngay, e, cho=None):
    """cho: list để nhận người ⏳ chờ chốt (luot() lưu vào so_bao) — None khi chỉ xem."""
    dau, cuoi = khung_ca(loai, ngay)
    xem_tho = doc_so(dau - 30 * 3600, cuoi + 3600)
    g = theo_nguoi(xem_tho, e)                           # mọi ca, lùi 30h: cần để nhận đổi ca
    d_dau = datetime.fromtimestamp(dau, VN)
    bay_gio = time.time()
    ds_ten = list(dict.fromkeys(ten for ten, (lx, _) in LICH.items() if lx == loai))
    khach = [ten for ten, (lx, _) in LICH.items() if lx != loai and lx in ca_bat(e)
             and khach_ca(chuan(ten), loai, ngay, (g.get(chuan(ten)) or {}).get("t") or [])]
    nguoi, vang_mat, muc = [], [], []
    for ten in ds_ten + khach:
        if ten in CHUNG_NICK:                            # chung nick → tự tách theo ca 1/ca 2 (POS riêng từng bạn)
            vs = tach_chung_nick(xem_tho, ten, ngay)
            muc += [(v["ten"], v["nhan"], v["ks"], v["ts"], False, True) for v in vs]
            if not vs:
                vang_mat.append(ten)
            continue
        k = chuan(ten)
        ts = (g.get(k) or {}).get("t") or []
        doi = ten in khach
        if doi:
            nhan, ks = khach_ca(k, loai, ngay, ts)
        else:
            bo = sau_doi_ca(e, k, ts)
            ts = [t for t in ts if t not in bo]
            nhan, ks = lich_nguoi(k, loai, ngay, ts)
        muc.append((ten, nhan, ks, ts, doi, False))
    for ten, nhan, ks, ts, doi, chung in muc:
        trong = [t for t in ts if any(a <= t < b for a, b in ks)]
        if not trong:
            if ten not in vang_mat:
                vang_mat.append(ten)
            continue
        nghi = nguong_nghi(e, ten)
        quang = []
        for i, (a, b) in enumerate(ks):
            tk = [t for t in trong if a <= t < b]
            if i > 0 and any(t < a for t in trong) and a < bay_gio:
                den = tk[0] if tk else min(b - 60, bay_gio)      # b = hết phút cuối (+60s) → hiện đúng giờ tròn
                if den - a >= nghi:
                    quang.append((a, den))
            quang += [(x, y) for x, y in zip(tk, tk[1:]) if y - x >= nghi]
        tong = sum(y - x for x, y in quang)
        # trễ/sớm tính trên giờ:phút ĐÃ HIỆN (bỏ giây) để "Vào 08:10" không thành "trễ 11 phút"
        tre = (trong[0] // 60 * 60) - ks[0][0]
        som = (ks[-1][1] - 60) - (trong[-1] // 60 * 60) if bay_gio > ks[-1][1] else 0
        if tong > MAU_DO * 60:
            mau = "🔴"
        elif tong > MAU_XANH * 60 or tre >= TRE_PHUT * 60 or som >= TRE_PHUT * 60:
            mau = "🟡"
        else:
            mau = "🟢"
        nguoi.append({"ten": ten, "nhan": nhan, "ks": ks, "vao": trong[0], "tan": trong[-1], "tre": tre, "som": som,
                      "quang": quang, "tong": tong, "mau": mau, "nghi": nghi, "doi": doi, "chung": chung})
    nguoi.sort(key=lambda x: x["vao"])
    dong = ["📋 *BÁO CÁO HOẠT ĐỘNG SALE*",
            f"🗓 *{CA[loai]['nhan']}* · {THU[d_dau.weekday()]} {d_dau:%d/%m/%Y} · ⏰ {vn(dau)}–{vn(cuoi - 60)}",
            "━━━━━━━━━━━━━━━"]
    for x in nguoi:
        vt = "📦 Vận đơn" if "vận đơn" in chuan(x["ten"]) else "💬 Sale"
        dong.append("")
        dong.append(f"{x['mau']} *{x['ten']}*" + (f" ({x['nhan']})" if x["nhan"] else "") + f" · {vt}"
                    + (" · 👥 chung nick" if x["chung"] else "") + (" · 🔁 đổi ca" if x["doi"] else ""))
        vao = f"🟩 Vào {vn(x['vao'])}" + (f" _(trễ {int(x['tre'] // 60)} phút)_" if x["tre"] >= TRE_PHUT * 60 else "")
        tan = f"🟥 Tan {vn(x['tan'])}" + (f" _(sớm {int(x['som'] // 60)} phút)_" if x["som"] >= TRE_PHUT * 60 else "")
        dong.append(f"      {vao}  ·  {tan}")
        if x["quang"]:                                   # chủ shop 24/09 21:30: liệt kê MỌI quãng dạng (12:01 - 12:40)
            lan = f" ({len(x['quang'])} lần)" if len(x["quang"]) > 1 else ""
            qs = [f"({vn(a)} - {vn(b)})" for a, b in x["quang"]]
            quang = qs[0] if len(qs) == 1 else ", ".join(qs[:-1]) + " và " + qs[-1]   # "(…), (…) và (…)"
            dong.append(f"      ⏸ Vắng *{phut(x['tong'])}*{lan}: {quang}")
        # không vắng → không ghi dòng nào (chủ shop 24/09 21:55: "k vắng thì k note")
    for ten in vang_mat:
        vt = "📦 Vận đơn" if "vận đơn" in chuan(ten) else "💬 Sale"
        ts = (g.get(chuan(ten)) or {}).get("t") or []
        sang = next(((lx2, d) for lx2 in ca_bat(e) if lx2 != loai
                     for d in (ngay, ngay - timedelta(days=1), ngay + timedelta(days=1))
                     if khach_ca(chuan(ten), lx2, d, ts)), None)
        sau = [c for c in ca_sau(loai, ngay, ten) if c[2] > bay_gio] if ten in LICH else []
        if doi_ca_bao(chuan(ten), ngay) == "off":        # chủ shop / trưởng ca đã báo off (#off)
            dong += ["", f"😴 *{ten}* · {vt}", "      Nghỉ (off) — đã báo trước"]
        elif sang:
            dong += ["", f"🔁 *{ten}* · {vt}", f"      🔁 Đổi sang {CA[sang[0]]['nhan']} ({sang[1]:%d/%m})"]
        elif bay_gio < cuoi:                             # ca chưa hết (xem giữa ca)
            dong += ["", f"⏰ *{ten}* · {vt}", "      Chưa vào ca"]
        elif sau:                                        # còn ca sau có thể đổi sang → chưa chốt được (chủ shop 25/09 18:20)
            dong += ["", f"⏳ *{ten}* · {vt}", f"      Không làm {CA[loai]['nhan']} — chờ xem đổi ca hay nghỉ"]
            if cho is not None:
                cho.append({"ten": ten, "ca": loai, "ngay": f"{ngay:%Y-%m-%d}", "han": max(c[2] for c in sau)})
        else:                                            # cả ca không làm = nghỉ (chủ shop 25/09 10:00: "k làm = off, tức là nghỉ")
            dong += ["", f"😴 *{ten}* · {vt}", "      Nghỉ (off)"]
    # chủ shop 24/09 21:30–21:40: bỏ khối tổng cuối + bỏ dòng chú thích màu → báo cáo dừng ở người cuối cùng
    return "\n".join(dong)


# ---------------------------------------------------------------- lệnh WhatsApp + chốt muộn
def bo_dau(s):
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").lower().split())


TU_CA = {"dem": "dem", "toi": "toi", "ngay": "ngay", "sang": "ngay"}


def _ngay_ca(lx, bay_gio, lui_toi_da=1):
    """Phiên ca `lx` đang chạy (bắt đầu hôm qua/nay) → ngày của nó; không có → hôm nay nếu chưa hết, không thì mai."""
    hom_nay = datetime.fromtimestamp(bay_gio, VN).date()
    for lui in range(lui_toi_da, -1, -1):
        d = hom_nay - timedelta(days=lui)
        a, b = khung_ca(lx, d)
        if a <= bay_gio < b:
            return d
    return hom_nay if bay_gio < khung_ca(lx, hom_nay)[1] else hom_nay + timedelta(days=1)


def doc_lenh(chu, bay_gio):
    """"#doica Trúc đêm [dd/mm]" | "#off Thu Hiền [dd/mm]" → ({kieu, ten, lx, ngay}, None) hoặc (None, lời lỗi)."""
    t = bo_dau(chu)
    m = re.match(r"#\s*(doi\s*ca|doica|off|nghi)\b(.*)$", t)
    if not m:
        return None, None                                # không phải lệnh của máy này → im
    kieu = "off" if m.group(1) in ("off", "nghi") else "doica"
    rest = re.sub(r"\bngay\s+(?=\d{1,2}\s*/)", " ", m.group(2))
    ngay = None
    md = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", rest)
    if md:
        try:
            ngay = date(datetime.fromtimestamp(bay_gio, VN).year, int(md.group(2)), int(md.group(1)))
        except ValueError:
            return None, "ngày không hợp lệ"
        rest = rest[:md.start()] + " " + rest[md.end():]
    tu = rest.split()
    lx = next((TU_CA[w] for w in reversed(tu) if w in TU_CA), None) if kieu == "doica" else None
    ten_tu = [w for w in tu if w not in TU_CA and w not in ("ca", "lam", "xuong", "len", "qua", "hom", "nay", "mai")]
    # "Mai Linh": chữ "mai" vừa là tên vừa là "ngày mai" → thử giữ "mai" trước, khớp đúng 1 người thì dùng
    ten_tu_mai = [w for w in tu if w not in TU_CA and w not in ("ca", "lam", "xuong", "len", "qua", "hom", "nay")]
    ung_mai = [ten for ten in LICH if ten_tu_mai and all(w in bo_dau(ten).split() for w in ten_tu_mai)]
    if len(ung_mai) == 1:
        ten_tu = ten_tu_mai
    if not ten_tu:
        return None, "thiếu tên người"
    ung = [ten for ten in LICH if all(w in bo_dau(ten).split() for w in ten_tu)]
    if len(ung) != 1:
        goi_y = ", ".join(ung) if ung else "không ai"
        return None, f"tên \"{' '.join(ten_tu)}\" khớp {goi_y} — gõ đủ tên hơn"
    ten = ung[0]
    if kieu == "doica" and not lx:
        return None, "thiếu ca (ngày / tối / đêm)"
    if kieu == "doica" and lx != LICH[ten][0] and (lx, vai(ten)) not in LICH_CHUAN:
        return None, f"chưa có giờ chuẩn {CA[lx]['nhan']} cho {ten}"
    if ngay is None:
        ngay = _ngay_ca(lx or LICH[ten][0], bay_gio)
        if tu.count("mai") - (1 if "mai" in ten_tu else 0) > 0:   # "#off Mai Linh mai" = ngày mai
            ngay += timedelta(days=1)
    return {"kieu": kieu, "ten": ten, "lx": lx, "ngay": ngay}, None


def xu_lenh(e, so):
    """Đọc lệnh mới trong lenh.jsonl → ghi doi_ca.json + trả lời trong nhóm."""
    da = so.setdefault("lenh_da_xu", [])
    try:
        dong = open(F_LENH, encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return
    lid = doc_json(F_LID, {})
    for d in dong:
        try:
            x = json.loads(d)
        except ValueError:
            continue
        if x.get("id") in da or time.time() - float(x.get("t") or 0) > 2 * 86400:
            continue
        da.append(x.get("id"))
        so_gui = ""
        for j in (x.get("ai"), x.get("ai2")):
            j = str(j or "")
            if j.endswith("@s.whatsapp.net"):
                so_gui = so_gui or _sdt(j.split("@")[0].split(":")[0])
            elif j.endswith("@lid"):
                so_gui = so_gui or lid.get(j.split("@")[0].split(":")[0], "")
        if so_gui not in LENH_SO:
            log(f"lệnh từ số {so_gui or '?'} (không có quyền) bỏ qua: {x.get('chu', '')[:60]}")
            continue
        l, loi = doc_lenh(x.get("chu", ""), float(x["t"]))
        if l is None and loi is None:
            continue
        if l is None:
            tra = f"❓ Chưa hiểu lệnh: {loi}.\nVí dụ: #doica Trúc đêm · #doica Quỳnh Trang tối 26/09 · #off Thu Hiền 26/09"
        else:
            k, khoa = chuan(l["ten"]), f"{l['ngay']:%Y-%m-%d}"
            bang = doc_json(F_DOI_CA, {})
            if l["kieu"] == "off":
                bang.setdefault(khoa, {})[k] = "off"
                tra = f"✅ Đã ghi: {l['ten']} nghỉ (off) {CA[LICH[l['ten']][0]]['nhan']} {l['ngay']:%d/%m}."
            elif l["lx"] == LICH[l["ten"]][0]:
                bang.get(khoa, {}).pop(k, None)
                tra = f"✅ Đã ghi: {l['ten']} làm lại {CA[l['lx']]['nhan']} {l['ngay']:%d/%m} như lịch gốc."
            else:
                bang.setdefault(khoa, {})[k] = l["lx"]
                tra = f"✅ Đã ghi: {l['ten']} làm {CA[l['lx']]['nhan']} {l['ngay']:%d/%m} (đổi ca)."
            ghi_json(F_DOI_CA, {d_: v for d_, v in bang.items() if v})
        ok, err = gui_wa(tra, x.get("nhom"))
        log("lệnh:", x.get("chu", "")[:60], "→", tra.splitlines()[0], "| gửi" if ok else f"| CHƯA GỬI ({err})")
    so["lenh_da_xu"] = da[-500:]


def ca_sau(loai, ngay, ten):
    """Các phiên ca KHÁC bắt đầu trong [hết ca −1h, hết ca +6h] mà người này có giờ chuẩn → [(ca, ngày, hết ca)]."""
    _, cuoi = khung_ca(loai, ngay)
    kq = []
    for lx2 in CA:
        if lx2 == loai or (lx2, vai(ten)) not in LICH_CHUAN:
            continue
        for d in (ngay, ngay + timedelta(days=1)):
            a2, b2 = khung_ca(lx2, d)
            if cuoi - 3600 <= a2 <= cuoi + 6 * 3600:
                kq.append((lx2, d, b2))
    return kq


def chot_muon(e, so):
    """Hết các ca sau → chốt người ⏳: đổi ca hay nghỉ, nhắn nhóm ca gốc."""
    cho = so.setdefault("cho_chot", {})
    for khoa, c in list(cho.items()):
        if time.time() < c["han"] + BAO_SAU_PHUT * 60:
            continue
        cho.pop(khoa)
        k, ngay = chuan(c["ten"]), date.fromisoformat(c["ngay"])
        g = theo_nguoi(doc_so(c["han"] - 40 * 3600, c["han"] + 3600), e)
        ts = (g.get(k) or {}).get("t") or []
        sang = next(((lx2, d) for lx2, d, _ in ca_sau(c["ca"], ngay, c["ten"]) if khach_ca(k, lx2, d, ts)), None)
        if sang:
            tra = f"🔁 {c['ten']} đã đổi sang {CA[sang[0]]['nhan']} ({sang[1]:%d/%m}) — không làm {CA[c['ca']]['nhan']} {ngay:%d/%m}."
        else:
            tra = f"😴 {c['ten']} nghỉ (off) {CA[c['ca']]['nhan']} {ngay:%d/%m} — không làm ca nào."
        ok, err = gui_wa(tra, nhom_ca(e, c["ca"]))
        log("chốt muộn:", tra, "→", "đã gửi" if ok else f"CHƯA GỬI ({err})")


# ---------------------------------------------------------------- gửi
def gui_wa(text, jid):
    if not jid:
        return False, "chưa có mã nhóm"
    try:
        r = subprocess.run(["node", NODE_GUI, text], cwd="/opt/aicloser", env=dict(os.environ, WA_JID=jid),
                           capture_output=True, text=True, timeout=120)
    except Exception as ex:                              # noqa: BLE001
        return False, str(ex)
    if r.returncode == 0:
        return True, ""
    ra = (r.stdout or "").strip().splitlines()
    return False, (ra[-1] if ra else (r.stderr or "").strip()[-200:] or f"node thoát mã {r.returncode}")


# ---------------------------------------------------------------- chạy
def luot():
    e = env()
    so = doc_json(F_SO, {})
    xem, chua_doc, loi = quet()
    moi = ghi_so(xem)
    dong = f"Pancake: {len(xem)} lượt xem thấy, {moi} mới vào sổ, {chua_doc} hội thoại chưa đọc" + (f" · LỖI {loi}" if loi else "")
    if (e.get("GIO_LAM_POS") or "1") != "0":
        pos, loi_pos, thieu = quet_pos()
        moi_pos = ghi_so(pos)
        dong += f" · POS: {len(pos)} lượt sửa đơn, {moi_pos} mới" + (f", {thieu} lượt chưa rõ tên" if thieu else "") \
            + (f" · LỖI {'; '.join(loi_pos)}" if loi_pos else "")
    try:
        wa, la = quet_wa(e)
        dong += f" · WhatsApp nhóm: {len(wa)} tin nhân viên, {ghi_so(wa)} mới"
    except Exception as ex:                              # noqa: BLE001 — sổ WhatsApp hỏng không được giết lượt
        dong += f" · WhatsApp LỖI {str(ex)[:80]}"
    try:
        tin, loi_tin = quet_tin()
        dong += f" · tin gửi Pancake: {ghi_so(tin)} mới" + (f" LỖI {loi_tin}" if loi_tin else "")
    except Exception as ex:                              # noqa: BLE001
        dong += f" · tin gửi LỖI {str(ex)[:80]}"
    log(dong)
    try:
        xu_lenh(e, so)                                   # lệnh #doica / #off trong nhóm WhatsApp
    except Exception as ex:                              # noqa: BLE001
        log("xử lệnh LỖI", str(ex)[:120])
    if not loi:                                          # Pancake quét hỏng thì đừng báo vắng oan
        for kieu, ten, tu, den, lx in xet_vang(e, so):
            ok, err = gui_wa(tin_nhac(kieu, ten, tu, den), nhom_ca(e, lx))
            log(ICON_NHAC[kieu], ten, f"[{CA[lx]['nhan']}] →", "đã gửi" if ok else f"CHƯA GỬI ĐƯỢC ({err})")
    da = so.setdefault("ca_da_bao", {})
    for cuoi, loai, ngay in cac_ca_vua_het(time.time()):
        k = f"{ngay:%Y-%m-%d} {loai}"
        if k in da:
            continue
        lan = so.setdefault("ca_thu", {}).get(k, 0)
        if lan >= 5:
            continue
        if lan == 0:                                     # vét thêm lần xem còn sót trước khi chốt ca
            xem2, _, _ = quet(SO_GOI_NAP)
            log(f"vét trước báo ca: {ghi_so(xem2)} lượt mới")
        cho = []
        ok, err = gui_wa(bao_cao_ca_dep(loai, ngay, e, cho), nhom_ca(e, loai))   # mẫu mới, chủ shop duyệt 24/09 21:50
        so["ca_thu"][k] = lan + 1
        if ok:
            da[k] = time.time()
            for c in cho:
                so.setdefault("cho_chot", {})[f"{c['ngay']} {c['ca']} {chuan(c['ten'])}"] = c
        log(f"📋 {k}:", "đã gửi" if ok else f"CHƯA GỬI ĐƯỢC lần {lan + 1} ({err})")
    for x in [x for x in da if x < f"{datetime.now(VN) - timedelta(days=7):%Y-%m-%d}"]:
        da.pop(x)
    try:
        chot_muon(e, so)
    except Exception as ex:                              # noqa: BLE001
        log("chốt muộn LỖI", str(ex)[:120])
    ghi_json(F_SO, so)


def main():
    a = sys.argv[1:]
    os.makedirs(STATE, exist_ok=True)
    if not ({"--xem", "--nghi", "--thu"} & set(a)):      # lệnh chỉ đọc không cần khoá (timer đang chạy vẫn xem được)
        khoa = open(os.path.join(STATE, ".khoa"), "w")
        try:
            fcntl.flock(khoa, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("lượt trước chưa xong — bỏ lượt này")
            return
    e = env()
    if "--nap" in a:
        n = int(a[a.index("--nap") + 1]) if len(a) > a.index("--nap") + 1 and a[a.index("--nap") + 1].isdigit() else SO_GOI_NAP
        xem, chua_doc, loi = quet(n)
        log(f"nạp {n} lần hỏi: {len(xem)} lượt xem, {ghi_so(xem)} lượt mới vào sổ" + (f" · LỖI {loi}" if loi else ""))
        ca = ca_chua(time.time(), list(CA))              # nạp POS từ đầu ca đang chạy (tối đa 10 giờ), không có ca thì 3 giờ
        lui = int(min(600, max(60, (time.time() - ca[2]) / 60 + 5))) if ca else 180
        pos, loi_pos, thieu = quet_pos(lui)
        log(f"POS {lui} phút: {len(pos)} lượt, {ghi_so(pos)} mới" + (f", {thieu} chưa rõ tên" if thieu else "") + (f" · LỖI {loi_pos}" if loi_pos else ""))
        wa, la = quet_wa(e, lui)
        log(f"WhatsApp nhóm {lui} phút: {len(wa)} tin nhân viên, {ghi_so(wa)} mới, {la} tin người ngoài danh sách")
    elif "--xem" in a:
        loai = next((("ngay" if x == "sang" else x) for x in a if x in CA or x == "sang"), None)   # ngay|toi|dem
        ngay = next((x for x in a if "/" in x), None)
        if ngay:
            d, m = (int(x) for x in ngay.split("/"))
            ngay = datetime(datetime.now(VN).year, m, d).date()
        hien = ca_chua(time.time(), list(CA)) or ("ngay", datetime.now(VN).date())
        loai = loai or hien[0]
        ngay = ngay or (hien[1] if loai == hien[0] else datetime.now(VN).date())
        print(bao_cao_ca_dep(loai, ngay, e))
    elif "--nghi" in a:
        so = doc_json(F_SO, {})
        kq = xet_vang(e, json.loads(json.dumps(so)))     # bản sao: không ghi sổ báo
        print("đang mở đợt vắng:", {k: (v.get("ten"), vn(v["tu"])) for k, v in (so.get("nghi") or {}).items()} or "không")
        for kieu, ten, tu, den, lx in kq:
            print(f"[{CA[lx]['nhan']}]", tin_nhac(kieu, ten, tu, den))
        if not kq:
            print("Lượt này không có tin vắng/quay lại nào.")
    elif "--thu" in a:                                   # --thu [ngay|toi|dem …] — mặc định mọi ca bật
        hong = 0
        for lx in [x for x in a if x in CA] or ca_bat(e):
            lich = "; ".join(f"{ten} {l if isinstance(l, str) else 'luân phiên ca 1/ca 2'}"
                             for ten, (c, l) in LICH.items() if c == lx)
            ok, err = gui_wa(f"🔔 Thử báo hoạt động {CA[lx]['nhan']} — nhóm này nhận: ⏸ vắng · ▶️ hoạt động lại · "
                             f"📋 báo cáo hết ca. Lịch theo dõi: {lich}.", nhom_ca(e, lx))
            print(CA[lx]["nhan"], "→", "đã gửi" if ok else f"CHƯA GỬI ĐƯỢC: {err}")
            hong += not ok
        sys.exit(1 if hong else 0)
    else:
        luot()


if __name__ == "__main__":
    main()

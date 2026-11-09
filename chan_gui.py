#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CỔNG CHẶN TIN RA — cửa DUY NHẤT mọi câu AI soạn phải qua trước khi tới khách.

Vì sao có file này (rút từ dự án Talpha, đã chạy thật 13.010 tin / 247 đơn):
mọi luật hành vi hiện nay của AI Sale đều nằm trong PROMPT. Prompt là lời khuyên, không
phải hàng rào — model quên một lần là khách nhận tin sai, và thứ hỏng ở đây không phải
tiền token mà là ĐƠN HÀNG và PAGE. Đo thật bên Talpha trên 779 tin page gửi:

  · 13,7% tin gửi ra KHÔNG có chữ nào (ảnh trơ / "...")
  · nhãn giá tiếng Việt "Combo 2 cái" bị in thẳng cho khách Ả Rập
  · một luồng tự động gửi tin DOẠ khách kèm ký tự Unicode ẩn để né bộ lọc trùng của Meta
    — một khách report là mất page, mất luôn traffic quảng cáo
  · khách HUỶ ĐƠN + BLOCK PAGE vì bot báo gấp đôi giá (tự nhân giá gói)

AI Sale của mình có RỦI RO CAO HƠN ở đúng chỗ đó: prompt viết 100% tiếng Việt, khách nói
Ả Rập / Taglish / Trung / Nhật; và bảng giá ba tầng (giá neo / giá chào / giá thực) có sẵn
ba con số to nhỏ khác nhau trong cùng một kịch bản — đúng loại dữ liệu làm model tính nhầm.

THUẦN LUẬT: không gọi model, không gọi mạng, chạy dưới 1ms. KHÔNG tự sửa tin —
chỉ trả phán quyết, người gọi quyết định soạn lại hay im.

    from chan_gui import kiem
    pq = kiem(tin, mkey="usa", kb_page=kb, gia=gia, tin_truoc=..., msgs=msgs)
    if pq.ket == "chan":     -> KHÔNG gửi, treo cho sale, ghi chú pq.ghi_chu()
    if pq.ket == "viet_lai": -> xin model viết lại 1 lần, lần 2 vẫn hỏng thì treo
    if pq.ket == "qua":      -> gửi

Lệnh:
  python3 chan_gui.py tu_kiem                 # 30 ca kiểm dựng sẵn — phải xanh hết
  python3 chan_gui.py thu <thị trường> <page> # soi kịch bản page: bộ giá + số được phép nói
"""

import json
import os
import re
import sys
import unicodedata
from datetime import date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════════════════════
# Mức phán quyết
# ══════════════════════════════════════════════════════════════════════════════
#   "chan"     — tuyệt đối không gửi. Sai ở đây làm mất đơn / mất page / sai tiền.
#   "viet_lai" — tin không sai sự thật, chỉ viết dở. Xin model viết lại ĐÚNG MỘT LẦN.
#   "nhac"     — VẪN GỬI, chỉ ghi sổ để đếm. Dành cho lỗi văn phong mà chính kịch bản của
#                shop cũng mắc — chặn ở đây là chặn oan, nhưng không đếm thì không sửa được.
#   "qua"      — sạch.
NANG, NHE, NHAC = "chan", "viet_lai", "nhac"

# CÂU CẢN KHÁCH MUA — chủ shop 14/09 tối, ca Lucy JJ (Madam Mystic USA): khách "You mean bibili ako iyang Golden
# Buddha?" → AI "Hindi po basta bili lang…" (đọc ra "Không/Đừng vội mua"). *"bạn rep như này chết tôi"*. Khách hỏi
# "vậy là phải mua à" thì đáp CÓ; không bao giờ mở đầu bằng phủ định chuyện mua.
CAN_MUA = re.compile(
    r"\bhindi\s+(?:po\s+)?(?:basta|kailangan(?:g)?|sapilitan)\s+(?:na\s+|ang\s+)?(?:bili|bumili|magbili|pagbili)"
    r"|\bhuwag\s+(?:po\s+|kayo\s+|mo\s+)?(?:magmadali(?:ng)?\s+(?:sa\s+)?(?:pagbili|bumili)|bumili)"
    r"|\bdon'?t\s+(?:rush|hurry)\s+(?:to\s+|into\s+)?(?:buy|order|purchas)|\bno\s+need\s+to\s+(?:buy|order|purchase)"
    r"|\byou\s+don'?t\s+(?:have|need)\s+to\s+(?:buy|order|purchase)|\bit'?s\s+not\s+(?:just\s+)?(?:about\s+)?(?:buying|selling)"
    r"|\bnot\s+just\s+(?:a\s+)?(?:purchase|buying)|đừng\s+vội\s+mua|không\s+cần\s+(?:phải\s+)?mua"
    r"|لا\s+تستعجل\w*\s+(?:في\s+)?(?:ال)?شراء|لا\s+داعي\s+(?:لل|ل)?شراء", re.I | re.U)


VIEC_KHI_CHAN = {
    "phui_quang_cao": "Khách nghi quảng cáo nói quá: nói công dụng CÓ trong kịch bản + kết quả khách thấy được, "
                      "rồi COD (nhận hàng kiểm rồi mới trả tiền). TUYỆT ĐỐI không đính chính/phủ nhận quảng cáo.",
    "bia_cua_hang": "Đừng khẳng định kho / cửa hàng / xuất xứ ngoài kịch bản page.",
    "bia_tien": "Con số tiền AI viết KHÔNG có trong bảng giá page — báo đúng bảng giá.",
    "duoi_gia_san": "Câu đó chào dưới giá sàn của page — báo đúng bảng giá.",
    "bao_gia_lai": "Khách vừa từ chối mà đã biết giá — níu (hỏi lý do + lý lẽ), đừng đọc lại bảng giá.",
    "bia_khan_hiem": "Kịch bản page không có hạn chót / khan hiếm / doạ mất suất cho người khác — đừng hứa.",
    "bia_thanh_toan": "Thị trường này chỉ COD tiền mặt — không thẻ, không chuyển khoản.",
    "doa_khach": "Câu mang tính doạ khách — một lần report là mất page.",
    "lo_noi_bo": "Câu để lộ chuyện nội bộ (bot / kịch bản / tra địa chỉ).",
    "bia_ma_don": "AI không có mã đơn thật — đừng đọc mã cho khách.",
    "can_mua": "Đừng cản khách mua; khách hỏi 'phải mua à?' thì đáp CÓ + giá trị sản phẩm.",
    "nhan_vo_da_mua": "POS không có đơn của khách — hỏi lại khách đặt ở page nào, tên + SĐT lúc đặt.",
    "bia_xem_anh": "Khách chưa gửi ảnh — nhắc khách gửi ảnh trước.",
    "hen_qua_han": "Ngày khách hẹn quá hạn giữ đơn — xin khách chọn ngày trong hạn.",
    "bao_han_som": "Khách chưa hẹn ngày quá hạn — đừng báo hạn giữ đơn trước.",
    "lot_tieng_viet": "Câu lọt tiếng Việt (hướng dẫn nội bộ) — viết lại đúng tiếng khách.",
    "khong_chot": "Câu chốt sớm giữa kịch bản tư vấn — đi đúng bước kịch bản.",
    "lap_sdt": "Câu lặp lại số điện thoại — bỏ.",
    "qua_dai": "Câu quá dài — viết 1-2 câu.",
    "ky_tu_an": "Câu có ký tự Unicode vô hình (dấu hiệu né bộ lọc Meta).",
}


class PhanQuyet:
    def __init__(self, tin):
        self.tin = tin
        self.loi = []          # [(mức, mã, mô tả)]

    def them(self, muc, ma, mo_ta):
        self.loi.append((muc, ma, mo_ta))

    @property
    def ket(self):
        if any(m == NANG for m, _, _ in self.loi):
            return "chan"
        if any(m == NHE for m, _, _ in self.loi):
            return "viet_lai"
        if self.loi:
            return "nhac"
        return "qua"

    @property
    def ma_loi(self):
        return [ma for _, ma, _ in self.loi]

    def ghi_chu(self):
        """Ghi chú nội bộ cho sale: MÃ LỖI ngắn + câu AI định gửi (chủ shop 12/09).

        Cùng khuôn với ghi chú gửi hỏng — một dòng đầu ngắn, xuống dòng là câu, để sale liếc
        là thấy. Mô tả dài của từng mã ("khẳng định về cửa hàng/địa điểm/xuất xứ … mà kịch bản
        page KHÔNG nói") đẩy câu khuất xuống dưới ô ghi chú mà sale đọc xong cũng không dùng;
        nó vẫn còn nguyên trong log lượt chạy và sổ việc (cột `chan`, `ma`).

        "ĐỪNG GỬI" phải nằm ngay đầu: câu này bị chặn vì SAI (bịa cửa hàng, sai giá…), sale mà
        chép gửi tay thì cổng chặn thành công cốc.
        """
        if not self.loi:
            return ""
        # KHÔNG CHÉP BẢN NHÁP VÀO GHI CHÚ NỮA (16/09, ca Tara Singh — Minty Fresh Smile KSA).
        # Bản 12/09 để "ĐỪNG GỬI" ngay đầu rồi in nguyên câu bị chặn cho sale xem. Đo thực tế:
        # sale vẫn chép gửi tay — 14/09 ca Yangrose (nhan_lap, đã bỏ ghi chú riêng cho mã đó),
        # 16/09 tài khoản "Từ Trang" chép đúng hai câu bị chặn (phui_quang_cao lúc 10:32,
        # bia_cua_hang lúc 10:38) gửi thẳng cho khách → khách đọc đúng câu đính chính quảng cáo
        # mà cổng vừa chặn, rồi trả lời "a new tooth won't grow back… I am wary".
        # Câu bị chặn là câu SAI, không phải bản nháp để sửa — ghi chú chỉ nói LÝ DO + VIỆC CẦN LÀM.
        # Câu đầy đủ vẫn còn trong log lượt chạy và sổ việc (cột `tin` khi không bị chặn / `ma`).
        viec = " · ".join(dict.fromkeys(VIEC_KHI_CHAN.get(m, "") for m in self.ma_loi if VIEC_KHI_CHAN.get(m)))
        return (f"AI SALE: cổng chặn ({', '.join(self.ma_loi)}) — AI KHÔNG gửi gì, sale trả lời khách giúp.\n"
                + (viec or "Câu AI định gửi SAI luật nên đã bỏ; đừng đi tìm chép lại."))

    def __repr__(self):
        return f"<{self.ket} {self.ma_loi}>"


# ══════════════════════════════════════════════════════════════════════════════
# Tiện ích
# ══════════════════════════════════════════════════════════════════════════════

_CHU_TOAN = re.compile("[\U0001D400-\U0001D7FF]")


def bo_chu_toan(t):
    """Chữ in đậm/nghiêng kiểu Unicode toán học → chữ thường: "𝐁𝐎𝐗 - 𝟖𝟗 𝐒𝐀𝐑" → "BOX - 89 SAR".

    Ca Noel B Mendoza 14/09 (Wellora Wellness Saudi): Botcake báo giá bằng chữ số in đậm, tien_trong
    không đọc ra → luật "không nhắc giá" tưởng page chưa báo giá, mức bán của page = []. Đo kịch bản
    12 nước: 6 page mất giá vì kiểu chữ này. Chỉ đổi dải U+1D400–1D7FF (thuần kiểu chữ), không đụng gì khác.
    """
    return _CHU_TOAN.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), str(t or ""))


def _chuan(s):
    return re.sub(r"[^\w\s]", " ", bo_chu_toan(s).lower(), flags=re.UNICODE)


def _giong_nhau(a, b):
    """Jaccard trên 3-gram ký tự. Bắt được cả tin sửa nhẹ vài chữ rồi gửi lại."""
    A, B = re.sub(r"\s+", " ", _chuan(a)).strip(), re.sub(r"\s+", " ", _chuan(b)).strip()
    if not A or not B:
        return 0.0
    if A == B:
        return 1.0
    g = lambda s: {s[i:i + 3] for i in range(len(s) - 2)}
    ga, gb = g(A), g(B)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 1 — tin rỗng / chỉ ký hiệu
# ══════════════════════════════════════════════════════════════════════════════
# Talpha đo: 2/3 trong 905 lần gửi ảnh là ảnh trơ hoặc chỉ kèm ba dấu chấm. Khách hỏi giá,
# nhận về mấy tấm ảnh và một dấu "…" — mất đơn mà không ai biết vì sổ vẫn ghi "đã trả lời".

def _rong(t):
    """Không có CHỮ nào (chữ cái hoặc chữ số) = coi như tin rỗng.

    Soi theo "có chữ không", KHÔNG theo "toàn ký hiệu": emoji hiện đại kèm ký tự chọn kiểu
    hiển thị (U+FE0F, category Mn) nên đếm kiểu cũ thì "❤️🥰" lọt qua như một tin bình thường.
    """
    for ch in str(t or ""):
        if unicodedata.category(ch)[0] in "LN":
            return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 2 — LỌT TIẾNG VIỆT  (lỗi nặng nhất, và hệ mình rủi ro hơn Talpha)
# ══════════════════════════════════════════════════════════════════════════════
# luat_model.md, kịch bản mẫu nội bộ, ghi chú cho sale, nhãn gói giá — tất cả tiếng Việt.
# Model chỉ cần trượt một nhịp là khách Kuwait nhận một câu tiếng Việt.
#
# ⚠️ KHÔNG được bắt bằng "có dấu tiếng Việt": Romania dùng ă â î ș ț, Tây Ban Nha dùng
# á é í ó ú ñ — bắt kiểu đó là chặn oan cả hai thị trường đó. Nên:
#   · TỪ CHỨC NĂNG tiếng Việt (là, của, nhé, khách hàng…) — không ngôn ngữ nào khác có
#   · KÝ TỰ RIÊNG của tiếng Việt (đ ơ ư ế ệ ộ ồ ầ ữ ị ụ ỹ…) — Romania/TBN không có
#   · DANH TỪ HÀNG HOÁ có dấu (cái, chiếc, hộp, combo…) — chỗ lọt nhiều nhất, hai bộ trên mù
# Cần ≥2 điểm mới kết luận, để một tên riêng lạ không làm chặn oan.

VN_TU = re.compile(
    r"\b(là|của|và|cho|với|được|nhé|nha|ạ|dạ|vâng|nhân\s*viên|khách\s*hàng|đơn\s*hàng"
    r"|giao\s*hàng|cảm\s*ơn|vui\s*lòng|chúng\s*tôi|chúng\s*em|anh\s*chị|sẽ|đã|không"
    r"|hàng|tiền|địa\s*chỉ|số\s*điện\s*thoại|bạn|mình|bên\s*em|quý\s*khách)\b", re.I | re.U)
# Ký tự CHỈ tiếng Việt mới có (loại hết ă â á é í ó ú vì Romania/Tây Ban Nha dùng chung).
VN_KY_TU = re.compile(r"[đĐơƠưƯ]|[ếềệểễắằặẳẵốồộổỗớờợởỡứừựửữịỉĩụủũỳỵỷỹẹẻẽạảãấầậẩẫ]", re.U)
VN_DANH_TU = re.compile(
    r"\b(cái|chiếc|tặng|hộp|tuýp|lọ|chai|gói|miếng|đôi|thùng|bộ|sản\s*phẩm|khuyến\s*mãi"
    r"|miễn\s*phí|số\s*lượng|màu\s*sắc|kích\s*cỡ|đặt\s*hàng|thanh\s*toán|giảm\s*giá"
    r"|vòng\s*tay|dây\s*chuyền|răng\s*giả|sđt)\b", re.I | re.U)


# ── NGÔN NGỮ CỦA TIN — để buộc AI trả lời đúng tiếng khách (chủ shop chốt 2026-09-10) ──
# Nhận diện bằng luật, KHÔNG đoán bừa: Ả Rập / Hindi / Bengali / Tamil… theo BẢNG CHỮ (không thể
# nhầm), Tagalog theo từ chức năng, còn lại chữ Latin coi là Anh. Tin quá ngắn hoặc không có
# dấu hiệu -> None (không phán).
#
# Ca 12/09 (Dineshbhai, Flat Jewelry KSA in Dubai): khách nhắn "My language Hindi". Bộ cũ thấy
# chữ "hindi" trong danh sách từ MẠNH Tagalog ("hindi" = "không") -> phán khách nói Tagalog ->
# bắt model soạn lại bằng Tagalog -> model chịu -> gửi luôn bản tiếng Anh "I'll continue in
# English". Sai hai tầng: (1) câu KHÁCH XIN NÓI TIẾNG X không phải mẫu tiếng để đo, phải hiểu
# là YÊU CẦU; (2) bộ cũ chỉ biết 3 thứ tiếng nên Hindi/Urdu/Bengali… đều vô hình.
# Từ MẠNH: một từ là đủ kết luận Tagalog (không trùng tiếng Anh).
TL_MANH = re.compile(
    r"\b(po|opo|magkano|salamat|kayo|kayong|ninyo|nyo|ako|ikaw|kami|namin|natin"
    r"|hindi|wala|meron|mayroon|gusto|pwede|puwede|paano|kailan|bakit|ilan|ilang"
    r"|talaga|maganda|mabuti|totoo|sige|naman|yung|iyong|sana|kasi|nakaka\w+|maka\w{3,}"
    r"|pampa\w{3,}|ipin|bibili|order\s+na\s+po)\b", re.I)
# Từ YẾU: hay trùng chữ tiếng Anh/viết tắt -> cần ít nhất 2 từ khác nhau.
TL_YEU = re.compile(r"\b(ang|ng|mga|ba|lang|din|rin|mo|ko|tayo|niyo|dito|diyan|kung|para|saan|siya|at)\b", re.I)
AR_KY_TU = re.compile(r"[\u0600-\u06FF]")
# Chữ RIÊNG của Urdu (ٹ ڈ ڑ ں ھ ہ ے ۓ) — tiếng Ả Rập không dùng. Ca Mohammad Ejaz 24/09: khách viết Urdu, bộ đo trả "ar",
# AI trả lời tiếng Ả Rập mà không bị bắt soạn lại.
UR_KY_TU = re.compile(r"[\u0679\u0688\u0691\u06BA\u06BE\u06C1\u06D2\u06D3]")
# Bảng chữ -> mã tiếng. Chữ Ả Rập dùng chung cho Ả Rập / Urdu / Ba Tư / Pashto nên chỉ kết luận
# được "cùng hệ chữ" (xem he_chu); Devanagari dùng chung Hindi / Marathi / Nepali, cũng vậy.
BANG_CHU = [
    ("hi", re.compile(r"[\u0900-\u097F]")),     # Devanagari (Hindi/Marathi/Nepali)
    ("bn", re.compile(r"[\u0980-\u09FF]")),     # Bengali
    ("pa", re.compile(r"[\u0A00-\u0A7F]")),     # Gurmukhi (Punjabi)
    ("gu", re.compile(r"[\u0A80-\u0AFF]")),     # Gujarati
    ("ta", re.compile(r"[\u0B80-\u0BFF]")),     # Tamil
    ("te", re.compile(r"[\u0C00-\u0C7F]")),     # Telugu
    ("kn", re.compile(r"[\u0C80-\u0CFF]")),     # Kannada
    ("ml", re.compile(r"[\u0D00-\u0D7F]")),     # Malayalam
    ("si", re.compile(r"[\u0D80-\u0DFF]")),     # Sinhala
    ("th", re.compile(r"[\u0E00-\u0E7F]")),     # Thái
    ("am", re.compile(r"[\u1200-\u137F]")),     # Amharic
    ("ru", re.compile(r"[\u0400-\u04FF]")),     # Cyrillic
    ("zh", re.compile(r"[\u4E00-\u9FFF]")),     # Hán
]
# Tên tiếng (khách gõ bằng chữ Latin) -> mã. Dùng cho câu "My language Hindi", "Urdu please"…
TEN_TIENG = {
    "hi": ("Hindi", "tiếng Hindi (chữ Devanagari)"),
    "ur": ("Urdu", "tiếng Urdu (chữ Ả Rập kiểu Urdu, KHÔNG phải tiếng Ả Rập)"),
    "ar": ("Arabic", "tiếng Ả Rập"),
    "tl": ("Tagalog", "TAGALOG/Taglish"),
    "en": ("English", "TIẾNG ANH"),
    "hi_la": ("Hinglish", "tiếng Anh THẬT ĐƠN GIẢN cho người gõ Hindi/Urdu bằng chữ Latin"),
    "bn": ("Bengali", "tiếng Bengali (chữ Bengal)"),
    "ml": ("Malayalam", "tiếng Malayalam"),
    "ta": ("Tamil", "tiếng Tamil"),
    "te": ("Telugu", "tiếng Telugu"),
    "kn": ("Kannada", "tiếng Kannada"),
    "mr": ("Marathi", "tiếng Marathi (chữ Devanagari)"),
    "gu": ("Gujarati", "tiếng Gujarati"),
    "pa": ("Punjabi", "tiếng Punjabi"),
    "ne": ("Nepali", "tiếng Nepali (chữ Devanagari)"),
    "si": ("Sinhala", "tiếng Sinhala"),
    "fa": ("Persian", "tiếng Ba Tư (Farsi)"),
    "ps": ("Pashto", "tiếng Pashto"),
    "ru": ("Russian", "tiếng Nga"),
    "fr": ("French", "tiếng Pháp"),
    "es": ("Spanish", "tiếng Tây Ban Nha"),
    "pt": ("Portuguese", "tiếng Bồ Đào Nha"),
    "de": ("German", "tiếng Đức"),
    "tr": ("Turkish", "tiếng Thổ Nhĩ Kỳ"),
    "id": ("Indonesian", "tiếng Indonesia"),
    "ms": ("Malay", "tiếng Mã Lai"),
    "zh": ("Chinese", "tiếng Trung"),
    "th": ("Thai", "tiếng Thái"),
    "am": ("Amharic", "tiếng Amharic"),
    "sw": ("Swahili", "tiếng Swahili"),
    "so": ("Somali", "tiếng Somali"),
    "vi": ("Vietnamese", "tiếng Việt"),
}
_TEN_MA = {
    "english": "en", "inglish": "en", "angrezi": "en",
    "hindi": "hi", "hindustani": "hi", "hindhi": "hi",
    "urdu": "ur", "urdo": "ur",
    "arabic": "ar", "arabi": "ar", "arab": "ar", "arbi": "ar",
    "tagalog": "tl", "filipino": "tl", "pilipino": "tl", "taglish": "tl", "bisaya": "tl", "cebuano": "tl",
    "bengali": "bn", "bangla": "bn", "bangali": "bn", "bangladeshi": "bn",
    "malayalam": "ml", "tamil": "ta", "telugu": "te", "kannada": "kn", "marathi": "mr",
    "gujarati": "gu", "gujrati": "gu", "punjabi": "pa", "panjabi": "pa", "nepali": "ne",
    "sinhala": "si", "sinhalese": "si", "sinhali": "si",
    "persian": "fa", "farsi": "fa", "pashto": "ps", "pushto": "ps",
    "russian": "ru", "french": "fr", "francais": "fr", "spanish": "es", "espanol": "es",
    "portuguese": "pt", "german": "de", "deutsch": "de", "turkish": "tr", "turkce": "tr",
    "indonesian": "id", "indonesia": "id", "bahasa": "id", "malay": "ms", "melayu": "ms",
    "chinese": "zh", "mandarin": "zh", "thai": "th", "amharic": "am", "swahili": "sw",
    "somali": "so", "vietnamese": "vi",
}
_TEN_RE = "|".join(sorted(_TEN_MA, key=len, reverse=True))
# Câu khách XIN nói tiếng X (gõ bằng chữ Latin). Mỗi mẫu bắt được tên tiếng ở nhóm 'ten'.
_YEU_CAU = [
    re.compile(r"\b(?:my|our|mera|meri|hamari|apna)\s+language\s*(?:is|:|-)?\s*(?:only\s+)?(?P<ten>" + _TEN_RE + r")\b", re.I),
    re.compile(r"\b(?:language|lang)\s*(?:is|:|-)?\s*(?P<ten>" + _TEN_RE + r")\b", re.I),
    re.compile(r"\b(?P<ten>" + _TEN_RE + r")\s+(?:language|lang|please|pls|plz|plss|only|me|mein|main|me\s+bolo|me\s+baat)\b", re.I),
    re.compile(r"\b(?:speak|talk|write|reply|answer|chat|type|text|message|explain|tell|say|bolo|baat)\s+(?:to\s+me\s+|with\s+me\s+|me\s+)?(?:in|with|by)?\s*(?P<ten>" + _TEN_RE + r")\b", re.I),
    re.compile(r"\b(?:in|use)\s+(?P<ten>" + _TEN_RE + r")\s*(?:please|pls|plz|only|\?|$)", re.I),
    re.compile(r"\b(?:i|we)\s+(?:only\s+|just\s+)?(?:know|speak|understand|read|write|use)\s+(?:only\s+)?(?P<ten>" + _TEN_RE + r")\b", re.I),
    re.compile(r"\b(?:can|could|do)\s+(?:you|u)\s+(?:speak|talk|understand|know|write|reply|chat)\s+(?:in\s+|with\s+)?(?P<ten>" + _TEN_RE + r")\b", re.I),
    re.compile(r"\b(?:do\s+you\s+have|any|is\s+there)\s+(?:a\s+|an\s+)?(?:someone|anyone|person|staff|agent)?\s*(?:who\s+)?(?:speak\w*\s+)?(?P<ten>" + _TEN_RE + r")\b", re.I),
]
# Khách chỉ nói KHÔNG biết tiếng Anh mà chưa nói muốn tiếng gì -> "?" (chỗ gọi phải hỏi khách).
_ANH = r"(?:english|inglish|inglis|englis|engles|ingles|angrezi|(?:bahasa\s+)?inggris)"
_KHONG_ANH = re.compile(
    r"\b(?:no|not|don'?t|dont|do\s+not|cannot|can'?t|cant|little|poor|weak|bad|tidak|tak|gak|nggak|ngga|"
    r"kurang|belum)\s+"
    r"(?:know\s+|understand\s+|speak\s+|good\s+|in\s+|much\s+|bisa\s+|tahu\s+|ngerti\s+|paham\s+|"
    r"mengerti\s+|pandai\s+)?" + _ANH + r"\b"
    r"|\b" + _ANH + r"\s+(?:no|nahi|nahin|nhi|not\s+good|little|weak|poor|tidak|gak|nggak)\b", re.I)
# "My indonesia no inglis", "I'm Indonesian, no English" — khách nêu tiếng/nước mình NGAY cạnh lời không biết
# tiếng Anh → đó là lời xin tiếng (ca Cucu Ella 15/09). Chỉ tên tiếng, không lấy tên nước khác.
_TEN_KEM_KHONG_ANH = re.compile(
    r"\b(?:my|me|i\s*'?\s*a?m|im|i|saya|aku)\s+(?:is\s+|from\s+|an?\s+)?(?P<ten>" + _TEN_RE + r")\b[\s,.;:/-]{0,3}"
    r"(?:(?:and\s+|but\s+)?(?:no|not|don'?t|dont|cannot|can'?t|cant|tidak|gak|nggak)\b)", re.I)
# "No English only Urdu" — tên tiếng đứng SAU lời không biết tiếng Anh
_CHI_TEN = re.compile(r"\b(?:only|just|use|pakai|pake)\s+(?P<ten>" + _TEN_RE + r")\b", re.I)


# "HINDI" TAGALOG ≠ TIẾNG HINDI (chủ shop 14/09 tối, ca Lucy JJ — Madam Mystic Fengshui Expert USA): khách "Hindi
# lang muna po .at maraming salamat" (= chưa đâu, cảm ơn) khớp mẫu "<tên> lang" → AI viết nguyên tin bằng chữ
# Devanagari, khách đáp "Hindi ko naintidihan ang mga letra ito" (không đọc được chữ này) — mất trắng một lượt níu.
# "hindi" = "không" trong Tagalog: câu có từ Tagalog đi kèm, không có chữ "language", không phải Hinglish → bỏ qua.
_TL_KEM_HINDI = re.compile(
    r"\b(?:po|opo|muna|lang|ko|ako|akong|kami|ang|ng|mga|sa|salamat|naman|kayo|ito|dito|wala|pero|kasi)\b", re.I)


# TÊN TIẾNG GÕ BẰNG CHỮ BẢN ĐỊA — khách xin tiếng của mình thì hay gõ luôn bằng chữ của tiếng đó.
_BAN_DIA = {
    "ar": ("عربي", "عربى", "عربيه", "عربية", "العربية", "العربيه", "بالعربي", "بالعربى", "بالعربية", "عرب"),
    "en": ("انجليزي", "إنجليزي", "انجليزية", "إنجليزية", "الانجليزية", "بالانجليزي", "انكليزي",
           "इंग्लिश", "अंग्रेजी", "ইংরেজি"),
    "ur": ("اردو", "أردو"),
    "hi": ("हिंदी", "हिन्दी"),
    "bn": ("বাংলা",),
    "fa": ("فارسی", "فارسي"),
    "ps": ("پښتو", "پشتو"),
    "ta": ("தமிழ்",),
    "ml": ("മലയാളം",),
    "te": ("తెలుగు",),
    "kn": ("ಕನ್ನಡ",),
    "si": ("සිංහල",),
    "ne": ("नेपाली",),
    "th": ("ไทย",),
    "zh": ("中文", "国语", "國語"),
}
# Tên tiếng gõ chữ Latin KHÔNG lấy khi đứng trơ: "hindi" = "không" trong Tagalog (ca Lucy JJ 14/09);
# "arab"/"filipino"/"bangladeshi"/"indonesia" là tên nước/quốc tịch — khách đang khai mình là ai.
_TEN_TRON_BO = {"hindi", "hindhi", "hindustani", "arab", "filipino", "pilipino", "bangladeshi", "indonesia"}
_TU_PHU_TIENG = {"language", "lang", "please", "pls", "plz", "plss", "po", "only", "just", "speak", "talk",
                 "sir", "maam", "mam", "madam", "ok", "من", "فضلك", "لو", "سمحت", "بليز"}


def ten_tieng_tron(t):
    """Tin khách CHỈ gồm TÊN MỘT NGÔN NGỮ -> mã tiếng. None = không phải.

    Chủ shop 20/09, ca ابو منصور (Soothing Cooling Gel in Saudi): khách gõ đúng một chữ "عربي" rồi
    "عربيه"; tin 1 chữ nên vo_nghia coi là rỗng → AI đáp tiếng Tagalog rồi treo, sale rep tay.
    Một chữ tên tiếng là lời xin rõ ràng, không phải tin trơ.
    """
    import unicodedata
    s = re.sub(r"[\u200b-\u200f\u0640\u064b-\u0652]", "", unicodedata.normalize("NFC", str(t or "")))
    # Giữ DẤU KẾT HỢP (Mn): "हिंदी"/"বাংলা" mà cắt theo [^\w] thì vỡ thành hai ba mảnh, không khớp bảng nào.
    goi = "".join(c if (c.isalnum() or unicodedata.category(c).startswith("M")) else " "
                  for c in s).strip().lower()
    tu = [w for w in goi.split() if w]
    if not tu or len(tu) > 3:
        return None
    chinh = [w for w in tu if w not in _TU_PHU_TIENG]
    if len(chinh) != 1:
        return None
    w = chinh[0]
    for ma, ds in _BAN_DIA.items():
        if w in ds:
            return ma
    if w in _TEN_MA and w not in _TEN_TRON_BO:
        return _TEN_MA[w]
    return None


def tieng_yeu_cau(t):
    """Khách XIN nói tiếng gì? -> mã tiếng ('hi', 'ur', 'ar'…), '?' = khách chỉ nói không biết
    tiếng Anh, None = câu này không phải yêu cầu về ngôn ngữ."""
    t = str(t or "").strip()
    if not t:
        return None
    ma = ten_tieng_tron(t)               # tin chỉ có tên tiếng (20/09, ca ابو منصور)
    if ma:
        return ma
    ma = None
    for rx in _YEU_CAU:
        m = rx.search(t)
        if m and m.group("ten").lower() == "hindi" and not re.search(r"\blanguage\b", t, re.I) \
                and _TL_KEM_HINDI.search(t) and not la_hinglish(t):
            continue                  # "Hindi lang muna po" — Tagalog (ca Lucy JJ 14/09)
        if m:
            ma = _TEN_MA.get(m.group("ten").lower())
            if ma == "en" and _KHONG_ANH.search(t):
                ma = None             # "No English only Urdu" — "English only" không phải xin tiếng Anh
                continue
            if ma:
                break
    if ma:
        return ma
    if _KHONG_ANH.search(t):
        for rx in (_TEN_KEM_KHONG_ANH, _CHI_TEN):
            m = rx.search(t)
            if m and _TEN_MA.get(m.group("ten").lower()) not in (None, "en"):
                return _TEN_MA[m.group("ten").lower()]
        if la_indo(t):                # "saya tidak bisa bahasa inggris" — câu gõ bằng chính tiếng Indo
            return "id"
        return "?"
    return None


def he_chu(ma):
    """Gom các tiếng cùng bảng chữ: đo bằng luật chỉ phân biệt được tới mức này."""
    # "hi_la" (Hindi/Urdu gõ chữ Latin) được đáp bằng tiếng Anh đơn giản → cùng nhóm "en" khi so.
    # "ur" TÁCH khỏi "ar" (24/09) — đo được bằng chữ riêng của Urdu, đáp tiếng Ả Rập cho khách Urdu là sai tiếng.
    return {"fa": "ar", "ps": "ar", "mr": "hi", "ne": "hi", "hi_la": "en", "ms": "id"}.get(ma, ma)


# HINDI/URDU GÕ CHỮ LATIN (Hinglish) — chủ shop 2026-09-14, ca Sallam Khan (Golden Buddha Blessings):
# khách "Hamare picture do", "Subah kabhi dobara", gửi voice 3 lần → bộ đo coi là "en", AI chép
# nguyên bước kịch bản TAGALOG "Tiningnan ko ang palad mo…" (miễn soạn lại vì là mẫu của shop).
# Từ MẠNH: một từ là đủ; từ YẾU: cần ≥2 từ khác nhau (tránh "hai" = hi, "kal", "do"…).
HI_LA_MANH = re.compile(
    r"\b(mujhe|mujhko|hamare|hamara|humare|humara|hamko|humko|kabhi|dobara|chahiye|chahie|bhejo|bhejiye"
    r"|kitna|kitne|kitni|nahi|nahin|nhi|kyun|kyon|kaise|kaisa|aapka|apka|aapko|apko|tumhara|kijiye|dijiye"
    r"|karein|karenge|samajh|samjha|batao|bataiye|bolo|boliye|haan\s+ji|theek\s+hai|thik\s+hai|kya\s+hai)\b", re.I)
HI_LA_YEU = re.compile(
    r"\b(hai|hain|aap|ap|mera|meri|mere|abhi|accha|acha|achha|subah|shaam|kal|bhai|karo|wala|wali|paisa"
    r"|paise|kya|ho|hoga|raha|rahi|lo|lena|dena|par|ke|ki|ka|se|ko|main|mai|hum|tum)\b", re.I)


# TIẾNG INDONESIA / MÃ LAI (chủ shop 2026-09-14, ca Rizki Nya Hany — Kreain Nature PH in Saudi):
# khách "aku pesan 1 gratis 1" bị đo là "en" → AI soạn tiếng Anh, luật đúng tiếng không bắt.
# Đo trên 18.654 tin khách + tin AI cũ (mọi nước): 99 tin trúng, đều là tiếng Indo thật (trước đó
# bị coi là "en", tin AI tiếng Indo còn bị coi là "tl" vì "kami"). Ca nhầm duy nhất: tin tiếng Anh
# có TÊN GÓI "Beli 1 Gratis 1" của page → bỏ cụm tên gói trước khi đo.
# Cần ≥1 từ MẠNH và tổng ≥2 từ khác nhau. "bisa"/"sama"/"alamat" trùng Tagalog → chỉ là từ YẾU.
ID_MANH = re.compile(
    r"\b(saya|aku|kakak|pesan|pesen|berapa|brp|harganya|tidak|gak|nggak|ngga|enggak|sudah|udah|belum|blm"
    r"|kirim|bayar|terima\s+kasih|makasih|trimakasih|beli|gimana|bagaimana|kapan|ongkir|barangnya|apakah"
    r"|dengan|untuk|bisakah|boleh|mahu|sekarang|dimana|bagus|mbak|dapat|alamatnya|jual|punya)\b", re.I)
ID_YEU = re.compile(r"\b(ini|itu|yang|dan|ada|mau|kak|min|ya|juga|gratis|satu|dua|tiga|nak|tak|lagi|sama"
                    r"|apa|bisa|alamat|harga|barang)\b", re.I)
_TEN_GOI_ID = re.compile(r"\bbeli\s*\d+\s*gratis\s*\d+", re.I)


def la_indo(t):
    t = _TEN_GOI_ID.sub(" ", str(t or ""))
    manh = {m.lower() for m in ID_MANH.findall(t)}
    return bool(manh) and len(manh) + len({m.lower() for m in ID_YEU.findall(t)}) >= 2


def la_hinglish(t):
    t = str(t or "")
    return bool(HI_LA_MANH.search(t)) or len({m.lower() for m in HI_LA_YEU.findall(t)}) >= 3


def ngon_ngu(t):
    """Mã tiếng ('ar' | 'tl' | 'en' | 'hi' | 'bn' | …) hoặc None. None = không đủ căn cứ, chỗ gọi đừng phán.
    Câu khách XIN nói tiếng X không phải mẫu tiếng để đo -> None (dùng tieng_yeu_cau)."""
    t = str(t or "").strip()
    if len(re.findall(r"\w", t, re.U)) < 4:
        return None
    if tieng_yeu_cau(t):
        return None
    if len(AR_KY_TU.findall(t)) >= 3:
        return "ur" if len(UR_KY_TU.findall(t)) >= 2 else "ar"
    for ma, rx in BANG_CHU:
        if len(rx.findall(t)) >= 3:
            return ma
    if la_indo(t):                          # trước Tagalog: tin Indo hay có "kami"/"sana"
        return "id"
    if TL_MANH.search(t) or len(set(m.lower() for m in TL_YEU.findall(t))) >= 2:
        return "tl"
    if la_hinglish(t):
        return "hi_la"
    if re.search(r"[A-Za-z]{3}", t):
        return "en"
    return None


def _diem_tieng_viet(t):
    d = 0
    if VN_TU.search(t):
        d += 2                                   # từ chức năng: bằng chứng mạnh nhất
    if VN_DANH_TU.search(t):
        d += 2
    n = len(VN_KY_TU.findall(t))
    if n >= 3:
        d += 2
    elif n >= 1:
        d += 1
    return d


# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 3 — BỊA TIỀN  (Talpha CORE §6 — luật đắt nhất trong cả bộ)
# ══════════════════════════════════════════════════════════════════════════════
# Bên Talpha: khách nói "2 sets", model tính 2 × SET 2 = 298 → khách huỷ đơn + block page.
# Bên mình còn dễ sai hơn vì mỗi page có SẴN ba con số khác nhau (neo $350 / chào $199 /
# thực $129) và các mẫu combo — model rất dễ cộng, nhân, hoặc lấy nhầm tầng.
#
# LUẬT: mọi con số tiền AI nói ra phải là con số CÓ THẬT trong kịch bản của chính page đó,
# hoặc đúng bằng giá sàn đã tính. Không có trong bảng = BỊA, chặn.
# (Đây là ràng buộc mạnh hơn prompt: prompt bảo "đừng bịa", cổng này khiến bịa không lọt ra.)

TIEN_TE = {"uae": "AED", "saudi": "SAR", "kuwait": "KWD", "qatar": "QAR", "oman": "OMR",
           "bahrain": "BHD", "taiwan": "NT$", "japan": "JPY", "usa": "USD",
           "spain": "EUR", "romania": "RON", "bulgaria": "EUR"}

# Ký hiệu/mã tiền tệ đứng TRƯỚC hoặc SAU con số. Chỉ những con số dính tiền tệ mới bị soi —
# nếu không sẽ bắt nhầm SĐT, mã bưu chính, "2-5 ngày", số nhà.
_MA_TIEN = (r"\$|€|¥|£|₱|AED|SAR|KWD|QAR|OMR|BHD|USD|TWD|NT\$|JPY|EUR|RON|BGN|лв"
            # 25/09 (ca Ne Ne · Meco Jewelry Kuwait "also 10 KD maam"): mã viết tắt vùng Vịnh — đứng riêng, không dính chữ khác
            r"|(?<![a-z])KD(?![a-z])|(?<![a-z])BD(?![a-z])|(?<![a-z])SR(?![a-z])|(?<![a-z])QR(?![a-z0-9])|(?<![a-z])Dhs?(?![a-z])"
            r"|درهم|ريال|دينار|دولار|元|円|ペソ|pesos?|dirhams?|riyals?|dinars?|dollars?")
# Ký hiệu tiền tệ RIÊNG của từng thị trường — dùng khi cần bắt ĐÚNG tiền của nước đó.
MA_RIENG = {
    "uae": r"AED|(?<![a-z])Dhs?(?![a-z])|د\.إ|درهم|dirhams?", "saudi": r"SAR|(?<![a-z])SR(?![a-z])|ر\.س|ريال|riyals?",
    "kuwait": r"KWD|(?<![a-z])KD(?![a-z])|د\.ك|دينار|dinars?", "qatar": r"QAR|(?<![a-z])QR(?![a-z0-9])|ر\.ق|ريال|riyals?",
    "oman": r"OMR|ر\.ع|ريال|riyals?", "bahrain": r"BHD|(?<![a-z])BD(?![a-z])|د\.ب|دينار|dinars?",
    "taiwan": r"NT\$|TWD|元", "japan": r"JPY|¥|円",
    "usa": r"\$|USD|dollars?", "spain": r"€|EUR|euros?",
    "romania": r"RON|lei", "bulgaria": r"€|EUR|BGN|лв|euros?",
}
# 09/11/2026 (bản clone, shop VIỆT NAM): tiền Việt viết "99k", "149.000đ", "199.000 VND", "99 nghìn".
# Đơn vị đọc khớp nhau: "99k" → 99 · "99.000đ" → _so("99.000") = 99 — cùng tính bằng NGHÌN đồng.
# Chữ "k" CHỈ bật cho tiến trình chạy thị trường Việt Nam (service đặt AI_TIEN_VND=1): ở page trang sức
# nước ngoài "18k" là tuổi vàng — bật chung thì "18k gold" thành giá 18 (đo 09/11: tự gắn page theo tiền
# tệ gắn sai 6 page trang sức vào Việt Nam vì đúng chữ "k" này). Không bật thì 12 nước cũ y như trước.
MA_VND = r"(?<![a-z])k(?![a-zà-ỹđ])|vnđ|vnd|(?<![a-zà-ỹđ])đ(?![a-zà-ỹđ])|đồng|nghìn|ngàn"
MA_RIENG["vietnam"] = MA_VND
if os.environ.get("AI_TIEN_VND") == "1":
    _MA_TIEN = _MA_TIEN + "|" + MA_VND


def so_tien_cua(t, mkey):
    """Con số mang ĐÚNG tiền tệ của thị trường này.

    Vì sao cần: bài chào hàng hay nhắc tiền nước khác. Đo thật 2026-09-08 — mẫu cảnh báo lừa
    đảo của page Saudi viết "Our staff reported 3159 pesos / Not 159 pesos"; đọc kiểu chung
    chung thì 3159 thành một MỨC GIÁ page đang bán, và model được phép chào con số đó.
    """
    ma = MA_RIENG.get(mkey or "")
    if not ma:
        return tien_trong(t)
    rg = re.compile(rf"(?:(?:{ma})\s*([\d][\d,.]{{0,9}})|([\d][\d,.]{{0,9}})\s*(?:{ma}))",
                    re.I | re.U)
    ra = []
    for a, b in rg.findall(bo_chu_toan(t)):
        v = _so(a or b)
        if v is not None:
            ra.append(v)
    return ra


SO_TIEN = re.compile(
    rf"(?:(?:{_MA_TIEN})\s*([\d][\d,.]{{0,9}})|([\d][\d,.]{{0,9}})\s*(?:{_MA_TIEN}))",
    re.I | re.U)


def _so(x):
    """'1,299.00' -> 1299 · '199' -> 199 · '79,5' -> 79.5 (phẩy thập phân kiểu Âu).

    Ca thật 10/09 (Edd Mac, Leg Glow Lab UAE): AI viết "79,5 AED each", bản cũ bỏ dấu phẩy
    thành 795 → cổng chặn "bịa tiền 795". Dấu phẩy theo sau 1-2 chữ số là THẬP PHÂN; theo sau
    đúng 3 chữ số (và không còn gì) mới là dấu nghìn.
    """
    s = str(x).strip().rstrip(".")
    if re.fullmatch(r"\d+,\d{1,2}", s):
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return int(v) if v == int(v) else round(v, 2)


def tien_trong(t):
    """Mọi con số TIỀN trong một đoạn chữ (chỉ số có ký hiệu/mã tiền tệ đi kèm)."""
    ra = []
    for a, b in SO_TIEN.findall(bo_chu_toan(t)):
        v = _so(a or b)
        if v is not None:
            ra.append(v)
    return ra


# ── ĐƠN VỊ BÁN CỦA PAGE — quyết định cách tính giá số lượng lạ ───────────────
# Chủ shop chốt 2026-09-09, hai trường hợp:
#
#   TH1 · page bán theo SỐ LƯỢNG (1 pcs, 2 pcs…)
#         Khách nói con số là SỐ PCS. Muốn n pcs -> giá 2 PCS chia 2, nhân n.
#
#   TH2 · page bán theo SET / COMBO (set1, set2, combo1, combo2…)
#         "set 2" nghĩa là SET SỐ 2, KHÔNG phải 2 set. "combo 2" là COMBO SỐ 2, không phải
#         2 × combo 1. Khách muốn n set/combo -> giá SET2/COMBO2 chia 2, nhân n.
#
# Neo luôn là GÓI SỐ 2 (2 pcs, set 2, combo 2) chia đôi — không bao giờ lấy gói số 1, vì gói
# 1 luôn đắt hơn tính trên mỗi đơn vị.

R_SET_N = re.compile(r"\b(SET|COMBO)\s*(\d{1,2})\b", re.I)
# Cho phép TÊN SẢN PHẨM chen giữa số và đơn vị: "2 Pixiu Bracelets – $299" (Lucky Aura Gems US)
# — không có chỗ này thì máy bỏ qua dòng bảng giá thật và chỉ đọc được câu quảng cáo.
R_PCS_N = re.compile(
    r"\b(\d{1,2})\s*(?:x\s*)?(?:[A-Za-z]+\s+){0,2}"
    r"(?:pcs?|pieces?|cái|chiếc|bottles?|box(?:es)?|jars?|tubes?|packs?|bars?|units?|items?"
    r"|sachets?|pairs?|sets?|bote|piraso"
    r"|bracelets?|rings?|necklaces?|earrings?|pendants?|chains?|anklets?)\b", re.I | re.U)


def don_vi_ban(kb_page):
    """Page này bán theo đơn vị gì, và giá của 'gói số 2' là bao nhiêu.

    Trả {'kieu': 'set'|'combo'|'pcs'|'buy', 'gia_2': giá gói số 2, 'moi_don_vi': giá 1 đơn vị}
    hoặc None nếu không xác định được — lúc đó KHÔNG được tự tính, phải treo cho sale.
    """
    dong_gia = []                       # [(dòng bảng giá, giá của dòng đó)]
    for m in (kb_page or {}).get("mau") or []:
        for d in "\n".join(m.get("tin") or []).split("\n"):
            t = set(tien_trong(d))
            # DÒNG BẢNG GIÁ CHỈ CÓ ĐÚNG MỘT MỨC (như bang_sl_gia / _gia_dong_combo). Lấy min
            # của dòng nhiều số là lấy nhầm: "2 Sets - 69 AED + 10 AED shipping" ra 10 (tiền
            # ship -> 3 set = 15 AED), "1pc $199, 2pcs $299, nag-add lang $100" ra 100.
            # Đo 20/09 trên 328 page: 5 page đang sai vì chỗ này, sửa xong mất 0 page đúng.
            if len(t) == 1:
                dong_gia.append((d, t.pop()))
    if not dong_gia:
        return None

    # TH2a — nhãn SET n / COMBO n
    theo = {}
    for d, g in dong_gia:
        x = R_SET_N.search(d)
        if x:
            theo.setdefault(int(x.group(2)), g)
    if theo.get(2):
        k = R_SET_N.search([d for d, _ in dong_gia if R_SET_N.search(d)][0]).group(1).lower()
        return {"kieu": k, "gia_2": theo[2], "moi_don_vi": theo[2] / 2.0}

    # TH2b — BUY n GET n (hai số bằng nhau) = n set
    theo = {}
    for d, g in dong_gia:
        x = R_BUY_N_GET_N.search(d)
        if x and x.group(1) == x.group(2):
            theo.setdefault(int(x.group(1)), g)
    if theo.get(2):
        return {"kieu": "buy", "gia_2": theo[2], "moi_don_vi": theo[2] / 2.0}

    # TH1 — bán theo số lượng: dòng nào ghi "2 pcs" thì đó là giá 2 pcs
    theo = {}
    for d, g in dong_gia:
        if km_trong(d):        # dòng "Buy 1 Get 1 — 2 bottles 109" là GÓI, không phải giá 2 đơn vị
            continue
        for x in R_PCS_N.finditer(d):
            theo.setdefault(int(x.group(1)), g)
    if theo.get(2):
        return {"kieu": "pcs", "gia_2": theo[2], "moi_don_vi": theo[2] / 2.0}
    return None


# Chủ shop 22/09: ",9 nhé" rồi "chỉ kuwait" — luật đuôi ,9 CHỈ cho shop Kuwait. Mở thêm nước thì thêm vào đây.
DUOI_9_THI_TRUONG = ("kuwait",)


def gia_duoi_9(dv, mkey=None):
    """Page KUWAIT bán giá đuôi ,9 (gói số 2 = 21,9 KWD) → giá ngoài bảng giữ ,9. Nước khác (kể cả page giá thập phân
    ,9), page Kuwait giá số nguyên (16 KWD), hay không biết nước (mkey None) → False: làm tròn xuống như cũ."""
    g = (dv or {}).get("gia_2")
    return (mkey in DUOI_9_THI_TRUONG and g is not None and g != int(g)
            and round((g - int(g)) * 10) == 9)


def gia_ngoai_bang(dv, n, mkey=None):
    """Giá n đơn vị KHÔNG có trong bảng = (gói số 2 ÷ 2) × n, làm tròn XUỐNG (chủ shop 09/09: 253,5 → 253).

    Page giá đuôi ,9 thì giữ đuôi ,9 (chủ shop 22/09 ",9 nhé", ca Fe Cavan Cavan · Kuwait Amoura Gold): 21,9 ÷ 2 × 4 = 43,8
    → 43,9 — đúng giá sale đang báo và lịch sử đơn POS của page (3 bộ 32,9 · 4 bộ 43,9). MỌI chỗ tính thang giá ngoài
    bảng (cổng so_duoc_phep, ai_sale.bo_gia → san_ngoai_bang → dòng GIÁ SỐ LƯỢNG NGOÀI BẢNG trong prompt) phải đi qua đây."""
    g = int(dv["moi_don_vi"] * n)
    return round(g + 0.9, 1) if gia_duoi_9(dv, mkey) else g


# ── GÓI KIỂU "BUY n GET n" — điều kiện để được nhân giá theo set ─────────────
# Chủ shop chốt 2026-09-09: luật "chia giá gói 2 set rồi nhân" CHỈ áp cho page viết gói kiểu
# BUY n GET n. Page viết kiểu khác thì khách hỏi số lạ là TREO cho sale.
# Lý do, đo trên 181 page: có ba kiểu khác mà chia đôi là ra SAI —
#   "BUY 2 GET 1 FREE"      (Đài Loan)  số 2 là số mua, không phải số set
#   "SET 2: Buy 6 pcs"      (Bahrain)   SET 2 là 6 cái, không phải 2 set
#   "Combo 1: Buy 1 Take 1" (Kuwait)    kiểu Take, không phải Get
R_BUY_N_GET_N = re.compile(r"\bBUY\s*(\d{1,2})\s*GET\s*(\d{1,2})\b", re.I)


def goi_buy_n_get_n(kb_page):
    """{số set: giá} cho page viết gói kiểu BUY n GET n (hai số BẰNG NHAU).

    Chỉ nhận khi hai số bằng nhau: "BUY 2 GET 2" là 2 set, còn "BUY 2 GET 1" là mua 2 tặng 1
    — con số 2 ở đó không phải số set, chia đôi là sai tiền.
    """
    ra = {}
    for m in (kb_page or {}).get("mau") or []:
        for dong in "\n".join(m.get("tin") or []).split("\n"):
            g = R_BUY_N_GET_N.search(dong)
            if not g or g.group(1) != g.group(2):
                continue
            tien = tien_trong(dong)
            if tien:
                ra[int(g.group(1))] = min(tien)
    return ra


R_SO_LUONG = re.compile(
    r"(?:total\s+)?(\d{1,2})\s*(?:x\s*)?(?:pcs?|pieces?|bottles?|sets?|boxes?|products?|items?"
    r"|tubes?|jars?|packs?|bars?|units?|combo)\b", re.I)


def don_gia_suy_ra(kb_page):
    """Đơn giá suy từ gói: cùng một dòng kịch bản có 'q chai/pcs/set...' và giá P → cho P/q.

    Chủ shop chốt 2026-09-10 (ca Edd Mac): AI viết "2 bottles for 159 AED — that's only 79,5
    AED each" là câu chuẩn, cổng không được chặn. Chỉ nhận q ghi NGAY trong dòng có giá đó
    (2..10), nên "5.3g" hay số lẻ không lọt.
    """
    ra = set()
    for m in (kb_page or {}).get("mau") or []:
        for d in "\n".join(m.get("tin") or []).split("\n"):
            gia = tien_trong(d)
            if not gia:
                continue
            for q in {int(x) for x in R_SO_LUONG.findall(d)}:
                if 2 <= q <= 10:
                    for P in gia:
                        v = P / q
                        ra.add(int(v) if v == int(v) else round(v, 2))
    return ra


def so_duoc_phep(kb_page, gia=None):
    """Tập con số tiền AI ĐƯỢC PHÉP nói với page này.

    = mọi con số tiền xuất hiện trong bất kỳ mẫu nào của kịch bản page
      + giá sàn tính được (mục 4 — con số này KHÔNG có trong kịch bản, do tool tính ra)
      + đơn giá suy từ gói (P/q, xem don_gia_suy_ra).
    """
    ok = set()
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            ok.update(tien_trong(tin))
            # Kịch bản hay viết trần "199 → 129" không kèm ký hiệu ở con số thứ hai.
            ok.update(int(x.replace(",", "")) for x in re.findall(r"\b(\d[\d,]{1,6})\b", tin))
    ok.update(don_gia_suy_ra(kb_page))
    if gia:
        # ── GIÁ NHIỀU SET, ngoài bảng (chủ shop chốt 2026-09-09) ────────────
        # "Lấy tiền 2 set chia 2 rồi nhân với số set khách muốn."
        #   BUY 1 GET 1 = 99 · BUY 2 GET 2 = 169  ->  mỗi set 169/2 = 84,5
        #   3 set = 84,5 × 3 = 253,5  ->  khách được báo 253
        # CHỈ áp cho page viết gói kiểu BUY n GET n và CÓ gói 2 set. Page khác không mở phép
        # nhân — khách hỏi số lạ ở đó thì luật bảo treo cho sale, không tự tính.
        # LÀM TRÒN XUỐNG (chủ shop chốt 2026-09-09): 84,5 × 3 = 253,5 -> báo khách 253.
        # Chỉ cho ĐÚNG con số làm tròn xuống — mở thêm bản làm tròn lên là mở thêm một con số
        # hợp lệ không cần thiết, mà mỗi con số hợp lệ thừa là một chỗ AI báo sai mà cổng
        # không bắt được.
        dv = don_vi_ban(kb_page)
        if dv:
            for n in range(3, 11):
                ok.add(gia_ngoai_bang(dv, n, gia.get("thi_truong")))     # làm tròn xuống; Kuwait giá ,9 giữ ,9 (22/09)
        # nên phải nằm trong tập cho qua. Cả bảng sàn-theo-combo.
        for k in ("gia_thuc", "gia_san", "san_thap_nhat"):
            if gia.get(k):
                ok.add(int(gia[k]))
        ok.update(int(x) for x in gia.get("gia_chao") or [])
        ok.update(int(x) for x in gia.get("gia_ban") or [])
        ok.update(int(x) for x in (gia.get("san_theo_gia") or {}).values())
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 3b — GÓI / SỐ LƯỢNG KHÔNG KHỚP BẢNG GIÁ
# ══════════════════════════════════════════════════════════════════════════════
# Ca Shaallyn Nabayat (Leg Glow Lab UAE, 19/09/2026): bảng giá "1 bottle → 109 AED / 2 bottles → 159 AED",
# khách "1bottle I mean", AI gửi "Buy 1 Get 1 — 2 bottles, 109 AED"; khách hỏi lại "109for 2bottles po" thì
# AI còn "Yes po", rồi "Reserved na po ang Buy 1 Get 1 (2 bottles)" — ba tin liền. 109 là giá THẬT nên luật 3
# (bịa tiền) không thấy gì: sai ở chỗ GHÉP (giá 1 chai gắn cho 2 chai) và BỊA TÊN chương trình tặng kèm page
# không có. Chủ shop: *"chương trình mua 1 mà, làm gì có tặng 1 đâu"*.
# Đo 3.662 tin AI đã soạn (11 nước, tới 19/09), tính cả tin Botcake/sale/khách trong hội thoại: 13 tin dính,
# cả 13 là lỗi thật (Leg Glow ×3, Lean Body KSA ×4, Japan Herb Lab KSA ×4, Slim & Glow Saudi ×1, Veloura ×1),
# 0 chặn oan. Bẫy: Mint Breeze viết "𝐁𝐮𝐲 𝟏 𝐆𝐞𝐭 𝟏" bằng chữ in đậm Unicode — không bo_chu_toan là chặn oan 37 tin.
_SO_CHU_KM = {"one": 1, "two": 2, "three": 3}
_N_KM = r"(\d{1,2}|one|two|three)"
# Chữ "Buy" không bắt buộc (vá 2, ca Slimora Body 19/09: AI viết trần "2 Get 2 — 4 shapewear total, 99 AED").
R_KM_TANG = re.compile(
    r"\b(?:(?:buy|bili|mua)\s*)?" + _N_KM + r"\s*,?\s*(?:and\s+)?(?:get|take|tặng)\s*" + _N_KM + r"\b"
    r"|\bb\s?(\d)\s?[gt]\s?(\d)\b"
    r"|(?<![\d.,])(\d)\s*\+\s*(\d)(?![\d.,%])"
    r"|\b(bogo)\b", re.I | re.U)
# Số lượng đứng TRƯỚC danh từ đơn vị ("2 bottles", "4 pcs"). "SET 2"/"combo 2" là số hiệu gói — không tính.
R_SL_GOI = re.compile(
    r"\b(\d{1,2})\s*(?:x\s*)?(?:pcs?|pieces?|bottles?|box(?:es)?|jars?|tubes?|packs?|bars?|units?|items?"
    r"|sachets?|pairs?|sets?|bracelets?|rings?|necklaces?|bote|piraso)\b", re.I | re.U)
_CAT_CAU = re.compile(r"(?<!\d)[.!?](?!\d)|\n|;")


def km_trong(t):
    """{(mua, tặng)} — chương trình 'mua n tặng m' nhắc trong câu ('Buy 1 Get 1', 'B1T1', '1+1', 'BOGO')."""
    ra = set()
    for m in R_KM_TANG.finditer(bo_chu_toan(str(t or ""))):
        g = [x for x in m.groups() if x]
        if g[0].lower() == "bogo":
            ra.add((1, 1))
        else:
            ra.add(tuple(int(_SO_CHU_KM.get(x.lower(), x)) for x in g[:2]))
    return ra


def _chu_page(kb_page, cau_page=None):
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            yield str(tin or "")
    for c in cau_page or ():
        yield str(c or "")


def bang_sl_gia(kb_page, cau_page=None):
    """{số lượng: {giá}} — dòng kịch bản / tin page mang ĐÚNG một số lượng và ĐÚNG một mức giá."""
    ra = {}
    for tin in _chu_page(kb_page, cau_page):
        for d in bo_chu_toan(tin).split("\n"):
            sl, g = {int(x) for x in R_SL_GOI.findall(d)}, set(tien_trong(d))
            if len(sl) == 1 and len(g) == 1:
                ra.setdefault(sl.pop(), set()).add(g.pop())
    return ra


def sai_gia_so_luong(t, kb_page, cau_page=None):
    """[(số lượng AI nói, giá AI gán, [giá đúng], [số lượng thật của giá đó])] — câu ghép lệch bảng.

    Chỉ xét câu có đúng MỘT số lượng + MỘT mức giá, và giá đó là giá của một số lượng KHÁC trong bảng.
    Câu liệt kê nhiều mức, đơn giá 'each', giá sàn (không nằm trong bảng) → bỏ qua.
    """
    bang = bang_sl_gia(kb_page, cau_page)
    ra = []
    for cau in _CAT_CAU.split(bo_chu_toan(str(t or ""))):
        sl, g = {int(x) for x in R_SL_GOI.findall(cau)}, set(tien_trong(cau))
        if len(sl) != 1 or len(g) != 1:
            continue
        n, P = sl.pop(), g.pop()
        if n in bang and P not in bang[n]:
            cua = sorted(k for k, v in bang.items() if P in v and k != n)
            if cua:
                ra.append((n, P, sorted(bang[n]), cua))
    return ra


def bang_goi_gia(kb_page, cau_page=None):
    """{(mua, tặng): {giá}} — dòng kịch bản / tin page mang ĐÚNG một gói mua-tặng và ĐÚNG một mức giá."""
    ra = {}
    for tin in _chu_page(kb_page, cau_page):
        for d in bo_chu_toan(tin).split("\n"):
            k, g = km_trong(d), set(tien_trong(d))
            if len(k) == 1 and len(g) == 1:
                ra.setdefault(k.pop(), set()).add(g.pop())
    return ra


def sai_gia_goi(t, kb_page, cau_page=None):
    """[(gói AI nói, giá AI gán, [giá đúng của gói đó], [gói thật của giá đó])] — so giá THEO GÓI.

    Vá 2 (ca ITx Shahab Guli, Slimora Body 19/09): kịch bản chỉ có "Buy 1 Get 1 FREE – 99 AED", AI viết "2 Get 2 — 4
    shapewear total, 99 AED". sai_gia_so_luong không thấy vì "shapewear" không phải đơn vị nó biết. Chỉ xét câu có đúng
    MỘT gói + MỘT mức giá mà giá đó là giá của gói KHÁC trong bảng (gói lạ không có trong bảng cũng tính).
    """
    bang = bang_goi_gia(kb_page, cau_page)
    ra = []
    for cau in _CAT_CAU.split(bo_chu_toan(str(t or ""))):
        k, g = km_trong(cau), set(tien_trong(cau))
        if len(k) != 1 or len(g) != 1:
            continue
        goi, P = k.pop(), g.pop()
        if P in bang.get(goi, set()):
            continue
        cua = sorted(x for x, v in bang.items() if P in v and x != goi)
        if cua:
            ra.append((goi, P, sorted(bang.get(goi, ())), cua))
    return ra


# ══════════════════════════════════════════════════════════════════════════════
# SỐ KHÁCH NÓI MƠ HỒ TRÊN PAGE CHỈ BÁN THEO GÓI MUA-TẶNG (chủ shop 2026-09-21)
# ══════════════════════════════════════════════════════════════════════════════
# Ca Ming Hui Sapeda · Veloura Lip Beauty Saudi: bảng chỉ có "Mua 1 tặng 2 — 3 thỏi son 109 SAR"
# và "Mua 2 tặng 4 — 6 thỏi son 159 SAR"; khách gõ "Only 2 ok" (chỉ muốn nhận 2 thỏi) → AI đọc
# con số thành SỐ HIỆU GÓI rồi chốt luôn "Buy 2 Get 4 Free — 6 lipsticks, 159". Chủ shop: *"trường
# hợp only 2 là khách chỉ muốn nhận 2 cái thì bạn nên hỏi lại khách ý bạn muốn mua 1 tặng 2 hay
# mua 2 tặng 4 nhé"*. Sai gói ở đây là sai TIỀN (109 ↔ 159) và sai số hàng giao.
#
# LUẬT: số khách nói mà KHÔNG kèm chữ buy/set/combo là SỐ SẢN PHẨM KHÁCH MUỐN NHẬN. Không gói nào
# cho đúng ngần ấy sản phẩm → MƠ HỒ → hỏi lại một câu, cấm tự chọn gói.
#
# CỐ Ý KHÔNG BẮT (đo 118.792 tin khách thật trong state/*/so_chi_phi.jsonl; 1.016 tin lọt cửa
# "câu ngắn có số + page bán theo ≥2 gói, không có bảng theo đơn vị"):
#   · số = số MUA của gói nhỏ nhất, thường là "1" (626 tin) — luật 19/09 đã chốt hiểu là gói nhỏ
#     nhất; đó cũng là gói RẺ NHẤT nên không có rủi ro tiền;
#   · có gói cho ĐÚNG ngần ấy sản phẩm (304) — "2 pcs" trên page BUY 1 GET 1 chính là gói đó;
#   · số lớn hơn tổng của mọi gói (28) — việc của luật SỐ LƯỢNG NGOÀI BẢNG, không phải chọn gói;
#   · khách tự gọi tên gói ("buy 2 get 2", "1+1"), nói rõ "buy n", hay nhắc free/tặng (8).
# Còn lại 50 lượt (20 tin khác nhau) mới là mơ hồ: "Only 2 ok", "Magkano 3 pcs", "3 for how much?",
# "Tatlo sana d ba 299$ ang tallo", "5sr 2pcs sa kamsa2 Po eh", "999 for 3"…
_DV_SL_KH = (r"(?:pcs?|pieces?|sets?|boxes?|box|bottles?|batle|botel|tubes?|jars?|packs?|orders?|oder"
             r"|units?|items?|bote|piraso|kahon|sachets?|pairs?|bars?|cans?)")
R_SL_DV_KH = re.compile(r"(?<![\w.,/-])(\d{1,2})\s*" + _DV_SL_KH + r"\b", re.I)
R_SL_TRON_KH = re.compile(r"(?<![\w.,/-])(\d{1,2})(?![\w.,/-])")
R_SL_CHI_KH = re.compile(r"\b(?:only|just)\s*(\d{1,2})\b|\b(\d{1,2})\s*(?:lang|lng)\b", re.I)
R_SL_CHU_KH = re.compile(r"(?<![\wأ-ي])(isa|dalawa|tatlo|apat|lima|anim|وحده|واحده|واحد|اثنين|ثنتين)"
                         r"(?![\wأ-ي])", re.I | re.U)
_SL_CHU_KH = {"isa": 1, "dalawa": 2, "tatlo": 3, "apat": 4, "lima": 5, "anim": 6,
              "وحده": 1, "واحده": 1, "واحد": 1, "اثنين": 2, "ثنتين": 2}
# "2" kiểu nhắn tắt = "to" ("how 2 order", "want 2 buy") — 35 lượt trong mẫu đo, phải loại.
R_HAI_LA_TO = re.compile(r"\b(?:how|want|wanna|need|like|try|going|gusto|paano)\s*2\b"
                         r"|\b2\s*(?:order|buy|pay|use|know|send|ask|make|apply|claim|get\s+it)\b", re.I)
# Số trong câu ĐỊA CHỈ / GIỜ / NGÀY / ĐỢI LƯƠNG không phải số lượng.
R_SO_KHONG_SL = re.compile(
    r"\b(?:block|street|st\.|exit|villa|house|bldg|building|flat|apt|road|area|zone|mall|center|centre"
    r"|am|pm|oras|month|buwan|week|linggo|date|day|days|araw|years?|taon|tanggal|tgl|tnggl"
    r"|salary|sahod|sweldo|gajian|payday|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b"
    r"|january|february|march|april|august|september|october|november|december", re.I)
R_SO_DAI_KH = re.compile(r"\d{6,}")
# Khách nói SỐ MUA của gói: "buy 2", "اطلب اثنين" — không kèm đơn vị ngay sau.
R_SO_MUA_KH = re.compile(r"\b(?:buy|bumili|bili|mua|اطلب|ابغى|اريد|أريد)\s*(\d{1,2})(?!\s*"
                         + _DV_SL_KH + r")\b", re.I | re.U)
R_TANG_KH = re.compile(r"\b(?:free|libre|gift)\b|مجان", re.I | re.U)


def _bang_don_vi(kb_page, cau_page=None):
    """{số lượng: {giá}} như bang_sl_gia nhưng BỎ dòng có chương trình mua-tặng.

    Dòng "Buy 1 Get 1 — 2 pcs 99 AED" là dòng GÓI, không phải bảng bán lẻ theo đơn vị. Tính nhầm nó
    là bảng đơn vị thì goi_mo_ho tưởng page bán lẻ theo cái và tắt lịm ở đúng những page hay bị hỏi
    (ClearVision "Magkano 3 pcs", Minty, Skin Renew). Cùng cách don_vi_ban() lọc từ 20/09.
    """
    ra = {}
    for tin in _chu_page(kb_page, cau_page):
        for d in bo_chu_toan(tin).split("\n"):
            if km_trong(d):
                continue
            sl, g = {int(x) for x in R_SL_GOI.findall(d)}, set(tien_trong(d))
            if len(sl) == 1 and len(g) == 1:
                ra.setdefault(sl.pop(), set()).add(g.pop())
    return ra


def so_khach_muon(t):
    """Số SẢN PHẨM khách nói trong câu NGẮN (≤ 8 từ), hoặc None.

    Câu dài, câu có SĐT / địa chỉ / giờ / ngày / lương, và câu có ≥2 con số khác nhau đều trả None —
    thà bỏ sót còn hơn hỏi lại oan một câu khách vừa trả lời (ca Menskie 20/09).
    """
    t = bo_chu_toan(str(t or "")).strip()
    if not t or len(t.split()) > 8:
        return None
    if R_SO_DAI_KH.search(t) or R_SO_KHONG_SL.search(t) or R_HAI_LA_TO.search(t):
        return None
    # ≥2 từ VIẾT HOA không đứng đầu câu = tên riêng / địa chỉ ("Lord Stephen Al waleed DSO 3
    # Receptionist security"), không phải lời chọn số lượng. "po", "I" lẻ vẫn lọt qua.
    if sum(1 for w in t.split()[1:] if w[:1].isupper() and w[1:2].islower()) >= 2:
        return None
    so = {int(x) for x in R_SL_DV_KH.findall(t)}
    so |= {int(g) for m in R_SL_CHI_KH.finditer(t) for g in m.groups() if g}
    if not so and not tien_trong(t):      # câu có giá: con số là TIỀN, không phải số lượng
        so = {int(x) for x in R_SL_TRON_KH.findall(t)}
        if any(x > 10 for x in so):       # năm, SĐT rút gọn, giá lẻ…
            return None
    so = {x for x in so if 1 <= x <= 10}
    if not so:
        m = R_SL_CHU_KH.search(t)
        if m:
            so = {_SL_CHU_KH[m.group(1).lower()]}
    return so.pop() if len(so) == 1 else None


R_KHONG_SL_GOI = re.compile(r"\b(?:\d*hrs?|hours?|mins?|minutes?|whats?\w*|wha?rs\w*|number)\b", re.I)


def goi_khach_noi(kb_page, cau_page, loi_khach):
    """Gói khớp con số khách nói trên page CHỈ bán theo gói → {"goi": (mua, tặng), "gia": {giá}, "so", "cach", "loi"} / None.

    MUA_N_TANG_N_2409 — chủ shop 24/09, ca Dilaila Dilaila (Healthy Figure PH in Kuwait, gói 2/4/6 hộp): khách "2 pc" → AI
    tự đọc thành Mua 2 tặng 2 (4 hộp 16 KWD); khách "3 packs" → AI hỏi lại 2 lần, sale tự lên Mua 3 tặng 3. Chủ shop chốt:
    page Mua N tặng N thì "3 packs" / "order 3" = Mua 3 tặng 3. Thứ tự đọc (khớp luật "SỐ TRƠN TRÊN PAGE BÁN THEO GÓI"):
      khách gọi tên gói ("2 get 2", "1+1") → None: model vốn hiểu đúng, còn khách DÁN tin quảng cáo cũng có tên gói (đo 24/09);
      "so_mua" — "buy 2" nói rõ số MUA;
      "tong"    — có ĐÚNG một gói cho n sản phẩm ("2 pc" trên page BUY 1 GET 1);
      "so_mua"  — page Mua N tặng N, n không khớp tổng gói nào mà khớp SỐ MUA ("3 packs" → Mua 3 tặng 3).
    """
    bang = bang_goi_gia(kb_page, cau_page)
    if len(bang) < 2 or _bang_don_vi(kb_page, cau_page):
        return None
    loi = str(loi_khach or "").strip()[:120]
    ra = lambda g, cach, n: {"goi": g, "gia": bang[g], "so": n, "cach": cach, "loi": loi}
    if km_trong(loi_khach):
        return None
    # CHON_GOI_2809 — log 28/09: "Ok now order 2+free 2", "اشترِ 2 واحصل على 2 مجانًا" bị ép thành Mua 1 tặng 1 (khách tự gọi gói
    # bằng chữ free mà km_trong không đọc được); "Aftr 1 to 2hrs liit siya", "2 whars app number" không phải số lượng.
    if R_KHONG_SL_GOI.search(loi):
        return None
    if R_TANG_KH.search(loi):        # có chữ free/مجان → con số ĐẦU là SỐ MUA ("Buy 2 get free", "2+free 2", "اشترِ 2 … مجانًا")
        d = re.search(r"\d{1,2}", bo_chu_toan(loi).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
        mua = [g for g in bang if d and g[0] == int(d.group())]
        return ra(mua[0], "so_mua", int(d.group())) if len(mua) == 1 else None
    n = so_khach_muon(loi_khach)
    if n is None:
        return None
    m = R_SO_MUA_KH.search(bo_chu_toan(str(loi_khach or "")))
    if m and int(m.group(1)) == n:
        mua = [g for g in bang if g[0] == n]
        if len(mua) == 1:
            return ra(mua[0], "so_mua", n)
    tong = [g for g in bang if g[0] + g[1] == n]
    if len(tong) == 1:
        return ra(tong[0], "tong", n)
    if not tong and all(a == b for a, b in bang):
        mua = [g for g in bang if g[0] == n]
        if len(mua) == 1:
            return ra(mua[0], "so_mua", n)
    return None


def goi_mo_ho(kb_page, cau_page, loi_khach):
    """{"so": n, "bang": {(mua, tặng): {giá}}, "loi": lời khách} khi số khách nói MƠ HỒ, không thì None.

    Mơ hồ = page CHỈ bán theo ≥2 gói mua-tặng (không có bảng giá theo đơn vị) và số khách nói không
    khớp gói nào theo cả hai cách đọc (xem khối chú thích ở trên).
    """
    bang = bang_goi_gia(kb_page, cau_page)
    if len(bang) < 2 or _bang_don_vi(kb_page, cau_page):
        return None
    n = so_khach_muon(loi_khach)
    if n is None or n < 2:
        return None
    tong = {a + b for a, b in bang}
    if n > max(tong) or n in tong:
        return None
    if n == min(bang, key=lambda g: g[0] + g[1])[0]:   # số MUA của gói nhỏ nhất
        return None
    if all(a == b for a, b in bang) and any(a == n for a, _ in bang):
        return None      # page Mua N tặng N: n = SỐ MUA của một gói → gói đó (MUA_N_TANG_N_2409, xem goi_khach_noi)
    if km_trong(loi_khach) or R_TANG_KH.search(str(loi_khach or "")):
        return None
    m = R_SO_MUA_KH.search(bo_chu_toan(str(loi_khach or "")))
    if m and int(m.group(1)) == n and any(a == n for a, _ in bang):
        return None
    return {"so": n, "bang": bang, "loi": str(loi_khach or "").strip()[:120]}


# ── GIỜ MỞ CỬA CỬA HÀNG MÀ KỊCH BẢN KHÔNG GHI (chủ shop 20/09, luat/34_cua_hang.md) ───────────
# Khách vùng Vịnh hay hỏi "anong oras po kayo bukas". Kịch bản 337 page không page nào ghi giờ, nên
# model hoặc BỊA ("bukas ang store namin tuwing 10am–10pm" — thử thật 20/09 trên ChunHo Golden
# Jewerly) hoặc nói toạc ra là mình không biết. Bịa nguy hơn: khách đi tới nơi đóng cửa là mất cả
# đơn lẫn uy tín. CHỈ tính câu vừa nói GIỜ vừa nói CỬA HÀNG — câu hẹn giờ GIAO HÀNG ("deliver
# 4pm-11pm", "the rider comes 9am") không đụng tới. Đo 6.525 tin AI đã gửi (so_viec, 8 nước): 2 câu
# có giờ + chữ cửa hàng, cả 2 là hẹn giao hàng → cổng này chưa từng cắt oan câu nào.
GIO_TRONG_CAU = re.compile(
    r"\b\d{1,2}\s*[:.]?\d{0,2}\s*(?:am|pm|a\.m|p\.m)\b|\b\d{1,2}\s*[-–—]\s*\d{1,2}\s*(?:am|pm)\b"
    r"|\b24\s*/\s*7\b|\b\d{1,2}\s*(?:صباحا|مساء)", re.I | re.U)
MO_CUA = re.compile(r"\b(?:open|opens|opening|bukas|nagbubukas|store|shop|branch|showroom)\b|تفتح|يفتح|دوام", re.I | re.U)
GIAO_TRONG_CAU = re.compile(
    r"\b(?:deliver\w*|delivery|rider|courier|ship\w*|padala|ihatid|dating|arrive|schedule)\b|توصيل|المندوب", re.I | re.U)


def _cau_gio_cua_hang(t):
    """Các câu trong tin đang KHẲNG ĐỊNH giờ mở cửa của cửa hàng."""
    return [c for c in re.split(r"(?<=[.!?])\s+|\n+", t or "")
            if GIO_TRONG_CAU.search(c) and MO_CUA.search(c) and not GIAO_TRONG_CAU.search(c)]


def gio_cua_hang_trong_kich_ban(kb_page):
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            s = str(tin or "")
            if GIO_TRONG_CAU.search(s) and MO_CUA.search(s) and not GIAO_TRONG_CAU.search(s):
                return True
    return False


def bia_gio_cua_hang(t, kb_page):
    """Tin có khẳng định giờ mở cửa mà kịch bản page không hề ghi giờ nào?"""
    return bool(_cau_gio_cua_hang(t)) and not gio_cua_hang_trong_kich_ban(kb_page)


def bo_cau_gio_cua_hang(t):
    """Bỏ trọn các câu nói giờ mở cửa, giữ nguyên phần còn lại."""
    bo = set(_cau_gio_cua_hang(t))
    giu = [c for c in re.split(r"(?<=[.!?])\s+|\n+", t or "") if c not in bo]
    return " ".join(x.strip() for x in giu if x.strip()).strip()


def bia_khuyen_mai(t, kb_page, cau_page=None, cau_khach=None):
    """Chương trình 'mua n tặng m' AI nhắc mà kịch bản, tin page lẫn lời khách (khách chép từ quảng cáo)
    đều không có."""
    ai = km_trong(t)
    if not ai:
        return set()
    co = set()
    for tin in _chu_page(kb_page, list(cau_page or ()) + list(cau_khach or ())):
        co |= km_trong(tin)
    return ai - co


def cau_trong_hoi_thoai(msgs):
    """(tin page, tin khách) cho luật 3b. Page = Botcake/sale/broadcast — KHÔNG tính tin AI và ghi chú cổng
    chặn: câu sai AI đã gửi không được tự hợp thức hoá chính nó (ca Shaallyn: tin 2, 3 lặp lại tin 1)."""
    pg, kh = [], []
    for m in msgs or []:
        t = m.get("text") or ""
        if m.get("boi") == "khach":
            kh.append(t)
        elif m.get("boi") in ("botcake", "nguoi", "hethong") and "AI SALE" not in t and "CỔNG CHẶN" not in t:
            pg.append(t)
    return pg, kh


# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 4 — BỊA KHAN HIẾM / KHUYẾN MÃI KHÔNG CÓ TRONG KỊCH BẢN
# ══════════════════════════════════════════════════════════════════════════════
# Câu "còn 2 suất cuối", "hôm nay là ngày cuối" là thứ model tự nghĩ ra rất dễ dàng vì nó
# học từ hàng triệu quảng cáo. Kịch bản không ghi = mình không có quyền hứa.
# Khẳng định về CỬA HÀNG / ĐỊA ĐIỂM / XUẤT XỨ — AI không biết shop có cửa hàng hay không.
# Ca Suraj Patra (Dubai Luxe Charm, 10/09): AI viết "We don't have a physical store — we're an
# online shop based in UAE" — kịch bản không hề nói. Nghe hợp lý, nhưng là bịa.
CUA_HANG = re.compile(
    r"\b(physical\s+store|physical\s+shop|showroom|our\s+(?:store|shop|branch|office|warehouse)\s+is"
    r"|we\s+(?:are|'re)\s+(?:located|based)|based\s+in\s+\w+|located\s+in\s+\w+|visit\s+our\s+(?:store|shop)"
    r"|no\s+(?:physical\s+)?store|don'?t\s+have\s+a\s+(?:physical\s+)?(?:store|shop)|online\s+shop\s+based"
    r"|walk[- ]in|pick[- ]?up\s+(?:at|from)|imported\s+from|made\s+in\s+\w+)\b", re.I)


# Kịch bản page CÓ ĐỊA CHỈ CỬA HÀNG THẬT — không phải "Store in a cool, dry place" hay "Thank you for visiting our
# store". Thêm 20/09: CUA_HANG ở trên chỉ nhận ra 14/223 page, trong khi 38 page có hẳn khối địa chỉ ("TMW Gold and
# Diamonds has 3 stores in Saudi Arabia: 🏣 Store 1: Al Olaya…", "This is our store address po") — AI chép đúng khối
# đó cho khách vẫn bị chặn là "bịa cửa hàng", khách không nhận được tin nào (47 lần trong log 09-20/09).
CUA_HANG_KB = re.compile(
    r"🏣|🏬"
    r"|\b(?:store|branch|showroom)\s*(?:no\.?\s*)?\d\s*[:：]"
    r"|\bour\s+(?:store|shop|branch|showroom)\s+(?:address|location)\b"
    r"|\b(?:has|have)\s+\d+\s+(?:stores?|branch(?:es)?|showrooms?)\b"
    r"|\b(?:stores?|branch(?:es)?|showrooms?)\s+(?:in|at)\s+[A-Z][\w']+\s*[:：]"
    r"|\bstore\s+pick\s*-?\s*up\b"
    r"|\b(?:visit|shop)\s+(?:and\s+shop\s+)?(?:directly\s+)?(?:at|in)\s+our\s+(?:stores?|shops?|branch(?:es)?)\b",
    re.I | re.U)


def _kich_ban_co_cua_hang(kb_page):
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            s = str(tin or "")
            if CUA_HANG.search(s) or CUA_HANG_KB.search(s):
                return True
    return False


def _kich_ban_co_khan_hiem(kb_page, rx=None):
    """Kịch bản page có câu khan hiếm / hạn chót nào không (so ý, không so chữ).

    `rx` (24/09): nhóm cần so — mặc định nhóm hạn chót / số lượng (KHAN_HIEM) như trước."""
    rx = rx or KHAN_HIEM
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            if rx.search(str(tin or "")):
                return True
    return False


KHAN_HIEM = re.compile(
    r"\b(last\s+\d+\s+(?:slots?|pieces?|stocks?|items?)|only\s+\d+\s+(?:left|remaining)"
    r"|huling\s+\w*\s*(?:araw|slot)|today\s+only|last\s+day|ends?\s+today|limited\s+stock"
    r"|hurry|mabilisan|ngayong\s+araw\s+lang|آخر\s+يوم|اخر\s+قطع"
    r"|limited[\s-]+time|will\s+end|ends?\s+at\s+\d{1,2}\s*(?:am|pm)|before\s+it\s+ends)\b",
    re.I | re.U)

# ── 24/09 (chủ shop, ca Nida Sumagaysay Duque · Madam Mystic Fengshui Expert USA 2): AI viết "baka mapunta sa iba ang
# slot at blessings mo" (suất và phước của chị có thể rơi vào tay người khác) — doạ MẤT SUẤT CHO NGƯỜI KHÁC là khan hiếm
# bịa cùng loại, mà KHAN_HIEM (chỉ có hạn chót / số lượng) không bắt. Tách thành NHÓM riêng và so ý THEO NHÓM: AI chỉ
# được nói kiểu nào khi kịch bản page có câu CÙNG NHÓM. 3 page Madam Mystic (USA, USA 2, TW 1340006199194919) có mẫu
# /Khokhantaichinh "i-hold ko muna ang slot mo para hindi mapunta sa iba ang blessings mo" → ở đó AI được nói "mất suất",
# nhưng KHÔNG vì thế mà được nói "ngayong araw lang" (nhóm hạn chót) — so gộp như trước là mở luôn cả hai.
# Đo /root/thu_khan_hiem/do.py trên 44.821 nháp AI + 8.438 mẫu kịch bản của 354 page (24/09): 58 nháp khớp nhóm mới,
# 19 page có mẫu cùng nhóm; bỏ mẫu "mawala ang promo" (20 nháp — đó là câu giữ ưu đãi chủ shop dặn), sửa "few remaining"
# để không bắt "few remaining teeth" (page răng giả); "naubos" chỉ bắt khi đi với stock/slot/promo (phát lại sổ việc: "naubos niyo
# na yung product" là khách dùng hết hàng, không phải khan hiếm).
KHAN_HIEM_MAT_SUAT = re.compile(
    r"\b(?:mapunta\s+(?:na\s+)?sa\s+iba|ma(?:ku)?kuha\s+(?:na\s+)?ng\s+iba|maunahan\s+(?:ka|kayo|po|pa|na|ng\s+iba)"
    r"|may\s+(?:iba(?:ng)?\s+)?(?:kukuha|kumuha)|i?bi(?:bi)?gay\s+(?:na\s+)?(?:ko\s+|namin\s+)?sa\s+iba"
    r"|maubos(?:an)?|naubos\s+(?:na\s+)?(?:ang\s+)?(?:stock|slot|promo|supply)"
    r"|(?:ko)?konti\s+na\s+lang\s+(?:ang\s+)?(?:slot|stock|natitira|available)"
    r"|limitado(?:ng)?\s+(?:slot|stock|piraso|lang)|unang\s+\d+\s+(?:customer|buyer|order|tao)"
    r"|(?:someone|somebody|another\s+(?:customer|person|buyer|client)|other\s+(?:customers?|people|buyers?)|others)"
    r"\s+(?:else\s+)?(?:(?:might|may|will|could|would|can)\s+)?(?:takes?|grabs?|claims?|snatch(?:es)?|books?|reserves?)"
    r"|(?:slot|spot|promo|offer|discount|reservation|blessing|item|stock|unit|piece)s?\s+(?:\w+\s+){0,3}?"
    r"(?:go|goes|be\s+given|given|be\s+offered|offered|be\s+released|released)\s+to\s+(?:someone|somebody|another|other|others)"
    r"|lose\s+(?:your|the|this|that)\s+(?:slot|spot|reservation|promo|offer|discount)"
    r"|(?:slot|spot|reservation)s?\s+(?:\w+\s+){0,2}?(?:is|are|will\s+be|may\s+be|might\s+be|could\s+be|gets?|be)"
    r"\s+(?:gone|taken|filled(?:\s+up)?|lost|given\s+away)"
    r"|limited\s+(?:slots?|spots?|seats?|quantity|quantities|pieces|pcs|units|availability|supply|number)"
    r"|(?:slots?|spots?)\s+(?:are\s+|is\s+)?(?:filling|running)\s+(?:up|out|low)"
    r"|few\s+(?:slots?|spots?|pieces|pcs|units|items|stocks?)\b|few\s+left\b|few\s+remaining(?!\s+[a-z])"
    r"|before\s+(?:it'?s|they'?re|its|it\s+is|they\s+are)\s+(?:all\s+)?(?:gone|sold\s+out|taken|out\s+of\s+stock)"
    r"|before\s+(?:someone|somebody|others?|another)\s+(?:else\s+)?(?:takes?|grabs?|gets?|claims?|books?)"
    r"|first\s+come[,\s]+first\s+serve[d]?|while\s+(?:stocks?|supplies|slots?|supply)\s+last"
    r"|(?:almost|nearly)\s+(?:sold\s+out|gone|out\s+of\s+stock|full)"
    r"|running\s+(?:out|low)\s+(?:of|on)\s+(?:stock|slots?|units|pieces)"
    r"|sold\s+out|first\s+\d+\s+(?:customers?|buyers?|orders?|people))\b",
    re.I | re.U)
# 25/09 (chủ shop): "Page mà kịch bản không có câu hạn chót nào, bạn tự nói khách về hạn chót" — HẠN CHÓT ưu đãi (hôm nay /
# 11 giờ tối nay) nói được ở MỌI page. Chỉ còn so kịch bản cho SỐ LƯỢNG (còn N cái / sắp hết hàng — kịch bản có câu khan hiếm
# bất kỳ như trước) và MẤT SUẤT (kịch bản phải có câu cùng nhóm).
KHAN_HIEM_SO_LUONG = re.compile(
    r"\b(last\s+\d+\s+(?:slots?|pieces?|stocks?|items?)|only\s+\d+\s+(?:left|remaining)|huling\s+\w*\s*slot"
    r"|limited\s+stock|اخر\s+قطع)\b", re.I | re.U)
# 25/09 (chủ shop, ngay sau khi mở hạn chót): "mở" — số lượng + mất suất cũng nói được ở MỌI page. Không còn nhóm nào phải so
# kịch bản; giữ các regex KHAN_HIEM* để đo / bật lại (đặt lại tuple cũ là xong).
KHAN_HIEM_NHOM = ()
# bản 25/09 11:58: (("số lượng", KHAN_HIEM_SO_LUONG, KHAN_HIEM), ("mất suất cho người khác", KHAN_HIEM_MAT_SUAT, KHAN_HIEM_MAT_SUAT))


def khan_hiem_bia(t, kb_page):
    """Lời khan hiếm trong câu AI mà kịch bản page KHÔNG có câu CÙNG NHÓM → (tên nhóm, match); không → None.

    So ý theo NHÓM chứ không so chữ: page có "today only" thì AI được nói "ngayong araw lang"; page có
    "hindi mapunta sa iba ang blessings mo" thì AI được nói "baka mapunta sa iba" — nhưng không chéo nhóm.
    """
    t = str(t or "")
    for ten, rx, rx_kb in KHAN_HIEM_NHOM:
        m = rx.search(t)
        if m and not _kich_ban_co_khan_hiem(kb_page, rx_kb):
            return ten, m
    return None

# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 5 — DOẠ KHÁCH / KÝ TỰ ẨN
# ══════════════════════════════════════════════════════════════════════════════
# Ca thật bên Talpha: luồng đòi hàng hoàn gửi "I'll be taking you to social media and posting
# in group of Filipino in SAUDI", chèn ký tự vô hình để né bộ lọc trùng của Meta.
DOA = re.compile(
    r"\b(report\s+you|take\s+you\s+to\s+(?:social\s+media|police)|blacklist|sue\s+you"
    r"|legal\s+action|ipa-?post\s+kita|isusumbong|أبلغ\s+عنك)\b", re.I | re.U)
# ⚠️ CHỪA U+200D (ZWJ): emoji ghép hiện đại dùng nó thật — 💆‍♀️ 👩‍💻 🧑‍🍳. Đo trên 4.824 đoạn
# kịch bản thật: bắt cả ZWJ thì chặn oan 10 mẫu chỉ vì có emoji người.
KY_TU_AN = re.compile(r"[\u200b\u200c\u200e\u200f\u202a-\u202e\u2060-\u2064\ufeff]")

# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 6 — LỘ CHUYỆN NỘI BỘ
# ══════════════════════════════════════════════════════════════════════════════
# Hai ca cụ thể của mình:
#  · Mục 9b chốt 1 thì 2 ghi rõ: khách xác nhận đúng nhà rồi thì "TUYỆT ĐỐI không nhắc gì
#    tới chuyện vừa có người đi tra địa chỉ". Luật đó chỉ nằm trong prompt — đây là chỗ
#    biến nó thành hàng rào.
#  · Model xưng "AI", nhắc "Botcake", "kịch bản", "sale" là khách biết đang nói với máy.
NOI_BO = re.compile(
    r"\b(botcake|pancake|kịch\s*bản|quick\s*repl(?:y|ies)|prompt|conversation[_\s]?id"
    r"|page[_\s]?id|shop[_\s]?id|as\s+an\s+ai|i\s+am\s+an?\s+(?:ai|bot|chatbot|language\s+model)"
    r"|(?:our|the)\s+(?:sale|sales|support)?\s*team\s+(?:checked|verified|looked\s+up|searched)"
    r"|we\s+(?:checked|verified|searched|looked\s+up)\s+(?:your\s+)?(?:house|address|location)"
    r"\s+(?:on|via|in)\s+google)\b",
    re.I | re.U)
# ⚠️ KHÔNG bắt "Google Maps" trần: 30 mẫu kịch bản thật xin khách chia sẻ vị trí qua Google Maps
# ("Paki-share po ng lokasyon ninyo sa Google Maps") — câu hoàn toàn hợp lệ, chặn là mất địa chỉ.

# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 7 — BỊA MÃ ĐƠN
# ══════════════════════════════════════════════════════════════════════════════
# AI không có mã đơn tại thời điểm soạn tin — mã do POS sinh sau. Đọc ra một mã là bịa,
# và khách sẽ dùng đúng mã đó để hỏi/khiếu nại về sau.
# Câu PHỦI QUẢNG CÁO của chính page — chủ shop chốt 2026-09-12 (ca Manuel Meringuez, Minty
# Fresh Smile UAE 11/09: khách hỏi "regrow teeth in a week, is it true?", AI đáp "not actual
# tooth regrowth" — cãi lại quảng cáo trước mặt khách, mất đơn). Luật trong prompt là lời
# khuyên; đây là hàng rào. Chỉ bắt cụm ĐÍNH CHÍNH rõ ràng, không bắt "not" chung chung:
# "we do not accept card", "does not contain chemicals", "cannot deliver today" phải QUA.
# Đã soi 5.317 mẫu kịch bản thật: 0 mẫu dính. Hai bẫy đã gặp lúc dựng: "hindi talaga kaya"
# trúng "hindi talaga kaya ng budget" (Madam Jane TW); "(can) really affect" trúng câu
# chào hàng Mint Breeze — nên "really/actually" CHỈ bắt khi đi sau phủ định.
PHUI_QC = re.compile(
    r"(not\s+(actually|really|exactly|entirely|completely)\s+(true|correct|accurate|possible|the\s+case)"
    r"|\bnot\s+actual\s+\w+"
    r"|that'?s\s+not\s+(true|correct|accurate|how\s+it\s+works)"
    r"|(the\s+)?ads?\s+(is|are|was|were|may\s+be|might\s+be)\s+"
    r"(not\s+\w+|misleading|exaggerat\w*|inaccurate|overstat\w*|wrong|false)"
    r"|(does|do|will|would|can|could)\s+not\s+(actually|really)\s+\w+"
    r"|(doesn'?t|don'?t|won'?t|can'?t|couldn'?t|wouldn'?t|isn'?t|aren'?t)\s+(actually|really)\s+\w+"
    r"|no\s+(product|toothpaste|cream|gel|serum|bracelet|supplement|oil|patch)\s+can\b"
    r"|(cannot|can'?t)\s+(grow|regrow|cure|heal|replace|restore|promise|guarantee)\b"
    r"|it\s+(is|'s)\s+(not\s+possible|impossible)\b"
    r"|hindi\s+(po\s+)?totoo"
    r"|غير\s+صحيح|ليس\s+صحيح)", re.I | re.U)

# ── 21/09 — CHỐI MỌC RĂNG / CHỐI QUẢNG CÁO BẰNG TIẾNG KHÁC (chủ shop: "MD Shahin Mondol lại chối là như nào? tôi dặn bạn sao") ──
# Ca MD Shahin Mondol (Minty Fresh Smile KSA, khách Bangladesh): AI viết tiếng Bengali "সত্যি বলতে — … শুধু পেস্ট দিয়ে ফাঁকা
# জায়গায় নতুন দাঁত গজানো সম্ভব নয়" (nói thật — chỉ bằng kem thì không mọc được răng mới ở chỗ trống), rồi khách hỏi lại thì
# "নতুন দাঁত গজানো পেস্টের কাজ নয়" (mọc răng mới không phải việc của kem). PHUI_QC chỉ biết Anh/Tagalog/Ả Rập nên cả hai lọt.
# Tiếng Anh hở đúng kiểu đó: "new teeth won't grow", "not the job of a toothpaste", "whether new teeth grow depends on…".
# Mẫu MỌC RĂNG neo vào chữ RĂNG trong cùng vế câu: "সম্ভব নয়" / "संभव नहीं" trơn là câu thường ("ngoài COD thì không được").
# Chữ Bengali không dùng \b (dấu nguyên âm không phải \w); "য়" có 2 cách gõ (1 mã hoặc য + ়) nên mẫu nhận cả hai.
_Y = "(?:\u09df|\u09af\u09bc)"                     # য়
_NOY = "ন" + _Y                                       # নয় (không phải)
_NA = "না(?![\u0980-\u09ff])"                        # না đứng riêng — không ăn "নাকি", "নাম"
_KHONG_BN = "(?:" + _NOY + "|" + _NA + ")"
_BN = "[\u0980-\u09ff]"
_DANT = "দাঁত"                                        # răng
_MOC_BN = "(?:গজা|গজি|উঠ|ওঠ)"                          # mọc / nhú lên
_HI_DANT = "दा[ँं]त"
_HI_KHONG = "(?:नहीं|नही)"
_UR_KHONG = "(?:نہیں|نھیں|نہی|نهیں)"
_PHUI_NAM_A = [
    # EN — mọc răng
    r"\bteeth\s+(?:won'?t|will\s+not|cannot|can'?t|don'?t|do\s+not|never)\s+(?:\w+\s+){0,2}?(?:grow|regrow|come\s+(?:back|out|in))",
    r"\b(?:won'?t|will\s+not|doesn'?t|does\s+not|don'?t|do\s+not)\s+(?:\w+\s+){0,2}?(?:grow|regrow)\s+(?:\w+\s+){0,2}?(?:teeth|tooth)\b",
    r"\b(?:grow\w*|regrow\w*)\s+(?:new\s+|back\s+)?(?:teeth|tooth)\s+(?:is|isn'?t)\s+(?:not\s+)?(?:\w+\s+){0,3}?(?:job|role|purpose|function|possible)\b",
    r"\bnot\s+(?:the\s+)?(?:job|role|purpose)\s+of\s+(?:a\s+|the\s+|any\s+)?(?:tooth)?paste",
    r"\b(?:new\s+teeth|tooth\s+regrowth|teeth\s+regrowth|regrow\w*|grow\w*\s+(?:new\s+)?teeth)[^.!?\n]{0,50}?\bdepend\w*\s+on\b",
    # TL — "hindi po tutubo ang bagong ngipin"
    r"\b(?:hindi|di)\s+(?:po\s+)?(?:na\s+)?(?:\w+\s+)?(?:tutubo|tumutubo|makakatubo|magpapatubo|mapapatubo)\b[^.!?\n]{0,30}?\bngipin",
    r"\bngipin\b[^.!?\n]{0,30}?\b(?:hindi|di)\s+(?:po\s+)?(?:na\s+)?(?:tutubo|tumutubo)\b",
    # AR — "لن تنبت أسنان جديدة", "لا يمكن أن تنمو أسنان جديدة" (phủ định phải sát động từ)
    r"(?:لن|لا)\s+(?:ت|ي)(?:نبت|نمو)",
    r"(?:لا\s+يمكن|مستحيل|غير\s+ممكن)\s+(?:\S+\s+){0,2}?(?:إنبات|انبات|نمو|تنبت|ينبت|تنمو|ينمو)",
    r"(?:إنبات|انبات|نمو)\s+(?:\S+\s+){0,2}?(?:مستحيل|غير\s+ممكن)",
    # BN — "দাঁত গজানো সম্ভব নয়", "দাঁত উঠবে না", "গজানো পেস্টের কাজ নয়", "দাঁত ওঠা নির্ভর করে…", "সত্যি নয়"
    _DANT + r"[^\n।!?]{0,50}?(?:সম্ভব\s*" + _KHONG_BN + r"|অসম্ভব)",
    _MOC_BN + _BN + r"*\s*(?:" + _BN + r"+\s*){0,3}?(?:সম্ভব\s*" + _KHONG_BN + r"|অসম্ভব)",
    _DANT + r"[^\n।!?]{0,30}?(?:গজাবে|গজা" + _Y + r"|গজাতে\s*পার\S*|উঠবে|ওঠে|উঠতে\s*পার\S*)\s*" + _NA,
    _MOC_BN + _BN + r"*\s*(?:" + _BN + r"+\s*){0,3}?কাজ\s*" + _KHONG_BN,
    _DANT + r"[^\n।!?]{0,40}?" + _MOC_BN + r"[^\n।!?]{0,40}?নির্ভর\s*কর",
    r"সত্যি\s*" + _NOY, r"সত্য\s*" + _NOY, r"সত্যি\s*না(?=\s*[।!.,?]|\s*$)",
    # HI — "नए दांत उगना संभव नहीं", "दांत नहीं उगेंगे", "सच नहीं"
    _HI_DANT + r"[^\n।!?]{0,50}?(?:(?:संभव|सम्भव|मुमकिन)\s*" + _HI_KHONG + r"|असंभव|असम्भव|नामुमकिन)",
    _HI_DANT + r"[^\n।!?]{0,30}?(?:" + _HI_KHONG + r"\s*उग|उग\s*" + _HI_KHONG + r"|उग\s*सक(?:ते|ता|ती)\s*" + _HI_KHONG + ")",
    _HI_DANT + r"[^\n।!?]{0,50}?निर्भर",
    r"सच\s*" + _HI_KHONG,
    # UR — "نئے دانت اگنا ممکن نہیں", "دانت نہیں اگیں گے", "سچ نہیں"
    r"دانت[^\n.!?۔]{0,50}?(?:ممکن\s*" + _UR_KHONG + r"|ناممکن)",
    r"دانت[^\n.!?۔]{0,30}?(?:" + _UR_KHONG + r"\s*(?:اگ|اُگ)|(?:اگ|اُگ)\S*\s*" + _UR_KHONG + ")",
    r"دانت[^\n.!?۔]{0,50}?منحصر",
    r"سچ\s*" + _UR_KHONG,
]
PHUI_QC = re.compile("(?:" + PHUI_QC.pattern + ")|" + "|".join(_PHUI_NAM_A), re.I | re.U)

# ── 23/09 — CHỐI BẰNG "KHÔNG HỨA / KHÔNG ĐẢM BẢO / KHÔNG PHẢI PHÉP MÀU" (chủ shop: "lại chối sản phẩm rồi", ca Fely F Castillo —
# Madam Mystic Fengshui Expert TW): khách "Pag nagkaroon po ba nyan tas tumaya ako s lotto mananalo" → AI "Hindi namin maipapangako
# ang panalo sa lotto, pero dala mo ang magandang intensyon…". PHUI_QC chỉ biết "cannot promise/guarantee" tiếng Anh sát nhau.
# Câu rào kiểu này ở mọi tiếng đều là CHỐI SẢN PHẨM: không hứa / không đảm bảo / không chắc / tuỳ may / không phải phép màu /
# kết quả tuỳ người. Chủ shop 23/09: "cái gì tốt là sản phẩm đều hỗ trợ được" — nói CÓ theo ý nghĩa trong kịch bản rồi chốt.
# Câu KHẲNG ĐỊNH ("guaranteed 18K gold", "7-day money-back guarantee", "pangako ko sasamahan kita") không có phủ định → qua.
_KHONG_HUA = [
    # EN
    r"\b(?:there(?:'s|\s+is|\s+are)\s+)?(?:no|not\s+a|without\s+(?:any\s+)?)\s+(?:100%\s+|absolute\s+|sure\s+|real\s+)?guarantees?\b",
    r"\bnot\s+(?:100%\s+|fully\s+|really\s+|always\s+)?guaranteed\b",
    r"\b(?:do|does|did)\s*(?:n'?t|\s+not)\s+(?:\w+\s+)?(?:promise|guarantee|assure|ensure)\b",
    r"\b(?:won'?t|will\s+not|wouldn'?t|would\s+not|shouldn'?t)\s+(?:\w+\s+)?(?:promise|guarantee|assure)\b",
    r"\b(?:unable|not\s+able|not\s+in\s+a\s+position|not\s+allowed)\s+to\s+(?:promise|guarantee|assure)\b",
    r"\b(?:cannot|can'?t|couldn'?t|could\s+not|can\s+not)\s+(?:\w+\s+){1,2}?(?:promise|guarantee|assure|ensure|predict)\b",
    r"\b(?:no\s+one|nobody|noone|no\s+(?:item|necklace|bracelet|amulet|charm|ring|stone))\s+can\s+(?:\w+\s+)?"
    r"(?:promise|guarantee|predict|assure|make\s+you\s+win)\b",
    r"\b(?:it|this|that|which|necklace|bracelet|amulet|charm|product)(?:'s|\s+is|\s+isn'?t)\s+(?:not\s+)?(?:a\s+)?"
    r"(?:magic|magical|miracle|miraculous)\b(?!\s+(?:touch|feeling|moment|of))",
    r"\bnot\s+(?:a\s+|some\s+)?(?:magic|magical|miracle)\s*(?:item|charm|amulet|solution|pill|cure|product|fix|wand|object|thing)?\b",
    r"\bno\s+(?:magic|miracle)s?\b",
    r"\b(?:won'?t|will\s+not|doesn'?t|does\s+not|cannot|can'?t|not\s+going\s+to)\s+(?:\w+\s+){0,2}?(?:make|let|help)\s+"
    r"(?:you|anyone|someone|people)\s+win\b",
    r"\bresults?\s+(?:may|can|will|might|could)\s+vary\b",
    r"\b(?:depends?|depending|rely|relies)\s+(?:entirely\s+|largely\s+|mostly\s+|still\s+|also\s+)?(?:on|upon)\s+"
    r"(?:your\s+|one'?s\s+|the\s+)?(?:luck|fate|chance|chances|destiny|faith|belief|odds)\b",
    r"\b(?:game|matter)\s+of\s+(?:chance|luck)\b|\bup\s+to\s+(?:luck|chance|fate)\b",
    # TL — "hindi namin maipapangako", "wala kaming maipapangako", "hindi ko ma-guarantee", "walang garantiya", "hindi ito magic"
    r"\bhindi\s+(?:po\s+)?(?:ko|namin|naming|natin|kami|ako|nito|niya|ito|siya)?\s*(?:po\s+)?(?:ma|mai|maka)-?i?(?:pa)?pangako",
    r"\bwala(?:ng)?\s+(?:po\s+)?(?:kaming|akong|kami|ako|itong)?\s*(?:po\s+)?(?:ma)?i?pa?pangako",
    r"\bhindi\s+(?:po\s+)?(?:ko|namin|naming|kami|ako|nito|ito|siya)?\s*(?:po\s+)?(?:ma|mai|maka|magpa|makapag)?-?(?:ga)?"
    r"(?:garantiya\w*|guarantee\w*|garantisado\w*|garantihan)",
    r"\bwala(?:ng)?\s+(?:po\s+)?(?:kaming\s+|akong\s+)?(?:garantiya|guarantee|kasiguraduhan|katiyakan|siguradong\s+panalo)\b",
    r"\bhindi\s+(?:po\s+)?(?:ko|namin|naming|kami|ako|nito|ito)?\s*(?:po\s+)?(?:ma|mai)-?(?:sisiguro|siguro|sigurado|tiyak|titiyak)\b",
    r"\bhindi\s+(?:po\s+)?(?:ito\s+|iyan\s+|yan\s+|naman\s+)?(?:siguradong|garantisadong|tiyak\s+na)\s+"
    r"(?:panalo|mananalo|manalo|swerte|suwerte|gagana|tatalab|uubra|yayaman)",
    r"\bhindi\s+(?:po\s+)?(?:ito|iyan|yan|siya|naman\s+ito)?\s*(?:po\s+)?(?:isang\s+)?(?:magic|mahika|milagro|salamangka)\b",
    r"\bwalang\s+(?:po\s+)?(?:magic|mahika|milagro)\b",
    r"\bhindi\s+(?:po\s+)?(?:ka|kayo|kita)\s+(?:po\s+)?(?:agad\s+|basta\s+|awtomatiko\w*\s+|siguradong\s+)?"
    r"(?:mananalo|manalo|yayaman|susuwertehin|swertehin)\b",
    r"\b(?:naka)?depende\s+(?:pa\s+)?(?:rin\s+)?(?:po\s+)?(?:ito\s+|iyan\s+|yan\s+|ang\s+lahat\s+)?sa\s+"
    r"(?:swerte|suwerte|tadhana|kapalaran|pananampalataya|paniniwala|tsansa)\b",
    r"\bnasa\s+(?:swerte|suwerte|tadhana|kapalaran)\s+(?:pa\s+rin|lang|na\s+lang|pa)\b",
    # ID
    r"\b(?:tidak|tak|nggak|gak|ga|belum)\s+(?:bisa\s+|dapat\s+|akan\s+|mungkin\s+|pernah\s+)?(?:kami\s+|saya\s+|aku\s+)?(?:men)?jamin\w*",
    r"\b(?:tidak|tak|nggak|gak|ga)\s+ada\s+(?:yang\s+)?(?:jaminan|garansi)\b|\btanpa\s+(?:jaminan|garansi)\b|\bbukan\s+jaminan\b",
    r"\b(?:tidak|tak|nggak|gak|ga)\s+(?:bisa\s+|akan\s+|berani\s+)?(?:kami\s+|saya\s+|aku\s+)?(?:ber)?janji\w*",
    r"\bbukan\s+(?:barang\s+|benda\s+|hal\s+|sesuatu\s+yang\s+)?(?:sihir|ajaib|magic|sulap|keajaiban)\b",
    r"\btergantung\s+(?:juga\s+|pada\s+|dari\s+|sama\s+|kepada\s+)?(?:keberuntungan|nasib|rezeki|rejeki|takdir|hoki)\b",
    # AR — "لا نضمن", "ما نقدر نضمن", "لا يوجد ضمان", "ليس سحرا", "يعتمد على الحظ"
    r"(?:لا|ما|لن|مو|مش)\s+(?:نستطيع|نقدر|يمكننا|يمكن|أستطيع|استطيع|أقدر|اقدر|بنقدر)\s+(?:أن\s+|ان\s+)?"
    r"(?:نضمن|أضمن|اضمن|نعد|نوعد|أوعد|اوعد|نؤكد|أؤكد|اؤكد|نتعهد)",
    r"(?:لا|ما|لن|مو|مش)\s+(?:نضمن|أضمن|اضمن|يضمن|تضمن|بنضمن|بضمن|نوعد|أوعد|اوعد|بنوعد|نعدك|أعدك|اعدك|نتعهد|أتعهد|اتعهد)",
    r"(?:لا\s+يوجد|لا\s+توجد|ليس\s+هناك|ما\s+في|مافي|مافيه|ماكو|بدون|من\s+غير|بلا)\s+(?:أي\s+|اي\s+|أية\s+)?(?:ضمان|ضمانة|ضمانات|وعد|وعود)",
    r"(?:ليس|ليست|مش|مو|ماهو|ما\s+هو|ماهي|ما\s+هي|مب)\s+(?:سحر|سحرا|سحراً|سحرية|معجزة|خارقة)",
    r"(?:يعتمد|تعتمد|بيعتمد|بتعتمد|يتوقف|تتوقف)\s+(?:كليا\s+|كلياً\s+|فقط\s+|أيضا\s+|ايضا\s+|أيضاً\s+)?(?:على\s+|ع\s+)?"
    r"(?:الحظ|حظك|حظكم|القدر|النصيب|الإيمان|الايمان|إيمانك|ايمانك|نيتك|النية)",
    r"(?:النتائج|النتيجة)\s+(?:قد\s+)?(?:تختلف|تتفاوت)",
    # BN / HI / UR — "không đảm bảo / không hứa được", "kết quả tuỳ người"
    r"(?:গ্যারান্টি|গ্যারেন্টি|গেরান্টি|নিশ্চ" + _Y + r"তা|ওয়াদা|ও" + _Y + r"াদা|প্রতিশ্রুতি)\s*"
    r"(?:দিতে\s*পার(?:ি|ব|ছি)\s*না|করতে\s*পার(?:ি|ব|ছি)\s*না|নেই|নাই|দেই\s*না|দিচ্ছি\s*না|দেওয়া\s*(?:যায়|সম্ভব)\s*না)",
    r"(?:কোনো?|কোন)\s*(?:গ্যারান্টি|গ্যারেন্টি|নিশ্চ" + _Y + r"তা)\s*(?:নেই|নাই)",
    r"ফলাফল\s*(?:ভিন্ন|আলাদা)\s*হতে\s*পারে",
    r"(?:गारंटी|गारण्टी|गारन्टी|वादा)\s*(?:नहीं|नही)",
    r"(?:कोई|कोइ)\s*(?:गारंटी|गारण्टी|गारन्टी|वादा)\s*(?:नहीं|नही)",
    r"(?:परिणाम|नतीजे?)\s*(?:अलग|भिन्न)\s*हो\s*सकत",
    r"(?:گارنٹی|گارنٹي|وعدہ|وعده)\s*(?:نہیں|نھیں)",
    r"(?:کوئی|كوئي)\s*(?:گارنٹی|وعدہ)\s*(?:نہیں|نھیں)",
    r"(?:نتیجہ|نتائج)\s*(?:مختلف|الگ)\s*ہو\s*سکت",
]
PHUI_QC = re.compile("(?:" + PHUI_QC.pattern + ")|" + "|".join(_KHONG_HUA), re.I | re.U)
_CHU_THUONG = re.compile(r"[^\w\s]", re.U)


def _chuan_cau(x):
    return re.sub(r"\s+", " ", _CHU_THUONG.sub(" ", str(x or "").lower())).strip()


def _cau_khop_kb(t, m, kb_page=None, cau_page=None):
    """Câu chứa chỗ khớp có SẴN trong kịch bản page / tin page đã gửi → lời shop tự viết ("Hindi po ito magic o guarantee ng
    pera" — Blessed Feng Shui Bracelets TW; "Results may vary" — Glow & Grace), không phải AI tự chối. Đo 23/09: 5/5.819 đoạn
    kịch bản dính mẫu mới, đều là câu shop; AI chép nguyên bước kịch bản thì phải qua."""
    if not (kb_page or cau_page):
        return False
    kb = _chuan_cau(_chu_kich_ban(kb_page, cau_page))
    if not kb:
        return False
    s, e = m.span()
    dau = max([t.rfind(c, 0, s) for c in "\n.!?"] + [-1]) + 1
    cuoi = min([i for i in (t.find(c, e) for c in "\n.!?") if i >= 0] + [len(t)])
    cau = _chuan_cau(t[dau:cuoi])
    return len(cau) >= 8 and cau in kb


def _phui_qc_m(t, kb_page=None, cau_page=None):
    """Chỗ khớp PHUI_QC đầu tiên KHÔNG phải câu chép từ kịch bản page; không có thì None."""
    for m in PHUI_QC.finditer(t):
        if not _cau_khop_kb(t, m, kb_page, cau_page):
            return m
    return None

# ── PHỦI BỆNH CHÍNH PAGE ĐANG BÁN (chủ shop 19/09 "bạn lại phủi quảng cáo à?", ca Namzuged Xam — Soothing
# Cooling Gel in Saudi) ──
# Kịch bản page bán cho TRĨ không gọi tên bệnh (luật quảng cáo Facebook), chỉ tả "discomfort vùng hậu môn,
# bukol, pagdurugo, bơm vào anal canal". Khách hỏi "Mawawala po ba ang almuranas? Magagamot niya ba ito?" →
# khối ❓ KHÁCH HỎI SẢN PHẨM bảo "bệnh kịch bản không nói → không phải thuốc chữa bệnh đó" → AI nhắn "hindi po
# ito gamot para sa almuranas" rồi "almuranas phải đi bác sĩ, gel chỉ pang-relief lang". PHUI_QC không bắt vì
# không có chữ "not true / not actual". Câu kiểu này chỉ là PHỦI khi bệnh đó CHÍNH là bệnh page bán — trà thảo
# mộc mà khách hỏi tim to, kính đọc sách mà hỏi đục thuỷ tinh thể thì nói thật + hỏi bác sĩ vẫn đúng. Nên cổng
# chỉ bắt khi bệnh nhắc trong tin AI / tin khách khớp BENH_PAGE của kịch bản (tên bệnh HOẶC vùng kịch bản tả).
BENH_PAGE = {
    # bệnh: (khách / AI gọi tên, dấu hiệu kịch bản + tin page đang bán cho bệnh đó)
    "trĩ": (r"almuranas|almoranas|h(?:a)?emorr?h?oids?|\bpiles\b|بواسير|\bwasir\b|ambeien|bawasir|\btrĩ\b",
            r"almuranas|almoranas|h(?:a)?emorr?h?oid|\bpiles\b|بواسير|\banal\b|\banus\b|\brectal\b|pagdumi"
            r"|bowel\s+movement|\bpuwi?t\b|\bpuwet\b|\bpwet\b|hậu\s+môn|الشرج"),
    "giãn tĩnh mạch": (r"varicos\w*|varikos\w*|spider\s+veins?|varises|الدوالي|دوالي|giãn\s+tĩnh\s+mạch",) * 2,
    "mụn cóc": (r"\bwarts?\b|kulugo|butlig|ثآليل|ثؤلول|\bkutil\b|skin\s+tags?|mụn\s+cóc",) * 2,
    "rụng tóc": (r"hair\s*(?:fall|loss)|balding|\bbald\b|kalbo|\w*lagas\b|تساقط\s+الشعر|الصلع|rontok|\bbotak\b|rụng\s+tóc",
                 r"hair\s*(?:fall|loss)|balding|\bbald\b|kalbo|\w*lagas\b|تساقط\s+الشعر|الصلع|rontok|rụng\s+tóc"
                 r"|hair\s+(?:re)?growth|regrow\w*\s+(?:your\s+)?hair"),
    "khớp": (r"arthritis|rayuma|\bgout\b|joint\s+pain|kasukasuan|المفاصل|النقرس|asam\s+urat|rematik|đau\s+khớp",
             # chỉ page bán cho ĐAU KHỚP — "dark knees / joints" ở page làm trắng da không tính (đo 19/09: 12 page oan)
             r"arthritis|rayuma|\bgout\b|joint\s+(?:pain|ache|stiff\w*)|pain\w*\s+(?:in\s+)?(?:the\s+|your\s+)?joints?"
             r"|kasukasuan|آلام\s+المفاصل|التهاب\s+المفاصل|النقرس|knee\s+pain|sakit\s+(?:sa|ng)\s+tuhod|masakit\s+na\s+tuhod"),
    "nấm": (r"fung(?:us|al|i)\b|halamang[- ]?singaw|alipunga|فطري|\bjamur\b|nấm\s+(?:móng|da)",) * 2,
    "sừng hoá da": (r"keratosis|chicken\s+skin|balat\s+manok|dày\s+sừng",) * 2,
    "u xơ": (r"myoma|fibroids?|الأورام\s+الليفية|\bmiom\w*|u\s+xơ",) * 2,
    # Oxyelle Womb Care Gel (Kreain Nature PH in Uae, ca Grenelyn 23/09): kịch bản tả đau bụng kinh / ấm tử cung —
    # khách "bwan bwan p akong denudugo pero ang lumalabas may mga belog na dugo" (tháng nào cũng ra máu cục) → AI bảo đi
    # bác sĩ. Vế page chỉ nhận page bán cho kinh nguyệt / tử cung (không dính page giảm mỡ bụng có chữ "puson").
    "kinh nguyệt": (r"menstrua\w*|dysmenorr\w*|\bregla\b|\bmens\b|nireregla|d[ie]nudugo|\bdugo\b|blood\s+clots?|\bclots?\b"
                    r"|heavy\s+(?:period|flow|bleeding)|\bcramps?\b|period\s+(?:pain|cramps?)|sakit\s+(?:ng\s+|sa\s+)?puson"
                    r"|masakit\s+(?:ang\s+)?puson|الدورة\s*الشهرية|الحيض|تقلصات|جلطات|\bhaid\b|menstruasi|kinh\s+nguyệt"
                    r"|hành\s+kinh|máu\s+cục|tử\s+cung|\bwomb\b|\bmatris\b",
                    r"menstrua\w*|\bwomb\b|dysmenorr\w*|\bregla\b|period\s+(?:pain|cramps?)|الرحم|الحيض"
                    r"|الدورة\s+الشهرية|\bhaid\b|menstruasi|tử\s+cung|kinh\s+nguyệt"),
    "mắt": (r"cataract|katarata|glaucoma|الساد|الماء\s+الأبيض|katarak|đục\s+thuỷ\s+tinh",) * 2,
    "tiền liệt": (r"prostat\w*|البروستاتا|tiền\s+liệt",) * 2,
    # Japan Herb Lab: "herbal support product — not a guaranteed cure" cho kem bôi tuyến giáp
    "tuyến giáp": (r"thyroid|goit(?:er|re)|\bbosyo\b|الغدة\s+الدرقية|\bgondok\b|bướu\s+cổ|tuyến\s+giáp",) * 2,
    # Kreain Nature Aura: quảng cáo nói tác dụng lên phổi, AI đáp "hindi po ito gamot sa loob ng baga"
    "phổi": (r"\bbaga\b|\blungs?\b|الرئة|الرئتين|paru-?paru|\bphổi\b",) * 2,
}
BENH_PAGE = {k: (re.compile(a, re.I | re.U), re.compile(b, re.I | re.U)) for k, (a, b) in BENH_PAGE.items()}
PHU_THUOC = re.compile(
    r"\bhindi\s+(?:po\s+)?(?:ito|iyan|yan|siya)?\s*(?:po\s+)?(?:isang\s+)?(?:gamot|lunas|medisina)\b"
    r"|\bhindi\s+(?:po\s+)?(?:ito|siya|iyan|yan)\s+(?:po\s+)?(?:nakakagamot|nagpapagaling|makakagamot|gagamot)"
    r"|\b(?:not|isn'?t|is\s+not|it'?s\s+not)\s+(?:a|an)\s+(?:\w+\s+)?(?:medicine|cure|treatment|drug|medication|remedy)\b"
    r"|\bnot\s+(?:meant|designed|intended|made)\s+to\s+(?:cure|treat|heal)\b"
    r"|\b(?:does|do|will|can)\s*(?:n'?t|not)\s+(?:cure|treat|heal|remove|eliminate)\b"
    r"|\b(?:pang-?\s?relief|relief|pampaginhawa|pampagaan)\s+lang\b|\bsintomas\s+lang\b"
    r"|\b(?:only|just)\s+(?:for\s+)?(?:temporary\s+)?(?:relief|symptoms?)\b|\bsymptoms?\s+only\b"
    r"|ليس\s+(?:علاجا?|دواء)|مش\s+(?:علاج|دواء)|لا\s+(?:يعالج|يشفي)|\bbukan\s+obat\b"
    r"|\btidak\s+(?:menyembuhkan|mengobati)\b|không\s+phải\s+(?:là\s+)?thuốc", re.I | re.U)
DAY_BAC_SI = re.compile(
    r"\b(?:consult|see|check\s+with|visit|go\s+to|ask)\s+(?:a|your|an|the)\s+(?:\w+\s+)?(?:doctor|physician|specialist)"
    r"|\b(?:magpa)?konsulta\w*\s+(?:po\s+)?(?:muna\s+)?(?:sa|ng)\s+doktor|\bpumunta\s+(?:po\s+)?(?:muna\s+)?sa\s+doktor"
    r"|\bmagpatingin\s+(?:po\s+)?(?:muna\s+)?sa\s+doktor|\bdoktor\b.{0,40}\b(?:gamot|procedure|operasyon|opera)\b"
    r"|(?:راجع|استشر|استشارة|مراجعة)\s+(?:ال)?طبيب|\b(?:periksa|konsultasi)\s+ke\s+dokter", re.I | re.U)
# 23/09 ca Grenelyn: "mas mabuting ipakonsulta muna ito sa doktor — hindi po namin kayo maa-advisean tungkol diyan"
# lọt vì "ipakonsulta" dính tiền tố (không có \b trước "konsulta") và có chữ chen giữa; câu "shop không tư vấn được"
# cũng là chối. Ca Loreins (cùng page): "it's best to have a doctor check it".
_DAY_BAC_SI_THEM = [
    r"konsulta\w*[^.!?\n]{0,30}?\b(?:doktor|doctor|ob-?gyne?|espesyalista|ospital|hospital|clinic|klinika)\b",
    r"magpa-?tingin\w*[^.!?\n]{0,30}?\b(?:doktor|doctor|ob-?gyne?|ospital|hospital|clinic|klinika)\b",
    r"\bpumunta[^.!?\n]{0,20}?\bsa\s+(?:isang\s+)?(?:doktor|doctor|ob-?gyne?|ospital|hospital|clinic|klinika)\b",
    r"\bsa\s+doktor\s+(?:po\s+)?muna\b",
    r"\b(?:consult|see|check\s+with|visit|go\s+to|ask|talk\s+to|speak\s+(?:to|with)|seek)\s+(?:a|your|an|the)\s+"
    r"(?:\w+\s+){0,2}?(?:doctor|physician|specialist|gyn\w*|ob-?gyn\w*|healthcare\s+(?:professional|provider)"
    r"|medical\s+professional)",
    r"\bhave\s+(?:a|your)\s+doctor\s+(?:check|look)",
    r"\bseek\s+(?:proper\s+|immediate\s+)?medical\s+(?:advice|attention|help|care)\b",
    r"\b(?:we|i)\s*(?:can(?:no|')?t|cannot|can\s+not|are\s+not\s+able\s+to|am\s+not\s+able\s+to|are\s+unable\s+to"
    r"|'?m\s+unable\s+to|'re\s+not\s+able\s+to)\s+(?:give\s+(?:you\s+)?|provide\s+)?(?:medical\s+)?(?:advi[cs]e|diagnos\w*)",
    r"\bhindi\s+(?:po\s+)?(?:namin|ko)\s+(?:po\s+)?(?:kayo\s+|ikaw\s+)?(?:po\s+)?(?:ma+-?advise\w*|mapapayuhan"
    r"|mabibigyan\s+ng\s+(?:medical\s+)?(?:advice|payo))",
    r"\b(?:we(?:'re|\s+are)|i(?:'m|\s+am))\s+not\s+(?:a\s+)?(?:doctors?|medical\s+professionals?)\b",
    r"\bhindi\s+(?:po\s+)?(?:kami|ako)\s+(?:mga\s+)?doktor\b",
    r"(?:راجعي|استشيري|زوري)\s+(?:ال)?طبيب", r"لا\s+(?:نستطيع|يمكننا|أستطيع)\s+(?:تقديم\s+)?(?:نصيحة|استشارة)\s+طبية",
]
DAY_BAC_SI = re.compile("(?:" + DAY_BAC_SI.pattern + ")|" + "|".join(_DAY_BAC_SI_THEM), re.I | re.U)
# Câu cảnh báo dùng sản phẩm của chính kịch bản ("if irritation occurs, discontinue and consult a doctor") không phải chối.
# Chỉ bắt NGỮ CẢNH cảnh báo ("if itching persists", "irritation occurs") — "pangangati, pamumula" trơn là TRIỆU CHỨNG
# sản phẩm lo, không được tha (đo 23/09: ca Samson — Legs Smoothing Cream).
CANH_BAO_DUNG = re.compile(
    r"irritat\w*\s+(?:occurs?|develops?|persists?|happens?)|\bif\s+(?:any\s+)?(?:irritation|redness|rash|itching"
    r"|allerg\w*)\b|discontinue|stop\s+using|itigil\s+(?:ang\s+)?(?:paggamit|gamitin)|allergic\s+reaction"
    r"|kapag\s+(?:nagka|may)\s*(?:iritasyon|pamumula|allergy)|avoid\s+contact|تهيج|توقف\w*\s+عن\s+الاستخدام"
    r"|hentikan\s+pemakaian|jika\s+(?:terjadi\s+)?iritasi", re.I | re.U)


KHONG_CAN = re.compile(      # "No need to see a doctor first" — phủ định ngay trước, cùng vế câu
    r"no\s+need|don'?t\s+need|do\s+not\s+need|don'?t\s+have\s+to|without|hindi\s+(?:na\s+)?(?:po\s+)?kailangan"
    r"|di\s+na\s+kailangan|لا\s+داعي|لا\s+حاجة|tidak\s+perlu|không\s+cần", re.I | re.U)
UONG = re.compile(r"\s*(?:minum|oral|na\s+iniinom|iniinom|inumin|للشرب|فموي)", re.I | re.U)   # "bukan obat minum"
# Lời dặn CÓ ĐIỀU KIỆN kiểu kịch bản ("If you are taking medication…, consult your doctor") — không phải đẩy khách đi.
DIEU_KIEN = re.compile(
    r"\bif\s+you\s*(?:are|'re|have|take)\b[^.!?\n]{0,40}?(?:medication|medicine|maintenance|pregnan|breast-?feed|nursing"
    r"|allerg)|\bkung\s+(?:kayo\s+|ikaw\s+)?(?:po\s+)?(?:ay\s+)?(?:may\s+)?(?:iniinom|maintenance|buntis|nagpapasuso"
    r"|allergy|allergic)|إذا\s+كن?ت[^.!?\n]{0,30}(?:أدوية|دواء|حامل|مرضع)|jika\s+(?:anda\s+)?(?:sedang\s+)?(?:hamil"
    r"|menyusui|minum\s+obat)", re.I | re.U)


def _cau_quanh(t, m):
    """Câu (giữa hai dấu . ! ? xuống dòng) chứa chỗ khớp m."""
    dau = max(t.rfind(x, 0, m.start()) for x in ".!?\n") + 1
    cuoi = min([i for i in (t.find(x, m.end()) for x in ".!?\n") if i >= 0] or [len(t)])
    return t[dau:cuoi]


def _tha_cau(t, m, kh, bac_si):
    """True khi chỗ khớp PHU_THUOC / DAY_BAC_SI KHÔNG phải chối sản phẩm: cảnh báo dùng (kích ứng), câu nói về bệnh
    khác hẳn (BENH_KHAC), phủ định ngay trước ("no need to see a doctor"), 'không phải thuốc UỐNG'; riêng câu bác sĩ:
    khách tự nói bầu / cho bú / dị ứng… hoặc lời dặn có điều kiện ("if you are taking medication…")."""
    cau = _cau_quanh(t, m)
    if CANH_BAO_DUNG.search(cau) or BENH_KHAC.search(cau):
        return True
    dau_menh = max(t.rfind(x, 0, m.start()) for x in ",.;!?—\n") + 1
    if KHONG_CAN.search(t[dau_menh:m.start()]):
        return True
    if bac_si:
        return bool(KHACH_CAN_BAC_SI.search(kh) or DIEU_KIEN.search(cau))
    return bool(UONG.match(t, m.end()) or re.search(r"\boral\b", m.group(0), re.I))


# Khách hỏi chung "thuốc gì / chữa khỏi không" mà không gọi tên bệnh (ca Jessie 18/09 "anong gamot po sir." →
# AI "hindi gamot kundi cooling gel") — ở page bán cho bệnh thì chối "không phải thuốc" cũng là phủi.
HOI_CHUA = re.compile(
    r"\bgamot\b|\bmedicine\b|\bcured?\b|\blunas\b|gagaling|mawawala|matatanggal|mapapagaling|magagamot|\btreat\w*"
    r"|\bheal\w*|علاج|دواء|يشفي|يعالج|\bobat\b|sembuh|chữa|khỏi", re.I | re.U)
# Bệnh ngoài danh sách (khách hỏi "có chữa huyết áp không" ở page trĩ) → nói thật "không phải thuốc huyết áp" là đúng.
BENH_KHAC = re.compile(
    r"high\s*blood|\bbp\b|blood\s+pressure|hypertension|altapresyon|diabet\w*|\bsugar\b|asukal|cholesterol|\bheart\b"
    r"|\bpuso\b|kidney|\bbato\b|\bliver\b|\batay\b|cancer|kanser|stroke|\basthma\b|hika|ضغط|السكر|القلب|الكلى|سرطان"
    r"|darah\s+tinggi|kencing\s+manis|jantung|huyết\s+áp|tiểu\s+đường|tim\b|ung\s+thư", re.I | re.U)
# Khách tự nêu lý do cần hỏi bác sĩ (bầu, cho con bú, thuốc duy trì, dị ứng, trẻ nhỏ) → khuyên hỏi bác sĩ là ĐÚNG.
KHACH_CAN_BAC_SI = re.compile(
    r"buntis|pregnan\w*|breast\s*feed\w*|nagpapasuso|maintenance|allerg\w*|\bbata\b|\bbaby\b|\bkids?\b|\bchild\w*"
    r"|حامل|الحمل|مرضع|رضاعة|حساسية|طفل|أطفال|\bhamil\b|menyusui|\bbầu\b|cho\s+con\s+bú|dị\s+ứng", re.I | re.U)


def _chu_kich_ban(kb_page, cau_page=None):
    """Toàn bộ chữ kịch bản page + tin Botcake/sale trong hội thoại (quảng cáo có khi gọi tên bệnh)."""
    ra = []
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            if isinstance(tin, str):
                ra.append(tin)
    ra.extend(str(x) for x in (cau_page or []))
    return "\n".join(ra)


def phui_benh(t, kb_page=None, cau_khach=None, cau_page=None):
    """(câu phủi, tên bệnh) khi tin AI chối công dụng cho CHÍNH bệnh page đang bán; không thì None."""
    t = str(t or "")
    kh = "\n".join(str(x) for x in (cau_khach or [])[-8:])
    m = PHU_THUOC.search(t)
    if m and _tha_cau(t, m, kh, bac_si=False):
        m = None
    if not m:
        m = DAY_BAC_SI.search(t)
        if m and _tha_cau(t, m, kh, bac_si=True):
            m = None
    if not m:
        return None
    kb = _chu_kich_ban(kb_page, cau_page)
    if m.group(0).lower() in kb.lower():        # câu của chính shop (HDSD "consult a doctor if…") thì tha
        return None
    hoi = t + "\n" + kh
    benh_page = [ten for ten, (_, r_page) in BENH_PAGE.items() if r_page.search(kb)]
    for ten in benh_page:
        if BENH_PAGE[ten][0].search(hoi):
            return m.group(0), ten
    # ĐẨY KHÁCH ĐI BÁC SĨ / "shop không tư vấn được" dù bệnh không nằm trong BENH_PAGE (chủ shop 23/09, ca Grenelyn:
    # "sao lại chối sản phẩm vậy, cứ cái gì tốt là sản phẩm đều hỗ trợ được") — trừ các ca _tha_cau và khi khách / AI
    # đang nói bệnh khác hẳn page (BENH_KHAC: tim, huyết áp…).
    md = DAY_BAC_SI.search(t)
    if md and not BENH_KHAC.search(hoi) and not _tha_cau(t, md, kh, bac_si=True) \
            and md.group(0).lower() not in kb.lower():
        return md.group(0), "đẩy đi bác sĩ"
    # không gọi tên bệnh nào: khách hỏi "thuốc gì / khỏi không" mà AI chối là thuốc (không tính câu bác sĩ)
    # (23/09: xét đúng câu m đã qua _tha_cau, không search lại cả tin — "bukan obat minum" không phải chối)
    if benh_page and PHU_THUOC.search(m.group(0)) and HOI_CHUA.search(kh) \
            and not any(r_ten.search(hoi) for r_ten, _ in BENH_PAGE.values()) and not BENH_KHAC.search(hoi):
        return m.group(0), benh_page[0]
    return None


def benh_page_khach_hoi(cau_khach, kb_page=None, cau_page=None):
    """(tên bệnh, câu khách) khi mấy tin khách gần nhất gọi tên ĐÚNG bệnh page đang bán; không thì None.
    ai_sale dùng để gắn dòng 🩺 vào gói soạn — model tự "thận trọng y tế" mà chối kể cả khi không có khối ❓."""
    kb = None
    for c in reversed([str(x) for x in (cau_khach or [])][-4:]):
        for ten, (r_ten, r_page) in BENH_PAGE.items():
            if r_ten.search(c):
                if kb is None:
                    kb = _chu_kich_ban(kb_page, cau_page)
                if r_page.search(kb):
                    return ten, c
    return None


def phui_qc(t, kb_page=None, cau_khach=None, cau_page=None):
    """Câu phủi quảng cáo (chuỗi) — PHUI_QC hoặc chối công dụng cho bệnh page đang bán; không có thì None."""
    m = _phui_qc_m(str(t or ""), kb_page, cau_page)                 # 23/09: tha câu chép từ kịch bản
    if m:
        return m.group(0)
    pb = phui_benh(t, kb_page, cau_khach, cau_page)
    return pb[0] if pb else None

MA_DON = re.compile(
    r"\b(?:order\s*(?:id|no|number|#)|tracking\s*(?:no|number|id)|ref(?:erence)?\s*(?:no|#)"
    r"|mã\s*đơn|رقم\s*الطلب)\s*[:#]?\s*(?=[A-Z0-9\-]{4,}\b)(?=[A-Z\-]*\d)[A-Z0-9\-]{4,}\b",
    re.I | re.U)
# ⚠️ Mã PHẢI có ít nhất một chữ số. Không có ràng buộc đó thì 52 mẫu thật bị chặn oan vì câu
# "larawan ng TRACKING NUMBER gaya ng ipinapakita" — "gaya" bị đọc thành mã vận đơn.

# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 8 — DÁN LẠI CHECKLIST  (mục 1 + Talpha CORE §4c)
# ══════════════════════════════════════════════════════════════════════════════
# "✓ Họ tên ✓ SĐT ✓ Địa chỉ ✓ Số lượng" — vi phạm đúng cái chủ shop gọi là lỗi nặng nhất:
# hỏi lại cái khách đã cho.
CHECKLIST = re.compile(r"(?:[✓✔•\-\*]\s*\S+[^\n]{0,40}\n){3,}", re.U)
XIN_LAI = re.compile(
    r"(?:full\s*name|pangalan)\b[^\n]{0,60}\n[^\n]{0,60}\b(?:number|mobile|contact)\b",
    re.I | re.U)

# ══════════════════════════════════════════════════════════════════════════════
# LUẬT 9 — KẾT LƯỢT THỤ ĐỘNG  (mục 5b#2 — luật của chính chủ shop)
# ══════════════════════════════════════════════════════════════════════════════
# "LUÔN kết bằng một câu hỏi hướng tới việc mua hàng" là luật cứng trong LUAT_AI_SALE.md
# nhưng chưa có gì đo được nó. Câu không có dấu hỏi + kết bằng lời mời thụ động = thả khách.
THU_DONG = re.compile(
    r"(let\s+me\s+know|feel\s+free\s+to\s+ask|sabihin\s+n?i?y?o\s+lang|just\s+let\s+us\s+know"
    r"|any\s+questions?\s*[.!]?\s*$|thank\s+you\s*[.!]?\s*$|salamat\s*(?:po)?\s*[.!]?\s*$"
    r"|شكرا\s*$)", re.I | re.U)

DAU_HOI = re.compile(r"[?؟]")

# Trần độ dài: mục 5b "ngắn gọn". Talpha hạ max_tokens về 400 để ép model viết 1-3 câu;
# mình chưa hạ trần model nên đo bằng ký tự. 700 ký tự ≈ 5-6 câu — đã là dài với Messenger.
DAI_TOI_DA = 700


# ══════════════════════════════════════════════════════════════════════════════
# CỔNG
# ══════════════════════════════════════════════════════════════════════════════

def _la_mau_cua_shop(t, kb_page, nguong=0.7):
    """Câu này có phải AI đang CHÉP LẠI một mẫu của shop không?

    Ba luật văn phong (phải kết bằng câu hỏi · không dán checklist · ngắn gọn) là luật cho
    câu AI TỰ VIẾT. Mẫu do shop viết thì shop chịu trách nhiệm — bắt AI viết lại mẫu
    /Chaohang hay /Paypal là làm hỏng đúng thứ đang bán được hàng.
    Đo trên 4.824 mẫu thật: 71% mẫu không có dấu hỏi, 8% là danh sách gạch đầu dòng.
    """
    for m in (kb_page or {}).get("mau") or []:
        ds = [x for x in (m.get("tin") or []) if (x or "").strip()]
        # Mẫu Pancake hay gồm NHIỀU PHẦN (page gửi 2-4 tin liền) — 91/271 bước tâm linh là vậy. AI chỉ gửi
        # được 1 tin nên chép cả mẫu là nối các phần lại; so với từng phần thì bản nối chỉ giống ~0,5 và bị
        # coi là AI tự viết → rơi vào cổng "tin quá dài", cắt mất 3/4 bước kịch bản (ca Lee Maria 20/09).
        for mau in ds + (["\n\n".join(ds), "\n".join(ds)] if len(ds) > 1 else []):
            if _giong_nhau(t, mau) >= nguong:
                return True
    return False


def _co_trong_kich_ban(cum, kb_page):
    """Cụm chữ này có thật trong kịch bản của page không?

    Có mới được nói. 59/4.824 mẫu thật CÓ chào khan hiếm ("TODAY ONLY", "First 50 Customers",
    "promotion may end soon") — đó là lời shop tự viết, AI nhắc lại là đúng. Cấm cào bằng là
    cấm AI dùng chính chương trình khuyến mãi của shop.
    """
    if not kb_page:
        return False
    c = re.sub(r"\s+", " ", bo_chu_toan(cum).lower()).strip()
    if not c:
        return False
    for m in kb_page.get("mau") or []:
        for tin in m.get("tin") or []:
            if c in re.sub(r"\s+", " ", bo_chu_toan(tin).lower()):
                return True
    return False


# Hứa gửi ảnh mà lượt này không có ảnh — từ 11/09 ảnh qua API TẮT (Facebook chặn #2022), câu
# "here are the photos" trơ trọi làm khách tưởng bị quên. Chỉ bắt kiểu KHẲNG ĐỊNH đang gửi;
# câu XIN khách gửi ảnh ("could you send a photo") không bắt.
HUA_ANH = re.compile(
    r"\b(here (are|is) (the |some |our )?(photo|photos|picture|pictures|pic|pics|image|images)"
    r"|(sending|sent|attaching|attached) (you )?(the |some )?(photo|photos|picture|pictures|pic|pics|image|images)"
    r"|(photo|photos|picture|pictures|pic|pics) (below|attached)"
    r"|(eto|ito|narito|heto) (na )?(po )?(ang )?(mga )?(larawan|litrato|picture|pictures|pics))\b"
    r"|هذه الصور|إليك الصور|هاي الصور", re.I | re.U)
# Chuỗi số dài kiểu số điện thoại trong câu trả lời — Facebook đọc là dấu hiệu spam; "your number"
# là đủ, không cần đọc lại số. Chỉ NHẮC (vẫn gửi) để đếm, luật chính nằm trong luat_model.md.
SDT_TRONG_CAU = re.compile(r"(?<![\d.,])(\+?\d[\d\s\-().]{6,}\d)(?![\d.,])")


# Thị trường COD: CHỈ tiền mặt trả bưu tá khi nhận hàng — không thẻ, không chuyển khoản, không
# thanh toán online. Chủ shop 11/09 bắt ca NY Nurti Sailan (Kreain Nature UAE): khách "I have card",
# AI bịa "We accept card payment too". Chỉ Mỹ/Úc (thu tiền sau) mới có phương thức theo kịch bản.
THU_TIEN_SAU = ("usa", "australia")
PHUONG_THUC_LA = (r"(credit card|debit card|card payment|bank card|card|visa|mastercard|master card"
                  r"|bank transfer|transfer|online payment|pay online|payment link|apple pay|google pay"
                  r"|tabby|tamara|paypal|gcash)")
NHAN_THANH_TOAN = re.compile(
    r"\b((we|kami|po)\s+)?(also\s+)?(accept|accepts|accepting|take|takes|allow|allows|tumatanggap( kami)?( ng)?|pwede( po)?( ang| ng| mag-?)?)"
    r"\s+(the\s+|a\s+|by\s+|with\s+)?" + PHUONG_THUC_LA
    + r"|" + PHUONG_THUC_LA + r"\s+(payment\s+)?(is|are|po ay|ay)\s+(also\s+)?(accepted|available|ok|okay|fine|welcome|possible|pwede)"
    + r"|(pay|payment|bayad|magbayad)\s+(by|with|via|using|through|thru|sa pamamagitan ng)\s+(the\s+|a\s+|your\s+)?" + PHUONG_THUC_LA
    + r"|(نقبل|يمكنك? الدفع ب|الدفع ب)(البطاقة|بطاقة|فيزا|تحويل)", re.I | re.U)
# Phủ định chỉ tính trong CÙNG MỘT VẾ CÂU (sau dấu . ! ? ; — gần nhất). Bản đầu nhìn lùi 40 ký tự
# và có chữ "no" nên "No problem, dear! We accept card" bị coi là phủ định → lọt đúng ca thật.
PHU_DINH = re.compile(r"\b(don'?t|do not|doesn'?t|does not|not|cannot|can'?t|never|only cash|cash only"
                      r"|hindi|wala|walang|sorry|unfortunately)\b|\bلا\b|غير|\bما\b", re.I | re.U)


def _bia_thanh_toan(t, mkey):
    """Câu nhận thẻ/chuyển khoản/online ở thị trường COD, không kèm phủ định trong cùng vế câu."""
    if (mkey or "") in THU_TIEN_SAU:
        return None
    for m in NHAN_THANH_TOAN.finditer(t):
        truoc = t[max(0, m.start() - 60):m.start()]
        truoc = re.split(r"[.!?;—\n]", truoc)[-1]      # chỉ giữ vế câu đang đứng
        if PHU_DINH.search(truoc):
            continue                                  # "we don't accept card, cash only" — đúng, cho qua
        return m.group(0)
    return None


# Mỹ/Úc KHÔNG phải COD tại cửa (chủ shop 14/09, ca Zeny Abalos Calimquim / Golden Fortune Energy
# Necklace US): khách nhận hàng, xem, rồi mới trả cho SHOP qua Check/Venmo/Zelle… — shipper không thu
# gì. AI chép lối nói COD của vùng Vịnh: "bayad ka na lang sa rider", "hindi nagustuhan → hindi kunin
# at walang babayaran". Đo 14/09: 11/49 tin gửi ở Mỹ dính, cổng cũ cho qua cả 11. Chữ "COD" trần KHÔNG
# bắt — nhiều kịch bản page Mỹ dùng "COD" theo nghĩa trả sau khi nhận.
_NGUOI_GIAO = r"(rider|courier|driver|delivery\s*(man|guy|boy|person|agent)|shipper|postman|mailman|kartero|mensahero)"
_TRA_NGUOI_GIAO = re.compile(
    r"\b(pay|paying|payment|cash|bayad|magbayad|nagbabayad|magbabayad|babayaran|bayaran)\b"
    r"[^.!?\n]{0,40}\b" + _NGUOI_GIAO + r"\b"
    r"|\b" + _NGUOI_GIAO + r"\b[^.!?\n]{0,25}\b(collect|collects|singil|maningil|kolektahin)\b", re.I)
_KHONG_UNG_KHONG_TRA = re.compile(
    r"\bhindi\s+(po\s+)?(niyo|ninyo|mo|kayo|ka)?\s*(po\s+)?(kunin|tanggapin)\b"
    r"|\brefuse\s+(to\s+(accept|receive|take)\s+)?(the\s+|your\s+)?(parcel|package|delivery|order|item)"
    r"|\b(return|give)\s+(it|the\s+(parcel|package|item))\s+(back\s+)?to\s+the\s+(rider|courier|driver)"
    r"|\bonly\s+pay\s+if\b|\bpay\s+only\s+if\b"
    r"|(\bkung\s+(po\s+)?hindi\b|\bif\s+(you\s+)?(don'?t|do\s+not)\s+(like|love)|\bnot\s+satisfied\b|\bif\s+not\b)"
    r"[^.!?\n]{0,50}\b(hindi|walang|don'?t|no\s+need|not)\b[^.!?\n]{0,25}"
    r"\b(kunin|bayaran|babayaran|magbayad|pay|take\s+it|accept\s+it)\b", re.I)


# Mỹ/Úc KHÔNG HẸN GIAO LẠI / KHÔNG CẦN CÓ NHÀ (chủ shop 14/09 tối): bưu tá để hàng ở hộp thư / trước cửa.
# *"hẹn giao lại thì k có, còn ngày hẹn thì vẫn dùng"* — "giao ngày lương / preferred date" VẪN qua. Ca thật:
# Philip Gutib "i-schedule ang delivery sa weekend para andoon ka sa bahay para tanggapin".
HEN_LICH_GIAO = re.compile(
    r"\b(para|so\s+that|so)\s+(ka\s+|kayo\s+|mo\s+)?(andoon|nandoon|nasa\s+bahay|you'?re\s+(at\s+)?home"
    r"|you\s+(can|will|would)\s+be\s+(at\s+)?home|someone\s+(is\s+|will\s+be\s+|can\s+be\s+)?(at\s+)?home)"
    r"|\b(be|stay|are)\s+(at\s+)?home\s+(to|when)\s+(receive|accept|get)"
    r"|\bre-?deliver\w*|\bdeliver\w*\s+(it\s+)?again\b|\b(ihatid|ipadala|hatid)\s+(ulit|muli)\b|\bsecond\s+(delivery\s+)?attempt"
    r"|\b(rider|courier|driver|delivery\s+(man|guy))\s+will\s+(call|contact|text|message)"
    r"|\btatawag(an)?\s+(sa\s+)?(kayo|ka|inyo|iyo)\b[^.!?\n]{0,20}\b(rider|courier)"
    r"|\b(what|which)\s+time\s+(are\s+you|will\s+you\s+be|you'?re)\s+(at\s+)?home"
    r"|\banong\s+oras\b[^.!?\n]{0,25}\b(bahay|andoon|nandoon)\b", re.I)


def _cod_tai_cua(t, mkey):
    """Câu kiểu COD tại cửa ở Mỹ/Úc: trả tiền cho người giao, hoặc không ưng thì khỏi nhận/khỏi trả."""
    if (mkey or "") not in THU_TIEN_SAU:
        return None
    for m in _TRA_NGUOI_GIAO.finditer(t):
        truoc = re.split(r"[.!?;—\n]", t[max(0, m.start() - 60):m.start()])[-1]
        if PHU_DINH.search(truoc):
            continue          # "you don't pay the rider — pay us after" / "hindi kailangang magbayad sa rider" — đúng
        return m.group(0)
    m = _KHONG_UNG_KHONG_TRA.search(t)
    return m.group(0) if m else None


# AI NÓI NHƯ ĐÃ XEM ẢNH khi khách CHƯA gửi ảnh (chủ shop 14/09, ca Vicky Villacortez / Madam Mystic
# Fengshui Expert USA): Botcake vừa xin "📸 I-send mo ang picture ng kanang palad mo", khách chỉ nhắn
# "Ready na ako madam", AI gửi luôn bước đọc chỉ tay "Tiningnan ko ang palad mo…". Chỉ xét khi ai_sale
# báo `khach_chua_gui_anh=True`. Chỉ bắt câu KHẲNG ĐỊNH đã xem — câu nhắc gửi ảnh ("send a photo of your
# palm so Madam can read it") phải qua.
_BIA_XEM_ANH = re.compile(
    r"\b(tiningnan|sinuri|binasa|nakita|napansin|nabasa)\s+ko\s+(ang\s+|sa\s+)?(iyong\s+|inyong\s+|mga\s+)?"
    r"(palad|larawan|litrato|picture|photo|kamay|linya)"
    r"|\b(money|life|heart|fate|love|wealth|career|luck)\s+line\s+(mo|niyo|ninyo)\b"
    r"|\b(bigat|sanga|putol|marka|hadlang)\w*\s+(sa\s+)?(iyong\s+)?(linya|palad)\s+(mo|niyo|ninyo)\b"
    r"|\bi\s+(have\s+)?(looked\s+at|seen|saw|read|checked|examined|studied|analy[sz]ed)\s+your\s+(palm|photo|picture|hand|pic)"
    r"|\byour\s+palm\s+(shows|reveals|tells|has)\b|\bi\s+(can\s+)?(see|saw|noticed?)\s+(in|on)\s+your\s+(palm|photo|picture)",
    re.I)


# AI NHẬN VƠ "hàng CỦA BẠN" khi khách nói đã mua mà POS không có đơn (chủ shop 14/09, ca Juliet
# Delrosario / Golden Buddha Blessings: "may Golden Buddha ka na pala! Maswerte ka…"). Chỉ xét khi
# ai_sale báo `khach_noi_da_mua=True` (khách vừa khẳng định đã mua, và đã qua cửa POS-không-đơn).
_XAC_NHAN_MUA = re.compile(
    r"\b(you(\s+already)?\s+(have|own|bought|got|purchased|received)\b|you'?ve\s+(already\s+)?"
    r"(bought|got|purchased|received)|your\s+(order|purchase|golden\s+buddha|buddha|bracelet|ring|"
    r"charm|amulet|set|item|product|soap|denture|kit)\b|congrat|thank(s|\s+you)\s+for\s+(your\s+)?"
    r"(order|purchase|buying|ordering)|(ka|kayo)\s+na\s+pala\b|may\s+[\w\s'-]{0,40}?\s+(ka|kayo)\s+na\b|"
    r"(hawak|nakuha|natanggap|nabili|nakabili)\s+(mo|niyo|ninyo)\s+na\b|"
    r"(golden\s+buddha|buddha|bracelet|ring|charm|amulet|order|item|set|soap)\s+(mo|niyo|ninyo)\b|"
    r"salamat\s+sa\s+(pag-?order|pagbili|order|pagtangkilik)|شكرا\s+(على|لـ?)\s*(طلبك|شرائك)|طلبك)",
    re.I | re.U)
# Câu HỎI LẠI đúng luật thì cho qua dù có chữ "your order": "which page did you order from?"
_HOI_NHAM_SHOP = re.compile(
    r"(which|what|where)\s+(page|shop|store|seller)|order(ed)?\s+from|did\s+you\s+(order|buy|purchase)|"
    r"(mistaken|confused|mix(ed)?\s+up|another|other|different)\s+(page|shop|store|seller)|"
    r"(saan|san)\s+(mo|ka|kayo|niyo)\s+(nag-?order|umorder|bumili|nakabili|nkbili)|(ibang|iba)\s+(page|shop|tindahan)|"
    r"(nagkamali|namali)|(pangalan|name)\s+(at|and|&)\s+(number|numero)|page\s+(ba|po)|"
    r"صفحة\s+(ثانية|أخرى|اخرى)|متجر\s+(ثاني|آخر|اخر)|من\s+أي\s+(صفحة|متجر)", re.I | re.U)


def kiem(tin, mkey=None, kb_page=None, gia=None, tin_truoc=None, co_anh=False,
         hanh_dong="tra_loi", cho_phep_so=None, khach_noi_da_mua=False, gia_cu_khi_tu_choi=None,
         gia_page_da_bao=None, khach_chua_gui_anh=False, hom_nay=None, khach_hen_qua_han=False,
         cau_page=None, cau_khach=None, khach_viet=False):
    """Soi một câu AI vừa soạn. Trả PhanQuyet.

    tin        — câu định gửi
    mkey       — thị trường ('usa', 'uae'…) để biết tiền tệ và ngôn ngữ bản địa
    kb_page    — kịch bản page (state/<tt>/kich_ban.json[page_id]) — nguồn con số hợp lệ
    gia        — bộ ba giá từ ai_sale.bo_gia(kb_page)
    tin_truoc  — câu AI đã gửi gần nhất trong CHÍNH hội thoại này (chống nhắn lặp)
    co_anh     — lượt này có gửi kèm ảnh không (ảnh trơ là lỗi, ảnh + chữ thì không)
    hanh_dong  — 'tra_loi' | 'tra_loi_treo' | 'len_don' | 'im' | 'treo' | 'xac_minh_nha'
    cho_phep_so— tự truyền tập số hợp lệ, thay cho việc tính lại từ kb_page
    khach_noi_da_mua — khách vừa khẳng định "đã mua từ mình" mà POS không có đơn (ai_sale tính)
    gia_cu_khi_tu_choi — tập giá page đã báo, chỉ truyền khi tin cuối của khách là lời từ chối
    gia_page_da_bao — tập giá Botcake/sale ĐÃ TỰ BÁO cho khách trong hội thoại này: hợp lệ như giá kịch
                      bản và không tính là dưới sàn (page tự nói ra, ca Aruna 14/09 "2 sets 13.9 KWD")
    khach_chua_gui_anh — page vừa xin khách gửi ảnh mà khách chưa gửi (ai_sale tính)
    hom_nay    — ngày chốt để tính HẠN GIỮ ĐƠN (mặc định hôm nay; tự kiểm truyền cố định)
    cau_page / cau_khach — tin Botcake/sale/broadcast và tin khách trong hội thoại (cau_trong_hoi_thoai):
                      chương trình / bảng số lượng-giá page tự nói ra là hợp lệ như kịch bản (luật 3b)
    """
    pq = PhanQuyet(tin or "")
    t = str(tin or "")

    # 'im'/'treo'/'xac_minh_nha' KHÔNG gửi tin — chỉ cần chắc là không có chữ nào lọt ra.
    if hanh_dong in ("im", "treo", "xac_minh_nha"):
        if t.strip():
            pq.them(NANG, "khong_duoc_nhan",
                    f"hành động '{hanh_dong}' KHÔNG được nhắn cho khách, nhưng model có soạn tin")
        return pq

    # ── 1. rỗng ───────────────────────────────────────────────────────────────
    if _rong(t):
        pq.them(NANG, "tin_rong",
                "tin không có chữ nào" + (" — khách sẽ chỉ nhận ảnh trơ" if co_anh else ""))
        return pq                                    # rỗng thì các luật sau vô nghĩa

    # ── 2. lọt tiếng Việt ─────────────────────────────────────────────────────
    if _diem_tieng_viet(t) >= 2 and not khach_viet:        # VIET_2709 — khách TỰ viết tiếng Việt thì được trả lời tiếng Việt
        pq.them(NANG, "lot_tieng_viet",
                "câu có tiếng Việt — tiếng Việt chỉ là hướng dẫn nội bộ, không bao giờ gửi khách")

    # ── 3. bịa tiền ───────────────────────────────────────────────────────────
    duoc = cho_phep_so if cho_phep_so is not None else so_duoc_phep(kb_page, gia)
    da_bao = set(gia_page_da_bao or ())
    if duoc:
        duoc = set(duoc) | da_bao
        la = sorted({v for v in tien_trong(t) if v not in duoc})
        if la:
            pq.them(NANG, "bia_tien",
                    f"nói con số tiền KHÔNG có trong kịch bản page: {la} "
                    f"({TIEN_TE.get(mkey or '', '')}) — nghi tự cộng/nhân giá gói")
        # Ngưỡng là SÀN THẤP NHẤT trong bảng sàn-theo-combo, không phải sàn của một mức.
        # Page bán nhiều combo (SkinPop Glow US: $109 và $149) thì mỗi combo một sàn ($99, $139);
        # chặn theo sàn của combo đắt là chặn oan AI báo đúng giá combo rẻ.
        nguong = (gia or {}).get("san_thap_nhat") or (gia or {}).get("gia_san")
        if nguong:
            # đơn giá "79,5 AED each" suy từ gói 2 chai 159 đương nhiên thấp hơn sàn 1 chai —
            # không phải chào dưới sàn
            dg = don_gia_suy_ra(kb_page)
            duoi = [v for v in tien_trong(t) if 0 < v < nguong and v not in dg and v not in da_bao]
            if duoi:
                pq.them(NANG, "duoi_gia_san",
                        f"chào giá {duoi} thấp hơn sàn thấp nhất của page ({nguong}) — "
                        f"mục 4, phải treo cho sale")

    # ── 3b. gói / số lượng lệch bảng giá (ca Shaallyn 19/09) ─────────────────
    if kb_page:
        km_la = bia_khuyen_mai(t, kb_page, cau_page, cau_khach)
        if km_la:
            pq.them(NANG, "bia_goi",
                    f"nói chương trình {', '.join(f'mua {a} tặng {b}' for a, b in sorted(km_la))} mà kịch bản lẫn "
                    f"tin page KHÔNG có — gọi gói đúng chữ bảng giá (chủ shop 19/09: 'chương trình mua 1, làm gì có tặng 1')")
        for n, P, dung, cua in sai_gia_so_luong(t, kb_page, cau_page):
            pq.them(NANG, "sai_gia_sl",
                    f"ghép {n} đơn vị với giá {P:g} — bảng giá: {n} đơn vị = {'/'.join(f'{x:g}' for x in dung)}, "
                    f"còn {P:g} là giá của {'/'.join(map(str, cua))} đơn vị")
            break
        for goi, P, dung, cua in sai_gia_goi(t, kb_page, cau_page):
            pq.them(NANG, "sai_gia_goi",
                    f"gán giá {P:g} cho gói mua {goi[0]} tặng {goi[1]} — "
                    + (f"bảng giá gói đó là {'/'.join(f'{x:g}' for x in dung)}" if dung else "page KHÔNG có gói đó")
                    + f", còn {P:g} là giá gói {', '.join(f'mua {a} tặng {b}' for a, b in cua)}")
            break

    # ── 4-7. bịa cam kết / doạ / lộ nội bộ / bịa mã đơn ───────────────────────
    kh = khan_hiem_bia(t, kb_page)          # 24/09: so ý theo NHÓM (hạn chót / mất suất) — xem khan_hiem_bia
    if kh:
        # So Ý chứ không so CHỮ. Chặn oan thật 2026-09-10 (Emma Lapastora, Skin Renew UAE):
        # kịch bản page viết "promotion will end at 11 PM today", AI viết "hurry, the offer
        # ends at 11 PM today" — bản cũ đi tìm đúng chữ 'hurry' trong kịch bản, không thấy,
        # chặn. Khách hỏi rồi không được trả lời. Giờ: page có dùng khan hiếm/hạn chót thì AI
        # được nói theo cách của nó; page KHÔNG có thì mới là bịa.
        pq.them(NANG, "bia_khan_hiem",
                f"hứa khan hiếm — {kh[0]} ({kh[1].group(0)!r}) mà kịch bản page KHÔNG có câu cùng loại")
    ch = CUA_HANG.search(t)
    if ch and not _kich_ban_co_cua_hang(kb_page):
        pq.them(NANG, "bia_cua_hang",
                f"khẳng định về cửa hàng/địa điểm/xuất xứ ({ch.group(0)!r}) mà kịch bản page KHÔNG nói")
    if DOA.search(t):
        pq.them(NANG, "doa_khach", "câu mang tính doạ khách — một lần report là mất page")
    if KY_TU_AN.search(t):
        pq.them(NANG, "ky_tu_an", "có ký tự Unicode vô hình (dấu hiệu né bộ lọc trùng của Meta)")
    if NOI_BO.search(t):
        pq.them(NANG, "lo_noi_bo", "để lộ chuyện nội bộ (bot/kịch bản/việc tra địa chỉ)")
    if MA_DON.search(t):
        pq.them(NANG, "bia_ma_don", "đọc mã đơn cho khách — AI không có mã thật, đây là bịa")
    pq_qc = _phui_qc_m(t, kb_page, cau_page)                        # 23/09: tha câu chép từ kịch bản
    if pq_qc:
        pq.them(NANG, "phui_quang_cao",
                f"đính chính / phủ nhận quảng cáo của chính page ({pq_qc.group(0)!r}) — luật 12/09: "
                f"bắc cầu về công dụng có trong kịch bản rồi chốt, không được cãi lại quảng cáo")
    else:
        _pb = phui_benh(t, kb_page, cau_khach, cau_page)
        if _pb:
            pq.them(NANG, "phui_quang_cao",
                    f"chối công dụng cho CHÍNH bệnh page đang bán ({_pb[1]}: {_pb[0]!r}) — kịch bản tả đúng vùng / "
                    f"triệu chứng, chỉ không gọi tên vì luật Facebook (ca Namzuged 19/09)")

    _cm = CAN_MUA.search(t)
    if _cm:
        pq.them(NANG, "can_mua",
                f"câu này CẢN khách mua ({_cm.group(0)!r}) — khách hỏi có phải mua không thì đáp CÓ + giá trị, "
                f"không bao giờ nói 'đừng vội mua / không chỉ là mua' (chủ shop 14/09, ca Lucy JJ)")
    # ── 8-9. VĂN PHONG — chỉ soi câu AI TỰ VIẾT, không soi mẫu shop chép lại ──
    # ── 7b. bịa phương thức thanh toán ở thị trường COD (luật 11/09) ──────────
    if gia_cu_khi_tu_choi and set(tien_trong(t)) & set(gia_cu_khi_tu_choi):
        pq.them(NANG, "bao_gia_lai",
                "khách vừa từ chối sau khi ĐÃ BIẾT GIÁ mà câu này báo lại giá cũ — phải níu (hỏi lý do + "
                "lý lẽ), không đọc lại bảng giá (chủ shop 14/09, ca Fe Borabo)")
    if khach_chua_gui_anh:
        m_xa = _BIA_XEM_ANH.search(t)
        if m_xa:
            pq.them(NANG, "bia_xem_anh",
                    f"khách CHƯA gửi ảnh mà câu này nói như đã xem ({m_xa.group(0)!r}) — phải nhắc khách "
                    f"gửi ảnh trước, không đọc chỉ tay / gửi bước kế (chủ shop 14/09, ca Vicky)")
    if khach_noi_da_mua and _XAC_NHAN_MUA.search(t) and not _HOI_NHAM_SHOP.search(t):
        pq.them(NANG, "nhan_vo_da_mua",
                "khách nói đã mua nhưng POS không có đơn — câu này nhận vơ hàng của khách là của "
                "mình; phải hỏi lại khách đặt ở page nào / tên + SĐT lúc đặt (có thể nhầm shop)")
    # ── 7c. hứa giao QUÁ HẠN GIỮ ĐƠN 1 tháng (chủ shop 14/09, ca Jessica "February 24") ──
    # Câu nói ngày quá hạn mà KHÔNG kèm ngày nào trong hạn = nhận lời khách. Câu từ chối đúng luật
    # ("we can't wait until February — we hold it only until October 31") có ngày trong hạn → qua.
    qh = hua_giao_qua_han(t, hom_nay, kb_page, mkey)
    _bh = BAO_HAN.search(t) if not khach_hen_qua_han else None
    if _bh:
        pq.them(NANG, "bao_han_som",
                f"nói trước hạn giữ đơn ({_bh.group(0)!r}) khi khách chưa hẹn ngày quá hạn — để khách tự chọn ngày "
                f"nhận, chỉ báo hạn khi ngày khách nêu quá hạn")
    if qh:
        pq.them(NANG, "hen_qua_han",
                f"nhận giao ngày {qh:%d/%m/%Y} — quá hạn giữ đơn (hết {han_giu_don(hom_nay, mkey):%d/%m/%Y}); shop chỉ "
                f"giữ đơn {so_thang_giu_don(mkey)} tháng từ ngày chốt, phải xin khách chọn ngày trong hạn")
    # ── 7d. hứa giao SỚM hơn thời gian giao thật (chủ shop 14/09 tối, ca Wahida "deliver tomorrow") ──
    hs = hua_giao_som(t, hom_nay, mkey, kb_page)
    if hs:
        lo, hi, _ng = thoi_gian_giao(mkey, kb_page)
        pq.them(NANG, "hua_giao_som",
                f"hứa giao quá sớm ({hs!r}) — hàng mất {lo}-{hi} ngày (không tính cuối tuần/lễ), không "
                f"thị trường nào giao hôm nay/ngày mai; nói đúng thời gian giao, không nhận lời khách")
    bia_tt = _bia_thanh_toan(t, mkey)
    if bia_tt:
        pq.them(NANG, "bia_thanh_toan",
                f"nói nhận '{bia_tt}' — thị trường COD chỉ nhận TIỀN MẶT trả bưu tá; khách không có "
                f"tiền mặt thì nói rõ và hẹn giao lúc có tiền mặt, không được hứa thẻ/chuyển khoản")
    if (mkey or "") in THU_TIEN_SAU:
        _hl = HEN_LICH_GIAO.search(t)
        if _hl:
            pq.them(NANG, "hen_lich_giao",
                    f"hẹn giao để khách có nhà / giao lại ({_hl.group(0)!r}) — thị trường {mkey} bưu tá để hàng ở hộp "
                    f"thư/trước cửa, không cần ai ở nhà, không gọi trước, không giao lại (ngày hẹn theo ngày lương thì được)")
    cod_cua = _cod_tai_cua(t, mkey)
    if cod_cua:
        pq.them(NANG, "cod_tai_cua",
                f"nói {cod_cua!r} — thị trường {mkey} KHÔNG thu tiền tại cửa: khách nhận hàng, xem, rồi "
                f"mới trả cho SHOP qua Check/Venmo/Zelle…; không nhắc trả rider, không hứa không ưng thì khỏi trả")

    # ── 8. hứa ảnh mà không có ảnh (luật 11/09) ─────────────────────────────
    if not co_anh and HUA_ANH.search(t):
        pq.them(NHE, "hua_anh", "câu nói đang gửi ảnh nhưng lượt này KHÔNG có ảnh nào "
                                "(ảnh qua API đang tắt) — viết lại, không hứa ảnh")
    # ── 9. đọc lại số điện thoại của khách (luật 11/09) ─────────────────────
    for m_sdt in SDT_TRONG_CAU.finditer(t):
        if len(re.sub(r"\D", "", m_sdt.group(1))) >= 8:
            pq.them(NHAC, "lap_sdt", "lặp lại số điện thoại trong câu trả lời — 'your number' là đủ "
                                     "(chuỗi số dài là dấu hiệu spam với Facebook)")
            break

    muc_vp = NHAC if _la_mau_cua_shop(t, kb_page) else NHE
    if CHECKLIST.search(t) or XIN_LAI.search(t):
        pq.them(muc_vp, "dan_checklist",
                "dán lại danh sách thông tin cần xin — mục 1 cấm hỏi lại cái khách đã cho")

    if len(t) > DAI_TOI_DA:
        # Chỉ NHẮC, không bắt viết lại: 3,3% mẫu kịch bản thật cũng dài hơn ngưỡng này
        # (hướng dẫn thanh toán, mô tả thành phần) và chúng dài có lý do.
        pq.them(NHAC, "qua_dai", f"{len(t)} ký tự — mục 5b yêu cầu ngắn gọn")
    # 'tra_loi_treo' = rep 1 câu rồi giao sale (chủ shop chốt 2026-09-12): câu bàn giao
    # KHÔNG được kết bằng câu hỏi chốt đơn — hỏi tiếp là lại mở thêm một vòng cãi nhau.
    if not DAU_HOI.search(t) and hanh_dong not in ("len_don", "tra_loi_treo"):
        pq.them(muc_vp, "khong_chot",
                "không có câu hỏi nào — mục 5b#2: mọi tin phải kết bằng câu hỏi hướng tới mua hàng")
    elif THU_DONG.search(t.strip()) and not DAU_HOI.search(t.strip()[-60:]):
        pq.them(muc_vp, "ket_thu_dong", "kết lượt bằng câu chờ đợi thụ động — mục 5b#2")

    # ── 10. nhắn lặp ──────────────────────────────────────────────────────────
    if tin_truoc:
        g = _giong_nhau(t, tin_truoc)
        if g >= 0.85:
            pq.them(NANG, "nhan_lap",
                    f"gần trùng câu AI vừa gửi ({g:.0%}) — khách nhận hai tin giống nhau")
        elif g >= 0.65:
            pq.them(NHE, "hoi_lap", f"lặp ý câu trước ({g:.0%}) — mục 4: mỗi lần một góc khác")

    return pq


# HẠN GIỮ ĐƠN 1 THÁNG — chủ shop 2026-09-14, ca Jessica Dongon (Meco Jewelry Kuwait): khách "February
# po sir" (đợi lương tháng 2 NĂM SAU), AI đáp "I-schedule ko na po ang delivery sa February 24" và lên
# đơn. *"khách hẹn tận tháng 2 năm sau bạn cũng ok à, như vậy tôi lấy đâu ra đơn hàng … bảo khách chỉ
# nhận giữ đơn hàng trong vòng 1 tháng kể từ ngày chốt đơn, ví dụ đến hết tháng 10"* (nói ngày 14/09).
# Hạn = NGÀY CUỐI của tháng liền sau tháng chốt (14/09 → 31/10) — theo đúng ví dụ của chủ shop.
# Bộ đọc ngày dùng chung cho ai_sale (khách hẹn ngày nào) và cổng chặn (AI hứa giao ngày nào).
_THANG_TEN = [
    (1, r"january|jan|enero|يناير|كانون الثاني"), (2, r"february|feb|pebrero|febrero|فبراير|شباط"),
    (3, r"march|marso|مارس|آذار"), (4, r"april|apr|abril|أبريل|ابريل|إبريل|نيسان"),
    (5, r"mayo|مايو|أيار"), (6, r"june|hunyo|junio|يونيو|يونيه|حزيران"),
    (7, r"july|hulyo|julio|يوليو|يوليه|تموز"), (8, r"august|aug|agosto|أغسطس|اغسطس|آب"),
    (9, r"september|sept|sep|setyembre|septyembre|septiembre|سبتمبر|أيلول"),
    (10, r"october|oktober|oktobre|oktubre|octubre|oct|okt|أكتوبر|اكتوبر|تشرين الأول"),
    (11, r"november|nov|nobyembre|noviembre|نوفمبر|تشرين الثاني"),
    (12, r"december|dec|disyembre|diciembre|ديسمبر|كانون الأول"),
]
# Chữ ngắn dễ trùng từ thường CHỈ tính khi dính số ngày ("jun 5"). KHÔNG có "may": tiếng Tagalog
# "may 3-digit combination", "May 4 beautiful colors" (= có) — quét 6.520 mẫu kịch bản 14/09 bắt oan 9 mẫu.
_THANG_CAN_SO = [(3, r"mar"), (6, r"jun"), (7, r"jul")]


def _ten_thang(ds, tien_to):
    return "|".join(f"(?P<{tien_to}{m}_{i}>{p})" for i, (m, p) in enumerate(ds))


_KHONG_PHAI_NGAY = r"(?!\s*-?\s*(?:birth\s*-?\s*stones?|stones?|sets?|collection|edition)\b)"   # "July Birthstone Set"
_B = r"(?<![A-Za-z؀-ۿ])"   # biên chữ chạy được cả tiếng Ả Rập (\b không ổn với Unicode ghép)
_E = r"(?![A-Za-z؀-ۿ])"
_THANG_RE = re.compile(
    r"(?:(?P<d1>\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+|ng\s+|de\s+)?" + _B + "(?:" + _ten_thang(_THANG_TEN + _THANG_CAN_SO, "a") + ")" + _E + _KHONG_PHAI_NGAY +
    r"|" + _B + "(?:" + _ten_thang(_THANG_TEN, "b") + ")" + _E + _KHONG_PHAI_NGAY + r"\.?\s*(?P<d2>\d{1,2})?(?:st|nd|rd|th)?(?!\d)"
    r"|" + _B + "(?:" + _ten_thang(_THANG_CAN_SO, "c") + r")\.?\s+(?P<d3>\d{1,2})(?:st|nd|rd|th)?(?!\d))", re.I | re.U)
_THANG_ZH = re.compile(r"(\d{1,2})\s*月(?:\s*(\d{1,2})\s*[日号號])?")
# Số dd/mm CHỈ tính khi có năm (24/02/2027): "1/3 ang presyo", "24/7" trong kịch bản không phải ngày.
_NGAY_SO = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(\d{2,4})(?![\d/])")
_NAM = re.compile(r"(?<!\d)(20\d\d)(?!\d)")
_NAM_SAU = re.compile(r"\bnext\s+year\b|susunod\s+na\s+taon|sa\s+sunod\s+na\s+tuig|السنة\s+(?:الجاية|الجاي|القادمة)|"
                      r"العام\s+(?:القادم|الجاي)|明年", re.I | re.U)
_THANG_SAU = re.compile(r"\bnext\s+month\b|susunod\s+na\s+buwan|الشهر\s+(?:الجاي|القادم)|下個月|下个月", re.I | re.U)
_SO_CHU = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "dalawa": 2, "tatlo": 3, "apat": 4, "lima": 5}
_NHIEU_THANG = re.compile(r"\b(?:after|in)\s+(\d+|two|three|four|five|six)\s+months?\b|"
                          r"\b(\d+|dalawa|tatlo|apat|lima)\s*(?:na\s+)?(?:months?|buwan)\b|"
                          r"بعد\s+(?:شهرين|ثلاث(?:ة)?\s+(?:شهور|اشهر|أشهر))", re.I | re.U)


# Mỹ/Úc giữ đơn 2 tháng (chủ shop 14/09 tối: *"ở mỹ thì cho hẹn trong vòng 2 tháng nhé là 31/11"* — tháng 11 chỉ
# có 30 ngày → hết 30/11). Nước khác 1 tháng.
GIU_DON_THANG = {"usa": 2, "australia": 2}


def so_thang_giu_don(mkey=None):
    return GIU_DON_THANG.get(mkey or "", 1)


# NÓI TRƯỚC HẠN GIỮ ĐƠN (chủ shop 14/09 tối): *"phải để khách trả lời xem muốn nhận ngày nào trước, đến khi quá
# thời gian mới báo khách. chứ k phải là tôi giữ đơn cho bạn 1 tháng, 2 tháng ngay từ đầu"*. Ca: Celona (UAE, đã hẹn
# ngày 28 mà AI thêm "promo price hanggang October 31 lang ma-hold"), Cleofa (TW), Beck ("reserve the promo until end
# of month"). Đo 1.853 tin gửi: bắt 5 — 3 ca trên + 2 tin Jessica (khách đã hẹn tháng 2 → cờ khach_hen_qua_han miễn).
# Không bắt "hanggang 11pm", "until 11 PM today", "within 1 month of use".
_TH_BH = (r"(january|february|march|april|may|june|july|august|september|october|november|december"
          r"|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec|enero|febrero|marso|abril|mayo|hunyo|hulyo|agosto"
          r"|setyembre|oktubre|nobyembre|disyembre)")
BAO_HAN = re.compile(
    r"\b(hold|held|i-?hold|ma-?hold|reserv\w*|i-?reserve|keep|kept|save|valid|available|good)\b[^.!?\n]{0,50}"
    r"\b(until|till|til|up\s+to|hanggang|only\s+until)\s+(the\s+)?(end\s+of\s+(the\s+|this\s+|next\s+)?month|" + _TH_BH + r"\b)"
    r"|\bhanggang\s+" + _TH_BH + r"\s*\d{0,2}\s+(lang|only)\b"
    r"|\b(only|just)\s+(hold|keep|reserve)\w*\b[^.!?\n]{0,30}\b(for\s+)?(1|one|2|two)\s+months?"
    r"|\b(hold|keep|reserve)\w*\b[^.!?\n]{0,30}\b(within|for)\s+(1|one|2|two)\s+months?"
    r"|\b(before|bago)\s+(that\s+date|the\s+deadline|" + _TH_BH + r"\s+(30|31)\b)"
    r"|\bpromo\s+price\b[^.!?\n]{0,30}\b(until|hanggang)\s+" + _TH_BH, re.I)


def han_giu_don(hom_nay=None, mkey=None):
    """Ngày cuối cùng shop còn giữ đơn: cuối tháng thứ N sau tháng chốt — N=1 (14/09 → 31/10), Mỹ/Úc N=2 (→ 30/11)."""
    d = hom_nay or date.today()
    t = d.month + so_thang_giu_don(mkey)          # tháng hạn (có thể > 12)
    y, m = d.year + (t - 1) // 12, (t - 1) % 12 + 1
    dau_thang_ke = date(y + (m == 12), m % 12 + 1, 1)
    return dau_thang_ke - timedelta(days=1)


def _ngay_hop_le(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


# Tháng KHÔNG kèm ngày trong câu AI chỉ tính khi có giới từ đứng trước ("sa February", "in February",
# "until February") — "Hi Febrero" (tên khách), "Hi June", "August Peridot" không phải lịch giao.
_GIOI_TU_THANG = re.compile(r"(?:\b(?:sa|in|on|until|till|by|before|after|this|next|come|ng|hanggang|pagdating\s+ng|"
                            r"bago|early|mid|late|end\s+of)|في|بعد|قبل|حتى|شهر)\s*$", re.I | re.U)


def ngay_trong_cau(t, hom_nay=None, can_gioi_tu=False):
    """Mọi ngày (date) đọc được trong câu, đã suy năm. Tháng không kèm ngày → ngày 1 của tháng đó
    (sớm nhất có thể: tháng 1 đã quá hạn thì cả tháng quá hạn). Tháng nhỏ hơn tháng hiện tại, không
    ghi năm → năm sau ("February" nói ngày 14/09 = 02/2027). Không đọc số trơn ("on the 25th") vì
    ngày trong tháng này/tháng sau luôn còn trong hạn.
    can_gioi_tu — cổng soi câu AI: tháng trơn phải có giới từ đứng trước mới tính (khách thì cứ tính)."""
    t = str(t or "")
    hn = hom_nay or date.today()
    nam = _NAM.search(t)
    nam = int(nam.group(1)) if nam else None
    ra = []

    def _them(m, d):
        y = nam or (hn.year + 1 if m < hn.month else hn.year)
        v = _ngay_hop_le(y, m, d or 1)
        if v:
            ra.append(v)

    for mo in _THANG_RE.finditer(t):
        thang = next(int(k[1:].split("_")[0]) for k, v in mo.groupdict().items() if v and k[0] in "abc")
        ngay = mo.group("d1") or mo.group("d2") or mo.group("d3")
        if can_gioi_tu and not ngay and not _GIOI_TU_THANG.search(t[:mo.start()]):
            continue
        _them(thang, int(ngay) if ngay else None)
    for mo in _THANG_ZH.finditer(t):
        if 1 <= int(mo.group(1)) <= 12:
            _them(int(mo.group(1)), int(mo.group(2)) if mo.group(2) else None)
    for mo in _NGAY_SO.finditer(t):   # dd/mm — Philippines, vùng Vịnh, Đài Loan viết ngày trước
        d, m = int(mo.group(1)), int(mo.group(2))
        y = int(mo.group(3))
        v = _ngay_hop_le(y + 2000 if y < 100 else y, m, d)
        if v:
            ra.append(v)
    if _NAM_SAU.search(t):
        ra.append(date(hn.year + 1, 1, 1))
    if _THANG_SAU.search(t):   # "next month" là ngày TRONG hạn — khách đổi ý thì thôi kéo câu cũ (ca Jessica "Oktober")
        ra.append(han_giu_don(hn).replace(day=1))
    for mo in _NHIEU_THANG.finditer(t):
        g = (mo.group(1) or mo.group(2) or "").lower()
        so = int(g) if g.isdigit() else _SO_CHU.get(g, 2 if not g else 0)
        if so >= 2:
            ra.append(hn + timedelta(days=31 * so))
    return ra


def ngay_qua_han(t, hom_nay=None, mkey=None):
    """Ngày muộn nhất trong câu nếu nó QUÁ hạn giữ đơn, không thì None."""
    ds = ngay_trong_cau(t, hom_nay)
    han = han_giu_don(hom_nay, mkey)
    muon = max(ds) if ds else None
    return muon if muon and muon > han else None


# Câu có nói chuyện GIAO/HẸN — cổng chỉ soi ngày trong những câu này: kịch bản page đá tháng sinh
# ("Month of January set ang aming best-seller"), "after 3 months" trong quảng cáo giảm cân không phải lịch giao.
_GIAO = re.compile(
    r"\b(deliver\w*|schedul\w*|i-?schedule|book\w*|ship\w*|arriv\w*|rider|courier|hatid\w*|ihatid|dating|"
    r"padala|reserv\w*|hold|receive|matanggap|tanggap\w*|wait|payday|salary|sweldo|suweldo|sahod)\b|"
    r"توصيل|نوصل|يوصل|يوصلك|موعد|راتب|送達|到貨|配送|寄出", re.I | re.U)


def hua_giao_qua_han(t, hom_nay=None, kb_page=None, mkey=None):
    """Câu AI có HẸN GIAO vào ngày quá hạn giữ đơn không? Trả ngày đó hoặc None.

    Chỉ ngày nằm trong câu nói chuyện giao/hẹn. Câu có kèm bất kỳ ngày nào TRONG hạn thì coi là đang
    từ chối đúng luật ("can't wait until February — we hold it only until October 31") → None.
    Chép nguyên mẫu của shop thì không đụng."""
    t = str(t or "")
    if not t or (kb_page and _la_mau_cua_shop(t, kb_page)):
        return None
    han = han_giu_don(hom_nay, mkey)
    if any(d <= han for d in ngay_trong_cau(t, hom_nay, True)):
        return None
    ds = [d for c in re.split(r"(?<=[.!?。！？])\s+|\n+", t) if _GIAO.search(c) for d in ngay_trong_cau(c, hom_nay, True)]
    return max(ds) if ds and max(ds) > han else None


# THỜI GIAN GIAO HÀNG — chủ shop chốt 2026-09-23: *"thời gian giao hàng ở saudi là 3-7 ngày, còn lại các nước là 2-5 ngày"*,
# *"đài và mỹ thì thời gian theo kịch bản page nhé"* (Úc đi chung shop Mỹ).
# Trước đó (14/09, ca Wahida) ưu tiên "page đã nói trong hội thoại" > kịch bản > mặc định cho MỌI nước, và khoang_ngay_trong
# bắt MỌI cụm "N–M days" không xét ngữ cảnh → ca Hanah (Healthy Figure PH in Saudi, 23/09 20:29 VN): mẫu chào hàng Botcake
# "Lumiit ang tiyan at bewang (7–10 days pa lang may changes na)" = thời gian THẤY KẾT QUẢ bị lấy làm ngày giao, khối 🚚 ghi
# 7-10, AI rep "Mga 7-10 days po ang delivery". Nay: Saudi + các nước Vịnh = số cố định; Đài/Mỹ = khoảng NÓI VỀ GIAO HÀNG hay
# gặp nhất trong kịch bản page (khoang_ngay_giao_trong), không đọc tin hội thoại nữa; kịch bản không ghi → mặc định dưới.
THOI_GIAN_GIAO = {"saudi": (3, 7)}
THOI_GIAN_GIAO_MAC_DINH = (2, 5)      # uae, kuwait, qatar, oman, bahrain và mọi thị trường khác
THEO_KICH_BAN = {"taiwan": (3, 7), "usa": (5, 10)}   # số theo kịch bản page; giá trị = mặc định khi kịch bản không ghi
_SO_NGAY = re.compile(
    r"(?<![\d.,])(\d{1,2})\s*(?:-|–|—|~|to|or|hanggang|至|到)\s*(\d{1,2})\s*(?:working\s+|business\s+)?"
    r"(?:days?|araw|أيام|ايام|يوم|天|日)", re.I | re.U)


def khoang_ngay_trong(t):
    """Khoảng "2-5 days" / "5–10 araw" / "2-5 أيام" đầu tiên trong câu → (lo, hi), không có thì None."""
    for mo in _SO_NGAY.finditer(str(t or "")):
        lo, hi = int(mo.group(1)), int(mo.group(2))
        if 1 <= lo <= hi <= 30:
            return lo, hi
    return None


# Từ GIAO HÀNG / từ KẾT QUẢ — để phân biệt "delivery takes 2-5 days" với "see changes in 7–10 days", "30 days supply".
_TU_GIAO_HANG = re.compile(
    r"\b(?:deliver\w*|ship\w*|arriv\w*|receiv\w*|dispatch\w*|courier|rider|parcel|reach\w*|ihatid|hatid\w*|maihatid|"
    r"dating|darating|makarating|matanggap|matatanggap|makuha|padala|ipadala)\b|"
    r"توصيل|التوصيل|نوصل|يوصل|يوصلك|يوصلكم|توصلك|تستلم|استلام|الشحن|يصل|يصلك|送達|到貨|配送|寄出|送到|收到|出貨", re.I | re.U)
_KET_QUA_NGAY = re.compile(
    r"\b(?:result\w*|change\w*|effect\w*|feel\w*|see|notice\w*|lighter|slimmer|improve\w*|visible|supply|use|using|"
    r"consum\w*|treatment|course|wear\w*|pagbabago|resulta|mapapansin|pumayat|payat|lumiit|magbago|epekto|gumaan|ramdam|"
    r"mararamdaman|inom|uminom|gamit|gamitin)\b|نتيجة|نتائج|تحسن|تلاحظ|استخدام|效果|改善|使用|見效|见效", re.I | re.U)
_DAU_CAU = ".!?\n。！؟"


def _bien_cau(t, mo):
    """(đầu, cuối) của câu chứa cụm khớp mo trong t."""
    d = max((t.rfind(x, 0, mo.start()) for x in _DAU_CAU), default=-1) + 1
    c = min([i for i in (t.find(x, mo.end()) for x in _DAU_CAU) if i >= 0] + [len(t)])
    return d, c


def _la_khoang_giao(t, mo):
    a, b = int(mo.group(1)), int(mo.group(2))
    if not (1 <= a <= b <= 30):
        return False
    d, c = _bien_cau(t, mo)
    if not _TU_GIAO_HANG.search(t[d:c]):
        return False
    return not (_KET_QUA_NGAY.search(t[max(d, mo.start() - 45):mo.start()])
                or _KET_QUA_NGAY.search(t[mo.end():min(c, mo.end() + 25)]))


def khoang_ngay_giao_trong(t):
    """Khoảng "N-M days" NÓI VỀ GIAO HÀNG đầu tiên trong t → (lo, hi); cụm về kết quả / dùng hàng bỏ qua; không có → None."""
    t = str(t or "")
    for mo in _SO_NGAY.finditer(t):
        if _la_khoang_giao(t, mo):
            return int(mo.group(1)), int(mo.group(2))
    return None


def khoang_giao_kich_ban(kb_page):
    """{(lo, hi): số mẫu} — các khoảng ngày GIAO trong kịch bản page."""
    dem = {}
    for m in (kb_page or {}).get("mau") or []:
        for tin in m.get("tin") or []:
            k = khoang_ngay_giao_trong(tin)
            if k:
                dem[k] = dem.get(k, 0) + 1
    return dem


def thoi_gian_giao(mkey=None, kb_page=None, cau_page=None):
    """(lo, hi, nguồn) — số ngày giao. Saudi / Vịnh: bảng cố định (chủ shop 23/09). Đài / Mỹ: khoảng giao hàng hay gặp nhất
    trong kịch bản page, không ghi thì mặc định THEO_KICH_BAN. cau_page giữ cho tương thích, KHÔNG dùng nữa."""
    mk = (mkey or "").lower()
    if mk in THEO_KICH_BAN:
        dem = khoang_giao_kich_ban(kb_page)
        if dem:
            k = max(dem, key=lambda x: (dem[x], x[0]))
            return k[0], k[1], "kịch bản page"
        lo, hi = THEO_KICH_BAN[mk]
        return lo, hi, "kịch bản page không ghi — mặc định thị trường"
    lo, hi = THOI_GIAN_GIAO.get(mk, THOI_GIAN_GIAO_MAC_DINH)
    return lo, hi, "chủ shop chốt theo thị trường"


def khoang_cho_phep(mkey=None, kb_page=None):
    """Tập (lo, hi) AI được nói: số của thị trường; Đài/Mỹ thêm mọi khoảng giao có trong kịch bản page."""
    lo, hi, _ = thoi_gian_giao(mkey, kb_page)
    cp = {(lo, hi)}
    if (mkey or "").lower() in THEO_KICH_BAN:
        cp |= set(khoang_giao_kich_ban(kb_page))
    return cp


def sua_so_ngay_giao(t, lo, hi, cho_phep=None):
    """Câu AI nói "N-M days" về GIAO HÀNG mà không nằm trong cho_phep → CODE thay bằng lo-hi (không gọi model, không chặn).
    Ca Hanah 23/09 (trên). Trả (tin mới, [(cũ, mới)…])."""
    t = str(t or "")
    cp = set(cho_phep or ()) | {(lo, hi)}
    doi = []

    def _thay(mo):
        if (int(mo.group(1)), int(mo.group(2))) in cp or not _la_khoang_giao(t, mo):
            return mo.group(0)
        moi = f"{lo}-{hi}" + mo.group(0)[mo.end(2) - mo.start():]
        doi.append((mo.group(0), moi))
        return moi

    return _SO_NGAY.sub(_thay, t), doi


_SOM_TU = r"tomorrow|tmrw|tomorow|tonight|bukas|same[\s-]*day|next[\s-]*day|within\s+24\s*h\w*|in\s+24\s*h\w*"
_GIAO_DT = (r"deliver\w*|ship\w*|arriv\w*|receiv\w*|dispatch\w*|ihatid|hatid\w*|maihatid|dating|darating|"
            r"matanggap|matatanggap|natanggap")
_GIAO_SOM = re.compile(
    r"\b(?:" + _GIAO_DT + r"|schedul\w*|i-?schedule|book\w*|arrang\w*)\b[^.!?\n]{0,40}?\b(?:" + _SOM_TU + r")\b"
    # "today" chỉ đi với động từ NHẬN/TỚI — "FREE SHIPPING TODAY ONLY" / "free delivery today" là khuyến mãi của page
    r"|(?<!free\s)\b(?:deliver(?:ed|s)?|arriv\w*|receiv\w*|ihatid|hatid\w*|dating|darating|matanggap|matatanggap)\b"
    r"[^.!?\n]{0,25}?\b(?:today|ngayong\s+araw)\b(?!\s*only)"
    r"|\b(?:" + _SOM_TU + r")\b[^.!?\n]{0,25}?\b(?:" + _GIAO_DT + r")\b"
    r"|(?:توصيل|نوصل|يوصل|يوصلك|يوصلكم|توصلك|تستلم|استلام)[^.!؟\n]{0,30}?(?:بكرة|بكره|غدا|غدًا|غداً|باچر|باكر|اليوم)"
    r"|(?:بكرة|بكره|غدا|غدًا|غداً|باچر|باكر)[^.!؟\n]{0,20}?(?:توصيل|نوصل|يوصل|يوصلك|تستلم)"
    r"|(?:明天|今天|明日|今日)[^。！？\n]{0,8}?(?:送達|到貨|配送|寄出|送到|收到)"
    r"|(?:送達|到貨|配送|送到|收到)[^。！？\n]{0,8}?(?:明天|今天|明日)", re.I | re.U)
# Câu TỪ CHỐI giao sớm là đúng luật: "we can't deliver tomorrow — it takes 2-5 days".
_PHU_DINH_GIAO = re.compile(
    r"\b(?:can'?t|cannot|can\s+not|not|won'?t|unable|impossible|isn'?t|no|hindi|di|sorry|unfortunately)\b"
    r"|لا|لن|ما\s|مو\s|للأسف|不|無法|没法|沒辦法", re.I | re.U)
# "…but tomorrow is fine" / "pero bukas ok" — phủ định trước, nhận lời sau: vẫn là hứa.
_NHUNG_SOM = re.compile(r"\b(?:but|pero|however|instead)\b[^.!?\n]{0,15}?\b(?:" + _SOM_TU + r")\b", re.I)


def hua_giao_som(t, hom_nay=None, mkey=None, kb_page=None):
    """Câu AI có hứa giao sớm hơn thời gian giao thật không? Trả cụm chữ vi phạm hoặc None.

    Bắt: "deliver tomorrow / tomorrow delivery / arrive today / bukas / غدا / 明天送達", và ngày có tên tháng
    rơi vào trước hôm nay + số ngày giao tối thiểu ("deliver on September 15" nói ngày 14/09).
    Câu có phủ định sát cụm đó ("can't deliver tomorrow") thì qua — trừ khi lại "but tomorrow"."""
    t = str(t or "")
    for c in re.split(r"(?<=[.!?。！？])\s+|\n+", t):
        if not c.strip():
            continue
        m_nhung = _NHUNG_SOM.search(c)
        if m_nhung and _GIAO.search(c):
            return m_nhung.group(0)
        for mo in _GIAO_SOM.finditer(c):
            ngu_canh = c[max(0, mo.start() - 30):mo.end() + 20]
            if not _PHU_DINH_GIAO.search(ngu_canh):
                return mo.group(0)
        if _GIAO.search(c) and not _PHU_DINH_GIAO.search(c):
            hn = hom_nay or date.today()
            lo = thoi_gian_giao(mkey, kb_page)[0]
            for d in ngay_trong_cau(c, hn, True):
                if hn <= d < hn + timedelta(days=lo):
                    return f"{d:%d/%m}"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Tự kiểm — chạy `python3 chan_gui.py tu_kiem`, phải xanh hết mới được dùng
# ══════════════════════════════════════════════════════════════════════════════

_KB_TRI = {"mau": [{"tin": [   # rút gọn từ Soothing Cooling Gel in Saudi — không một chữ "almuranas"
    "Mahapdi o makati kapag matagal na nakaupo? Pakiramdam na bawat pagdumi ay kinakatakutan? Pangangati, Hapdi, "
    "Bukol, Pagdurugo", "Help soothe itching, burning, and discomfort around the anal area."]}]}

_KB_TU_CUNG = {"mau": [{"tin": [   # rút gọn từ Kreain Nature PH in Uae (Oxyelle Womb Care Gel)
    "Struggling with menstrual cramps, back pain, and discomfort every month... Oxyelle Womb Care Gel provides a fast, "
    "soothing warming sensation to your abdomen",
    "Use 1–2 times daily, especially before bedtime or during your menstrual period for a more soothing warming sensation."]}]}

CA_KIEM = [
    # (mô tả, tin, kwargs, kết mong đợi, mã lỗi bắt buộc phải có)
    ("nhận giao ngày mai (ca Wahida 14/09) — chặn",
     "Hi Wahida 😊 Noted! I can arrange delivery for tomorrow 🚚 Which one would you like? And please send your "
     "contact number so I can schedule delivery for tomorrow 💞", {"mkey": "uae", "hom_nay": date(2026, 9, 14)},
     "chan", "hua_giao_som"),
    ("\"For tomorrow delivery\" (ca Wahida) — chặn",
     "Hi Wahida 😊 For tomorrow delivery, which bundle would you like?", {"mkey": "uae"}, "chan", "hua_giao_som"),
    ("\"cannot deliver today but tomorrow is fine\" — chặn",
     "We cannot deliver today but tomorrow is fine. Shall I reserve 2 sets for you?", {"mkey": "uae"},
     "chan", "hua_giao_som"),
    ("Tagalog \"ihatid bukas\" — chặn",
     "Okay po Teresa, pwede ko ihatid bukas ang order 😊 Ano pong contact number?", {"mkey": "saudi"},
     "chan", "hua_giao_som"),
    ("Ả Rập \"التوصيل بكرة\" — chặn",
     "تمام، التوصيل بكرة إن شاء الله. ممكن رقم الجوال؟", {"mkey": "saudi"}, "chan", "hua_giao_som"),
    ("\"deliver on September 15\" nói ngày 14/09 — chặn",
     "Noted! Delivery on September 15, COD 😊 What's your complete address?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "chan", "hua_giao_som"),
    ("từ chối ngày mai, nói 2-5 ngày — qua",
     "Sorry Wahida, we can't deliver tomorrow 😊 Delivery takes 2-5 days (excluding weekends). Which bundle "
     "would you like?", {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("\"receive in 2-5 days\" + order today — qua",
     "Order today and you will receive it within 2-5 days, cash on delivery 😊 Which set would you like?",
     {"mkey": "uae"}, "qua", None),
    ("\"FREE DELIVERY TODAY ONLY\" là khuyến mãi — qua",
     "FREE DELIVERY TODAY ONLY po! Buy 1 Take 1. Order na po?", {"mkey": "kuwait", "kb_page": {"mau": [
         {"tu_khoa": "p", "tin": ["FREE DELIVERY TODAY ONLY! Buy 1 Take 1"]}]}}, "qua", None),
    ("\"promo ends today\" không phải lịch giao — qua",
     "Matatapos ang promo ngayong araw 😊 Free delivery at COD. Gusto mo bang umorder?", {"mkey": "saudi"}, "qua", None),
    ("giao 20 September (sau 2 ngày) — qua",
     "Noted! Delivery on September 20, COD 😊 What's your complete address?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("nhận giao tháng 2 năm sau (ca Jessica 14/09) — chặn",
     "Noted po Jessica 😊 1 Couple Ring Set — 12.9 KWD, free delivery, schedule sa February 24. COD po — "
     "wala kayong babayaran ngayon 💛", {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "chan", "hen_qua_han"),
    ("từ chối tháng 2, xin ngày trước 31 October — qua",
     "Pasensya po Jessica 😊 Ang order ay pwedeng i-hold hanggang October 31 lang. Kailan po ang sweldo "
     "niyo bago October 31? COD po, wala kayong babayaran ngayon 💛",
     {"mkey": "kuwait", "hom_nay": date(2026, 9, 14), "khach_hen_qua_han": True}, "qua", None),
    ("báo hạn khi khách chưa hẹn quá hạn (ca Celona 14/09) — chặn",
     "Salamat Celona 😊 Na-book ko na po ang 1 Set — 149 AED. Ang promo price po ay hanggang October 31 lang ma-hold — pwede po bang i-deliver before that date?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "chan", "bao_han_som"),
    ("hỏi khách muốn nhận ngày nào — qua",
     "No problem po 😊 Kailan po ang sweldo ninyo? I-deliver natin sa araw na yun. COD — walang babayaran ngayon 💛",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("promo tới 11pm hôm nay — qua",
     "Paalala lang po, hanggang 11pm lang po ang promo natin ngayon 😊 Alin po ang gusto ninyo?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("Mỹ: hẹn 25 November — trong hạn 2 tháng, qua",
     "Noted po! We'll deliver on November 25 😊 Ano pong complete address niyo?", {"mkey": "usa", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("Mỹ: hẹn December 5 — quá hạn 30/11, chặn",
     "Noted po! We'll schedule delivery on December 5 😊 Ano pong complete address niyo?", {"mkey": "usa", "hom_nay": date(2026, 9, 14)}, "chan", "hen_qua_han"),
    ("Kuwait: hẹn 25 November — quá hạn 31/10, chặn",
     "Noted po! We'll schedule delivery on November 25, COD 😊 Ano pong complete address niyo?", {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "chan", "hen_qua_han"),
    ("hẹn 30 October — trong hạn, qua",
     "Noted po! Delivery on October 30, COD — you pay the rider then 😊 Ano pong complete address niyo?", {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("\"May 4 colors\" tiếng Tagalog không phải tháng 5 — qua",
     "May 4 beautiful colors po tayo ngayon, free delivery 💚 Which one do you like?", {"mkey": "usa", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("tên bộ \"1 July Birthstone Set\" + delivery — qua",
     "Noted ma'am — 1 July Birthstone Set at 149 AED, free delivery 💎 May I have your contact number?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("tên khách Febrero — qua",
     "Hi Febrero 😊 1 Set is 149 AED, free shipping and Cash on Delivery. Which one would you like?",
     {"mkey": "uae", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("\"sa February\" không kèm ngày (ca Jessica) — chặn",
     "Pwede ko na po i-book ngayon at ischedule ang delivery sa February pag may sweldo 😊 Okay po ba?",
     {"mkey": "kuwait", "hom_nay": date(2026, 9, 14)}, "chan", "hen_qua_han"),
    ("page tháng sinh nói January không phải lịch giao — qua",
     "Sa ngayon, ang Month of January set ang aming best-seller! ✨ Gusto niyo po bang i-process ang order niyo ngayon?",
     {"mkey": "usa", "hom_nay": date(2026, 9, 14)}, "qua", None),
    ("câu bán hàng bình thường",
     "Hello po! Ang Gold Charm Bracelet po ay $129 na lang. Gusto niyo po bang i-order ko na?",
     {}, "qua", None),
    ("tin rỗng", "", {}, "chan", "tin_rong"),
    ("chỉ ba chấm kèm ảnh", "...", {"co_anh": True}, "chan", "tin_rong"),
    ("chỉ emoji", "❤️🥰", {}, "chan", "tin_rong"),
    ("hứa ảnh mà không có ảnh",
     "Hi sis! Here are the photos of our chain 💛 Which one would you like, 1 or 2?", {}, "viet_lai", "hua_anh"),
    ("hứa ảnh có ảnh kèm thì qua",
     "Hi sis! Here are the photos of our chain 💛 Which one would you like, 1 or 2?", {"co_anh": True}, "qua", None),
    ("xin khách gửi ảnh KHÔNG bị bắt",
     "Could you send me a photo of the item you received so I can check it for you?", {}, "qua", None),
    ("đọc lại số điện thoại khách",
     "Noted your number 0521003473 sis! Which combo would you like, 1 or 2 pcs?", {}, "nhac", "lap_sdt"),
    ("bịa nhận thẻ ở thị trường COD (ca NY Nurti 11/09)",
     "No problem, dear! We accept card payment too — you can pay when the order arrives 😊 Which combo would you like?",
     {"mkey": "uae"}, "chan", "bia_thanh_toan"),
    ("từ chối thẻ đúng luật thì qua",
     "Sorry sis, we don't accept card — cash on delivery only. Can you prepare cash for the courier? Which combo would you like?",
     {"mkey": "uae"}, "qua", None),
    ("Tagalog nhận thẻ — chặn",
     "Pwede po ang card payment pagdating ng order 😊 Ilang pcs po ang gusto niyo?", {"mkey": "uae"}, "chan", "bia_thanh_toan"),
    ("Mỹ có phương thức theo kịch bản — không chặn",
     "You can pay with PayPal or Venmo after you receive it. Which one do you prefer?", {"mkey": "usa"}, "qua", None),
    ("Mỹ: trả tiền cho rider (ca Zeny 14/09) — chặn",
     "Sa USA po tayo, COD — receive mo muna, i-check mo, tapos bayad ka na lang sa rider. Gusto mo bang subukan muna, Zeny? 😊",
     {"mkey": "usa"}, "chan", "cod_tai_cua"),
    ("Mỹ: không ưng thì không nhận (ca Zeny 14/09) — chặn",
     "Tama po, Zeny! 😊 Sa COD, makikita niyo muna ang actual product bago magbayad — kung hindi same sa demo o hindi niyo nagustuhan, pwede niyong hindi kunin at walang babayaran 🙏 Paki-send lang ang Phone Number?",
     {"mkey": "usa"}, "chan", "cod_tai_cua"),
    ("Mỹ: only pay if you like them — chặn",
     "Since it's Cash on Delivery, you can check the keychains first when they arrive and only pay if you like them. Would you like to try? 🍀",
     {"mkey": "usa"}, "chan", "cod_tai_cua"),
    ("Mỹ: kung hindi nagustuhan hindi kailangang bayaran — chặn",
     "Kaya po namin ino-offer ang COD — makikita niyo muna ang necklace bago magbayad. Kung hindi niyo nagustuhan, hindi niyo kailangang bayaran 🙏 Gusto niyo bang subukan?",
     {"mkey": "usa"}, "chan", "cod_tai_cua"),
    ("Mỹ: trả cho shop sau khi nhận — qua",
     "Walang babayaran ngayon po 😊 Natanggap muna ang necklace, i-check, saka magbayad sa amin sa Venmo. Paki-send ang Phone Number at Address?",
     {"mkey": "usa"}, "qua", None),
    ("Mỹ: hẹn giao cuối tuần để có người nhà (ca Philip 14/09) — chặn",
     "Pero no worries, pwede nating i-schedule ang delivery sa weekend para andoon ka sa bahay para tanggapin ang Golden Buddha 🙏✨",
     {"mkey": "usa"}, "chan", "hen_lich_giao"),
    ("Mỹ: mẫu No_MONEY hẹn ngày có tiền — ngày hẹn vẫn dùng, qua",
     "Umorder ka na ngayon para makuha ang promo, ihahatid ko ito sa araw na gusto mo. 😊 Kailan ka magkakaroon ng pera para maipadala ko na ang produkto sa’yo? 💖",
     {"mkey": "usa"}, "qua", None),
    ("Mỹ: hứa rider gọi trước / giao lại — chặn",
     "Don't worry dear, the rider will call you before delivery, and if you're not there we can re-deliver it 😊",
     {"mkey": "usa"}, "chan", "hen_lich_giao"),
    ("Mỹ: thời gian giao 5-10 ngày — qua",
     "Sa USA po, ang delivery ay 5–10 araw (hindi kasama ang weekend at holiday). Alin po ang gusto ninyo?",
     {"mkey": "usa"}, "qua", None),
    ("Mỹ: để hộp thư, không cần ở nhà — qua",
     "No worries po 😊 The parcel will be left in your mailbox or at your front door, no need to be home. Please send your full address?",
     {"mkey": "usa"}, "qua", None),
    ("Kuwait: hẹn giao ngày lương vẫn được — qua",
     "No problem po 😊 Which date do you get your salary? I can deliver on your salary day, COD — pay the rider then.",
     {"mkey": "kuwait"}, "qua", None),
    ("Mỹ: không trả rider phí ship (phủ định) — qua",
     "Yes po, FREE shipping — hindi niyo kailangang magbayad ng kahit ano sa rider. Alin po ang gusto ninyo, $199 o $299?",
     {"mkey": "usa"}, "qua", None),
    ("UAE: trả tiền cho rider là đúng — qua",
     "With COD you pay nothing today — you only pay the rider when the ring is in your hands. Which set would you like?",
     {"mkey": "uae"}, "qua", None),
    ("nhận vơ hàng của khách (ca Juliet 14/09) — chặn",
     "Hello Juliet 😊 Narinig ko na may Golden Buddha ka na pala! Maswerte ka talaga dahil hawak mo na ang gabay.",
     {"mkey": "uae", "khach_noi_da_mua": True}, "chan", "nhan_vo_da_mua"),
    ("nhận vơ kiểu Anh — chặn",
     "Great to hear you already have it! Place your Golden Buddha on the east side of your home 😊",
     {"mkey": "uae", "khach_noi_da_mua": True}, "chan", "nhan_vo_da_mua"),
    ("hỏi lại khách nhầm shop — qua",
     "Hi Juliet 😊 Hindi po namin makita ang order niyo sa system. Saan po kayo nag-order — sa page na ito ba? Pakisend po ng pangalan at number na ginamit niyo para ma-check ko.",
     {"mkey": "uae", "khach_noi_da_mua": True}, "qua", None),
    ("đọc chỉ tay khi khách chưa gửi ảnh (ca Vicky 14/09) — chặn",
     "Hello, Vicky. Si Madam Mystic na itong kausap mo.\n\nTiningnan ko ang palad mo… at nagulat ako sa nakita ko.\n"
     "Sa money line at life line mo, may mga sanga at putol-putol na marka",
     {"mkey": "usa", "khach_chua_gui_anh": True}, "chan", "bia_xem_anh"),
    ("nhắc gửi ảnh chỉ tay — qua",
     "Salamat Vicky 😊 Para masimulan ni Madam ang pagbabasa, i-send mo ang malinaw na picture ng kanang palad mo 📸 Ready ka ba?",
     {"mkey": "usa", "khach_chua_gui_anh": True}, "qua", None),
    ("nhắc gửi ảnh tiếng Anh — qua",
     "Thank you Vicky 😊 Please send a clear photo of your right palm so Madam can read the lines of your palm 🙏 Can you send it now?",
     {"mkey": "usa", "khach_chua_gui_anh": True}, "qua", None),
    ("đã xem ảnh kiểu Anh — chặn",
     "Dear Vicky, I have looked at your palm and your life line shows a strong blockage.",
     {"mkey": "usa", "khach_chua_gui_anh": True}, "chan", "bia_xem_anh"),
    ("bot đã báo 2 sets 13.9 — AI nói 13.9 thì qua (ca Aruna 14/09)",
     "Great choice, Aruna! 2 Couple Ring Sets for you — only 13.9 KWD with FREE delivery 🚚 Your contact number please?",
     {"mkey": "kuwait", "kb_page": {"mau": [{"tu_khoa": "p", "tin": ["🌻 1 Couple Ring Set – Only 12,9 KWD + 🚚 FREE Delivery"]}]},
      "gia": {"gia_ban": [12.9], "san_thap_nhat": 12}, "gia_page_da_bao": {9.9, 13.9, 12.9}}, "qua", None),
    ("AI tự nhân 12,9×2 = 25,8 — vẫn chặn (ca Aruna 14/09)",
     "Great choice, Aruna! 2 Couple Ring Sets for you — that's 25,8 KWD with FREE delivery 🚚",
     {"mkey": "kuwait", "kb_page": {"mau": [{"tu_khoa": "p", "tin": ["🌻 1 Couple Ring Set – Only 12,9 KWD + 🚚 FREE Delivery"]}]},
      "gia": {"gia_ban": [12.9], "san_thap_nhat": 12}, "gia_page_da_bao": {9.9, 13.9, 12.9}}, "chan", "bia_tien"),
    ("khách từ chối mà báo lại giá cũ (ca Fe Borabo 14/09) — chặn",
     "Hi Fe 😊 Oo, BUY 1 TAKE 1 means 2 sets. 239 AED for 2 sets, free shipping, Cash on Delivery. Ready ka na po ba?",
     {"mkey": "uae", "gia_cu_khi_tu_choi": {149, 239}}, "chan", "bao_gia_lai"),
    ("khách từ chối, AI níu không nêu giá — qua",
     "Sige po Fe 😊 Pwedeng malaman bakit hindi pa ngayon? COD po — buksan at check-in bago magbayad. Ano pong alalahanin niyo?",
     {"mkey": "uae", "gia_cu_khi_tu_choi": {149, 239}}, "qua", None),
    ("lượt 3 nêu mức giảm MỚI — qua",
     "Para sa inyo Fe, special price 215 AED for 2 sets only today 😊 Would you like me to reserve it?",
     {"mkey": "uae", "gia_cu_khi_tu_choi": {149, 239}}, "qua", None),
    ("không có cờ thì câu 'your order' vẫn qua",
     "Your order will arrive in 2-5 days 😊 Which combo would you like?",
     {"mkey": "uae"}, "qua", None),
    ("giá tiền không bị coi là số điện thoại",
     "Buy 1 Get 1 is 109 AED and Buy 2 Get 2 is 159 AED — which one would you like?", {}, "qua", None),
    ("lọt tiếng Việt rõ",
     "Dạ bên em giao hàng trong 2-5 ngày ạ, chị lấy combo 2 cái nhé?",
     {}, "chan", "lot_tieng_viet"),
    ("lọt tiếng Việt kiểu nhãn gói",
     "Hello po! Combo 2 cái — $199 po. Order na po tayo?",
     {}, "chan", "lot_tieng_viet"),
    ("lọt chữ SĐT (ca Gha Cabilin Plaza 14/09)",
     "Ano pong SĐT at complete address niyo sa Jeddah?",
     {}, "chan", "lot_tieng_viet"),
    ("tiếng Tây Ban Nha KHÔNG bị chặn oan",
     "¡Hola! El precio es 39 EUR con envío gratis. ¿Le preparo el pedido?",
     {"mkey": "spain"}, "qua", None),
    ("tiếng Romania KHÔNG bị chặn oan",
     "Bună ziua! Prețul este 199 RON, plata la primire. Doriți să vă înregistrez comanda?",
     {"mkey": "romania"}, "qua", None),
    ("tiếng Ả Rập bình thường",
     "مرحبا! السعر 199 درهم والتوصيل مجاني. هل أسجل لك الطلب؟",
     {"mkey": "uae"}, "qua", None),
    ("doạ khách", "If you don't pay I will report you and post in the Filipino group?",
     {}, "chan", "doa_khach"),
    ("ký tự ẩn", "Hello po,\u200b ready na po ba kayo?", {}, "chan", "ky_tu_an"),
    ("bịa khan hiếm", "Only 2 left po! Today only. Order na po?", {}, "chan", "bia_khan_hiem"),
    ("lộ nội bộ — nhắc tra địa chỉ",
     "Thank you po! Our sales team checked your address on Google Maps. Ready na po ba kayo?",
     {}, "chan", "lo_noi_bo"),
    ("lộ nội bộ — xưng AI", "I am an AI assistant po. Ano pong maitutulong?", {}, "chan", "lo_noi_bo"),
    ("bịa mã đơn", "Your Order ID: AB12345 po. Salamat! May tanong pa po kayo?",
     {}, "chan", "bia_ma_don"),
    ("dán checklist",
     "Please send po:\n✓ Full name\n✓ Mobile number\n✓ Complete address\n✓ Quantity\nSalamat?",
     {}, "viet_lai", "dan_checklist"),
    ("kết thụ động không chốt",
     "Yes po, 2-5 days delivery. Just let me know po.", {}, "viet_lai", "khong_chot"),
    ("hành động im mà vẫn soạn tin",
     "Hello po!", {"hanh_dong": "im"}, "chan", "khong_duoc_nhan"),
    ("hành động treo mà vẫn soạn tin",
     "We will check po.", {"hanh_dong": "treo"}, "chan", "khong_duoc_nhan"),
    ("xac_minh_nha để trống thì qua", "", {"hanh_dong": "xac_minh_nha"}, "qua", None),
    # ── Phủi quảng cáo (luật 12/09) — chặn cả hai chiều: bắt đúng câu cãi, tha câu bán hàng ──
    ("phủi: 'not actual tooth regrowth'",
     "Hi Manuel, the product supports enamel repair — not actual tooth regrowth in one week. "
     "Which set works for you?", {}, "chan", "phui_quang_cao"),
    ("phủi: 'no product can'",
     "I understand, but no product can grow new teeth, dear. Do you want to try it?",
     {}, "chan", "phui_quang_cao"),
    ("phủi: 'doesn't really' + Tagalog 'hindi po totoo'",
     "It doesn't really whiten in 3 days po, hindi po totoo yung ads. Order na po?",
     {}, "chan", "phui_quang_cao"),
    ("phủi: Ả Rập 'غير صحيح'",
     "غير صحيح ما ورد في الإعلان، لكن المنتج مفيد. هل تريد الطلب؟", {}, "chan", "phui_quang_cao"),
    # ── 21/09 ca MD Shahin Mondol (Minty Fresh Smile KSA) — chối mọc răng bằng tiếng Bengali, cổng cũ mù ──
    ("phủi: Bengali 'গজানো সম্ভব নয়' (ca Shahin)",
     "MD Shahin, সত্যি বলতে — নতুন দাঁত ওঠা নির্ভর করে আপনার গাম ও দাঁতের অবস্থার উপর, শুধু পেস্ট দিয়ে ফাঁকা "
     "জায়গায় নতুন দাঁত গজানো সম্ভব নয় 😊 আপনি কি ১ সেট নিতে চান?", {}, "chan", "phui_quang_cao"),
    ("phủi: Bengali 'পেস্টের কাজ নয়' (ca Shahin)",
     "MD Shahin, ঠিক বলেছেন — নতুন দাঁত গজানো পেস্টের কাজ নয় 😊 আপনি কি ১ সেট নিতে চান?", {}, "chan", "phui_quang_cao"),
    ("phủi: EN 'new teeth won't grow' + 'not the job of a toothpaste'",
     "Honestly, new teeth won't grow from it, that is not the job of a toothpaste. Would you like to try it?",
     {}, "chan", "phui_quang_cao"),
    ("phủi: Hindi 'दांत नहीं उगेंगे'", "इस पेस्ट से नए दांत नहीं उगेंगे। क्या आप ऑर्डर करना चाहेंगे?",
     {}, "chan", "phui_quang_cao"),
    # ── 23/09 ca Fely F Castillo (Madam Mystic TW) — chối bằng "không hứa / không đảm bảo / không phải phép màu" ──
    ("phủi: TL 'Hindi namin maipapangako ang panalo sa lotto' (ca Fely)",
     "Fely, ang Golden Fortune Necklace ay simbolo ng swerte at prosperity — isinusuot ito ng marami para sa biyaya. 🙏\n"
     "Hindi namin maipapangako ang panalo sa lotto, pero dala mo ang magandang intensyon. 😊\n"
     "Gusto mo bang ireserba ko na ang isa para sa'yo? ❤️", {}, "chan", "phui_quang_cao"),
    ("phủi: TL 'walang garantiya na mananalo'",
     "Opo, pampaswerte po ito pero walang garantiya na mananalo ka sa lotto. Order na po?", {}, "chan", "phui_quang_cao"),
    ("phủi: TL 'hindi ko po masisiguro'",
     "Hindi ko po masisiguro na mananalo kayo, pero simbolo ito ng swerte. Ireserba ko na?", {}, "chan", "phui_quang_cao"),
    ("phủi: TL 'hindi ito magic'",
     "Hindi po ito magic, dear — simbolo lang ng swerte. Gusto mo bang umorder?", {}, "chan", "phui_quang_cao"),
    ("phủi: EN 'can't really promise a jackpot'",
     "Dear, we can't really promise a jackpot, but it brings positive energy. Shall I reserve one?", {}, "chan", "phui_quang_cao"),
    ("phủi: EN 'there's no guarantee you will win'",
     "There's no guarantee you will win, but many wearers feel luckier 🍀 Want one?", {}, "chan", "phui_quang_cao"),
    ("phủi: EN 'it's not a magic item'",
     "Honestly it's not a magic item — it just carries good intentions. Order now?", {}, "chan", "phui_quang_cao"),
    ("phủi: EN 'depends on your luck'",
     "Winning the lottery still depends on your luck, dear. Would you like one?", {}, "chan", "phui_quang_cao"),
    ("phủi: ID 'tidak bisa menjamin menang'",
     "Kami tidak bisa menjamin menang lotre ya Kak, tapi gelang ini membawa energi positif. Mau dipesan?",
     {}, "chan", "phui_quang_cao"),
    ("phủi: AR 'لا نضمن الفوز'",
     "لا نضمن الفوز باليانصيب، لكن القلادة تجلب الطاقة الإيجابية. هل تريد الطلب؟", {}, "chan", "phui_quang_cao"),
    ("phủi: BN 'গ্যারান্টি দিতে পারি না'",
     "গ্যারান্টি দিতে পারি না যে লটারি জিতবেন, তবে এটি সৌভাগ্য আনে 🍀 অর্ডার করবেন?", {}, "chan", "phui_quang_cao"),
    ("phủi: 'Hindi po ito magic o guarantee ng pera' AI tự viết (không có trong kịch bản)",
     "Hindi po ito magic o guarantee ng pera — simbolo lang ng abundance. Gusto mo bang umorder?", {}, "chan", "phui_quang_cao"),
    ("KHÔNG phủi: cùng câu đó nhưng CÓ trong kịch bản page (Blessed Feng Shui Bracelets TW) → lời shop, qua",
     "Hindi po ito magic o guarantee ng pera — simbolo lang ng abundance. Gusto mo bang umorder?",
     {"kb_page": {"mau": [{"tin": ["Naiintindihan ko po. 🙏💛\nKung money at prosperity ang intention ninyo, traditionally ang "
                                   "Jade ay associated with abundance.\nHindi po ito magic o guarantee ng pera — simbolo lang ng "
                                   "abundance."]}]}}, "qua", None),
    ("KHÔNG phủi: câu khẳng định đúng cho ca Fely phải qua",
     "Opo Fely! Ang Golden Fortune Necklace ay ginawa para humatak ng swerte at biyaya sa pera — marami sa mga nagsusuot ang "
     "nagbabahagi na sumuwerte sila sa taya at negosyo 🍀 Dalhin mo lang ito tuwing tataya ka. Ireserba ko na ba ang isa para "
     "sa'yo? ❤️", {}, "qua", None),
    ("KHÔNG phủi: cam kết hoàn tiền CÓ trong kịch bản ('7-day money-back guarantee') qua",
     "Yes 😊 We have a 7-day money-back guarantee if you're not satisfied. Would you like to try it?", {}, "qua", None),
    ("KHÔNG phủi: 'Guaranteed genuine 18K gold' là câu khẳng định",
     "Guaranteed genuine 18K gold with certificate 💛 Which set would you like?", {}, "qua", None),
    ("KHÔNG phủi: TL 'Pangako ko, sasamahan kita' là lời hứa, không phải chối",
     "Pangako ko, sasamahan kita sa buong proseso 😊 Pwede ko na bang makuha ang address mo?", {}, "qua", None),
    ("KHÔNG phủi: TL bước kịch bản 'hindi ka nag-iisa … swerte' qua",
     "Hindi ka nag-iisa, Fely. Ang daming umaasa ng ganitong klaseng swerte. Ready ka na ba?", {}, "qua", None),
    ("KHÔNG phủi: AR 'نضمن لك ذهب أصلي' là khẳng định",
     "نضمن لك ذهب 18 قيراط أصلي مع شهادة 💛 أي طقم تريدين؟", {}, "qua", None),
    ("KHÔNG phủi: Bengali bắc cầu + mời mua (ca Shahin)",
     "দাঁতের ছবি দেখলাম, MD Shahin 😊 নিয়মিত ব্যবহারে ধীরে ধীরে পার্থক্য বোঝা যাবে। আপনি কি ১ সেট নিতে চান? 📦",
     {}, "qua", None),
    ("KHÔNG phủi: Bengali 'ngoài COD không được' là luật thanh toán",
     "ক্যাশ অন ডেলিভারি ছাড়া অন্য পেমেন্ট সম্ভব নয়। আপনি কি অর্ডার করবেন?", {}, "qua", None),
    ("KHÔNG phủi: 'do not accept card' là luật COD, phải qua",
     "We do not accept card, dear — cash on delivery only. Which set would you like?",
     {"mkey": "uae"}, "qua", None),
    ("KHÔNG phủi: 'does not contain' / 'cannot deliver today' là câu bán hàng, phải qua",
     "It does not contain harsh chemicals 😊 We cannot deliver today, delivery takes 2-5 days. "
     "Shall I reserve 2 sets for you?", {}, "qua", None),
    # ── Phủi bệnh page đang bán (ca Namzuged 19/09) — kịch bản trĩ không gọi tên bệnh, chỉ tả vùng ──
    ("phủi bệnh: 'hindi po ito gamot para sa almuranas' ở page trĩ",
     "Namzuged, hindi po ito gamot para sa almuranas. Gel po ito para maibsan ang pangangati. Gusto niyo po bang subukan?",
     {"kb_page": _KB_TRI, "cau_khach": ["Mawawala po ba ang almuranas", "Magagamot niya ba ito"]},
     "chan", "phui_quang_cao"),
    ("phủi bệnh: 'almuranas phải đi bác sĩ, relief lang' ở page trĩ",
     "Namzuged, para sa almuranas mismo, kailangan po ng konsultasyon sa doktor para sa tamang gamot o procedure. "
     "Ang gel po ay pang-relief lang.", {"kb_page": _KB_TRI, "cau_khach": ["Magagamot niya ba ito"]},
     "chan", "phui_quang_cao"),
    ("phủi bệnh: khách gọi tên bệnh, AI chối chung 'hindi gamot kundi…'",
     "Hi Jessie! 😊 Ang gel po ay hindi gamot kundi cooling gel para sa pangangati at hapdi.",
     {"kb_page": _KB_TRI, "cau_khach": ["pwede ba sa almoranas?"]}, "chan", "phui_quang_cao"),
    ("phủi bệnh: khách hỏi 'anong gamot', không gọi tên bệnh (ca Jessie)",
     "Hi Jessie! 😊 Ang Soothing Cooling Gel po ay hindi gamot kundi cooling gel na nagbibigay ng ginhawa.",
     {"kb_page": _KB_TRI, "cau_khach": ["anong gamot po sir."]}, "chan", "phui_quang_cao"),
    ("KHÔNG phủi: page trĩ, khách hỏi huyết áp → 'không phải thuốc huyết áp' qua",
     "Hindi po ito gamot sa high blood — para po ito sa pangangati at hapdi sa area. Gusto niyo po bang subukan?",
     {"kb_page": _KB_TRI, "cau_khach": ["gamot din ba ito sa high blood?"]}, "qua", None),
    ("KHÔNG phủi: page trĩ, AI bắc cầu thành phần + mời thử",
     "Opo, para po mismo sa ganitong discomfort ang gel — ang Sophora Flavescens at Dragon's Blood ay tumutulong "
     "maibsan ang pangangati, hapdi at pamamaga. Gusto niyo po bang subukan?",
     {"kb_page": _KB_TRI, "cau_khach": ["Mawawala po ba ang almuranas"]}, "qua", None),
    ("KHÔNG phủi: bệnh KHÁC page (trà mà hỏi tim to) → hỏi bác sĩ vẫn qua",
     "Hi Jane! 😊 For heart enlargement, it's best to consult a doctor first for proper treatment. Our tea supports "
     "healthy circulation. Would you like to try it?",
     {"kb_page": {"mau": [{"tin": ["Nine-Ingredient Herbal Tea supports healthy cholesterol and circulation."]}]},
      "cau_khach": ["pwede ba sa lumaki ang puso?"]}, "qua", None),
    ("KHÔNG phủi: khách bầu hỏi gel trĩ → hỏi bác sĩ vẫn qua",
     "Congrats po! 😊 Dahil buntis po kayo, mas mainam na magpakonsulta muna sa doktor bago gamitin. Gusto niyo po "
     "bang ipareserve ko?", {"kb_page": _KB_TRI, "cau_khach": ["buntis ako may almuranas pwede ba?"]}, "qua", None),
    # ── 23/09 ca Grenelyn (Oxyelle Womb Care Gel) — đẩy khách đi bác sĩ là chối sản phẩm ──
    ("bác sĩ: 'ipakonsulta muna ito sa doktor' ở page tử cung (ca Grenelyn)",
     "Salamat sa pag-share, Grenelyn 🙏 Ang Oxyelle Womb Care Gel ay nakakatulong magbigay ng warming comfort sa puson. "
     "Pero dahil may mga blood clot po kayong napapansin, mas mabuting ipakonsulta muna ito sa doktor — hindi po namin "
     "kayo maa-advisean tungkol diyan.", {"kb_page": _KB_TU_CUNG, "cau_khach": [
         "madam, bwan bwan p akong denudugo pero ang lumalabas may mga belog na dugo"]}, "chan", "phui_quang_cao"),
    ("bác sĩ: 'have a doctor check it' ở page tử cung (ca Loreins)",
     "Thanks for telling me, Loreins 😊 That pain after urinating isn't something the gel is meant for — it's best to "
     "have a doctor check it, since it can be a urine infection.", {"kb_page": _KB_TU_CUNG, "cau_khach": [
         "masakit po after umihi"]}, "chan", "phui_quang_cao"),
    ("bác sĩ: page không có trong BENH_PAGE, 'consult your OB-GYN' vẫn chặn",
     "I understand, dear. For the yellow discharge it's better to consult your OB-GYN first. Do you want to order?",
     {"kb_page": {"mau": [{"tin": ["Oxyelle Feminine Wash helps reduce itching & unpleasant odor."]}]},
      "cau_khach": ["may yellow discharge ako"]}, "chan", "phui_quang_cao"),
    ("KHÔNG phủi: tư vấn đúng cho khách ra máu cục (ca Grenelyn) phải qua",
     "Salamat sa pag-share, Grenelyn 🙏 Ang Oxyelle Womb "
     "Care Gel ay nagbibigay ng init at ginhawa sa puson lalo na tuwing may regla. Pwede ko na po bang makuha ang "
     "contact number at address ninyo?", {"kb_page": _KB_TU_CUNG, "cau_khach": [
         "madam, bwan bwan p akong denudugo pero ang lumalabas may mga belog na dugo", "48 yrs n po ako"]}, "qua", None),
    ("KHÔNG phủi: cảnh báo kích ứng của kịch bản ('irritation … consult a doctor') qua",
     "Apply on the lower abdomen 1-2 times daily 😊 If irritation occurs, stop using and consult a doctor. "
     "Which bundle would you like?", {"kb_page": _KB_TU_CUNG, "cau_khach": ["how to use?"]}, "qua", None),
    ("KHÔNG phủi: khách bầu hỏi gel tử cung → hỏi bác sĩ vẫn qua",
     "Congrats po! 😊 Dahil buntis po kayo, mas mainam na magpakonsulta muna sa doktor bago gamitin. Gusto niyo po "
     "bang ipareserve ko?", {"kb_page": _KB_TU_CUNG, "cau_khach": ["buntis po ako pwede ba sa puson?"]}, "qua", None),
    ("KHÔNG phủi: 'recommended by doctors' là câu bán hàng",
     "Our gel is recommended by doctors and trusted by over 54,000 women 😊 Which bundle would you like?",
     {"kb_page": _KB_TU_CUNG, "cau_khach": ["legit ba?"]}, "qua", None),
    ("KHÔNG phủi: 'No need to see a doctor first' (ca Feker) là câu bán hàng",
     "No need to see a doctor first, Feker 😊 Oxyelle is a gentle warming gel for your lower abdomen — just apply it "
     "before bedtime. Would you like to try it?", {"kb_page": _KB_TU_CUNG, "cau_khach": ["ok"]},
     "qua", None),
    ("KHÔNG phủi: 'bukan obat minum' = không phải thuốc UỐNG (ca Andini)",
     "Betul, ini gel oles untuk pemakaian luar di perut bagian bawah, bukan obat minum 😊 Hangatnya membantu meredakan "
     "kram. Mau coba yang mana, Andini?", {"kb_page": _KB_TU_CUNG, "cau_khach": [
         "Ini obat luar, apakah serius bekerja buat mengobati organ dalam"]}, "qua", None),
    ("KHÔNG phủi: chối chữa ung thư (bệnh khác hẳn) ở page tử cung qua",
     "Miracle, Oxyelle Womb Care Gel is not a treatment for cancer — for that, please keep following your doctor's "
     "advice. It gives a soothing warming sensation to the abdomen. Shall I confirm your order?",
     {"kb_page": _KB_TU_CUNG, "cau_khach": ["I have cancer can I use?"]}, "qua", None),
    ("KHÔNG phủi: lời dặn có điều kiện 'If you are taking medication… consult your doctor' qua",
     "This tea is made from 9 natural herbs 😊 If you are taking medication, consult your doctor before using it "
     "regularly. Would you like to try it?", {"kb_page": {"mau": [{"tin": ["Nine-Ingredient Herbal Tea."]}]},
      "cau_khach": ["What is side effects"]}, "qua", None),
    ("KHÔNG phủi: bắc cầu đúng công thức, phải qua",
     "Our Croent 7.5% Hydroxyapatite toothpaste rebuilds your enamel — the outer layer that "
     "wears down over time. Most customers notice whiter, less sensitive teeth in the first "
     "week. Which set would you like, dear?", {}, "qua", None),
    ("rep 1 câu rồi giao sale — không cần câu hỏi cuối",
     "I understand, dear. What the toothpaste works on is the enamel — repairing and "
     "strengthening it. Let me send you the details and real customer feedback 😊",
     {"hanh_dong": "tra_loi_treo"}, "qua", None),
    # ── Khoá lại 4 lớp CHẶN OAN đã tìm được khi soi 4.824 mẫu kịch bản thật ──────
    ("[thật] emoji ghép ZWJ không phải ký tự né lọc",
     "💆‍♀️ How to use: clean the area first. Gusto niyo po ba mag-order?", {}, "qua", None),
    ("[thật] xin khách chia sẻ vị trí Google Maps là hợp lệ",
     "Paki-share po ng lokasyon ninyo sa Google Maps para maihatid namin nang tama?",
     {}, "qua", None),
    ("[thật] nhắc chữ 'tracking number' không phải bịa mã đơn",
     "Paki-send po ang larawan ng MONEY ORDER at ng TRACKING NUMBER gaya ng ipinapakita po?",
     {}, "qua", None),
    ("[thật] khan hiếm CÓ trong kịch bản thì được nói",
     "FREE SHIPPING — TODAY ONLY po! Combo 1: Buy 1 Take 1 — 7 KWD. Order na po?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": [
         "🚚 FREE SHIPPING — TODAY ONLY! Combo 1: Buy 1 Take 1 —7 KWD"]}]}}, "qua", None),
    ("bịa cửa hàng: 'no physical store, online shop based in UAE' mà kịch bản không nói → CHẶN (ca Suraj 10/09)",
     "Hi Suraj! 😊 We don't have a physical store — we're an online shop based in UAE. Order now?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": ["1 pc 89 AED, 2 pcs 139 AED, free delivery"]}]}},
     "chan", "bia_cua_hang"),
    ("kịch bản có nói địa điểm thì AI được nhắc → QUA",
     "We're based in Dubai and ship nationwide 🚚 Ready to order?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": ["Our store is based in Dubai, free delivery all UAE. 1 pc 89 AED"]}]}},
     "qua", None),
    ("đơn giá suy từ gói '2 bottles 159' → 79,5 each là QUA (ca Edd Mac 10/09)",
     "Hi Edd! 😊 One bottle is 109 AED with free delivery. Or you can get 2 bottles for 159 AED — "
     "that's only 79,5 AED each, much better value! 💙 Which one would you prefer — 1 bottle or 2 bottles?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": [
         "🌿 1 bottle: 109 AED + FREE delivery\n🌿 2 bottles: 159 AED + FREE delivery"]}]},
      "gia": {"gia_ban": [109, 159], "san_thap_nhat": 99}}, "qua", None),
    ("đơn giá bịa (70 each) vẫn chặn",
     "2 bottles for 159 AED — that's only 70 AED each! Which one?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": [
         "🌿 1 bottle: 109 AED\n🌿 2 bottles: 159 AED"]}]},
      "gia": {"gia_ban": [109, 159], "san_thap_nhat": 99}}, "chan", "bia_tien"),
    ("khan hiếm có trong kịch bản, AI nói bằng chữ khác thì QUA (ca Emma 10/09)",
     "No problem po! Hurry though — the offer ends at 11 PM today! 🔥 Ready na po ba kayo?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": [
         "Because the promotion will end at 11 PM today, dear 😘 Price 7 KWD"]}]}},
     "qua", None),
    ("khan hiếm KHÔNG có trong kịch bản thì chặn",
     "Hurry po, only 2 left! Order na po?",
     {"kb_page": {"mau": [{"tu_khoa": "p", "tin": ["Price 7 KWD, free delivery"]}]}},
     "chan", "bia_khan_hiem"),
    ("nhắn lặp y nguyên",
     "Ready na po ba kayo mag-order? Free delivery po!",
     {"tin_truoc": "Ready na po ba kayo mag-order? Free delivery po!"}, "chan", "nhan_lap"),
]

# Ca về TIỀN dùng chung một kịch bản giả lập giống page Gold Charm Bracelet US
KB_GIA_LAP = {"mau": [
    {"tu_khoa": "Chốt-Giá", "tin": ["Regular value $350"]},
    {"tu_khoa": "báo_giá", "tin": ["1 pc — $199\nBUY 2 GET 1 — $299"]},
    {"tu_khoa": "Giảm_giá", "tin": ["$199 → $129 today"]},
]}
GIA_GIA_LAP = {"gia_chao": [199, 299], "gia_thuc": 129, "gia_san": 119,
               "gia_ban": [129, 199], "san_theo_gia": {129: 119, 199: 180},
               "san_thap_nhat": 119}

CA_TIEN = [
    ("giá thực trong bảng — qua", "It's $129 po with free delivery. Order na po?", "qua", None),
    ("giá chào trong bảng — qua", "SET 2 po is $299 for 3 pcs. Kukunin niyo po ba?", "qua", None),
    ("giá sàn tính ra — qua", "Sige po, $119 na lang para sa inyo. Order na po?", "qua", None),
    ("TỰ NHÂN giá gói — chặn", "For 2 sets po that's $598 total. Ok po ba?", "chan", "bia_tien"),
    ("tổng lạ — chặn", "Total po is $258 for 2 pcs. Proceed na po?", "chan", "bia_tien"),
    ("dưới giá sàn — chặn", "Ok po, $99 na lang final. Sige na po?", "chan", "duoi_gia_san"),
]


def tu_kiem():
    tong = sai = 0
    for mo_ta, tin, kw, mong, ma in CA_KIEM:
        tong += 1
        pq = kiem(tin, **kw)
        ok = pq.ket == mong and (ma is None or ma in pq.ma_loi)
        if not ok:
            sai += 1
        print(f"  {'✅' if ok else '❌'} {mo_ta:44s} → {pq.ket:9s} {pq.ma_loi}")
    print()
    for mo_ta, tin, mong, ma in CA_TIEN:
        tong += 1
        pq = kiem(tin, mkey="usa", kb_page=KB_GIA_LAP, gia=GIA_GIA_LAP)
        ok = pq.ket == mong and (ma is None or ma in pq.ma_loi)
        if not ok:
            sai += 1
        print(f"  {'✅' if ok else '❌'} {mo_ta:44s} → {pq.ket:9s} {pq.ma_loi}")
    hn = date(2026, 9, 14)
    for cau, mong in [("February po sir", date(2027, 2, 1)), ("feb 24 sweldo", date(2027, 2, 24)),
                      ("24 de febrero", date(2027, 2, 24)), ("sa 30 october po", None), ("next year", date(2027, 1, 1)),
                      ("after 3 months", hn + timedelta(days=93)), ("12/12", None), ("24/02/2027", date(2027, 2, 24)), ("15/10/2026", None),
                      ("December po", date(2026, 12, 1)), ("may 5", None), ("jun 5", date(2027, 6, 5)), ("may pera sa 15", None),
                      ("بعد شهرين", hn + timedelta(days=62)), ("فبراير", date(2027, 2, 1)), ("2月", date(2027, 2, 1)),
                      ("1/3 ang presyo", None), ("24/7 po", None), ("12.9 KWD", None)]:
        tong += 1
        ra = ngay_qua_han(cau, hn)
        ok = ra == mong
        sai += not ok
        print(f"  {'✅' if ok else '❌'} ngày quá hạn {cau!r:28s} → {ra}")
    for cau, mong in [("It takes 2-5 days to delivery dear", (2, 5)), ("sa loob ng 5–10 araw", (5, 10)),
                      ("خلال 2-5 أيام", (2, 5)), ("12.9-13.9 KWD", None), ("24/7", None)]:
        tong += 1
        ra = khoang_ngay_trong(cau)
        ok = ra == mong
        sai += not ok
        print(f"  {'✅' if ok else '❌'} khoảng ngày giao {cau!r:34s} → {ra}")
    for cau, mong in [   # khoảng ngày NÓI VỀ GIAO HÀNG (chủ shop 23/09, ca Hanah) — None = không phải ngày giao
        ("🔥 Lumiit ang tiyan at bewang (7–10 days pa lang may changes na)", None),
        ("📦 You will receive your order within 5–7 days po!", (5, 7)),
        ("It take 2 - 5 days to delivery dear", (2, 5)),
        ("Results in 7-10 days. Delivery takes 5-10 days.", (5, 10)),
        ("most customers feel lighter in the first 7–10 days", None),
        ("التوصيل خلال 2-5 أيام", (2, 5)),
    ]:
        tong += 1
        ra = khoang_ngay_giao_trong(cau)
        ok = ra == mong
        sai += not ok
        print(f"  {'✅' if ok else '❌'} khoảng ngày GIAO {cau[:44]!r} → {ra}")
    KB_TW = {"mau": [{"tin": ["It take 5-7 days to delivery dear"]},
                     {"tin": ["👉Your order is TWD. You will receive it within 5-7 days! ❤️"]},
                     {"tin": ["🔥 Lumiit ang tiyan (7–10 days pa lang may changes na)"]}]}
    for mk, kb, mong, nguon in [("saudi", KB_TW, (3, 7), "chủ shop"), ("uae", KB_TW, (2, 5), "chủ shop"),
                                ("kuwait", None, (2, 5), "chủ shop"), ("taiwan", KB_TW, (5, 7), "kịch bản page"),
                                ("usa", KB_TW, (5, 7), "kịch bản page"), ("taiwan", None, (3, 7), "không ghi"),
                                ("usa", {"mau": []}, (5, 10), "không ghi"), (None, None, (2, 5), "chủ shop")]:
        tong += 1
        ra = thoi_gian_giao(mk, kb, ["Delivery 7-10 days"])
        ok = ra[:2] == mong and nguon in ra[2]
        sai += not ok
        print(f"  {'✅' if ok else '❌'} thời gian giao {str(mk):7s} → {ra[:2]} ({ra[2]})")
    for mk, kb, cau, mong in [   # máy sửa số ngày giao trong câu AI — None = phải để yên
        ("saudi", None, "Delivery takes 2-5 days (excluding weekends) 😊 Which bundle?",
         "Delivery takes 3-7 days (excluding weekends) 😊 Which bundle?"),
        ("saudi", None, "Mga 7-10 days po ang delivery, Hanah 😊", "Mga 3-7 days po ang delivery, Hanah 😊"),
        ("saudi", None, "1 cup a day helps shrink the belly, most customers feel lighter in the first 7–10 days.", None),
        ("saudi", None, "Lumiit ang tiyan at bewang (7–10 days pa lang may changes na)", None),
        ("saudi", None, "Delivery takes 3-7 days. You'll see changes in 7-10 days.", None),
        ("uae", None, "Your order will arrive in 2-5 days 😊", None),
        ("kuwait", None, "التوصيل خلال 3-7 أيام", "التوصيل خلال 2-5 أيام"),
        ("taiwan", KB_TW, "配送約 5-7 天到貨", None),
        ("taiwan", KB_TW, "Mga 2-4 days po ang delivery 😊", "Mga 5-7 days po ang delivery 😊"),
        ("usa", None, "Shipping takes 2-5 business days to your address.", "Shipping takes 5-10 business days to your address."),
        ("saudi", None, "Buy 1 Get 1 — 2 tubes for 109 SAR, 30 days supply.", None),
    ]:
        tong += 1
        _lo, _hi, _ = thoi_gian_giao(mk, kb)
        ra, doi = sua_so_ngay_giao(cau, _lo, _hi, khoang_cho_phep(mk, kb))
        ok = ra == (mong or cau) and bool(doi) == (mong is not None)
        sai += not ok
        print(f"  {'✅' if ok else '❌'} sửa số ngày giao [{mk:6s}] {cau[:42]!r} → {ra[:42]!r}")
    print(f"\n  {tong - sai}/{tong} ca đúng." + ("" if sai else "  Cổng dùng được."))
    return 1 if sai else 0


def cmd_thu(mkey, khoa):
    """In bộ giá + tập số hợp lệ của 1 page thật — để mắt thường soát trước khi bật cổng."""
    f = os.path.join(SCRIPT_DIR, "state", mkey, "kich_ban.json")
    if not os.path.exists(f):
        sys.exit(f"❌ Chưa có kịch bản {mkey}. Chạy: python3 kich_ban.py tai {mkey}")
    kb = json.load(open(f, encoding="utf-8"))
    pid, v = None, None
    if khoa in kb:
        pid, v = khoa, kb[khoa]
    else:
        for k, x in kb.items():
            if khoa.lower() in (x.get("ten_page") or "").lower():
                pid, v = k, x
                break
    if not v:
        sys.exit(f"Không thấy page {khoa!r} trong {mkey}.")
    try:
        sys.path.insert(0, SCRIPT_DIR)
        import ai_sale
        gia = ai_sale.bo_gia(v, mkey)
    except Exception as e:                       # noqa: BLE001
        print(f"⚠️  không tính được bộ giá ({e})")
        gia = None
    duoc = sorted(so_duoc_phep(v, gia))
    print(f"\n═══ {v['ten_page']} ({pid}) — {len(v['mau'])} mẫu câu ═══\n")
    print(f"  Tiền tệ thị trường : {TIEN_TE.get(mkey, '?')}")
    if gia:
        print(f"  Giá chào           : {gia['gia_chao']}")
        print(f"  Giá thực           : {gia['gia_thuc']}")
        print(f"  Mức page thật sự bán: {gia['gia_ban']}")
        for g, sn in sorted((gia.get("san_theo_gia") or {}).items()):
            print(f"     giá {g:>6} → sàn {sn}")
        print(f"  Sàn thấp nhất      : {gia['san_thap_nhat']}  ← ngưỡng cổng chặn")
    print(f"\n  {len(duoc)} con số AI được phép nói:\n   {duoc}")
    print("\n  → Con số nào AI nói ra ngoài danh sách này sẽ bị chặn (mã 'bia_tien').")
    if gia and not gia.get("san_thap_nhat"):
        print("  ⚠️  Page này KHÔNG rút được mức giá nào → cổng chặn không canh được giá sàn.")
    elif gia and not gia.get("gia_thuc"):
        print("  ℹ️  Page này không có mẫu /Giảm_giá — sàn tính thẳng trên giá combo trong "
              "/báo_giá (đúng cấu trúc của phần lớn page).")


def main():
    a = sys.argv[1:]
    if a and a[0] == "tu_kiem":
        sys.exit(tu_kiem())
    elif len(a) >= 3 and a[0] == "thu":
        cmd_thu(a[1], a[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

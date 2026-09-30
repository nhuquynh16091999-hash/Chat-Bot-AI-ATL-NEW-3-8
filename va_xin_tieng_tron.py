"""Vá 20/09 — tin khách CHỈ GỒM TÊN MỘT NGÔN NGỮ ("عربيه", "Arabic", "urdu please") là LỜI XIN TIẾNG,
không phải "không có gì để trả lời".

Ca ابو منصور · Soothing Cooling Gel in Saudi (chủ shop 20/09 sáng): 19/09 21:53 VN khách gõ đúng một chữ
"عربي" (= tiếng Ả Rập) ngay sau tin chào Tagalog của Botcake. `vo_nghia` coi tin 1 chữ là tin rỗng nên
`_tieng_cua_khach` LOẠI tin đó khỏi danh sách đo tiếng → AI không thấy dấu hiệu nào, đáp nguyên một bài
tiếng Tagalog. 20/09 07:01 VN khách nhắc lại "عربيه" → vẫn 1 chữ → cổng "Botcake im mà tin khách không có
gì để trả lời" bật → TREO; 5 phút sau sale Nguyễn Duyên phải tự gõ câu tiếng Ả Rập. *"sao k rep tiếng ả
rập cũng k rep tn khách vậy"*.

`tieng_yeu_cau` chỉ bắt tên tiếng gõ chữ Latin KÈM ngữ cảnh ("arabic please", "speak arabic") — tên tiếng
đứng một mình, nhất là gõ bằng chữ bản địa (عربي / اردو / हिंदी / বাংলা), trượt hết.

Sửa 3 chỗ:
  1. chan_gui.ten_tieng_tron  — tin chỉ gồm tên một tiếng → mã tiếng (cả chữ bản địa).
  2. chan_gui.tieng_yeu_cau   — hỏi hàm trên TRƯỚC các mẫu cũ.
  3. ai_sale.vo_nghia + _tin_co_noi_dung — tin xin tiếng KHÔNG phải tin rỗng (mở cổng treo, mở cửa
     Botcake-đã-rep, và trả tin đó lại cho `_tieng_cua_khach` để AI đổi sang đúng tiếng khách xin).

Chạy: python3 va_xin_tieng_tron.py chan_gui.py ai_sale.py   (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f_cg, f_ai = sys.argv[1], sys.argv[2]
src_cg = open(f_cg, encoding="utf-8").read()
src_ai = open(f_ai, encoding="utf-8").read()
if "ten_tieng_tron" in src_cg or "ten_tieng_tron" in src_ai:
    sys.exit("đã vá rồi — không làm gì")

VA_CG = [(
    '''def tieng_yeu_cau(t):
    """Khách XIN nói tiếng gì? -> mã tiếng ('hi', 'ur', 'ar'…), '?' = khách chỉ nói không biết
    tiếng Anh, None = câu này không phải yêu cầu về ngôn ngữ."""
    t = str(t or "").strip()
    if not t:
        return None
    ma = None
''',
    '''# TÊN TIẾNG GÕ BẰNG CHỮ BẢN ĐỊA — khách xin tiếng của mình thì hay gõ luôn bằng chữ của tiếng đó.
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
    s = re.sub(r"[\\u200b-\\u200f\\u0640\\u064b-\\u0652]", "", str(t or ""))
    goi = re.sub(r"[^\\w]+", " ", s, flags=re.U).strip().lower()
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
''')]

VA_AI = [(
    '''    if re.match(CHAO, low) and len(low.split()) <= 4:
        return True
    return len(low.split()) <= 1
''',
    '''    if re.match(CHAO, low) and len(low.split()) <= 4:
        return True
    # "عربيه" / "Arabic" / "urdu please" — một chữ, nhưng là LỜI XIN TIẾNG. Để nó rơi vào "tin rỗng"
    # thì `_tieng_cua_khach` loại luôn tin đó (AI đáp sai tiếng) và cổng treo bật (AI không đáp gì cả) —
    # ca ابو منصور 19-20/09, Soothing Cooling Gel in Saudi.
    if CG.ten_tieng_tron(t):
        return False
    return len(low.split()) <= 1
'''), (
    '''    if MUON_MUA.search(t) or CACH_DAT.search(t):
        return True
    return len(re.findall(r"\\w+", t, re.U)) >= 4
''',
    '''    if MUON_MUA.search(t) or CACH_DAT.search(t):
        return True
    if CG.ten_tieng_tron(t):
        return True                                  # khách xin đổi tiếng — Botcake rep tiếng cũ là chưa đủ
    return len(re.findall(r"\\w+", t, re.U)) >= 4
''')]

for f, src, va in ((f_cg, src_cg, VA_CG), (f_ai, src_ai, VA_AI)):
    for cu, moi in va:
        n = src.count(cu)
        if n != 1:
            sys.exit(f"❌ {f}: khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:160]}")
        src = src.replace(cu, moi)
    compile(src, f, "exec")
    open(f, "w", encoding="utf-8").write(src)
    print(f"✔ đã vá {f}")

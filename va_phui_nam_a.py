# -*- coding: utf-8 -*-
"""VÁ 21/09: AI chối quảng cáo MỌC RĂNG bằng tiếng Bengali mà cổng không bắt (ca MD Shahin Mondol, Minty Fresh Smile KSA).

Chủ shop: "MD Shahin Mondol lại chối là như nào? tôi dặn bạn sao". Hai lỗ:
  1. chan_gui.PHUI_QC chỉ biết Anh / Tagalog / Ả Rập → câu Bengali "…নতুন দাঁত গজানো সম্ভব নয়" (không thể mọc răng mới)
     và "নতুন দাঁত গজানো পেস্টের কাজ নয়" (mọc răng không phải việc của kem) lọt thẳng tới khách. Tiếng Anh cũng hở
     đúng kiểu này ("new teeth won't grow", "not the job of a toothpaste", "…depends on your gums").
  2. nap_luat chỉ nạp khối 30_quang_cao.md khi khách hỏi bằng Anh/Tagalog/Indo/Ả Rập → khách Bangladesh hỏi "এটা দিয়ে কি
     নতুন দাঁত উঠবে?" thì model soạn tự do, không có luật "không chối, không hứa, lần 2 thì treo".

Chạy:  python3 va_phui_nam_a.py          (vá /opt/pancake-tool/chan_gui.py + nap_luat.py, có .bak)
       python3 va_phui_nam_a.py kiem     (chỉ kiểm dấu vết, không ghi)
Mỗi chỗ thay đều assert count==1 — phiên khác sửa trúng vùng đó thì thoát, KHÔNG ghi.
"""
import os
import py_compile
import sys
import time

THU_MUC = os.environ.get("PT_DIR", "/opt/pancake-tool")
F_CG = os.path.join(THU_MUC, "chan_gui.py")
F_NL = os.path.join(THU_MUC, "nap_luat.py")
DAU = {F_CG: ("_PHUI_NAM_A", "phủi: Bengali 'গজানো সম্ভব নয়'"), F_NL: ("HOI_MOC_RANG", "HOI_QC_NAM_A")}

# ───────────────────────────── chan_gui.py: nối thêm mẫu vào PHUI_QC ─────────────────────────────
CG_MOC = '''    r"|hindi\\s+(po\\s+)?totoo"
    r"|غير\\s+صحيح|ليس\\s+صحيح)", re.I | re.U)
'''
CG_THEM = CG_MOC + '''
# ── 21/09 — CHỐI MỌC RĂNG / CHỐI QUẢNG CÁO BẰNG TIẾNG KHÁC (chủ shop: "MD Shahin Mondol lại chối là như nào? tôi dặn bạn sao") ──
# Ca MD Shahin Mondol (Minty Fresh Smile KSA, khách Bangladesh): AI viết tiếng Bengali "সত্যি বলতে — … শুধু পেস্ট দিয়ে ফাঁকা
# জায়গায় নতুন দাঁত গজানো সম্ভব নয়" (nói thật — chỉ bằng kem thì không mọc được răng mới ở chỗ trống), rồi khách hỏi lại thì
# "নতুন দাঁত গজানো পেস্টের কাজ নয়" (mọc răng mới không phải việc của kem). PHUI_QC chỉ biết Anh/Tagalog/Ả Rập nên cả hai lọt.
# Tiếng Anh hở đúng kiểu đó: "new teeth won't grow", "not the job of a toothpaste", "whether new teeth grow depends on…".
# Mẫu MỌC RĂNG neo vào chữ RĂNG trong cùng vế câu: "সম্ভব নয়" / "संभव नहीं" trơn là câu thường ("ngoài COD thì không được").
# Chữ Bengali không dùng \\b (dấu nguyên âm không phải \\w); "য়" có 2 cách gõ (1 mã hoặc য + ়) nên mẫu nhận cả hai.
_Y = "(?:\\u09df|\\u09af\\u09bc)"                     # য়
_NOY = "ন" + _Y                                       # নয় (không phải)
_NA = "না(?![\\u0980-\\u09ff])"                        # না đứng riêng — không ăn "নাকি", "নাম"
_KHONG_BN = "(?:" + _NOY + "|" + _NA + ")"
_BN = "[\\u0980-\\u09ff]"
_DANT = "দাঁত"                                        # răng
_MOC_BN = "(?:গজা|গজি|উঠ|ওঠ)"                          # mọc / nhú lên
_HI_DANT = "दा[ँं]त"
_HI_KHONG = "(?:नहीं|नही)"
_UR_KHONG = "(?:نہیں|نھیں|نہی|نهیں)"
_PHUI_NAM_A = [
    # EN — mọc răng
    r"\\bteeth\\s+(?:won'?t|will\\s+not|cannot|can'?t|don'?t|do\\s+not|never)\\s+(?:\\w+\\s+){0,2}?(?:grow|regrow|come\\s+(?:back|out|in))",
    r"\\b(?:won'?t|will\\s+not|doesn'?t|does\\s+not|don'?t|do\\s+not)\\s+(?:\\w+\\s+){0,2}?(?:grow|regrow)\\s+(?:\\w+\\s+){0,2}?(?:teeth|tooth)\\b",
    r"\\b(?:grow\\w*|regrow\\w*)\\s+(?:new\\s+|back\\s+)?(?:teeth|tooth)\\s+(?:is|isn'?t)\\s+(?:not\\s+)?(?:\\w+\\s+){0,3}?(?:job|role|purpose|function|possible)\\b",
    r"\\bnot\\s+(?:the\\s+)?(?:job|role|purpose)\\s+of\\s+(?:a\\s+|the\\s+|any\\s+)?(?:tooth)?paste",
    r"\\b(?:new\\s+teeth|tooth\\s+regrowth|teeth\\s+regrowth|regrow\\w*|grow\\w*\\s+(?:new\\s+)?teeth)[^.!?\\n]{0,50}?\\bdepend\\w*\\s+on\\b",
    # TL — "hindi po tutubo ang bagong ngipin"
    r"\\b(?:hindi|di)\\s+(?:po\\s+)?(?:na\\s+)?(?:\\w+\\s+)?(?:tutubo|tumutubo|makakatubo|magpapatubo|mapapatubo)\\b[^.!?\\n]{0,30}?\\bngipin",
    r"\\bngipin\\b[^.!?\\n]{0,30}?\\b(?:hindi|di)\\s+(?:po\\s+)?(?:na\\s+)?(?:tutubo|tumutubo)\\b",
    # AR — "لن تنبت أسنان جديدة", "لا يمكن أن تنمو أسنان جديدة" (phủ định phải sát động từ)
    r"(?:لن|لا)\\s+(?:ت|ي)(?:نبت|نمو)",
    r"(?:لا\\s+يمكن|مستحيل|غير\\s+ممكن)\\s+(?:\\S+\\s+){0,2}?(?:إنبات|انبات|نمو|تنبت|ينبت|تنمو|ينمو)",
    r"(?:إنبات|انبات|نمو)\\s+(?:\\S+\\s+){0,2}?(?:مستحيل|غير\\s+ممكن)",
    # BN — "দাঁত গজানো সম্ভব নয়", "দাঁত উঠবে না", "গজানো পেস্টের কাজ নয়", "দাঁত ওঠা নির্ভর করে…", "সত্যি নয়"
    _DANT + r"[^\\n।!?]{0,50}?(?:সম্ভব\\s*" + _KHONG_BN + r"|অসম্ভব)",
    _MOC_BN + _BN + r"*\\s*(?:" + _BN + r"+\\s*){0,3}?(?:সম্ভব\\s*" + _KHONG_BN + r"|অসম্ভব)",
    _DANT + r"[^\\n।!?]{0,30}?(?:গজাবে|গজা" + _Y + r"|গজাতে\\s*পার\\S*|উঠবে|ওঠে|উঠতে\\s*পার\\S*)\\s*" + _NA,
    _MOC_BN + _BN + r"*\\s*(?:" + _BN + r"+\\s*){0,3}?কাজ\\s*" + _KHONG_BN,
    _DANT + r"[^\\n।!?]{0,40}?" + _MOC_BN + r"[^\\n।!?]{0,40}?নির্ভর\\s*কর",
    r"সত্যি\\s*" + _NOY, r"সত্য\\s*" + _NOY, r"সত্যি\\s*না(?=\\s*[।!.,?]|\\s*$)",
    # HI — "नए दांत उगना संभव नहीं", "दांत नहीं उगेंगे", "सच नहीं"
    _HI_DANT + r"[^\\n।!?]{0,50}?(?:(?:संभव|सम्भव|मुमकिन)\\s*" + _HI_KHONG + r"|असंभव|असम्भव|नामुमकिन)",
    _HI_DANT + r"[^\\n।!?]{0,30}?(?:" + _HI_KHONG + r"\\s*उग|उग\\s*" + _HI_KHONG + r"|उग\\s*सक(?:ते|ता|ती)\\s*" + _HI_KHONG + ")",
    _HI_DANT + r"[^\\n।!?]{0,50}?निर्भर",
    r"सच\\s*" + _HI_KHONG,
    # UR — "نئے دانت اگنا ممکن نہیں", "دانت نہیں اگیں گے", "سچ نہیں"
    r"دانت[^\\n.!?۔]{0,50}?(?:ممکن\\s*" + _UR_KHONG + r"|ناممکن)",
    r"دانت[^\\n.!?۔]{0,30}?(?:" + _UR_KHONG + r"\\s*(?:اگ|اُگ)|(?:اگ|اُگ)\\S*\\s*" + _UR_KHONG + ")",
    r"دانت[^\\n.!?۔]{0,50}?منحصر",
    r"سچ\\s*" + _UR_KHONG,
]
PHUI_QC = re.compile("(?:" + PHUI_QC.pattern + ")|" + "|".join(_PHUI_NAM_A), re.I | re.U)
'''

CG_KIEM_MOC = '''    ("phủi: Ả Rập 'غير صحيح'",
     "غير صحيح ما ورد في الإعلان، لكن المنتج مفيد. هل تريد الطلب؟", {}, "chan", "phui_quang_cao"),
'''
CG_KIEM_THEM = CG_KIEM_MOC + '''    # ── 21/09 ca MD Shahin Mondol (Minty Fresh Smile KSA) — chối mọc răng bằng tiếng Bengali, cổng cũ mù ──
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
    ("KHÔNG phủi: Bengali bắc cầu + mời mua (ca Shahin)",
     "দাঁতের ছবি দেখলাম, MD Shahin 😊 নিয়মিত ব্যবহারে ধীরে ধীরে পার্থক্য বোঝা যাবে। আপনি কি ১ সেট নিতে চান? 📦",
     {}, "qua", None),
    ("KHÔNG phủi: Bengali 'ngoài COD không được' là luật thanh toán",
     "ক্যাশ অন ডেলিভারি ছাড়া অন্য পেমেন্ট সম্ভব নয়। আপনি কি অর্ডার করবেন?", {}, "qua", None),
'''

# ───────────────────────────── nap_luat.py: nạp khối 30 cho Bengali/Hindi/Urdu + hỏi mọc răng ─────────────────────────────
NL_MOC = '''# Khách hỏi hoàn tiền / trả lại / đổi khi không hiệu quả
HOI_HOAN_TIEN = re.compile('''
NL_THEM = '''# 21/09 (ca MD Shahin Mondol, Minty Fresh Smile KSA): khách Bangladesh hỏi bằng tiếng Bengali "এটা দিয়ে কি নতুন দাঁত
# উঠবে?" — hai mẫu trên chỉ biết Anh/Tagalog/Indo/Ả Rập nên khối 30 KHÔNG nạp, model soạn tự do rồi CHỐI quảng cáo
# ("নতুন দাঁত গজানো সম্ভব নয়"). Thêm: (1) nghi quảng cáo / hàng thật bằng Bengali · Hindi · Urdu (chữ gốc + chữ Latinh);
# (2) khách nhắc chuyện MỌC RĂNG MỚI ở mọi tiếng — lời hứa quảng cáo bị AI chối nhiều nhất (Minty Fresh Smile: 11/09 Manuel,
# 16/09 Tara Singh, 21/09 Shahin). Chữ Bengali không dùng \\b; "য়" có 2 cách gõ nên mẫu nhận cả hai.
_Y_BN = "(?:\\u09df|\\u09af\\u09bc)"
HOI_QC_NAM_A = re.compile("|".join([
    r"সত্যি|সত্য|আসল|নকল|ভু" + _Y_BN + r"া|প্রতারণা|প্রতারক|ধোঁকা|ধোকা|বাটপার|বিশ্বাস|প্রমাণ|বিজ্ঞাপন",
    r"কাজ\\s*(?:করবে|হবে)\\s*(?:তো|কি)|(?:কি|কী)\\s*কাজ\\s*(?:করবে|হবে)",
    r"सच|असली|नकली|धोखा|फ्रॉड|फ़्रॉड|यकीन|विश्वास|भरोसा|सबूत|विज्ञापन|काम\\s*कर(?:ेगा|ेगी)",
    r"سچ|اصلی|نقلی|دھوکہ|دھوکا|فراڈ|یقین|بھروسہ|ثبوت|اشتہار|کام\\s*کر(?:ے|ی)\\s*گ[اى]",
    r"\\b(?:sach|sachi|sacchi|sachhi|sotti|shotti|asli|nakli|nokol|dhoka|dhokha|fraud|froud|yakin|yakeen|vishwas|biswas"
    r"|bharosa|saboot|sabut|proman)\\b",
]), re.I | re.U)
HOI_MOC_RANG = re.compile("|".join([
    r"\\bnew\\s+(?:teeth|tooth)\\b", r"\\bre-?grow\\w*", r"\\bgrow\\w*\\s+back\\b",
    r"\\b(?:teeth|tooth)\\s+(?:will\\s+|to\\s+|can\\s+)?grow\\w*", r"\\bgrow\\w*\\s+(?:new\\s+|back\\s+)?(?:teeth|tooth)\\b",
    r"\\bbagong\\s+ngipin\\b", r"\\b(?:tutubo|tumubo|tumutubo|magpapatubo|patubuin|mapapatubo)\\b",
    r"\\bgigi\\s+baru\\b", r"\\btumbuh\\s+gigi\\b", r"\\bgigi\\s+(?:bisa\\s+|akan\\s+)?tumbuh\\b",
    r"أسنان\\s*جديدة|اسنان\\s*جديدة|سن\\s*جديد|ضرس\\s*جديد|تنبت|ينبت|إنبات|انبات|نمو\\s*(?:ال)?(?:أسنان|اسنان)",
    r"تطلع\\s*(?:ال)?(?:أسنان|اسنان|سن)|يطلع\\s*(?:ال)?(?:سن|ضرس)",
    r"নতুন\\s*দাঁত", r"দাঁত[^\\n।!?]{0,20}?(?:গজা|গজি|উঠ|ওঠ)", r"(?:গজা|গজি|উঠ|ওঠ)[^\\n।!?]{0,10}?দাঁত",
    r"न(?:ए|ये)\\s*दा[ँं]त", r"दा[ँं]त[^\\n।!?]{0,20}?उग", r"उग[^\\n।!?]{0,10}?दा[ँं]त",
    r"نئے\\s*دانت", r"دانت[^\\n.!?۔]{0,20}?(?:اگ|اُگ)",
    r"\\bnotun\\s+dat\\b", r"\\bdat\\s+(?:gojabe|gojbe|uthbe|ujbe)\\b", r"\\bna(?:y|)e\\s+da+nt\\b", r"\\bda+nt\\s+ug\\w*",
    r"mọc\\s+răng|răng\\s+mới|răng\\s+mọc",
]), re.I | re.U)
''' + NL_MOC
NL_DK_CU = '''    if HOI_QUANG_CAO.search(t) or NGHI_NGO_QC.search(t):
        khoi.append("30_quang_cao.md")'''
NL_DK_MOI = '''    if (HOI_QUANG_CAO.search(t) or NGHI_NGO_QC.search(t)
            or HOI_QC_NAM_A.search(t) or HOI_MOC_RANG.search(t)):      # 21/09 ca Shahin (Bengali)
        khoi.append("30_quang_cao.md")'''


def kiem():
    ok = True
    for f, cac in DAU.items():
        s = open(f, encoding="utf-8").read()
        for c in cac:
            n = s.count(c)
            print(("OK  " if n else "MẤT ") + f"{os.path.basename(f)}: {c}  ({n})")
            ok = ok and n > 0
    return ok


def main():
    if sys.argv[1:] == ["kiem"]:
        sys.exit(0 if kiem() else 1)
    cg = open(F_CG, encoding="utf-8").read()
    nl = open(F_NL, encoding="utf-8").read()
    if "_PHUI_NAM_A" in cg or "HOI_MOC_RANG" in nl:
        sys.exit("đã vá rồi — không ghi lại")
    for ten, s, cu in (("chan_gui PHUI_QC", cg, CG_MOC), ("chan_gui CA_KIEM", cg, CG_KIEM_MOC),
                       ("nap_luat HOI_HOAN_TIEN", nl, NL_MOC), ("nap_luat luat_tinh_huong", nl, NL_DK_CU)):
        n = s.count(cu)
        assert n == 1, f"{ten}: mốc khớp {n} lần (phải 1) — phiên khác đã sửa vùng này, KHÔNG ghi"
    cg2 = cg.replace(CG_MOC, CG_THEM, 1).replace(CG_KIEM_MOC, CG_KIEM_THEM, 1)
    nl2 = nl.replace(NL_MOC, NL_THEM, 1).replace(NL_DK_CU, NL_DK_MOI, 1)
    moc = time.strftime("%Y%m%d-%H%M")
    for f, cu, moi in ((F_CG, cg, cg2), (F_NL, nl, nl2)):
        tam = f + ".tam-phui-nam-a"
        open(tam, "w", encoding="utf-8").write(moi)
        py_compile.compile(tam, doraise=True)            # lỗi cú pháp thì dừng ở đây, file thật chưa đụng
    for f, cu, moi in ((F_CG, cg, cg2), (F_NL, nl, nl2)):
        open(f + f".bak-{moc}-truoc-phui-nam-a", "w", encoding="utf-8").write(cu)
        os.replace(f + ".tam-phui-nam-a", f)
        print(f"đã vá {f} (bak-{moc}-truoc-phui-nam-a)")
    print("--- kiểm lại dấu vết ---")
    sys.exit(0 if kiem() else 1)


if __name__ == "__main__":
    main()

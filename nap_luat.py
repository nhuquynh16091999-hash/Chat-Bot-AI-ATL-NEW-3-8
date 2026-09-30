"""BẢN NHÁP — CHƯA CÀI. Nạp luật theo nước / loại page / tình huống thay cho luat_model.md nguyên khối.

Cách ráp một lượt soạn:
  system[0] (lưu đệm) = 00_chung + (11_my_uc nếu Mỹ/Úc, không thì 10_cod)       → chỉ 2 bản, đệm luôn ấm
  system[1] (lưu đệm) = kịch bản page (on_dinh) + 20_tam_linh nếu page tư vấn theo bước
  cuối tin người dùng  = các khối 30-33 CHỈ khi phát hiện tình huống (không lưu đệm nên giữ khối ngắn)
Tắt bằng AI_LUAT_TACH=0 → quay về luat_model.md cũ ngay, không cần sửa code.
"""
import os
import re

THU_MUC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "luat")

# Khách hỏi quảng cáo có thật không / hàng thật không
HOI_QUANG_CAO = re.compile(
    r"\b(?:is (?:it|this|that) (?:true|real|legit|original)|really\??$|legit|scam|fake|real gold|original|ads? (?:said|say)|"
    r"advertis\w*|totoo|tutoo|peke|hindi ba (?:peke|scam)|asli|beneran|palsu|pure (?:gold|\d+k)|gold[ -]?plated|authentic)\b|صحيح|حقيقي|أصلي|نصب", re.I | re.U)
# …và kiểu NGHI NGỜ không dùng một chữ nào ở trên (ca Tara Singh 16/09, Minty Fresh Smile KSA): "You claim that new
# teeth will grow … I do not grasp how … satisfy my doubts—then I will place the order". Khối 30 không được nạp →
# model tự do viết "not actual teeth growing" → cổng phui_quang_cao chặn → khách KHÔNG được trả lời chữ nào.
NGHI_NGO_QC = re.compile(
    r"\b(?:you\s+(?:claim|claimed|say|said|promise[d]?|guarantee[d]?)"
    r"|how\s+(?:is|can|could|would)\s+(?:it|this|that|a|an|the)\b"
    r"|how\s+(?:does|do|did)\s+(?:it|this|that)\s+work"
    r"|(?:explain|clarify)\s+(?:to\s+me\s+)?(?:how|why|this)"
    r"|(?:do\s?n[o']?t|don[o']?t|cannot|can[o']?t|couldn[o']?t)\s+(?:understand|grasp|believe|see)\s+(?:how|why|this|that|it)\b"
    r"|(?:my|any|these|the)\s+doubts?|i\s+doubt\b|doubtful"
    r"|hard\s+to\s+believe|too\s+good\s+to\s+be\s+true|unbelievable"
    r"|proof|evidence|prove\s+it|any\s+study|studies|clinically\s+proven"
    r"|hindi\s+(?:po\s+)?(?:ako\s+)?naniniwala|mahirap\s+paniwalaan|patunay|paano\s+(?:po\s+)?(?:nangyari|nangyayari|gumagana)"
    r"|kok\s+bisa|gak\s+percaya|tidak\s+percaya|bukti(?:nya)?"
    r")\b|كيف\s+يمكن|لا\s+أصدق|ما\s+أصدق|دليل|أثبت|إثبات", re.I | re.U)
# 21/09 (ca MD Shahin Mondol, Minty Fresh Smile KSA): khách Bangladesh hỏi bằng tiếng Bengali "এটা দিয়ে কি নতুন দাঁত
# উঠবে?" — hai mẫu trên chỉ biết Anh/Tagalog/Indo/Ả Rập nên khối 30 KHÔNG nạp, model soạn tự do rồi CHỐI quảng cáo
# ("নতুন দাঁত গজানো সম্ভব নয়"). Thêm: (1) nghi quảng cáo / hàng thật bằng Bengali · Hindi · Urdu (chữ gốc + chữ Latinh);
# (2) khách nhắc chuyện MỌC RĂNG MỚI ở mọi tiếng — lời hứa quảng cáo bị AI chối nhiều nhất (Minty Fresh Smile: 11/09 Manuel,
# 16/09 Tara Singh, 21/09 Shahin). Chữ Bengali không dùng \b; "য়" có 2 cách gõ nên mẫu nhận cả hai.
_Y_BN = "(?:\u09df|\u09af\u09bc)"
HOI_QC_NAM_A = re.compile("|".join([
    r"সত্যি|সত্য|আসল|নকল|ভু" + _Y_BN + r"া|প্রতারণা|প্রতারক|ধোঁকা|ধোকা|বাটপার|বিশ্বাস|প্রমাণ|বিজ্ঞাপন",
    r"কাজ\s*(?:করবে|হবে)\s*(?:তো|কি)|(?:কি|কী)\s*কাজ\s*(?:করবে|হবে)",
    r"सच|असली|नकली|धोखा|फ्रॉड|फ़्रॉड|यकीन|विश्वास|भरोसा|सबूत|विज्ञापन|काम\s*कर(?:ेगा|ेगी)",
    r"سچ|اصلی|نقلی|دھوکہ|دھوکا|فراڈ|یقین|بھروسہ|ثبوت|اشتہار|کام\s*کر(?:ے|ی)\s*گ[اى]",
    r"\b(?:sach|sachi|sacchi|sachhi|sotti|shotti|asli|nakli|nokol|dhoka|dhokha|fraud|froud|yakin|yakeen|vishwas|biswas"
    r"|bharosa|saboot|sabut|proman)\b",
]), re.I | re.U)
HOI_MOC_RANG = re.compile("|".join([
    r"\bnew\s+(?:teeth|tooth)\b", r"\bre-?grow\w*", r"\bgrow\w*\s+back\b",
    r"\b(?:teeth|tooth)\s+(?:will\s+|to\s+|can\s+)?grow\w*", r"\bgrow\w*\s+(?:new\s+|back\s+)?(?:teeth|tooth)\b",
    r"\bbagong\s+ngipin\b", r"\b(?:tutubo|tumubo|tumutubo|magpapatubo|patubuin|mapapatubo)\b",
    r"\bgigi\s+baru\b", r"\btumbuh\s+gigi\b", r"\bgigi\s+(?:bisa\s+|akan\s+)?tumbuh\b",
    r"أسنان\s*جديدة|اسنان\s*جديدة|سن\s*جديد|ضرس\s*جديد|تنبت|ينبت|إنبات|انبات|نمو\s*(?:ال)?(?:أسنان|اسنان)",
    r"تطلع\s*(?:ال)?(?:أسنان|اسنان|سن)|يطلع\s*(?:ال)?(?:سن|ضرس)",
    r"নতুন\s*দাঁত", r"দাঁত[^\n।!?]{0,20}?(?:গজা|গজি|উঠ|ওঠ)", r"(?:গজা|গজি|উঠ|ওঠ)[^\n।!?]{0,10}?দাঁত",
    r"न(?:ए|ये)\s*दा[ँं]त", r"दा[ँं]त[^\n।!?]{0,20}?उग", r"उग[^\n।!?]{0,10}?दा[ँं]त",
    r"نئے\s*دانت", r"دانت[^\n.!?۔]{0,20}?(?:اگ|اُگ)",
    r"\bnotun\s+dat\b", r"\bdat\s+(?:gojabe|gojbe|uthbe|ujbe)\b", r"\bna(?:y|)e\s+da+nt\b", r"\bda+nt\s+ug\w*",
    r"mọc\s+răng|răng\s+mới|răng\s+mọc",
]), re.I | re.U)
# 23/09 (ca Fely F Castillo, Madam Mystic Fengshui Expert TW; chủ shop: "lại chối sản phẩm rồi"): khách hỏi "Pag nagkaroon po
# ba nyan tas tumaya ako s lotto mananalo" (đeo rồi đánh lotto có trúng không) → không khớp HOI_QUANG_CAO nên không khối nào nạp,
# model tự viết "Hindi namin maipapangako ang panalo sa lotto". Khách hỏi may mắn / trúng số / giàu / hiệu quả → nạp 36_may_man.md.
HOI_MAY_MAN = re.compile("|".join([
    r"\b(?:lotto|lottery|loto|jackpot|swertres|ez2|bingo|casino|raffle|sweepstakes?|jueteng|sabong|scratch\s*cards?|slots?)\b",
    r"\b(?:mananalo|manalo|panalo|mapanalo|panalunin|tataya|tumaya|taya|pustahan|sugal|magsugal|nagsusugal|sugarol)\b",
    r"\b(?:swerte|suwerte|swertehin|swertihin|suwertehin|masuwerte|maswerte|malas|kamalasan|minamalas|pampaswerte|pampa-?swerte"
    r"|pampasuwerte)\b",
    r"\b(?:luck|lucky|luckier|unlucky|fortunes?|misfortune|winnings?|jinx|cursed?)\b",
    r"\b(?:will|would|can|could|do|does)\s+(?:i|we|it|this|that|you)\s+(?:really\s+|surely\s+|definitely\s+)?"
    r"(?:win|earn|get\s+rich|become\s+rich|attract|bring)\b",
    r"\b(?:get|become|be|make\s+me)\s+(?:rich|wealthy|lucky)\b|\byayaman\b|\byumaman\b|\bkayamanan\b|\bmagiging\s+mayaman\b",
    r"\b(?:gagana|tatalab|uubra|gumagana|tumatalab|epektibo|epiktib\w*|epekti\w*|efekti\w*|mabisa|may\s+epekto|may\s+bisa)\b",
    r"\b(?:will|does|do|would|can|is)\s+(?:it|this|that|they)\s+(?:really\s+|actually\s+|truly\s+)?"
    r"(?:work|works|help|helps|effective|powerful|working|bring|attract|change)\b",
    r"\b(?:togel|judi|menang|hoki|keberuntungan|beruntung|rezeki|rejeki|kaya\s+raya|jadi\s+kaya|manjur|ampuh|berhasil|mujarab"
    r"|sial|kesialan)\b",
    r"يانصيب|اليانصيب|لوتو|\bحظ|حظي|الحظ|محظوظ|نحس|أربح|اربح|نربح|فوز|أفوز|افوز|قمار|رهان|ثروة|أغنى|اغنى|يفيد|ينفع|فعال|يجيب|بركة|رزق",
    r"লটারি|ভাগ্য|সৌভাগ্য|জিতব|জিততে|ধনী|কাজ\s*কর",
    r"लॉटरी|किस्मत|भाग्य|जीत|अमीर|काम\s*कर",
    r"لاٹری|قسمت|جیت|امیر|کام\s*کر",
]), re.I | re.U)
# Khách hỏi hoàn tiền / trả lại / đổi khi không hiệu quả
HOI_HOAN_TIEN = re.compile(
    r"\b(?:refund|money ?back|return (?:it|the|back)|can i return|exchange|guarantee|warranty|i ?balik|isauli|palit|"
    r"garantiya|kembalikan|dikembalikan|uang kembali|retur)\b|استرجاع|استرداد|ضمان|ترجيع", re.I | re.U)

# Khách hỏi CỬA HÀNG / đòi tới mua tận nơi (chủ shop 20/09: *"sao b k gửi store cho khách và hướng khách mua online
# để nhận ưu đãi"*). Đo trên 29.688 tin khách riêng (so_chi_phi, 8 nước): bắt 69 tin. Bẫy đã vá:
#   · "restore" chứa "store" → từ cửa hàng phải có \b hai đầu.
#   · "pick up" phần lớn là hẹn NHẬN HÀNG ("I will pick up my order") chứ không phải tới cửa hàng → bỏ hẳn nhánh đó.
#   · "center/office/clinic" hay nằm trong ĐỊA CHỈ khách gửi ("City centre salmya", "Chiffon center Al imam") → chỉ
#     tính khi đi kèm your/ur/niyo/kayo hoặc where/saan.
#   · "gold shop / any shop / shopee / mall / our shop" là cửa hàng NGƯỜI KHÁC → loại, trừ khi có "your/niyo".
# "pwesto/puwesto" = chỗ bán, cửa hàng (24/09, ca Delia Arcelao: "saan dto ang pwesto nyo" — bộ dò không nhận, luật 34 không nạp)
_CH_N = r"(?:stores?|shops?|branch(?:es)?|outlets?|showrooms?|tindahan|pwesto|puwesto|محلات?|معرض|فروع|فرع)"
_CH_N2 = r"(?:office|clinic|cent(?:er|re)|مركز|عيادة)"
# \b hai đầu là bắt buộc: không có thì "our shop" (cửa hàng CỦA KHÁCH) khớp nhầm vào "ur" — ca "that is my
# time here in our shop" (Bliss Gallery KSA, khách nói giờ làm ở tiệm của chính họ).
_CH_CUA_TOI = r"\b(?:your|you're|ur|yr|we're|inyo|niyo|nyo|ninyo|nio|nyu|kayo|namin)\b"
KHONG_PHAI_CH = re.compile(
    r"\b(?:gold|jewel\w*|pawn\w*|any|another|other|nearest|nearby|retail|lazada|tiktok|mall|online)\s+" + _CH_N
    + r"|\bshopping\s+(?:mall|cent(?:er|re))\b|\bshoppee?\b|\bonline\s+shop\b"
    + r"|\b(?:our|my|aming|aking)\s+(?:shop|store|tindahan)\b", re.I | re.U)
HOI_CUA_HANG = re.compile(
    r"\b(?:where|saan|nasaan|nsan|asan)\b[^.?!\n]{0,24}?\b" + _CH_N + r"\b"
    + r"|\b" + _CH_N + r"\b[^.?!\n]{0,20}?\b(?:location|address|adress|located|hours?|open|bukas)\b"
    + r"|\b(?:location|address|adress)\b[^.?!\n]{0,14}?\b" + _CH_N + r"\b"
    + r"|\b(?:send|give|share|provide)\b[^.?!\n]{0,20}?\b" + _CH_N + r"\b"
    + r"|\b(?:do|does)\s+(?:you|u|yu)\s+(?:have|hav)\b[^.?!\n]{0,20}?\b" + _CH_N + r"\b"
    + r"|\b(?:may|meron|mayroon|mern|mron)\b[^.?!\n]{0,20}?\b" + _CH_N + r"\b"
    + r"|\b" + _CH_N + r"\s+" + _CH_CUA_TOI + r"\b|" + _CH_CUA_TOI + r"\s+" + _CH_N + r"\b"
    + r"|\bphysical\s+(?:stores?|shops?|branch)\b|\bwalk[\s-]?in\b"
    + r"|\b(?:visit|come|go|drop|pass|stop)\b[^.?!\n]{0,16}?\b" + _CH_N + r"\b"
    + r"|\b(?:i|we)\s+(?:will|'ll|can|could|want\s+to|wanna|would\s+like\s+to|like\s+to)?\s*visit\b"
    + r"|\b(?:pumunta|punta|pupunta|papunta|bisita|bibisita|dumalaw|dadaan|dumaan)\b[^.?!\n]{0,24}?(?:\b" + _CH_N + r"\b|sa\s+inyo|sa\s+iyo|dyan|diyan|jan)"
    + r"|\b(?:mamili|mamimili)\b|\b(?:bumili|bibili|makabili)\b[^.?!\n]{0,24}?\b(?:saan|dyan|diyan|jan|mismo|mismong)\b"
    + r"|\bsaan\b[^.?!\n]{0,20}?\b(?:pwede|puwede|pede|puede)\b[^.?!\n]{0,14}?\b(?:bumili|mamili|kumuha|bili|order)\b"
    + r"|\bopen(?:ing)?\s+(?:hours?|time|times)\b|\banong\s+oras\b[^.?!\n]{0,20}?\b(?:bukas|nagbubukas|sarado)\b"
    + r"|\b(?:where|saan|nasaan|wherenis)\b[^.?!\n]{0,20}?\b" + _CH_N2 + r"\b"
    + r"|" + _CH_CUA_TOI + r"\s+" + _CH_N2 + r"\b|\b" + _CH_N2 + r"\s+" + _CH_CUA_TOI + r"\b"
    + r"|\b(?:visit|come\s+to|go\s+to|pumunta\s+sa)\b[^.?!\n]{0,14}?\b" + _CH_N2 + r"\b"
    + r"|\b(?:do|does)\s+(?:you|u)\s+have\b[^.?!\n]{0,14}?\b" + _CH_N2 + r"\b"
    + r"|(?:وين|اين|أين|فين)\s*(?:ال)?(?:محل|محلات|معرض|فرع|مركز|عيادة)"
    + r"|عنوان\s*(?:ال)?(?:محل|محلات|معرض|فرع|مركز|عيادة)"
    + r"|عند(?:كم|ك)\s*(?:ال)?(?:محل|محلات|معرض|فرع|مركز|عيادة)"
    + r"|(?:أزور|ازور|أجي|اجي|أروح|اروح)\s*(?:ال)?(?:محل|معرض|فرع|مركز|عندكم)",
    re.I | re.U)


def hoi_cua_hang(t):
    """Tin khách đang hỏi cửa hàng / đòi tới mua tận nơi?"""
    t = t or ""
    if not t.strip():
        return False
    if hoi_dinh_vi_shop(t):
        return True
    if KHONG_PHAI_CH.search(t) and not re.search(_CH_CUA_TOI, t, re.I):
        return False
    return bool(HOI_CUA_HANG.search(t))


# ── KHÁCH ĐÒI ĐỊA ĐIỂM MÀ KHÔNG DÙNG CHỮ store/shop (chủ shop 21/09, ca Elvie Dela Torre · ChunHo Golden Jewerly) ──
# "Send mi the location. Para di na ako mahirapan maghanap bukas" — HOI_CUA_HANG ở trên đòi phải có DANH TỪ cửa hàng
# nên trượt; khối 34 không nạp; model tự bịa đường "hindi po ako makakapag-send ng location namin" (kịch bản page có
# hẳn khối 3 cửa hàng). Đo 34.055 tin khách thật (so_chi_phi, 8 nước): nhánh này bắt thêm 62 tin, soát tay đều là
# khách đòi địa điểm CỦA SHOP. Bẫy đã vá:
#   · "our address …" → "ur" lọt vào giữa, phải \b hai đầu · "send q ung address", "Send ako Ng location",
#     "I'll just send the location on WhatsApp" = khách SẼ GỬI địa chỉ CỦA HỌ → _DV_CUA_KHACH loại.
#   · "your address is very far", "I kept your address" → "your + location" trơn chỉ tính khi có dấu hỏi / lời xin /
#     tin ngắn ≤5 chữ.  · đòi địa chỉ để TRẢ HÀNG (return/refund) là khiếu nại, không phải hỏi cửa hàng.
_DV = (r"\b(?:location|locaton|locatin|lokasyon|lokashon|address(?:es)?|adress|addres|"
       r"google\s*maps?|maps?|pin|gps|coordinates?|directions?)\b")
_DV_BAN = r"\b(?:your|you'?re|ur|yr|yours|niyo|nyo|ninyo|nio|nyu|kayo|inyo|yo)\b"
_DV_TOI = r"\b(?:me|mi|us|sakin|samin|akin)\b"
_DV_XIN = r"\b(?:send|snd|give|share|provide|forward|drop|pasend|pa-?send|pakisend|paki-?send|padala|ipadala)\b"
_DV_HOI = r"\b(?:where|wher|wer|were|when|what'?s?|saan|san|nasaan|nsan|asan|pwede|puwede|can|could|may|please|pls|plz|paki)\b"
_DV_CUA_KHACH = re.compile(
    r"\b(?:my|mine|akin|aking|amin|aming)\b\s*(?:\w+\s+){0,2}?" + _DV
    + r"|" + _DV + r"\s*(?:\w+\s+){0,2}?\b(?:ko|q|namin|nmin|natin|akin|aking|mo|ako|kami)\b"
    + r"|\b(?:i|we|ako|kami|ko|q|ill|i'?ll)\b(?:\s+\w+){0,3}?\s*" + _DV_XIN
    + r"|" + _DV_XIN + r"\s*(?:\w+\s+){0,2}?\b(?:you|u|yo|na|ko|q|ako|kami|namin|sayo|sa\s+inyo)\b"
    + r"|\b(?:sent|nasend|ipapadala|ibibigay)\b"
    + r"|\breturn\b|\brefund\b|\bmoney\s*back\b|\bcomplain\w*\b",
    re.I | re.U)

# Khách nói KHÔNG gửi được định vị ("Hindi nmin ma reach sa Google", "wala nakalagay na location para pindotin ko",
# "Hindi ko masend location ko, may WhatsApp po ba kayo?") → luật 35: xin số WhatsApp CỦA KHÁCH.
# Đo 34.055 tin: bắt 7. Bẫy: "not in my location now" (khách đang ở nước khác) và "not come in my location"
# (chuyện GIAO HÀNG) → bỏ "no|not" trơn khỏi vế phủ định; "can't you send your location" là đòi shop gửi → để cho 34.
_KHONG_DV = r"(?:hindi|hnd|hindo|di|wala|walang|wla|cannot|can'?t|cant|can\s+not|unable|dont|don'?t|doesn'?t|mahirap|ayaw)"
KHONG_GUI_DUOC_DV = re.compile(
    r"\b" + _KHONG_DV + r"\b[^.?!\n]{0,34}?\b(?:google|maps?|gps|pin|location|lokasyon|waze)\b"
    r"|\bno\b[^.?!\n]{0,12}?\b(?:google|maps?|gps|location|lokasyon)\b"
    r"|\b(?:google|maps?|gps|location|lokasyon)\b[^.?!\n]{0,24}?\b(?:not\s+working|error|hindi\s+gumagana|ayaw\s+gumana)\b"
    r"|\b(?:hindi|di|hnd)\s+ko\s+alam\b[^.?!\n]{0,30}?\b(?:send|magsend|location|maps?|pin|lokasyon)\b"
    r"|لا\s*(?:أستطيع|استطيع|اقدر|أقدر)[^.?!\n]{0,24}?(?:الموقع|خرائط|قوقل|جوجل)"
    r"|ما\s*(?:أقدر|اقدر)[^.?!\n]{0,24}?(?:الموقع|خرائط)",
    re.I | re.U)
_KHONG_PHAI_GUI_DV = re.compile(
    r"\b(?:deliver\w*|driver|courier|rider|shipping|ship|area|magdeliver|hatid)\b"
    r"|\b(?:can'?t|cant|cannot|why\s+don'?t)\s+(?:you|u|yu)\b", re.I | re.U)


def khong_gui_duoc_dinh_vi(t):
    """Khách kêu KHÔNG gửi được vị trí Google → nạp khối 35 (xin số WhatsApp CỦA KHÁCH)."""
    t = t or ""
    if not t.strip() or _KHONG_PHAI_GUI_DV.search(t):
        return False
    return bool(KHONG_GUI_DUOC_DV.search(t))


def hoi_dinh_vi_shop(t):
    """Khách đòi ĐỊA ĐIỂM / ĐỊNH VỊ của shop mà không dùng chữ store/shop."""
    t = t or ""
    if not t.strip() or _DV_CUA_KHACH.search(t) or khong_gui_duoc_dinh_vi(t):
        return False
    if re.search(_DV_XIN + r"(?:\s+\w+){0,2}?\s*" + _DV, t, re.I | re.U):
        return True
    if re.search(_DV_XIN + r"\s*" + _DV_TOI, t, re.I | re.U) and re.search(_DV, t, re.I | re.U):
        return True
    if re.search(r"\b(?:where|wher|wer|were|saan|san|nasaan|nsan|asan)\b[^.?!\n]{0,18}?" + _DV, t, re.I | re.U):
        return True
    if re.search(_DV + r"\s*" + _DV_BAN + r"|" + _DV_BAN + r"\s*" + _DV, t, re.I | re.U):
        return bool("?" in t or re.search(_DV_HOI, t, re.I | re.U) or len(t.split()) <= 5)
    return False



# LUẬT TIẾNG ANH (chủ shop duyệt 20/09 — cắt tiền): cùng một đoạn luật, bản tiếng Anh chỉ tốn ~60% token của bản tiếng Việt
# (đo bằng bộ đếm token của Kimi: 00_chung 9.494 → 5.736). luat/ vẫn là bản gốc tiếng Việt; luat_en/ là bản model đọc.
THU_MUC_ANH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "luat_en")
_DAU = re.compile(r"<!-- nguon_sha256: ([0-9a-f]{64}) -->\n")
_DA_BAO_LECH = set()


def _bat_luat_anh():
    """AI_LUAT_ANH trong .env — mặc định BẬT; "0" = chỉ dùng tiếng Việt. Đọc thẳng file mỗi lần (nap_luat không có env())."""
    try:
        with open(os.path.join(os.path.dirname(THU_MUC), ".env"), encoding="utf-8") as f:
            for l in f:
                if l.startswith("AI_LUAT_ANH="):
                    return l.split("=", 1)[1].strip() != "0"
    except OSError:
        pass
    return True


def _sha(t):
    import hashlib
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _ban_anh(ten, goc):
    """Bản tiếng Anh của `ten` nếu có và đóng dấu KHỚP bản tiếng Việt `goc`; không thì None."""
    p = os.path.join(THU_MUC_ANH, ten)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        t = f.read()
    m = _DAU.match(t)
    if m and m.group(1) == _sha(goc):
        return t[m.end():].strip()
    if ten not in _DA_BAO_LECH:
        _DA_BAO_LECH.add(ten)
        print(f"⚠️  luat_en/{ten} KHÔNG khớp luat/{ten} (bản tiếng Việt đã sửa sau lúc dịch) — dùng TIẾNG VIỆT tới khi "
              f"dịch lại + `python3 nap_luat.py dong_dau {ten}`", flush=True)
    return None


def _doc(ten):
    with open(os.path.join(THU_MUC, ten), encoding="utf-8") as f:
        goc = f.read()
    if _bat_luat_anh():
        anh = _ban_anh(ten, goc)
        if anh:
            return anh
    return goc.strip()


def luat_he_thong(mkey, thu_tien_sau=("usa", "australia")):
    """Phần luật nằm trong system — chỉ 2 biến thể nên bộ nhớ đệm của nhà cung cấp luôn trúng."""
    return _doc("00_chung.md") + "\n\n" + _doc("11_my_uc.md" if mkey in thu_tien_sau else "10_cod.md")


def luat_theo_page(on_dinh, kich_ban_theo_buoc):
    """Kịch bản page (đã lưu đệm theo page) + luật tâm linh nếu page tư vấn theo bước."""
    return on_dinh + ("\n\n" + _doc("20_tam_linh.md") if kich_ban_theo_buoc else "")


def luat_tinh_huong(noi_dung, tin_khach_cuoi):
    """Khối luật riêng cho đúng tình huống lượt này. `noi_dung` là gói gửi model (đã có các dòng ⚠️/⛔ hệ thống
    tự chèn); `tin_khach_cuoi` là các tin khách sau tin cuối của page."""
    t = " ".join(tin_khach_cuoi or [])
    khoi = []
    if (HOI_QUANG_CAO.search(t) or NGHI_NGO_QC.search(t)
            or HOI_QC_NAM_A.search(t) or HOI_MOC_RANG.search(t)):      # 21/09 ca Shahin (Bengali)
        khoi.append("30_quang_cao.md")
    if HOI_HOAN_TIEN.search(t):
        khoi.append("31_hoan_tien.md")
    if HOI_MAY_MAN.search(t):                                  # 23/09 ca Fely (may mắn / trúng số)
        khoi.append("36_may_man.md")
    if hoi_cua_hang(t):
        khoi.append("34_cua_hang.md")
    if khong_gui_duoc_dinh_vi(t):
        khoi.append("35_dinh_vi.md")
    if ("KHÁCH NÓI ĐÃ MUA HÀNG CỦA MÌNH" in noi_dung
            or "KHÁCH KHIẾU NẠI / ĐÒI HOÀN TIỀN MÀ KHÔNG CÓ ĐƠN" in noi_dung):
        khoi.append("32_da_mua_khong_don.md")
    if "KHÁCH HẸN NGÀY QUÁ HẠN" in noi_dung:
        khoi.append("33_hen_qua_han.md")
    return "\n\n".join(_doc(k) for k in khoi), khoi

# Chỗ nối trong ai_sale.py (sẽ vá bằng script assert count==1 khi được duyệt):
#   soan_bang_model():  he_thong = [khoi(luat_he_thong(mkey))] + [khoi(luat_theo_page(on_dinh, tam_linh))]
#                       noi_dung += "\n\nLUẬT RIÊNG CHO TÌNH HUỐNG NÀY:\n" + luat_tinh_huong(...)[0]   (nếu có)
#   mkey lấy từ dòng "bán ở thị trường <tt>" đầu on_dinh; tam_linh = kich_ban_theo_buoc(kb_page) is not None.


if __name__ == "__main__":
    import sys as _s
    if len(_s.argv) >= 3 and _s.argv[1] == "dong_dau":
        for ten in _s.argv[2:]:
            goc = open(os.path.join(THU_MUC, ten), encoding="utf-8").read()
            p = os.path.join(THU_MUC_ANH, ten)
            t = _DAU.sub("", open(p, encoding="utf-8").read(), count=1)
            open(p, "w", encoding="utf-8").write(f"<!-- nguon_sha256: {_sha(goc)} -->\n" + t)
            print(f"đã đóng dấu luat_en/{ten} theo luat/{ten} hiện tại")
    else:
        print("AI_LUAT_ANH:", "BẬT" if _bat_luat_anh() else "TẮT (chỉ tiếng Việt)")
        for ten in sorted(os.listdir(THU_MUC)):
            if not ten.endswith(".md"):
                continue
            goc = open(os.path.join(THU_MUC, ten), encoding="utf-8").read()
            if not os.path.exists(os.path.join(THU_MUC_ANH, ten)):
                tt = "chưa dịch → tiếng Việt"
            else:
                tt = "TIẾNG ANH (khớp)" if _ban_anh(ten, goc) else "LỆCH → tiếng Việt, cần dịch lại"
            print(f"  {ten:26} {tt}")

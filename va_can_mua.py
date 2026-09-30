"""Vá 14/09 tối — ca Lucy JJ (Madam Mystic Fengshui Expert USA): khách "You mean bibili ako iyang Golden Buddha?",
Botcake báo giá 199$ ngay 3 giây sau, model (cửa xét) vẫn chen vào; cổng nhắc giá bắt bỏ giá nên model mở đầu
"Hindi po basta bili lang…" (dịch ra "Đừng vội mua"). Chủ shop: *"sao lại đừng vội mua, bạn rep như này chết tôi"*.
Mỗi chỗ thay đúng 1 lần; lệch là thoát không ghi."""
import sys

D = sys.argv[1] if len(sys.argv) > 1 else "."


def vá(ten, cac_cho, dau):
    p = f"{D}/{ten}"
    src = open(p, encoding="utf-8").read()
    if dau in src:
        print(ten, "đã vá rồi — bỏ qua")
        return
    for cu, moi in cac_cho:
        n = src.count(cu)
        assert n == 1, f"{ten}: khớp {n} lần: {cu[:80]!r}"
        src = src.replace(cu, moi)
    open(p, "w", encoding="utf-8").write(src)
    print("đã vá", p)


CAN_MUA_RE = '''# CÂU CẢN KHÁCH MUA — chủ shop 14/09 tối, ca Lucy JJ (Madam Mystic USA): khách "You mean bibili ako iyang Golden
# Buddha?" → AI "Hindi po basta bili lang…" (đọc ra "Không/Đừng vội mua"). *"bạn rep như này chết tôi"*. Khách hỏi
# "vậy là phải mua à" thì đáp CÓ; không bao giờ mở đầu bằng phủ định chuyện mua.
CAN_MUA = re.compile(
    r"\\bhindi\\s+(?:po\\s+)?(?:basta|kailangan(?:g)?|sapilitan)\\s+(?:na\\s+|ang\\s+)?(?:bili|bumili|magbili|pagbili)"
    r"|\\bhuwag\\s+(?:po\\s+|kayo\\s+|mo\\s+)?(?:magmadali(?:ng)?\\s+(?:sa\\s+)?(?:pagbili|bumili)|bumili)"
    r"|\\bdon'?t\\s+(?:rush|hurry)\\s+(?:to\\s+|into\\s+)?(?:buy|order|purchas)|\\bno\\s+need\\s+to\\s+(?:buy|order|purchase)"
    r"|\\byou\\s+don'?t\\s+(?:have|need)\\s+to\\s+(?:buy|order|purchase)|\\bit'?s\\s+not\\s+(?:just\\s+)?(?:about\\s+)?(?:buying|selling)"
    r"|\\bnot\\s+just\\s+(?:a\\s+)?(?:purchase|buying)|đừng\\s+vội\\s+mua|không\\s+cần\\s+(?:phải\\s+)?mua"
    r"|لا\\s+تستعجل\\w*\\s+(?:في\\s+)?(?:ال)?شراء|لا\\s+داعي\\s+(?:لل|ل)?شراء", re.I | re.U)
'''

vá("chan_gui.py", [
    ('''    # ── 8-9. VĂN PHONG — chỉ soi câu AI TỰ VIẾT, không soi mẫu shop chép lại ──
''', '''    _cm = CAN_MUA.search(t)
    if _cm:
        pq.them(NANG, "can_mua",
                f"câu này CẢN khách mua ({_cm.group(0)!r}) — khách hỏi có phải mua không thì đáp CÓ + giá trị, "
                f"không bao giờ nói 'đừng vội mua / không chỉ là mua' (chủ shop 14/09, ca Lucy JJ)")
    # ── 8-9. VĂN PHONG — chỉ soi câu AI TỰ VIẾT, không soi mẫu shop chép lại ──
'''),
    ('''NANG, NHE, NHAC = "chan", "viet_lai", "nhac"
''', '''NANG, NHE, NHAC = "chan", "viet_lai", "nhac"
''' + "\n" + CAN_MUA_RE),
], "CAN_MUA")

vá("ai_sale.py", [
    # khách hỏi "có phải mua không" + Botcake đã báo giá bằng con số → im như hỏi giá
    ('''        if HOI_GIA.search(lam_sach(cuoi["text"]).lower()) and any(
                CG.tien_trong(m.get("text")) for m in bot_sau):
            return "im", "khách hỏi giá, Botcake đã báo giá bằng con số — không nhắn đè"
''', '''        if (HOI_GIA.search(lam_sach(cuoi["text"]).lower()) or HOI_MUA.search(lam_sach(cuoi["text"]))) and any(
                CG.tien_trong(m.get("text")) for m in bot_sau):
            return "im", "khách hỏi giá / hỏi có phải mua không, Botcake đã báo giá bằng con số — không nhắn đè"
'''),
    ('''    r"|كم|بكم|السعر|سعر|كام", re.I)
''', '''    r"|كم|بكم|السعر|سعر|كام", re.I)
# Khách hỏi về chuyện MUA ("You mean bibili ako?", "so I need to buy it?") — 14/09 tối, ca Lucy JJ.
HOI_MUA = re.compile(
    r"\\byou\\s+mean\\b[^.!?]{0,40}\\b(?:buy|bili|bibili|bumili|order|purchase)"
    r"|\\b(?:do|so|then)\\s+i\\s+(?:need|have)\\s+to\\s+(?:buy|order|purchase|pay)\\b"
    r"|\\bbibili\\s+(?:ba\\s+)?(?:po\\s+)?(?:ako|kami)\\b|\\bkailangan\\b[^.!?]{0,20}\\b(?:bumili|bilhin)\\b"
    r"|\\bhow\\s+much\\s+(?:do\\s+)?i\\s+(?:have|need)\\s+to\\s+pay", re.I)
'''),
    # cổng nhắc giá: hỏi mua cũng là hỏi giá; Botcake đáp sau tin khách không làm mất tin khách
    ('''    return any(HOI_GIA.search(t.lower()) for t in kh[:so_tin])
''', '''    return any(HOI_GIA.search(t.lower()) or HOI_MUA.search(t) for t in kh[:so_tin])
'''),
    ('''    kh = []
    for m in reversed(msgs or []):
        if m.get("boi") == "khach":
            if lam_sach(m.get("text") or "").strip():
                kh.append(lam_sach(m["text"]))
        elif m.get("boi") != "hethong":
            break
    return any(HOI_GIA''', '''    kh = []
    for m in reversed(msgs or []):
        if m.get("boi") == "khach":
            if lam_sach(m.get("text") or "").strip():
                kh.append(lam_sach(m["text"]))
        elif m.get("boi") == "botcake" and not kh:
            continue              # Botcake đáp ngay sau tin khách (cửa xét) — tin khách vẫn là tin cần xét
        elif m.get("boi") != "hethong":
            break
    return any(HOI_GIA'''),
    # luật cứng ở vòng soạn
    ('''                # KHÁCH VỪA CHỌN GÓI MÀ MODEL CHÀO HÀNG LẠI (chủ shop 14/09, KHACH_VUA_CHON_GOI) — chưa đủ
''', '''                # CÂU CẢN KHÁCH MUA (chủ shop 14/09 tối, ca Lucy JJ: "Hindi po basta bili lang…" = "đừng vội mua").
                # Bắt soạn lại 1 lần; vẫn cản → treo cho sale (cổng can_mua NANG là rào cuối).
                if (not err_m and qd and qd.get("hanh_dong") in ("tra_loi", "len_don", "tra_loi_treo")
                        and CG.CAN_MUA.search(qd.get("tin_nhan") or "")):
                    print(f"{nhan} 🚫 model viết câu CẢN khách mua — bắt soạn lại")
                    dem["can_mua"] = dem.get("can_mua", 0) + 1
                    qd2, e2 = soan_bang_model(
                        noi_dung + "\\n\\nSAI: bạn viết câu CẢN khách mua ('Hindi po basta bili lang', 'đừng vội mua', "
                        "'not just a purchase', 'no need to buy'…). Chủ shop cần bán hàng. Khách hỏi 'vậy là phải mua à?' "
                        "thì đáp CÓ (Yes po / Opo) + giá trị sản phẩm + giá page đã báo nếu có, rồi mời đặt. Viết lại "
                        "tin_nhan, KHÔNG có câu phủ định chuyện mua.", on_dinh)
                    if not e2 and qd2 and (qd2.get("tin_nhan") or "").strip() and not CG.CAN_MUA.search(qd2.get("tin_nhan") or ""):
                        qd = qd2
                    else:
                        qd = {"hanh_dong": "treo", "tin_nhan": "",
                              "ly_do": "AI định gửi câu cản khách mua",
                              "ghi_chu": "AI định nói 'đừng vội mua' — sale rep khách giúp"}
                # KHÁCH VỪA CHỌN GÓI MÀ MODEL CHÀO HÀNG LẠI (chủ shop 14/09, KHACH_VUA_CHON_GOI) — chưa đủ
'''),
], "HOI_MUA")

p = f"{D}/luat_model.md"
s = open(p, encoding="utf-8").read()
if "KHÔNG BAO GIỜ CẢN KHÁCH MUA" not in s:
    cu = "KHÁCH TỪ CHỐI / HOÃN MUA → GIỮ ƯU ĐÃI, KHÔNG THẢ KHÁCH"
    assert s.count(cu) == 1
    s = s.replace(cu, """KHÔNG BAO GIỜ CẢN KHÁCH MUA (chủ shop chốt 2026-09-14 tối, ca Lucy JJ — Madam Mystic USA): khách hỏi "You mean
bibili ako iyang Golden Buddha?" (vậy là tôi phải mua à?) → SAI: "Hindi po basta bili lang…" (đọc ra "Không/Đừng vội
mua"). Chủ shop: *"sao lại đừng vội mua, bạn rep như này chết tôi"*.
- Khách hỏi "có phải mua không / phải trả tiền không" → đáp CÓ ("Opo / Yes") + giá trị + giá page đã báo, rồi mời đặt.
- ⛔ CẤM mọi câu mở đầu phủ định chuyện mua: "Hindi po basta bili", "huwag magmadali sa pagbili", "don't rush to
  buy", "no need to buy", "it's not just about buying". Muốn nói "đây là vật linh thiêng" thì nói thẳng, không chêm "không chỉ là mua".
- Botcake vừa báo giá ngay sau câu hỏi của khách → IM, không nhắn đè.

""" + cu)
    open(p, "w", encoding="utf-8").write(s)
    print("đã vá", p)

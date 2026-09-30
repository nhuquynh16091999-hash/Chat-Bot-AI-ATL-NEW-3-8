#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VÁ 2026-09-20 — AI KHÔNG ĐƯỢC CHỐI VIỆC BÊN MÌNH NHẮN WHATSAPP.

Ca Marry F Mamauag (Golden Soap House KSA): khách "bạn nhắn cho tôi qua WhatsApp được không /
bên bạn đã nhắn tôi", AI đáp *"hindi po ako ang nag-message sa WhatsApp niyo… kung kanino po kayo
nag-usap doon, hindi po ako iyon"* — chối luôn. Chủ shop: *"nhân viên tôi nhắn cho khách mà"*.

Gốc là dòng luật sáng nay "đừng xác nhận số cũ" — model mở rộng thành phủ nhận. Nhân viên CÓ
liên hệ khách qua WhatsApp; chối là mất tin, mất đơn. Luật sửa ở luat/, cổng cứng ở đây.
"""
import re
import shutil
import sys

F = "/opt/pancake-tool/ai_sale.py"
BAK = F + ".bak-20260920-truoc-khong-choi-wa"
s = open(F, encoding="utf-8").read()


def thay(anchor, moi, ten):
    global s
    n = s.count(anchor)
    assert n == 1, f"{ten}: mốc xuất hiện {n} lần (phải đúng 1) — DỪNG"
    s = s.replace(anchor, moi, 1)
    print(f"  ✓ {ten}")


A1 = '''CHE_WA = "[dead WhatsApp number - never send it; ask the customer for THEIR WhatsApp instead]"
'''
M1 = A1 + '''

# CHỐI VIỆC BÊN MÌNH NHẮN WHATSAPP (chủ shop 20/09, ca Marry F Mamauag — Golden Soap House KSA).
# Nhân viên shop CÓ nhắn khách qua WhatsApp. Luật "không đưa số của mình" sáng nay bị model hiểu
# rộng thành phủ nhận: "hindi po ako ang nag-message sa WhatsApp niyo… hindi po ako iyon". Khách
# đang nói chuyện với đúng shop mà bị chối thì mất tin ngay. Cấm cứng, không tin prompt.
CHOI_WA = re.compile(
    r"hindi\\s+(?:po\\s+)?(?:ako|kami)\\s+(?:ang\\s+)?(?:nag-?|nagme|nag\\s)?(?:message|text|contact)"
    r"|hindi\\s+(?:po\\s+)?(?:ako|kami)\\s+(?:iyon|yun|yon|ito)"
    r"|(?:di|hindi)\\s+(?:po\\s+)?(?:ako|kami)\\s+(?:ang\\s+)?(?:nag-?(?:message|text|usap|kausap)|kausap)"
    r"|(?:that|it|this)\\s+(?:was\\s?n[o']?t|is\\s?n[o']?t|wasn't)\\s+(?:me|us)"
    r"|\\b(?:i|we)\\s+(?:did\\s?n[o']?t|didn't|never)\\s+(?:message|text|contact|write|send you)"
    r"|\\bnot\\s+(?:me|us)\\s+who\\b"
    r"|\\b(?:we|i)\\s+(?:do\\s?n[o']?t|don't)\\s+(?:have|use)\\s+whats?\\s*app"
    r"|wala\\s+(?:po\\s+)?kaming\\s+whats?\\s*app"
    r"|\\u0644\\u0633\\u062a\\s+\\u0623\\u0646\\u0627|\\u0644\\u0645\\s+\\u0623\\u0631\\u0627\\u0633\\u0644\\u0643|\\u0645\\u0627\\s+\\u0631\\u0627\\u0633\\u0644\\u062a\\u0643",
    re.I | re.U)
'''
thay(A1, M1, "1. regex CHOI_WA")


A2 = '''                # SỐ KHÔNG PHẢI SỐ BẢN ĐỊA Ở NƯỚC BẮT BUỘC (chủ shop 20/09, ca Lyn Amsiugal — Kuwait Amoura
'''
M2 = '''                # KHÔNG CHỐI VIỆC BÊN MÌNH NHẮN WHATSAPP (chủ shop 20/09, ca Marry F Mamauag). Nhân viên CÓ
                # nhắn khách qua WhatsApp — chối là khách mất tin ngay giữa lúc sắp chốt. Bắt viết lại 1 lần:
                # công nhận ngắn rồi làm tiếp việc đang dở ở đây; vẫn chối thì treo cho sale, thà im còn hơn.
                _tin_choi = ((qd or {}).get("tin_nhan") or "").strip()
                if (not err_m and qd and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo", "len_don")
                        and _tin_choi and CHOI_WA.search(_tin_choi)):
                    _cum_choi = CHOI_WA.search(_tin_choi).group(0)[:40]
                    print(f"{nhan} 🙅 chối đã nhắn WhatsApp [{_cum_choi}] — bắt viết lại")
                    dem["choi_wa"] = dem.get("choi_wa", 0) + 1
                    _nhe_choi = _thu_sua_nhe(
                        nhan, dem, "chối đã nhắn WhatsApp", _tin_choi,
                        "NEVER deny that we contacted the customer: our staff DO message customers on WhatsApp, so "
                        "\\"that wasn't me\\" / \\"hindi po ako ang nag-message\\" / \\"we don't have WhatsApp\\" is wrong and "
                        "costs their trust. Rewrite: acknowledge it briefly and warmly (yes, our team handles that), "
                        "then carry on with what you were doing here — ask for the location, the phone number, or the "
                        "bundle. Do NOT confirm any specific number and do NOT give out a number. Same language as the "
                        "draft, 1-2 short sentences, keep every price unchanged.", msgs,
                        lambda t: not CHOI_WA.search(t) and not WA_SHOP.search(t) and len(t) >= 30)
                    qd2, e2 = (dict(qd, tin_nhan=_nhe_choi), None) if _nhe_choi else soan_bang_model(
                        noi_dung + "\\n\\nSAI: tin_nhan CHỐI việc bên mình nhắn khách qua WhatsApp (\\"hindi po ako ang "
                        "nag-message\\", \\"that wasn't me\\", \\"bên mình không dùng WhatsApp\\"). Nhân viên shop CÓ nhắn "
                        "khách qua WhatsApp — chối là khách mất tin. Viết lại: công nhận ngắn gọn rồi làm tiếp việc "
                        "đang dở ở đây (xin vị trí / SĐT / chốt gói). KHÔNG xác nhận số cụ thể, KHÔNG đưa số nào. "
                        "Đúng tiếng khách, 1-2 câu.\\n\\nBản sai: «" + _tin_choi + "»", on_dinh)
                    _t2_choi = ((qd2 or {}).get("tin_nhan") or "").strip()
                    if not e2 and qd2 and _t2_choi and not CHOI_WA.search(_t2_choi) \\
                            and not WA_SHOP.search(_t2_choi) and qd2.get("hanh_dong") == qd.get("hanh_dong"):
                        qd = qd2
                    else:
                        print(f"{nhan} 🙅 viết lại vẫn chối — treo cho sale")
                        dem["choi_wa_treo"] = dem.get("choi_wa_treo", 0) + 1
                        qd = {"hanh_dong": "treo", "tin_nhan": "",
                              "ly_do": "AI chối việc bên mình nhắn WhatsApp",
                              "ghi_chu": "khách nói bên mình đã nhắn qua WhatsApp — sale trả lời tay, ĐỪNG chối, "
                                         "công nhận rồi chốt tiếp"}

''' + A2
thay(A2, M2, "2. cổng chặn câu chối — mọi lượt")

if "--thu" in sys.argv:
    print("… chạy thử, không ghi")
    sys.exit(0)
shutil.copy2(F, BAK)
open(F, "w", encoding="utf-8").write(s)
print(f"đã ghi {F} (sao lưu {BAK})")

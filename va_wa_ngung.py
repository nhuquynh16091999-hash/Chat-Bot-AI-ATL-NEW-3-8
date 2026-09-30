#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VÁ 2026-09-20 — SỐ WHATSAPP CỦA SHOP ĐÃ NGƯNG, ĐỔI SANG XIN SỐ CỦA KHÁCH.

Chủ shop 20/09: số WhatsApp đang nằm trong kịch bản đã ngưng hoạt động. Khách bấm vào
"wa.me/…" rồi nhắn thì KHÔNG AI nhận — mất đơn mà không ai biết. Đo cùng ngày:
  · kịch bản 286/337 page còn link/số: wa.me/12027736276 (272 mẫu), wa.me/971543610815 (213), 18702097265 (3)
  · log AI Sale còn giữ: 85 tin AI ĐÃ GỬI số đó ra cho khách
Prompt không đủ (model chép thẳng từ kịch bản), nên vá 4 tầng:
  1) khối kịch bản gửi model: che link, thay bằng nhắc "xin số của khách"
  2) cổng mọi lượt (kể cả bước kịch bản nguyên văn): tin có số shop → gỡ / bắt viết lại / treo
  3) lưới cuối ngay trước khi gửi thật: gỡ số khỏi mọi bong bóng, kể cả tin 2-3 của bước
  4) luật luat/00_chung.md + luat_en/00_chung.md (vá riêng, không ở file này)
"""
import re
import shutil
import sys

F = "/opt/pancake-tool/ai_sale.py"
BAK = F + ".bak-20260920-truoc-wa-ngung"
s = open(F, encoding="utf-8").read()


def thay(anchor, moi, ten):
    global s
    n = s.count(anchor)
    assert n == 1, f"{ten}: mốc xuất hiện {n} lần (phải đúng 1) — DỪNG, không sửa gì"
    s = s.replace(anchor, moi, 1)
    print(f"  ✓ {ten}")


# ───────────────────────── 1. Hằng + hàm gỡ số ─────────────────────────
A1 = '''def cat_cau_tha_khach(t):
    """Bỏ các câu/cụm thả khách ("Take your time!") khỏi tin; còn quá ngắn thì trả nguyên."""
    cau = re.split(r"(?<=[.!?])\\s+", t or "")
    giu = [c for c in cau if not THA_KHACH.search(c)]
    kq = " ".join(giu).strip()
    return kq if len(kq) >= 40 else (t or "")
'''

M1 = A1 + '''

# SỐ / LINK WHATSAPP CỦA SHOP ĐÃ NGƯNG (chủ shop 20/09, ca Ismail — Sakura Skin Care KSA: AI gửi
# "wa.me/+12027736276" cho khách xin WhatsApp). Số đó không còn ai nhận: khách nhắn vào là đơn chết
# lặng, sale cũng không thấy. Kịch bản 286/337 page vẫn còn link nên model chép ra rất dễ — prompt
# không đủ, phải chặn bằng máy. HƯỚNG MỚI: không đưa số của mình nữa, mà XIN SỐ WHATSAPP CỦA KHÁCH
# rồi shop nhắn trước, khách gửi vị trí ở đó.
# Có số WhatsApp mới chạy được thì bỏ số đó khỏi danh sách này — không phải sửa chỗ nào khác.
SO_WA_NGUNG = ("12027736276", "971543610815", "18702097265")


def _pat_so_wa(s):
    """Số viết rời ("+971 54 361 0815", "1-202-773-6276") vẫn phải bắt được."""
    return r"\\+?\\s*" + r"[\\s.\\u2011\\u2013()-]{0,2}".join(s)


WA_SHOP = re.compile(
    r"(?:https?://)?(?:www\\.)?(?:wa\\.me|wa\\.link|api\\.whatsapp\\.com/send|chat\\.whatsapp\\.com)/?\\S*"
    + "".join("|" + _pat_so_wa(x) for x in SO_WA_NGUNG), re.I | re.U)

CHE_WA = "[dead WhatsApp number - never send it; ask the customer for THEIR WhatsApp instead]"


def cat_wa_shop(t):
    """Bỏ HẲN câu nào có link/số WhatsApp đã ngưng; còn lại quá ngắn thì trả None.

    Cố ý KHÔNG gỡ mỗi con số trong câu: đo trên 96 tin AI đã gửi thật, gỡ trơ để lại câu cụt
    ("You can reach us on WhatsApp here:", "Our WhatsApp number is.") — khách đọc ra lỗi. Trả None
    = chỗ gọi phải soạn lại (xin số của KHÁCH) hoặc treo; thà im còn hơn gửi số chết.
    """
    goc = (t or "").strip()
    giu = [c for c in re.split(_NGAT_CAU, goc) if c.strip() and not WA_SHOP.search(c)]
    kq = _don_cau(" ".join(giu))
    if WA_SHOP.search(kq) or len(kq) < 40:
        return None
    return kq
'''
thay(A1, M1, "1. hằng SO_WA_NGUNG + WA_SHOP + cat_wa_shop()")


# ───────────────────── 2. Che số trong khối kịch bản gửi model ─────────────────────
A2 = '''    def khoi(m, tran_tin):
        t = "\\n".join(m["tin"])
'''
M2 = '''    def khoi(m, tran_tin):
        # Số WhatsApp trong mẫu đã NGƯNG (20/09): che ngay ở đầu vào thì model không có gì để chép,
        # đỡ phải gọi model sửa ở cổng đầu ra. Che tại chỗ nên mẫu vẫn giữ nguyên ý "liên hệ WhatsApp".
        t = WA_SHOP.sub(CHE_WA, "\\n".join(m["tin"]))
'''
thay(A2, M2, "2. che số trong khối kịch bản gửi model")


# ───────────────────── 3. Lưới cuối ngay trước khi gửi thật ─────────────────────
A3 = '''    Page bị Facebook chặn kênh Public API (#2022) → né sang kênh tài khoản (gui_tin_qua_user)
    ngay trong lần gửi này; page đã biết là bị chặn (_FB_CHAN) thì đi thẳng kênh tài khoản.
    """
'''
M3 = A3 + '''    # LƯỚI CUỐI CHO SỐ WHATSAPP ĐÃ NGƯNG (20/09) — cửa này mọi tin đều qua, kể cả mẫu shop gửi
    # nguyên văn và bong bóng thứ 2-3 của bước kịch bản (những đường mà cổng ở tầng quyết định cố ý
    # không đụng vào chữ của shop). Bong bóng chỉ có mỗi số thì bỏ hẳn, coi như đã xong: nội dung duy
    # nhất của nó là thứ bị cấm gửi.
    if text and WA_SHOP.search(text):
        _sach_wa = cat_wa_shop(text)
        if not _sach_wa:
            log(f"   📵 tin toàn số WhatsApp đã ngưng — KHÔNG gửi: {text[:100]!r}")
            return True, None
        log(f"   📵 bỏ câu có số WhatsApp đã ngưng khỏi tin sắp gửi: {text[:100]!r}")
        text = _sach_wa
'''
thay(A3, M3, "3. lưới cuối trong gui_tin()")


# ───────────────────── 4. Cổng mọi lượt ở tầng quyết định ─────────────────────
A4 = '''                            print(f"{nhan} 🪁 viết lại vẫn thả khách — giữ bản cũ")
                            dem["tha_khach_hong"] = dem.get("tha_khach_hong", 0) + 1
'''
M4 = A4 + '''
                # SỐ WHATSAPP CỦA SHOP ĐÃ NGƯNG — MỌI LƯỢT (chủ shop 20/09). Khác các cổng trên: cổng
                # này KHÔNG miễn cho mẫu của shop, vì chính kịch bản là nơi số chết nằm (286/337 page).
                # Rẻ trước: bước kịch bản thì gỡ bằng máy (0 đồng, giữ nguyên chữ shop); câu model tự
                # soạn thì bắt viết lại để XIN SỐ CỦA KHÁCH — đó mới là việc cần làm, gỡ trơ số đi là
                # câu cụt. Viết lại hỏng → gỡ máy; gỡ không được → treo, thà im còn hơn gửi số chết.
                _tin_wa = ((qd or {}).get("tin_nhan") or "").strip()
                if (not err_m and qd and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo", "len_don")
                        and _tin_wa and WA_SHOP.search(_tin_wa)):
                    _cum_wa = WA_SHOP.search(_tin_wa).group(0)[:40]
                    _cat_wa = cat_wa_shop(_tin_wa)
                    dem["wa_ngung"] = dem.get("wa_ngung", 0) + 1
                    if qd.get("buoc_kich_ban") and _cat_wa:
                        print(f"{nhan} 📵 gỡ số WhatsApp đã ngưng [{_cum_wa}] khỏi bước kịch bản bằng CODE")
                        dem["wa_ngung_cat"] = dem.get("wa_ngung_cat", 0) + 1
                        qd["tin_nhan"] = _cat_wa
                        if qd.get("tin_phan"):
                            _phan_wa = [p for p in (cat_wa_shop(x) if WA_SHOP.search(x) else x
                                                    for x in qd["tin_phan"]) if p]
                            if _phan_wa:
                                qd["tin_phan"] = _phan_wa
                            else:
                                qd.pop("tin_phan", None)
                    else:
                        print(f"{nhan} 📵 số WhatsApp đã ngưng [{_cum_wa}] — bắt viết lại, xin số của KHÁCH")
                        _nhe_wa = _thu_sua_nhe(
                            nhan, dem, "số WhatsApp ngưng", _tin_wa,
                            "Our shop's WhatsApp number is DEAD — nobody reads it, so sending it loses the order. "
                            "Rewrite with NO WhatsApp link or number of ours (\\"wa.me/…\\", \\"wa.link/…\\", any of our "
                            "phone numbers). Instead ASK THE CUSTOMER FOR THEIR OWN WhatsApp number and say you will "
                            "message them there right away so they can share their location with you; add that they "
                            "can also send it right here in this chat. Same language as the draft, 1-2 short "
                            "sentences, keep every price unchanged.", msgs,
                            lambda t: not WA_SHOP.search(t) and len(t) >= 30)
                        qd2, e2 = (dict(qd, tin_nhan=_nhe_wa), None) if _nhe_wa else soan_bang_model(
                            noi_dung + "\\n\\nSAI: tin_nhan có link/số WhatsApp CỦA SHOP — số đó ĐÃ NGƯNG HOẠT ĐỘNG, "
                            "khách nhắn vào không ai nhận, mất đơn. Viết lại tin_nhan KHÔNG có link/số WhatsApp nào "
                            "của mình; thay vào đó XIN SỐ WHATSAPP CỦA KHÁCH và nói mình sẽ nhắn cho khách ở đó ngay "
                            "để khách gửi vị trí (gửi luôn trong khung chat này cũng được). Đúng tiếng khách, 1-2 "
                            "câu, giữ nguyên mọi con số giá.\\n\\nBản sai: «" + _tin_wa + "»", on_dinh)
                        _t2_wa = ((qd2 or {}).get("tin_nhan") or "").strip()
                        if not e2 and qd2 and _t2_wa and not WA_SHOP.search(_t2_wa) \\
                                and qd2.get("hanh_dong") == qd.get("hanh_dong"):
                            qd = qd2
                        elif _cat_wa:
                            print(f"{nhan} 📵 viết lại vẫn kèm số ngưng — gỡ bằng CODE")
                            dem["wa_ngung_cat"] = dem.get("wa_ngung_cat", 0) + 1
                            qd["tin_nhan"] = _cat_wa
                        else:
                            print(f"{nhan} 📵 không gỡ được số WhatsApp ngưng — treo cho sale")
                            dem["wa_ngung_treo"] = dem.get("wa_ngung_treo", 0) + 1
                            qd = {"hanh_dong": "treo", "tin_nhan": "",
                                  "ly_do": "tin chỉ còn số WhatsApp đã ngưng",
                                  "ghi_chu": "AI định gửi số WhatsApp đã ngưng cho khách — sale trả lời tay: "
                                             "xin số WhatsApp CỦA KHÁCH rồi nhắn trước cho khách"}
'''
thay(A4, M4, "4. cổng số WhatsApp ngưng — mọi lượt")


# ───────────────────────── ghi ─────────────────────────
if "--thu" in sys.argv:
    print("… chạy thử, không ghi file")
    sys.exit(0)
shutil.copy2(F, BAK)
open(F, "w", encoding="utf-8").write(s)
print(f"đã ghi {F} (sao lưu: {BAK})")

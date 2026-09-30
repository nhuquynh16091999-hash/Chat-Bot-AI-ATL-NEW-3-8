#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Soạn bản THAY THẾ cho mẫu kịch bản có số WhatsApp đã ngưng — CHƯA GHI, chỉ in để duyệt.

Chủ shop 20/09: không có số mới, cứ XIN SỐ CỦA KHÁCH rồi nhân viên chủ động nhắn.
Sửa THEO DÒNG để giữ nguyên bố cục mẫu (gạch đầu dòng 👉, xuống dòng, emoji).
"""
import glob
import json
import re
import sys

SO = ("12027736276", "971543610815", "18702097265")


def _pat(s):
    return r"\+?\s*" + r"[\s.\u2011\u2013()-]{0,2}".join(s)


WA = re.compile(r"(?:https?://)?(?:www\.)?(?:wa\.me|wa\.link|api\.whatsapp\.com/send|chat\.whatsapp\.com)/?\S*"
                + "".join("|" + _pat(x) for x in SO), re.I | re.U)

# hai biến thể: (liên hệ / giao hàng) và (gửi vị trí)
CAU = {
    "en": ("Please send us your WhatsApp number — our team will message you there about your delivery.",
           "Please send us your WhatsApp number — our team will message you there so you can share your location."),
    "tl": ("Pakisend po ang WhatsApp number ninyo — kokontakin po kayo ng team namin doon para sa delivery.",
           "Pakisend po ang WhatsApp number ninyo — ime-message po kayo ng team namin doon para maipadala ninyo ang location."),
    "ar": ("أرسل لنا رقم الواتساب الخاص بك وسيتواصل معك فريقنا عليه بخصوص التوصيل.",
           "أرسل لنا رقم الواتساب الخاص بك وسيراسلك فريقنا عليه لترسل لنا موقعك."),
    "zh": ("請把您的 WhatsApp 號碼發給我們，我們的團隊會在 WhatsApp 上與您聯繫配送事宜。",
           "請把您的 WhatsApp 號碼發給我們，我們的團隊會在 WhatsApp 上聯繫您，您可以在那裡發送位置。"),
}
DICH = {
    "en": ("Gửi cho bên em số WhatsApp của anh/chị — nhân viên bên em sẽ nhắn ở đó về đơn giao.",
           "Gửi cho bên em số WhatsApp của anh/chị — nhân viên bên em nhắn ở đó để anh/chị gửi vị trí."),
    "tl": ("Gửi giúp em số WhatsApp của anh/chị — nhân viên bên em sẽ liên hệ ở đó về việc giao hàng.",
           "Gửi giúp em số WhatsApp của anh/chị — nhân viên bên em nhắn ở đó để anh/chị gửi vị trí."),
    "ar": ("Gửi cho bên em số WhatsApp của anh/chị — nhân viên bên em sẽ liên hệ ở đó về việc giao hàng.",
           "Gửi cho bên em số WhatsApp của anh/chị — nhân viên bên em nhắn ở đó để anh/chị gửi vị trí."),
    "zh": ("Gửi cho bên em số WhatsApp của anh/chị — nhân viên bên em sẽ liên hệ ở đó về việc giao hàng.",
           "Gửi cho bên em số WhatsApp của anh/chị — nhân viên bên em nhắn ở đó để anh/chị gửi vị trí."),
}
VI_TRI = re.compile(r"location|lokasyon|maps|موقع|位置|地址|pin\b", re.I | re.U)
# tiền tố đầu dòng cần giữ: "👉 ", "- ", "• ", "2️⃣ "…
DAU_DONG = re.compile(r"^(\s*(?:[-•*·]|\d+[.)]|[\U0001F300-\U0001FAFF\u2600-\u27BF][\uFE0F\u20E3]?)+\s*)")


def tieng(t):
    if re.search(r"[\u0600-\u06FF]", t):
        return "ar"
    if re.search(r"[\u4e00-\u9fff]", t):
        return "zh"
    if re.search(r"\b(?:po|niyo|ninyo|pwede|opo|salamat|ipadala|kayo|mo ako)\b", t, re.I):
        return "tl"
    return "en"


def thay_mot(tin):
    """Thay TỪNG DÒNG có số WhatsApp; giữ nguyên mọi dòng khác và bố cục."""
    if not WA.search(tin or ""):
        return tin, 0
    lg = tieng(tin)
    ra, n = [], 0
    for dong in (tin or "").split("\n"):
        if not WA.search(dong):
            ra.append(dong)
            continue
        n += 1
        # Trong dòng, chỉ thay ĐÚNG CÂU chứa số; câu khác của dòng giữ nguyên
        # ("via WhatsApp: wa.me/… We'll be happy to assist you! 😍" → giữ vế cuối).
        m = DAU_DONG.match(dong)
        dau = m.group(1) if m else ""
        than = dong[len(dau):]
        cau_ra, da = [], False
        for c in re.split(r"(?<=[.!?。！？])\s+", than):
            if WA.search(c):
                if not da:
                    cau_ra.append(CAU[lg][1 if VI_TRI.search(dong) else 0])
                    da = True
                continue
            if c.strip():
                cau_ra.append(c.strip())
        ra.append(dau + " ".join(cau_ra))
    return "\n".join(ra), n


if __name__ == "__main__":
    ds = []
    for f in sorted(glob.glob("/opt/pancake-tool/state/*/kich_ban.json")):
        mk = f.split("/")[-2]
        for pid, kb in json.load(open(f)).items():
            ten = kb.get("ten") or kb.get("ten_page") or kb.get("name") or pid
            for m in (kb.get("mau") or []):
                for tin in (m.get("tin") or []):
                    if WA.search(tin or ""):
                        moi, _ = thay_mot(tin)
                        ds.append((mk, pid, ten, m.get("tu_khoa") or "", tin, moi))
    print(f"TỔNG: {len(ds)} câu dính số · {len({(a, b) for a, b, *_ in ds})} page\n")
    dem = {}
    for *_, cu, _m in ds:
        k = tieng(cu)
        dem[k] = dem.get(k, 0) + 1
    print("theo tiếng:", dem, "\n")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    for mk, pid, ten, tk, cu, moi in ds[:0]:
        pass
    # chọn mẫu đa dạng: mỗi tiếng vài ca, ưu tiên ca dài (có bố cục)
    chon, seen = [], {}
    for r in sorted(ds, key=lambda x: -len(x[4])):
        k = tieng(r[4])
        if seen.get(k, 0) >= max(1, n // 2):
            continue
        seen[k] = seen.get(k, 0) + 1
        chon.append(r)
        if len(chon) >= n:
            break
    for mk, pid, ten, tk, cu, moi in chon:
        k = tieng(cu)
        vt = 1 if VI_TRI.search(cu) else 0
        print(f"── [{mk}] {ten} · mẫu /{tk} · tiếng={k}")
        print(f"   TRƯỚC:\n{cu[:500]}")
        print(f"   SAU:\n{moi[:500]}")
        print(f"   (dịch câu mới: {DICH[k][vt]})\n")

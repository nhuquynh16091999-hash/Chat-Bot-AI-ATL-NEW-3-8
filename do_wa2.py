#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đo hàm cắt trên 96 tin thật + đếm ca HỨA gửi số của shop (chưa kèm số)."""
import glob
import re
import sys
sys.path.insert(0, "/opt/pancake-tool")

SO_WA_NGUNG = ("12027736276", "971543610815", "18702097265")


def _pat_so_wa(s):
    return r"\+?\s*" + r"[\s.‑–()-]{0,2}".join(s)


WA_SHOP = re.compile(
    r"(?:https?://)?(?:www\.)?(?:wa\.me|wa\.link|api\.whatsapp\.com/send|chat\.whatsapp\.com)/?\S*"
    + "".join("|" + _pat_so_wa(x) for x in SO_WA_NGUNG), re.I | re.U)

_NGAT_CAU = re.compile("(?<=[.!?])\\s+|(?<=[\U0001F300-\U0001FAFF☀-➿❤])\\s+")


def _don_cau(t):
    t = re.sub(r"\s{2,}", " ", t or "").strip()
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r"([,—-]\s*)+([.!?])", r"\2", t)
    t = re.sub(r"^[\s,—-]+", "", t)
    t = re.sub(r"([.!?])\s*([,—])\s*", r"\1 ", t)
    return t[:1].upper() + t[1:] if t else t


def cat_wa_shop(t):
    goc = (t or "").strip()
    giu = [c for c in re.split(_NGAT_CAU, goc) if c.strip() and not WA_SHOP.search(c)]
    kq = _don_cau(" ".join(giu))
    if WA_SHOP.search(kq) or len(kq) < 40:
        return None
    return kq


DONG = re.compile(r"\]\s(?:💬|📨)\s(.+)$")
tin = []
for f in glob.glob("/var/log/aisale-chat*.log"):
    for l in open(f, encoding="utf-8", errors="replace"):
        m = DONG.search(l.rstrip("\n"))
        if m and m.group(1).strip():
            tin.append(m.group(1).strip())

bat = [t for t in tin if WA_SHOP.search(t)]
none = [t for t in bat if cat_wa_shop(t) is None]
print(f"bị bắt: {len(bat)} · cắt máy ra câu dùng được: {len(bat)-len(none)} · phải gọi model/treo: {len(none)}")
print("\n— 6 ca cắt máy OK (trước → sau) —")
n = 0
for t in bat:
    kq = cat_wa_shop(t)
    if kq and n < 6:
        n += 1
        print(f"  TRƯỚC: {t[:160]}\n  SAU  : {kq[:160]}\n")
print("— 5 ca KHÔNG cắt được (đi đường viết lại) —")
for t in none[:5]:
    print("  ·", t[:160])

HUA = re.compile(r"\b(?:send|give|share|provide)\s+(?:you\s+)?(?:my|our|the)\s+whats?\s*app"
                 r"|\b(?:my|our)\s+whats?\s*app\s*(?:number|no\b)"
                 r"|whats?\s*app\s*(?:namin|ko)\b", re.I)
hua = [t for t in tin if HUA.search(t) and not WA_SHOP.search(t)]
print(f"\n— HỨA gửi số WhatsApp CỦA SHOP mà chưa kèm số: {len(hua)} tin —")
for t in hua[:8]:
    print("  ·", t[:150])

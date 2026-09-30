#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đo CẢ HAI CHIỀU regex WA_SHOP trên tin AI đã gửi thật: bắt oan (số khách) và thả oan (số shop lọt)."""
import glob
import re

SO_WA_NGUNG = ("12027736276", "971543610815", "18702097265")


def _pat_so_wa(s):
    return r"\+?\s*" + r"[\s.‑–()-]{0,2}".join(s)


WA_SHOP = re.compile(
    r"(?:https?://)?(?:www\.)?(?:wa\.me|wa\.link|api\.whatsapp\.com/send|chat\.whatsapp\.com)/?\S*"
    + "".join("|" + _pat_so_wa(x) for x in SO_WA_NGUNG), re.I | re.U)

DONG = re.compile(r"\]\s(?:💬|📨)\s(.+)$")
tin = []
for f in glob.glob("/var/log/aisale-chat*.log"):
    for l in open(f, encoding="utf-8", errors="replace"):
        m = DONG.search(l.rstrip("\n"))
        if m and m.group(1).strip():
            tin.append(m.group(1).strip())
print("tin AI đã gửi đọc được:", len(tin))

bat = [t for t in tin if WA_SHOP.search(t)]
print("WA_SHOP bắt:", len(bat), f"({len(bat)/max(len(tin),1)*100:.2f}%)")
print("\n— CỤM BẮT ĐƯỢC (soi bắt oan) —")
cum = {}
for t in bat:
    for m in WA_SHOP.findall(t):
        pass
    c = WA_SHOP.search(t).group(0)
    cum[c] = cum.get(c, 0) + 1
for k, v in sorted(cum.items(), key=lambda x: -x[1])[:20]:
    print(f"  {v:4} {k!r}")

# THẢ OAN: tin có chữ whatsapp / wa. mà regex KHÔNG bắt
tha = [t for t in tin if not WA_SHOP.search(t)
       and re.search(r"whats?\s*app|wa\.me|wa\.link|واتس", t, re.I | re.U)]
print("\n— tin nhắc WhatsApp mà KHÔNG bị bắt:", len(tha), "(soi 12 ca) —")
for t in tha[:12]:
    print("   ·", t[:150])

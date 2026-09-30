#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gỡ BẢN SAO THỪA: page nằm trong thư mục mà shop POS của thư mục đó KHÔNG sở hữu.

Chạy SAU bước xếp lại, nên mọi page đã có mặt ở đúng thư mục của nó. Gỡ bản thừa là hết
cảnh hai thư mục tranh nhau token của cùng một page.
Fail-closed: thị trường nào không tra được shop thì KHÔNG đụng.
"""
import glob, json, os, shutil, sys, time
sys.path.insert(0, "/opt/pancake-tool")
os.chdir("/opt/pancake-tool")
import ai_sale as A

THAT = "--that" in sys.argv
tok = {f.split("/")[1]: json.load(open(f, encoding="utf-8"))
       for f in sorted(glob.glob("state/*/page_tokens.json"))}
shop = {}
for tt in tok:
    try:
        shop[tt] = A._pages_cua_shop(tt)
    except Exception:
        shop[tt] = None

moc = time.strftime("%Y%m%d-%H%M%S")
tong = 0
for tt, d in tok.items():
    if shop.get(tt) is None:
        print(f"  {tt:9s} ⚠️  không tra được shop — BỎ QUA")
        continue
    thua = [p for p, s in d.items() if s.get("token") and p not in shop[tt]]
    con = sum(1 for s in d.values() if s.get("token")) - len(thua)
    if not thua:
        continue
    tong += len(thua)
    print(f"  {tt:9s} gỡ {len(thua):4d} bản thừa · còn {con:4d} page đúng shop")
    if THAT:
        shutil.copy(f"state/{tt}/page_tokens.json",
                    f"state/{tt}/page_tokens.json.truoc-go-{moc}")
        for p in thua:
            d.pop(p, None)
        json.dump(d, open(f"state/{tt}/page_tokens.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
print(f"\n  tổng bản thừa: {tong}")
print("  ✅ đã gỡ" if THAT else "  → CHỈ SOI. Thêm --that để gỡ thật.")

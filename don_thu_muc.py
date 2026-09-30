#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Xếp lại page về ĐÚNG thư mục thị trường theo shop POS.

Không xoá mù: page nào POS bảo thuộc shop nào thì CHUYỂN về thư mục đó (giữ nguyên token,
tag, mọi thứ). Chỉ page KHÔNG thuộc shop nào của mình mới bị gỡ — và gỡ thì kê tên ra.
Mặc định CHỈ SOI, phải --that mới ghi.
"""
import collections, glob, json, os, shutil, sys, time
sys.path.insert(0, "/opt/pancake-tool")
os.chdir("/opt/pancake-tool")
import ai_sale as A

THAT = "--that" in sys.argv
tok = {f.split("/")[1]: json.load(open(f, encoding="utf-8"))
       for f in sorted(glob.glob("state/*/page_tokens.json"))}
ten = {}
for d in tok.values():
    ten.update({p: (s.get("name") or p) for p, s in d.items()})

# Hỏi POS MỘT LẦN cho mọi thị trường
shop = {}
for tt in tok:
    try:
        shop[tt] = A._pages_cua_shop(tt)
    except Exception:
        shop[tt] = None
tra_duoc = [t for t, v in shop.items() if v is not None]
print(f"\n  Tra được shop của {len(tra_duoc)}/{len(tok)} thị trường: {', '.join(tra_duoc)}")
if len(tra_duoc) < len(tok):
    print(f"  ⚠️  KHÔNG tra được: {', '.join(t for t in tok if shop[t] is None)} — sẽ không đụng vào")

chu = {}                      # page -> thị trường sở hữu theo POS
for tt in tra_duoc:
    for p in shop[tt]:
        chu.setdefault(p, tt)

o_dau = collections.defaultdict(list)
for tt, d in tok.items():
    for p, s in d.items():
        if s.get("token"):
            o_dau[p].append(tt)

chuyen, go, dung_cho = [], [], 0
for p, ds in o_dau.items():
    that_su = chu.get(p)
    if that_su and that_su in ds:
        dung_cho += 1
        continue
    if that_su:
        chuyen.append((p, that_su, ds))
    else:
        go.append((p, ds))

print(f"\n  ✅ đã đúng chỗ      : {dung_cho} page")
print(f"  ➡️  cần CHUYỂN về đúng thư mục : {len(chuyen)} page")
print(f"  🗑  không thuộc shop nào → gỡ  : {len(go)} page\n")
for p, t, ds in chuyen[:10]:
    print(f"    {ten.get(p,p)[:40]:42s} {','.join(ds):22s} → {t}")
if len(chuyen) > 10:
    print(f"    … còn {len(chuyen)-10} page")
if go:
    print()
    for p, ds in go[:6]:
        print(f"    gỡ  {ten.get(p,p)[:40]:42s} (đang ở {','.join(ds)})")
    if len(go) > 6:
        print(f"    … còn {len(go)-6} page")

if not THAT:
    sys.exit(print("\n  → CHỈ SOI. Thêm --that để làm thật."))

moc = time.strftime("%Y%m%d-%H%M%S")
for tt in tok:
    shutil.copy(f"state/{tt}/page_tokens.json", f"state/{tt}/page_tokens.json.truoc-xep-{moc}")
for p, t, ds in chuyen:
    ban = next(tok[x][p] for x in ds)          # giữ nguyên token + tag đang có
    tok[t][p] = ban
    for x in ds:
        if x != t:
            tok[x].pop(p, None)
for p, ds in go:
    for x in ds:
        tok[x].pop(p, None)
for tt, d in tok.items():
    json.dump(d, open(f"state/{tt}/page_tokens.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    n = sum(1 for s in d.values() if s.get("token"))
    print(f"  {tt:9s} còn {n:4d} page có token")
print(f"\n  ✅ xong · sao lưu: state/*/page_tokens.json.truoc-xep-{moc}")

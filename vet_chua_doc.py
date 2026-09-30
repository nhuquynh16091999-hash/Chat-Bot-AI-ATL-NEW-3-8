#!/usr/bin/env python3
"""Quét sổ việc, hội thoại nào AI đã gửi tin thật mà cờ đang "đã đọc" thì đánh lại.

Sinh ra vì đo 2026-09-10: API /unread báo success nhưng Pancake lật lại 4/5 ca.
Dùng như lưới vét sau mỗi vòng chạy thật.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quet_hoi_thoai as Q, ai_sale as A

mkey = sys.argv[1] if len(sys.argv) > 1 else "uae"
that = "--that" in sys.argv
Q.set_state_dir(os.path.join(Q.SCRIPT_DIR, "state", mkey))
so = os.path.join(Q.SCRIPT_DIR, "state", mkey, "so_viec.jsonl")
d = [json.loads(l) for l in open(so, encoding="utf-8") if l.strip()]
d = [x for x in d if x.get("that") and x.get("tin")]
seen = set(); cases = []
for x in d:                       # mỗi hội thoại 1 lần, lấy lượt mới nhất
    k = (x["pid"], x["conv"])
    if k in seen: continue
    seen.add(k); cases.append(x)
toks = Q.load_json(Q.TOKENS_FILE, {})
print(f"soát {len(cases)} hội thoại AI đã gửi tin thật ({mkey}):")
for x in cases:
    tok = (toks.get(str(x["pid"])) or {}).get("token")
    if not tok:
        print("  ⚠️  không có token:", x["khach"]); continue
    da, err = A._co_da_doc(x["pid"], x["conv"], tok)
    if da is None:
        print("  ⚠️  không đọc được cờ:", x["khach"], "—", err); continue
    if not da:
        print("  ✅ đang CHƯA ĐỌC:", x["khach"], "·", x["page"]); continue
    if not that:
        print("  ❗ đang ĐÃ ĐỌC (sẽ đánh lại):", x["khach"], "·", x["page"]); continue
    ok, e = A.danh_dau_chua_doc(x["pid"], x["conv"], tok, dry=False)
    print(("  ✅ đã đánh lại: " if ok else f"  🚨 ĐÁNH LẠI HỎNG ({e}): ") + x["khach"] + " · " + x["page"])

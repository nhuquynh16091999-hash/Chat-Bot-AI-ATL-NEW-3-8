#!/usr/bin/env python3
"""Ghi chú nội bộ cho 15 hội thoại AI đã lỡ nhắn đè lên Botcake (10/09/2026).

Chủ shop duyệt: sale cần biết đường xử, đừng để khách treo đó.
Chạy khan mặc định; thêm --that mới ghi thật.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quet_hoi_thoai as Q, ai_sale as A

mkey = "uae"; that = "--that" in sys.argv
Q.set_state_dir(os.path.join(Q.SCRIPT_DIR, "state", mkey))
toks = Q.load_json(Q.TOKENS_FILE, {})
d = [json.loads(l) for l in open(f"state/{mkey}/so_viec.jsonl", encoding="utf-8") if l.strip()]
seen, cases = set(), []
for x in [k for k in d if k.get("that") and k.get("tin")]:
    if (x["pid"], x["conv"]) in seen: continue
    seen.add((x["pid"], x["conv"])); cases.append(x)

GC = ("[AI Sale] 10/09: AI tự nhắn cho khách MỘT tin trong khi Botcake đã trả lời trúng "
      "câu khách hỏi rồi — tin thừa, lỗi của tool, đã sửa luật để không lặp lại. "
      "Nhờ sale đọc lại đoạn chat và chốt tiếp giúp. Tin AI đã gửi: ")

print(f"{'GHI THẬT' if that else 'CHẠY THỬ'} — {len(cases)} hội thoại:")
for x in cases:
    tok = (toks.get(str(x["pid"])) or {}).get("token")
    if not tok:
        print("  ⚠️  không có token:", x["khach"]); continue
    _, cus, err = A.tin_cua_hoi_thoai(x["pid"], x["conv"], tok)
    if not cus:
        print("  ⚠️  không lấy được mã khách:", x["khach"], err or ""); continue
    noi = GC + (x["tin"] or "")[:180].replace("\n", " ")
    if not that:
        print(f"  · {x['khach'][:24]:26s} · {x['page'][:28]}"); continue
    ok, e = A.ghi_chu(x["pid"], cus, tok, noi, dry=False)
    print(("  ✅ " if ok else f"  🚨 HỎNG ({e}) ") + f"{x['khach'][:24]:26s} · {x['page'][:28]}")

import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q
PID = "1300508383138780"
tok = json.load(open("state/uae/page_tokens.json", encoding="utf-8"))[PID]["token"]
res, _ = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{PID}/conversations",
                     {"page_access_token": tok, "since": int(time.time())-86400*4,
                      "until": int(time.time()), "order_by": "updated_at"})
for c in (res or {}).get("conversations") or []:
    ten = ((c.get("customers") or [{}])[0].get("name") or "")
    if not ten.startswith("Arlene"):
        continue
    print(f"  Hội thoại: {ten}\n")
    so = [x.get("captured") or x.get("phone_number") for x in (c.get("recent_phone_numbers") or [])]
    for cu in (c.get("customers") or []):
        so += [x.get("phone_number") for x in (cu.get("recent_phone_numbers") or [])]
    so = [s for s in dict.fromkeys(so) if s]
    print(f"  Số Pancake đã ghi lại trong hội thoại này: {so}")
    print(f"  Số SALE dùng để lên đơn #48962           : 0506051046")
    print(f"  → Có nằm trong danh sách? {'✅ CÓ — tra là ra đơn' if '0506051046' in so else '🚨 KHÔNG — vẫn mù'}")
    break

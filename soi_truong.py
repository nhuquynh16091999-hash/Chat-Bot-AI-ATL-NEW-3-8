import json, os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q, time
tokens = Q.load_json("state/uae/page_tokens.json", {})
pid, st = next((p, s) for p, s in tokens.items() if s.get("token") and not s.get("token_hong"))
res, err = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{pid}/conversations",
                       {"page_access_token": st["token"], "since": int(time.time())-86400,
                        "until": int(time.time()), "order_by": "updated_at"})
cs = (res or {}).get("conversations") or []
print(f"  page {st.get('name')} — {len(cs)} hội thoại 24h\n")
if cs:
    c = cs[0]
    print("  Các trường có sẵn trong DANH SÁCH hội thoại (không cần đọc tin nhắn):")
    for k in sorted(c):
        v = c[k]
        print(f"    {k:28s} {str(v)[:70]}")

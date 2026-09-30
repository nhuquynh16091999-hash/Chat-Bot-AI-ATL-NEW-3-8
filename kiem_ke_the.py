import json, os, sys, time, collections
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q
Q.set_state_dir("state/uae")
tok = json.load(open("state/uae/page_tokens.json", encoding="utf-8"))
song = [(p, s) for p, s in tok.items() if s.get("token") and not s.get("token_hong")][:25]
dem = collections.Counter(); n = 0
for pid, st in song:
    res, err = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{pid}/conversations",
                           {"page_access_token": st["token"],
                            "since": int(time.time())-86400*2, "until": int(time.time()),
                            "order_by": "updated_at"})
    if err: continue
    for c in (res or {}).get("conversations") or []:
        n += 1
        for t in (c.get("tags") or []):
            if t and t.get("text"):
                dem[t["text"]] += 1
    time.sleep(0.15)
print(f"  Thẻ đang dùng trên {n} hội thoại UAE (48h, {len(song)} page):\n")
for ten, c in dem.most_common(28):
    print(f"    {c:4d}  {ten}")

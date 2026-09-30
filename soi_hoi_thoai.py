import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q
Q.set_state_dir("state/uae")
PID = "1246701271865447"
tok = Q.load_json("state/uae/page_tokens.json", {})[PID]["token"]
res, err = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{PID}/conversations",
                       {"page_access_token": tok, "since": int(time.time())-86400*2,
                        "until": int(time.time()), "order_by": "updated_at"})
for c in (res or {}).get("conversations") or []:
    cid = str(c.get("id"))
    if cid[-18:] not in ("_27939682652348902"[-18:], "_28202929212731094"[-18:]):
        continue
    ten = ((c.get("customers") or [{}])[0].get("name") or "?")
    print(f"\n══════ {ten} ══════")
    print(f"  TAGS đang gắn : {[t.get('text') for t in (c.get('tags') or []) if t]}")
    print(f"  địa chỉ đã lưu: {len((c.get('customers') or [{}])[0].get('shop_customer_addresses') or [])}")
    m, err2 = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{PID}/conversations/{cid}/messages",
                          {"page_access_token": tok})
    tin = (m or {}).get("messages") or []
    print(f"  {len(tin)} tin — 12 tin cuối:")
    for t in tin[-12:]:
        f = t.get("from") or {}
        ai = "KHÁCH" if str(f.get("id")) != PID else (f.get("admin_name") or "hệ thống")
        print(f"    [{ai[:12]:12s}] {(t.get('message') or '(ảnh/đính kèm)')[:110]}")

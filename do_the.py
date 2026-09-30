import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q
Q.set_state_dir("state/uae")
tok = json.load(open("state/uae/page_tokens.json", encoding="utf-8"))
CA = [("Veloura Collection", "Arlene Cantero"),
      ("Leg Glow Lab UAE", "Elle Chim"),
      ("BodyFirm Essentials UAE", "Jori Khan"),
      ("Ginger Belly Care UAE", "MD Ahasan")]
for ten_page, ten_khach in CA:
    pid = next((p for p, s in tok.items() if (s.get("name") or "").startswith(ten_page[:20])), None)
    if not pid:
        print(f"  {ten_page}: không thấy page"); continue
    res, err = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{pid}/conversations",
                           {"page_access_token": tok[pid]["token"],
                            "since": int(time.time())-86400*3, "until": int(time.time()),
                            "order_by": "updated_at"})
    for c in (res or {}).get("conversations") or []:
        nk = ((c.get("customers") or [{}])[0].get("name") or "")
        if not nk.lower().startswith(ten_khach.split()[0].lower()):
            continue
        tags = [t for t in (c.get("tags") or []) if t]
        print(f"\n  {ten_khach} @ {ten_page}")
        for t in tags:
            print(f"      id={t.get('id')!r:>6}  {t.get('text')!r}")
        break
    time.sleep(0.3)

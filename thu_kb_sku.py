import json, os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as A, ket_nap_page as K

tong = cu_ra = kb_ra = 0
vd = []
for mkey in ("uae", "saudi", "kuwait", "usa"):
    A.set_market(mkey)
    catalog = K.tai_catalog()
    if not catalog:
        continue
    tok = json.load(open(f"state/{mkey}/page_tokens.json", encoding="utf-8"))
    try: kb = json.load(open(f"state/{mkey}/kich_ban.json", encoding="utf-8"))
    except Exception: kb = {}
    sp = json.load(open(f"state/{mkey}/page_products.json", encoding="utf-8")) if os.path.exists(f"state/{mkey}/page_products.json") else {}
    try: hs = json.load(open(f"state/{mkey}/page_ho_so.json", encoding="utf-8"))
    except Exception: hs = {}
    for pid, st in tok.items():
        if not st.get("token") or st.get("token_hong"):
            continue
        if (sp.get(pid) or {}).get("variation_id") or (hs.get(pid) or {}).get("variation_id"):
            continue                          # đã có SKU rồi
        v = kb.get(pid) or {}
        if not v.get("mau"):
            continue
        tong += 1
        # nguồn MỚI: kịch bản
        chu_kb = "\n".join(t for m in v["mau"] for t in (m.get("tin") or []))[:6000]
        r2, tin2, _ = K.chot_sku_bang_luat(st.get("name") or "", chu_kb, [], catalog)
        if r2:
            kb_ra += 1
            if len(vd) < 6:
                vd.append((mkey, st.get("name"), r2.get("ten"), tin2))
print(f"  {tong} page CHƯA có SKU (có kịch bản, token sống)\n")
print(f"  Dùng KỊCH BẢN để khớp tên  ->  chốt được {kb_ra} page  ({kb_ra*100//max(tong,1)}%)\n")
for m, p, s, t in vd:
    print(f"    [{m}] {(p or '')[:34]:36s} -> {(s or '')[:40]}")

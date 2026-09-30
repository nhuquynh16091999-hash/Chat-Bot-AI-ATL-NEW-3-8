import json, os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
o = P.api("GET", f"/shops/{P.SHOP_ID}/orders/48962")
o = (o or {}).get("data") or o
print("── Các trường ĐỊNH DANH KHÁCH trên đơn #48962 ──")
for k in sorted(o):
    if any(t in k.lower() for t in ("customer", "fb", "psid", "social", "account")):
        v = o[k]
        print(f"   {k:24s} {str(v)[:120]}")
print("\n── Thử tra theo tên khách ──")
for ten in ("Arlene Cantero", "Elle Chim"):
    ds = P.fetch_orders({"page_size": 50, "page_number": 1, "search": ten})
    print(f"   search={ten!r} → {len(ds)} đơn")
    for x in ds[:4]:
        print(f"      #{x.get('id')} · {P.STATUS_BY_CODE.get(x.get('status'),x.get('status')):12s}"
              f" · {x.get('bill_phone_number')} · conv {str(x.get('conversation_id'))[-18:]}")

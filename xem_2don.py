import os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
for oid in ("48962", "49226"):
    o = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
    o = (o or {}).get("data") or o
    if not isinstance(o, dict) or not o.get("id"):
        print(f"  #{oid}: không đọc được\n"); continue
    print(f"── #{oid} ──")
    for k in ("id","display_id","status","bill_full_name","bill_phone_number",
              "page_id","conversation_id","inserted_at"):
        print(f"     {k:18s} {o.get(k)!r}")
    sa = o.get("shipping_address") or {}
    print(f"     {'địa chỉ':18s} {str(sa.get('full_address') or sa.get('address'))[:70]!r}")
    print(f"     {'sđt ship':18s} {sa.get('phone_number')!r}")
    print(f"     {'trạng thái':18s} {P.STATUS_BY_CODE.get(o.get('status'), o.get('status'))}")
    print()

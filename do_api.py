import os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
CONV = "1300508383138780_27839097342409393"   # Arlene Cantero
MONG = "48962"
o = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{MONG}")
o = (o or {}).get("data") or o
cus = (o.get("customer") or {})
print(f"  đơn #{MONG}: customer.id = {cus.get('id')!r}\n")
thu = [
    ("conversation_id", {"conversation_id": CONV}),
    ("conversation_ids", {"conversation_ids": CONV}),
    ("customer_id", {"customer_id": cus.get("id")}),
    ("customer_ids", {"customer_ids": cus.get("id")}),
    ("search=conv", {"search": CONV}),
]
for ten, extra in thu:
    if any(v is None for v in extra.values()):
        print(f"  {ten:20s} (bỏ qua — thiếu giá trị)"); continue
    try:
        ds = P.fetch_orders({"page_size": 50, "page_number": 1, **extra})
        ids = [str(x.get("id")) for x in ds]
        print(f"  {ten:20s} → {len(ds):3d} đơn · có #{MONG}? "
              f"{'✅ CÓ' if MONG in ids else 'không'}"
              + (f" · {ids[:6]}" if 0 < len(ds) <= 8 else ""))
    except Exception as e:
        print(f"  {ten:20s} ✖ {str(e)[:60]}")

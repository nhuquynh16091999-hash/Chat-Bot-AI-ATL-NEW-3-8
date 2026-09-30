import os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
CA = [("Jori Khan","0564605687"), ("Arlene Cantero","0565979121"),
      ("MD Ahasan","0545615707"), ("Muhammad Ramzan","0567748303"),
      ("Elle Chim","0521723813"), ("Felsa Babor","0509674764"),
      ("Vange Carias","0529396654")]
print("Tra TOÀN BỘ lịch sử đơn theo SĐT (không giới hạn thời gian):\n")
for ten, sdt in CA:
    ds = P.fetch_orders({"page_size": 100, "page_number": 1, "search": sdt})
    song = [o for o in ds if o.get("status") not in (6, 7)]
    print(f"  {ten:18s} {sdt}  → {len(ds)} đơn ({len(song)} chưa hủy)")
    for o in ds:
        print(f"      #{o.get('id')} · {P.STATUS_BY_CODE.get(o.get('status'),o.get('status')):14s}"
              f" · {(o.get('inserted_at') or '')[:10]} · page {str(o.get('page_id'))[-6:]}"
              f" · {(o.get('bill_full_name') or '')[:20]}")
    if not ds:
        print("      (không có đơn nào — khách hoàn toàn mới)")
    time.sleep(0.4)

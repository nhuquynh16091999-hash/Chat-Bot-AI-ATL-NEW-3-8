import os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
print("── search=0507421089, KHÔNG mốc thời gian ──")
for o in P.fetch_orders({"page_size": 100, "page_number": 1, "search": "0507421089"}):
    print(f"   display_id={o.get('display_id')!r:>10} id={str(o.get('id'))[:10]}"
          f" · {P.STATUS_BY_CODE.get(o.get('status'), o.get('status')):14s}"
          f" · {(o.get('bill_full_name') or '')[:20]:22s} · {o.get('bill_phone_number')}"
          f" · {o.get('inserted_at','')[:16]} · conv {str(o.get('conversation_id'))[-16:]}")
print("\n── 14 ngày trang 1: 3 đơn đầu, xem display_id trông thế nào ──")
for o in P.fetch_orders({"startDateTime": int(time.time())-14*86400, "endDateTime": int(time.time()),
                         "page_size": 3, "page_number": 1}):
    print(f"   display_id={o.get('display_id')!r} · {o.get('inserted_at','')[:16]}")

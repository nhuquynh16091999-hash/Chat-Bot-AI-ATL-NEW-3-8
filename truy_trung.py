import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D
D.set_market("uae")
import pancake_order as P
now = int(time.time())
for sdt in ("0507421089", "0542651831"):
    print(f"\n═══ SĐT {sdt} — mọi đơn 14 ngày ═══")
    ds = P.fetch_orders({"startDateTime": now-14*86400, "endDateTime": now,
                         "page_size": 100, "page_number": 1, "search": sdt})
    if not ds:
        print("   (tìm theo search: KHÔNG ra đơn nào)")
    for o in ds:
        print(f"   #{o.get('display_id') or o.get('id')} · {P.STATUS_BY_CODE.get(o.get('status'),o.get('status')):14s}"
              f" · page {o.get('page_id')} · conv {str(o.get('conversation_id'))[-18:]}"
              f" · {o.get('inserted_at','')[:16]} · sđt trên đơn: {o.get('bill_phone_number')}")
    # quét thủ công toàn bộ, không dùng search
    print("   — quét thủ công (không dùng search) —")
    thay = 0
    for pg in (1,2,3):
        for o in P.fetch_orders({"startDateTime": now-14*86400, "endDateTime": now,
                                 "page_size": 100, "page_number": pg}):
            p = (o.get("bill_phone_number") or "")
            if sdt[-8:] in p.replace(" ",""):
                thay += 1
                print(f"   #{o.get('display_id') or o.get('id')} · {P.STATUS_BY_CODE.get(o.get('status'),o.get('status')):14s}"
                      f" · page {o.get('page_id')} · conv {str(o.get('conversation_id'))[-18:]}"
                      f" · {o.get('inserted_at','')[:16]} · {p}")
    if not thay: print("   (quét tay cũng không thấy)")

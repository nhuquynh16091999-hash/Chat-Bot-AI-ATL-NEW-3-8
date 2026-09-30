import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
now = int(time.time())
CONV = {"1246701271865447_27939682652348902": "Clarito Nacario / 0507421089",
        "1246701271865447_28202929212731094": "Ielans Adeveca / 0542651831"}
TEN = ["clarito", "nacario", "cristeta", "aceveda", "ielans", "adeveca"]
for mkey in ("uae", "saudi", "kuwait", "qatar", "oman", "bahrain"):
    D.set_market(mkey)
    thay = []
    for pg in (1, 2, 3, 4, 5):
        ds = P.fetch_orders({"startDateTime": now-60*86400, "endDateTime": now,
                             "page_size": 100, "page_number": pg})
        for o in ds:
            ten = (o.get("bill_full_name") or "").lower()
            conv = str(o.get("conversation_id") or "")
            if conv in CONV or any(t in ten for t in TEN):
                thay.append(o)
        if len(ds) < 100:
            break
    if thay:
        print(f"\n═══ {mkey.upper()} ═══")
        for o in thay:
            print(f"   #{o.get('display_id') or o.get('id')} · {P.STATUS_BY_CODE.get(o.get('status'),o.get('status')):14s}"
                  f" · {(o.get('bill_full_name') or '')[:22]:24s} · {o.get('bill_phone_number')}"
                  f" · page {str(o.get('page_id'))[-6:]} · {o.get('inserted_at','')[:16]}"
                  f" · conv {str(o.get('conversation_id'))[-16:]}")
print("\n(60 ngày, 6 thị trường, tìm theo tên khách và mã hội thoại)")

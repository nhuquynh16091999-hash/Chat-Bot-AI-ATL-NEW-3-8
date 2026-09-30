import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
now = int(time.time())
# tìm #47600 bằng cách lật nhiều trang hơn
tim = {"47600", "49313"}
thay = {}
for pg in range(1, 40):
    ds = P.fetch_orders({"startDateTime": now-120*86400, "endDateTime": now,
                         "page_size": 100, "page_number": pg})
    for o in ds:
        if str(o.get("display_id")) in tim:
            thay[str(o.get("display_id"))] = (o, pg)
    if len(thay) == len(tim) or len(ds) < 100:
        break
print(f"  lật {pg} trang ({pg*100} đơn) mới tìm đủ\n")
for ma in ("47600", "49313"):
    if ma not in thay:
        print(f"  #{ma}: KHÔNG thấy trong {pg*100} đơn gần nhất"); continue
    o, trang = thay[ma]
    print(f"  #{ma}  (nằm ở trang {trang})")
    for k in ("status", "bill_full_name", "bill_phone_number", "page_id",
              "conversation_id", "inserted_at", "shipping_fee", "cod"):
        print(f"      {k:20s} {o.get(k)}")
    print(f"      {'trạng thái':20s} {P.STATUS_BY_CODE.get(o.get('status'), o.get('status'))}")
    print()

import os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
now = int(time.time())
def thu(ten, params):
    ds = P.fetch_orders(params)
    ids = [str(o.get("display_id")) for o in ds]
    print(f"  {ten:44s} → {len(ds):3d} đơn · có 49313? {'CÓ' if '49313' in ids else 'không'}"
          f" · có 47600? {'CÓ' if '47600' in ids else 'không'}")
    return ds
thu("14 ngày, trang 1", {"startDateTime": now-14*86400, "endDateTime": now, "page_size":100, "page_number":1})
thu("120 ngày, trang 1", {"startDateTime": now-120*86400, "endDateTime": now, "page_size":100, "page_number":1})
thu("KHÔNG có mốc thời gian, trang 1", {"page_size":100, "page_number":1})
thu("search=0507421089", {"startDateTime": now-14*86400, "endDateTime": now, "page_size":100, "page_number":1, "search":"0507421089"})
thu("search=0507421089 KHÔNG mốc tg", {"page_size":100, "page_number":1, "search":"0507421089"})
thu("search=47600", {"page_size":100, "page_number":1, "search":"47600"})

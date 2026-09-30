import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D
D.set_market("uae")
import pancake_order as P

now = int(time.time())
ds = P.fetch_orders({"startDateTime": now - 3*86400, "endDateTime": now, "page_size": 100, "page_number": 1})
co = [o for o in ds if o.get("conversation_id") and o.get("status") not in D.TRANG_THAI_DA_XONG]
if not co:
    sys.exit("  không tìm được đơn thật có gắn hội thoại trong 3 ngày")
o = co[0]
conv = str(o["conversation_id"])
print(f"  Đơn thật dùng để thử: #{o.get('display_id') or o['id']} · hội thoại {conv[:40]}\n")

t0 = time.time()
x, ly, _k = D.find_existing(conv, o.get("bill_phone_number"), page_id=o.get("page_id"))
t_cu = time.time() - t0
print(f"  ① Đường CŨ (lật 300 đơn qua API): {t_cu:.1f}s → {'tìm thấy' if x else 'KHÔNG thấy'}")

D.nho_don(conv, o)
t0 = time.time()
y, ly2 = D.don_da_nho(conv)
t_moi = time.time() - t0
print(f"  ② Đường SỔ NHỚ                   : {t_moi:.1f}s → {'tìm thấy' if y else 'KHÔNG thấy'}")
if y:
    print(f"     lý do ghi ra: {ly2}")
    print(f"     đúng đơn?    {'✅ đúng' if str(y.get('id'))==str(o['id']) else '🚨 SAI ĐƠN'}")
print(f"\n  nhanh hơn {t_cu/max(t_moi,0.01):.0f} lần")
print(f"  sổ lưu tại: {D._f_so_don()}")

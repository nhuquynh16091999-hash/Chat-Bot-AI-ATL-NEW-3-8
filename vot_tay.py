# Vớt tay các đơn landing bị đẩy thẳng vào 'Đã xác nhận' (tool không quét tới nấc này)
import os, sys
os.chdir("/opt/pancake-tool"); sys.path.insert(0, "/opt/pancake-tool")
import pancake_order as P, don_landing as L, auto_len_don as A

IDS = [int(x) for x in sys.argv[1].split(",")]
DRY = "--that" not in sys.argv
A.set_market("uae"); L._chuan_bi_regex("uae")
print("=== CHẠY", "KHÔ (chỉ xem)" if DRY else "THẬT", "===")
IDX = L.chi_muc_don()
for i, oid in enumerate(IDS):
    r = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}"); o = r.get("data") or r
    if not L.la_don_landing(o):
        print(f"#{oid} KHÔNG phải đơn landing -> bỏ qua"); continue
    if o.get("status") != 1:
        print(f"#{oid} không còn ở 'Đã xác nhận' (nay {o.get('status')}) -> bỏ qua"); continue
    print(f"--- #{oid}")
    try:
        print("   =>", L.xu_ly_mot(o, IDX, DRY))
    except Exception as e:
        print("   !! LỖI:", type(e).__name__, e)

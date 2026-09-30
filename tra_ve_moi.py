# -*- coding: utf-8 -*-
"""Trả đơn TOOL tự xác nhận SAI về 'Mới' — CHỈ đơn còn ở 'Đã xác nhận'.
Đơn đã vào dây chuyền gửi (chờ in / đã in / đóng hàng / chờ chuyển / đã gửi) KHÔNG đụng."""
import time, sys
sys.path.insert(0, "/opt/pancake-tool")
import auto_len_don as D, pancake_order as P

THAT = "--that" in sys.argv
DAU = ("ĐỦ thông tin, đã tự xác nhận", "Đủ thông tin → chuyển Đã xác nhận")
DUOC_SUA = {1}                      # 1 = Đã xác nhận. Ngoài ra không đụng gì.
KHONG_DUNG = {8, 9, 2, 3, 12, 13, 16, 20}
now = int(time.time())
sua, bo_qua = [], []
for tt in ("uae", "saudi", "kuwait", "oman", "qatar", "bahrain"):
    D.set_market(tt)
    don = []
    for page in range(1, 9):
        data = P.fetch_orders({"startDateTime": now - 7*86400, "endDateTime": now,
                               "page_size": 100, "page_number": page})
        if not data: break
        don += data
    for o in don:
        st = o.get("status") or 0
        if st == 0 or not any(d in (o.get("note") or "") for d in DAU):
            continue
        dc = ((o.get("shipping_address") or {}).get("full_address") or "").strip()
        li = D.dia_chi_du_giao(dc)
        if not li:
            continue
        r = (tt, o.get("id"), o.get("bill_full_name"), o.get("bill_phone_number"),
             P.STATUS_BY_CODE.get(st, st), li, dc)
        (sua if st in DUOC_SUA else bo_qua).append(r)

print(f"{'🚨 LÀM THẬT' if THAT else '🧪 CHẠY THỬ'} — trả về 'Mới': {len(sua)} đơn · "
      f"KHÔNG đụng: {len(bo_qua)} đơn\n")
print("── SẼ TRẢ VỀ 'Mới' (đang ở 'Đã xác nhận', chưa vào dây chuyền gửi) ──")
for tt, oid, ten, sdt, st, li, dc in sua:
    print(f"  [{tt:6s}] id={oid} · {str(ten)[:22]:22s} · {sdt or '-':14s} · {li}")
    print(f"           {dc[:78] or '(trống)'}")
    if THAT:
        D.set_market(tt)
        ghi = (str(P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}").get("data", {}).get("note") or "").strip()
               + f"\n[Tự động 17/09] Trả về Mới — địa chỉ chưa đủ để giao ({li}). "
                 f"Sale gọi khách xin đường/số nhà rồi xác nhận lại.")
        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body={"status": 0, "note": ghi.strip()})
        print("           ✔ đã trả về Mới + ghi note")
print("\n── KHÔNG ĐỤNG (đã vào dây chuyền gửi / đã hủy) — sale tự soát ──")
for tt, oid, ten, sdt, st, li, dc in bo_qua:
    print(f"  [{tt:6s}] id={oid} · {str(ten)[:22]:22s} · {sdt or '-':14s} · [{st}] · {li}")
    print(f"           {dc[:78] or '(trống)'}")

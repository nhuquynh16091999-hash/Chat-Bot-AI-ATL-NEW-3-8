import os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
GHI = ("[Tự động] HỦY: đơn do vòng quét tự động tạo nhầm ngày 09/09/2026. "
       "Khách đã có đơn cũ trên cùng hội thoại, đã thu tiền — đây không phải thương vụ mới.")
for oid in ("49313", "49314"):
    o = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
    o = (o or {}).get("data") or o
    if not isinstance(o, dict) or not o.get("id"):
        print(f"  #{oid}: không đọc được đơn"); continue
    if o.get("status") == 6:
        print(f"  #{oid}: đã ở trạng thái Đã hủy rồi"); continue
    body = {"status": 6, "note": ((o.get("note") or "").strip() + "\n" + GHI).strip()}
    P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body=body)
    lai = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
    lai = (lai or {}).get("data") or lai
    print(f"  #{oid}: {P.STATUS_BY_CODE.get(lai.get('status'), lai.get('status'))}")

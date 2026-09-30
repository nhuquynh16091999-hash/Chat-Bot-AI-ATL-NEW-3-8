import json, os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
CUS = "1e1d2646-8c19-45f2-ac28-720dd97643cc"   # customer.id trên đơn #48962
def thu(ten, duong, params=None):
    try:
        d = P.api("GET", duong, params=params or {})
        s = json.dumps(d, ensure_ascii=False)
        co = "48962" in s
        print(f"  {'✅' if co else '  '} {ten:48s} {len(s):7d} ký tự · có #48962? {'CÓ' if co else 'không'}")
        return d if co else None
    except Exception as e:
        print(f"     {ten:48s} ✖ {str(e)[:46]}")
        return None
S = f"/shops/{P.SHOP_ID}"
thu("customers/{id}/orders", f"{S}/customers/{CUS}/orders")
thu("customers/{id}", f"{S}/customers/{CUS}")
thu("orders?customer_id (lọc phía server?)", f"{S}/orders", {"customer_id": CUS, "page_size": 20})
thu("orders?search=<customer id>", f"{S}/orders", {"search": CUS, "page_size": 20})

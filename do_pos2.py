import json, os, sys, urllib.parse, urllib.request, urllib.error
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D, pancake_order as P
D.set_market("uae")
CUS = "1e1d2646-8c19-45f2-ac28-720dd97643cc"
CONV = "1300508383138780_27839097342409393"
BASE = "https://pos.pages.fm/api/v1"
def thu(ten, duong, params=None):
    p = dict(params or {}); p["api_key"] = P.API_KEY
    u = f"{BASE}{duong}?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(u, timeout=25) as r:
            s = r.read().decode()
    except urllib.error.HTTPError as e:
        print(f"     {ten:46s} HTTP {e.code}"); return
    except Exception as e:
        print(f"     {ten:46s} ✖ {str(e)[:40]}"); return
    co = "48962" in s
    print(f"  {'✅' if co else '  '} {ten:46s} {len(s):7d} ký tự · có #48962? {'CÓ' if co else 'không'}")
S = f"/shops/{P.SHOP_ID}"
thu("customers/{id}/orders", f"{S}/customers/{CUS}/orders")
thu("customers/{id}", f"{S}/customers/{CUS}")
thu("orders + customer_id", f"{S}/orders", {"customer_id": CUS, "page_size": 20})
thu("orders + bill_phone_number", f"{S}/orders", {"bill_phone_number": "0506051046", "page_size": 20})
thu("orders + conversation_id", f"{S}/orders", {"conversation_id": CONV, "page_size": 20})
thu("orders + search=sđt sale dùng", f"{S}/orders", {"search": "0506051046", "page_size": 20})

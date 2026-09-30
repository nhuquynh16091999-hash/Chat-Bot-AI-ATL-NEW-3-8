import json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q
PID = "1300508383138780"                       # Veloura Collection
CONV = "1300508383138780_27839097342409393"    # Arlene Cantero -> đơn #48962
tok = json.load(open("state/uae/page_tokens.json", encoding="utf-8"))[PID]["token"]
usr = Q.load_env().get("PANCAKE_USER_TOKEN", "")

def thu(ten, url, params):
    try:
        u = url + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=25) as r:
            d = json.loads(r.read().decode() or "{}")
        s = json.dumps(d, ensure_ascii=False)
        co = "48962" in s
        print(f"  {'✅' if co else '  '} {ten:52s} {len(s):6d} ký tự · có #48962? {'CÓ' if co else 'không'}")
        if co:
            print(f"       khoá: {list(d)[:8]}")
        return d
    except Exception as e:
        print(f"     {ten:52s} ✖ {str(e)[:44]}")
        return None

P2 = "https://pages.fm/api/v2"
P1 = "https://pages.fm/api/public_api/v1"
W  = "https://pancake.vn/api/v1"
thu("v2 /conversations/{c}/orders", f"{P2}/pages/{PID}/conversations/{CONV}/orders", {"page_access_token": tok})
thu("v1 /conversations/{c}/orders", f"{P1}/pages/{PID}/conversations/{CONV}/orders", {"page_access_token": tok})
thu("v2 /conversations/{c}", f"{P2}/pages/{PID}/conversations/{CONV}", {"page_access_token": tok})
thu("web /conversations/{c}/orders", f"{W}/pages/{PID}/conversations/{CONV}/orders", {"access_token": usr})
thu("web /conversations/{c}", f"{W}/pages/{PID}/conversations/{CONV}", {"access_token": usr})

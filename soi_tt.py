import json, sys
sys.path.insert(0, "/opt/pancake-tool")
import os
os.chdir("/opt/pancake-tool")
import ai_sale as A
mk = json.load(open("markets.json", encoding="utf-8"))
print("  Thị trường     shop POS có   thư mục giữ   đang bật")
for tt in [k for k in mk if not k.startswith("_")]:
    try:
        s = A._pages_cua_shop(tt)
        n = "?" if s is None else len(s)
    except Exception:
        n = "?"
    try:
        d = json.load(open(f"state/{tt}/page_tokens.json", encoding="utf-8"))
        co = sum(1 for x in d.values() if x.get("token"))
    except Exception:
        co = 0
    bat = mk[tt].get("bat")
    co_chay = "" if (n not in ("?", 0) or co) else "   ← TRỐNG"
    print(f"  {tt:12s} {str(n):>10}   {co:10d}   {str(bat):>7}{co_chay}")

import sys, json, glob
sys.path.insert(0, "/tmp/thu_cm")
import ai_sale as A
g = {"gia_ban": [199]}
shop = {"boi": "botcake", "text": "SPECIAL OFFER TODAY: BUY 1 GET 1 FREE — $199 + FREE SHIPPING"}
def thu(t): return A.khach_vua_chon_goi([shop, {"boi": "khach", "text": t}], "usa", g)
for t in ["Gusto yang na sa picture", "I want this", "I'll take it", "Gusto ko pero wala budget", "Gusto ba ito?",
          "i want to order", "How to order?", "I want to know the price", "I like it", "Kukunin ko po", "Where is my order",
          "I need this for my mom", "Ok i order", "أبغى واحد"]:
    print(repr(t), bool(thu(t)))
kh = set(); bat = []
for f in glob.glob("/opt/pancake-tool/state/*/so_chi_phi.jsonl"):
    for l in open(f, encoding="utf-8", errors="ignore"):
        try: t = json.loads(l).get("hoi")
        except Exception: continue
        if isinstance(t, str) and t.strip() and t not in kh:
            kh.add(t)
            if A.MUON_MUA.search(t) and thu(t): bat.append(t[:110].replace("\n", " "))
print("câu khách:", len(kh), "bắt thêm:", len(bat)); [print("  *", x) for x in bat[:70]]

import json, ai_sale as A
shop = {"boi": "nguoi", "text": 'Will you choose the "buy 1 get 1 free" or the "buy 2 get 2 free" offer? 109 / 159 SAR'}
g = {"gia_ban": [109, 159]}
def thu(*kh): return A.khach_vua_chon_goi([shop] + [{"boi": "khach", "text": x} for x in kh], "saudi", g)
dung = [("Only 1 items to try", "If good and true i order more"), ("1 only",), ("just one po",), ("buy 1 get 1",),
        ("1+1",), ("2 pcs",), ("159",), ("I take 2 sets",), ("isa po",), ("2 get 2 po",), ("b1g1 pls",)]
sai = [("This one can use for fugal resh",), ("1 bottle are you sure effective",),
       ("እወ ክመርፅ ይደሊ እየ ኣጠቃቅምኡለ ክትነግርኒ ይደሊ እየ ል1 ሓባ 109 ድዮ",), ("how much",), ("1 item how much?",),
       ("I have only one question",), ("no money",), ("Sa sahod nalang salamat",), ("2 pcs effective ba",)]
print("NÊN BẮT:", sum(bool(thu(*k)) for k in dung), "/", len(dung), [k for k in dung if not thu(*k)])
print("KHÔNG NÊN BẮT:", sum(not thu(*k) for k in sai), "/", len(sai), [k for k in sai if thu(*k)])
tins = set()
for l in open("/tmp/luot_all.jsonl"):
    try: t = json.loads(l).get("tin")
    except Exception: continue
    if t: tins.add(t.strip())
bat = [t for t in tins if A.khach_vua_chon_goi([shop, {"boi": "khach", "text": t}], "saudi", g)]
print(f"kho {len(tins)} câu thật → bắt {len(bat)}:"); [print("   ", repr(t[:80])) for t in sorted(bat)]

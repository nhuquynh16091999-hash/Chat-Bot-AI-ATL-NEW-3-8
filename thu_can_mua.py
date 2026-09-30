import sys, json, glob
sys.path.insert(0, "/tmp/thu_cm")
import ai_sale as A, chan_gui as CG
exec(open("/tmp/soi_lucy_msgs.py").read())
cut = [m for m in msgs if m["luc"] < "2026-09-14T13:34:30"]
print("QUYET Lucy:", A.ai_co_vao_cuoc(cut))
print("hoi_gia_gan:", A.khach_hoi_gia_gan(cut))
for t in ["Hindi po basta bili lang, Lucy JJ 😊 Ang Golden Buddha", "Opo, Lucy JJ 😊 199$ lang", "You don't have to pay anything today",
          "Don't rush to buy", "Wala po kayong babayaran ngayon", "It's not just about buying, it's a blessing", "hindi kailangan magbayad ngayon"]:
    print(repr(t[:40]), bool(CG.CAN_MUA.search(t)))
# đo cả chiều: tin AI thật đã gửi 3 ngày qua bị bắt bao nhiêu
n = 0; bat = []
for f in glob.glob("/opt/pancake-tool/state/*/so_chi_phi.jsonl"):
    for l in open(f, encoding="utf-8", errors="ignore"):
        try: r = json.loads(l)
        except Exception: continue
        t = r.get("tin") or r.get("tin_nhan") or ""
        if isinstance(t, str) and t:
            n += 1
            if CG.CAN_MUA.search(t): bat.append(t[:120])
print("tin AI:", n, "bắt:", len(bat)); [print("  -", x) for x in bat[:15]]
kh = set(); moi = []
for f in glob.glob("/opt/pancake-tool/state/*/so_chi_phi.jsonl"):
    for l in open(f, encoding="utf-8", errors="ignore"):
        try: t = json.loads(l).get("hoi")
        except Exception: continue
        if isinstance(t, str) and t and t not in kh:
            kh.add(t)
            if A.HOI_MUA.search(t): moi.append(t[:100])
print("câu khách:", len(kh), "HOI_MUA bắt:", len(moi)); [print("  *", x) for x in moi[:25]]

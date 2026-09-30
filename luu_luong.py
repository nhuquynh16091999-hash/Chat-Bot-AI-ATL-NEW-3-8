import json, sys, os, time, urllib.request, urllib.parse, re, collections
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import quet_hoi_thoai as Q
tok = Q.load_env().get("PANCAKE_USER_TOKEN", "")
NGAY = 7
now = time.time()
dr = time.strftime("%d/%m/%Y 00:00:00", time.localtime(now - NGAY*86400)) + " - " + time.strftime("%d/%m/%Y 23:59:59", time.localtime(now))
def goi(path, body=None, **p):
    p["access_token"] = tok
    u = "https://pancake.vn/api/v1" + path + "?" + urllib.parse.urlencode(p)
    rq = urllib.request.Request(u, data=json.dumps(body).encode() if body is not None else None,
                                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, method="POST" if body is not None else "GET")
    for lan in range(4):
        try:
            with urllib.request.urlopen(rq, timeout=40) as r: return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(1.5 * (lan + 1)); continue
            return {"loi": e.code, "than": e.read().decode()[:120]}
        except Exception as e:
            return {"loi": str(e)[:100]}
    return {"loi": "429"}
pg = goi("/pages")
cat = pg.get("categorized") or {}
pages = []
print("categorized:", {k: (type(v).__name__, len(v) if hasattr(v, "__len__") else v) for k, v in cat.items()}, flush=True)
for k, v in pg.items():
    if k != "categorized": print("khoá khác:", k, type(v).__name__, (len(v) if hasattr(v, "__len__") else v), flush=True)
da = set()
for nhom, ds in cat.items():
    if not isinstance(ds, list): continue
    for p in ds:
        if not isinstance(p, dict) or str(p.get("id") or p.get("page_id")) in da: continue
        da.add(str(p.get("id") or p.get("page_id")))
        pages.append({"id": str(p.get("id") or p.get("page_id")), "ten": p.get("name"), "nhom": nhom,
                      "shop_id": p.get("shop_id"), "country": p.get("country"), "role": p.get("role_in_page"),
                      "goi_con": p.get("has_active_subscription"), "het_goi_tu": p.get("no_package_since"),
                      "so_user": len(p.get("users") or []),
                      "goi": (p.get("package") or p.get("plan") or {}).get("name") if isinstance(p.get("package") or p.get("plan"), dict) else p.get("package") or p.get("plan"),
                      "het_han": p.get("deactivation_days_left"), "is_activated": p.get("is_activated"), "platform": p.get("platform")})
print("nhóm:", {k: len(v or []) for k, v in cat.items()}, "| tổng:", len(pages), flush=True)
print("khoá page mẫu:", sorted(pages[0].keys()) if pages else None, flush=True)
_m = next((p for ds in cat.values() if isinstance(ds, list) for p in ds if isinstance(p, dict)), {})
print("khoá gốc mẫu:", sorted(_m.keys())[:70], flush=True)
kq = []
for i, p in enumerate(pages):
    d = goi("/statistics/customer_engagements", {"page_ids": p["id"]}, date_range=dr, statistic_type="day")
    st = d.get("engagement_statistics") or []
    p.update({"inbox": sum(x.get("inbox", 0) for x in st), "comment": sum(x.get("comment", 0) for x in st),
              "khach_moi": sum(x.get("customer_engagement_new_inbox", 0) for x in st),
              "don": sum(x.get("order_count", 0) for x in st), "so_ngay": len(st),
              "theo_ngay": {x["time"]: x.get("inbox", 0) for x in st}, "loi": d.get("loi")})
    kq.append(p)
    if i % 25 == 0:
        print(i, p["ten"], p["inbox"], p.get("loi") or "", flush=True)
        json.dump(kq, open("/opt/pancake-tool/state/luu_luong_toan_bo.json", "w"), ensure_ascii=False)
    time.sleep(0.3)
json.dump(kq, open("/opt/pancake-tool/state/luu_luong_toan_bo.json", "w"), ensure_ascii=False)
print("XONG", len(kq), "page; lỗi:", sum(1 for p in kq if p.get("loi")), flush=True)

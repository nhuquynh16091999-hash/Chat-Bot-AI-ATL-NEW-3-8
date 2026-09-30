"""Xếp thẻ đơn 71 'XN QUA WA' (POS Saudi) vào nhóm 5 'WA - SALE CARE' + màu, rồi thử gắn lên đơn nháp
#78050 (Kính ổn TEST 0963160534) và trả lại thẻ cũ. Chạy trên VPS: python3 /opt/pancake-tool/thu_the_nhom.py"""
import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, "/opt/pancake-tool")
import care_don_wa as C

v = json.load(open("/opt/pancake-tool/markets.json"))["saudi"]


def rq(m, path, body=None):
    u = f"{C.POS_API}/shops/{v['shop_id']}{path}?api_key={v['api_key']}"
    r = urllib.request.Request(u, data=json.dumps(body).encode() if body is not None else None,
                               method=m, headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=30).read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} {e.read()[:200]}"


def the71():
    return next((t for t in rq("GET", "/orders/tags")["data"] if t["id"] == 71), None)


print("THE 71 TRUOC", the71())
for m, pa, b in [
    ("PUT", "/orders/tags/71", {"name": "XN QUA WA", "color": "#10c373", "group_ids": [5]}),
    ("PUT", "/orders/tags/71", {"name": "XN QUA WA", "color": "#10c373", "groups": [5]}),
    ("PUT", "/orders/tags/71", {"name": "XN QUA WA", "color": "#10c373", "groups": [{"id": 5, "name": "WA - SALE CARE"}]}),
    ("PUT", "/orders/tags", {"id": 71, "name": "XN QUA WA", "color": "#10c373", "group_ids": [5]}),
]:
    r = rq(m, pa, b)
    t = the71()
    print("SUA", m, pa, json.dumps(b, ensure_ascii=False), "=>", str(r)[:120], "| the71:", t)
    if t and t.get("groups"):
        break

o = rq("GET", "/orders/78050")["data"]
if o["bill_phone_number"] != "0963160534":
    sys.exit("DUNG: don 78050 khong phai don thu")
rq("PUT", "/orders/78050", {"tags": [71]})
time.sleep(2)
print("GAN 71 ->", rq("GET", "/orders/78050")["data"]["tags"])
rq("PUT", "/orders/78050", {"tags": [t["id"] for t in o["tags"]]})
time.sleep(2)
print("TRA LAI ->", rq("GET", "/orders/78050")["data"]["tags"])

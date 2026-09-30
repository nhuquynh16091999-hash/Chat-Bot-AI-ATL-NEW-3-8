"""Thử gắn thẻ đơn POS trên đơn nháp #78050 (Saudi, số VN 0963160534) rồi trả lại thẻ cũ.
Chạy trên VPS: python3 /opt/pancake-tool/thu_the_78050.py"""
import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, "/opt/pancake-tool")
import care_don_wa as C

mk = json.load(open("/opt/pancake-tool/markets.json"))
v = mk["saudi"]


def rq(m, path, body=None):
    u = f"{C.POS_API}/shops/{v['shop_id']}{path}?api_key={v['api_key']}"
    r = urllib.request.Request(u, data=json.dumps(body).encode() if body is not None else None,
                               method=m, headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=30).read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} {e.read()[:300]}"


o = rq("GET", "/orders/78050")["data"]
print("DON", o["id"], o["bill_full_name"], o["bill_phone_number"], "status", o["status"], "the cu", o["tags"])
if o["bill_phone_number"] != "0963160534":
    sys.exit("DUNG: don 78050 khong phai don thu so 0963160534")
for b in ([44], [{"id": 44, "name": "Đợi đơn cũ"}], [71], [{"id": 71, "name": "XN QUA WA"}]):
    rq("PUT", "/orders/78050", {"tags": b})
    time.sleep(2)
    print("THU", json.dumps(b, ensure_ascii=False), "->", rq("GET", "/orders/78050")["data"]["tags"])
rq("PUT", "/orders/78050", {"tags": [t["id"] for t in o["tags"]]})
time.sleep(2)
print("TRA LAI ->", rq("GET", "/orders/78050")["data"]["tags"])

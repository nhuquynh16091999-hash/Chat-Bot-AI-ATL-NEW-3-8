"""TẮT chia tự động (hard_round_robin) trên mọi page — chủ shop yêu cầu 20/09 23:4x vì sale
không thấy hội thoại.

Vì sao không dùng chia_sale.py: nó đọc current_settings_key của cả 478 page lúc đầu rồi ghi rải
rác trong ~10 phút, key cũ nên Pancake bỏ qua lệnh ghi. Script này mỗi page ĐỌC KEY MỚI ngay
trước khi ghi, và xác nhận bằng PHẢN HỒI của lệnh ghi (GET settings có cache, đọc lại ngay sau
khi ghi sẽ ra giá trị cũ → báo động sai).

    python3 tat_chia_ngay.py          # tắt thật
    python3 tat_chia_ngay.py --thu    # chỉ xem page nào đang bật
"""
import json, os, sys, time, urllib.request, urllib.parse
ARGS = sys.argv[:]; sys.argv = ["x"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quet_hoi_thoai as Q
TOK = Q.USER_TOKEN
THU = "--thu" in ARGS

def call(method, url, params, body=None):
    u = url + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    for lan in range(3):
        req = urllib.request.Request(u, data=data, method=method,
              headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try: return json.loads(e.read())
            except Exception: return {"message": f"HTTP {e.code}"}
        except Exception as e:
            if lan == 2: return {"message": str(e)[:80]}
            time.sleep(2)

pages = call("GET", "https://pages.fm/api/v1/pages", {"access_token": TOK}) or {}
cat = pages.get("categorized") or {}
allp = (cat.get("activated") or []) + (cat.get("inactivated") or [])
print(f"soi {len(allp)} page…", flush=True)
tk = {"tat_duoc": 0, "von_da_tat": 0, "loi": 0, "khong_doc": 0}
for p in allp:
    pid, ten = str(p["id"]), str(p["name"])[:42]
    s = call("GET", f"https://pages.fm/api/v1/pages/{pid}/settings", {"access_token": TOK}) or {}
    st = s.get("settings")
    if not isinstance(st, dict): tk["khong_doc"] += 1; continue
    if not st.get("hard_round_robin") and not (st.get("hard_round_robin_inbox_user_ids") or []):
        tk["von_da_tat"] += 1; continue
    if THU:
        print(f"  [THỬ] {ten:42s} đang BẬT ({len(st.get('hard_round_robin_inbox_user_ids') or [])} người)", flush=True)
        tk["tat_duoc"] += 1; continue
    r = call("POST", f"https://pancake.vn/api/v1/pages/{pid}/settings", {"access_token": TOK},
             {"changes": json.dumps({"hard_round_robin": False,
                                     "hard_round_robin_inbox_user_ids": []}),
              "current_settings_key": st.get("current_settings_key")})
    sau = ((r or {}).get("change_settings") or {}).get("settings") or {}
    if sau and not sau.get("hard_round_robin") and not (sau.get("hard_round_robin_inbox_user_ids") or []):
        tk["tat_duoc"] += 1; print(f"  ✔ {ten:42s} đã TẮT", flush=True)
    else:
        tk["loi"] += 1
        print(f"  ✖ {ten:42s} KHÔNG tắt được: {str((r or {}).get('message'))[:60]}", flush=True)
    time.sleep(0.25)
print(f"\nTắt được {tk['tat_duoc']} · vốn đã tắt {tk['von_da_tat']} · lỗi {tk['loi']}"
      f" · không đọc được settings {tk['khong_doc']}")

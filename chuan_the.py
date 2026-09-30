"""Chuẩn hoá thẻ hội thoại (settings.tags) cho mọi page CÒN GÓI — chủ shop chốt 26/09/2026.
  1. Xoá thẻ thừa: tên nằm trong XOA (nhân viên nghỉ, thẻ AI cũ, thẻ chết) + bản trùng tên của thẻ thường
     — chủ shop 26/09 tối: *"thẻ trùng nhau thì xoá thẻ nào ko hoạt động"* → giữ ĐÚNG MỘT bản sale dùng nhiều nhất
     (lượt gắn 30 ngày, rồi 90 ngày, rồi id nhỏ nhất), xoá các bản kia dù còn vài lượt gắn (hội thoại gắn bản đó mất thẻ).
  2. Sắp theo thứ tự CHUAN (mẫu: page Kreain Nature PH in Uae). Thẻ ngoài danh sách xếp cuối, giữ thứ tự cũ.
KHÔNG BAO GIỜ xoá (kể cả bản trùng): thẻ có chữ bot/delay/tukhoa, "Đã gửi" (AI + daemon dựa vào để biết khách
đã mua), US/USA/TAIWAN/TW (page Mỹ, Đài), TEST, AI CHAT. Thẻ lạ không có trong XOA thì giữ — thêm sale mới không bị xoá oan.
  3. Thêm thẻ PHẢI CÓ (THEM) nếu page thiếu — 26/09: "AI CHAT" (sale gắn → AI Sale ngưng chat hội thoại đó, gỡ → AI
     chat lại; THE_AI_CHAT_2609 trong ai_sale.py). Gửi KHÔNG kèm id — Pancake tự cấp id + nhích current_tag_index.
Id thẻ giữ lại không đổi → hội thoại đã gắn không lệch. Pancake hiện 8 thẻ/hàng, thẻ ĐẦU mảng nằm hàng DƯỚI CÙNG.
  python3 chuan_the.py --thu              # chạy thử, không ghi
  python3 chuan_the.py --page <ID>        # 1 page
  python3 chuan_the.py                    # tất cả page còn gói
  python3 chuan_the.py --tu-dong          # timer: page mới chưa làm lần nào + quét hết nếu lần quét hết cuối đã >20 giờ
Log state/chuan_the.log · bản cũ từng page trước khi ghi: state/chuan_the_bak/<ngày>.json
"""
import json, sys, os, time, unicodedata, urllib.request, urllib.parse, datetime
ARGS = sys.argv[:]; sys.argv = ["x"]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import quet_hoi_thoai as Q
TOK = Q.USER_TOKEN
DRY = "--thu" in ARGS
AUTO = "--tu-dong" in ARGS
ONE = ARGS[ARGS.index("--page")+1] if "--page" in ARGS else None
PAUSE = 1.0 if AUTO else 0.45     # timer chạy chung token với AI Sale → giãn hơn
CHUAN = ["kiểm hàng", "câu hỏi", "mua hàng", "đã gửi", "hết hàng", "trả hàng", "bot", "mlinh",
         "quỳnh trang", "hiền", "duyên", "trang", "thái", "phương anh", "bỏ qua", "bị block",
         "thảo", "hiền ca đêm", "au", "blook", "cskh", "delay bot",
         "us", "usa", "tw", "taiwan", "tukhoa", "test", "ai chat"]
# biến thể gõ khác nhau nằm cùng ô với thẻ chuẩn
GOP = {"bott": "bot", "delaybot": "delay bot", "bot delay": "delay bot", "botdelay": "delay bot",
       "botdelayy": "delay bot", "delay": "delay bot"}
XOA = {"thư", "plinh", "bình", "ngân", "thúy", "thuý", "thu hương", "ánh", "hương", "diệp",
       "ai chăm", "ai chốt", "ai back sale", "ai backsale", "lên đơn",
       "set nhẫn", "set chim công", "vòng chúa", "hoa tai",
       "đã confirm", "đã/đang hoàn", "đã lên đơn", "hẹn mua", "chưa có tiền", "đã nhận hàng",
       "đã thu tiền", "đã tt", "đtt", "khách hàng", "linh", "thai", "box",
       # chủ shop 26/09: "PANH vs Phương Anh là 1" — đo 30 ngày: Phương Anh 1069 lượt, PANH 15; page có PANH đều có Phương Anh
       "panh"}
GIU = {"đã gửi", "da gui", "us", "usa", "tw", "taiwan", "test", "ai chat"}
# Thẻ PHẢI CÓ trên mọi page (chủ shop 26/09: *"khi sale gắn thẻ AI CHAT là bạn ngưng chat, gỡ là chat lại"*).
# Gửi KHÔNG kèm id: đo 26/09 trên Hibiscus Herbal Tea PH in Saudi — tự đặt id thì Pancake nhận thẻ nhưng BỎ QUA bộ đếm
# current_tag_index (ghi riêng cũng bỏ qua) → thẻ sale tạo tay sau này có thể trùng id; thiếu id thì Pancake tự cấp
# (#17) và nhích bộ đếm theo. Cũng tránh dùng lại id thẻ đã xoá (AI Chăm, LÊN ĐƠN…) còn nằm trên hội thoại cũ.
THEM = [{"color": "#f5222d", "is_lead_event": False, "lighten_color": "rgba(245,34,45,0.4)", "text": "AI CHAT"}]
TEN_THEM = {" ".join(x["text"].split()).lower() for x in THEM}
def norm(s): return " ".join(unicodedata.normalize("NFC", str(s or "")).split()).lower()
def giu(n): return n in GIU or any(k in n for k in ("bot", "delay", "tukhoa", "tu khoa", "từ khoá", "từ khóa"))
def o(t):
    n = norm(t.get("text")); n = GOP.get(n, n)
    return CHUAN.index(n) if n in CHUAN else len(CHUAN)
def sap(tags): return [t for _, t in sorted(enumerate(tags), key=lambda x: (o(x[1]), x[0]))]
def call(method, url, params, body=None):
    u = url + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    for lan in range(4):
        req = urllib.request.Request(u, data=data, method=method,
              headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r: res = json.loads(r.read())
        except urllib.error.HTTPError as e:
            try: res = json.loads(e.read())
            except Exception: res = {"success": False, "message": f"HTTP {e.code}"}
        except Exception as e:
            res = {"success": False, "message": str(e)[:100]}
        if not isinstance(res, dict): res = {"success": False, "message": str(res)[:100]}
        if res.get("error_code") == 429 or "internal error" in str(res.get("message","")).lower(): time.sleep(3 + 3*lan); continue
        return res
    return res
def settings(pid): return call("GET", f"https://pages.fm/api/v1/pages/{pid}/settings", {"access_token": TOK})
def save(pid, key, tags):
    return call("POST", f"https://pancake.vn/api/v1/pages/{pid}/settings", {"access_token": TOK},
                {"changes": json.dumps({"tags": tags}), "current_settings_key": key})
def usage(pid):
    den = datetime.date.today(); tu = den - datetime.timedelta(days=90)
    u = {}; u30 = {}; ok = True
    # date_range dài quá ~115 ngày trả series RỖNG không báo lỗi → hỏi từng 30 ngày
    for k in range(3):
        a = tu + datetime.timedelta(days=30*k); b = min(den, a + datetime.timedelta(days=29))
        time.sleep(PAUSE)
        r = call("POST", "https://pancake.vn/api/v1/statistics/tags",
                 {"access_token": TOK, "date_range": f"{a:%d/%m/%Y} 00:00:00 - {b:%d/%m/%Y} 23:59:59",
                  "statistic_type": "day"}, {"page_ids": str(pid)})
        ok = ok and bool((r or {}).get("success"))
        for key, arr in ((r or {}).get("data") or {}).get("series", {}).items():
            try: tid = int(str(key).replace("tag_", ""))
            except ValueError: continue
            n = sum(x.get("total", 0) for x in arr)
            u[tid] = u.get(tid, 0) + n
            if k == 2: u30[tid] = u30.get(tid, 0) + n
    return u, u30, ok
def them_the(tags):
    """Thẻ THEM page còn thiếu (chưa có id — Pancake tự cấp khi ghi)."""
    co = {norm(t.get("text")) for t in tags}
    return [dict(x) for x in THEM if norm(x["text"]) not in co]
def khoa(ds):
    """Dấu thứ tự để so trước/sau ghi: id thẻ; thẻ THEM (mới, id do Pancake cấp) thì theo tên."""
    return [("+" + norm(t.get("text"))) if (t.get("id") is None or norm(t.get("text")) in TEN_THEM) else t["id"] for t in ds]
def ke_hoach(pid, tags, log_warn):
    """(danh sách mới, [mô tả xoá]) — chỉ xoá theo XOA + bản trùng của thẻ không được giữ."""
    rm = {}; groups = {}
    for t in tags:
        n = norm(t.get("text"))
        if n in XOA and not giu(n): rm[t["id"]] = t.get("text", "").strip()
        elif not giu(n): groups.setdefault(n, []).append(t)
    dups = {n: a for n, a in groups.items() if len(a) > 1}
    if dups:
        u, u30, ok = usage(pid)
        if not ok: log_warn("không lấy được thống kê → không xoá bản trùng lần này")
        for a in (dups.values() if ok else []):
            a.sort(key=lambda t: (-(u30.get(t["id"], 0)), -(u.get(t["id"], 0)), t["id"]))
            for t in a[1:]:
                rm[t["id"]] = (t.get("text", "").strip() + f" (trùng #{t['id']} {u30.get(t['id'], 0)} lượt/30 ngày,"
                               f" giữ #{a[0]['id']} {u30.get(a[0]['id'], 0)})")
    moi = sap([t for t in tags if t["id"] not in rm])
    return moi, list(rm.values())

ST = os.path.join(HERE, "state"); os.makedirs(os.path.join(ST, "chuan_the_bak"), exist_ok=True)
F_DA = os.path.join(ST, "chuan_the_da_lam.json")
da = Q.load_json(F_DA, {}) if hasattr(Q, "load_json") else (json.load(open(F_DA)) if os.path.exists(F_DA) else {})
da.setdefault("pages", {}); da.setdefault("quet_het", 0)
pages = call("GET", "https://pages.fm/api/v1/pages", {"access_token": TOK})
cat = (pages or {}).get("categorized") or {}
allp = (cat.get("activated") or []) + (cat.get("inactivated") or [])
if not allp: sys.exit(f"Không đọc được danh sách page: {(pages or {}).get('message')}")
song = [p for p in allp if p.get("has_active_subscription") and p.get("deactivation_days_left") in (None, "")]
quet_het = False
if ONE: lam = [p for p in allp if str(p["id"]) == ONE]
elif AUTO:
    quet_het = time.time() - da["quet_het"] > 20 * 3600
    lam = song if quet_het else [p for p in song if str(p["id"]) not in da["pages"]]
else: lam = song; quet_het = True
if AUTO and not lam: sys.exit(0)     # không có page mới → im, khỏi rác log
log = open(os.path.join(ST, "chuan_the.log"), "a")
def out(s): print(s, flush=True); log.write(s + "\n"); log.flush()
f_bak = os.path.join(ST, "chuan_the_bak", f"{datetime.date.today():%Y%m%d}.json")
bak = json.load(open(f_bak)) if os.path.exists(f_bak) else []
out(f"=== {datetime.datetime.now():%F %T} {'THỬ' if DRY else 'THẬT'}{' tự động' if AUTO else ''} · còn gói {len(song)}"
    f" · làm {len(lam)} page{' (quét hết)' if quet_het else ' (page mới)' if AUTO else ''}")
tk = {"page": 0, "dung_san": 0, "sua": 0, "xoa_the": 0, "khong_xac_minh": 0, "loi": 0}
for p in lam:
    pid = str(p["id"]); ten = (p.get("name") or "")[:40]; tk["page"] += 1
    time.sleep(PAUSE)
    s = settings(pid); st = (s or {}).get("settings")
    if not st or not isinstance(st.get("tags"), list):
        tk["loi"] += 1; out(f"  ✖ {ten} ({pid}): không đọc được settings: {(s or {}).get('message','')[:80]}"); continue
    tags = st["tags"]
    moi, xoa = ke_hoach(pid, tags, lambda m: out(f"  ⚠ {ten}: {m}"))
    them = them_the(moi)
    if them: moi = sap(moi + them)
    if khoa(moi) == khoa(tags):
        tk["dung_san"] += 1; da["pages"][pid] = int(time.time()); continue
    mo_ta = (f"{len(tags)}→{len(moi)} thẻ" + (f" · xoá {', '.join(xoa)}" if xoa else "")
             + (f" · thêm {', '.join(t['text'] for t in them)}" if them else "")
             + ("" if (xoa or them) else " · chỉ sắp"))
    if DRY:
        tk["sua"] += 1; tk["xoa_the"] += len(xoa); out(f"  [THỬ] {ten} ({pid}) {mo_ta}"); continue
    bak.append({"luc": f"{datetime.datetime.now():%F %T}", "pid": pid, "name": p.get("name"), "tags": tags})
    json.dump(bak, open(f_bak, "w"), ensure_ascii=False, indent=1)
    time.sleep(PAUSE)
    r = save(pid, st.get("current_settings_key"), moi)
    after = (((r or {}).get("change_settings") or {}).get("settings") or {}).get("tags")
    if not after or them:          # phản hồi có khi trả tags rỗng; thẻ mới thì phải đọc lại mới thấy id Pancake cấp
        time.sleep(3.5); after = ((settings(pid) or {}).get("settings") or {}).get("tags")
    if them and after and any(not isinstance(t.get("id"), int) for t in after if norm(t.get("text")) in TEN_THEM):
        tk["loi"] += 1; out(f"  ✖ {ten} ({pid}): {mo_ta} NHƯNG thẻ mới không được cấp id · {str(after)[-160:]}"); continue
    if after is not None and khoa(after) == khoa(moi):
        if them: mo_ta += " #" + ",".join(str(t["id"]) for t in after if norm(t.get("text")) in TEN_THEM)
        tk["sua"] += 1; tk["xoa_the"] += len(xoa); da["pages"][pid] = int(time.time())
        out(f"  ✔ {ten} ({pid}) {mo_ta}")
    elif after is None:
        tk["khong_xac_minh"] += 1; out(f"  ? {ten} ({pid}): ghi xong nhưng KHÔNG XÁC MINH ĐƯỢC · phản hồi {str(r)[:120]}")
    else:
        tk["loi"] += 1; out(f"  ✖ {ten} ({pid}): sau ghi CHƯA ĐÚNG · phản hồi {str(r)[:120]}")
if not DRY:
    if quet_het and not ONE and tk["loi"] == 0: da["quet_het"] = int(time.time())
    json.dump(da, open(F_DA, "w"), ensure_ascii=False)
out(f"=== XONG {json.dumps(tk, ensure_ascii=False)}")

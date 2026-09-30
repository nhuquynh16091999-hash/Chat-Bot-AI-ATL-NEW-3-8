"""Chia hội thoại cho sale TỰ ĐỘNG bằng vòng chia (round robin) sẵn có của Pancake.

Chủ shop 20/09/2026: *"có cách nào bạn tự động chia data cho sale thay tôi được không"* —
data = toàn bộ hội thoại mới của page, luật chia = đều luân phiên.

Pancake có sẵn cỗ máy chia trong cài đặt page (`hard_round_robin`): khách nhắn vào là nó
tự giao cho người kế tiếp trong danh sách. Việc duy nhất phải làm bằng tay là ĐẶT DANH SÁCH
cho từng page — tool này làm việc đó cho cả mấy trăm page trong một lượt.

Ba cửa API (đều bằng PANCAKE_USER_TOKEN trong .env, không cần page token):
    GET  pages.fm/api/v1/pages                      -> danh sách page tài khoản thấy
    GET  pages.fm/api/v1/pages/{pid}/users           -> nhân viên CỦA PAGE đó (có id + tên)
    GET  pages.fm/api/v1/pages/{pid}/settings        -> vòng chia hiện tại + current_settings_key
    POST pancake.vn/api/v1/pages/{pid}/settings      -> ghi vòng chia (giống don_the.py ghi thẻ)
API công khai `/public_api/v1/pages/{pid}/users` KHÔNG dùng được: 170/193 page trả 0 nhân viên.

    python3 chia_sale.py                                  # soi: page nào đang chia cho ai
    python3 chia_sale.py --ca --thu                        # ca nao dang truc, se doi gi
    python3 chia_sale.py --ca --that                       # ap ca dang truc (dung cho cron)
    python3 chia_sale.py --nhan-vien                       # liệt kê sale có thể đưa vào vòng chia
    python3 chia_sale.py --ai "Thu Hiền, Từ Trang" --thu   # xem trước sẽ đổi gì
    python3 chia_sale.py --ai "Thu Hiền, Từ Trang" --that  # ghi thật
    python3 chia_sale.py --chua-bat --ai "..." --that      # chỉ vá page chưa chia
    python3 chia_sale.py --tt saudi --ai "..." --that       # 1 thị trường
    python3 chia_sale.py --page 123... --tat --that         # tắt chia ở 1 page
⚠ NHIỀU NGƠỜI TRÙNG TÊN: có page 9 người tên "Từ Trang", 5 người "Thu Hiền" — nên
truyền UUID thay cho tên. Tên trùng thì tool BỎ QUA page đó và in các UUID để chọn.
Bộ ba đang chạy trên 138 page: 6be8f1f2-b867-488d-9fff-df78cf591bca (Thu Hiền),
df1de452-74bd-4784-bfdc-99140e493120 (Từ Trang), e3d6411e-433d-4147-89f2-b4e8d884c262 (Nguyễn Duyên).
Tài khoản khác (cần ADMINISTER mới ghi được): thêm 1 dòng vào .env rồi
    PANCAKE_USER_TOKEN_ADMIN=<token tài khoản chủ shop>
    python3 chia_sale.py --token-env PANCAKE_USER_TOKEN_ADMIN            # soi trước
Cờ thêm khi ghi: --comment (chia cả bình luận) · --online (chỉ giao người đang online)
                 --giao-lai N (N phút không đọc thì chuyển người khác, 0 = tắt)
Mỗi lần ghi đều sao lưu cấu hình cũ vào state/chia_sale_saoluu-<ngày giờ>.json để hoàn tác.
"""
import json, sys, os, re, time, datetime, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ARGS = sys.argv[:]; sys.argv = ["x"]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quet_hoi_thoai as Q

def _tok():
    """Token nao? --token <tok> | --token-env <TEN_BIEN> (doc .env hoac bien moi truong)
    | mac dinh PANCAKE_USER_TOKEN. Ghi cai dat vong chia can tai khoan ADMINISTER tren page —
    tai khoan EDIT_PROFILE bi Pancake tra "Missing permissions!" (do 20/09)."""
    if "--token" in ARGS: return ARGS[ARGS.index("--token") + 1].strip()
    if "--token-env" in ARGS:
        ten = ARGS[ARGS.index("--token-env") + 1].strip()
        t = (Q.ENV.get(ten) or os.environ.get(ten) or "").strip()
        if not t: sys.exit(f"Khong thay bien {ten} trong .env lan bien moi truong")
        if t.upper().startswith("DAN_TOKEN") or "<" in t or " " in t:
            sys.exit(f"Bien {ten} trong .env van con cho trong ({t[:24]!r}) — dan token that vao roi chay lai")
        return t
    return Q.USER_TOKEN
TOK   = _tok()
def arg(ten, mac_dinh=None):
    return ARGS[ARGS.index(ten) + 1] if ten in ARGS and ARGS.index(ten) + 1 < len(ARGS) else mac_dinh
THAT  = "--that" in ARGS
THU   = "--thu" in ARGS
TAT   = "--tat" in ARGS
AI    = arg("--ai")
ONE   = arg("--page")
TT    = arg("--tt")
CHUA  = "--chua-bat" in ARGS
CMT   = "--comment" in ARGS
CA    = "--ca" in ARGS
CHI_DS = "--chi-ds" in ARGS   # chi ghi danh sach nguoi, KHONG dung cong tac hard_round_robin
EP    = "--ep" in ARGS        # ap lai ca dang truc du so ca da ghi la da ap
ONL   = "--online" in ARGS
GIAO_LAI = arg("--giao-lai")
DS_NV = "--nhan-vien" in ARGS
PAUSE = 0.45
LA_UUID = lambda t: bool(re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", t.strip().lower()))
if not TOK: sys.exit("Thiếu PANCAKE_USER_TOKEN trong .env")
if (AI or TAT) and not (THU or THAT):
    sys.exit("Đổi vòng chia phải nói rõ --thu (xem trước) hay --that (ghi thật)")

def ca_bay_gio():
    """Ca nao dang truc, theo GIO VIET NAM. VPS chay gio Berlin nen phai quy doi o day,
    dung dat gio Berlin vao ca_sale.json. Ca 'dem' vat qua nua dem nen tu < den."""
    d = json.load(open(os.path.join(HERE, "ca_sale.json"), encoding="utf-8"))
    try:
        from zoneinfo import ZoneInfo
        gio = datetime.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    except Exception:                      # python cu / thieu tzdata
        gio = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    hm = gio.strftime("%H:%M")
    for c in d["ca"]:
        tu, den = c["tu"], c["den"]
        if (tu <= hm <= den) if tu <= den else (hm >= tu or hm <= den):
            return c, hm
    return None, hm

def call(method, url, params, body=None):
    u = url + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    res = {"success": False, "message": "chưa gọi"}
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
        if res.get("error_code") == 429 or "internal error" in str(res.get("message", "")).lower():
            time.sleep(3 + 3 * lan); continue
        return res
    return res

# ── page thuộc thị trường nào (để in cho dễ soi; lấy từ state/<tt>/page_tokens.json) ──
def ban_do_thi_truong():
    bd = {}
    mk = [k for k in json.load(open(os.path.join(HERE, "markets.json"))) if not k.startswith("_")]
    for m in mk:
        p = os.path.join(HERE, "state", m, "page_tokens.json")
        if os.path.exists(p):
            for pid in json.load(open(p)): bd[str(pid)] = m
    return bd

def ai_dang_chay():
    d = call("GET", "https://pages.fm/api/v1/me", {"access_token": TOK}) or {}
    me = d.get("data") or d.get("me") or {}
    return me.get("id"), me.get("name") or me.get("user_name") or "?"

def doc_page(pid):
    """Trả (settings, nhân viên) của 1 page. Page hết gói / bị vô hiệu hoá thì settings=None."""
    s = call("GET", f"https://pages.fm/api/v1/pages/{pid}/settings", {"access_token": TOK})
    st = (s or {}).get("settings")
    if not isinstance(st, dict):
        return None, (s or {}).get("message", "không đọc được settings"), []
    u = call("GET", f"https://pages.fm/api/v1/pages/{pid}/users", {"access_token": TOK})
    ns = [x for x in ((u or {}).get("users") or []) if x.get("id")]
    return st, None, ns

def ghi_page(pid, key, changes):
    return call("POST", f"https://pancake.vn/api/v1/pages/{pid}/settings", {"access_token": TOK},
                {"changes": json.dumps(changes), "current_settings_key": key})

pages = call("GET", "https://pages.fm/api/v1/pages", {"access_token": TOK})
cat = (pages or {}).get("categorized") or {}
allp = (cat.get("activated") or []) + (cat.get("inactivated") or [])
if not allp: sys.exit(f"Không đọc được danh sách page: {(pages or {}).get('message')}")
BD = ban_do_thi_truong()
if ONE: allp = [p for p in allp if str(p["id"]) == str(ONE)]
if TT:  allp = [p for p in allp if BD.get(str(p["id"])) == TT]
if not allp: sys.exit("Không có page nào khớp bộ lọc")

log = open(os.path.join(HERE, "state", "chia_sale.log"), "a")
def out(s): print(s, flush=True); log.write(s + "\n"); log.flush()

TOI, TEN_TOI = ai_dang_chay()
print(f"Tài khoản: {TEN_TOI} · đọc cài đặt {len(allp)} page…", file=sys.stderr)
kq = list(ThreadPoolExecutor(8).map(lambda p: (p, *doc_page(str(p["id"]))), allp))

# ───────────────────────────── chế độ SOI ─────────────────────────────
ten_cua = {}                      # id nhân viên -> tên
so_page_cua = {}                  # id nhân viên -> số page có mặt trong danh sách nhân viên
for p, st, err, ns in kq:
    for x in ns:
        ten_cua[x["id"]] = x.get("name") or "(không tên)"
        so_page_cua[x["id"]] = so_page_cua.get(x["id"], 0) + 1

if DS_NV:
    out(f"=== NHÂN VIÊN có thể đưa vào vòng chia ({len(ten_cua)} người)")
    nhom = {}
    for uid in ten_cua: nhom.setdefault(Q.norm(ten_cua[uid]), []).append(uid)
    for uid, n in sorted(so_page_cua.items(), key=lambda kv: -kv[1]):
        trung = len(nhom.get(Q.norm(ten_cua[uid]), [])) > 1
        out(f"  {n:4d} page  {ten_cua[uid]:26s} {uid}" + ("   ⚠ TRÙNG TÊN — phải dùng UUID" if trung else ""))
    sys.exit(0)

doc_ok = [(p, st, ns) for p, st, err, ns in kq if st]
loi    = [(p, err)    for p, st, err, ns in kq if not st]
def vong(st): return list(st.get("hard_round_robin_inbox_user_ids") or [])
def bang_nhau(cu, moi):
    """Danh sach nguoi so theo TAP, khong theo thu tu — neu khong thi moi lan cron chay lai
    se ghi de 142 page chi vi thu tu khac, va con tro luan phien cua Pancake bi dat lai."""
    for k, v in moi.items():
        c = cu.get(k)
        if isinstance(v, list) and isinstance(c, (list, type(None))):
            if sorted(v) != sorted(c or []): return False
        elif c != v: return False
    return True
def vai_tro(ns): return next((x.get("role_in_page") for x in ns if x.get("id") == TOI), "KHÔNG CÓ TRONG PAGE")
def dang_chia(st): return bool(st.get("hard_round_robin")) and bool(vong(st))

SO_CA = os.path.join(HERE, "state", "ca_da_ap.json")

def da_ap(ten_ca):
    """Ca nay ap xong chua? CRON_TZ khong an tren VPS (do 20/09: cron chay theo gio Berlin),
    nen cron chay 10 phut/lan va CHO SCRIPT tu quyet gio Viet Nam. Cua nay de moi lan chay
    khong dung viec chi ton 1 lan doc file. Ghi loi thi thu lai toi 3 luot roi thoi."""
    try: d = json.load(open(SO_CA, encoding="utf-8"))
    except Exception: return False
    return d.get("ca") == ten_ca and (not d.get("loi") or d.get("lan", 1) >= 3)

def ghi_so_ca(ten_ca, loi):
    try: cu = json.load(open(SO_CA, encoding="utf-8"))
    except Exception: cu = {}
    json.dump({"ca": ten_ca, "luc": datetime.datetime.now().isoformat(timespec="seconds"),
               "loi": loi, "lan": (cu.get("lan", 0) + 1) if cu.get("ca") == ten_ca else 1},
              open(SO_CA, "w"), ensure_ascii=False)

if CA:
    _ca, _hm = ca_bay_gio()
    if not _ca: sys.exit(f"ca_sale.json khong co ca nao phu gio Việt Nam {_hm}")
    _xau = [n for n in _ca["nguoi"] if not LA_UUID(n.get("uid", ""))]
    if _xau: sys.exit("ca_sale.json con uid chua chot: "
                      + ", ".join(f"{n['ten']}={n.get('uid')}" for n in _xau))
    AI = ",".join(n["uid"] for n in _ca["nguoi"])
    out(f"Giờ Việt Nam {_hm} → ca “{_ca['ten']}” ({_ca['tu']}-{_ca['den']}): "
        + ", ".join(n["ten"] for n in _ca["nguoi"]))
    if THAT and not EP and da_ap(_ca["ten"]):
        out(f"  ca “{_ca['ten']}” đã áp trước đó — không làm gì (thêm --ep để ép áp lại)")
        sys.exit(0)

if not AI and not TAT:
    out(f"=== SOI VÒNG CHIA · tài khoản {TEN_TOI} · {datetime.datetime.now():%F %T} · {len(allp)} page")
    for p, st, ns in sorted(doc_ok, key=lambda x: (BD.get(str(x[0]['id']), 'zz'), str(x[0]['name']))):
        v = vong(st)
        ai_do = ", ".join(ten_cua.get(u, u[:8]) for u in v) or "—"
        out(f"  {BD.get(str(p['id']),'?'):8s} {str(p['name'])[:40]:40s} "
            f"{'CHIA' if dang_chia(st) else 'TẮT ':4s} {len(ns):3d} nv → {ai_do}"
            + ("" if vai_tro(ns) == "ADMINISTER" else f"   [{vai_tro(ns)} — không ghi được]"))
    chia = [x for x in doc_ok if dang_chia(x[1])]
    bo = {}
    for p, st, ns in chia: bo.setdefault(tuple(sorted(vong(st))), []).append(p)
    out(f"\n  Đọc được cài đặt : {len(doc_ok)}/{len(allp)} page")
    out(f"  Đang chia tự động: {len(chia)} page · chưa chia: {len(doc_ok)-len(chia)} page")
    for b, ps in sorted(bo.items(), key=lambda kv: -len(kv[1])):
        out(f"     {len(ps):4d} page  ←  " + ", ".join(ten_cua.get(u, u[:8]) for u in b))
    if len(doc_ok) - len(chia):
        out("  Page chưa chia:")
        for p, st, ns in doc_ok:
            if not dang_chia(st):
                out(f"     {BD.get(str(p['id']),'?'):8s} {str(p['name'])[:44]:44s} ({len(ns)} nv)")
    if loi:
        ly_do = {}
        for p, e in loi: ly_do[str(e)[:38]] = ly_do.get(str(e)[:38], 0) + 1
        out(f"  Không đọc được   : {len(loi)} page — " +
            " · ".join(f"{k}: {v}" for k, v in sorted(ly_do.items(), key=lambda kv: -kv[1])))
    sys.exit(0)

# ───────────────────────── chế độ ĐẶT / TẮT ─────────────────────────
muon = [x.strip() for x in (AI or "").split(",") if x.strip()]
out(f"=== {'TẮT CHIA' if TAT else 'ĐẶT VÒNG CHIA'} · {datetime.datetime.now():%F %T} · "
    f"{'THỬ' if THU else 'THẬT'} · {len(doc_ok)} page đọc được"
    + (f" · người: {', '.join(muon)}" if muon else ""))
sao_luu, tk = [], {"doi": 0, "y_nguyen": 0, "thieu_nguoi": 0, "loi": 0, "bo_qua": 0,
                   "loi_quyen": 0, "loi_khac": 0}
for p, st, ns in doc_ok:
    pid, ten_page = str(p["id"]), str(p["name"])[:40]
    nhan = f"  {BD.get(pid,'?'):8s} {ten_page:40s}"
    if CHUA and dang_chia(st): tk["bo_qua"] += 1; continue
    if TAT:
        moi, changes = [], {"hard_round_robin": False}
    else:
        tra = {}
        for x in ns: tra.setdefault(Q.norm(x.get("name")), []).append(x["id"])
        co_id = {x["id"] for x in ns}
        moi, thieu, mo_ho = [], [], []
        for t in muon:
            if LA_UUID(t):
                (moi.append(t.strip().lower()) if t.strip().lower() in co_id else thieu.append(t)); continue
            ds = tra.get(Q.norm(t)) or []
            if len(ds) == 1:  moi.append(ds[0])
            elif not ds:      thieu.append(t)
            else:             mo_ho.append((t, ds))
        if thieu and CA and moi:
            # Ca kip: ai khong co trong page thi bo ra, page van phai doi nguoi truc —
            # de nguyen danh sach ca truoc la khach ca dem roi vao tay nguoi ca sang.
            out(f"{nhan} ⚠ page không có {', '.join(t if not LA_UUID(t) else t[:8] for t in thieu)}"
                f" — ca này chỉ còn {len(moi)} người trên page")
            thieu = []
        if thieu:
            tk["thieu_nguoi"] += 1
            out(f"{nhan} ✖ page không có: {', '.join(thieu)} (page này {len(ns)} nv) — BỎ QUA")
            continue
        if mo_ho:
            tk["thieu_nguoi"] += 1
            for t, ds in mo_ho:
                out(f"{nhan} ✖ page có {len(ds)} người tên “{t}” — BỎ QUA, phải truyền UUID: {', '.join(ds)}")
            continue
        changes = {"hard_round_robin_inbox_user_ids": moi}
        if not CHI_DS:
            # Chu shop chot 20/09: MOI sale phai thay duoc data cua minh VA cua nguoi khac,
            # nguoi khong duoc chia cung van thay. Ghim lai moi luot doi ca de khong ai bam
            # nguoc trong giao dien roi che mat nhau.
            changes = {"hard_round_robin": True,
                       "show_only_assigned_conv": False,
                       "hard_round_robin_show_all_convs_if_user_not_in_list": True,
                       # 20/09 su co: nut nay dang la 5 -> moi lan doi ca, Pancake GIANH lai moi
                       # hoi thoai 5 phut khong ai doc va giao cho nguoi trong danh sach moi.
                       # Do that: 1.120 hoi thoai bi lay khoi tay nguoi dang lam, sale mat don
                       # vua chot. Ep ve 0 = doi ca chi anh huong KHACH MOI.
                       "hard_round_robin_reassign_if_unread_after_x_min": 0,
                       **changes}
        if CMT: changes["hard_round_robin_comment_user_ids"] = moi
        if ONL: changes["hard_round_robin_only_assign_to_online_user"] = True
        if GIAO_LAI is not None:
            changes["hard_round_robin_reassign_if_unread_after_x_min"] = int(GIAO_LAI)
    if not TAT and vai_tro(ns) != "ADMINISTER":
        out(f"{nhan} ⚠ tài khoản {TEN_TOI} chỉ là {vai_tro(ns)} trên page này — Pancake sẽ từ chối ghi")
    cu = {k: st.get(k) for k in changes}
    if bang_nhau(cu, changes): tk["y_nguyen"] += 1; continue
    ai_cu = ", ".join(ten_cua.get(u, u[:8]) for u in vong(st)) or "—"
    ai_moi = ", ".join(ten_cua.get(u, u[:8]) for u in moi) or "—"
    if THU:
        out(f"{nhan} [THỬ] {ai_cu}  →  {ai_moi}"); tk["doi"] += 1; continue
    time.sleep(PAUSE)
    r = ghi_page(pid, st.get("current_settings_key"), changes)
    # KHÔNG tin câu trả lời của Pancake: 20/09 có 4 page trả "Missing permissions!" nhưng thay
    # đổi vẫn vào. Luôn đọc lại để biết sự thật.
    # XAC MINH BANG PHAN HOI CUA CHINH LENH GHI. Hai bai hoc dat gia 20/09:
    #  1. `GET settings` CO CACHE vai giay -> doc lai ngay sau khi ghi ra gia tri CU, bao sai
    #     ca hai chieu ("khong an" du da an, va nguoc lai).
    #  2. Cho `an = True` khi changes khong co khoa danh sach nguoi (che do --tat) la BAO BUA:
    #     no bao tat xong 141 page trong khi chua tat page nao.
    st2 = ((r or {}).get("change_settings") or {}).get("settings") or {}
    if not st2:                       # phan hoi khong kem settings -> danh phai doc lai
        time.sleep(3)
        st2 = (call("GET", f"https://pages.fm/api/v1/pages/{pid}/settings",
                    {"access_token": TOK}) or {}).get("settings") or {}
    an = bool(st2) and bang_nhau(st2, changes)
    lech = [k for k, v in changes.items() if not isinstance(v, list) and st2.get(k) != v] if st2 else []
    bao_loi = "" if (r or {}).get("success") else str((r or {}).get("message"))[:60]
    if an:
        sao_luu.append({"pid": pid, "ten": ten_page, "cu": cu})
        tk["doi"] += 1
        out(f"{nhan} ✔ {ai_cu}  →  {ai_moi}"
            + (f"   (núm chưa thấy đổi: {', '.join(lech)})" if lech else ""))
    else:
        tk["loi"] += 1
        # Loỗi QUYỀN là vĩnh viễn (30 page), lỗi khác mới đáng thử lại — không tách thì mỗi ca
        # quét lại 3 lượt 478 page vô ích.
        tk["loi_quyen" if "Missing permissions" in bao_loi else "loi_khac"] += 1
        out(f"{nhan} ✖ KHÔNG ĂN: {bao_loi or 'Pancake báo thành công nhưng đọc lại không đổi'}")
if sao_luu:
    f = os.path.join(HERE, "state", f"chia_sale_saoluu-{datetime.datetime.now():%Y%m%d-%H%M}.json")
    json.dump(sao_luu, open(f, "w"), ensure_ascii=False, indent=1)
    out(f"  Sao lưu cấu hình cũ: {f}")
if CA and THAT: ghi_so_ca(_ca["ten"], tk["loi_khac"])
out(f"  Đổi {tk['doi']} · y nguyên {tk['y_nguyen']} · thiếu người {tk['thieu_nguoi']}"
    f" · bỏ qua (đã chia) {tk['bo_qua']} · chặn quyền {tk['loi_quyen']}"
    f" · lỗi khác {tk['loi_khac']} · không đọc được {len(loi)}")

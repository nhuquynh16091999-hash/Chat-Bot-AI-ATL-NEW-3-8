#!/usr/bin/env python3
"""Ghi số đơn landing vào hội thoại Messenger của khách (chủ shop chốt 23/09/2026, "hướng B").

Khách đặt form landing xong bấm sang Messenger → Botcake gửi "Thank you for your order… Phone…
Product…". Khung "Đơn hàng" cạnh chat KHÔNG BAO GIỜ hiện đơn landing:
  - POS bỏ qua page_id/conversation_id khi sửa đơn đã tạo (thử thật trên #76556 — không trường nào đổi);
  - page nhận tin có thể nối shop POS khác shop của đơn (Yuki Store → shop 1720119150, đơn ở shop Saudi).
Sale không thấy đơn → dễ bấm "Tạo mới" ra đơn trùng. Nên: tìm đúng hội thoại rồi GHI CHÚ số đơn.

Chỉ ghi khi CẢ BA khớp (chủ shop: "phải đúng page khách mua sp"):
  1. một tin do PAGE gửi trong hội thoại có đủ SĐT của đơn (so 8 số cuối);
  2. cũng tin đó có mã hoặc tên sản phẩm của đơn;
  3. tin gửi trong [đơn tạo − 10 phút, đơn tạo + 3 giờ].
Lệch một thứ là bỏ qua, không đoán. Mã giới thiệu lúc khách bấm từ landing sang Messenger
(activities[].ref "ladipagesaudi_<tên>_<SĐT>_…_<giá>_<mã SP> <tên SP>") cũng được tính như tin Botcake.

24/09 thêm (chủ shop: "để tôi nắm được khách đó là khách nào", không được hủy đơn):
  - ghi vào ghi chú ĐƠN POS một dòng "[Tự động LP→Chat] …" kèm link mở đúng hội thoại
    (https://pancake.vn/<page>?c_id=<conv> — khuôn link lấy từ mã giao diện POS);
  - gắn page vào đơn + mã Facebook hội thoại vào khách POS của đơn (chỉ khi khách chưa có) —
    thử để khung "Đơn hàng" cạnh chat tự nhận đơn; lượt sau tự kiểm, log ✅/⏳.
  Chỉ làm khi đơn ĐÃ QUA "Mới"/"Chờ xác nhận": don_landing nhận đơn landing nhờ đơn CHƯA có page, gắn
  sớm là nó bỏ sót đơn đang treo. Dòng ghi chú mở đầu "[Tự động" = dòng hệ thống với tach_note.

24/09 tối (v3) — ĐÃ TÌM RA CÁCH ĐƠN HIỆN Ở KHUNG "ĐƠN HÀNG":
  - Pancake tự nối hồ sơ khách chat với khách POS THEO SĐT TRONG HỒ SƠ KHÁCH CHAT (đo 6/6 ca khách tự gõ SĐT).
    SĐT chỉ nằm trong tin Botcake/page thì Pancake không bắt → không nối (ca Parves).
  - Nên khi khớp: thêm SĐT đơn vào hồ sơ khách bằng lệnh chính thức
    PUT pages.fm/api/public_api/v1/pages/<page>/page_customers/<id> {"changes":{"phone_numbers":[…]}}
    (token page trong state/*/page_tokens.json). Thử #76556: 8 giây sau hồ sơ trỏ đúng khách POS, khung hiện đơn.
  - Bỏ gắn page_id vào đơn + fb_id cho khách POS (cách thử cũ, không làm đơn hiện, lại đụng don_landing).
  - Khách TỰ GÕ SĐT trùng đơn landing ≤7 ngày (ca Meliza #76573 → lên trùng #76930): ghi cảnh báo vào hội
    thoại. Pancake cũng tự nối ca này; cảnh báo để sale không bỏ lỡ.
  - Khung khớp tin Botcake / mã landing nới 3 giờ → 24 giờ. Đơn landing nạp 7 ngày mỗi 30 phút + 45 phút
    gần nhất mỗi lượt (POS không bị hỏi 7 ngày mỗi phút).

Chạy NỀN trong daemon pancake-len-don (auto_len_don.daemon gọi chay_nen), 60 giây/lượt, không chờ
vòng lên đơn (vòng đó dài hàng chục phút). Tắt: LANDING_VAO_CHAT=0 trong .env (đọc lại mỗi lượt,
không cần restart). Đọc tin qua API tài khoản KHÔNG kèm user_view → không để dấu "đã xem" (đã thử).

Lệnh tay:
  python3 landing_vao_chat.py thu  [--gio 3] [--page <page_id>]   # chỉ đọc, in ca khớp
  python3 landing_vao_chat.py mot  [--gio 3] [--page <page_id>]   # chạy thật 1 lượt
"""
import datetime
import glob
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(DIR, "state", "chung", "landing_vao_chat.json")
DS_PAGE = os.path.join(DIR, "state", "chung", "ds_page_tai_khoan.json")
LOG_FILE = os.path.join(DIR, "state", "nhat_ky.log")
WEB_API = "https://pancake.vn/api/v1"
POS_API = "https://pos.pages.fm/api/v1"
PUBLIC_API = "https://pages.fm/api/public_api/v1"

CHU_KY = 60                  # giây giữa hai lượt quét
CUA_SO_DON = 24 * 3600       # tin Botcake / mã landing trong 24 giờ sau đơn mới tính là khớp
TRUOC_DON = 10 * 60          # tin Botcake được phép sớm hơn giờ tạo đơn tối đa 10 phút
GOI_LAP = 120                # quét chồng lên lượt trước 2 phút cho khỏi sót ở mép
LO_GOP = 120                 # page mỗi lô lệnh gộp (344 page/URL thì Pancake trả 414)
VONG_TOI_DA = 8              # lật trang tối đa mỗi lô mỗi lượt
DOC_TOI_DA = 40              # hội thoại mở đọc tối đa mỗi lượt
NHIN_LAI_TOI_DA = 10 * 60    # mỗi lượt quét lùi tối đa 10 phút (lần đầu 5) — quét lùi xa phải lật ~20 trang
NGHI_KHI_CHAN = 180          # bị 429 / quá giờ thì nghỉ 3 phút: token tài khoản này AI Sale cũng đang dùng
TIN_NGAN = 6                 # hội thoại mới ≤ ngần này tin thì mở đọc dù không thấy SĐT/tên
TT_BO = {6, 7}               # đơn đã hủy / đã xóa thì không ghi
TT_CHUA_DI = {0, 17}         # Mới / Chờ xác nhận — don_landing còn xét, CHƯA được gắn page
CHO_GAN_TOI_DA = 24 * 3600   # đơn treo quá 24 giờ chưa qua xác nhận thì thôi gắn
KIEM_CACH = 600              # kiểm khung "Đơn hàng" mỗi 10 phút, tối đa KIEM_LAN lần
KIEM_LAN = 4
CANH_BAO_NGAY = 7 * 86400    # khách tự gõ SĐT trùng đơn landing trong 7 ngày → cảnh báo
KHO_LAM_MOI = 1800           # nạp lại đơn landing 7 ngày mỗi 30 phút
TEN_TT = {0: "Mới", 17: "Chờ xác nhận", 11: "Chờ hàng", 12: "Chờ in", 13: "Đã in", 20: "Đã đặt hàng",
          1: "Đã xác nhận", 8: "Đang đóng hàng", 9: "Chờ chuyển hàng", 2: "Đã gửi hàng", 3: "Đã nhận",
          16: "Đã thu tiền", 4: "Đang hoàn", 15: "Hoàn một phần", 5: "Đã hoàn", 6: "Đã hủy", 7: "Đã xóa"}
TT_DA_DI = {2, 3, 16, 4, 15, 5}   # đơn đã đi / đã xong → khách nhắn lại có thể là mua mới

_GOP_HONG = {}               # page lệnh gộp từ chối (hết gói / không quyền) -> lúc phát hiện; quên sau 30'
_NGHI = {"den": 0.0}         # nghỉ tới lúc này (sau 429 / quá giờ)


def _env():
    env = {}
    try:
        for line in open(os.path.join(DIR, ".env"), encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def _log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [LANDING→CHAT] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _http(method, url, params=None, body=None, timeout=60):
    u = url + ("?" + urllib.parse.urlencode(params or {}, doseq=True) if params else "")
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(u, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:                               # noqa: BLE001 — mạng chập chờn: bỏ lượt này
        return None, str(e)[:120]


def _giay(s):
    """'2026-09-23T09:25:42.000000' (UTC, không múi giờ) -> epoch."""
    try:
        return datetime.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=datetime.timezone.utc).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _chu(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _so(s):
    return re.sub(r"\D", "", str(s or ""))


def _tu_ten(s):
    return {w for w in _chu(s).split() if len(w) >= 3 and not w.isdigit()}


# ───────────────────────── đơn landing chờ ghi ─────────────────────────

def _thi_truong():
    try:
        mk = json.load(open(os.path.join(DIR, "markets.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in mk.items() if isinstance(v, dict) and v.get("bat", True) and v.get("api_key")}


def _san_pham(o):
    """[(mã, {từ tên})] của đơn — từ dòng hàng, không có thì từ dòng ưu đãi trong ghi chú."""
    out = []
    for it in o.get("items") or []:
        vi = it.get("variation_info") or {}
        ten = vi.get("name") or ""
        ma = str(vi.get("product_display_id") or "").strip()
        if not ma:
            m = re.match(r"\s*(\d{2,5})\b", ten)
            ma = m.group(1) if m else ""
        out.append((ma, {w for w in _chu(re.sub(r"^\s*\d+\s*-\s*", "", ten)).split() if len(w) >= 4}))
    if not out:
        for dong in (o.get("note") or "").splitlines():
            if "|" in dong:
                ten = dong.split("|", 1)[0]
                m = re.match(r"\s*(\d{2,5})\b", ten)
                out.append((m.group(1) if m else "",
                            {w for w in _chu(re.sub(r"^\s*\d+\s*-\s*", "", ten)).split() if len(w) >= 4}))
                break
    return [(ma, tu) for ma, tu in out if ma or tu]


_KHO = {"luc": 0.0, "don": {}}     # khoá "shop:id" -> đơn landing gọn (7 ngày)


def _mot_don(o, m, mkey):
    """Đơn landing gọn, hoặc None: không gắn hội thoại + nguồn landing/rỗng + chưa hủy + có SĐT."""
    if o.get("conversation_id") or o.get("status") in TT_BO or str(o.get("order_sources")) not in ("None", "-7", ""):
        return None
    # DON_CHAT_2909: đơn máy lên đơn tạo từ chat trên page trạm khác shop (không gắn được page) trông y đơn
    # landing — ca Realita #51528: khách chỉ hỏi, máy lại ghi "KHÁCH ĐÃ CÓ ĐƠN LANDING" + thẻ Đã gửi → AI im.
    if (o.get("note") or "").lstrip().startswith("[Tự động] Từ hội thoại"):
        return None
    sdt = _so(o.get("bill_phone_number"))
    if len(sdt) < 8:
        return None
    ten_sp = "; ".join(dict.fromkeys(
        (it.get("variation_info") or {}).get("name") or "" for it in o.get("items") or [])).strip("; ")
    if not ten_sp:
        dong = [x for x in (o.get("note") or "").splitlines() if "|" in x]
        ten_sp = dong[0].split("|", 1)[0].strip() if dong else ""
    scale = m.get("scale") or 100
    tien = o.get("money_to_collect")
    return {"khoa": f"{m['shop_id']}:{o.get('id')}", "id": o.get("id"), "mkey": mkey,
            "shop": str(m["shop_id"]), "ten_tt": m.get("ten") or mkey.upper(),
            "luc": _giay(o.get("inserted_at")), "sdt": sdt, "sdt8": sdt[-8:], "bill_sdt": o.get("bill_phone_number"),
            "ten": o.get("bill_full_name") or "", "tu_ten": _tu_ten(o.get("bill_full_name")),
            "sp": _san_pham(o), "ten_sp": ten_sp, "tt": o.get("status"),
            "tien": (f"{tien / scale:g} {m.get('tien_te') or ''}".strip() if isinstance(tien, (int, float)) else ""),
            "khach_pos": (o.get("customer") or {}).get("id")}


def nap_kho(now, mks=None):
    """Đơn landing 7 ngày: nạp đủ mỗi 30 phút, giữa chừng chỉ nạp 45 phút gần nhất rồi trộn vào."""
    mks = mks or _thi_truong()
    du = now - _KHO["luc"] > KHO_LAM_MOI
    tu = now - CANH_BAO_NGAY if du else now - 45 * 60
    moi = {}
    for mkey, m in mks.items():
        for trang in range(1, 41 if du else 3):
            res, err = _http("GET", f"{POS_API}/shops/{m['shop_id']}/orders",
                             {"api_key": m["api_key"], "startDateTime": int(tu),
                              "endDateTime": int(now), "page_size": 100, "page_number": trang})
            if err or not isinstance((res or {}).get("data"), list):
                break
            for o in res["data"]:
                k = f"{m['shop_id']}:{o.get('id')}"
                moi[k] = _mot_don(o, m, mkey)          # None = không còn là đơn landing sống (đã hủy…)
            if len(res["data"]) < 100:
                break
            time.sleep(0.2)
    if du:
        _KHO["don"] = {k: v for k, v in moi.items() if v}
        _KHO["luc"] = now
    else:
        for k, v in moi.items():
            if v:
                _KHO["don"][k] = v
            else:
                _KHO["don"].pop(k, None)
    return _KHO["don"]


def don_cho(now, mks=None):
    """Đơn landing tạo trong CUA_SO_DON có sản phẩm — ứng viên khớp theo tin Botcake / mã landing."""
    return [d for d in nap_kho(now, mks).values() if d["sp"] and now - d["luc"] <= CUA_SO_DON]


# ───────────────────────── hội thoại mới đổi ─────────────────────────

def _page_con_goi(chi_page=None):
    if chi_page:
        return [str(chi_page)]
    try:
        d = json.load(open(DS_PAGE, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [str(p["id"]) for p in d.get("pages") or []
            if p.get("has_active_subscription") and p.get("platform", "facebook") == "facebook"]


def hoi_thoai_tu(moc, tok, chi_page=None):
    """Hội thoại INBOX đổi từ `moc` (epoch) trên mọi page còn gói — lệnh gộp, lật trang tới mốc.
    Trả (danh sách, đủ) — đủ=False khi có lô bị 429/quá giờ: đừng dời mốc, lượt sau quét lại."""
    now = time.time()
    for p, t in list(_GOP_HONG.items()):
        if now - t > 1800:
            _GOP_HONG.pop(p, None)
    ids = [p for p in _page_con_goi(chi_page) if p not in _GOP_HONG]
    ra, du = {}, True
    for i in range(0, len(ids), LO_GOP):
        lo = ids[i:i + LO_GOP]
        dem = {x: 0 for x in lo}
        for _ in range(VONG_TOI_DA + 3):                   # +3 lần gọi lại khi lô có page hỏng
            prm = {("pages[%s]" % x): dem[x] for x in lo}
            prm.update({"unread_first": "false", "mode": "NONE", "tags": '"ALL"', "except_tags": "[]",
                        "access_token": tok, "cursor_mode": "true", "from_platform": "web"})
            res, err = _http("GET", f"{WEB_API}/conversations", prm)
            cs = (res or {}).get("conversations")
            if not isinstance(cs, list):
                # MỘT page hết gói/không quyền là cả lô trả lỗi — Pancake kể tên page trong `errors`
                hong = {str(x.get("page_id")) for x in ((res or {}).get("errors") or [])
                        if isinstance(x, dict) and x.get("page_id")}
                if not hong:
                    du = False
                    if err and ("429" in err or "timed out" in err):
                        _NGHI["den"] = time.time() + NGHI_KHI_CHAN
                        _log(f"⚠ lệnh gộp bị chặn ({err}) — nghỉ {NGHI_KHI_CHAN // 60} phút")
                        return list(ra.values()), False
                    _log(f"⚠ lệnh gộp hỏng ({err or str(res)[:100]}) — bỏ lô này lượt này")
                    break
                for x in hong:
                    _GOP_HONG[x] = time.time()
                lo = [x for x in lo if x not in hong]
                if not lo:
                    break
                continue
            for c in cs:
                if c.get("type") == "INBOX" and _giay(c.get("updated_at")) >= moc:
                    ra[str(c.get("id"))] = c
            pw = res.get("pages_with_current_count") or {}
            dem.update({str(k): v for k, v in pw.items() if str(k) in dem})
            if not cs or min(_giay(c.get("updated_at")) for c in cs) < moc:
                break
            time.sleep(0.5)
    return list(ra.values()), du


def doc_tin(c, tok):
    """Tin + ghi chú của hội thoại qua API tài khoản. KHÔNG user_view → không lật dấu 'đã xem'."""
    pid = str(c.get("page_id") or "")
    cust = ((c.get("customers") or [{}])[0] or {}).get("id")
    if not (pid and cust):
        return None, "thiếu page_id/customer_id"
    return _http("GET", f"{WEB_API}/pages/{pid}/conversations/{c.get('id')}/messages",
                 {"access_token": tok, "customer_id": cust})


# ───────────────────────── so khớp ─────────────────────────

def _cham_sdt(chu, sdt8):
    """Tin có SĐT kết thúc bằng 8 số cuối của đơn (số có cách/gạch/+mã nước vẫn nhận)."""
    for cum in re.findall(r"\+?\d[\d\s\-.()]{6,}\d", chu or ""):
        if _so(cum).endswith(sdt8):
            return True
    return False


def _cham_sp(chu, sp):
    t = _chu(chu)
    tu = set(t.split())
    for ma, ten in sp:
        if ma and re.search(rf"(?<!\d){re.escape(ma)}(?!\d)", t):
            return True
        if ten and len(ten & tu) >= max(1, (len(ten) + 1) // 2):
            return True
    return False


def _cham_ref(ref, d):
    """Mã giới thiệu landing: '<nguồn>_<tên>_<SĐT>_<địa chỉ…>_<giá>_<mã SP> <tên SP>' — tách theo '_'."""
    phan = str(ref or "").split("_")
    return (any(len(_so(x)) >= 8 and _so(x).endswith(d["sdt8"]) for x in phan)
            and _cham_sp(" ".join(phan), d["sp"]))


def khop(c, tin, dons, hoat_dong=None):
    """Các đơn khớp hội thoại: tin PAGE gửi (hoặc mã giới thiệu landing) có đủ SĐT + sản phẩm,
    trong khung giờ của đơn."""
    pid = str(c.get("page_id") or "")
    ra = []
    for d in dons:
        if any(isinstance(a, dict) and a.get("ref")
               and d["luc"] - TRUOC_DON <= _giay(a.get("inserted_at")) <= d["luc"] + CUA_SO_DON
               and _cham_ref(a["ref"], d) for a in (hoat_dong or [])):
            ra.append(d)
            continue
        for m in tin:
            if str((m.get("from") or {}).get("id")) != pid:
                continue                                 # chỉ tin page/Botcake gửi, không tin khách tự gõ
            luc = _giay(m.get("inserted_at"))
            if not (d["luc"] - TRUOC_DON <= luc <= d["luc"] + CUA_SO_DON):
                continue
            chu = m.get("original_message") or m.get("message") or ""
            if _cham_sdt(chu, d["sdt8"]) and _cham_sp(chu, d["sp"]):
                ra.append(d)
                break
    return ra


def _dang_ngo(c, dons):
    """Có đáng mở đọc không (rẻ, chỉ nhìn danh sách): snippet có ≥6 số trùng SĐT đơn, tên trùng,
    hoặc hội thoại MỚI ít tin (khách vừa bấm từ landing — Botcake gửi xác nhận ngay sau)."""
    snip = c.get("snippet") or ""
    so_snip = [_so(x) for x in re.findall(r"\d[\d\s\-.]{5,}", snip)]
    ten = _tu_ten(((c.get("from") or {}).get("name") or "") + " " + snip)
    moi = _giay(c.get("inserted_at"))
    for d in dons:
        if any(len(x) >= 6 and x in d["sdt"] for x in so_snip):
            return True
        if d["tu_ten"] & ten:
            return True
        if moi >= d["luc"] - TRUOC_DON and (c.get("message_count") or 0) <= TIN_NGAN:
            return True
    return False


def _cau_ghi_chu(ds):
    so = ", ".join(f"#{d['id']}" for d in ds)
    sp = "; ".join(dict.fromkeys(str(d["ten_sp"] or "").strip() for d in ds if d["ten_sp"]))
    return (f"KHÁCH ĐÃ ĐẶT ĐƠN LANDING {so} (shop {ds[0]['ten_tt']}) — đừng tạo đơn mới, xem/sửa đơn trong POS."
            + (f" Sản phẩm: {sp}." if sp else ""))


# ───────────────────────── gắn đơn ↔ hội thoại ─────────────────────────

def _ten_page(pid):
    try:
        for p in json.load(open(DS_PAGE, encoding="utf-8")).get("pages") or []:
            if str(p.get("id")) == str(pid):
                return p.get("name") or str(pid)
    except (OSError, ValueError):
        pass
    return str(pid)


def _pos(mkey, path, method="GET", body=None):
    m = _thi_truong().get(mkey) or {}
    if not m:
        return None, f"không có thị trường {mkey}"
    res, err = _http(method, f"{POS_API}/shops/{m['shop_id']}{path}", {"api_key": m["api_key"]}, body)
    if err:
        return None, err
    return (res.get("data") if isinstance((res or {}).get("data"), dict) else res), None


def _dong_link(v):
    ten = v.get("ten_fb")
    return (f"[Tự động LP→Chat] Khách đã nhắn Messenger{': ' + ten if ten else ''} · page {_ten_page(v['page'])}"
            f" → https://pancake.vn/{v['page']}?c_id={v['conv']}")


def _giu(o):
    return (o.get("status"), o.get("shipping_fee"), o.get("cod"), o.get("money_to_collect"),
            o.get("bill_phone_number"), len(o.get("items") or []))


def gan_don(st, in_ra=False):
    """Đơn đã khớp hội thoại mà đã QUA xác nhận: ghi link hội thoại vào ghi chú đơn.
    Đơn còn Mới/Chờ XN thì chờ lượt sau (ghi chú đơn don_landing còn đọc)."""
    now = time.time()
    for k, v in list(st["da_ghi"].items()):              # ca ghi chú trước bản này: đưa vào hàng gắn một lần
        if not v.get("gan") and v.get("conv") and now - v.get("luc", 0) < 3 * 86400:
            shop, oid = k.split(":", 1)
            mkey = next((mk for mk, m in _thi_truong().items() if str(m["shop_id"]) == shop), None)
            if mkey:
                st["cho_gan"][k] = {"mkey": mkey, "id": int(oid), "conv": v["conv"], "page": v.get("page"),
                                    "ten_fb": v.get("ten_fb"), "cust_chat": v.get("cust_chat"), "luc": int(now)}
            v["gan"] = 1
    for k, v in list(st["cho_gan"].items()):
        o, err = _pos(v["mkey"], f"/orders/{v['id']}")
        if err or not isinstance(o, dict) or not o.get("id"):
            continue                                     # đọc hỏng: lượt sau thử lại
        tt = o.get("status")
        if tt in TT_BO:
            st["cho_gan"].pop(k, None)
            continue
        if tt in TT_CHUA_DI:
            if now - v.get("luc", now) > CHO_GAN_TOI_DA:
                _log(f"⏳ #{v['id']} còn 'Mới/Chờ xác nhận' sau 24 giờ — thôi gắn hội thoại (đã có ghi chú bên chat)")
                st["cho_gan"].pop(k, None)
            continue
        lam = []
        body = {}
        if f"c_id={v['conv']}" not in (o.get("note") or ""):
            body["note"] = ((o.get("note") or "").rstrip() + "\n" + _dong_link(v)).strip()
            lam.append("link hội thoại vào ghi chú đơn")
        if body:
            _, e1 = _pos(v["mkey"], f"/orders/{v['id']}", "PUT", body)
            o2, _ = _pos(v["mkey"], f"/orders/{v['id']}")
            if e1 or not isinstance(o2, dict):
                _log(f"✖ gắn #{v['id']} hỏng: {e1}")
                continue
            if _giu(o2) != _giu(o):
                # POS đổi trường không được đổi → ghi lại giá trị cũ, dừng gắn đơn này
                _pos(v["mkey"], f"/orders/{v['id']}", "PUT",
                     {x: o.get(x) for x in ("status", "shipping_fee", "cod", "bill_phone_number")})
                _log(f"✖ gắn #{v['id']} làm lệch đơn {_giu(o)} → {_giu(o2)} — đã ghi lại giá trị cũ, bỏ gắn")
                st["cho_gan"].pop(k, None)
                continue
        if lam:
            _log(f"🔗 #{v['id']} ↔ hội thoại {v.get('ten_fb') or v['conv']}: " + ", ".join(lam))
        st["cho_gan"].pop(k, None)
        time.sleep(0.2)


# ══ GHI CHÚ IN "CARE ĐƠN QUA MESS" (GHI_CHU_IN_2509) ══════════════════════════════════════════════════════════════
# Chủ shop 25/09 (ảnh Jerry Col Visto · YukiSmart, đơn #77161): *"các đơn landing có mess thì bạn ghi chú in là CARE ĐƠN QUA MESS
# BẰNG ID ĐƠN HÀNG"*. Đơn landing mặc định care qua WhatsApp; đơn nào khách ĐÃ nhắn Messenger — khớp tin Botcake / mã landing
# (da_ghi) hoặc khách tự gõ SĐT trùng đơn (canh_bao) — thì ô "Ghi chú in" (POS `note_print`) ghi đúng câu này. Ô đã có chữ thì NỐI
# thêm, không xoá. Đơn hủy / đã đi thì bỏ. Đơn khớp qua SĐT đã qua Mới/Chờ XN thì nối thêm link hội thoại vào ghi chú đơn (đơn khớp
# tin Botcake đã có gan_don lo; đơn còn Mới/Chờ XN thì KHÔNG đụng ghi chú đơn — don_landing còn đọc nó).
CAU_IN_MESS = "CARE ĐƠN QUA MESS BẰNG ID ĐƠN HÀNG"
IN_MOI_LUOT = 6                  # tối đa bấy nhiêu đơn mỗi lượt 60s (POS không bị hỏi dồn)


def _giu_in(o):
    """_giu + ĐVVC + mã vận đơn — đơn đang giao sửa ô in không được làm rơi vận đơn (GHI_CHU_IN_B_2509)."""
    p = o.get("partner") if isinstance(o.get("partner"), dict) else {}
    return _giu(o) + (p.get("partner_id"), p.get("extend_code"))


def _page_tram():
    """PAGE_LANDING_2909 — page trạm landing (state/chung/page_gan_them.json khoá tram_landing). Đọc hỏng → rỗng."""
    try:
        return set(json.load(open(os.path.join(DIR, "state", "chung", "page_gan_them.json"),
                                  encoding="utf-8")).get("tram_landing") or {})
    except (OSError, ValueError, AttributeError):
        return set()


# HUY_TRUNG_2909 — ca Mary Wisdom: máy ghi "KHÁCH ĐÃ ĐẶT ĐƠN LANDING #77424" lúc khách vừa đặt lặp, 13 phút sau
# don_landing hủy #77424 vì trùng #77000 (đơn đang đi) mà hội thoại không ai báo → sale/AI care nhầm đơn hủy.
# Đơn đã ghi vào hội thoại (da_ghi / canh_bao) mà bị HỦY vì TRÙNG → THÊM 1 ghi chú đính chính (không xoá ghi chú cũ).
HUY_MOI_LUOT = 6
R_HUY_TRUNG = re.compile(r"ĐÃ HỦY \(TRÙNG\)[^#]*#(\d+)")


def bao_huy_trung(st, tok):
    xong = st.setdefault("bao_huy", {})              # "khoá đơn|conv" -> lúc xong | [lúc xét, 0] (chưa hủy)
    now = time.time()
    viec = []
    for k, v in (st.get("da_ghi") or {}).items():
        if (v or {}).get("conv"):
            viec.append((k, v["conv"], v.get("cust_chat"), v.get("luc") or 0))
    for kk, luc in (st.get("canh_bao") or {}).items():
        k, _, conv = kk.partition("|")
        if conv:
            viec.append((k, conv, None, luc or 0))
    shop_mk = {str(m["shop_id"]): mk for mk, m in _thi_truong().items()}
    lam = 0
    for k, conv, cust, luc in viec:
        khoa = f"{k}|{conv}"
        x = xong.get(khoa)
        if isinstance(x, int) or now - luc > 2 * 86400 or lam >= HUY_MOI_LUOT:
            continue
        if isinstance(x, list) and now - x[0] < 1800:
            continue                                  # chưa hủy: 30 phút xem lại một lần
        shop, _, oid = k.partition(":")
        mkey = shop_mk.get(shop)
        if not mkey:
            continue
        lam += 1
        o, err = _pos(mkey, f"/orders/{oid}")
        if err or not isinstance(o, dict) or not o.get("id"):
            continue
        m = R_HUY_TRUNG.search(o.get("note") or "")
        if o.get("status") not in TT_BO or not m:
            xong[khoa] = [int(now), 0] if o.get("status") not in TT_BO else int(now)   # hủy vì lý do khác → thôi
            continue
        giu, _ = _pos(mkey, f"/orders/{m.group(1)}")
        tt = TEN_TT.get((giu or {}).get("status"), (giu or {}).get("status", "?"))
        page = conv.split("_", 1)[0]
        for q in ([] if cust else [o.get("bill_full_name"), o.get("bill_phone_number")]):
            if not q:
                continue
            r, _e = _http("GET", f"{WEB_API}/pages/{page}/conversations/search", {"q": q, "access_token": tok})
            c = next((c for c in (r or {}).get("conversations") or [] if str(c.get("id")) == conv), {})
            cust = ((c.get("customers") or [{}])[0] or {}).get("id")
            if cust:
                break
        if not cust:
            xong[khoa] = int(now)
            _log(f"✖ #{oid} hủy trùng — không tìm được hội thoại {conv} để ghi đính chính")
            continue
        cau = (f"ĐÍNH CHÍNH: đơn landing #{oid} ĐÃ HỦY vì khách đặt lặp (trùng) — đơn được giữ là "
               f"#{m.group(1)} (hiện: {tt}). Care / trả lời khách theo #{m.group(1)}.")
        r2, e2 = _http("POST", f"{WEB_API}/pages/{page}/customers/{cust}/notes", {"access_token": tok},
                       {"message": cau, "conversation_id": conv, "images": "[]", "links": "[]"})
        if e2 or not r2 or r2.get("success") is False:
            _log(f"✖ đính chính hủy trùng #{oid} hỏng ({conv}): {e2 or str(r2)[:120]}")
            continue
        xong[khoa] = int(now)
        _log(f"🔁 #{oid} hủy trùng → đính chính hội thoại {conv}: đơn đi #{m.group(1)} ({tt})")
        time.sleep(0.2)


def ghi_chu_in(st, in_ra=False):
    """Ghi 'Ghi chú in' cho đơn landing khách đã nhắn Messenger. Trả số đơn đã ghi."""
    viec = {}
    for k, v in (st.get("da_ghi") or {}).items():
        viec.setdefault(k, (v or {}).get("conv"))
    tram = _page_tram()                                  # PAGE_LANDING_2909 — chỉ page chạy landing
    for k in (st.get("canh_bao") or {}):
        khoa, _, conv = k.partition("|")
        if str(conv).split("_")[0] not in tram:          # PAGE_LANDING_2909 — khách nhắn page Mess thường: không phải khách landing
            continue
        viec.setdefault(khoa, conv or None)
    xong = st.setdefault("ghi_in", {})
    shop_mk = {str(m["shop_id"]): mk for mk, m in _thi_truong().items()}
    ghi = 0
    for khoa, conv in list(viec.items()):
        if khoa in xong or ghi >= IN_MOI_LUOT:
            continue
        shop, _, oid = khoa.partition(":")
        mkey = shop_mk.get(shop)
        if not mkey or not oid.isdigit():
            xong[khoa] = int(time.time())
            continue
        o, err = _pos(mkey, f"/orders/{oid}")
        if err or not isinstance(o, dict) or not o.get("id"):
            continue                                     # đọc hỏng: lượt sau thử lại
        tt = o.get("status")
        if tt in TT_BO or (tt in TT_DA_DI and tt != 2):  # GHI_CHU_IN_B_2509 — 'Đã gửi hàng' (đang giao) vẫn ghi
            xong[khoa] = int(time.time())
            continue
        body = {}
        cu = str(o.get("note_print") or "")
        if CAU_IN_MESS not in cu:
            body["note_print"] = (cu.rstrip() + "\n" + CAU_IN_MESS).strip()
        if conv and tt not in TT_CHUA_DI and f"c_id={conv}" not in (o.get("note") or ""):
            body["note"] = ((o.get("note") or "").rstrip() + "\n"
                            + _dong_link({"page": str(conv).split("_")[0], "conv": conv, "ten_fb": None})).strip()
        if not body:
            xong[khoa] = int(time.time())
            continue
        if in_ra:
            print(f"  🖨 SẼ GHI #{oid} ({mkey}, trạng thái {TEN_TT.get(tt, tt)}): " + ", ".join(sorted(body)))
            continue
        _, e1 = _pos(mkey, f"/orders/{oid}", "PUT", body)
        o2, _ = _pos(mkey, f"/orders/{oid}")
        if e1 or not isinstance(o2, dict):
            _log(f"✖ ghi chú in #{oid} hỏng: {e1}")
            continue
        if _giu_in(o2) != _giu_in(o):                   # GHI_CHU_IN_B_2509 — + ĐVVC / mã vận đơn
            # POS đổi trường không được đổi → ghi lại giá trị cũ, thôi đơn này
            _pos(mkey, f"/orders/{oid}", "PUT", {x: o.get(x) for x in ("status", "shipping_fee", "cod", "bill_phone_number")})
            _log(f"✖ ghi chú in #{oid} làm lệch đơn {_giu(o)} → {_giu(o2)} — đã ghi lại giá trị cũ, bỏ")
            xong[khoa] = int(time.time())
            continue
        if CAU_IN_MESS not in str(o2.get("note_print") or ""):
            _log(f"✖ ghi chú in #{oid}: POS chưa nhận note_print — lượt sau thử lại")
            continue
        xong[khoa] = int(time.time())
        ghi += 1
        _log(f"🖨 #{oid} ghi chú in: {CAU_IN_MESS}" + (" + link hội thoại vào ghi chú đơn" if "note" in body else ""))
        time.sleep(0.2)
    return ghi


def kiem_hien(st, tok):
    """Khung "Đơn hàng" cạnh chat đã nhận đơn chưa: khách bên chat trỏ đúng khách POS của đơn, hoặc
    Pancake đếm được đơn cho khách đó. Kiểm 4 lần cách 10 phút rồi ghi kết quả."""
    now = time.time()
    for k, v in list(st["kiem"].items()):
        if now < v.get("sau", 0):
            continue
        res, err = _http("GET", f"{WEB_API}/pages/{v['page']}/conversations/{v['conv']}/messages",
                         {"access_token": tok, "customer_id": v["cust_chat"]})
        if err or not isinstance(res, dict):
            continue
        kc = (res.get("customers") or [{}])[0] or {}
        hien = (kc.get("customer_id") and kc.get("customer_id") == v.get("khach_pos")) \
            or (kc.get("order_count") or 0) > 0 or bool(res.get("recent_orders"))
        v["lan"] = v.get("lan", 0) + 1
        if hien or v["lan"] >= KIEM_LAN:
            _log(("✅" if hien else "⏳") + f" #{v['id']} {'ĐÃ HIỆN' if hien else 'CHƯA hiện'} ở khung Đơn hàng"
                 f" · {v.get('ten_fb') or v['conv']} (kiểm {v['lan']} lần)")
            st["ket_qua"].append({"id": v["id"], "conv": v["conv"], "hien": bool(hien), "luc": int(now)})
            st["kiem"].pop(k, None)
        else:
            v["sau"] = int(now) + KIEM_CACH


# ───────────────────────── SĐT vào hồ sơ khách chat → khung "Đơn hàng" ─────────────────────────

_TOK_PAGE = {"luc": 0.0, "tok": {}}


def _token_page(pid):
    """Token page (Public API) có sẵn trong state/<tt>/page_tokens.json — KHÔNG sinh token mới."""
    if time.time() - _TOK_PAGE["luc"] > 600:
        bang = {}
        for f in glob.glob(os.path.join(DIR, "state", "*", "page_tokens.json")):
            try:
                for k, v in json.load(open(f, encoding="utf-8")).items():
                    if isinstance(v, dict) and v.get("token") and not v.get("token_hong"):
                        bang.setdefault(str(k), v["token"])
            except (OSError, ValueError):
                continue
        _TOK_PAGE.update(luc=time.time(), tok=bang)
    return _TOK_PAGE["tok"].get(str(pid))


def _sdt_ds(ds):
    return [_so(x.get("phone_number") if isinstance(x, dict) else x) for x in ds or []]


def them_sdt(page, conv, sdt):
    """Thêm SĐT đơn landing vào hồ sơ khách chat (giữ SĐT cũ). Trả (ok, lý do)."""
    tok = _token_page(page)
    if not tok:
        return False, "page chưa có token page"
    res, err = _http("GET", f"{PUBLIC_API}/pages/{page}/conversations/{conv}/messages", {"page_access_token": tok})
    kh = ((res or {}).get("customers") or [{}])[0] or {}
    if err or not kh.get("id"):
        return False, f"không đọc được hồ sơ khách ({err or 'thiếu id'})"
    cu = [x.get("phone_number") if isinstance(x, dict) else x for x in kh.get("recent_phone_numbers") or []]
    cu = [x for x in cu if x]
    # LEN_DAU_2909 — Pancake nối theo SĐT ĐẦU danh sách, so nguyên chuỗi → SĐT đơn (dạng POS) lên đầu, giữ số cũ phía sau
    if cu and str(cu[0]) == str(sdt):
        return True, "hồ sơ đã có SĐT (đứng đầu)"
    r2, e2 = _http("PUT", f"{PUBLIC_API}/pages/{page}/page_customers/{kh['id']}", {"page_access_token": tok},
                   {"changes": {"phone_numbers": [str(sdt)] + [x for x in cu if str(x) != str(sdt)]}})
    if e2 or not r2 or r2.get("success") is False:
        return False, f"thêm SĐT hỏng ({e2 or str(r2)[:100]})"
    return True, "đã đưa SĐT đơn lên đầu hồ sơ" if cu else "đã thêm SĐT"


def bu_sdt(st, toi_da=5):
    """Ca đã khớp trước v3 (chưa có cờ sdt): thêm SĐT bù để đơn hiện ở khung Đơn hàng."""
    now = time.time()
    lam = 0
    for k, v in list(st["da_ghi"].items()):
        if v.get("sdt") or not v.get("conv") or now - v.get("luc", 0) > 3 * 86400 or lam >= toi_da:
            continue
        shop, oid = k.split(":", 1)
        mkey = v.get("mkey") or next((mk for mk, m in _thi_truong().items() if str(m["shop_id"]) == shop), None)
        if not mkey:
            v["sdt"] = "khong_tt"
            continue
        o, err = _pos(mkey, f"/orders/{oid}")
        if err or not isinstance(o, dict) or not o.get("id"):
            continue
        lam += 1
        if o.get("status") in TT_BO:
            v["sdt"] = "huy"
            continue
        ok, ly_do = them_sdt(v.get("page") or v["conv"].split("_")[0], v["conv"], o.get("bill_phone_number"))
        v["sdt"] = 1 if ok else "loi"
        _log(("📱" if ok else "✖") + f" #{oid} (bù): {ly_do} — {v.get('ten_fb') or v['conv']}")
        time.sleep(0.2)


def _cau_canh_bao(ds):
    phan = []
    for d in ds:
        ngay = datetime.datetime.utcfromtimestamp(d["luc"] + 7 * 3600).strftime("%d/%m")   # giờ VN
        phan.append(f"#{d['id']} ({ngay} · {d['ten_sp'] or '?'} · {d['tien'] or '?'} · {TEN_TT.get(d['tt'], d['tt'])})")
    di_roi = all(d["tt"] in TT_DA_DI for d in ds)
    dau = "KHÁCH TỪNG ĐẶT LANDING" if di_roi else "KHÁCH ĐÃ CÓ ĐƠN LANDING"
    duoi = "kiểm trước khi tạo đơn mới." if di_roi else "đừng tạo đơn mới, xem/sửa đơn trong POS."
    return f"{dau} {', '.join(phan)} (shop {ds[0]['ten_tt']}) — {duoi}"


_SHOP_PAGE = {"luc": 0.0, "map": {}}


def _shop_cua_page(page):
    """LEN_DAU_2909 — shop POS đang giữ page (khung Đơn hàng chỉ hiện đơn cùng shop). Nạp lại mỗi 6 giờ; hỏng → None."""
    if time.time() - _SHOP_PAGE["luc"] > 6 * 3600:
        mp = {}
        for mkey, m in _thi_truong().items():
            r, e = _http("GET", f"{POS_API}/shops", {"api_key": m["api_key"]})
            for sh in (r or {}).get("shops") or []:
                if str(sh.get("id")) == str(m["shop_id"]):
                    for p in sh.get("pages") or []:
                        mp[str(p.get("id"))] = str(m["shop_id"])
        if mp:
            _SHOP_PAGE.update(luc=time.time(), map=mp)
    return _SHOP_PAGE["map"].get(str(page))


def canh_bao_sdt(st, convs, tok, that=True, in_ra=False):
    """Khách TỰ GÕ SĐT (Pancake bắt vào recent_phone_numbers) trùng đơn landing ≤7 ngày → ghi cảnh báo.
    Chỉ nhìn danh sách hội thoại, không mở tin."""
    theo_sdt = {}
    for d in _KHO["don"].values():
        theo_sdt.setdefault(d["sdt8"], []).append(d)
    ghi = 0
    for c in convs:
        cid = str(c.get("id"))
        sdts = {x[-8:] for x in _sdt_ds(c.get("recent_phone_numbers")) if len(x) >= 8}
        ds = [d for x in sdts for d in theo_sdt.get(x, [])
              if (d["khoa"] + "|" + cid) not in st["canh_bao"]
              and (st["da_ghi"].get(d["khoa"]) or {}).get("conv") != cid]
        if not ds:
            continue
        cau = _cau_canh_bao(ds)
        khach = (c.get("from") or {}).get("name") or "?"
        page = c.get("page_id")
        if not that:
            if in_ra:
                print(f"  ⚠ SẼ CẢNH BÁO · page {page} · {khach} · {cid}\n      {cau}")
        else:
            cust = ((c.get("customers") or [{}])[0] or {}).get("id")
            r2, e2 = _http("POST", f"{WEB_API}/pages/{page}/customers/{cust}/notes", {"access_token": tok},
                           {"message": cau, "conversation_id": cid, "images": "[]", "links": "[]"})
            if e2 or not r2 or r2.get("success") is False:
                _log(f"✖ cảnh báo hỏng {khach} ({cid}): {e2 or str(r2)[:120]}")
                continue
            _log(f"⚠ {', '.join('#' + str(d['id']) for d in ds)} ← khách tự gõ SĐT · {khach} · page {page}")
            for d in ds:
                st["canh_bao"][d["khoa"] + "|" + cid] = int(time.time())
            # LEN_DAU_2909 — đơn mới nhất cùng shop với page → SĐT đơn lên đầu hồ sơ để khung Đơn hàng hiện đơn
            cung = [d for d in ds if d["shop"] == _shop_cua_page(page)]
            if cung:
                d = max(cung, key=lambda x: x["luc"])
                ok, ly_do = them_sdt(page, cid, d["bill_sdt"])
                _log(("📱" if ok else "✖") + f" #{d['id']} (khách tự gõ SĐT): {ly_do} → khung Đơn hàng · {khach}")
        ghi += 1
        time.sleep(0.2)
    return ghi


# ───────────────────────── một lượt ─────────────────────────

def _nap():
    try:
        st = json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    st.setdefault("da_ghi", {})          # khoá đơn "shop:id" -> {conv, luc}
    st.setdefault("da_doc", {})          # conv_id -> updated_at đã đọc (khỏi đọc lại khi chưa có gì mới)
    st.setdefault("cho_gan", {})         # khoá đơn -> việc gắn đơn↔hội thoại đang chờ đơn qua xác nhận
    st.setdefault("kiem", {})            # khoá đơn -> chờ kiểm khung "Đơn hàng" đã nhận đơn chưa
    st.setdefault("ket_qua", [])         # kết quả kiểm (để báo chủ shop)
    st.setdefault("canh_bao", {})        # "khoá đơn|conv" -> lúc ghi cảnh báo khách tự gõ SĐT
    st.setdefault("ghi_in", {})          # khoá đơn -> lúc đã ghi 'Ghi chú in' CARE ĐƠN QUA MESS (GHI_CHU_IN_2509)
    if not st.get("ghi_in_b"):           # GHI_CHU_IN_B_2509 — xét lại 1 lần các đơn đã bỏ vì 'Đã gửi hàng'
        st["ghi_in"], st["ghi_in_b"] = {}, 1
    return st


def _luu(st):
    cu = time.time() - 3 * 86400
    st["da_ghi"] = {k: v for k, v in st["da_ghi"].items() if v.get("luc", 0) >= cu}
    st["da_doc"] = {k: v for k, v in st["da_doc"].items() if _giay(v) >= time.time() - CUA_SO_DON - 3600}
    st["ket_qua"] = st.get("ket_qua", [])[-300:]
    st["canh_bao"] = {k: v for k, v in st.get("canh_bao", {}).items() if v >= time.time() - CANH_BAO_NGAY - 86400}
    st["ghi_in"] = {k: v for k, v in st.get("ghi_in", {}).items() if v >= time.time() - 10 * 86400}  # GHI_CHU_IN_2509
    st["bao_huy"] = {k: v for k, v in st.get("bao_huy", {}).items()                                   # HUY_TRUNG_2909
                     if (v if isinstance(v, int) else v[0]) >= time.time() - 4 * 86400}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def mot_luot(that=True, gio=None, chi_page=None, in_ra=False):
    env = _env()
    tok = env.get("PANCAKE_USER_TOKEN", "")
    if not tok:
        return 0
    now = time.time()
    st = _nap() if that else {"da_ghi": {}, "da_doc": {}, "canh_bao": {}}
    if not gio and now < _NGHI["den"]:
        return 0
    if that:
        try:
            gan_don(st, in_ra)
            bu_sdt(st)
            kiem_hien(st, tok)
        except Exception as e:                           # noqa: BLE001 — bước gắn hỏng không chặn bước ghi chú
            _log(f"✖ bước gắn đơn lỗi: {e}")
        try:                                             # GHI_CHU_IN_2509 — ô 'Ghi chú in' đơn landing có Messenger
            ghi_chu_in(st)
        except Exception as e:                           # noqa: BLE001 — ghi chú in hỏng không chặn bước khớp
            _log(f"✖ bước ghi chú in lỗi: {e}")
        try:                                             # HUY_TRUNG_2909
            bao_huy_trung(st, tok)
        except Exception as e:                           # noqa: BLE001
            _log(f"✖ bước đính chính hủy trùng lỗi: {e}")
    if gio:
        moc = now - gio * 3600
    else:                                                # lần đầu: chỉ nhìn lại 5 phút
        moc = max(float(st.get("moc") or (now - 5 * 60)) - GOI_LAP, now - NHIN_LAI_TOI_DA)
    dons = [d for d in don_cho(now) if d["khoa"] not in st["da_ghi"]]
    if in_ra:
        print(f"  đơn landing 7 ngày: {len(_KHO['don'])} · chờ khớp 24 giờ ({len(dons)}): "
              + ", ".join(f"#{d['id']} {d['mkey']}" for d in dons[:30]))
    if not _KHO["don"]:
        if that:
            st["moc"] = now
            _luu(st)
        return 0
    convs, du = hoi_thoai_tu(moc, tok, chi_page)
    try:
        canh_bao_sdt(st, convs, tok, that, in_ra)
    except Exception as e:                               # noqa: BLE001 — cảnh báo hỏng không chặn bước khớp
        _log(f"✖ bước cảnh báo SĐT lỗi: {e}")
    ngo = [c for c in convs if st["da_doc"].get(str(c.get("id"))) != c.get("updated_at") and _dang_ngo(c, dons)]
    if in_ra:
        print(f"  hội thoại đổi từ mốc: {len(convs)} · đáng mở đọc: {len(ngo)}")
    ghi = 0
    for c in ngo[:DOC_TOI_DA]:
        cid = str(c.get("id"))
        res, err = doc_tin(c, tok)
        if err or not isinstance((res or {}).get("messages"), list):
            continue
        if _giay(c.get("updated_at")) < now:
            # Đổi SAU lúc lấy danh sách đơn thì đơn của nó có thể chưa nằm trong `dons` → đừng đánh
            # dấu đã đọc, lượt sau (mốc = now) đọc lại.
            st["da_doc"][cid] = c.get("updated_at")
        ds = [d for d in khop(c, res["messages"], dons, res.get("activities")) if d["khoa"] not in st["da_ghi"]]
        if not ds:
            continue
        # Ghi chú đã có số đơn (lượt trước ghi rồi mà sổ mất) → chỉ ghi sổ
        cu = " ".join(str(n.get("message") or "") for n in (res.get("notes") or []) if isinstance(n, dict))
        ds_moi = [d for d in ds if f"#{d['id']}" not in cu]
        khach = (c.get("from") or {}).get("name") or "?"
        page = c.get("page_id")
        if ds_moi:
            cau = _cau_ghi_chu(ds_moi)
            if not that:
                print(f"  📝 SẼ GHI · page {page} · {khach} · {cid}\n      {cau}")
            else:
                cust = ((c.get("customers") or [{}])[0] or {}).get("id")
                r2, e2 = _http("POST", f"{WEB_API}/pages/{page}/customers/{cust}/notes", {"access_token": tok},
                               {"message": cau, "conversation_id": cid, "images": "[]", "links": "[]"})
                if e2 or not r2 or r2.get("success") is False:
                    _log(f"✖ ghi chú hỏng {khach} ({cid}): {e2 or str(r2)[:120]}")
                    st["da_doc"].pop(cid, None)          # lượt sau đọc + ghi lại
                    continue
                _log(f"📝 {', '.join('#' + str(d['id']) for d in ds_moi)} → hội thoại {khach} · page {page}")
            ghi += 1
        cust_chat = ((c.get("customers") or [{}])[0] or {}).get("id")
        for d in ds:
            viec = {"mkey": d["mkey"], "id": d["id"], "conv": cid, "page": str(page), "ten_fb": khach,
                    "cust_chat": cust_chat, "luc": int(now)}
            if that:
                ok, ly_do = them_sdt(page, cid, d["bill_sdt"])
                _log(("📱" if ok else "✖") + f" #{d['id']}: {ly_do} → khung Đơn hàng · {khach}")
                st["da_ghi"][d["khoa"]] = dict(viec, gan=1, sdt=1 if ok else "loi")
                st["cho_gan"][d["khoa"]] = viec
                if ok and cust_chat:
                    st["kiem"][d["khoa"]] = dict(viec, khach_pos=d.get("khach_pos"), lan=0, sau=int(now) + 60)
            elif in_ra:
                print(f"      → thêm SĐT {d['bill_sdt']} vào hồ sơ khách (khung Đơn hàng) + link hội thoại vào đơn khi qua xác nhận")
        time.sleep(0.2)
    if that:
        if du:
            st["moc"] = now
        _luu(st)
    return ghi


# ───────────────────────── chạy nền trong daemon ─────────────────────────

_LUONG = None


def _vong_nen():
    while True:
        t = time.time()
        try:
            if _env().get("LANDING_VAO_CHAT", "1") != "0":
                mot_luot(that=True)
        except Exception as e:                           # noqa: BLE001 — lỗi một lượt không được giết luồng
            _log(f"✖ lượt lỗi: {e}")
        time.sleep(max(5, CHU_KY - (time.time() - t)))


def chay_nen():
    """Bật luồng nền (1 lần/tiến trình). Gọi từ auto_len_don.daemon()."""
    global _LUONG
    if _LUONG and _LUONG.is_alive():
        return
    _LUONG = threading.Thread(target=_vong_nen, name="landing_vao_chat", daemon=True)
    _LUONG.start()
    _log(f"🚀 luồng ghi số đơn landing vào hội thoại — {CHU_KY}s/lượt (tắt: LANDING_VAO_CHAT=0)")


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("thu", "mot"):
        print(__doc__)
        return
    gio = float(a[a.index("--gio") + 1]) if "--gio" in a else None
    page = a[a.index("--page") + 1] if "--page" in a else None
    n = mot_luot(that=(a[0] == "mot"), gio=gio, chi_page=page, in_ra=True)
    print(f"\n{'Đã ghi' if a[0] == 'mot' else 'Sẽ ghi'} {n} hội thoại.")


if __name__ == "__main__":
    main()

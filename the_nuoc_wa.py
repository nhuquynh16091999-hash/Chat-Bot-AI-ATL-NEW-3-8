#!/usr/bin/env python3
"""Tự gắn thẻ TÊN NƯỚC (SAUDI, UAE…) cho hội thoại mới trên các kênh WhatsApp nối Pancake.

Chủ shop 28/09/2026: *"tự động gắn thẻ tên nước khi data nhảy tới"* (kênh Xophia +84 357 407 840).

Cách đoán nước — CHỈ theo đơn vị tiền tệ trong tin khách gửi tới (chủ shop 28/09: "khoan không đoán nước
theo cách đó [đầu số], mà đoán nước theo đơn vị tiền tệ gửi tới"):
  SAR → SAUDI · AED → UAE · KWD/KD → KUWAIT · QAR/QR → QATAR · OMR → OMAN · BHD/BD → BAHRAIN.
Tin landing "Total: Buy 1 : 119 SAR…" là nguồn chính. Không thấy mã tiền → không gắn, đợi tin mới.
Đọc tin làm Pancake lật hội thoại thành ĐÃ XEM → hội thoại đang chưa đọc thì đọc xong đánh lại CHƯA ĐỌC.
Hội thoại đã có một thẻ nước thì bỏ qua. Thẻ phải có sẵn trên page — máy không tự tạo thẻ,
thiếu thẻ thì ghi log một lần.

PHẦN 2 — ĐÁNH DẤU ĐƠN ĐÃ XÁC NHẬN QUA WHATSAPP (chủ shop 28/09: "có cách nào để biết đơn nào dc xác nhận
qua whatsapp rồi không" → chọn THẺ ĐƠN POS). Khách có tin trên kênh WA → lấy SĐT (số WA + dòng "Phone:" trong
tin Order confirmation) → dò POS 6 nước vùng Vịnh → đơn landing (không conversation_id, chưa huỷ) tạo trong 48 giờ
trước tin khách → thêm thẻ đơn THE_XN (giữ nguyên thẻ cũ). Shop chưa có thẻ này → log 1 lần, không tự tạo
(thẻ tạo bằng API POS KHÔNG gắn được lên đơn — đo 28/09 id 71; chủ shop tạo tay id 72 thì được).

PHẦN 3 — ĐƠN XÁC NHẬN QUA MESSENGER (chủ shop 28/09: "có làm được những đơn xác nhận qua mess từ landing page như thế k").
Nguồn = sổ `ghi_in` của landing_vao_chat (đơn landing đã khớp hội thoại Messenger: tin Botcake/mã landing hoặc khách tự gõ SĐT
trùng đơn — đúng những đơn được ghi "CARE ĐƠN QUA MESS" vào Ghi chú in) → thêm thẻ đơn THE_MESS. Tối đa MESS_MOI_LUOT đơn/lượt.

PHẦN 4 — THẺ HỘI THOẠI "WA LADIPAGE" (chủ shop 28/09: "mỗi lần khách xác nhận đơn ở ladi thì b auto gắn thẻ 2 là WA LADIPAGE
+ kèm tên nước"). Hội thoại WA được gắn THE_LADI khi tin khách là tin xác nhận đơn landing (R_XN_LADI) HOẶC SĐT khớp một đơn
landing trong POS (phần 2). Thẻ nước vẫn theo mã tiền (phần 1).

PHẦN 5 — HỘI THOẠI MESSENGER CỦA ĐƠN LANDING (chủ shop 28/09: "các đơn ladi xác nhận qua mess, có đơn hàng là gắn thẻ LADI PAGE
+ kèm tên nước"; sau đổi tên thẻ thành MESS LADI). Nguồn = sổ landing_vao_chat (da_ghi: tin Botcake/mã landing; canh_bao: khách tự gõ SĐT trùng đơn) → hội thoại
+ đơn. Đơn còn sống (không huỷ/xoá) → gắn THE_LADI_MESS + thẻ nước THEO SHOP CỦA ĐƠN (shop Saudi → SAUDI…). Chỉ làm trên page
đã có thẻ THE_LADI_MESS (page trạm landing — chủ shop tạo). Page thiếu thẻ nước → máy tự thêm thẻ nước vào settings page.

Chạy: python3 the_nuoc_wa.py [--xem]   (--xem = chỉ in, không gắn). Timer 1 phút trên VPS.
"""
import os
import re
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import care_don_wa as C  # noqa: E402  (http_json, kenh_wa, _env, WEB_API)

NUOC = ["SAUDI", "UAE", "KUWAIT", "QATAR", "OMAN", "BAHRAIN"]
TIEN = [  # mã tiền đứng sát con số → thẻ
    (r"SAR|ر\.?\s?س|ريال\s*سعودي", "SAUDI"),
    (r"AED|Dhs?|د\.?\s?إ|درهم", "UAE"),
    (r"KWD|KD|د\.?\s?ك|دينار\s*كويتي", "KUWAIT"),
    (r"QAR|QR|ر\.?\s?ق|ريال\s*قطري", "QATAR"),
    (r"OMR|ر\.?\s?ع|ريال\s*عماني", "OMAN"),
    (r"BHD|BD|د\.?\s?ب|دينار\s*بحريني", "BAHRAIN"),
]
SO_DO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "the_nuoc_wa.json")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "the_nuoc_wa.log")
XEM = "--xem" in sys.argv
THE_XN = "XN QUA WA"
THE_MESS = "XN QUA MESS"
THE_LADI = "WA LADIPAGE"
THE_DA_GUI = "ĐÃ GỬI"          # 28/09 chủ shop: "những đơn đã mua của mess ladi, có đơn hàng rồi thì gắn thêm thẻ đã gửi"
THE_LADI_MESS = "MESS LADI"   # 28/09 chủ shop đổi tên thẻ "LADI PAGE" → "MESS LADI" (cùng id)
MAU_NUOC = {"SAUDI": "#52c41a", "UAE": "#1890ff", "KUWAIT": "#fa8c16", "QATAR": "#722ed1", "OMAN": "#eb2f96", "BAHRAIN": "#13c2c2"}
R_XN_LADI = re.compile(r"order\s*confirmation|confirm\s+my\s+order|xác\s*nhận\s*đơn|تأكيد\s*(?:ال)?طلب", re.I)
SO_LVC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "chung", "landing_vao_chat.json")
MESS_MOI_LUOT = 30
SHOP_VINH = ["saudi", "uae", "kuwait", "qatar", "oman", "bahrain", "romania", "bulgaria"]  # XN_KHACH_2909: + shop Âu chạy landing
XN_LUI = 48 * 3600          # đơn tạo tối đa 48 giờ trước tin khách
XN_TOI = 15 * 60            # … hoặc tối đa 15 phút sau (đồng hồ lệch, khách nhắn trước khi POS ghi xong)
TT_BO = {6, 7}              # đơn đã huỷ / đã xoá thì thôi


def _don_chat(o):
    """DON_CHAT_2909: đơn máy lên đơn tạo từ hội thoại (page trạm khác shop, không gắn page) — KHÔNG phải landing."""
    return (o.get("note") or "").lstrip().startswith("[Tự động] Từ hội thoại")


def ghi(s):
    dong = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {s}"
    print(dong)
    if not XEM:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(dong + "\n")


def post(url, params, body):
    import urllib.parse, urllib.request, urllib.error
    rq = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                data=urllib.parse.urlencode(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(rq, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8") or "{}")
        return d, (None if d.get("success", True) else str(d)[:150])
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:120]


def nuoc_tu_chu(chu):
    """Thẻ nước theo mã tiền đứng sát một con số ("119 SAR", "SAR 119", "119SAR")."""
    for mau, the in TIEN:
        if re.search(rf"\d[\d.,]*\s*(?:{mau})(?![A-Za-z])|(?<![A-Za-z])(?:{mau})\s*\d", chu or "", re.I):
            return the
    return None


def tin_khach(tok, pid, c):
    """Chữ các tin KHÁCH gửi (bỏ tin page / nhân viên). None = đọc hỏng."""
    cu = ((c.get("customers") or [{}])[0] or {}).get("id")
    if not cu:
        return None
    res, err = C.http_json(f"{C.WEB_API}/pages/{pid}/conversations/{c['id']}/messages",
                           {"access_token": tok, "customer_id": cu, "user_view": "true", "is_new_api": "true"})
    if err:
        return None
    return [m.get("original_message") or m.get("message") or "" for m in (res or {}).get("messages") or []
            if str((m.get("from") or {}).get("id")) != str(pid)]


def nuoc_tu_tin(ds):
    for chu in ds or []:
        the = nuoc_tu_chu(chu)
        if the:
            return the
    return None


def _gio(s):
    import datetime
    try:
        return datetime.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=datetime.timezone.utc).timestamp()
    except Exception:
        return None


def pos(m, v, path, body=None, params=None):
    import urllib.parse, urllib.request, urllib.error
    u = f"{C.POS_API}/shops/{v['shop_id']}{path}?" + urllib.parse.urlencode(dict(params or {}, api_key=v["api_key"]))
    rq = urllib.request.Request(u, data=json.dumps(body).encode() if body is not None else None,
                                method=m, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=60) as r:
            return json.loads(r.read().decode("utf-8") or "{}"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:120]


_THE_ID = {}


def the_xn_id(k, v, so, ten=THE_XN):
    if (k, ten) not in _THE_ID:
        d, e = pos("GET", v, "/orders/tags")
        _THE_ID[(k, ten)] = next((t["id"] for t in (d or {}).get("data") or []
                                  if str(t.get("name") or "").strip().upper() == ten), None) if not e else "loi"
        nhan = f"pos:{k}" if ten == THE_XN else f"pos:{k}:{ten}"
        if _THE_ID[(k, ten)] is None and nhan not in so["thieu_the"]:
            so["thieu_the"].append(nhan)
            ghi(f"🏷 POS {k} chưa có thẻ đơn '{ten}' — tạo TAY trên POS (nhóm tuỳ ý) thì máy tự gắn")
    v2 = _THE_ID[(k, ten)]
    return None if v2 == "loi" else v2


def danh_dau_don_mess(so, mk):
    """Thẻ THE_MESS cho đơn landing mà landing_vao_chat đã khớp hội thoại Messenger (sổ ghi_in)."""
    try:
        lvc = json.load(open(SO_LVC, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        ghi(f"⚠️ không đọc được sổ landing_vao_chat: {str(e)[:80]}")
        return
    shop = {str(v.get("shop_id")): k for k, v in mk.items() if isinstance(v, dict) and v.get("shop_id")}
    lam = 0
    for khoa in sorted(lvc.get("ghi_in") or {}, key=lambda x: -(lvc["ghi_in"][x] or 0)):
        if khoa in so["don_mess"] or lam >= MESS_MOI_LUOT:
            continue
        sid, oid = khoa.split(":", 1)
        k = shop.get(sid)
        v = mk.get(k) or {}
        if not v.get("api_key"):
            continue
        tid = the_xn_id(k, v, so, THE_MESS)
        if tid is None:
            continue
        lam += 1
        d, e = pos("GET", v, f"/orders/{oid}")
        o = (d or {}).get("data") or {}
        if e or not o:
            continue
        cu = [t.get("id") for t in o.get("tags") or [] if isinstance(t, dict)]
        if o.get("status") in TT_BO or tid in cu or _don_chat(o):
            so["don_mess"][khoa] = int(time.time())
            continue
        if XEM:
            ghi(f"[XEM] đơn {k} #{oid} ({o.get('bill_full_name')}) → thẻ {THE_MESS}")
            continue
        pos("PUT", v, f"/orders/{oid}", body={"tags": cu + [tid]})
        d2, _ = pos("GET", v, f"/orders/{oid}")
        co = tid in [t.get("id") for t in ((d2 or {}).get("data") or {}).get("tags") or []]
        ghi(f"{'✅' if co else '✖ hỏng (POS không lưu thẻ)'} thẻ {THE_MESS} đơn {k} #{oid} ({o.get('bill_full_name')})")
        if co:
            so["don_mess"][khoa] = int(time.time())


def danh_dau_don_xn(c, ds, so, mk):
    """Gắn thẻ THE_XN cho đơn landing khớp SĐT khách trong hội thoại WA c."""
    so_dt = set()
    wa = re.sub(r"\D", "", str((c.get("from") or {}).get("id") or ""))
    if len(wa) >= 9:
        so_dt.add(wa[-9:])
    for chu in ds or []:
        for m in re.finditer(r"(?:phone|số\s*điện\s*thoại|الهاتف|رقم\s*الجوال)\s*[:：]\s*([+\d][\d \-]{6,})", chu, re.I):
            d = re.sub(r"\D", "", m.group(1))
            if len(d) >= 8:
                so_dt.add(d[-9:])
    luc = _gio(c.get("last_customer_interactive_at")) or _gio(c.get("updated_at"))
    if not so_dt or not luc:
        return False
    thay = False
    for k in SHOP_VINH:
        v = mk.get(k) or {}
        if not v.get("api_key"):
            continue
        for sdt in so_dt:
            d, e = pos("GET", v, "/orders", params={"search": sdt, "page_size": 30})
            if e:
                ghi(f"⚠️ POS {k} dò {sdt}: {e}")
                continue
            for o in (d or {}).get("data") or []:
                t0 = _gio(o.get("inserted_at"))
                if (o.get("conversation_id") or o.get("status") in TT_BO or not t0 or _don_chat(o)
                        or re.search(r"\btest\b", str(o.get("bill_full_name") or ""), re.I)
                        or not (luc - XN_LUI <= t0 <= luc + XN_TOI)
                        or re.sub(r"\D", "", str(o.get("bill_phone_number") or ""))[-9:] != sdt):
                    continue
                thay = True
                khoa = f"{k}:{o['id']}"
                cu = [t.get("id") for t in o.get("tags") or [] if isinstance(t, dict)]
                tid = the_xn_id(k, v, so)
                if khoa in so["don_xn"] or tid is None or tid in cu:
                    continue
                if XEM:
                    ghi(f"[XEM] đơn {k} #{o['id']} ({o.get('bill_full_name')}, {sdt}) → thẻ {THE_XN}")
                    continue
                r, e2 = pos("PUT", v, f"/orders/{o['id']}", body={"tags": cu + [tid]})
                d2, _ = pos("GET", v, f"/orders/{o['id']}")
                co = tid in [t.get("id") for t in ((d2 or {}).get("data") or {}).get("tags") or []]
                ghi(f"{'✅' if co else '✖ hỏng ' + str(e2 or 'POS không lưu thẻ')} thẻ {THE_XN} đơn {k} #{o['id']} "
                    f"({o.get('bill_full_name')}, {sdt})")
                if co:
                    so["don_xn"][khoa] = int(time.time())
    return thay


def tra_chua_doc(tok, pid, cid):
    """Đánh lại CHƯA ĐỌC, đọc lại cờ seen cho chắc (Pancake hay lật trễ vài giây)."""
    for _ in range(3):
        post(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/mark_unread", {"access_token": tok}, {})
        time.sleep(3)
        res, _e = C.http_json(f"{C.WEB_API}/pages/{pid}/conversations", {"access_token": tok})
        c = next((x for x in (res or {}).get("conversations") or [] if x.get("id") == cid), None)
        if c is None or not c.get("seen"):
            return
    ghi(f"⚠️ {cid}: đánh lại chưa đọc 3 lần vẫn bị lật đã xem")


def _the_page(tok, pid):
    res, err = C.http_json(f"https://pages.fm/api/v1/pages/{pid}/settings", {"access_token": tok})
    st = (res or {}).get("settings") or res or {}
    import unicodedata
    return st, {unicodedata.normalize("NFC", str(t.get("text") or "").strip().upper()): t.get("id")
                for t in st.get("tags") or []}, err


def _them_the_nuoc(tok, pid, ten, so):
    """Thêm thẻ nước vào settings page (GET ngay trước POST, gửi KHÔNG id — Pancake tự cấp). → id hoặc None."""
    st, ids, err = _the_page(tok, pid)
    if err or not st.get("current_settings_key"):
        return None
    if ten in ids:
        return ids[ten]
    mau = MAU_NUOC.get(ten, "#1890ff")
    tags = list(st.get("tags") or []) + [{"text": ten, "color": mau, "lighten_color": mau, "is_lead_event": False}]
    if XEM:
        ghi(f"[XEM] page {pid} sẽ thêm thẻ {ten}")
        return None
    body = json.dumps({"changes": json.dumps({"tags": tags}), "current_settings_key": st["current_settings_key"]}).encode()
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{C.WEB_API}/pages/{pid}/settings?access_token={tok}", data=body, method="POST",
            headers={"Content-Type": "application/json"}), timeout=40).read()
    except Exception as e:  # noqa: BLE001
        ghi(f"✖ page {pid} thêm thẻ {ten} hỏng: {str(e)[:80]}")
        return None
    time.sleep(3.5)
    _st, ids, _e = _the_page(tok, pid)
    ghi(f"{'🏷 thêm' if ten in ids else '✖ không thấy sau khi thêm'} thẻ {ten} trên page {pid}")
    return ids.get(ten)


def danh_dau_hoi_thoai_mess(tok, so, mk):
    try:
        lvc = json.load(open(SO_LVC, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    shop = {str(v.get("shop_id")): k for k, v in mk.items() if isinstance(v, dict) and v.get("shop_id")}
    cap = {}
    for k, v in (lvc.get("da_ghi") or {}).items():
        if v.get("conv"):
            cap.setdefault(v["conv"], k)
    for k in lvc.get("canh_bao") or {}:
        don, conv = k.split("|", 1)
        cap.setdefault(conv, don)
    trang = {}
    lam = 0
    for conv, don in cap.items():
        cu = so["hoi_thoai_mess"].get(conv)
        bu_da_gui = isinstance(cu, int) and conv not in so["da_gui_mess"]      # ca gắn trước 28/09 chiều → bù thẻ Đã gửi
        if lam >= MESS_MOI_LUOT or (cu is not None and not bu_da_gui
                                    and not (isinstance(cu, list) and time.time() - cu[1] > 6 * 3600)):
            continue                                  # page chưa có thẻ LADI PAGE → 6 giờ xem lại một lần
        pid = conv.split("_", 1)[0]
        if pid not in trang:
            _st, ids, err = _the_page(tok, pid)
            trang[pid] = None if err else ids
        ids = trang[pid]
        if ids is None:
            continue
        if THE_LADI_MESS not in ids:
            so["hoi_thoai_mess"][conv] = ["page không có thẻ " + THE_LADI_MESS, int(time.time())]
            continue
        sid, oid = don.split(":", 1)
        k = shop.get(sid)
        v = mk.get(k) or {}
        if not v.get("api_key"):
            continue
        lam += 1
        d, e = pos("GET", v, f"/orders/{oid}")
        o = (d or {}).get("data") or {}
        if e or not o:
            continue
        if _don_chat(o):
            so["hoi_thoai_mess"][conv] = f"đơn {k} #{oid} là đơn chat, không phải landing"
            so["da_gui_mess"][conv] = "đơn chat"
            continue
        if o.get("status") in TT_BO:
            if not bu_da_gui:
                so["hoi_thoai_mess"][conv] = f"đơn {k} #{oid} đã huỷ"
            else:
                so["da_gui_mess"][conv] = "đơn huỷ"
            continue
        nuoc = k.upper()
        if nuoc not in ids:
            tid = _them_the_nuoc(tok, pid, nuoc, so)
            if tid is None:
                continue
            ids[nuoc] = tid
        if XEM:
            ghi(f"[XEM] hội thoại {conv} (đơn {k} #{oid}, {o.get('bill_full_name')}) → {THE_LADI_MESS} + {nuoc}")
            continue
        loi = []
        gan = [THE_LADI_MESS, nuoc]
        if THE_DA_GUI in ids:
            gan.append(THE_DA_GUI)
        elif f"{pid}:{THE_DA_GUI}" not in so["thieu_the"]:
            so["thieu_the"].append(f"{pid}:{THE_DA_GUI}")
            ghi(f"🏷 page {pid} chưa có thẻ 'Đã gửi' — không gắn được thẻ này")
        for ten in gan:
            r, e2 = post(f"{C.WEB_API}/pages/{pid}/conversations/{conv}/toggle_tag",
                         {"access_token": tok}, {"tag_id": ids[ten], "value": 1})
            if e2:
                loi.append(f"{ten}: {e2}")
        ghi(f"{'✖ hỏng ' + '; '.join(loi) if loi else '✅'} gắn {' + '.join(gan)} hội thoại {conv} "
            f"(đơn {k} #{oid}, {o.get('bill_full_name')})")
        if not loi:
            so["hoi_thoai_mess"][conv] = int(time.time())
            if THE_DA_GUI in gan:
                so["da_gui_mess"][conv] = int(time.time())


# CHUYEN_THE_2909 — ca Abdul haque Haque: thẻ XN QUA WA gắn #78086 lúc 07:53 (đơn còn Mới), 20 phút sau don_landing HỦY #78086 vì
# trùng #77446 (đơn đang đi) → thẻ nằm trên đơn hủy. Đơn đã gắn thẻ XN mà bị MÁY hủy trùng → chuyển thẻ sang đơn được giữ (số đơn
# trong ghi chú hủy), gỡ khỏi đơn hủy. Đơn hủy tay (không có ghi chú hủy trùng) thì để nguyên.
R_HUY_TRUNG = re.compile(r"ĐÃ HỦY \(TRÙNG\)[^#]*#(\d+)")
CHUYEN_MOI_LUOT = 15


def _the_don(o):
    return [t.get("id") for t in o.get("tags") or [] if isinstance(t, dict)]


def chuyen_the_huy(so, mk):
    xong = so.setdefault("chuyen_the", {})         # "nước:đơn:thẻ" -> lúc xong | [lúc xét] (chưa hủy, 30 phút xem lại)
    shop = {str(v.get("shop_id")): k for k, v in mk.items() if isinstance(v, dict) and v.get("shop_id")}
    viec = [(k.partition(":")[0], k.partition(":")[2], THE_XN, luc) for k, luc in so["don_xn"].items()]
    viec += [(shop.get(k.partition(":")[0]), k.partition(":")[2], THE_MESS, luc) for k, luc in so["don_mess"].items()]
    now, lam = time.time(), 0
    for m, oid, ten, luc in viec:
        khoa = f"{m}:{oid}:{ten}"
        x = xong.get(khoa)
        if (not m or isinstance(x, int) or not isinstance(luc, (int, float)) or now - luc > 4 * 86400
                or lam >= CHUYEN_MOI_LUOT or (isinstance(x, list) and now - x[0] < 1800)):
            continue
        v = mk.get(m) or {}
        if not v.get("api_key"):
            continue
        tid = the_xn_id(m, v, so, ten)
        if tid is None:
            continue
        lam += 1
        d, e = pos("GET", v, f"/orders/{oid}")
        o = (d or {}).get("data") or {}
        if e or not o:
            continue
        if o.get("status") not in TT_BO:
            xong[khoa] = [int(now)]
            continue
        mm = R_HUY_TRUNG.search(o.get("note") or "")
        if tid not in _the_don(o) or not mm:
            xong[khoa] = int(now)                    # thẻ đã gỡ / hủy tay → để nguyên
            continue
        gid = mm.group(1)
        d2, e2 = pos("GET", v, f"/orders/{gid}")
        g = (d2 or {}).get("data") or {}
        if e2 or not g:
            continue
        if g.get("status") in TT_BO:
            xong[khoa] = int(now)
            ghi(f"ℹ️ đơn {m} #{oid} hủy trùng #{gid} nhưng #{gid} cũng đã hủy — thẻ {ten} để nguyên")
            continue
        if XEM:
            ghi(f"[XEM] chuyển thẻ {ten}: đơn hủy {m} #{oid} → đơn được giữ #{gid} ({g.get('bill_full_name')})")
            continue
        if tid not in _the_don(g):
            pos("PUT", v, f"/orders/{gid}", body={"tags": _the_don(g) + [tid]})
        pos("PUT", v, f"/orders/{oid}", body={"tags": [t for t in _the_don(o) if t != tid]})
        g2 = ((pos("GET", v, f"/orders/{gid}")[0] or {}).get("data") or {})
        o2 = ((pos("GET", v, f"/orders/{oid}")[0] or {}).get("data") or {})
        co, bo = tid in _the_don(g2), tid not in _the_don(o2)
        ghi(f"{'✅' if co and bo else '✖ hỏng'} chuyển thẻ {ten}: đơn hủy {m} #{oid} → đơn được giữ #{gid} "
            f"({g.get('bill_full_name')}){'' if co else ' — CHƯA gắn được đơn giữ'}{'' if bo else ' — CHƯA gỡ được đơn hủy'}")
        if co and bo:
            xong[khoa] = int(now)
    for k in [k for k, x in xong.items() if (x if isinstance(x, int) else x[0]) < now - 6 * 86400]:
        xong.pop(k)


def main():
    tok = C._env().get("PANCAKE_USER_TOKEN") or ""
    kenh, err = C.kenh_wa(tok)
    if err or not kenh:
        ghi(f"⚠️ không lấy được kênh WhatsApp: {err or 'danh sách rỗng'}")
        return 1
    try:
        so = json.load(open(SO_DO, encoding="utf-8"))
    except Exception:
        so = {}
    for k, d in (("thieu_the", []), ("khong_ro", {}), ("xn", {}), ("don_xn", {}), ("don_mess", {}), ("khong_ladi", {}), ("hoi_thoai_mess", {}), ("da_gui_mess", {})):
        so.setdefault(k, d)
    mk = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "markets.json"), encoding="utf-8"))
    for so_wa, pid in kenh.items():
        res, err = C.http_json(f"{C.WEB_API}/pages/{pid}/settings", {"access_token": tok})
        st = (res or {}).get("settings") or res or {}
        the_id = {str(t.get("text") or "").strip().upper(): t.get("id") for t in st.get("tags") or []}
        id_nuoc = {the_id[v] for v in NUOC if v in the_id}
        res, err = C.http_json(f"{C.WEB_API}/pages/{pid}/conversations", {"access_token": tok})
        if err:
            ghi(f"⚠️ {pid}: đọc hội thoại hỏng {err}")
            continue
        for c in (res or {}).get("conversations") or []:
            can_nuoc = not (set(c.get("tags") or []) & id_nuoc) and so["khong_ro"].get(c["id"]) != c.get("updated_at")
            can_xn = (so["xn"].get(c["id"]) != c.get("updated_at") and c.get("last_customer_interactive_at")
                      and (_gio(c["last_customer_interactive_at"]) or 0) > time.time() - XN_LUI)
            can_ladi = (THE_LADI in the_id and the_id[THE_LADI] not in (c.get("tags") or [])
                        and so["khong_ladi"].get(c["id"]) != c.get("updated_at"))
            if not can_nuoc and not can_xn and not can_ladi:
                continue
            sdt = re.sub(r"\D", "", str((c.get("from") or {}).get("id") or c["id"].rsplit("_", 1)[-1]))
            ds = tin_khach(tok, pid, c)
            if not c.get("seen") and not XEM:
                tra_chua_doc(tok, pid, c["id"])       # đọc tin vừa lật thành đã xem → trả lại
            if ds is None:
                continue                              # đọc hỏng → lượt sau thử lại
            khop_don = False
            if can_xn:
                khop_don = danh_dau_don_xn(c, ds, so, mk)
                if not XEM:
                    so["xn"][c["id"]] = c.get("updated_at")
            if can_ladi:
                if khop_don or any(R_XN_LADI.search(x or "") for x in ds):
                    ly = "đơn landing POS" if khop_don else "tin xác nhận landing"
                    if XEM:
                        ghi(f"[XEM] +{sdt} → {THE_LADI} ({ly})")
                    else:
                        r, e = post(f"{C.WEB_API}/pages/{pid}/conversations/{c['id']}/toggle_tag",
                                    {"access_token": tok}, {"tag_id": the_id[THE_LADI], "value": 1})
                        ghi(f"{'✖ hỏng ' + str(e) if e else '✅'} gắn {THE_LADI} cho +{sdt} ({ly}) kênh +{so_wa}")
                else:
                    so["khong_ladi"][c["id"]] = c.get("updated_at")
            if not can_nuoc:
                continue
            the, cach = nuoc_tu_tin(ds), "mã tiền"
            if not the:
                so["khong_ro"][c["id"]] = c.get("updated_at")
                continue
            if the not in the_id:
                if f"{pid}:{the}" not in so["thieu_the"]:
                    so["thieu_the"].append(f"{pid}:{the}")
                    ghi(f"🏷 kênh +{so_wa} chưa có thẻ '{the}' — tạo thẻ tên này trên Pancake thì máy tự gắn")
                continue
            if XEM:
                ghi(f"[XEM] +{sdt} → {the} ({cach})")
                continue
            r, e = post(f"{C.WEB_API}/pages/{pid}/conversations/{c['id']}/toggle_tag",
                               {"access_token": tok}, {"tag_id": the_id[the], "value": 1})
            ghi(f"{'✖ hỏng ' + str(e) if e else '✅'} gắn {the} cho +{sdt} ({cach}) kênh +{so_wa}")
            so["khong_ro"].pop(c["id"], None)
    danh_dau_don_mess(so, mk)
    danh_dau_hoi_thoai_mess(tok, so, mk)
    try:
        chuyen_the_huy(so, mk)                     # CHUYEN_THE_2909
    except Exception as e:  # noqa: BLE001
        ghi(f"⚠️ chuyển thẻ đơn hủy trùng lỗi: {str(e)[:120]}")
    for k in list(so["xn"]):
        if len(so["xn"]) <= 3000:
            break
        so["xn"].pop(k)
    if not XEM:
        json.dump(so, open(SO_DO, "w", encoding="utf-8"), ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

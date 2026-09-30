#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tải KỊCH BẢN ("Trả lời nhanh") của từng page về máy — nguồn kịch bản duy nhất của AI Sale.

Đây là thứ mục 12.1 trong LUAT_AI_SALE.md ghi là "CHẶN, API không đọc được".
Đã tìm ra ngày 2026-09-03: endpoint nằm ở host **pancake.vn** (giao diện web), không phải
pages.fm (Open API) — nên đợt dò 28/8 chỉ quét pages.fm mới trượt:

    GET https://pancake.vn/api/v1/pages/{page_id}/settings
        ?access_token=<PANCAKE_USER_TOKEN>&load_quick_replies_only=true&client_version=0

  · Dùng **user token** (PANCAKE_USER_TOKEN trong .env), KHÔNG phải page token
    -> lấy được kịch bản cả những page đang hỏng page-token.
  · `client_version` là số phiên bản kịch bản client đang giữ. Gửi đúng số hiện hành,
    API trả {"data": "data_up_to_date"} cho nhẹ; **gửi 0 thì trả toàn bộ nội dung**.
  · Trả về: quick_replies[] (mỗi mẫu: keyword + nhiều messages + ảnh) và quick_reply_topics[].

Lệnh:
  python3 kich_ban.py tai <thị trường>          # tải kịch bản mọi page -> state/<tt>/kich_ban.json
  python3 kich_ban.py xem <thị trường> <page>   # in kịch bản 1 page (page_id hoặc 1 phần tên)
  python3 kich_ban.py thieu <thị trường>        # page nào chưa có kịch bản / kịch bản rỗng
  python3 kich_ban.py dongbo <thị trường>       # chỉ tải lại page nào vừa sửa trên Pancake

`ai_sale.py chay/du_bao` TỰ gọi dongbo ở đầu mỗi vòng, nên sửa "Trả lời nhanh" trên Pancake
xong là vòng sau dùng ngay. Tắt bằng cờ --khong-dong-bo nếu cần chạy nhanh.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import quet_hoi_thoai as qht

WEB_API = "https://pancake.vn/api/v1"


def _state(mkey, ten_file):
    return os.path.join(SCRIPT_DIR, "state", mkey, ten_file)


def _pages(mkey):
    """{page_id: {name, token?}} — đọc từ page_tokens.json của thị trường."""
    f = _state(mkey, "page_tokens.json")
    if not os.path.exists(f):
        sys.exit(f"❌ Thị trường {mkey!r} chưa setup. Chạy: python3 auto_len_don.py setup {mkey}")
    return json.load(open(f, encoding="utf-8"))


def tai_1_page(page_id, user_token):
    """Trả (dict kịch bản, lỗi). Kịch bản: {'mau': [...], 'chu_de': [...], 'phien_ban': int}."""
    u = f"{WEB_API}/pages/{page_id}/settings?" + urllib.parse.urlencode({
        "access_token": user_token,
        "load_quick_replies_only": "true",
        "client_version": "0",          # 0 = bắt API trả toàn bộ nội dung
    })
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode() or "{}")
    except Exception as e:
        return None, str(e)
    if not res.get("success"):
        return None, f"API trả success=false: {str(res)[:120]}"
    qr = (res.get("quick_replies") or {})
    data = qr.get("data")
    if not isinstance(data, dict):           # 'data_up_to_date' hoặc dạng lạ
        return None, f"không có nội dung (data={str(data)[:40]})"
    return {
        "mau": data.get("quick_replies") or [],
        "chu_de": data.get("quick_reply_topics") or [],
        "phien_ban": qr.get("lastest_version"),
    }, None


def kiem_phien_ban(page_id, user_token, ver):
    """Hỏi RẺ: kịch bản page này còn đúng phiên bản `ver` không?

    Đây là mẹo `client_version` của API Pancake — gửi đúng số phiên bản đang giữ thì API trả
    vỏn vẹn {"data": "data_up_to_date"}. Đo thật 2026-09-05 trên page Leg Glow Lab UAE:
    hỏi toàn bộ 20.000 byte, hỏi kiểu này 100 byte — nhẹ hơn 200 lần.
    Nhờ vậy mỗi vòng chạy kiểm được cả thị trường trong vài giây.

    Trả (đã_đổi, phiên_bản_mới_nhất, lỗi). đã_đổi=True nghĩa là phải tải lại toàn bộ page đó.
    """
    u = f"{WEB_API}/pages/{page_id}/settings?" + urllib.parse.urlencode({
        "access_token": user_token,
        "load_quick_replies_only": "true",
        "client_version": str(ver if ver is not None else 0),
    })
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode() or "{}")
    except Exception as e:
        return None, None, str(e)
    if not res.get("success"):
        # Hay gặp nhất: mã 121/122 "không tìm thấy / đã hết hạn gói cước" của page đó trên
        # Pancake. Phải trả về LỖI chứ không phải "có bản mới": nếu không, mỗi vòng chạy lại
        # tưởng page vừa sửa rồi đi tải lại, tải lại cũng hỏng, và không ai biết lý do thật.
        return None, None, str(res.get("message") or res)[:90]
    qr = res.get("quick_replies") or {}
    if not isinstance(qr, dict):
        return None, None, f"dạng trả về lạ: {str(qr)[:60]}"
    moi_nhat = qr.get("lastest_version")
    if qr.get("data") == "data_up_to_date" or qr.get("new_version") is False:
        return False, moi_nhat, None
    return True, moi_nhat, None


def dong_bo(mkey, im=False):
    """Đồng bộ kịch bản: kiểm phiên bản mọi page, CHỈ tải lại page nào vừa sửa trên Pancake.

    Có hàm này thì chủ shop sửa "Trả lời nhanh" xong là vòng chạy sau dùng bản mới ngay,
    không phải nhớ chạy `kich_ban.py tai` — trước đây quên là AI báo giá cũ cho khách.

    Chỉ soi những page ĐÃ có trong kich_ban.json. Page chưa từng lấy được (hết gói cước
    Pancake chẳng hạn) thì phải chạy `tai` đầy đủ, vì ở đây chưa có phiên bản nào để so.

    Trả (số page kiểm, danh sách page vừa cập nhật, danh sách (tên page, lỗi),
    số page có token mà chưa có kịch bản).
    """
    tok = qht.load_env().get("PANCAKE_USER_TOKEN", "")
    f = _state(mkey, "kich_ban.json")
    if not tok or not os.path.exists(f):
        return 0, [], [], 0
    kb = json.load(open(f, encoding="utf-8"))
    try:
        # page_tokens.json giữ TOÀN BỘ page của tài khoản, không lọc theo thị trường —
        # chỉ page có token mới thật sự thuộc thị trường này. Đếm cả page không token là
        # báo động giả (đo thật: 43 page "thiếu" trong khi con số đúng là 0).
        chua = sum(1 for p, v in _pages(mkey).items()
                   if p not in kb and v.get("token"))
    except SystemExit:
        chua = 0
    doi, loi = [], []
    for pid, v in list(kb.items()):
        # Hỏi 27 page liên tiếp thì thỉnh thoảng rớt một hai cái. Rớt mà bỏ qua lặng lẽ là
        # page vừa sửa không được cập nhật — nên thử lại một lần trước khi tính là lỗi.
        da_doi, _moi, err = kiem_phien_ban(pid, tok, v.get("phien_ban"))
        if err:
            time.sleep(0.6)
            da_doi, _moi, err = kiem_phien_ban(pid, tok, v.get("phien_ban"))
        if err:
            loi.append((v.get("ten_page") or pid, err))
            continue
        time.sleep(0.08)
        if not da_doi:
            continue
        m, err = tai_1_page(pid, tok)
        if err:
            loi.append((v.get("ten_page") or pid, err))
            continue
        kb[pid] = {"ten_page": v.get("ten_page"), "phien_ban": m["phien_ban"],
                   "chu_de": [{"id": c.get("id"), "ten": c.get("text") or c.get("name")} for c in m["chu_de"]],
                   "mau": [_gon(x) for x in m["mau"]], "tai_luc": int(time.time())}
        doi.append(v.get("ten_page") or pid)
        if im:
            print(f"  ♻️  kịch bản mới: {v.get('ten_page','?')[:44]} "
                  f"({len(kb[pid]['mau'])} mẫu)")
    if doi:
        json.dump(kb, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return len(kb), doi, loi, chua


def in_loi_dong_bo(loi, thut="     "):
    """Gộp lỗi theo lý do rồi in. Cùng một lý do lặp 7 dòng mỗi vòng chạy là nhiễu, che mất
    những dòng đáng đọc — mà đây lại là tình trạng kéo dài ngày này qua ngày khác."""
    if not loi:
        return
    nhom = {}
    for ten, e in loi:
        nhom.setdefault(e, []).append(ten)
    for e, ds in sorted(nhom.items(), key=lambda x: -len(x[1])):
        print(f"{thut}⚠️  {len(ds)} page không kiểm được kịch bản — {e}")
        print(f"{thut}   " + ", ".join(t[:34] for t in ds[:6])
              + (f" … +{len(ds)-6}" if len(ds) > 6 else ""))


def _gon(mau):
    """Rút 1 mẫu câu về dạng gọn cho AI đọc: từ khoá + các tin + ĐƯỜNG DẪN ảnh.

    Trước 2026-09-05 chỉ đếm `so_anh` rồi vứt ảnh đi, nên AI gửi được chữ mà mất ảnh — đúng
    những mẫu quan trọng nhất: /Paypal, /VENMO, /CASH_APP, /MoneyGram+WesternUnion, /chaohang.
    Nay giữ cả `url` (host content.pancake.vn) để gửi kèm được.
    """
    tins, anh = [], []
    for m in mau.get("messages") or []:
        t = (m.get("message") or "").strip()
        anh += [x.get("url") for x in (m.get("photos") or []) if x.get("url")]
        if t:
            tins.append(t)
    return {
        "tu_khoa": mau.get("shortcut") or "",          # API gọi là "shortcut" (gõ /<shortcut>)
        "chu_de_id": mau.get("type_id"),
        "tin": tins,
        "so_anh": len(anh),
        "anh": anh,
    }


def cmd_tai(mkey):
    tok = qht.load_env().get("PANCAKE_USER_TOKEN", "")
    if not tok:
        sys.exit("❌ Thiếu PANCAKE_USER_TOKEN trong .env")
    pages = _pages(mkey)
    f_kb = _state(mkey, "kich_ban.json")
    # GỘP, không ghi đè: page nào lần này lỗi (hết gói cước Pancake chẳng hạn) mà lần trước
    # đã lấy được thì GIỮ bản cũ. Ghi đè thẳng là mất trắng kịch bản của page đó, AI hết chạy.
    cu = json.load(open(f_kb, encoding="utf-8")) if os.path.exists(f_kb) else {}
    out, loi, giu = dict(cu), [], 0
    print(f"\n📥 Tải kịch bản {len(pages)} page của {mkey}…\n")
    for pid, st in pages.items():
        ten = st.get("name", "?")
        kb, err = tai_1_page(pid, tok)
        if err:
            loi.append((ten, err))
            if pid in cu:
                giu += 1
            continue
        out[pid] = {
            "ten_page": ten,
            "phien_ban": kb["phien_ban"],
            "chu_de": [{"id": c.get("id"), "ten": c.get("text") or c.get("name")} for c in kb["chu_de"]],
            "mau": [_gon(m) for m in kb["mau"]],
            "tai_luc": int(time.time()),
        }
        n = len(out[pid]["mau"])
        print(f"  {'✅' if n else '⚠️ '} {ten[:44]:46s} {n:3d} mẫu câu", flush=True)
        time.sleep(0.15)
    json.dump(out, open(f_kb, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    co = sum(1 for v in out.values() if v["mau"])
    print(f"\n💾 {f_kb}")
    print(f"   {co} page CÓ kịch bản | {len(out)-co} page kịch bản rỗng | {len(loi)} page lỗi"
          + (f" (trong đó {giu} page giữ nguyên bản chụp cũ)" if giu else ""))
    for ten, e in loi[:10]:
        print(f"   ✖ {ten[:44]:46s} {e[:60]}")


def _tim(mkey, khoa):
    kb = json.load(open(_state(mkey, "kich_ban.json"), encoding="utf-8"))
    if khoa in kb:
        return khoa, kb[khoa]
    for pid, v in kb.items():
        if khoa.lower() in (v["ten_page"] or "").lower():
            return pid, v
    sys.exit(f"Không thấy page {khoa!r}. Chạy 'tai' trước, hoặc gõ 1 phần tên page.")


def cmd_xem(mkey, khoa):
    pid, v = _tim(mkey, khoa)
    print(f"\n═══ {v['ten_page']} ({pid}) — {len(v['mau'])} mẫu câu ═══\n")
    ten_cd = {c["id"]: c["ten"] for c in v.get("chu_de") or []}
    for m in v["mau"]:
        cd = ten_cd.get(m.get("chu_de_id"))
        print(f"── /{m['tu_khoa']}" + (f"   [chủ đề: {cd}]" if cd else "")
              + (f"   [{m['so_anh']} ảnh]" if m["so_anh"] else ""))
        for t in m["tin"]:
            print("   " + t.replace("\n", "\n   "))
        print()


def cmd_thieu(mkey):
    kb = json.load(open(_state(mkey, "kich_ban.json"), encoding="utf-8"))
    rong = [(v["ten_page"], pid) for pid, v in kb.items() if not v["mau"]]
    print(f"\n{len(kb)-len(rong)}/{len(kb)} page có kịch bản. Page KHÔNG có mẫu câu nào:\n")
    for ten, pid in rong:
        print(f"  ✖ {ten[:46]:48s} {pid}")
    print("\n→ Page rỗng thì AI không có nguồn giá/chính sách để trả lời (luật mục 10: không bịa).")


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "tai":
        cmd_tai(a[1])
    elif len(a) >= 3 and a[0] == "xem":
        cmd_xem(a[1], a[2])
    elif len(a) >= 2 and a[0] == "thieu":
        cmd_thieu(a[1])
    elif len(a) >= 2 and a[0] in ("dongbo", "dong_bo"):
        t = time.time()
        n, doi, loi, chua = dong_bo(a[1], im=True)
        print(f"\n  Kiểm {n} page trong {time.time()-t:.1f}s — "
              f"{len(doi)} page có kịch bản mới, {len(loi)} lỗi.")
        in_loi_dong_bo(loi, "  ")
        if chua:
            print(f"  {chua} page chưa từng lấy được kịch bản — chạy "
                  f"`python3 kich_ban.py tai {a[1]}` nếu vừa gia hạn gói cước Pancake.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

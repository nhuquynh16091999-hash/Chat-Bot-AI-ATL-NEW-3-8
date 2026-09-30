#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quét hội thoại Pancake có tag "Lên đơn" để tạo đơn tự động.
API chat Pancake: https://developer.pancake.biz/  (pages.fm)

Lệnh:
  python3 quet_hoi_thoai.py pages            # liệt kê page + tình trạng token/tag
  python3 quet_hoi_thoai.py setup            # tạo page token + tìm tag cho các page
  python3 quet_hoi_thoai.py setup --only ID1,ID2   # chỉ setup 1 số page
  python3 quet_hoi_thoai.py setup --force-token --hong  # cấp lại token cho page bị đánh dấu HỎNG
  python3 quet_hoi_thoai.py quet             # quét hội thoại có tag, ghi state/pending.json
  python3 quet_hoi_thoai.py quet --gio 48    # quét trong 48 giờ gần nhất
  python3 quet_hoi_thoai.py danh-dau <page_id> <conversation_id> <ghi chú>  # đánh dấu đã xử lý
  python3 quet_hoi_thoai.py pending          # xem các hội thoại đang chờ lên đơn

Cấu hình trong .env (cùng thư mục):
  PANCAKE_USER_TOKEN=...   # pages.fm -> Tài khoản -> Cài đặt cá nhân -> API Access Token
  TAG_NAME=Lên đơn         # tên tag đánh dấu hội thoại đã chốt (mặc định: Lên đơn)
  PAGES=id1,id2            # (tùy chọn) chỉ quét các page này; bỏ trống = tất cả
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE_USER = "https://pages.fm/api/v1"
BASE_PAGE_V1 = "https://pages.fm/api/public_api/v1"
BASE_PAGE_V2 = "https://pages.fm/api/public_api/v2"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_TIMEOUT = 10 * 60  # khóa tự hết hạn sau 10 phút (phòng phiên xử lý bị chết giữa chừng)


def set_state_dir(d):
    """Chuyển thư mục state (mỗi thị trường 1 thư mục riêng)."""
    global STATE_DIR, TOKENS_FILE, PROCESSED_FILE, PENDING_FILE, META_FILE, LOCK_FILE
    STATE_DIR = d
    TOKENS_FILE = os.path.join(d, "page_tokens.json")
    PROCESSED_FILE = os.path.join(d, "da_xu_ly.json")
    PENDING_FILE = os.path.join(d, "pending.json")
    META_FILE = os.path.join(d, "meta.json")
    LOCK_FILE = os.path.join(d, "lock.json")


set_state_dir(os.path.join(SCRIPT_DIR, "state"))


def set_pos(api_key, shop_id):
    """Chuyển shop POS dùng để lọc page theo thị trường."""
    global POS_API_KEY, POS_SHOP_ID
    POS_API_KEY, POS_SHOP_ID = api_key, str(shop_id)


def load_env():
    env = {}
    path = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()
USER_TOKEN = ENV.get("PANCAKE_USER_TOKEN", "")
TAG_NAME = ENV.get("TAG_NAME", "Lên đơn")
PAGES_FILTER = [p.strip() for p in ENV.get("PAGES", "").split(",") if p.strip()]
POS_API_KEY = ENV.get("PANCAKE_API_KEY", "")
POS_SHOP_ID = ENV.get("PANCAKE_SHOP_ID", "")


def die(msg):
    print(f"\n❌ {msg}")
    sys.exit(1)


def strip_accents(s):
    import unicodedata
    s = str(s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm(s):
    return re.sub(r"\s+", " ", strip_accents(str(s or "")).lower()).strip()


# Tiền tố cố định của lỗi "token page đã chết" — chỗ khác nhận diện bằng la_loi_token().
LOI_TOKEN = "token hỏng"


def loi_api(res):
    """Lỗi nằm trong THÂN phản hồi: pages.fm trả HTTP 200 kèm {"success": false, ...}.

    Không bắt là NUỐT LỖI. Token page chết thì res.get("conversations") ra None, chỗ gọi
    đọc thành "page này không có hội thoại nào gắn tag" nên sale gắn tag "Lên đơn" mà
    không đơn nào được tạo, cũng không ai được báo. Đo 2026-09-03 trên UAE: 30/48 page
    trả error_code 105 "access_token renewed please use new access_token".
    Cùng cách làm với loi_token() trong ai_sale.py.
    """
    if not isinstance(res, dict) or res.get("success") is not False:
        return None                    # endpoint cũ (vd /tags) không có khoá success -> coi là được
    ma = str(res.get("error_code") or res.get("message_code") or "").strip()
    # `message` trống không có nghĩa là "không rõ lý do": Pancake còn trả `message_code`
    # (vd "invalid_upload_fb_attachments_result" khi đính kèm hỏng ở page bị #2022) hoặc gói lỗi
    # trong `error`/`errors`. Nuốt hết thành "không rõ lý do" là tự bịt mắt mình — 48/156 lượt
    # gửi ảnh hỏng ngày 20/09 đều rơi vào đây, không ai biết vì sao.
    tin = (str(res.get("message") or "").strip()
           or str(res.get("error") or res.get("errors") or "").strip()
           or ("" if ma else f"phản hồi lạ: {str({k: v for k, v in res.items() if k != 'success'})[:160]}"))
    if ma == "105" or "token" in tin.lower():
        return f"{LOI_TOKEN} ({ma or '?'}: {tin})"
    return f"API lỗi {ma or '?'}: {tin}" if tin else f"API lỗi {ma}"


def la_loi_token(err):
    """Lỗi này là token page chết (phải cấp lại token) chứ không phải trục trặc tạm thời?"""
    return bool(err) and str(err).startswith(LOI_TOKEN)


def danh_dau_token(st, err):
    """Ghi/xoá dấu 'token hỏng' trên hồ sơ 1 page. True = hồ sơ có đổi, phải lưu lại.

    Có dấu này thì lệnh 'pages' / 'bao-cao' nói THẬT còn bao nhiêu page chạy được, và
    'setup --hong' biết phải cấp lại token cho đúng những page nào — khỏi gọi lại API.
    """
    if la_loi_token(err):
        if (st.get("token_hong") or {}).get("ly_do") == err:
            return False
        st["token_hong"] = {"luc": int(time.time()), "ly_do": err}
        return True
    if err:
        return False                   # lỗi mạng/tạm thời: giữ nguyên dấu cũ, đừng kết luận
    return st.pop("token_hong", None) is not None


def luu_dau_token(ready):
    """Lưu RIÊNG dấu token_hong: đọc lại file rồi mới ghi, để không đè mất token mà lệnh
    setup chạy tay cùng lúc vừa cấp."""
    tokens = load_json(TOKENS_FILE, {})
    for pid, st in ready.items():
        if pid not in tokens:
            continue
        if st.get("token_hong"):
            tokens[pid]["token_hong"] = st["token_hong"]
        else:
            tokens[pid].pop("token_hong", None)
    save_json(TOKENS_FILE, tokens)


def http_json(method, url, params=None):
    """Gọi API, trả (data, error). Không dừng chương trình khi lỗi.

    Chỗ gọi CHỈ cần kiểm `err`: lỗi của pages.fm phần lớn nằm trong thân phản hồi
    HTTP 200 (xem loi_api) chứ không phải ở mã HTTP.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            loi = loi_api(data)
            return (None, loi) if loi else (data, None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:300]
        return None, f"HTTP {e.code}: {raw}"
    except Exception as e:
        return None, str(e)


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pos_shop_page_ids():
    """Danh sách page id thuộc shop POS đã cấu hình — để không đụng page của shop khác."""
    if not (POS_API_KEY and POS_SHOP_ID):
        return None
    res, err = http_json("GET", "https://pos.pages.fm/api/v1/shops", {"api_key": POS_API_KEY})
    if err:
        print(f"⚠ Không lấy được danh sách page của shop POS: {err}")
        return None
    for s in res.get("shops") or []:
        if str(s.get("id")) == str(POS_SHOP_ID):
            return {str(p.get("id")) for p in (s.get("pages") or []) if p.get("id")}
    return None


def get_pages():
    if not USER_TOKEN:
        die("Chưa có PANCAKE_USER_TOKEN trong .env\n"
            "   Lấy tại: pages.fm → Tài khoản (góc trái dưới) → Cài đặt cá nhân → API Access Token")
    res, err = http_json("GET", f"{BASE_USER}/pages", {"access_token": USER_TOKEN})
    if err:
        die(f"Không lấy được danh sách page: {err}")
    pages = res.get("pages") or []
    if not pages:  # API trả dạng categorized
        pages = (res.get("categorized") or {}).get("activated") or []
    if PAGES_FILTER:
        pages = [p for p in pages if str(p.get("id")) in PAGES_FILTER]
    else:
        shop_ids = pos_shop_page_ids()
        # PHẢI phân biệt "không tra được" (None -> đành không lọc) với "shop KHÔNG có page nào"
        # (set rỗng -> giữ 0 page). Trước 2026-09-05 dùng `if shop_ids:` nên set rỗng cũng rơi
        # vào nhánh không lọc, tức shop trống thì bộ lọc TỰ TẮT và mọi page của tài khoản lọt qua.
        # Đo thật: shop Bulgaria có 0 page, setup vẫn cấp token cho 159 page của Kuwait/Qatar/
        # UAE/Đài Loan rồi ghi vào state/bulgaria/ — chạy trên đó là bán giá EUR cho khách vùng Vịnh.
        if shop_ids is not None:
            lac = [p for p in pages if str(p.get("id")) not in shop_ids]
            pages = [p for p in pages if str(p.get("id")) in shop_ids]
            if lac:
                print(f"   ⚠ Bỏ qua {len(lac)} page KHÔNG thuộc shop {POS_SHOP_ID} "
                      f"(vd: {', '.join((x.get('name') or '?')[:24] for x in lac[:3])})")
    return pages


# ---------------- Lệnh ----------------

def cmd_pages():
    pages = get_pages()
    tokens = load_json(TOKENS_FILE, {})
    print(f"\n📄 Tổng số page: {len(pages)}  (TAG_NAME = {TAG_NAME!r})")
    for p in pages:
        pid = str(p.get("id"))
        st = tokens.get(pid, {})
        token_ok = "✔ token" if st.get("token") else "✖ chưa có token"
        if st.get("token_hong"):
            token_ok = f"✖ TOKEN HỎNG ({time.strftime('%d/%m %H:%M', time.localtime(st['token_hong'].get('luc', 0)))})"
        ids = tag_ids_of(st)
        tag_ok = f"✔ tag id {', '.join(str(i) for i in ids)}" if ids else "✖ chưa thấy tag"
        print(f"  • {pid}  {p.get('name', '?')[:50]:<50}  {token_ok}, {tag_ok}")
    print("\n→ Chạy 'setup' để tạo token + tìm tag cho các page còn thiếu.")
    if any(st.get("token_hong") for st in tokens.values()):
        print("→ Cấp lại token cho page HỎNG: setup --force-token --hong")


# find_tag_ids trả đúng chuỗi này khi GỌI ĐƯỢC nhưng page không có tag — khác hẳn
# lỗi gọi API (token hỏng / mạng). Chỗ gọi phân biệt 2 loại bằng hằng số này.
KHONG_CO_TAG = "không có tag này trên page"


def find_tag_ids(page_id, token):
    """TẤT CẢ tag id trùng tên TAG_NAME trên page.
    Nhiều page lỡ tạo 2 tag cùng tên 'Lên đơn' — nhân viên gắn cái nào cũng phải nhận."""
    res, err = http_json("GET", f"{BASE_PAGE_V1}/pages/{page_id}/tags", {"page_access_token": token})
    if err:
        return [], err
    ids = [t.get("id") for t in res.get("tags") or []
           if norm(t.get("text")) == norm(TAG_NAME) and t.get("id") is not None]
    if not ids:
        return [], KHONG_CO_TAG
    return ids, None


def tag_ids_of(st):
    """Đọc danh sách tag id của 1 page — chấp nhận cả state cũ chỉ có 'tag_id'."""
    ids = st.get("tag_ids")
    if ids:
        return list(ids)
    return [st["tag_id"]] if st.get("tag_id") is not None else []


def cap_lai_token(pid, ten=None):
    """Sinh token MỚI cho ĐÚNG một page, lưu ngay vào page_tokens.json. Trả (token, lỗi).

    Vì sao có hàm này: chủ shop đăng xuất/đăng nhập lại Pancake hằng ngày để thêm page mới,
    và Pancake thu hồi token page cũ mỗi lần như vậy. Trước đây phải chạy tay
    `setup --force-token --hong` mới chạy lại được — không ai nhớ, nên AI im lặng bỏ page
    suốt nhiều ngày mà không ai biết (mục 11: token hỏng thì bỏ qua page đó).

    ✅ USER TOKEN KHÔNG chết theo — kiểm chứng 2026-09-08: đăng nhập lại nhiều lần, user token
    trong .env vẫn gọi được và nhìn thấy 706 page. Nên token page sinh lại được BẤT CỨ LÚC NÀO,
    không cần người làm gì. Đây là cơ sở của việc tự chữa trong vòng chạy.

    ⚠️ Sinh token mới LÀM TOKEN CŨ HẾT HIỆU LỰC. Chỉ gọi khi token cũ đã chết (lỗi 105) —
    đừng gọi cho page đang chạy tốt.

    🔒 KHOÁ AN TOÀN `PANCAKE_SERVER=1` — thiếu nó thì KHÔNG sinh token.
    Pancake chỉ giữ MỘT page token còn hiệu lực cho mỗi page. Máy Mac sinh token là token của
    VPS chết ngay, và ngược lại — hai máy đánh nhau, ngày nào cũng có bên mất token.
    `ket_nap_page.py` đã có khoá này từ đầu (HUONG_DAN_SERVER.md mục "khóa an toàn"), nhưng
    nó nằm ở CHỖ GỌI nên hàm nào không biết là đi vòng qua được — và đúng là đã đi vòng qua
    thật ngày 2026-09-08. Nay khoá đặt ở ĐÂY, chỗ duy nhất sinh token, nên không ai vòng được.
    """
    if (os.environ.get("PANCAKE_SERVER") or load_env().get("PANCAKE_SERVER")) != "1":
        return None, ("máy này KHÔNG phải server (thiếu PANCAKE_SERVER=1) — không sinh token, "
                      "vì sẽ vô hiệu token của VPS đang chạy thật")
    res, err = http_json("POST", f"{BASE_USER}/pages/{pid}/generate_page_access_token",
                         {"access_token": USER_TOKEN})
    token = ((res or {}).get("page_access_token")
             or ((res or {}).get("data") or {}).get("page_access_token"))
    if not token:
        return None, (err or str(res))[:120]
    tokens = load_json(TOKENS_FILE, {})
    st = tokens.get(str(pid)) or {"name": ten or str(pid)}
    if ten:
        st["name"] = ten
    st["token"] = token
    st.pop("token_hong", None)
    tag_ids, _ = find_tag_ids(str(pid), token)
    if tag_ids:
        st["tag_ids"] = tag_ids
        st["tag_id"] = tag_ids[0]
    tokens[str(pid)] = st
    save_json(TOKENS_FILE, tokens)
    return token, None


def cmd_setup(only=None, force_token=False, chi_hong=False):
    tokens = load_json(TOKENS_FILE, {})
    if chi_hong:
        # Chỉ các page vòng quét đã ghi dấu token hỏng. Bắt buộc kèm force_token:
        # token cũ vẫn còn nguyên trong file nên nhánh "chỉ tạo khi chưa có" sẽ bỏ qua.
        only = {pid for pid, st in tokens.items() if st.get("token_hong")}
        force_token = True
        if not only:
            print("✔ Không page nào đang bị đánh dấu token hỏng — không phải cấp lại gì.")
            return
        print(f"🔑 Cấp lại token cho {len(only)} page bị đánh dấu HỎNG...")
    pages = get_pages()
    if only:
        pages = [p for p in pages if str(p.get("id")) in only]
    ok = miss_tag = fail = 0
    for p in pages:
        pid = str(p.get("id"))
        name = p.get("name", "?")
        st = tokens.get(pid, {"name": name})
        st["name"] = name
        # 1. Page access token: chỉ tạo khi chưa có (tạo lại sẽ vô hiệu token cũ!)
        if not st.get("token") or force_token:
            res, err = http_json("POST", f"{BASE_USER}/pages/{pid}/generate_page_access_token",
                                 {"access_token": USER_TOKEN})
            token = (res or {}).get("page_access_token") or ((res or {}).get("data") or {}).get("page_access_token")
            if not token:
                print(f"  ✖ {name[:45]}: không tạo được token ({err or res})")
                fail += 1
                tokens[pid] = st
                continue
            st["token"] = token
            st.pop("token_hong", None)       # token mới -> xoá dấu hỏng của vòng quét cũ
        # 2. Tìm tag (có thể trùng tên nhiều cái -> giữ hết)
        tag_ids, err = find_tag_ids(pid, st["token"])
        st["tag_ids"] = tag_ids
        st["tag_id"] = tag_ids[0] if tag_ids else None   # giữ cho tương thích ngược
        if not tag_ids:
            print(f"  ⚠ {name[:45]}: có token nhưng {err}")
            miss_tag += 1
        else:
            if len(tag_ids) > 1:
                print(f"  ℹ {name[:45]}: page có {len(tag_ids)} tag trùng tên {TAG_NAME!r} "
                      f"(id {tag_ids}) — đã nhận hết")
            ok += 1
        tokens[pid] = st
        save_json(TOKENS_FILE, tokens)  # lưu ngay từng page, gián đoạn không mất tiến độ
        time.sleep(0.15)  # tôn trọng rate limit
    save_json(TOKENS_FILE, tokens)
    print(f"\n✅ Sẵn sàng: {ok} page  |  ⚠ thiếu tag {TAG_NAME!r}: {miss_tag} page  |  ✖ lỗi token: {fail} page")
    if miss_tag:
        print(f"→ Tạo tag tên {TAG_NAME!r} trên các page còn thiếu (trong Pancake), rồi chạy setup lại.")


def message_text(m):
    t = m.get("original_message") or m.get("message") or ""
    t = re.sub(r"<[^>]+>", " ", str(t))          # bỏ HTML
    return re.sub(r"\s+", " ", t).strip()[:500]


MAX_TIN = 200   # API chỉ trả ~30 tin/lần -> phải gọi nhiều lần, nếu không sẽ mất thông tin
                # khách cho từ trước (hội thoại dài, bot gửi nhiều tin quảng cáo)


def extract_conversation(page_id, page_name, token, conv, max_tin=MAX_TIN):
    """Lấy tin nhắn + thông tin khách của 1 hội thoại (tự lật trang để lấy đủ tin cũ)."""
    cid = conv.get("id")
    url = f"{BASE_PAGE_V1}/pages/{page_id}/conversations/{cid}/messages"
    res = None
    raw, seen_ids = [], set()
    while len(raw) < max_tin:
        params = {"page_access_token": token}
        if raw:
            params["current_count"] = len(raw)
        r, err = http_json("GET", url, params)
        if err:
            if res is None:
                return {"page_id": page_id, "page_name": page_name, "conversation_id": cid, "error": err}
            break                                # lấy được phần nào dùng phần đó
        if res is None:
            res = r                              # trang đầu chứa hồ sơ khách
        batch = r.get("messages") or []
        moi = [m for m in batch if m.get("id") not in seen_ids]
        seen_ids.update(m.get("id") for m in batch)
        if not moi:
            break                                # hết tin cũ
        raw.extend(moi)
        if len(batch) < 25:                      # trang cuối (API trả ~30/lần)
            break
        time.sleep(0.15)                         # tôn trọng rate limit 5 lệnh/giây/page

    msgs = []
    for m in raw:                                # thứ tự API: mới -> cũ
        text = message_text(m)
        if not text:
            continue
        frm = m.get("from") or {}
        is_shop = bool(frm.get("admin_id") or frm.get("admin_name")) or str(frm.get("id")) == str(page_id)
        msgs.append({"luc": m.get("inserted_at"), "ai": "shop" if is_shop else "khach", "noi_dung": text})
    msgs.reverse()                               # thành thứ tự cũ -> mới

    # Thông tin khách do nhân viên đã lưu (nếu có)
    customers = []
    for c in res.get("customers") or []:
        customers.append({
            "ten": c.get("name"),
            "sdt_gan_day": [x.get("phone_number") for x in (c.get("recent_phone_numbers") or []) if x.get("phone_number")],
            "dia_chi_da_luu": [
                {"ten": a.get("full_name"), "sdt": a.get("phone_number"),
                 "dia_chi": a.get("full_address") or a.get("address"),
                 "dia_chi_goc": a.get("address")}      # không có đuôi ", <tỉnh>" Pancake tự ghép
                for a in (c.get("shop_customer_addresses") or [])
            ],
        })
    # SĐT xuất hiện trong nội dung chat (UAE: 05xxxxxxxx / +9715xxxxxxx, VN: 0xxxxxxxxx)
    all_text = " ".join(m["noi_dung"] for m in msgs)
    phones = list(dict.fromkeys(re.findall(r"(?:\+?971|0)5\d{8}|0\d{9,10}", all_text)))

    return {
        "page_id": page_id,
        "page_name": page_name,
        "conversation_id": cid,
        "loai": conv.get("type"),
        "khach": (conv.get("from") or {}).get("name"),
        "cap_nhat_luc": conv.get("updated_at"),
        "ho_so_khach": customers,
        "sdt_trong_chat": phones,
        "tin_nhan": msgs,
    }


def acquire_lock():
    """Chặn 2 phiên quét chạy chồng nhau (nguy cơ tạo đơn trùng). True = lấy được khóa."""
    lock = load_json(LOCK_FILE, {})
    if lock.get("luc") and time.time() - lock["luc"] < LOCK_TIMEOUT:
        return False
    save_json(LOCK_FILE, {"luc": time.time()})
    return True


def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def cmd_scan(hours=None):
    if not acquire_lock():
        print("LOCKED: đang có phiên xử lý khác chạy — dừng, KHÔNG xử lý gì thêm.")
        return
    tokens = load_json(TOKENS_FILE, {})
    ready = {pid: st for pid, st in tokens.items() if st.get("token") and tag_ids_of(st)}
    if not ready:
        release_lock()
        die("Chưa có page nào sẵn sàng. Chạy 'setup' trước.")
    processed = load_json(PROCESSED_FILE, {})
    meta = load_json(META_FILE, {})
    now = int(time.time())
    if hours:
        since = now - int(hours * 3600)
    else:
        since = max(meta.get("last_scan", now - 24 * 3600) - 900, now - 72 * 3600)

    pending, errors, hong = [], [], []
    doi_dau = False
    for pid, st in ready.items():
        muon = set(tag_ids_of(st))
        convs, loi_page = {}, None
        for tid in sorted(muon):     # page có 2 tag trùng tên -> hỏi API từng cái rồi gộp
            res, err = http_json("GET", f"{BASE_PAGE_V2}/pages/{pid}/conversations",
                                 {"page_access_token": st["token"], "tags": tid,
                                  "type": "INBOX",   # 16/09: không đụng bình luận, để sale xử
                                  "since": since, "until": now, "order_by": "updated_at"})
            if err:
                loi_page = err
                continue
            for c in res.get("conversations") or []:
                convs[c.get("id")] = c
            if len(muon) > 1:
                time.sleep(0.1)
        doi_dau = danh_dau_token(st, loi_page) or doi_dau
        if loi_page:
            # Token hỏng thì pages.fm vẫn trả HTTP 200 (xem loi_api). Bản cũ chỉ kiểm mã
            # HTTP nên hiểu nhầm thành "page không có hội thoại gắn tag" và im lặng bỏ qua:
            # tag "Lên đơn" của sale rơi vào hư không, không đơn nào được tạo.
            errors.append(f"{st.get('name', pid)} ({pid}): {loi_page}")
            if la_loi_token(loi_page):
                hong.append(pid)
            if not convs:
                continue
        for conv in convs.values():
            # Xác nhận tag thật sự đang gắn (API đôi khi trả cả hội thoại từng có tag)
            tag_ids = {t.get("id") for t in (conv.get("tags") or []) if t}
            if not (muon & tag_ids):
                continue
            key = f"{pid}_{conv.get('id')}"
            if key in processed:
                continue
            record = extract_conversation(pid, st.get("name", pid), st["token"], conv)
            if record.get("error"):
                # Đọc hụt tin nhắn -> KHÔNG đẩy vào pending: hồ sơ rỗng sẽ thành đơn trắng.
                # Cũng không đánh dấu đã xử lý, nên vòng sau tự quét lại hội thoại này.
                errors.append(f"{st.get('name', pid)} / hội thoại {conv.get('id')}: {record['error']}")
                continue
            pending.append(record)
            time.sleep(0.1)
        time.sleep(0.1)

    if doi_dau:
        luu_dau_token(ready)
    meta["last_scan"] = now
    save_json(META_FILE, meta)
    save_json(PENDING_FILE, {"quet_luc": now, "cho_xu_ly": pending, "loi": errors})
    if not pending:
        release_lock()  # không có gì để xử lý -> nhả khóa ngay cho phiên sau

    print(f"\n🔎 Đã quét {len(ready)} page (từ {int((now - since) / 3600)} giờ trước)")
    print(f"   Hội thoại chờ lên đơn: {len(pending)}")
    for r in pending:
        print(f"   • [{r['page_name']}] {r.get('khach')} — {len(r.get('tin_nhan', []))} tin nhắn — conv {r['conversation_id']}")
    if errors:
        print(f"   ⚠ Lỗi {len(errors)} chỗ:")
        for e in errors[:8]:
            print(f"      - {e}")
        if len(errors) > 8:
            print(f"      ... và {len(errors) - 8} lỗi nữa")
    if hong:
        print(f"   ⚠ {len(hong)}/{len(ready)} page TOKEN HỎNG — hội thoại gắn tag {TAG_NAME!r} "
              f"trên các page này KHÔNG lên đơn được.")
        print(f"      → Cấp lại token: python3 auto_len_don.py setup "
              f"{os.path.basename(STATE_DIR)} --force-token --hong")
    print(f"\n→ Chi tiết trong: {PENDING_FILE}")


def cmd_mark(page_id, conv_id, note):
    processed = load_json(PROCESSED_FILE, {})
    processed[f"{page_id}_{conv_id}"] = {"luc": int(time.time()), "ghi_chu": note}
    save_json(PROCESSED_FILE, processed)
    # bỏ khỏi pending nếu có
    pend = load_json(PENDING_FILE, {})
    if pend.get("cho_xu_ly"):
        pend["cho_xu_ly"] = [r for r in pend["cho_xu_ly"]
                             if not (str(r.get("page_id")) == str(page_id) and str(r.get("conversation_id")) == str(conv_id))]
        save_json(PENDING_FILE, pend)
    print(f"✔ Đã đánh dấu {page_id}/{conv_id}: {note}")


def cmd_pending():
    pend = load_json(PENDING_FILE, {})
    items = pend.get("cho_xu_ly") or []
    print(f"\n📥 Hội thoại chờ lên đơn: {len(items)}")
    for r in items:
        print(f"  • [{r.get('page_name')}] {r.get('khach')} — conv {r.get('conversation_id')}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1].lower(), sys.argv[2:]
    if os.path.isdir(os.path.join(SCRIPT_DIR, "state", "uae")) and cmd in ("setup", "quet", "pages"):
        die("Hệ thống đã chuyển sang ĐA THỊ TRƯỜNG.\n"
            "   Dùng:  python3 auto_len_don.py " + cmd + " <thị trường>   (ví dụ: uae, saudi, japan...)\n"
            "   Xem danh sách:  python3 auto_len_don.py thi-truong")
    if cmd == "pages":
        cmd_pages()
    elif cmd == "setup":
        only = None
        force = "--force-token" in args
        if "--only" in args:
            only = set(args[args.index("--only") + 1].split(","))
        cmd_setup(only, force, "--hong" in args)
    elif cmd == "quet":
        hours = None
        if "--gio" in args:
            hours = float(args[args.index("--gio") + 1])
        cmd_scan(hours)
    elif cmd == "danh-dau":
        if len(args) < 2:
            die("Dùng: danh-dau <page_id> <conversation_id> [ghi chú]")
        cmd_mark(args[0], args[1], " ".join(args[2:]) or "đã xử lý")
    elif cmd == "pending":
        cmd_pending()
    elif cmd == "mo-khoa":
        release_lock()
        print("✔ Đã nhả khóa xử lý.")
    else:
        print(__doc__)
        die(f"Lệnh không hiểu: {cmd}")


if __name__ == "__main__":
    main()

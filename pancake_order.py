#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ tạo đơn hàng Pancake POS qua Open API chính thức.
API docs: https://docs.pancake.biz/pos/api/  (base: https://pos.pages.fm/api/v1)

Cách dùng nhanh:
  python3 pancake_order.py cuahang                 # liệt kê cửa hàng (lấy SHOP_ID)
  python3 pancake_order.py sp "áo thun"            # tìm sản phẩm / mẫu mã
  python3 pancake_order.py tao                     # tạo đơn (hỏi từng bước)
  python3 pancake_order.py don 12345               # xem đơn hàng
  python3 pancake_order.py trangthai 12345 xacnhan # chuyển trạng thái đơn
  python3 pancake_order.py trangthai               # xem bảng mã trạng thái
  python3 pancake_order.py don-hoi-thoai <conv_id> --sdt 0501234567   # tìm đơn đã có của hội thoại/SĐT (chống trùng)
  python3 pancake_order.py sua 12345 --sdt 0501111111 --note-them "bổ sung SĐT"  # sửa đơn, nối thêm ghi chú

Tạo đơn nhanh 1 dòng (không hỏi):
  python3 pancake_order.py tao --ten "Nguyễn Văn A" --sdt 0901234567 \
      --diachi "12 Nguyễn Trãi, Thanh Xuân, Hà Nội" \
      --sp "gold necklace:2=99" --note "Giao giờ hành chính" --trangthai xacnhan --yes
  # --sp "id:2=99"  -> 2 cái TỔNG 99 AED (1 sản phẩm luôn là 1 dòng, mua 1 tặng 1 = số lượng 2)
  # --sp "id:1@49.5" -> đơn giá 49.5 AED/cái;  --qua "id:1" -> quà tặng KHÁC sản phẩm
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE_URL = "https://pos.pages.fm/api/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Mã trạng thái theo tài liệu chính thức của Pancake POS
STATUSES = [
    (0, "Mới", ["moi", "new"]),
    (17, "Chờ xác nhận", ["choxacnhan", "cho-xac-nhan"]),
    (11, "Chờ hàng", ["chohang"]),
    (12, "Chờ in", ["choin"]),
    (13, "Đã in", ["dain"]),
    (20, "Đã đặt hàng", ["dadathang"]),
    (1, "Đã xác nhận", ["xacnhan", "daxacnhan", "confirm"]),
    (8, "Đang đóng hàng", ["donghang", "dangdonghang"]),
    (9, "Chờ chuyển hàng", ["chochuyen", "chochuyenhang"]),
    (2, "Đã gửi hàng", ["dagui", "gui", "guihang", "daguihang"]),
    (3, "Đã nhận", ["danhan", "nhan"]),
    (16, "Đã thu tiền", ["dathutien", "thutien"]),
    (4, "Đang hoàn", ["danghoan"]),
    (15, "Hoàn một phần", ["hoanmotphan"]),
    (5, "Đã hoàn", ["dahoan"]),
    (6, "Đã hủy", ["huy", "dahuy", "cancel"]),
    (7, "Đã xóa", ["daxoa", "xoa"]),
]
STATUS_BY_CODE = {code: name for code, name, _ in STATUSES}


def load_env():
    """Đọc file .env nằm cùng thư mục với script."""
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
API_KEY = ENV.get("PANCAKE_API_KEY") or os.environ.get("PANCAKE_API_KEY", "")
SHOP_ID = ENV.get("PANCAKE_SHOP_ID") or os.environ.get("PANCAKE_SHOP_ID", "")

# Cấu hình thị trường hiện tại (mặc định UAE; auto_len_don.set_market sẽ đổi)
CURRENCY_SCALE = 100      # Pancake lưu tiền theo đơn vị nhỏ (AED x100; JPY/TWD x1)
CURRENCY_LABEL = "AED"
PROVINCES = None          # [(id, [từ khóa nhận diện])] — None = dùng EMIRATES mặc định
COUNTRY_CODE = "971"


def set_shop(api_key, shop_id, scale=100, label="AED", provinces=None, country_code="971"):
    """Chuyển ngữ cảnh sang shop/thị trường khác (đa thị trường)."""
    global API_KEY, SHOP_ID, CURRENCY_SCALE, CURRENCY_LABEL, PROVINCES, COUNTRY_CODE
    API_KEY, SHOP_ID = api_key, str(shop_id)
    CURRENCY_SCALE, CURRENCY_LABEL = scale, label
    PROVINCES, COUNTRY_CODE = provinces, str(country_code)


def die(msg):
    print(f"\n❌ {msg}")
    sys.exit(1)


def require_key():
    if not API_KEY:
        die(
            "Chưa có API key. Vào Pancake POS: Cài đặt → Nâng cao → Kết nối bên thứ 3 → Webhook/API\n"
            "   Bấm Tạo (Create) ở khung API KEY, rồi dán vào file .env cạnh script này:\n"
            "   PANCAKE_API_KEY=xxxxx"
        )


def require_shop():
    require_key()
    if not SHOP_ID:
        die("Chưa có SHOP_ID. Chạy:  python3 pancake_order.py cuahang\n   rồi thêm PANCAKE_SHOP_ID=... vào file .env")


def api(method, path, params=None, body=None):
    """Gọi API Pancake POS, trả về JSON đã parse."""
    params = dict(params or {})
    params["api_key"] = API_KEY
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params, doseq=True)}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            err = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
        except Exception:
            err = raw[:500]
        die(f"API lỗi {e.code} ({method} {path}):\n{err}")
    except urllib.error.URLError as e:
        die(f"Không kết nối được API: {e.reason}")


def parse_money(s):
    """Nhập số tiền ('99', '99.5', '6,999', '1,299.50') -> đơn vị Pancake lưu (x CURRENCY_SCALE).
    Trả None nếu rỗng."""
    s = str(s or "").strip().lower()
    s = re.sub(r"(aed|dhs|dirhams?|đ|vnd)", "", s).replace(" ", "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)   # 6,999 / 1.299 là dấu hàng nghìn
    elif "." in s and "," in s:
        s = s.replace(",", "")       # 1,299.50
    elif "," in s:
        s = s.replace(",", ".")      # 99,5
    try:
        v = float(s)
    except ValueError:
        die(f"Số tiền không hợp lệ: {s!r}")
    return int(round(v * CURRENCY_SCALE))


def fmt_money(n):
    """n tính theo đơn vị Pancake lưu -> chuỗi tiền dễ đọc theo thị trường hiện tại."""
    if n is None:
        return "-"
    if CURRENCY_SCALE == 1:
        return f"{n:,.0f} {CURRENCY_LABEL}"
    s = f"{n / CURRENCY_SCALE:,.2f}".rstrip("0").rstrip(".")
    return f"{s} {CURRENCY_LABEL}"


def parse_status(s):
    """Nhận '1', 'xacnhan', 'đã xác nhận'... -> mã trạng thái."""
    s = str(s).strip().lower()
    if s.isdigit() and int(s) in STATUS_BY_CODE:
        return int(s)
    key = re.sub(r"[^a-z0-9]", "", strip_accents(s))
    for code, name, aliases in STATUSES:
        if key in aliases or key == re.sub(r"[^a-z0-9]", "", strip_accents(name.lower())):
            return code
    die(f"Không hiểu trạng thái {s!r}. Chạy 'python3 pancake_order.py trangthai' để xem bảng mã.")


def strip_accents(s):
    import unicodedata
    s = str(s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# 7 tiểu vương quốc UAE trong hệ thống geo của Pancake (shop bán hàng UAE)
EMIRATES = [
    ("971_1", ["abu dhabi", "abudhabi", "al ain", "alain"]),
    ("971_3", ["dubai"]),
    ("971_6", ["sharjah"]),
    ("971_2", ["ajman"]),
    ("971_4", ["fujairah"]),
    ("971_5", ["ras al khaimah", "ras alkhaimah", "rak"]),
    ("971_7", ["umm al quwain", "umm alquwain"]),
]


# Tên địa danh trùng chữ thường gặp trong chat — không dùng làm khoá (vẫn nhận bản chữ Ả Rập).
# "anak" = con (Tagalog) nhưng cũng là thị trấn Anak/عنك ở Saudi: tin Botcake "...kapatid, anak..."
# thành địa chỉ đơn #74149 (Luluk Comel, 14/09/2026). 45 ngày Saudi không có đơn thật nào ở Anak.
KHOA_TINH_TRUNG_TU_THUONG = {"anak"}


def detect_emirate(diachi):
    """Tìm tỉnh/bang/tiểu vương quốc xuất hiện muộn nhất trong địa chỉ (thường nằm cuối).
    Dùng bảng PROVINCES của thị trường hiện tại (mặc định: 7 tiểu vương quốc UAE).

    ⚠️ TÊN NGẮN NẰM TRONG TÊN DÀI: 'Mures' là đuôi của 'Maramures', nên khi khách ghi
    'Maramureș' thì rfind('mures') LUÔN trả vị trí lớn hơn rfind('maramures') — lấy theo
    "muộn nhất" là tên ngắn LUÔN thắng, không phải thỉnh thoảng. Đơn Romania #590 bị gán
    tỉnh Mureş trong khi khách ghi Maramureş, lệch 150km, euShipments không tra ra 'Borsa'
    ở Mureş nên đơn đứng luôn (19/08/2026). Cùng kiểu: Iasi/Iasilor, Cluj/Clujana.

    Cách chữa: bỏ mọi mảnh khớp NẰM GỌN bên trong một mảnh khớp khác, rồi mới lấy cái muộn
    nhất trong số còn lại. Giữ nguyên lối so chuỗi con (không đòi ranh giới từ) để những
    trường hợp dính liền như 'Dubailand' -> Dubai vẫn nhận ra được như trước.
    """
    provinces = PROVINCES if PROVINCES else EMIRATES
    t = " " + norm_ascii(diachi) + " "
    khop = []                                   # [(dau, cuoi, pid)]
    for pid, keys in provinces:
        for k in keys:
            if len(k) < 3:
                continue
            if not re.search(r"[a-z]", k):     # chữ Ả Rập/Hán: vẫn khớp chuỗi con (dính tiền tố بـ/الـ)
                pos = t.rfind(k)
                if pos >= 0:
                    khop.append((pos, pos + len(k), pid))
                continue
            if k in KHOA_TINH_TRUNG_TU_THUONG:
                continue
            # Chữ Latin: khoá phải ĐỨNG ĐẦU TỪ (cho dính 'al'/'el': albaha, alkhobar), khoá ≤4 ký tự
            # còn phải ĐỨNG CUỐI TỪ (cho thêm đuôi 'h': Bahah). Bản cũ khớp chuỗi con nên chữ Tagalog
            # thành tỉnh Saudi: 'kinakabahan'/'bahay' -> Al Baha, 'pinanganak' -> Anak — đơn #73762,
            # #74140, #74144 lấy nguyên đoạn chat làm địa chỉ, 2 đơn tự 'Đã xác nhận' (14/09/2026).
            # Đo 30 ngày 11 nước: 5.900 địa chỉ POS không đổi kết quả ca nào; tin khách chỉ gỡ ca nhầm.
            hit = list(re.finditer(r"(?<![a-z])(?:al-?|el-?)?" + re.escape(k)
                                   + (r"h?(?![a-z])" if len(k) <= 4 else ""), t))
            if hit:
                khop.append((hit[-1].start(), hit[-1].end(), pid))
    if not khop:
        return None
    ngoai = [m for m in khop
             if not any(o is not m and o[0] <= m[0] and m[1] <= o[1] and
                        (o[1] - o[0]) > (m[1] - m[0]) for o in khop)]
    return max(ngoai or khop, key=lambda m: m[0])[2]


# Chữ Ả Rập có nhiều cách viết cùng một chữ (أ إ آ ا / ة ه / ى ي) và chữ số riêng.
# Phải quy về một dạng thì tên thành phố khách gõ mới khớp bảng tỉnh.
_AR_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي", "ـ": "",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
})


def norm_ascii(s):
    t = strip_accents(str(s or "")).lower().translate(_AR_MAP)
    return re.sub(r"\s+", " ", t).strip()


def variation_label(v):
    """Ghép tên sản phẩm + thuộc tính mẫu mã cho dễ đọc."""
    product = v.get("product") or {}
    name = product.get("name") or v.get("name") or "(không tên)"
    attrs = ", ".join(f.get("value", "") for f in (v.get("fields") or []) if f.get("value"))
    return f"{name} ({attrs})" if attrs else name


# ---------------- Các lệnh ----------------

def cmd_shops():
    require_key()
    res = api("GET", "/shops")
    shops = res.get("shops") or res.get("data") or []
    if not shops:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    print("\n🏪 Danh sách cửa hàng:")
    for s in shops:
        print(f"  • SHOP_ID: {s.get('id')}  —  {s.get('name')}")
        for p in s.get("pages") or []:
            print(f"      trang: {p.get('name')} ({p.get('platform', '')})")
    print("\n→ Thêm dòng  PANCAKE_SHOP_ID=<id>  vào file .env")


def search_variations(keyword, page_size=15):
    res = api("GET", f"/shops/{SHOP_ID}/products/variations",
              params={"search": keyword, "page_size": page_size})
    return res.get("data") or []


def print_variations(items):
    for i, v in enumerate(items, 1):
        price = fmt_money(v.get("retail_price"))
        stock = v.get("remain_quantity")
        print(f"  {i:>2}. {variation_label(v)}  |  giá {price}  |  tồn {stock}  |  mã {v.get('display_id') or v.get('id')}")


def cmd_products(keyword):
    require_shop()
    items = search_variations(keyword)
    if not items:
        print(f"Không tìm thấy sản phẩm nào khớp: {keyword!r}")
        return
    print(f"\n🔎 Kết quả cho {keyword!r}:")
    print_variations(items)


def pick_items_interactive():
    """Vòng lặp tìm & chọn sản phẩm."""
    chosen = []
    while True:
        keyword = input("\n🔎 Tìm sản phẩm (tên/mã/barcode): ").strip()
        if not keyword:
            if chosen:
                break
            print("Cần ít nhất 1 sản phẩm.")
            continue
        items = search_variations(keyword)
        if not items:
            print("Không tìm thấy, thử từ khóa khác.")
            continue
        print_variations(items)
        pick = input("Chọn số thứ tự (Enter để tìm lại): ").strip()
        if not pick.isdigit() or not (1 <= int(pick) <= len(items)):
            continue
        v = items[int(pick) - 1]
        qty = input("Số lượng [1]: ").strip()
        qty = int(qty) if qty.isdigit() and int(qty) > 0 else 1
        total = parse_money(input(f"TỔNG tiền dòng này cho {qty} sản phẩm (AED, Enter = giá mặc định): "))
        chosen.append({"variation": v, "quantity": qty, "unit_fils": None, "total_fils": total, "bonus": False})
        print(f"  ✔ Đã thêm: {variation_label(v)} x{qty}")
        more = input("Thêm sản phẩm nữa? (y/N): ").strip().lower()
        if more not in ("y", "yes", "co", "có"):
            break
    return chosen


def resolve_item_spec(spec, bonus=False):
    """'kw:2@49.5' = 2 cái, ĐƠN GIÁ 49.5 AED/cái. 'kw:2=99' = 2 cái, TỔNG DÒNG 99 AED.
    bonus=True: hàng tặng kèm (giá 0)."""
    unit_fils = total_fils = None
    if "@" in spec:
        spec, x = spec.rsplit("@", 1)
        unit_fils = parse_money(x)
    elif "=" in spec:
        spec, x = spec.rsplit("=", 1)
        total_fils = parse_money(x)
    if ":" in spec:
        keyword, qty_s = spec.rsplit(":", 1)
        qty = int(qty_s) if qty_s.strip().isdigit() else 1
    else:
        keyword, qty = spec, 1
    keyword = keyword.strip()
    # Nếu trông giống UUID thì dùng thẳng làm variation_id
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", keyword.lower()):
        return {"variation": {"id": keyword}, "quantity": qty, "unit_fils": unit_fils, "total_fils": total_fils, "bonus": bonus}
    items = search_variations(keyword)
    if not items:
        die(f"Không tìm thấy sản phẩm: {keyword!r}")
    if len(items) > 1:
        # Khớp chính xác display_id/barcode thì chọn luôn
        exact = [v for v in items if keyword.lower() in (str(v.get("display_id", "")).lower(), str(v.get("barcode", "")).lower())]
        if len(exact) == 1:
            return {"variation": exact[0], "quantity": qty, "unit_fils": unit_fils, "total_fils": total_fils, "bonus": bonus}
        print(f"\n⚠ Từ khóa {keyword!r} khớp {len(items)} mẫu mã — hãy dùng từ khóa/mã cụ thể hơn:")
        print_variations(items)
        sys.exit(1)
    return {"variation": items[0], "quantity": qty, "unit_fils": unit_fils, "total_fils": total_fils, "bonus": bonus}


def merge_chosen(chosen):
    """Gộp các lựa chọn theo mẫu mã: 1 sản phẩm CHỈ 1 dòng trên đơn.
    Khách lấy 2 (kể cả mua 1 tặng 1) -> 1 dòng số lượng 2, đơn giá = tổng dòng / số lượng."""
    merged, order_keys = {}, []
    for it in chosen:
        vid = it["variation"]["id"]
        if vid not in merged:
            merged[vid] = {"variation": it["variation"], "quantity": 0, "total_fils": 0, "has_paid": False}
            order_keys.append(vid)
        m = merged[vid]
        q = it["quantity"]
        m["quantity"] += q
        if not it.get("bonus"):
            m["has_paid"] = True
            if it.get("total_fils") is not None:
                m["total_fils"] += it["total_fils"]
            elif it.get("unit_fils") is not None:
                m["total_fils"] += it["unit_fils"] * q
            else:
                m["total_fils"] += (it["variation"].get("retail_price") or 0) * q
    out = []
    for vid in order_keys:
        m = merged[vid]
        m["bonus"] = not m["has_paid"]
        m["unit_fils"] = int(round(m["total_fils"] / m["quantity"])) if m["quantity"] else 0
        m["variation_id"] = vid
        out.append(m)
    return out


def items_payload(chosen):
    out = []
    for m in merge_chosen(chosen):
        item = {"variation_id": m["variation_id"], "quantity": m["quantity"],
                "variation_info": {"retail_price": m["unit_fils"]}}
        if m["bonus"]:
            item["is_bonus_product"] = True
        out.append(item)
    return out


def build_order_body(ten, sdt, diachi, chosen, cod, ship, note, free_ship):
    body = {
        "shop_id": int(SHOP_ID),
        "bill_full_name": ten,
        "bill_phone_number": sdt,
        "shipping_address": {
            "full_name": ten,
            "phone_number": sdt,
            # Để trống province_id: Pancake tự phân tích địa chỉ chữ thành tỉnh/quận/phường
            "address": diachi,
        },
        "items": items_payload(chosen),
    }
    if diachi:
        em = detect_emirate(diachi)
        if em:
            body["shipping_address"]["province_id"] = em
            body["shipping_address"]["country_code"] = COUNTRY_CODE
    if cod is not None:
        body["cod"] = cod
    if ship is not None:
        body["shipping_fee"] = ship
    if free_ship:
        body["is_free_shipping"] = True
    if note:
        body["note"] = note
    return body


def preview_order(ten, sdt, diachi, chosen, cod, ship, note, status_code):
    print("\n" + "=" * 52)
    print("📋 XEM LẠI ĐƠN HÀNG")
    print("=" * 52)
    print(f"  Khách hàng : {ten}")
    print(f"  SĐT        : {sdt}")
    print(f"  Địa chỉ    : {diachi}")
    total = 0
    print("  Sản phẩm   :")
    for m in merge_chosen(chosen):
        line = f"    - {variation_label(m['variation'])} x{m['quantity']}"
        if m["bonus"]:
            line += " (tặng kèm)"
        else:
            line += f" @ {fmt_money(m['unit_fils'])} = {fmt_money(m['unit_fils'] * m['quantity'])}"
            total += m["unit_fils"] * m["quantity"]
        print(line)
    if total:
        print(f"  Tiền hàng  : {fmt_money(total)}")
    print(f"  Phí ship   : {fmt_money(ship) if ship is not None else 'theo cài đặt shop'}")
    print(f"  COD thu hộ : {fmt_money(cod) if cod is not None else 'hệ thống tự tính'}")
    if note:
        print(f"  Ghi chú    : {note}")
    if status_code is not None:
        print(f"  Trạng thái : {STATUS_BY_CODE[status_code]} (sau khi tạo)")
    print("=" * 52)


def cmd_create(args):
    require_shop()
    # Đọc tham số 1 dòng
    opts = {"sp": [], "qua": []}
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--ten", "--sdt", "--diachi", "--cod", "--ship", "--note", "--trangthai", "--conv", "--page"):
            opts[a[2:]] = args[i + 1]; i += 2
        elif a == "--sp":
            opts["sp"].append(args[i + 1]); i += 2
        elif a == "--qua":
            opts["qua"].append(args[i + 1]); i += 2
        elif a == "--freeship":
            opts["freeship"] = True; i += 1
        elif a == "--yes":
            opts["yes"] = True; i += 1
        else:
            die(f"Tham số không hiểu: {a}")

    # Có --ten là chế độ 1 dòng (cho phép tạo đơn thiếu SĐT/sản phẩm — dùng cho đơn tự động)
    interactive = "ten" not in opts

    if interactive:
        print("\n🧾 TẠO ĐƠN HÀNG MỚI (Enter để bỏ qua mục không bắt buộc)")
        ten = input("Tên khách hàng: ").strip()
        while not ten:
            ten = input("Tên khách hàng (bắt buộc): ").strip()
        sdt = input("Số điện thoại: ").strip()
        while not sdt:
            sdt = input("Số điện thoại (bắt buộc): ").strip()
        diachi = input("Địa chỉ đầy đủ (số nhà, đường, phường/xã, quận/huyện, tỉnh/TP): ").strip()
        chosen = pick_items_interactive()
        cod = parse_money(input("Tiền COD thu hộ (Enter = hệ thống tự tính): "))
        ship = parse_money(input("Phí ship (Enter = theo cài đặt): "))
        note = input("Ghi chú: ").strip()
        st = input("Trạng thái sau khi tạo (Enter = Mới, ví dụ: xacnhan): ").strip()
        status_code = parse_status(st) if st else None
        free_ship = False
    else:
        ten = opts.get("ten") or die("Thiếu --ten")
        sdt = opts.get("sdt", "")
        diachi = opts.get("diachi", "")
        chosen = [resolve_item_spec(s) for s in opts["sp"]] + \
                 [resolve_item_spec(s, bonus=True) for s in opts["qua"]]
        cod = parse_money(opts.get("cod"))
        ship = parse_money(opts.get("ship"))
        note = opts.get("note", "")
        status_code = parse_status(opts["trangthai"]) if opts.get("trangthai") else None
        free_ship = bool(opts.get("freeship"))

    conv_id = opts.get("conv")
    page_id = opts.get("page")

    preview_order(ten, sdt, diachi, chosen, cod, ship, note, status_code)

    if not opts.get("yes"):
        ok = input("\n▶ Xác nhận TẠO ĐƠN? (y/N): ").strip().lower()
        if ok not in ("y", "yes", "co", "có"):
            print("Đã hủy, không tạo đơn.")
            return

    body = build_order_body(ten, sdt, diachi, chosen, cod, ship, note, free_ship)
    if conv_id:
        body["conversation_id"] = conv_id
    if page_id:
        body["page_id"] = str(page_id)
    res = api("POST", f"/shops/{SHOP_ID}/orders", body=body)
    order = res.get("data") if isinstance(res.get("data"), dict) else res
    oid = order.get("id")
    if not oid:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        die("Không đọc được mã đơn từ phản hồi API (xem chi tiết ở trên).")

    print(f"\n✅ ĐÃ TẠO ĐƠN #{order.get('display_id') or oid}  (id hệ thống: {oid})")
    if order.get("money_to_collect") is not None:
        print(f"   Tiền phải thu (COD): {fmt_money(order.get('money_to_collect'))}")
    print(f"   Trạng thái hiện tại: {STATUS_BY_CODE.get(order.get('status'), order.get('status'))}")
    if order.get("link"):
        print(f"   Link: {order['link']}")

    # Chuyển trạng thái sau khi tạo nếu được yêu cầu
    if status_code is not None and order.get("status") != status_code:
        api("PUT", f"/shops/{SHOP_ID}/orders/{oid}", body={"status": status_code})
        print(f"   ↪ Đã chuyển trạng thái sang: {STATUS_BY_CODE[status_code]}")


def order_brief(o, ly_do):
    items = []
    for it in o.get("items") or []:
        vi = it.get("variation_info") or {}
        items.append({"ten": vi.get("name") or it.get("variation_id"), "so_luong": it.get("quantity")})
    return {
        "id": o.get("id"),
        "ma_don": o.get("display_id"),
        "ly_do_khop": ly_do,
        "trang_thai": STATUS_BY_CODE.get(o.get("status"), o.get("status")),
        "khach": o.get("bill_full_name"),
        "sdt": o.get("bill_phone_number"),
        "cod_aed": (o.get("cod") / 100) if o.get("cod") is not None else None,
        "tong_phai_thu_aed": (o.get("money_to_collect") / 100) if o.get("money_to_collect") is not None else None,
        "san_pham": items,
        "ghi_chu": o.get("note"),
        "conversation_id": o.get("conversation_id"),
        "tao_luc": o.get("inserted_at"),
    }


def fetch_orders(params):
    res = api("GET", f"/shops/{SHOP_ID}/orders", params=params)
    return res.get("data") or []


def cmd_orders_of_conversation(args):
    """don-hoi-thoai <conversation_id> [--sdt <phone>] [--ngay N]
    Tìm đơn đã tồn tại của hội thoại (kể cả đơn sale tạo tay) để tránh tạo trùng."""
    if not args:
        die("Dùng: don-hoi-thoai <conversation_id> [--sdt <SĐT>] [--ngay 14]")
    require_shop()
    conv_id = args[0]
    phone = args[args.index("--sdt") + 1] if "--sdt" in args else None
    days = int(args[args.index("--ngay") + 1]) if "--ngay" in args else 14
    now = int(time.time())
    common = {"startDateTime": now - days * 86400, "endDateTime": now, "page_size": 100}

    found = {}
    for page in (1, 2, 3):  # quét tối đa 300 đơn gần nhất theo hội thoại
        data = fetch_orders({**common, "page_number": page})
        for o in data:
            if str(o.get("conversation_id") or "") == str(conv_id):
                found[o.get("id")] = order_brief(o, "cùng hội thoại")
        if len(data) < 100:
            break
    if phone:  # đơn cùng SĐT (sale có thể tạo tay không gắn hội thoại)
        for o in fetch_orders({**common, "page_number": 1, "search": phone}):
            if o.get("id") not in found:
                found[o.get("id")] = order_brief(o, "cùng SĐT")

    print(json.dumps({"tim_thay": len(found), "don": list(found.values())}, ensure_ascii=False, indent=2))


def cmd_edit(args):
    """sua <ORDER_ID> [--ten] [--sdt] [--diachi] [--sp kw:qty ...] [--cod] [--ship] [--trangthai] [--note-them "..."]
    Chỉ gửi các trường được truyền; --note-them NỐI THÊM vào ghi chú nội bộ (không ghi đè)."""
    if not args:
        die("Dùng: sua <ORDER_ID> [--sdt ...] [--diachi ...] [--cod ...] [--note-them \"...\"]")
    require_shop()
    oid = args[0]
    opts = {"sp": [], "qua": []}
    i = 1
    while i < len(args):
        a = args[i]
        if a in ("--ten", "--sdt", "--diachi", "--cod", "--ship", "--trangthai", "--note-them"):
            opts[a[2:]] = args[i + 1]; i += 2
        elif a == "--sp":
            opts["sp"].append(args[i + 1]); i += 2
        elif a == "--qua":
            opts["qua"].append(args[i + 1]); i += 2
        else:
            die(f"Tham số không hiểu: {a}")

    res = api("GET", f"/shops/{SHOP_ID}/orders/{oid}")
    order = res.get("data") if isinstance(res.get("data"), dict) else res
    if not order.get("id"):
        die(f"Không tìm thấy đơn {oid}")

    body = {}
    ten, sdt, diachi = opts.get("ten"), opts.get("sdt"), opts.get("diachi")
    if ten:
        body["bill_full_name"] = ten
    if sdt:
        body["bill_phone_number"] = sdt
    if diachi:
        # Địa chỉ mới dạng chữ: để trống province_id cho POS tự phân tích lại
        old = order.get("shipping_address") or {}
        body["shipping_address"] = {
            "full_name": ten or old.get("full_name") or order.get("bill_full_name"),
            "phone_number": sdt or old.get("phone_number") or order.get("bill_phone_number"),
            "address": diachi,
        }
        em = detect_emirate(diachi)
        if em:
            body["shipping_address"]["province_id"] = em
            body["shipping_address"]["country_code"] = COUNTRY_CODE
    elif ten or sdt:
        addr = dict(order.get("shipping_address") or {})
        if ten:
            addr["full_name"] = ten
        if sdt:
            addr["phone_number"] = sdt
        if addr:
            body["shipping_address"] = addr
    if opts.get("cod") is not None:
        body["cod"] = parse_money(opts["cod"])
    if opts.get("ship") is not None:
        body["shipping_fee"] = parse_money(opts["ship"])
    if ("shipping_address" in body and "shipping_fee" not in body
            and (order.get("shipping_fee") or 0)):
        # POS xóa phí chuyển về 0 mỗi khi ghi lại ô địa chỉ -> phải gửi kèm phí cũ,
        # không thì đơn thành giao-không-thu-tiền (quy ước shop: tiền thu nằm ở phí).
        body["shipping_fee"] = order["shipping_fee"]
    if opts["sp"] or opts["qua"]:
        chosen = [resolve_item_spec(s) for s in opts["sp"]] + \
                 [resolve_item_spec(s, bonus=True) for s in opts["qua"]]
        body["items"] = items_payload(chosen)
        print("⚠ Danh sách sản phẩm của đơn sẽ bị THAY TOÀN BỘ bằng danh sách mới.")
    if opts.get("note-them"):
        body["note"] = ((order.get("note") or "").strip() + "\n" + opts["note-them"]).strip()
    if opts.get("trangthai"):
        body["status"] = parse_status(opts["trangthai"])

    if not body:
        die("Không có gì để sửa — truyền ít nhất 1 trường.")
    api("PUT", f"/shops/{SHOP_ID}/orders/{oid}", body=body)
    print(f"✅ Đã cập nhật đơn #{order.get('display_id') or oid}: " + ", ".join(body.keys()))


def cmd_status(args):
    if not args:
        print("\n📌 Bảng mã trạng thái Pancake POS:")
        for code, name, aliases in STATUSES:
            print(f"  {code:>3}  {name:<16}  (gõ tắt: {aliases[0]})")
        print("\nDùng:  python3 pancake_order.py trangthai <MÃ ĐƠN> <trạng thái>")
        return
    if len(args) < 2:
        die("Dùng:  python3 pancake_order.py trangthai <MÃ ĐƠN> <trạng thái>")
    require_shop()
    oid, st = args[0], parse_status(args[1])
    api("PUT", f"/shops/{SHOP_ID}/orders/{oid}", body={"status": st})
    print(f"✅ Đơn {oid} → {STATUS_BY_CODE[st]}")


def cmd_get_order(oid):
    require_shop()
    res = api("GET", f"/shops/{SHOP_ID}/orders/{oid}")
    order = res.get("data") if isinstance(res.get("data"), dict) else res
    print(f"\n🧾 Đơn #{order.get('display_id') or oid}")
    print(f"  Trạng thái : {STATUS_BY_CODE.get(order.get('status'), order.get('status'))}")
    print(f"  Khách      : {order.get('bill_full_name')}  —  {order.get('bill_phone_number')}")
    addr = (order.get("shipping_address") or {}).get("full_address") or (order.get("shipping_address") or {}).get("address")
    print(f"  Địa chỉ    : {addr}")
    for it in order.get("items") or []:
        vi = (it.get("variation_info") or {})
        name = vi.get("name") or it.get("variation_id")
        print(f"  SP         : {name} x{it.get('quantity')}")
    print(f"  COD        : {fmt_money(order.get('money_to_collect') or order.get('cod'))}")
    if order.get("note"):
        print(f"  Ghi chú    : {order.get('note')}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1].lower(), sys.argv[2:]
    if cmd in ("cuahang", "shops"):
        cmd_shops()
    elif cmd in ("sp", "sanpham"):
        if not args:
            die("Dùng:  python3 pancake_order.py sp \"từ khóa\"")
        cmd_products(" ".join(args))
    elif cmd == "tao":
        cmd_create(args)
    elif cmd == "trangthai":
        cmd_status(args)
    elif cmd == "don-hoi-thoai":
        cmd_orders_of_conversation(args)
    elif cmd == "sua":
        cmd_edit(args)
    elif cmd == "don":
        if not args:
            die("Dùng:  python3 pancake_order.py don <MÃ ĐƠN>")
        cmd_get_order(args[0])
    else:
        print(__doc__)
        die(f"Lệnh không hiểu: {cmd}")


if __name__ == "__main__":
    main()

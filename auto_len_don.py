#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TỰ ĐỘNG LÊN ĐƠN TỪ HỘI THOẠI — bản server ĐA THỊ TRƯỜNG, thuần luật, KHÔNG cần AI.

Các thị trường cấu hình trong markets.json (11 thị trường: UAE, Saudi, Kuwait, Qatar,
Oman, Bahrain, Đài Loan, Nhật, Mỹ, Tây Ban Nha, Romania). Mỗi thị trường tự động dùng
đúng: API key + shop, tiền tệ (Nhật/Đài Loan x1, còn lại x100), định dạng SĐT,
bảng tỉnh/bang (tự tải từ Pancake), và bảng sản phẩm tự học riêng.

Quy trình mỗi vòng (từng thị trường):
  0. Kết nạp page mới (1 lần/giờ): tạo page token + chốt SKU + đọc bảng giá->số lượng
     từ lời chào hàng của bot — xem ket_nap_page.py
  1. Quét hội thoại có tag "Lên đơn"  2. Trích thông tin bằng luật
  3. Chống trùng (sale đã tạo -> chỉ bổ sung + note)  4. Đủ -> tạo + "Đã xác nhận";
  thiếu -> vẫn tạo, để "Mới" + note  5. Đánh dấu đã xử lý, ghi state/nhat_ky.log
  6. Xử lý luôn ĐƠN LANDING PAGE của thị trường đó (xem don_landing.py)

Lệnh:
  python3 auto_len_don.py thi-truong               # xem danh sách thị trường + trạng thái
  python3 auto_len_don.py setup <thị trường>       # tạo token page + dò tag "Lên đơn" (vd: setup saudi)
  python3 auto_len_don.py setup <thị trường> --force-token --hong  # cấp lại token cho page bị đánh dấu HỎNG
  python3 auto_len_don.py pages <thị trường>       # xem page nào sẵn sàng
  python3 auto_len_don.py hoc-san-pham [thị trường]  # học bảng sản phẩm từ đơn cũ (bỏ trống = tất cả)
  python3 auto_len_don.py ket-nap [thị trường] [--thu]  # kết nạp page mới ngay, không đợi nhịp 1 giờ
  python3 auto_len_don.py bao-cao [thị trường ...]   # báo cáo: page thiếu tag, page chưa chốt SKU
  python3 auto_len_don.py soi <thị trường> "<tên khách>"     # soi vì sao khách chưa lên đơn (chỉ đọc)
  python3 auto_len_don.py lam-lai <thị trường> "<tên khách>" # cho hội thoại bị bỏ sót được quét lại
  python3 auto_len_don.py quet-khong-tag <tt> [--gio 2] [--thu]  # lên đơn KHÔNG cần tag
  python3 auto_len_don.py chay [thị trường] [--thu] [--gio 72]  # chạy 1 vòng
      (--thu = chỉ in, không tạo thật | --gio N = quét bù ngược N giờ, dùng sau khi bật thêm page)
  python3 auto_len_don.py daemon [--giay 30]       # chạy liên tục tất cả thị trường (systemd)
"""

import json
import os
import re
import sys
import time
import unicodedata

import pancake_order as P
import quet_hoi_thoai as Q

BASE_DIR = Q.SCRIPT_DIR
BASE_STATE = os.path.join(BASE_DIR, "state")
MARKETS_FILE = os.path.join(BASE_DIR, "markets.json")
LOG_FILE = os.path.join(BASE_STATE, "nhat_ky.log")

# Từ khóa nhận diện bổ sung cho tỉnh/bang (ngoài tên chuẩn tải từ Pancake)
# Kuwait: khách hay ghi tên KHU thay vì tên tỉnh -> ánh xạ khu phổ biến về đúng tỉnh
ALIAS_THEM = {
    # Bahrain (BANG_KB_2409, ca Yolly Ranara #1063 "Salman Town Budaiya" → thiếu tỉnh, đơn treo "Mới"): danh mục POS chỉ có
    # 4 tỉnh Capital / Muharraq / Northern / Southern, khách ghi tên KHU. Học từ 615 đơn POS sale đã chọn tỉnh (200 ngày tới
    # 24/09): +326 địa chỉ nhận ra, 89 ca đúng cũ giữ nguyên; 27 ca lệch tỉnh sale chọn hầu hết là SALE nhầm ("Juffair,
    # Manama" → Southern, "Al Hidd" → Capital…). Bỏ các khu dữ liệu chia đôi: Sitra, Sanad, A'ali, Salmabad, Jurdab, Zallaq.
    "973_R0000001": ["manama", "gudaibiya", "juffair", "hoora", "adliya", "tubli", "sanabis", "seef", "mahooz",
                     "umm al hassam", "ras rumman", "zinj", "bilad al qadeem", "naim", "salmaniya", "diplomatic area"],
    "973_R0000002": ["hidd", "arad", "busaiteen", "galali", "qalali", "amwaj", "diyar al muharraq", "samaheej", "dair"],
    "973_R0000003": ["hamad town", "saar", "hamala", "janabiya", "janabiyah", "malkiya", "barbar", "diraz", "duraz",
                     "salman town", "madinat salman", "jasra", "maqaba", "budaiya", "budaiyah"],
    "973_R0000004": ["riffa", "isa town", "askar"],
    "971_1": ["abudhabi", "al ain", "alain"],
    "971_5": ["rak"],
    # Saudi: khách vùng Al-Ahsa ghi 'Al Ahsa'/'Alhassa' — danh mục POS gọi vùng này là
    # Hofuf (chính id 966_hofuf đã mang tên Ả Rập الاحساء = Al Ahsa). Không khai thì tầng
    # gần đúng đọc 'al ahsa' thành 'Al Bahah' (r=0.80, cách 900km) hoặc bỏ trống -> treo đơn.
    "966_hofuf": ["al ahsa", "alahsa", "alhassa", "alhasa", "al hasa", "hufuf", "al hufuf"],
    "965_R0000001": ["fahaheel", "mangaf", "mahboula", "abu halifa", "fintas", "sabahiya", "riqqa", "wafra", "egaila"],
    "965_R0000002": ["kuwait city", "capital", "sharq", "shuwaikh", "qibla", "dasma", "bneid al gar", "mirqab"],
    "965_R0000003": ["khaitan", "jleeb", "ardiya", "abbasiya", "rabiya", "farwaniya"],
    "965_R0000004": ["hawally", "salmiya", "salwa", "jabriya", "mishref", "rumaithiya", "bayan", "maidan hawalli"],
    "965_R0000006": ["abu fatira", "qurain", "adan", "sabah al salem", "messila"],
}

# Khách vùng Vịnh rất hay gõ địa chỉ bằng TIẾNG Ả RẬP -> bảng tỉnh của Pancake chỉ có tên
# Latin nên không dò ra, đơn bị treo oan vì "thiếu địa chỉ". Bổ sung tên Ả Rập ở đây.
# (chuẩn hóa أ/إ/آ→ا, ة→ه, ى→ي nằm trong P.norm_ascii nên viết kiểu nào cũng khớp)
# Lưu ý: Pancake có 2 id trùng nghĩa (makkah/mecca, albahah/baha) — chỉ gán tiếng Ả Rập
# cho MỘT id để địa chỉ không bị nhảy qua lại giữa hai tỉnh.
ALIAS_AR = {
    # ---- Saudi ----
    "966_riyadh": ["الرياض"], "966_jeddah": ["جدة"], "966_makkah": ["مكة", "مكة المكرمة"],
    "966_madina": ["المدينة", "المدينة المنورة"], "966_dammam": ["الدمام"], "966_khobar": ["الخبر"],
    "966_qatif": ["القطيف"], "966_jubail": ["الجبيل"], "966_dhahran": ["الظهران"],
    "966_hofuf": ["الهفوف", "الأحساء"], "966_mubarraz": ["المبرز"], "966_taif": ["الطائف"],
    "966_tabuk": ["تبوك"], "966_buraydah": ["بريدة"], "966_unayzah": ["عنيزة"],
    "966_hail": ["حائل"], "966_abha": ["أبها"], "966_khamismushait": ["خميس مشيط"],
    "966_najran": ["نجران"], "966_jazan": ["جازان"], "966_sabya": ["صبيا"],
    "966_samtah": ["صامطة"], "966_abuarish": ["أبو عريش"], "966_albahah": ["الباحة"],
    "966_arar": ["عرعر"], "966_sakaka": ["سكاكا"], "966_qurayyat": ["القريات"],
    "966_hafaralbatin": ["حفر الباطن"], "966_khafji": ["الخفجي"], "966_rastanura": ["رأس تنورة"],
    "966_safwa": ["صفوى"], "966_saihat": ["سيهات"], "966_tarout": ["تاروت"], "966_anak": ["عنك"],
    "966_buqayq": ["بقيق"], "966_alkharj": ["الخرج"], "966_addiriyah": ["الدرعية"],
    "966_almajmaah": ["المجمعة"], "966_alduwadimi": ["الدوادمي"], "966_zulfi": ["الزلفي"],
    "966_afif": ["عفيف"], "966_arrass": ["الرس"], "966_albadayea": ["البدائع"],
    "966_bukayriyah": ["البكيرية"], "966_almithnab": ["المذنب"], "966_muzahimiyah": ["المزاحمية"],
    "966_hotatbanitamim": ["حوطة بني تميم"], "966_wadialdawasir": ["وادي الدواسر"],
    "966_sulayyil": ["السليل"], "966_sharurah": ["شرورة"], "966_bisha": ["بيشة"],
    "966_tathleeth": ["تثليث"], "966_namas": ["النماص"], "966_tnuma": ["تنومة"],
    "966_mahayelaseer": ["محايل عسير", "محايل"], "966_asir": ["عسير"], "966_turbah": ["تربة"],
    "966_rabigh": ["رابغ"], "966_khulais": ["خليص"], "966_thuwal": ["ثول"], "966_yanbu": ["ينبع"],
    "966_alqunfudhah": ["القنفذة"], "966_wajah": ["الوجه"], "966_diba": ["ضباء"],
    "966_taima": ["تيماء"], "966_khaibar": ["خيبر"], "966_tareef": ["طريف"], "966_rafha": ["رفحاء"],
    "966_dawmataljandal": ["دومة الجندل"], "966_aloyun": ["العيون"], "966_artawiyah": ["الأرطاوية"],
    "966_dhahransouth": ["ظهران الجنوب"], "966_eastern_province": ["المنطقة الشرقية"],
    # ---- UAE ----
    "971_1": ["أبوظبي", "أبو ظبي", "العين"], "971_2": ["عجمان"], "971_3": ["دبي"],
    "971_4": ["الفجيرة"], "971_5": ["رأس الخيمة"], "971_6": ["الشارقة"], "971_7": ["أم القيوين"],
    # ---- Kuwait ----
    "965_R0000001": ["الأحمدي", "الفحيحيل"], "965_R0000002": ["العاصمة", "مدينة الكويت"],
    "965_R0000003": ["الفروانية"], "965_R0000004": ["حولي", "السالمية"],
    "965_R0000005": ["الجهراء"], "965_R0000006": ["مبارك الكبير"],
    # ---- Qatar ----
    "974_R0000006": ["الدوحة"], "974_R0000005": ["الظعاين"], "974_R0000002": ["الخور"],
    "974_R0000007": ["الريان"], "974_R0000003": ["الشحانية"], "974_R0000001": ["الشمال"],
    "974_R0000008": ["الوكرة"], "974_R0000004": ["أم صلال"],
    # ---- Oman ----
    "968_R0000010": ["مسقط"], "968_R0000009": ["ظفار", "صلالة"], "968_R0000001": ["الداخلية", "نزوى"],
    "968_R0000002": ["الظاهرة"], "968_R0000003": ["شمال الباطنة", "صحار"],
    "968_R0000004": ["جنوب الباطنة"], "968_R0000005": ["البريمي"], "968_R0000006": ["الوسطى"],
    "968_R0000007": ["شمال الشرقية"], "968_R0000008": ["جنوب الشرقية", "صور"],
    "968_R0000011": ["مسندم"],
    # ---- Bahrain ----
    "973_R0000001": ["العاصمة", "المنامة"], "973_R0000002": ["المحرق"],
    "973_R0000003": ["الشمالية"], "973_R0000004": ["الجنوبية"],
}

# Trạng thái thị trường hiện tại (set_market gán)
MK = None            # dict cấu hình thị trường hiện tại
PHONE_RE = None
PRICE_RES = []
PRODUCTS_FILE = ATTEMPTS_FILE = None


def load_markets():
    with open(MARKETS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


MARKETS = load_markets()


def log(msg):
    prefix = f"[{MK['ten']}] " if MK else ""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {prefix}{msg}"
    print(line)
    os.makedirs(BASE_STATE, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _migrate_legacy_uae(state_dir):
    """Bản cũ 1 thị trường lưu state phẳng — tự chuyển vào state/uae/ (giữ da_xu_ly chống trùng)."""
    legacy = ["page_tokens.json", "da_xu_ly.json", "pending.json", "meta.json",
              "page_products.json", "attempts.json", "provinces.json"]
    os.makedirs(state_dir, exist_ok=True)
    moved = []
    for name in legacy:
        old, new = os.path.join(BASE_STATE, name), os.path.join(state_dir, name)
        if os.path.exists(old) and not os.path.exists(new):
            os.rename(old, new)
            moved.append(name)
    if moved:
        log(f"Đã chuyển state bản cũ vào state/uae/: {', '.join(moved)}")


def load_provinces(mkey, m):
    """Tải bảng tỉnh/bang của thị trường từ Pancake (cache lại).

    Danh mục POS hay ghi kèm tên gọi khác trong ngoặc hoặc sau gạch chéo — Qatar ghi
    thủ đô là 'Ad Dawhah (Doha)' trong khi khách chỉ gõ 'Doha', thế là cả đơn nằm lại
    'Mới' vì THIẾU TỈNH/THÀNH (đơn #6090, #6093, #6094...). Nên tách từng mảnh thành
    bí danh riêng, giống cách bang_quan_huyen() đã làm cho cấp quận/huyện.
    """
    cache = os.path.join(BASE_STATE, mkey, "provinces.json")
    data = Q.load_json(cache, None)
    if data is None:
        res, err = Q.http_json("GET", "https://pos.pages.fm/api/v1/geo/provinces",
                               {"api_key": m["api_key"], "country_code": m["country_code"]})
        data = (res or {}).get("data") or []
        if data:
            Q.save_json(cache, data)
        elif err:
            log(f"⚠ Không tải được bảng tỉnh ({err}) — địa chỉ sẽ khó nhận diện")
    provinces = []
    for p in data or []:
        keys = set()
        for name in (p.get("name"), p.get("name_en")):
            if not name:
                continue
            keys.add(P.norm_ascii(name))       # vẫn giữ nguyên văn 'ad dawhah (doha)'
            for phan in re.split(r"[/(),]", name):
                keys.add(P.norm_ascii(phan))   # + 'ad dawhah' và 'doha' đứng riêng
        pid = str(p.get("id"))
        for alias in ALIAS_THEM.get(pid, []) + ALIAS_AR.get(pid, []):
            keys.add(P.norm_ascii(alias))     # chuẩn hóa để tên Ả Rập khớp mọi cách viết
        provinces.append((pid, [k for k in keys if len(k) >= 3]))
    return provinces


def set_market(mkey):
    """Chuyển toàn bộ hệ thống sang ngữ cảnh 1 thị trường."""
    global MK, PHONE_RE, PRICE_RES, PRODUCTS_FILE, ATTEMPTS_FILE
    m = MARKETS.get(mkey)
    if not m:
        raise SystemExit(f"Không có thị trường {mkey!r}. Có: {', '.join(MARKETS)}")
    MK = dict(m, key=mkey)
    state_dir = os.path.join(BASE_STATE, mkey)
    if mkey == "uae":
        _migrate_legacy_uae(state_dir)
    Q.set_state_dir(state_dir)
    Q.set_pos(m["api_key"], m["shop_id"])
    provinces = load_provinces(mkey, m)
    P.set_shop(m["api_key"], m["shop_id"], scale=m.get("scale", 100),
               label=m.get("tien_te", ""), provinces=provinces or None,
               country_code=m["country_code"])
    PHONE_RE = re.compile(m["sdt_regex"])
    words = m.get("tu_tien_te") or ""
    PRICE_RES = [re.compile(
        r"(?:order|total|cod|amount|price|合計|総額|注文|總共|共)\D{0,20}?(\d[\d.,]*)\s*(?:" + words + ")", re.I)]
    if m.get("ky_hieu_truoc"):
        PRICE_RES.append(re.compile(
            r"(?:order|total|cod|amount|price|合計|総額|注文|總共|共)\D{0,20}?(?:" + m["ky_hieu_truoc"] + r")\s*(\d[\d.,]*)", re.I))
    PRODUCTS_FILE = os.path.join(state_dir, "page_products.json")
    ATTEMPTS_FILE = os.path.join(state_dir, "attempts.json")
    return m


def enabled_markets():
    return [k for k, m in MARKETS.items() if m.get("bat", True)]


# ---------------- Học bảng sản phẩm từ đơn cũ ----------------

def hoc_san_pham(days=45, max_pages=8):
    """Quét đơn cũ trong POS thị trường hiện tại, học cho từng page:
    sản phẩm chính, tiền thu -> số lượng, có kèm hộp không, và danh sách mẫu mã."""
    now = int(time.time())
    hop_id = MK.get("hop_id")
    table = {}
    for pg in range(1, max_pages + 1):
        try:
            data = P.fetch_orders({"startDateTime": now - days * 86400, "endDateTime": now,
                                   "page_size": 100, "page_number": pg})
        except (SystemExit, Exception) as e:  # noqa: BLE001 — lỗi API 1 trang không hủy cả lượt học
            log(f"⚠ Lỗi đọc đơn trang {pg} ({e}) — dùng dữ liệu đã đọc được")
            break
        for o in data:
            page_id = str(o.get("page_id") or "")
            items = o.get("items") or []
            if not page_id or not items:
                continue
            t = table.setdefault(page_id, {"variations": {}, "gia_qty": {}, "co_hop": 0, "tong": 0})
            chinh = [it for it in items if it.get("variation_id") != hop_id]   # hộp không tính là SP
            t["tong"] += 1
            if hop_id and any(it.get("variation_id") == hop_id for it in items):
                t["co_hop"] += 1
            for it in chinh:
                vid = it.get("variation_id")
                if not vid:
                    continue
                vi = it.get("variation_info") or {}
                v = t["variations"].setdefault(vid, {"so_don": 0, "ten": vi.get("name"),
                                                     "product_id": it.get("product_id")})
                v["so_don"] += 1
                if not v.get("product_id"):
                    v["product_id"] = it.get("product_id")
            mtc, qty_chinh = o.get("money_to_collect"), sum(it.get("quantity") or 0 for it in chinh)
            if mtc and qty_chinh:
                g = t["gia_qty"].setdefault(str(mtc), {})
                g[str(qty_chinh)] = g.get(str(qty_chinh), 0) + 1
        if len(data) < 100:
            break
        time.sleep(0.2)

    out, nhieu_mau, bo_test = {}, 0, []
    for page_id, t in table.items():
        # Bỏ hẳn sản phẩm test ra khỏi dữ liệu học — không để nó thành SP chính của page
        sach = {vid: v for vid, v in t["variations"].items() if not la_sp_test(v.get("ten"))}
        if len(sach) < len(t["variations"]):
            bo_test.append(f"{page_id}:" + ",".join(
                str(v.get("ten")) for vid, v in t["variations"].items() if vid not in sach))
        t["variations"] = sach
        if not t["variations"]:
            continue
        vid, vinfo = max(t["variations"].items(), key=lambda kv: kv[1]["so_don"])
        gia_qty = {}
        for gia, qtys in t["gia_qty"].items():
            qty, _ = max(qtys.items(), key=lambda kv: kv[1])
            gia_qty[gia] = int(qty)
        muc = {"variation_id": vid, "ten": vinfo.get("ten"), "so_don": vinfo["so_don"],
               "gia_qty": gia_qty,
               "co_hop": bool(hop_id) and t["co_hop"] * 2 > t["tong"]}   # đa số đơn cũ có hộp
        # Danh sách mẫu mã (để chọn đúng mẫu khách chốt)
        pid_sp = vinfo.get("product_id")
        if pid_sp:
            try:
                r = P.api("GET", f"/shops/{P.SHOP_ID}/products/{pid_sp}")
                d = r.get("data") if isinstance(r.get("data"), dict) else r
                mm = [{"id": v.get("id"), "ten": v.get("display_id")}
                      for v in (d.get("variations") or []) if v.get("id") and v.get("display_id")]
                if len(mm) > 1:
                    muc["mau_ma"] = mm
                    nhieu_mau += 1
            except (SystemExit, Exception):  # noqa: BLE001 — thiếu mẫu mã không chặn việc học
                pass
            time.sleep(0.1)
        out[page_id] = muc
    Q.save_json(PRODUCTS_FILE, out)
    co_hop = sum(1 for v in out.values() if v.get("co_hop"))
    log(f"Học sản phẩm: {len(out)} page ({co_hop} page kèm hộp, {nhieu_mau} page nhiều mẫu mã) — {days} ngày")
    if bo_test:
        log(f"  ⚠ Bỏ qua SP test khi học ({len(bo_test)} page): {'; '.join(bo_test[:5])}")
    return out


# Trang sức -> luôn kèm hộp 008 (quy tắc shop). Nhận diện theo tên sản phẩm,
# cộng thêm những page mà đơn cũ vốn đã kèm hộp.
# "earing"/"siliver" là cách kho gõ sai trong danh mục POS ('003 - Gold Earing',
# '187 - Fengshui Siliver') — không khai thì hai SP này rớt khỏi luật kèm hộp dù đơn
# thật vẫn luôn có hộp (đo 30 ngày: 003 có hộp 11/11 đơn, 187 có hộp 19/28).
TU_TRANG_SUC = ["necklace", "ring", "earring", "earing", "bracelet", "bangle", "jewelry",
                "jewellery", "pendant", "anklet", "charm", "buddha", "stone set", "chain",
                "silver", "siliver"]


def la_trang_suc(ten_sp):
    # 's?' bắt cả dạng số nhiều: '201 - Fengshui Horse Jade Crystal Bracelets' từng KHÔNG
    # khớp \bbracelet\b nên trượt luật kèm hộp, dù 20/21 đơn của nó đều có hộp.
    t = P.norm_ascii(ten_sp)
    return any(re.search(r"\b" + re.escape(k) + r"s?\b", t) for k in TU_TRANG_SUC)


# Đơn TEST của mình lọt vào dữ liệu học -> page tưởng bán "SP TEST".
# Gặp là TREO đơn cho nhân viên check, tuyệt đối không đẩy sản phẩm rác sang vận chuyển.
SP_TEST_RE = re.compile(
    r"\btest\b|\bdemo\b|\bsample\b|\bthu nghiem\b|\bsp test\b|\bdon test\b|"
    r"\bhuy ngay\b|\bxoa di\b|\bxoa don\b|\bkhong giao\b|\bkhong dung\b|\babc\b|\bxxx\b")


def la_sp_test(ten_sp):
    """Tên sản phẩm trông như hàng test/rác? (khớp theo TỪ, nên 'Testosterone' không dính)"""
    return bool(ten_sp) and bool(SP_TEST_RE.search(P.norm_ascii(ten_sp)))


def chon_dvvc(ten_sp, page_id=None):
    """Đơn vị vận chuyển, ưu tiên từ trên xuống:
    (1) LUẬT THEO PAGE `dvvc_theo_page` trong markets.json — chủ shop 24/09/2026: page Madam Mystic
        Fengshui Expert TW (1161512757051326) hàng nằm kho Bình An → đi BÌNH AN EXP thay NAZA (đo POS
        11-24/09: 8 đơn của page đều bị sale đổi tay sau khi tool tạo). `tu_khoa` rỗng = mọi sản phẩm
        của page; có `tu_khoa` thì chỉ sản phẩm khớp. Tra trên MỌI thị trường (page_id là duy nhất)
        để không dính bẫy MK kẹt nước khác khi module bị import thành bản thứ hai trong daemon.
    (2) theo sản phẩm `dvvc_dac_biet` (Mỹ: hàng kho AMI / dropship CJ);
    (3) `dvvc` mặc định của thị trường."""
    t = norm_sp(ten_sp)
    pid = str(page_id or "").strip()
    if pid:
        for m in ([MK] if MK else []) + list(MARKETS.values()):
            for rule in (m or {}).get("dvvc_theo_page") or []:
                if str(rule.get("page_id") or "").strip() != pid:
                    continue
                tk = rule.get("tu_khoa") or []
                if tk and not any(norm_sp(k) in t for k in tk):
                    continue
                return {"id": rule["id"], "ten": rule["ten"]}
    for rule in MK.get("dvvc_dac_biet") or []:
        if any(norm_sp(k) in t for k in rule.get("tu_khoa") or []):
            return {"id": rule["id"], "ten": rule["ten"]}
    return MK.get("dvvc")


def norm_sp(s):
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


# ---------------- Trích xuất bằng luật ----------------

def so_latin(t):
    """Chữ số Ả Rập-Ấn/Ba Tư -> Latin. Bảng nằm ở ho_so (nạp muộn vì vòng import)."""
    import ho_so as HS
    return HS.so_latin(t)


def _van_sdt(t):
    """Chữ để DÒ SĐT: chữ số Latin + nối số khách tách bằng dấu phẩy ("055,9138041") — xem ho_so.noi_phay_sdt.
    Chủ shop 23/09: "bỏ dấu phẩy là dc mà". Phải cùng luật với AI chat, không thì AI chốt bằng số mà đơn không nhận."""
    import ho_so as HS
    t = HS.so_latin(t)
    try:
        return HS.noi_phay_sdt(t, (MK or {}).get("key"))
    except Exception:                                    # noqa: BLE001 — hỏng thì dò như cũ
        return t


def _chuan_hoa_ban_dia(p):
    """Số khách gõ -> dạng chuẩn của thị trường.

    Khách gõ mã nước đủ kiểu: '+971...', '00971...', '0971...', thậm chí '00966 0 5...'.
    Bản cũ CẮT MÃ NƯỚC TRƯỚC rồi mới bỏ số 0 dẫn đầu, nên '00966590338389' không khớp
    tiền tố '966' (đứng sau hai số 0) -> giữ nguyên 13 chữ số -> đơn treo vì "SĐT không
    đúng định dạng" trong khi số hoàn toàn hợp lệ. Nay bóc xen kẽ '0'/mã nước cho tới
    khi hết, nên mọi cách gõ đều về một số.
    """
    d = re.sub(r"\D", "", so_latin(p))
    cc = str(MK["country_code"])
    while True:
        truoc = d
        d = d.lstrip("0")
        # +6: giữ lại phần thân số; số ngắn hơn thế thì '971' đầu là số thật, không phải mã nước
        if d.startswith(cc) and len(d) > len(cc) + 6:
            d = d[len(cc):]
        if d == truoc:
            break
    if MK.get("sdt_them_0") and d:
        d = "0" + d
    return d


# Mã điện thoại của những nước KHÁCH THẬT hay dùng (lao động/du học ở vùng Vịnh, châu Âu).
# Chỉ cần đủ để NHẬN RA số nước ngoài rồi giữ nguyên mã nước — không phải danh bạ 200 nước.
MA_QUOC_TE = {
    "63": "Philippines", "62": "Indonesia", "91": "Ấn Độ", "92": "Pakistan",
    "880": "Bangladesh", "94": "Sri Lanka", "977": "Nepal", "95": "Myanmar",
    "84": "Việt Nam", "66": "Thái Lan", "60": "Malaysia", "86": "Trung Quốc",
    "20": "Ai Cập", "249": "Sudan", "962": "Jordan", "963": "Syria", "964": "Iraq",
    "961": "Lebanon", "967": "Yemen", "970": "Palestine", "212": "Maroc",
    "216": "Tunisia", "213": "Algeria", "90": "Thổ Nhĩ Kỳ", "98": "Iran",
    "93": "Afghanistan", "251": "Ethiopia", "254": "Kenya", "234": "Nigeria",
    "256": "Uganda", "255": "Tanzania", "27": "Nam Phi", "998": "Uzbekistan",
    # 996/960 gần như không có khách thật, để trong bảng là để BẪY GÕ NHẦM bên dưới nhận ra
    # '996…' chính là '966…' gõ lệch 1 phím (ca thật Saudi #69031).
    "996": "Kyrgyzstan", "960": "Maldives",
    "971": "UAE", "966": "Ả Rập Xê Út", "965": "Kuwait", "974": "Qatar",
    "968": "Oman", "973": "Bahrain", "886": "Đài Loan", "81": "Nhật Bản",
    "82": "Hàn Quốc", "34": "Tây Ban Nha", "40": "Romania", "351": "Bồ Đào Nha",
    "44": "Anh", "33": "Pháp", "49": "Đức", "39": "Ý", "31": "Hà Lan", "32": "Bỉ",
    "41": "Thụy Sĩ", "43": "Áo", "353": "Ireland", "48": "Ba Lan", "30": "Hy Lạp",
    "36": "Hungary", "7": "Nga/Kazakhstan", "1": "Mỹ/Canada", "61": "Úc", "64": "New Zealand",
}

_DAI_BAN_DIA = {}


def dai_sdt_ban_dia():
    """Số chữ số của PHẦN THÂN một SĐT hợp lệ ở thị trường này (không tính số 0 dẫn đầu).
    Suy thẳng từ regex trong markets.json — khỏi khai tay 11 nước."""
    key = MK.get("key")
    if key in _DAI_BAN_DIA:
        return _DAI_BAN_DIA[key]
    dai = None
    for tien in ("0", ""):
        for than in range(6, 13):
            for d in "56789234":
                thu = tien + d + "1234567890"[:than]
                if PHONE_RE and PHONE_RE.fullmatch(thu):
                    dai = len(thu) - len(tien)
                    break
            if dai:
                break
        if dai:
            break
    _DAI_BAN_DIA[key] = dai
    return dai


def _lech_mot_chu_so(a, b):
    """Hai mã nước chỉ khác nhau ĐÚNG 1 chữ số? ('996' vs '966', '963' vs '966')"""
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def phan_loai_sdt(goc):
    """Số khách gõ -> ('ban_dia' | 'ngoai' | 'hong', số đã chuẩn hóa, mô tả).

    LUẬT USER (2026-08-23): TRỪ KUWAIT (bắt buộc đúng số Kuwait mới đi được đơn), các
    thị trường còn lại CHẤP NHẬN số nước khác — hay gặp nhất là số Philippines — miễn là
    số đó có WhatsApp để bên vận chuyển liên hệ được. Vì thế số nước ngoài phải GIỮ
    NGUYÊN MÃ NƯỚC ('+63…') chứ không cắt như số bản địa: thiếu mã nước là shipper
    không WhatsApp/gọi được, mà tool thì không có cách nào tự kiểm tra số có WhatsApp hay
    không — việc đó do người chốt đơn bảo đảm.
    """
    goc = so_latin(goc)
    so = re.sub(r"\D", "", str(goc or ""))
    if not so:
        return "hong", "", "đơn không có số điện thoại"

    ban_dia = _chuan_hoa_ban_dia(goc)
    if PHONE_RE and PHONE_RE.fullmatch(ban_dia):
        return "ban_dia", ban_dia, f"số {MK['ten']}"

    # Số Philippines dân Phi gõ theo kiểu bản địa '09171234567' (11 chữ số, mở đầu 09).
    # Xét TRƯỚC vòng dò mã nước, không thì '9171234567' bị đọc thành '91' = Ấn Độ.
    if re.fullmatch(r"09\d{9}", so):
        return "ngoai", "+63" + so[1:], "số Philippines (+63, gõ kiểu bản địa 09…)"

    cc = str(MK["country_code"])
    nhan = so.lstrip("0")
    ro_quoc_te = str(goc).strip().startswith("+") or so.startswith("00")
    than_ban_dia = dai_sdt_ban_dia() or 0
    if nhan.startswith(cc):
        # Mở đầu bằng mã nước của CHÍNH thị trường mà vẫn không hợp lệ = số bản địa gõ
        # sai, đừng thử đọc thành nước khác ('9651643416' không phải số Thụy Sĩ +41).
        return "hong", ban_dia, ""
    if not ro_quoc_te and so.startswith("0"):
        # MỘT số 0 dẫn đầu là TIỀN TỐ GỌI NỘI HẠT, không phải cách viết số quốc tế — quốc tế
        # là '+' hoặc '00', cả hai đã bật ro_quoc_te nên không vướng chốt này. Chuỗi
        # '0' + mã nước + thân số không phải khuôn quay số của nước nào, đọc kiểu đó là GÁN
        # BỪA QUỐC TỊCH: số Pakistan '03365031008' bị đọc thành '+33 65031008' = số Pháp ở
        # thị trường Kuwait (số Pháp thật thân phải 9 chữ số). Số Philippines gõ kiểu bản
        # địa '09…' đã bắt ở trên nên không vướng chốt này.
        # Luật user 2026-08-24: "phải ĐÚNG số" — thà trả 'hong' (landing hủy / Facebook
        # treo) còn hơn đẩy đơn đi bằng một quốc tịch bịa ra và một số không ai bắt máy.
        return "hong", ban_dia, ""
    for n in (3, 2, 1):
        ma = nhan[:n]
        if ma not in MA_QUOC_TE:
            continue
        than = nhan[n:].lstrip("0")
        # Mã 1 chữ số (Mỹ/Canada, Nga) chỉ nhận khi thân số đúng 10 chữ số, không thì
        # số bản địa nào gõ thiếu/thừa cũng bị gán bừa quốc tịch.
        if not ((len(than) == 10) if n == 1 else (7 <= len(than) <= 11)):
            continue
        # Số KHÔNG có dấu '+'/'00' mà chỉ dài bằng số bản địa thì nhiều khả năng là số
        # bản địa lạ dải, không phải số ngoại: '981299245' là ĐIỆN THOẠI BÀN Tây Ban Nha
        # (mã vùng 981 A Coruña) chứ không phải +98 Iran. Phải dài hơn hẳn mới dám đọc.
        if not ro_quoc_te and len(nhan) < than_ban_dia + 2:
            break
        # BẪY GÕ NHẦM MÃ NƯỚC (đo trên đơn thật Saudi #69031 '996506990937' và #69367
        # '09630556838034'): mã lệch đúng 1 chữ số so với mã thị trường MÀ phần sau lại là
        # số bản địa hợp lệ -> gõ nhầm 996/963 thay vì 966. Gắn nhầm cho khách quốc tịch
        # khác là đơn đi sai hãng vận chuyển, nên trả về 'hong' để nhân viên sửa.
        if (_lech_mot_chu_so(ma, cc) and PHONE_RE
                and PHONE_RE.fullmatch(_chuan_hoa_ban_dia(than))):
            return ("hong", ban_dia,
                    f"SĐT {so} nghi GÕ NHẦM mã nước +{ma} (đúng ra là +{cc}) — bỏ mã đi thì "
                    f"{_chuan_hoa_ban_dia(than)} là số {MK['ten']} hợp lệ: nhân viên xác minh rồi sửa")
        return "ngoai", "+" + ma + than, f"số {MA_QUOC_TE[ma]} (+{ma})"
    return "hong", ban_dia, ""


def normalize_phone(p):
    """Dạng chuẩn để LƯU vào đơn: số bản địa giữ khuôn bản địa, số nước ngoài giữ '+mã nước'."""
    return phan_loai_sdt(p)[1]


# Ứng viên "trông như số điện thoại" trong tin nhắn — cố tình rộng, việc lọc để
# phan_loai_sdt làm. Chặn hai đầu bằng ký tự không phải số/dấu phân cách để không cắt
# giữa một dãy số dài (mã vận đơn, giá tiền).
SDT_UNG_VIEN_RE = re.compile(r"(?<![\d/,.])\+?\d[\d\s\-.()]{7,17}\d(?![\d/,.])")


# PH_DIA_CHI_2509 — KHÚC GIỮA MỘT SỐ NƯỚC NGOÀI KHÔNG PHẢI SỐ BẢN ĐỊA (ca War Kins · DOC Alipion-Tooth ARMOR KSA, đơn #77211).
# Khách gõ "#09554756987" (số Philippines 0955…) → PHONE_RE.findall dò trên cả câu bắt khúc "554756987" → đơn mang số SAUDI
# 0554756987 của một người không liên quan. Cùng lỗi ở nước khác: Kuwait "+639211765957" → "63921176", Qatar "09171234567" →
# "71234567", Đài "09171234567" → "0917123456". ho_so.trich (bên chat) đã tách ứng viên trước — bên đơn thì chưa.
# Chỉ BỎ khớp dính liền chữ số khác (trừ '0'/mã nước đứng trước: "00966 5…", "9660 5…") MÀ cả dãy số chứa nó là số NƯỚC
# NGOÀI (phan_loai_sdt); số hỏng / số nhà dính liền thì giữ như cũ.
_R_DAY_SO = re.compile(r"(?<!\d)\+?\d[\d\s.\-()]{6,17}\d(?!\d)")


def _tach_sdt_ban_dia(t):
    """(khớp PHONE_RE giữ lại, các số NƯỚC NGOÀI chứa khúc đã bỏ) — PH_DIA_CHI_2509."""
    t = str(t or "")
    cc = str(MK["country_code"])
    giu, bo = [], []
    for m in PHONE_RE.finditer(t):
        i, j = m.span()
        truoc = re.search(r"\d*$", t[:i]).group(0)
        sau = re.match(r"\d*", t[j:]).group(0)
        if not sau and (not truoc or re.fullmatch(rf"0*(?:{cc})?0*", truoc)):
            giu.append(m.group(0))
            continue
        a = i - len(truoc)
        if a > 0 and t[a - 1] == "+":
            a -= 1
        het = j + len(sau)
        # Dãy số chứa khớp: khối chữ số dính liền, và dãy có dấu cách/gạch ("+63 955 475 6987") — cắt tại cuối khối số của
        # khớp, kẻo nuốt số nhà phía sau ("#9560819979 11TH ST" → "…979 11" thành số Myanmar).
        khoi = [t[a:het]] + [t[u.start():het] for u in _R_DAY_SO.finditer(t) if u.start() <= i and het <= u.end()]
        ngoai = next((k for k in khoi if phan_loai_sdt(k)[0] == "ngoai"), None)
        if ngoai:
            bo.append(ngoai)
            continue
        giu.append(m.group(0))
    return giu, bo


def _sdt_ban_dia_trong(t):
    """Như PHONE_RE.findall(t), nhưng bỏ khớp chỉ là KHÚC GIỮA của một số nước ngoài dài hơn (PH_DIA_CHI_2509)."""
    return _tach_sdt_ban_dia(t)[0]


# Khách rất hay COPY nguyên cái form của shop rồi điền vào giữa:
#   "Please provide the information below... ✔️Your full name <tên> ✔️Contact number: <sđt>
#    ✔️Complete Address and Emirate: <ĐỊA CHỈ THẬT> For address please make it as detailed..."
# Nếu bê nguyên chuỗi đó vào ô địa chỉ thì đơn ra địa chỉ rác -> phải bóc lấy phần thật.
# Nhãn KHÔNG có dấu ":" thì không đòi ranh giới chữ ở cuối: khách dán mẫu rồi gõ DÍNH liền vào
# nhãn — "✔️Complete Addressprince majed bin abdulaziz road ar rayyan Riyadh" (An Ne, Kreain Nature
# PH - Ksa, 14/09/2026). Bản cũ đòi "address\b" nên không nhận ra nhãn, cả tin (câu mời + tên + nhãn
# SĐT) bị bê nguyên vào ô địa chỉ đơn.
NHAN_DIA_CHI = re.compile(r"(?:complete\s+|full\s+|shipping\s+|delivery\s+)?address[^:\n]{0,25}:|"
                          r"(?:complete\s+|full\s+|shipping\s+|delivery\s+)address"
                          r"(?:\s+and\s+(?:emirates?|city|province|region|state|governorate|area)\b)?", re.I)
NHAN_KHAC = re.compile(r"(?:your\s+)?full\s*name\s*:?|"
                       r"(?:contact|phone|mobile|whatsapp)\s*(?:number|no\.?)?\s*:", re.I)
DUOI_HUONG_DAN = re.compile(r"\bfor\s+address\b|make\s+it\s+as\s+detailed|as\s+detailed\s+as\s+possible|"
                            r"including\s+area\s+name|please\s+provide\s+the\s+information", re.I)
RAC_DAU_DONG = re.compile(r"^[\s\W_]+", re.U)
RAC_CUOI_DONG = re.compile(r"[\s\W_]+$", re.U)
# Tin tán gẫu / chốt deal — tuyệt đối không gộp vào địa chỉ
KHONG_PHAI_DIA_CHI = re.compile(
    r"\b(buy|get|free|gift|promo|discount|price|order|delivery|deliver|pay|cod|"
    r"ok|okay|yes|no|thanks?|thank you|please|sorry|hello|hi|good|when|how|what|"
    r"ma'?am|sir|po|sana|salam|shukran)\b", re.I)


def lam_sach_dia_chi(text):
    """Bóc địa chỉ thật ra khỏi form shop mà khách copy lại. Không phải form thì trả nguyên văn."""
    t = str(text or "")
    nhan = list(NHAN_DIA_CHI.finditer(t))
    if not nhan and not NHAN_KHAC.search(t) and not DUOI_HUONG_DAN.search(t):
        return t                                   # tin nhắn bình thường, không đụng vào
    if nhan:
        t = t[nhan[-1].end():]                     # bỏ mọi thứ trước nhãn "Address:"
    cat = [m.start() for m in (DUOI_HUONG_DAN.search(t), NHAN_KHAC.search(t)) if m]
    if cat:
        t = t[:min(cat)]                           # bỏ phần hướng dẫn / nhãn kế tiếp ở đuôi
    return RAC_CUOI_DONG.sub("", RAC_DAU_DONG.sub("", t))


def chon_dia_chi(text):
    """Làm sạch, nhưng nếu làm sạch mà mất tên tỉnh/bang thì giữ nguyên văn cho an toàn."""
    sach = lam_sach_dia_chi(text)
    if sach and P.detect_emirate(sach):
        return sach
    return text


# ── Tên người nhận khách TỰ ĐƯA (chủ shop 2026-09-14) ─────────────────────────────
# Ca An Ne (Kreain Nature PH - Ksa, đơn #74127): khách dán mẫu "✔️Your full name jhoan palacay ✔️Contact
# number:…" mà đơn vẫn mang tên Facebook "An Ne". Chủ shop: *"nếu khách đưa tên khác fb thì phần tên
# bỏ tên người nhận khách đưa trước - tên fb"* → "Jhoan Palacay - An Ne".
# 23/09 chủ shop ĐỔI THỨ TỰ (ca Cely Kuo, tên đọc từ ảnh): *"tên fb - tên thực ví dụ Cely Kuo - 郭仙莉"* →
# "An Ne - Jhoan Palacay". Chống trùng / đổi tên nháp so theo TẬP CHỮ (_chu_ten) nên đổi thứ tự không ảnh hưởng.
# Giữ nguyên tên Facebook ở đuôi là CỐ Ý: chống đơn trùng tra theo tên FB (_ten_khop_du đòi mọi chữ
# của tên FB có trong tên trên đơn) — bỏ tên FB đi là sale tạo tay xong tool vẫn đẻ thêm đơn.
# CHỈ nhận tên có NHÃN ("full name", "name:", "my name is", "姓名：", "الاسم:"). Không đoán tên từ tin
# trần kiểu "Jon pineda 0551633641 Sharjah…": chữ trước SĐT hay là tên đường/quận, đoán sai là
# đơn giao cho người không tồn tại.
NHAN_TEN = re.compile(
    r"(?:(?<![^\W\d_])(?:your\s+|receiver'?s?\s+|recipient'?s?\s+|customer'?s?\s+)?"
    r"(?:full|complete)\s*name(?:\s+is)?\s*[:：\-–]?"
    r"|(?:^|(?<=[\n✔✓☑✅•*\-]))[\s️]*(?:your\s+)?name\s*[:：\-–]?"
    r"|(?<![^\W\d_])(?:your\s+|receiver'?s?\s+|recipient'?s?\s+)?name\s*[:：]"
    r"|(?<![^\W\d_])(?:receiver|recipient)\s*[:：]"
    r"|(?<![^\W\d_])my\s+name\s+is\b"
    r"|(?:姓名|收件人|收件者)\s*[:：]?"
    r"|(?:الاسم\s+الكامل|الاسم|اسم)\s*[:：]?)", re.I | re.M)
# "Building name: green house", "Account holder name …" — nhãn "name" của thứ khác, không phải người nhận
TRUOC_NHAN_KHAC = re.compile(r"(?:building|bldg|street|road|area|shop|store|company|account|holder|bank|"
                             r"page|product|item|village|compound|tower|hotel|school|mall|hospital|"
                             r"mother'?s?|father'?s?|facebook|fb|user)\s*$", re.I)
# Chữ báo đã sang ô khác → dừng
HET_TEN = re.compile(r"\b(?:contact|phone|mobile|number|whatsapp|tel|address|city|emirate|province|area|"
                     r"location|landmark|and|with|from|in|at|po|ko|ang|na|please|pls|thanks?|order|my|bd|dob|birthday|"
                     r"age|road|rood|rd|street|st|near|building|bldg|villa|vila|flat|apartment|apt|district|"
                     r"old|new|airport|hospital|mall|mosque|tower|compound|house)\b"
                     r"|電話|手機|地址|الهاتف|رقم|العنوان", re.I)
KHONG_PHAI_TEN = re.compile(r"^(?:is|the|below|here|same|as|my|your|ok|okay|yes|no|sir|ma'?am|mam|"
                            r"what|full|name|dear|hello|hi)$", re.I)


def ten_khach_dua(khach_msgs):
    """Tên người nhận khách tự gõ có nhãn, tin MỚI nhất thắng. Không có thì None."""
    for m in reversed(khach_msgs):
        t = m.get("noi_dung") or ""
        for h in NHAN_TEN.finditer(t):               # trong một tin: nhãn tên ĐẦU TIÊN là người nhận
            if TRUOC_NHAN_KHAC.search(t[max(0, h.start() - 25):h.start()]):
                continue
            sau = t[h.end():h.end() + 80]
            cat = re.search(r"[\n\d✔✓☑✅•|,;:：/()\[\]@#+=!?]|[\U0001F000-\U0001FFFF☀-➿]", sau)
            if cat:
                sau = sau[:cat.start()]
            k = HET_TEN.search(sau)
            if k:
                sau = sau[:k.start()]
            chu = [w for w in re.findall(r"[^\W\d_][^\W\d_.'’\-]*(?:[.'’\-][^\W\d_]+)*\.?", sau)][:5]
            while chu and KHONG_PHAI_TEN.match(chu[0]):
                chu.pop(0)
            if not chu:
                continue
            ten = " ".join(chu).strip(" .-")
            if len(re.sub(r"[\W\d_]", "", ten)) < 2 or P.detect_emirate(ten):
                continue
            if ten == ten.lower() and re.search(r"[a-z]", ten):
                ten = ten.title()                     # "jhoan palacay" → "Jhoan Palacay"
            return ten
    return None


def ghep_ten(ten_dua, ten_fb):
    """Tên trên đơn: khách đưa tên khác FB → "<tên FB> - <tên khách đưa>" (chủ shop đổi thứ tự 23/09)."""
    if not ten_dua:
        return None
    if not ten_fb:
        return ten_dua
    a, b = _chu_ten(ten_dua), _chu_ten(ten_fb)
    if not b or b <= a:
        return ten_dua                                # đã chứa đủ tên FB
    if a <= b:
        return None                                   # khách gõ lại (một phần) tên FB → giữ như cũ
    return f"{ten_fb} - {ten_dua}"


# ── Khách chốt combo nào — đọc từ LỜI KHÁCH (chủ shop 2026-09-11) ─────────────────
# "1+1=99", "buy 2 get 2", "2 pcs", "99 aed", hay chỉ "99" khi trả lời câu "which combo?".
R_COMBO_KH = re.compile(r"\b(?:buy\s*)?(\d)\s*(?:\+|get|take|free\s*\+?)\s*(\d)\b", re.I)
# Tin khách nêu ≥2 số lượng ("2 sets MAY… 1 SETS APRIL… 1SETS MARCH", "1 set or 2 sets") → KHÔNG đoán mức giá.
# 22/09 ca Fe Cavan Cavan (Kuwait Amoura Gold, đơn #14598): bản cũ lấy "2 sets" đầu tiên → 21,9 KWD (giá 2 bộ) và TỰ
# XÁC NHẬN, trong khi khách đặt 2 + 1 + 1 = 4 bộ. Không cộng dồn để tự tính: "1 set or 2 sets" cộng ra 3 là sai.
NHIEU_SL = "NHIỀU DÒNG: "
# MUA_N_TANG_N_2409 — câu số lượng MỚI NHẤT của khách không ra được giá → DỪNG, không lùi về câu cũ (ca Dilaila 24/09: "2 pc"
# rồi "3 packs" — câu cũ đã lỗi thời). Xử y như NHIEU_SL: tin shop / giá mặc cả CŨ hơn câu đó không tính.
SL_CHUA_RO = "SỐ LƯỢNG CHƯA RÕ: "
# "order 3" / "buy 3" không kèm đơn vị. "buy N" = SỐ MUA của gói (luật 21/09); "order N" chỉ tính số mua trên page Mua N tặng N.
R_MUA_SO_KH = re.compile(r"\b(?:order|buy|bumili|bili|beli)\s*(\d{1,2})\b(?!\s*(?:get|take|free|\+|am|pm|st|nd|rd|th"
                         r"|days?|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|[:./-]\d))", re.I)
# 24/09 ca Tajul Islam (#76889, Japan Herb Lab KSA): "I.want.by.1pes" → không biết "pes" → đơn 0 SAR. Cùng lượt lòi ra
# `boxes?` chỉ khớp "boxe/boxes" nên "2 box" trượt (49 tin). Đo 29.592 tin khách: +82 tin đọc được, 0 tin đúng bị đổi.
# "pic" = cái (12/13 tin "1 pic how cost"…), không phải ảnh.
R_SL_KH = re.compile(r"\b(\d{1,2})\s*(?:pcs?|pieces?|box(?:es)?|bottles?|items?|sets?|packs?|jars?"
                     r"|pes|pis|pics?|pices?|peices?|peace|pcz|botles?|batle|botel|bote)\b", re.I)
R_CUE_KH = re.compile(r"[+=]|\b(?:buy|order|combo|promo|price|take|get|pcs?|pieces?|box|bottle|set|aed|dhs|dirhams?|sar|riyal|kwd|bhd|qar|omr|usd|\$)\b", re.I)
R_DIA_CHI_SO = re.compile(r"\b(?:villa|flat|apt|apartment|building|bldg|street|st|road|rd|block|blk|house|no\.?|#|zone|area|floor|tower|lane)\s*[:\-]?\s*$", re.I)


_KB_GOI = {}          # đường dẫn kich_ban.json -> (mtime, kịch bản, {pid: frozenset gói})


def goi_cua_page(page_id):
    """{(mua, tặng)} của page CHỈ bán theo gói mua-tặng (≥2 gói, không có bảng giá theo đơn vị) — đọc kịch bản như
    chan_gui.goi_mo_ho; không phải page gói / lỗi đọc → rỗng (MUA_N_TANG_N_2409)."""
    import chan_gui as CG
    f = os.path.join(Q.STATE_DIR, "kich_ban.json")
    try:
        mt = os.path.getmtime(f)
        if (_KB_GOI.get(f) or (None,))[0] != mt:
            _KB_GOI[f] = (mt, json.load(open(f, encoding="utf-8")), {})
        _mt, kb, nho = _KB_GOI[f]
        pid = str(page_id)
        if pid not in nho:
            kb_page = kb.get(pid) or {}
            bang = CG.bang_goi_gia(kb_page) if kb_page else {}
            nho[pid] = frozenset(bang) if len(bang) >= 2 and not CG._bang_don_vi(kb_page) else frozenset()
        return nho[pid]
    except Exception:                                    # noqa: BLE001
        return frozenset()


def gia_theo_loi_khach(khach_msgs, bang, goi=frozenset(), kb=None):
    """Khách đã chốt mức giá nào? Trả (giá đơn vị POS, mốc tin, lý do) hoặc (None, None, None).

    Đọc tin khách từ MỚI về CŨ, tin đầu tiên có dấu hiệu chốt là quyết định:
      1. nhắc thẳng MỘT mức giá có trong bảng giá page ("1+1=99", "99 aed", "99") — tin phải có
         dấu hiệu mua (+ = buy order combo pcs tiền tệ…) hoặc rất ngắn, và con số không đứng
         sau chữ địa chỉ ("Villa 99") hay nằm trong SĐT;
      2. công thức combo "1+1" / "buy 2 get 2" → số lượng → mức giá có đúng số lượng đó;
      3. "2 pcs" → số lượng → mức giá.
    Tin nhắc HAI mức trở lên (khách chép lại promo) → chưa chọn, bỏ qua tin đó.
    """
    if not bang:
        return None, None, None
    # Khoá bảng là chuỗi ("9900"); trả về SỐ đúng kiểu parse_money để fmt_money / tra số lượng dùng được.
    so_hoa = lambda g: int(float(g)) if float(g).is_integer() else float(g)
    qty_gia = {}
    for g, q in bang.items():
        qty_gia.setdefault(str(q), []).append(g)
    hien = {g: P.fmt_money(float(g)).split(" ")[0].replace(",", "") for g in bang}   # "9900" -> "99"

    def _mot_muc(ds):
        """MỘT mức giá cho số lượng này (Kuwait: 19 và 18,9 là CÙNG một mức — gia_duoi_9_don) → giá CÓ THẬT trong bảng."""
        if len({gia_duoi_9_don(so_hoa(g)) for g in ds}) != 1:
            # Bảng học có HAI giá cho cùng số lượng (HOP_POS_2509, page trà Saudi: 2 hộp = 99 và 90 SAR — một đơn sale bớt
            # giá; Veloura Lip Beauty: 3 thỏi 99 cũ và 109 mới) → chỉ lấy mức KỊCH BẢN đang ghi cho đúng số lượng đó; kịch
            # bản không phân xử được thì bỏ như cũ. Nơi gọi chỉ truyền `kb` cho page bán theo GÓI.
            ds = [g for g in ds if (kb or {}).get(g) == bang.get(g)]
            if len({gia_duoi_9_don(so_hoa(g)) for g in ds}) != 1:
                return None
        return so_hoa(min(ds, key=float))

    sl_moi = luc_moi = loi_moi = None     # câu số lượng MỚI NHẤT (MUA_N_TANG_N_2409) — câu cũ chỉ góp giá cho đúng số lượng đó
    for m in reversed(khach_msgs):
        t = PHONE_RE.sub(" ", m.get("noi_dung") or "")
        luc = str(m.get("luc") or "")
        ngan = len(t.split()) <= 4
        co_cue = bool(R_CUE_KH.search(t))
        if co_cue or ngan:
            trung = []
            for g, so in hien.items():
                for h in re.finditer(r"(?<![\d.,])" + re.escape(so) + r"(?![\d.,])", t):
                    if R_DIA_CHI_SO.search(t[max(0, h.start() - 14):h.start()]):
                        continue                          # "Villa 99" là số nhà, không phải giá
                    trung.append(g)
                    break
            trung = list(dict.fromkeys(trung))
            if len(trung) == 1 and (sl_moi is None or bang.get(trung[0]) in sl_moi):
                return so_hoa(trung[0]), luc, f'khách nhắc mức {hien[trung[0]]}: "{t.strip()[:60]}"'
            if len(trung) == 1:
                continue                                  # giá ở câu CŨ ứng với số lượng KHÁC câu mới nhất → bỏ
            if len(trung) > 1:
                continue                                  # chép lại promo, chưa chọn
        _sls = R_SL_KH.findall(t)
        if len(_sls) >= 2 and sl_moi is None:
            # tin MỚI NHẤT có số lượng mà nêu nhiều dòng → dừng ở đây, KHÔNG lùi về tin cũ (câu cũ đã lỗi thời)
            _tong = sum(int(x) for x in _sls)
            _g_tong = qty_gia.get(str(_tong), [])
            return None, luc, (f"{NHIEU_SL}khách nêu {' + '.join(_sls)} = {_tong} trong một tin: "
                               f'"{t.strip()[:70]}"'
                               + (f" (bảng page: {_tong} = {hien[_g_tong[0]]})" if len(_g_tong) == 1 else ""))
        c = R_COMBO_KH.search(t)
        s = None if c else R_SL_KH.search(t)
        b = None if (c or s) else R_MUA_SO_KH.search(t)
        if not (c or s or b):
            continue
        if c:
            n, loi = int(c.group(1)) + int(c.group(2)), c.group(0)
            thu = [n]
        else:
            n, loi = int((s or b).group(1)), (s or b).group(0)
            nn = len(goi) >= 2 and all(x == y for x, y in goi)          # page Mua N tặng N
            mua = [x + y for x, y in goi if x == n]                      # tổng của gói có SỐ MUA = n
            thu = []
            if b and len(mua) == 1 and not loi.lower().startswith("order"):
                thu.append(mua[0])                  # "buy 2" = gói có SỐ MUA 2 (luật 21/09)
            else:
                # "buy 2" nói rõ số MUA thì KHÔNG lùi về "2 món" (BANG_KB_BU_2509, ca Ummie #77069: bảng học thiếu mức 159 →
                # máy lùi về 2 món 109 SAR + tự xác nhận, trong khi AI đã chốt Mua 2 tặng 2 — 4 món 159 SAR)
                thu.append(n)                       # số SẢN PHẨM khách muốn nhận ("2 pc" trên page BUY 1 GET 1 = gói đó)
            if nn and len(mua) == 1:
                thu.append(mua[0])                  # "3 packs" / "order 3" trên page 2/4/6 hộp = Mua 3 tặng 3 (chủ shop 24/09)
            if n == 1 and goi and "1" not in qty_gia:
                thu.append(min(x + y for x, y in goi))   # "1 set" trên page chỉ bán gói = gói nhỏ nhất (luật 21/09)
        if sl_moi is not None:
            thu = [x for x in thu if x in sl_moi]  # câu CŨ chỉ góp giá cho đúng số lượng câu mới nhất (khách đổi ý)
        for sl in thu:
            g = _mot_muc(qty_gia.get(str(sl), []))
            if g is not None:
                return g, luc, (f'khách chốt combo "{loi}" = {sl} cái' if c else
                                f'khách nói "{loi}"' + (f" = gói Mua {n} tặng {sl - n}" if sl != n else ""))
        if sl_moi is None:
            sl_moi, luc_moi, loi_moi = set(thu), luc, loi
    if sl_moi is not None:
        return None, luc_moi, f'{SL_CHUA_RO}khách nói "{loi_moi}" — bảng page không ra được giá cho số lượng này'
    return None, None, None


# ═════════════════════════════════════════════════════════════════════════════
# GIÁ MỖI CÁI không phải TIỀN THU (GIA_MOI_CAI_2609 — chủ shop 26/09 "Erwella Aldon đơn 2 cái 239 sar ai lại lên cod bằng
# một nửa giá 119,5 sar", đơn #77279 Key Jewelry Saudi)
# ═════════════════════════════════════════════════════════════════════════════
# AI được nói đơn giá suy từ gói (chủ shop 10/09, don-gia-suy-tu-goi): "239 SAR is for 2 necklaces — that's already the best
# price, only 119.5 SAR each". PRICE_RES bắt số sau chữ "price" → 119,5 thành tiền thu. Sổ 27.238 tin AI: sau số tiền gặp
# "per box" 34, "each" 24, "per item" 10, "للقطعة" 5, "per set/tube/piece/bottle", "bawat isa"… — "99 AED / 2 pcs" là 99
# cho 2 cái, KHÔNG phải giá mỗi cái (dấu "/" chỉ tính khi theo sau là chữ đơn vị).
R_SAU_GIA_MOI_CAI = re.compile(
    r"^\s*(?:(?:na\s+)?lang\s+|po\s+|only\s+|just\s+)*(?:each\b|apiece\b|a\s+piece\b"
    r"|per\s+(?:piece|pcs?|item|unit|one|necklace|bottle|box|pack|set|tube|jar|pair|ring|bracelet|bar|sachet|cream)(?:e?s)?\b"
    r"|/\s*(?:pcs?|piece|item|unit|each|box|bottle|set|pack|tube)\b"
    r"|bawat\s+isa\b|kada\s+isa\b|للحبة|للقطعة|لكل\s|للواحد)", re.I | re.U)
R_TRUOC_GIA_MOI_CAI = re.compile(
    r"(?:\beach(?:\s+(?:one|piece|pc|item|set|necklace|bottle|box|cream|tube))?"
    r"|\bper\s+(?:piece|pcs?|item|unit|one|necklace|bottle|box|pack|set|tube)"
    r"|\ba\s+piece|\bbawat\s+isa|\bkada\s+isa|\btig-?)(?:\s*(?:is|at|only|just|costs?|lang|ay|for|[:=\-–—]))*\s*$", re.I)


def gia_moi_cai(t, h):
    """Con số của match `h` (nhóm 1 = số) trong câu `t` là giá MỖI CÁI: ngay sau là "each" / "per box" / "/pc" / "bawat isa"
    / "للقطعة"…, hoặc ngay trước là "each set is" / "per piece:" / "tig-"."""
    return bool(R_SAU_GIA_MOI_CAI.search(t[h.end():h.end() + 40])
                or R_TRUOC_GIA_MOI_CAI.search(t[max(0, h.start(1) - 30):h.start(1)]))


def gia_page_bao_lai(shop_msgs, luc_kh, gia_kh, bang):
    """Câu AI/sale MỚI NHẤT sau lời khách mà có nêu giá: nêu đúng MỘT mức trong bảng page, CÙNG số lượng với mức
    khách nhắc mà KHÁC số tiền → (mức đó, câu) = page không nhận con số khách nói. Còn lại → None (giữ lời khách).

    23/09 ca Jhomar Dipatuan (Minty Fresh Smile KSA, đơn #76371): khách hỏi "99 riyal po ba eto" (99 phải không?), AI
    đáp "Buy 1 Get 1 FREE — 2 pcs, 109 SAR", khách "1 set lng po" → tool vẫn lên 99 vì câu AI không có chữ
    order/total nên PRICE_RES không thấy, luật "tin mới hơn thắng" không chạy; sale phải sửa tay 99 → 109.
    Chỉ xét tin có nhãn người gửi ai/nguoi (AI Sale truyền "boi"): Botcake nhắc promo không phải lời đáp giá khách
    (cùng lẽ với gia_mac_ca). Daemon không truyền nhãn → hàm luôn None, daemon chạy như cũ.
    Khác số lượng thì không xét: AI mời gói lớn ("2 sets 159") không phải là từ chối giá gói khách chọn."""
    if gia_kh is None or not bang or str(gia_kh) not in bang:
        return None
    _tu = MK.get("tu_tien_te") or ""
    if isinstance(_tu, (list, tuple)):
        _tu = "|".join(map(re.escape, _tu))
    if not _tu:
        return None
    cac_rx = [re.compile(r"(\d[\d.,]*)\s*(?:" + _tu + r")\b", re.I | re.U)]
    if MK.get("ky_hieu_truoc"):
        cac_rx.append(re.compile(r"(?:" + MK["ky_hieu_truoc"] + r")\s*(\d[\d.,]*)", re.I | re.U))
    for m in reversed(shop_msgs):
        if str(m.get("luc") or "") <= str(luc_kh or ""):
            break
        if m.get("boi") not in ("ai", "nguoi"):
            continue
        _t = m.get("noi_dung") or ""
        cac = [P.parse_money(h.group(1)) for rx in cac_rx for h in rx.finditer(_t)
               if not gia_moi_cai(_t, h)]                                    # GIA_MOI_CAI_2609: bỏ giá mỗi cái
        cac = list(dict.fromkeys(g for g in cac if g is not None and str(g) in bang))
        if not cac:
            continue                              # câu không nêu giá (xin SĐT, hỏi địa chỉ…) → xét câu cũ hơn
        if (len(cac) == 1 and gia_duoi_9_don(cac[0]) != gia_duoi_9_don(gia_kh)     # 19 ≡ 18,9 ở Kuwait (MUA_N_TANG_N_2409)
                and bang.get(str(cac[0])) == bang.get(str(gia_kh))):
            return cac[0], f'"{(m.get("noi_dung") or "").strip()[:60]}"'
        return None                               # nêu đúng mức khách / nhiều mức / gói khác → giữ lời khách
    return None


# Địa chỉ RÁC: tin quảng cáo / tin mẫu xin thông tin bị ghi thành địa chỉ đơn. Pancake tự lưu địa chỉ
# đơn vào hồ sơ khách, nên rác một lần là lần sau tool lại lấy "địa chỉ hồ sơ đã lưu" ra dùng tiếp
# (đơn #74140 Carpio Jake: tin mẫu "1. Name: (Buong Pangalan)… , Baha" quay vòng, 14/09/2026).
# Đo 30 ngày 11 nước (~6.100 địa chỉ POS): chỉ bắt đúng 6 đơn rác + 1 đơn sale gõ tên SP vào ô địa chỉ.
_KHUNG_TRONG = re.compile(r"[:：]\s*(?:\n|\(|[✓✔☑]|\d+\.\s)|\bexample\b|\be\.g\.|free shipping|cash on delivery", re.I)


def dia_chi_rac(t):
    return bool(t) and (len(t) > 300 or bool(_KHUNG_TRONG.search(t)))


# ── CHỈ TỰ XÁC NHẬN KHI ĐỊA CHỈ ĐỦ ĐỂ SHIPPER GIAO (chủ shop 2026-09-17) ─────────────────────
# *"xác nhận đơn chỉ khi có địa chỉ và sdt đầy đủ, còn bạn đang xác nhận cả đơn chưa có địa chỉ
# đầy đủ"*. Luật cũ chỉ đếm chữ: `len(bỏ số)>=3 từ` là coi như đủ → 5 ngày có 160 đơn tool tự
# xác nhận thì 29 đơn (18%) KHÔNG giao được, gồm cả những thứ không phải địa chỉ:
#   "Jeddah Saudi Arabia, Jeddah" · "Al Malaz Riyadh ksa" · "Al Hilal Doha" (chỉ tên tỉnh/khu)
#   "How monny days in Riyadh" · "كم سعرة بسعودية الرياض" (câu hỏi giá của khách)
#   "Hi mam i am here in Riyadh KSA" (câu tán gẫu) · tin mẫu xin thông tin của chính shop
#   3 đơn ô địa chỉ TRỐNG TRƠN mà vẫn lên "Đã xác nhận"
# Nay đòi: bỏ các mảnh chỉ là tên tỉnh/nước (Pancake tự ghép ", Riyadh, Riyadh") thì phần LÕI
# khách gõ phải còn ≥2 chữ VÀ có số (nhà/villa/toà/đường) HOẶC có từ chỉ chỗ giao được
# (street/villa/building/tower/near/opposite/mall/hospital...). Đo 5 ngày: chặn 29/160 đơn tool,
# cả 29 đều đúng là chưa giao được; 131 đơn còn lại vẫn tự xác nhận như cũ. Đối chiếu 1073 đơn
# NGƯỜI xác nhận: luật chê 166 (15%) — 95 trong đó là đơn người xác nhận khi ô địa chỉ TRỐNG,
# 71 là địa chỉ chỉ có tên khu. Đơn không đủ KHÔNG bị bỏ: vẫn tạo, nằm "Mới" cho sale duyệt.
TU_DIA_CHI_GIAO = re.compile(
    r"\b(?:street|str|road|rd|avenue|ave|block|blk|villa|flat|apt|apartment|building|bldg|tower"
    r"|house|floor|room|unit|compound|mall|hospital|clinic|pharmacy|restaurant|school|university"
    r"|masjid|mosque|supermarket|market|hotel|exit|gate|zone|way|near|beside|behind|opposite"
    r"|next\s+to|landmark|bank|cafe|station|camp|labour|company|office|shop)\b"
    r"|شارع|طريق|بناية|عمارة|فيلا|شقة|مجمع|برج|مستشفى|صيدلي|مدرس|سوق|محطة|بجانب|خلف|مقابل|قرب|المنطق|منطق",
    re.I | re.U)
TEN_NUOC_BAN = re.compile(
    r"\b(?:saudi\s*arabia|ksa|united\s+arab\s+emirates|uae|u\.a\.e|qatar|kuwait|oman|bahrain"
    r"|emirates?)\b|السعودي|الامارات|الإمارات", re.I | re.U)


def loi_dia_chi(dc):
    """Bỏ mảnh chỉ là tên tỉnh/nước → phần LÕI do khách gõ. 'Jeddah Saudi Arabia, Jeddah' → ''."""
    manh = []
    for m in re.split(r"[,\n]", str(dc or "")):
        m = m.strip(" .-")
        if not m:
            continue
        r = TEN_NUOC_BAN.sub(" ", m).strip(" .-")
        if not r or (P.detect_emirate(r) and len(r.split()) <= 3):
            continue
        manh.append(r)
    return " ".join(manh).strip()


def dia_chi_du_giao(dc):
    """'' nếu địa chỉ đủ để giao; ngược lại trả LÝ DO còn thiếu (ghi thẳng vào note cho sale)."""
    import ho_so as HS                      # nạp muộn: ho_so cũng gọi ngược lại module này
    dc0 = str(dc or "").strip()
    if not dc0:
        return "chưa có địa chỉ"
    if dia_chi_rac(dc0):
        return "đang là tin mẫu/khung trống của shop"
    if HS.la_cau_hoi_dia_chi(dc0):
        return "đang là câu khách hỏi, không phải địa chỉ"
    loi = loi_dia_chi(dc0)
    if len(loi.split()) < 2:
        return "mới có tên tỉnh/thành"
    if not re.search(r"\d", loi) and not TU_DIA_CHI_GIAO.search(loi):
        return "thiếu đường/số nhà/toà nhà"
    return ""


def _dc_la_cau_hoi(dc):
    """Tin khách có tên tỉnh mà là CÂU HỎI / câu nói / tin mẫu shop → KHÔNG phải ứng viên địa chỉ.

    19/09 (đơn #75351, Lyn Omar Tahil · Hitana Store in Saudi): khách hỏi "How many day in Riyadh" →
    extract() chọn làm địa chỉ → ghi THẲNG vào ô địa chỉ đơn. Cửa xác nhận (dia_chi_du_giao) chặn được,
    nhưng ô địa chỉ vẫn mang câu hỏi, còn địa chỉ thật khách gửi sau (không có tên tỉnh) chỉ nằm trong
    note. Chủ shop: *"sao lại thêm chữ how many day vào địa chỉ, nó có phải địa chỉ đâu"*.
    Câu hỏi mà có SỐ + từ khoá địa chỉ ("ito ang address Dubai merdep st 13 b villa 1 A ?") vẫn là địa chỉ.
    Đo tin khách thật 6 nước (so_chi_phi.jsonl): bỏ 79 Saudi / 30 UAE / 4 Oman ứng viên — đều là câu hỏi."""
    import ho_so as HS
    c = str(dc or "")
    if dia_chi_rac(c):
        return True
    c2 = re.sub(r"\bd2\b", "dito", c, flags=re.I)
    if not (HS.la_cau_hoi_dia_chi(c2) or R_KHONG_PHAI_3_CAP.search(c2)):
        return False
    return not (re.search(r"\d", c) and HS.TU_DIA_CHI.search(c))


# ── ĐỊA CHỈ ĐỦ 3 CẤP: TỈNH/THÀNH + KHU/QUẬN + ĐƯỜNG/SỐ NHÀ/TOÀ NHÀ (chủ shop 2026-09-17) ───────
# *"3 cấp ví dụ như địa chỉ phải có đủ tỉnh/thành, khu/quận và đường/số nhà/toà nhà"*.
# Chưa có SĐT thì chỉ địa chỉ đủ CẢ BA cấp mới được mở đơn nháp. Cách dò từng cấp:
#   · tỉnh/thành — tên tỉnh POS; không có thì suy ngược từ tên khu (bảng quận/huyện POS, chỉ
#     nhận khi tên khu thuộc đúng MỘT tỉnh) — Kuwait/Qatar khách ghi khu chứ ít ghi tỉnh
#   · khu/quận  — tên quận/huyện/phường POS trong tỉnh đó, HOẶC từ khoá khu (district/area/حي…),
#     HOẶC còn lại một cụm tên riêng sau khi bỏ tên tỉnh/nước, từ đệm, cụm đường/toà nhà
#   · đường/nhà — từ khoá đường/toà nhà/số nhà/mốc (street, road, villa, building, near…)
# Vì sao phải siết: bản sáng 17/09 (HS.dia_chi_du_tin) cho tên tỉnh trơn mở đơn, và địa chỉ bộ trích
# daemon đọc ra (mọi tin khách có tên tỉnh) còn lọt thẳng qua len_don_som → tối 17/09 AI Sale vẫn mở
# #75017 "Ano whats app no nyu batha riyadh ako", #75002, #74958 "In her Dammam". Bản đầu tối 17/09
# cho "Block 3 Street 4 House 54" (không tên tỉnh/khu) và "tỉnh + đường" qua — lỏng hơn lời chủ shop.
# Đo 17/09: nháp không SĐT 3 ngày → saudi chặn 92/97, uae 5/6, kuwait 3/3, oman 4/4 (phần còn mở
# là địa chỉ thật). Địa chỉ thật đơn đã giao 10 ngày: uae 267/300, saudi 166/200, kuwait 83/90,
# oman 12/13, bahrain 5/5 qua — phần rớt đa số thiếu hẳn một cấp ("Al Karama Dubai",
# "Ar rawdah district jeddah"). Rớt chỉ là đợi: khách cho SĐT là mở đơn.
# Câu khách nói/hỏi có tên tỉnh mà không phải địa chỉ (Tagalog "d2" = "dito": ở đây); hỏi chỗ cửa hàng
R_KHONG_PHAI_3_CAP = re.compile(
    r"\b(?:ilang|kailan|magkano|mayron|meron|mero|ano|only\s+online|have\s+(?:a\s+)?shop|how\s+many\s+days"
    r"|provide|your\s+(?:store|shop|branch|office|location|outlet)"
    r"|(?:store|shop|branch|tindahan)\s+(?:niyo|nyo|kayo)|visit|vesite|visite|bisita)\b"
    r"|فيه\s+محل|عندكم|وين\s+(?:محلكم|مكانكم|فرعكم)", re.I)
R_CAP_KHU = re.compile(
    r"(?<![^\W\d_])(?:district|dist|area|zone|neighbou?rhood|hay|hayy)(?![^\W\d_])"
    r"|حي|منطقة|ضاحية", re.I)
R_CAP_KHU_BLOCK = re.compile(r"(?<![a-z])(?:block|blk|blok|blook|bock|blck)(?![a-z])", re.I)
R_CAP_DUONG = re.compile(      # cụm đứng TRƯỚC là tên đường/toà nhà → không phải tên khu
    r"(?<![a-z])(?:street|st|str|stret|strt|streat|road|rd|way|avenue|ave|lane|highway|exit"
    r"|building|bldg|bld|bilding|buliding|bulding|house|villa|flat|apartment|apt|floor|room|unit"
    r"|tower|compound|camp|mall|hospital|clinic|pharmacy|restaurant|school|university|college"
    r"|masjid|mosque|supermarket|hypermarket|market|hotel|gate|bank|cafe|cafeteria|caffeterea"
    r"|station|company|office|shop|store|salon|bakery|park|llc|l\.l\.c|trading|factory|warehouse"
    r"|establishment|est|housing|residence|residency|apartments|complex|villas)(?![a-z])"
    r"|شارع|طريق|عمارة|مبنى|فيلا|فله|شقة|منزل|بيت|مجمع|جادة|مسجد|جامع|مستشفى|مدرسة|سوق|محل|فندق"
    r"|بنك|صيدلية|مطعم|بوابة|مخرج|برج|دور", re.I)
# Số nhà / số toà nhà: "#28", "No. 5", "6457, Al Qurunful" (địa chỉ quốc gia Saudi), mã Plus "5C94+772".
# Số đi với đơn vị hàng/tiền/tuổi thì không phải số nhà.
R_CAP_SO_NHA = re.compile(
    r"#\s*\d+|(?<![a-z])(?:no|num)\.?\s*\d+|\b[23456789cfghjmpqrvwx]{4}\+[23456789cfghjmpqrvwx]{2,3}\b"
    r"|(?<![\d+])(?<!\d[.,])\d{2,5}(?!\d|[.,]\d)(?!\s*(?:pcs?|pieces?|box(?:es)?|items?|x\b|sar|aed|sr|riyals?|rials?"
    r"|kwd?|kd|qr|qar|omr|bd|bhd|dhs?|dirhams?|%|am\b|pm\b|days?|hours?|hrs?|mins?|years?|yrs?|months?|ml|g\b|kg))",
    re.I)
# Ngày tháng (ngày sinh khách hay gõ kèm tên: "Feb 21 1976") không phải số nhà
R_NGAY_THANG = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*\d{1,2}(?:st|nd|rd|th)?,?\s*(?:19|20)\d{2}\b"
    r"|\b\d{1,2}(?:st|nd|rd|th)?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?,?\s*(?:19|20)\d{2}\b"
    r"|\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)?\d{2}\b|\b(?:born|birthday|dob)\b", re.I)
R_CAP_MOC = re.compile(        # mốc: cụm đứng SAU là tên mốc
    r"(?<![a-z])(?:near|nr|beside|behind|opposite|opp|infront|in\s+front\s+of|next\s+to|across)(?![a-z])"
    r"|بجوار|قرب|مقابل|خلف|جنب|بجانب", re.I)
TU_DEM_DIA_CHI = set("""
i im am is are was be here there in at on of the a an my me we our you your and or to from for with
this that it its live living stay staying work working currently now only just also send deliver
delivery address addres adress location loc name number no num phone mobile whatsapp wa contact
city province country kingdom state sultanate emirate emirates united arab arabia saudi saudia ksa uae
kuwait qatar oman bahrain gulf middle east po ako sa dito dto d2 ng na ang ka ko mi kami nako nga ra
kay si ni mga taga nandito nakatira tinitirahan lugar saan maam madam mam sir hello hi hai ok okay
yes pls please thanks thank you want order buy pcs pc piece pieces box price how much many days cash
cod next born birthday dob jan feb mar apr may jun jul aug sep sept oct nov dec aku saya di tinggal alamat ana fi fil main mein hu hoon hai mera meri mere ghar area
ya al el bin bint abu umm um wa city's
في انا انا في السعودية المملكة العربية الامارات الإمارات الكويت قطر عمان البحرين مدينة الرياض
""".split())


def _la_ten(w):
    return (len(w) >= 3 and not w.isdigit() and w not in TU_DEM_DIA_CHI and not R_CAP_KHU.fullmatch(w)
            and not R_CAP_KHU_BLOCK.fullmatch(w) and not R_CAP_DUONG.fullmatch(w)
            and not R_CAP_MOC.fullmatch(w))


def _cap_khu_tu_khoa(tu):
    """'Al Olaya district' / 'حي النرجس' / 'Industrial Area A': từ khoá khu có TÊN đứng cạnh.
    Kuwait/Bahrain: 'Block 12' là cấp khu (tên khu ở đó hay trùng tên tỉnh: Farwaniya, Jahra)."""
    for i, w in enumerate(tu):
        if (MK["key"] in ("kuwait", "bahrain") and R_CAP_KHU_BLOCK.fullmatch(w)
                and i + 1 < len(tu) and tu[i + 1].isdigit()):
            return f"{w} {tu[i + 1]}"
        if R_CAP_KHU.fullmatch(w):
            for j in (i - 1, i + 1):
                if 0 <= j < len(tu) and (_la_ten(tu[j]) or (tu[j].isdigit() and j == i + 1)):
                    return f"{w} {tu[j]}"
    return ""


def _cap_khu_con_lai(doan):
    """Còn cụm tên riêng nào sau khi bỏ tên tỉnh/nước, từ đệm, cụm quanh từ đường/toà nhà/mốc?
    Xét TỪNG ĐOẠN (tách bởi dấu phẩy): "Albarsha2, Street 34A" — tên khu không bị cửa sổ của
    'Street' ở đoạn sau nuốt mất."""
    con = []
    for tu in doan:
        bo = set()
        for i, w in enumerate(tu):
            if R_CAP_DUONG.fullmatch(w):
                bo.update(range(i - 2, i + 1))
                if i + 1 < len(tu) and (tu[i + 1].isdigit() or len(tu[i + 1]) <= 3):
                    bo.add(i + 1)            # "building 12", "st 5a" — tên đứng SAU thì giữ lại
            elif R_CAP_MOC.fullmatch(w):
                bo.update(range(i, i + 4))
        con += [w for i, w in enumerate(tu) if i not in bo and _la_ten(w)]
    return con


def _chu_khoa(k):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", k)).strip()


_TINH_GOC = {}
# Nước mà "tỉnh" POS là cả một vùng lớn (governorate): bí danh gắn thêm cho tỉnh là TÊN KHU
# ('mangaf', 'mahboula' của Ahmadi), không phải cách viết khác của tên tỉnh như ở Saudi/UAE.
BI_DANH_LA_KHU = {"kuwait", "qatar", "oman", "bahrain"}


def _tinh_goc(bang):
    """Tên tỉnh THẬT (tên POS + tên Ả Rập của tỉnh). Bí danh trùng tên khu trong bảng quận/huyện
    — Kuwait gắn 'mangaf', 'salmiya' làm bí danh tỉnh — là tên KHU, không bỏ khi dò cấp khu."""
    mk = MK["key"]
    if mk not in _TINH_GOC:
        khu = {_chu_khoa(k) for _pid, keys, _did in bang for k in keys}
        goc = set()
        for p in Q.load_json(os.path.join(BASE_STATE, mk, "provinces.json"), []) or []:
            for name in (p.get("name"), p.get("name_en")):
                for phan in [name or ""] + re.split(r"[/(),]", name or ""):
                    if len(P.norm_ascii(phan)) >= 3:
                        goc.add(_chu_khoa(P.norm_ascii(phan)))
        if mk not in BI_DANH_LA_KHU:
            for _pid, keys in (P.PROVINCES or []):
                for k in keys:
                    if _chu_khoa(k) not in khu:
                        goc.add(_chu_khoa(k))
        _TINH_GOC[mk] = goc
    return _TINH_GOC[mk]


def cap_dia_chi(dc, tinh_id=None):
    """Dò 3 cấp của một chuỗi địa chỉ. Trả dict {tinh, khu, duong} (giá trị = cái dò được, rỗng = thiếu).
    `tinh_id`: tỉnh POS đã chọn trên đơn — ô địa chỉ của đơn thường không lặp lại tên tỉnh."""
    import don_landing as L
    L._MKEY = MK["key"]
    t = str(dc or "")
    kq = {"tinh": "", "khu": "", "duong": ""}
    m = R_CAP_DUONG.search(t) or R_CAP_MOC.search(t) or R_CAP_SO_NHA.search(t)
    if m:
        kq["duong"] = m.group(0)
    lines = [x.strip() for x in re.split(r"[,\n|،]| - ", t) if x.strip()] or [t]
    tinh = P.detect_emirate(t) or tinh_id
    khu_pos = ""
    try:
        bang = L.bang_quan_huyen()
    except Exception:                                    # noqa: BLE001 — không tải được bảng thì dò chữ
        bang = []
    tinh_keys = _tinh_goc(bang)
    if MK["key"] in BI_DANH_LA_KHU:
        bang = list(bang) + [(pid, [k for k in keys if _chu_khoa(k) not in tinh_keys], None)
                             for pid, keys in (P.PROVINCES or [])]
    # khoá tên khu: bỏ gạch nối ('al-shuhada' → 'al shuhada') + thêm bản bỏ mạo từ ('shuhada')
    bang = [(pid, sorted({v for k in keys for v in (_chu_khoa(k), re.sub(r"^(?:al|el|ad|ar|as|at|an|ash) ", "", _chu_khoa(k)))
                          if len(v) >= 4}), did) for pid, keys, did in bang]
    if not tinh and bang:
        # suy tỉnh từ tên khu: chỉ khớp đúng tên, và tên đó chỉ thuộc MỘT tỉnh
        ung = [((pid, did), keys) for pid, keys, did in bang]
        (bo, ten) = L._do_dia_danh(lines, ung, gan_dung=False)
        if bo:
            cung_ten = {pid for pid, keys, did in bang if ten in keys}
            if len(cung_ten) == 1:
                tinh, khu_pos = bo[0], ten
    if tinh:
        kq["tinh"] = str(tinh)
    if tinh and not khu_pos and bang:
        ung = [(did, [k for k in keys if k not in tinh_keys]) for pid, keys, did in bang if pid == tinh]
        ung = [(d, ks) for d, ks in ung if ks]
        _id, ten = L._do_dia_danh(lines, ung, gan_dung=True)
        # 'King Fahd' vừa là tên khu vừa là tên đường: đứng ngay trước 'road' thì là đường
        if ten and re.search(rf"\b{re.escape(ten)}\s+(?:road|rd|street|st|str|avenue|ave|way)\b",
                             P.norm_ascii(re.sub(r"[^\w\s]", " ", t))):
            ten = ""
        khu_pos = ten or ""
    if not khu_pos and bang:
        # tên khu khớp đúng nhưng nằm ở tỉnh khác tỉnh đã dò (khách ghi bí danh/tên nước lẫn)
        _id, ten = L._do_dia_danh(lines, [(did, [k for k in keys if k not in tinh_keys])
                                          for pid, keys, did in bang], gan_dung=False)
        if ten and not re.search(rf"\b{re.escape(ten)}\s+(?:road|rd|street|st|str|avenue|ave|way)\b",
                                 P.norm_ascii(re.sub(r"[^\w\s]", " ", t))):
            khu_pos = ten
    if tinh and not khu_pos and MK["key"] == "uae":
        try:
            _p, _d, _c, ten = L.do_khu_toan(lines, trong_tinh=tinh)
            khu_pos = ten or ""
        except Exception:                                # noqa: BLE001
            pass
    if khu_pos:
        kq["khu"] = khu_pos
        return kq
    doan = []
    for line in lines:
        x = _chu_khoa(P.norm_ascii(TEN_NUOC_BAN.sub(" ", line)))
        for k in sorted(tinh_keys, key=len, reverse=True):
            x = re.sub(rf"(?<!\w){re.escape(k)}(?!\w)", " ", x)
        doan.append(re.findall(r"[^\W\d_]+|\d+", x))
    con = _cap_khu_con_lai(doan)
    kq["khu"] = next((k for k in map(_cap_khu_tu_khoa, doan) if k), "") or " ".join(con[:3])
    return kq


def dia_chi_3_cap(dc, tinh_id=None):
    """Chuỗi khách gõ có phải địa chỉ đủ 3 cấp không? Trả (True/False, lý do).

    Dùng cho CẢ HAI cửa: mở đơn nháp khi chưa có SĐT, và TỰ XÁC NHẬN đơn (chủ shop 18/09:
    *"khi có cả 2 thông tin địa chỉ và sdt đầy đủ thì bấm xác nhận"* — "đầy đủ" = 3 cấp; vẫn phải
    có giá/combo khách chốt mới xác nhận). Đo 5 ngày: tool tự xác nhận 37 đơn chưa đủ 3 cấp, 9 đơn
    bị hủy/hoàn (Saudi 31% so với 11% ở đơn đủ 3 cấp) — nay để Mới cho sale bấm tay."""
    import ho_so as HS
    dc = re.sub(r"\s*\(model đọc ra từ lời khách\)\s*$", "", str(dc or "")).strip()
    if not dc:
        return False, "chưa có địa chỉ"
    mk = MK["key"]
    ok, vi = HS.dia_chi_du_tin(dc, mk)
    if not ok and vi == "địa danh Philippines":
        return False, vi
    if mk == "usa":
        return (True, "") if ok and vi == "đường/zip Mỹ" else (False, vi or "chưa đủ số nhà + đường + thành phố")
    if HS.khong_phai_dia_chi(dc, mk):
        return False, "khách nói chưa có địa chỉ / đang ở nơi khác"
    sach = re.sub(r"\bd2\b", "dito", dc, flags=re.I)
    if re.search(r"\bnumber\b", sach, re.I) and not re.search(r"\d", sach):
        return False, "khung mẫu chưa điền"
    if R_KHONG_PHAI_3_CAP.search(sach) or HS.la_cau_hoi_dia_chi(sach):
        return False, "là câu nói/câu hỏi, không phải địa chỉ"
    if dia_chi_rac(sach):
        return False, "tin mẫu/khung trống của shop"
    kq = cap_dia_chi(R_NGAY_THANG.sub(" ", sach), tinh_id)
    thieu = [ten for k, ten in (("tinh", "tỉnh/thành"), ("khu", "khu/quận"),
                                ("duong", "đường/số nhà/toà nhà")) if not kq[k]]
    if thieu:
        return False, "thiếu " + " + ".join(thieu)
    return True, ""


# ── KHÁCH VỪA GÕ ĐỊA CHỈ MỚI, KHÁC HỒ SƠ CŨ (23/09, đơn #50863 · Bardenas Leonicar · Solid Big Infinity Ring Gold UAE) ──
# Khách gõ "Leonicar bardenas 0568550928 Burj Al salam 15 floor room 1506" (không có chữ Dubai). Nhánh địa chỉ chỉ nhận tin
# có TÊN TỈNH nên bỏ qua, rơi xuống nhánh "hồ sơ đã lưu" → lấy địa chỉ ĐƠN CŨ "DIP 1 Tph accomodation … Dubai Investment
# Park" rồi TỰ XÁC NHẬN; nhánh dia_chi_ai (chữ khách gõ) đứng sau nên không bao giờ tới lượt. Đo 10 ngày: 210 đơn dùng địa
# chỉ hồ sơ, #50442 (khách gõ Sadiyat Island → đơn đi Muroor Road) và #49911 cũng giao lệch chỗ.
# Nay: khách gõ một địa chỉ (có số + từ địa chỉ) KHÁC CHỖ hồ sơ cũ → lấy chữ khách gõ, THIẾU tỉnh → không tự xác nhận, note
# ghi địa chỉ cũ cho sale hỏi. Khách gõ tắt / sai chính tả đúng chỗ cũ ("4 A St Villa 18 Jumairah 1") → vẫn dùng hồ sơ.
_TU_DC_THUONG = frozenset(
    "street str road block blk building bldg villa flat apt apartment house floor flr room near behind opposite infront "
    "front area city district zone tower number the and for with from uae ksa saudi arabia kuwait qatar oman bahrain "
    "united arab emirates emirate".split())


def _tu_dia_chi(t, bo=()):
    """(tên riêng ≥3 chữ cái, các con số) của một địa chỉ — bỏ SĐT, tên tỉnh, từ địa chỉ chung, tên khách."""
    t = PHONE_RE.sub(" ", so_latin(str(t or ""))).lower()
    so = set(re.findall(r"\d{1,6}", re.sub(r"\b\d+(?:st|nd|rd|th)\b", " ", t)))   # "3rd st" là tên đường, không phải số nhà
    chu = {w for w in re.findall(r"[^\W\d_]{3,}", t)
           if w not in _TU_DC_THUONG and w not in bo and not P.detect_emirate(w)}
    return chu, so


def _khop_tu(a, ds):
    if a in ds:
        return True
    if a.isdigit() or len(a) < 4:
        return False
    import difflib
    return any(not b.isdigit() and difflib.SequenceMatcher(None, a, b).ratio() >= 0.8 for b in ds)


def cung_cho(moi, cu, ten=""):
    """Địa chỉ khách vừa gõ `moi` có phải CÙNG CHỖ với địa chỉ hồ sơ `cu`?

    Cùng = ≥ nửa tên riêng của một bên có ở bên kia (gõ sai ≤20% vẫn tính) VÀ hai bên không có bộ số nhà tách rời hẳn
    ("building 12 al barsha" ≠ "building 12 deira"; "villa 38 … sadiyat" ≠ "bldg 168 … muroor"). Một bên không có tên
    riêng nào → không đủ để so → coi là cùng (giữ đường cũ, dùng hồ sơ)."""
    bo = set(re.findall(r"[^\W\d_]{3,}", str(ten or "").lower()))
    (ca, sa), (cb, sb) = _tu_dia_chi(moi, bo), _tu_dia_chi(cu, bo)
    if not ca or not cb:
        return True
    ty_le = max(sum(_khop_tu(x, cb) for x in ca) / len(ca), sum(_khop_tu(x, ca) for x in cb) / len(cb))
    return ty_le >= 0.5 and not (sa and sb and sa.isdisjoint(sb))


def dia_chi_khach_go_moi(khach_msgs):
    """Tin khách (6 tin gần nhất, mới trước) trông như ĐỊA CHỈ mà không có tên tỉnh — thứ nhánh tên-tỉnh bỏ sót."""
    import ho_so as HS
    for m in list(reversed(khach_msgs or []))[:6]:
        t = PHONE_RE.sub("", lam_sach_dia_chi(m.get("noi_dung") or "")).strip(" ,.-")
        if (len(t.split()) >= 3 and re.search(r"\d", t) and HS.TU_DIA_CHI.search(t)
                and not P.detect_emirate(t) and not dia_chi_rac(t) and not _dc_la_cau_hoi(t)
                and not HS.la_cau_hoi(t)                     # câu hỏi có số nhà cũng không đè hồ sơ
                and not re.search(r"please\s+provide|information\s+below|to\s+ensure", t, re.I)):
            return t[:250]
    return None


# ═════════════════════════════════════════════════════════════════════════════
# KUWAIT ĐỂ GIÁ ĐUÔI ,9 (chủ shop 24/09, ca Dilaila Dilaila #14651: *"kuwait để ,9 cho tôi nhe"*)
# ═════════════════════════════════════════════════════════════════════════════
# Sale Kuwait lưu tiền thu BỚT 0,1 so với giá kịch bản: 19 → 18,9 · 16 → 15,9 · 11 → 10,9. Đo POS 60
# ngày tới 24/09: 1.017/1.115 đơn chat đuôi ,9; sale tự sửa số tròn → ,9 109 lần; tool tự ghi số tròn
# 29/83 đơn. Giá chốt SỐ TRÒN → trừ 0,1 lúc GHI ĐƠN; giá có số lẻ (18,9 · 7,5) giữ nguyên. CHỈ đổi tiền
# thu trên đơn — AI vẫn báo khách đúng giá kịch bản (19) như sale đang làm. Bảng giá học được lẫn cả
# 19 lẫn 18,9 cho cùng số hộp, nên tra số lượng vẫn bằng giá gốc, không có mới thử mức ,9.
DUOI_9_DON_THI_TRUONG = ("kuwait",)


def gia_duoi_9_don(gia):
    """Tiền thu ghi lên đơn: thị trường trong DUOI_9_DON_THI_TRUONG + giá SỐ TRÒN → trừ 0,1."""
    if not gia or (MK or {}).get("key") not in DUOI_9_DON_THI_TRUONG:
        return gia
    sc = P.CURRENCY_SCALE or 1
    if sc < 10 or gia % sc:
        return gia
    return gia - sc // 10


_KB_BANG = {}          # đường dẫn kich_ban.json -> (mtime, kịch bản, {pid: bảng})


def _kich_ban_dung_tien(kb_page):
    """Kịch bản ghi giá bằng tiền tệ của thị trường ĐANG CHẠY, và tiền đó nhiều nhất? kich_ban.json mỗi nước lẫn page nước
    khác ("SmileFit Denture Saudi" trong kich_ban Kuwait ghi "99 SAR" — đọc thành 99 KWD là lên đơn gấp ~12 lần)."""
    txt = " " + json.dumps(kb_page, ensure_ascii=False) + " "
    dem = {}
    for k, m in MARKETS.items():
        tu = m.get("tu_tien_te") or ""
        if isinstance(tu, (list, tuple)):
            tu = "|".join(map(re.escape, tu))
        n = len(re.findall(r"\d\s*(?:" + tu + r")(?![A-Za-z])", txt, re.I)) if tu else 0
        if m.get("ky_hieu_truoc"):      # "$" dính sau chữ ("NT$1290") không phải đô Mỹ
            n += len(re.findall(r"(?<![A-Za-z])(?:" + m["ky_hieu_truoc"] + r")\s*\d", txt, re.I))
        dem[k] = n
    toi = dem.get((MK or {}).get("key"), 0)
    # Phải NHIỀU HƠN HẲN mọi nước KHÁC tiền: "riyal"/"ريال" chung Saudi-Qatar-Oman, "dinar" chung Kuwait-Bahrain — hoà
    # là không biết tiền nào → không dùng bảng kịch bản (Oman đọc nhầm giá SAR là lệch ~10 lần).
    return toi > 0 and all(toi > n for k, n in dem.items()
                           if k != (MK or {}).get("key") and MARKETS[k].get("tien_te") != (MK or {}).get("tien_te"))


def bang_gia_kich_ban(page_id):
    """{"<giá POS>": số lượng} đọc từ KỊCH BẢN page — dòng bảng giá theo đơn vị ("13 BHD for 1 Set") + dòng gói mua-tặng
    ("Buy 1 Get 1 — 99 AED" = 2 cái), đúng hàm cổng chặn dùng để soát giá AI báo. Một giá ứng 2 số lượng khác nhau → bỏ
    giá đó. Chỉ dùng khi page CHƯA có bảng học từ đơn thật (BANG_KB_2409)."""
    import chan_gui as CG
    f = os.path.join(Q.STATE_DIR, "kich_ban.json")
    try:
        mt = os.path.getmtime(f)
        if (_KB_BANG.get(f) or (None,))[0] != mt:
            _KB_BANG[f] = (mt, json.load(open(f, encoding="utf-8")), {})
        _mt, kb, nho = _KB_BANG[f]
        pid = str(page_id)
        if pid not in nho:
            kb_page = kb.get(pid) or {}
            ra = {}
            if isinstance(kb_page, dict) and kb_page and _kich_ban_dung_tien(kb_page):
                cap = [(sl, g) for sl, gs in CG._bang_don_vi(kb_page).items() for g in gs]
                cap += [(a + b, g) for (a, b), gs in CG.bang_goi_gia(kb_page).items() for g in gs]
                for sl, g in cap:
                    ra.setdefault(str(int(round(float(g) * P.CURRENCY_SCALE))), set()).add(sl)
            nho[pid] = {k: next(iter(v)) for k, v in ra.items() if len(v) == 1}
        return dict(nho[pid])
    except Exception:                                    # noqa: BLE001
        return {}


# ═════════════════════════════════════════════════════════════════════════════
# ĐƠN CHAT ĐIỀN ĐỦ CẤP ĐỊA GIỚI (DIA_GIOI_2509 — chủ shop 25/09: "phải lên đủ cấp để đẩy đơn, bạn chỉ mới chọn tỉnh")
# ═════════════════════════════════════════════════════════════════════════════
# Bộ dò = bộ dò đơn landing (don_landing.doc_don) + 2 cửa của cap_dia_chi: bỏ khoá trùng tên TỈNH ("Mishref, Hawalli" —
# Hawalli vừa là tỉnh vừa là tên một quận) và bỏ tên ĐƯỜNG ("Jarir Street"). Đo 20 ngày đơn chat có quận do người chọn:
# UAE 124/132 · Saudi 104/117 · Kuwait 20/25 · Bahrain 7/9 trùng; lệch đều trong cùng tỉnh. Không chắc → để trống.
# ĐÀI chưa bật: "Yongkang Dist, Tainan" ra quận sai + xã lấy từ tên đường "Zhongshan E Rd"; địa chỉ chữ Hán không đọc được.
DIA_GIOI_THI_TRUONG = ("uae", "saudi", "kuwait", "qatar", "oman", "bahrain")
_R_TEN_DUONG = r"\s+(?:road|rd|street|st|str|avenue|ave|way|highway|hwy)\b"


def dia_gioi_du_cap(dc, tinh_id=None):
    """(province_id, district_id, commune_id) dò từ chuỗi địa chỉ; `tinh_id` = tỉnh đã có trên đơn (chữ không ghi tỉnh)."""
    import don_landing as L
    if ((getattr(L.A, "MK", None) or {}).get("key")) != MK["key"]:
        L.A.set_market(MK["key"])      # daemon: don_landing nhập BẢN THỨ HAI của module này — MK có thể kẹt nước khác
    L._MKEY = MK["key"]
    lines = [x.strip() for x in re.split(r"[,\n|،]| - ", str(dc or "")) if x.strip()]
    if not lines:
        return tinh_id, None, None
    chu = P.norm_ascii(re.sub(r"[^\w\s]", " ", str(dc)))
    tinh = P.detect_emirate(", ".join(lines)) or tinh_id
    if not tinh:
        tinh, _cach = L.do_tinh(lines)
    quan = xa = None
    if not tinh:
        p, d, c, _t = L.do_khu_toan(lines)
        if p:
            tinh, quan, xa = p, d, c
    if tinh and not quan:
        bang = L.bang_quan_huyen()
        tinh_keys = _tinh_goc(bang)
        for loc_tinh in (True, False):          # bỏ khoá trùng tên tỉnh trước; không ra mới cho phép
            ung = [(did, [k for k in keys if not (loc_tinh and k in tinh_keys)])
                   for p, keys, did in bang if p == tinh and did]
            _id, ten = L._do_dia_danh(lines, [(d, ks) for d, ks in ung if ks], gan_dung=True)
            if _id and ten and "≈" not in ten and re.search(rf"\b{re.escape(ten)}" + _R_TEN_DUONG, chu):
                _id = None                      # 'Jarir Street' là tên đường, không phải quận
            if _id:
                quan = _id
                break
        if quan:
            xa, _ = L._do_dia_danh(lines, L.bang_xa(quan))
        else:
            _p, quan, xa, _t = L.do_khu_toan(lines, trong_tinh=tinh)
    return tinh, quan, xa


def _dien_dia_gioi(sa, dc, ghi=None):
    """Điền quận/huyện (+ phường/xã) vào khối shipping_address SẮP GỬI POS. Tỉnh đã có trên khối mà khác tỉnh dò từ chữ
    (sale chọn tay) → không đụng. True = có điền thêm quận."""
    if sa is None or not dc or (MK or {}).get("key") not in DIA_GIOI_THI_TRUONG:
        return False
    try:
        tinh, quan, xa = dia_gioi_du_cap(dc, sa.get("province_id"))
    except Exception as e:                               # noqa: BLE001 — dò hỏng thì để sale chọn, không làm hỏng đơn
        log(f"  ⚠ dò quận/xã hỏng ({e}) — để sale chọn")
        return False
    if not quan or (sa.get("province_id") and str(tinh) != str(sa.get("province_id"))):
        return False
    sa["province_id"] = tinh
    sa["country_code"] = sa.get("country_code") or P.COUNTRY_CODE
    sa["district_id"] = quan
    if xa:
        sa["commune_id"] = xa
    else:
        sa.pop("commune_id", None)       # xã phải thuộc đúng quận vừa chọn
    if ghi is not None:
        ghi.append("quận/huyện" + (" + phường/xã" if xa else ""))
    return True


# ═════════════════════════════════════════════════════════════════════════════
# CÂU XIN THÔNG TIN / NÓI VỀ CỬA HÀNG không phải địa chỉ khách (DIA_CHI_TIN_XIN_2509 — chủ shop 25/09 "sao phần địa chỉ lại
# cho cả 1 nùi như này", đơn #77279 Erwella Aldon · Key Jewelry Saudi)
# ═════════════════════════════════════════════════════════════════════════════
# Đường "địa chỉ từ tin xác nhận của shop" (Fallback 1 trong extract) chỉ chặn câu xin bằng tiếng Anh ("send us/me", "please"),
# nên câu AI "Paki-send na lang po ang contact number at street o building number ninyo sa Jeddah…" (Tagalog), "Just send your
# contact number and the building/villa name in Dubai…" (#50625) và "Our store: Kanz Tower… Deira, Dubai" (#50881) thành ô địa
# chỉ đơn. Đo 20 ngày: 10 đơn đi đường này, 3 rác. Mọi tin AI trong so_viec: 55 câu lọt bộ lọc cũ → bỏ CÂU xin/cửa hàng thì 12 câu
# xin thuần bị loại, 43 câu xác nhận vẫn nhận (chỉ cắt câu "Just send your number…" khỏi phần địa chỉ).
R_CAU_XIN_TT = re.compile(
    r"\b(?:just|please|kindly|can you|could you|pls|plz)\s+(?:send|share|drop|give)\b"
    r"|\bsend (?:us|me|your|the) (?:contact|number|phone|address|location|pin|full|complete|exact|building|villa|house|area|name)"
    r"|\bso (?:i|we) can (?:book|process|confirm|ship|deliver)\b"
    r"|\bpaki-?\w+|\bpwede (?:po )?(?:ba|bang)\b|\bpara ma-?(?:book|process|confirm|i-?book)\b"
    r"|\b(?:tolong|mohon)\b|\bkirimkan\b"
    r"|أرسل|ارسل|ابعث|يرجى|الرجاء"
    r"|\bour (?:store|shop|office|branch|showroom)\b|\bstore address\b|\bvisit (?:us|our)\b|محلنا|فرعنا|معرضنا", re.I | re.U)


def bo_cau_xin_tt(t):
    """Bỏ các CÂU xin thông tin / nói về cửa hàng khỏi một tin shop/AI, giữ phần còn lại (có thể rỗng)."""
    cau = re.split(r"(?<=[.!?])\s+|\n+|\s*(?:😊|💛|❤️|❤|🙏)\s*", str(t or ""))
    return " ".join(c for c in cau if c.strip() and not R_CAU_XIN_TT.search(c)).strip()


def extract(record, products):
    """Trích 5 mục từ 1 hội thoại theo luật của thị trường hiện tại."""
    msgs = record.get("tin_nhan") or []
    khach_msgs = [m for m in msgs if m.get("ai") == "khach"]
    shop_msgs = [m for m in msgs if m.get("ai") == "shop"]
    thieu, canh_bao = [], []

    # 1. SĐT — CHỈ từ tin của khách (tin shop chứa số WhatsApp/hotline của shop)
    sdt = None
    for m in reversed(khach_msgs):
        found = _sdt_ban_dia_trong(_van_sdt(m["noi_dung"]))    # PH_DIA_CHI_2509 — bỏ khúc giữa số nước ngoài
        if found:
            sdt = normalize_phone(found[-1])
            break
    if not sdt:
        # PHONE_RE chỉ biết khuôn BẢN ĐỊA nên số nước ngoài trong chat lọt hết, trong khi
        # luật user cho phép chốt đơn bằng số nước khác (thường là số Philippines) miễn có
        # WhatsApp. Quét ứng viên rộng rồi để phan_loai_sdt quyết — chỉ nhận cái nó đọc ra
        # ĐÚNG một nước, nên giá/ngày tháng trong chat không lọt.
        for m in reversed(khach_msgs):
            ngoai = [s for s in (phan_loai_sdt(u) for u in SDT_UNG_VIEN_RE.findall(_van_sdt(m["noi_dung"])))
                     if s[0] == "ngoai"]
            if not ngoai:                                # PH_DIA_CHI_2509 — số ngoài dính dấu ("#639526012280.", ",0956…,")
                ngoai = [phan_loai_sdt(u) for u in _tach_sdt_ban_dia(_van_sdt(m["noi_dung"]))[1]]
            if ngoai:
                sdt = ngoai[-1][1]
                if MK.get("sdt_bat_buoc_ban_dia"):
                    # Kuwait: số ngoại KHÔNG giao được -> vẫn ghi số vào đơn cho nhân viên
                    # thấy mà gọi, nhưng tính là THIẾU nên đơn không được tự xác nhận.
                    thieu.append(f"SĐT bản địa {MK['ten']} — khách mới chỉ cho {sdt} "
                                 f"({ngoai[-1][2]}), {MK['ten']} bắt buộc số bản địa mới đi được đơn")
                else:
                    canh_bao.append(f"SĐT nước ngoài {sdt} ({ngoai[-1][2]}) — ĐVVC liên hệ "
                                    f"qua WhatsApp số này")
                    if MK.get("ghi_chu_sdt_ngoai"):
                        canh_bao.append(MK["ghi_chu_sdt_ngoai"])
                break
    ho_so = (record.get("ho_so_khach") or [{}])[0]
    dia_chi_luu = (ho_so.get("dia_chi_da_luu") or [{}])[0]
    if not sdt and dia_chi_luu.get("sdt"):
        sdt = normalize_phone(dia_chi_luu["sdt"])
        canh_bao.append("SĐT lấy từ hồ sơ đã lưu")
        # Số lưu CHÍNH LÀ số máy đọc từ ẢNH (24/09 — ca Audrey C. Capitle #77053 / Cely Kuo #568): đơn nháp mở bằng số ảnh
        # làm hồ sơ Pancake lưu luôn số đó → lượt sau đi đường này, thôi tính THIẾU → tự xác nhận. Vẫn là số ảnh → THIẾU.
        _so_anh = re.sub(r"\D", "", normalize_phone(record.get("sdt_anh") or "") or "")
        if len(_so_anh) >= 7 and re.sub(r"\D", "", sdt or "")[-8:] == _so_anh[-8:]:
            canh_bao[-1] = f"SĐT {sdt} máy ĐỌC TỪ ẢNH khách gửi (đã vào hồ sơ lưu) — gọi kiểm trước khi giao"
            thieu.append("SĐT khách tự gõ (số hiện có là máy đọc từ ảnh — chưa tự xác nhận được)")
    if not sdt and record.get("sdt_anh"):
        # Khách gửi số BẰNG ẢNH (chụp màn hình danh bạ, hồ sơ WhatsApp, ảnh vận đơn) — 21/09.
        # Ghi vào đơn để sale thấy mà gọi, nhưng vẫn tính là THIẾU: số này máy đọc từ ảnh chứ
        # khách chưa gõ, mà sai một chữ số trong đơn COD là đơn giao hụt. Giống hệt cách Kuwait
        # xử số nước ngoài ở trên. (Đã qua cửa đọc-hai-lần-phải-khớp ở ai_sale.doc_tt_anh.)
        sdt = normalize_phone(record["sdt_anh"])
        canh_bao.append(f"SĐT {sdt} máy ĐỌC TỪ ẢNH khách gửi — gọi kiểm trước khi giao")
        thieu.append("SĐT khách tự gõ (số hiện có là máy đọc từ ảnh — chưa tự xác nhận được)")
    if not sdt:
        thieu.append("SĐT")

    # 2. Địa chỉ — ưu tiên tin khách chứa tên tỉnh/bang. Trong 6 tin gần nhất, lấy tin ĐẦY ĐỦ
    # NHẤT (nhiều chữ nhất), hoà thì lấy tin mới hơn. Bản cũ lấy tin MỚI NHẤT: ca Rolando
    # (Flat Jewelry, 10/09) khách gõ "Jon pineda 0551633641 Sharjah al nad qasimia near med
    # care hospital" rồi gõ thêm "Sharjah uae" — tool lấy "Sharjah uae", đơn bị treo
    # "địa chỉ quá sơ sài" dù khách đã cho đủ.
    diachi = None
    ung = [i for i in range(len(khach_msgs) - 1, max(-1, len(khach_msgs) - 7), -1)
           if P.detect_emirate(khach_msgs[i]["noi_dung"])]
    # Câu HỎI có tên tỉnh không bao giờ vào ô địa chỉ (19/09, #75351 "How many day in Riyadh") — xem _dc_la_cau_hoi
    cau_hoi_dc = [i for i in ung
                  if _dc_la_cau_hoi(PHONE_RE.sub("", chon_dia_chi(khach_msgs[i]["noi_dung"])).strip(" ,.-"))]
    ung = [i for i in ung if i not in cau_hoi_dc]
    for i in sorted(ung, key=lambda i: (len(PHONE_RE.sub("", khach_msgs[i]["noi_dung"]).split()), i),
                    reverse=True)[:1]:
        diachi = PHONE_RE.sub("", chon_dia_chi(khach_msgs[i]["noi_dung"])).strip(" ,.-")
        # Khách hay gõ tách làm 2 tin: "مكة المكرمة" trước rồi mới tới tên đường.
        # Chỉ gộp khi tin đang có QUÁ NGẮN (nếu không sẽ nuốt nhầm tin tán gẫu phía sau).
        if len(diachi.split()) < 5:
            for j in range(i + 1, min(i + 4, len(khach_msgs))):
                t = PHONE_RE.sub("", khach_msgs[j]["noi_dung"]).strip(" ,.-")
                if (len(t.split()) >= 3 and not KHONG_PHAI_DIA_CHI.search(t)
                        and not P.detect_emirate(t)):
                    diachi = f"{diachi}, {t}"
                    break
        break
    if not diachi:
        # Fallback 1: shop/bot thường nhắn XÁC NHẬN lại địa chỉ đầy đủ (khách chỉ trả lời "yes").
        # Chỉ nhận tin shop trông giống địa chỉ thật: có tỉnh + có số + có từ khóa địa chỉ
        # (tránh nhặt nhầm tin quảng cáo có nhắc tên thành phố).
        # Từ khoá phải là TỪ RIÊNG: bản cũ khớp 'city' trong 'Authenticity' nên tin quảng cáo
        # Botcake thành địa chỉ đơn #74149 rồi tự xác nhận (14/09/2026). Đo 30 ngày: nhánh này
        # chạy 5 lần, 2 lần lấy rác (tin quảng cáo, tin mẫu xin địa chỉ có 'Example: Riyadh...').
        DIA_CHI_TU_KHOA = re.compile(
            r"\b(?:district|street|province|villa|building|block|flat|near|exit|road|avenue|area|city|st|po box)\b",
            re.I)
        TIN_KHONG_PHAI_XAC_NHAN = re.compile(
            r"\?|\bplease\b|\bkindly\b|send (?:us|me)|\bprovide\b|make it as detail", re.I)
        for m in reversed(shop_msgs):
            t = m["noi_dung"]
            ghim = re.search(r"📍\s*([^\n📞📦🚚💵]+)", t)     # tin xác nhận kiểu "📍 địa chỉ 📞 ..."
            if ghim:
                t = ghim.group(1)
            elif dia_chi_rac(t) or TIN_KHONG_PHAI_XAC_NHAN.search(t):
                continue                                  # quảng cáo / tin mẫu xin địa chỉ
            t = bo_cau_xin_tt(t)                          # DIA_CHI_TIN_XIN_2509: bỏ câu XIN thông tin / nói về cửa hàng
            if P.detect_emirate(t) and (ghim or re.search(r"\d", t)) and DIA_CHI_TU_KHOA.search(t):
                diachi = PHONE_RE.sub("", chon_dia_chi(t)).strip(" ,.-")
                # Không cho tự xác nhận: địa chỉ khách chưa tự gõ, sale phải đọc lại
                thieu.append("sale xác nhận địa chỉ (tool lấy từ tin shop/bot, khách chưa tự gõ)")
                canh_bao.append("địa chỉ lấy từ tin xác nhận của shop — kiểm tra lại")
                break
    if not diachi:
        saved = dia_chi_luu.get("dia_chi")
        # Khách chưa có địa chỉ lưu nào → saved/dia_chi_goc đều None. Thiếu `or ""` thì goc.split văng
        # AttributeError: từ 14/09 17:53 tới 15/09 làm hỏng "lên đơn sớm" của AI Sale (ca Cucu Ella,
        # Golden Youth Beauty KSA) và giết cả vòng "lên đơn không tag" của daemon.
        goc = dia_chi_luu.get("dia_chi_goc") or saved or ""
        _manh = [x for x in goc.split(",")]
        while len(_manh) > 1 and len(_manh[-1].split()) <= 3 and P.detect_emirate(_manh[-1]):
            _manh.pop()                      # bỏ đuôi ", Baha, Baha" do đơn cũ ghép tỉnh vào
        goc = ",".join(_manh)
        # full_address trong hồ sơ luôn có đuôi ", <tỉnh>" Pancake tự ghép, nên câu chat bị lưu nhầm
        # ("…kinakabahan na Ako…, Baha" — đơn #74144, 14/09/2026) cũng "có tỉnh". Phần khách/sale gõ
        # không có tỉnh thì phải trông ra địa chỉ (có số + từ địa chỉ riêng). Đo 30 ngày: 41 đơn dùng
        # hồ sơ, luật này chỉ mất 1 (Plus Code "G8HR Q62").
        if saved and not dia_chi_rac(saved) and P.detect_emirate(saved) and (
                P.detect_emirate(goc) or (re.search(r"\d", goc) and re.search(
                    r"\b(?:district|street|villa|building|block|flat|room|road|avenue|area|st|apartment|house|near)\b",
                    goc, re.I))):
            _moi_dc = dia_chi_khach_go_moi(khach_msgs)
            if _moi_dc and not cung_cho(_moi_dc, saved,
                                        record.get("khach") or ho_so.get("ten") or dia_chi_luu.get("ten")):
                # khách vừa gõ chỗ KHÁC hồ sơ cũ (#50863, 23/09) — xem dia_chi_khach_go_moi
                diachi = _moi_dc
                canh_bao.append(f"khách vừa gõ địa chỉ MỚI, KHÁC hồ sơ cũ «{str(saved)[:100]}» — sale hỏi lại khách")
                thieu.append("tỉnh/thành (địa chỉ khách vừa gõ không có tên tỉnh — sale chọn tỉnh trên đơn)")
            else:
                diachi = saved
                canh_bao.append("địa chỉ lấy từ hồ sơ đã lưu")
                # Khách gửi địa chỉ bằng ẢNH trong hội thoại này (24/09 — ca Audrey C. Capitle #77053): nháp mở bằng địa chỉ ảnh
                # làm hồ sơ Pancake LƯU luôn địa chỉ đó → lượt sau đi đường này, thôi tính THIẾU → tự xác nhận. Cùng chỗ với
                # ảnh → vẫn là địa chỉ ảnh → THIẾU. Khác chỗ → khách vừa gửi địa chỉ MỚI bằng ảnh → giữ hồ sơ, THIẾU, sale hỏi.
                _dc_anh = record.get("dia_chi_anh")
                if _dc_anh:
                    if cung_cho(_dc_anh, saved, record.get("khach") or ho_so.get("ten") or dia_chi_luu.get("ten")):
                        canh_bao[-1] = "địa chỉ máy ĐỌC TỪ ẢNH khách gửi (đã vào hồ sơ lưu) — sale kiểm lại"
                        thieu.append("địa chỉ khách tự gõ (địa chỉ hiện có là máy đọc từ ảnh)")
                    else:
                        canh_bao.append(f"khách vừa gửi ẢNH địa chỉ KHÁC hồ sơ cũ: «{str(_dc_anh)[:120]}» — sale hỏi lại khách")
                        thieu.append("địa chỉ khách tự gõ (khách vừa gửi ẢNH địa chỉ khác hồ sơ cũ — sale hỏi lại)")
    if not diachi and record.get("dia_chi_ai"):
        # AI Sale thấy khách đã gõ địa chỉ mà KHÔNG có tên tỉnh ("Wadi side building jamaa park Khalid bin udday,
        # al jaradiya" — #75351, 19/09): bộ trích ở trên chỉ nhặt tin có tên tỉnh nên ô địa chỉ bỏ trống, chữ
        # khách chỉ nằm trong note. Nay ghi vào ô địa chỉ; không có tên tỉnh thì THIẾU → không tự xác nhận.
        diachi = record["dia_chi_ai"]
        canh_bao.append("địa chỉ AI Sale đọc từ lời khách — sale kiểm lại")
        if not P.detect_emirate(diachi):
            thieu.append("tỉnh/thành (địa chỉ khách gõ không có tên tỉnh — sale chọn tỉnh trên đơn)")
    if not diachi and record.get("dia_chi_anh"):
        # Địa chỉ khách gửi BẰNG ẢNH (21/09) — cùng lý lẽ với SĐT: ghi vào đơn, nhưng THIẾU.
        diachi = record["dia_chi_anh"]
        canh_bao.append("địa chỉ máy ĐỌC TỪ ẢNH khách gửi — sale kiểm lại")
        thieu.append("địa chỉ khách tự gõ (địa chỉ hiện có là máy đọc từ ảnh)")
    if not diachi:
        thieu.append("địa chỉ (phải có tên tỉnh/bang)" + (
            f" — khách mới HỎI, chưa cho địa chỉ: {khach_msgs[cau_hoi_dc[0]]['noi_dung'][:80]}"
            if cau_hoi_dc else ""))
    else:
        # Chỉ mỗi tên thành phố / câu tán gẫu thì shipper không giao được -> treo cho nhân viên.
        # (17/09: thay phép đếm chữ cũ bằng `dia_chi_du_giao`, xem ghi chú ở hàm đó)
        _li = dia_chi_du_giao(diachi)
        if _li:
            thieu.append(f"địa chỉ chưa đủ để giao — {_li}: {str(diachi)[:90]}")
        else:
            # Xác nhận đòi địa chỉ ĐỦ 3 CẤP: tỉnh + khu + đường/số nhà (chủ shop 18/09)
            _ok3, _li3 = dia_chi_3_cap(diachi)
            if not _ok3:
                thieu.append(f"địa chỉ chưa đủ 3 cấp — {_li3}: {str(diachi)[:90]}")

    # 3. Tên
    ten = dia_chi_luu.get("ten") or ho_so.get("ten") or record.get("khach") or "Khách Facebook"
    # Khách tự đưa tên người nhận khác tên FB → "<tên khách đưa> - <tên FB>" (chủ shop 14/09, ca An Ne)
    _ten_dua = ten_khach_dua(khach_msgs)
    # Tên người nhận khách ghi trong ẢNH cùng SĐT / địa chỉ (23/09, ca Cely Kuo — nhãn 郭仙莉 · 0901338177 · FamilyMart):
    # tên khách tự gõ có nhãn vẫn thắng. Đã qua cửa đọc-hai-lần-khớp ở ai_sale.doc_tt_anh.
    _tu_anh = not _ten_dua and bool(record.get("ten_anh"))
    if _tu_anh:
        _ten_dua = record["ten_anh"]
    _ten_ghep = ghep_ten(_ten_dua, record.get("khach") or ten)
    if _ten_ghep:
        ten = _ten_ghep
        if _tu_anh:
            canh_bao.append(f"tên người nhận {_ten_dua} máy ĐỌC TỪ ẢNH khách gửi — sale kiểm lại")

    # 4. Giá chốt — LỜI KHÁCH CHỐT trước, tin SHOP xác nhận sau; tin nào MỚI HƠN thì thắng.
    # Ca Hasan Ahmed (Skin Renew, 11/09/2026): khách gõ "Please order 1+1=99", bot promo liệt kê
    # "2 pcs — 99 AED / 4 pcs — 159 AED"; bản cũ lấy giá CUỐI trong tin shop mới nhất → 159 → 4 cái,
    # đơn tự xác nhận sai. Chủ shop: *"lên cho đúng số lượng chốt với khách"*.
    _map = products.get(str(record.get("page_id"))) or {}
    _bang = {str(k): v for k, v in (_map.get("gia_qty") or {}).items()}
    if not _bang:
        # PAGE MỚI chưa có đơn cũ (BANG_KB_2409): bảng giá đọc từ KỊCH BẢN — ca Yolly Ranara #1063 (Luxentra Gold Jewelry
        # Bahrain, "13 BHD for 1 Set / 19 BHD for 2 Sets"): AI chốt 13 BHD mà đơn lên 0 BHD.
        _bang = bang_gia_kich_ban(record.get("page_id"))
    else:
        # Bảng học THIẾU mức mà kịch bản có (page mới bán được 1 gói: {109 SAR: 2 món}) → bù đúng mức đó, KHÔNG đụng số lượng
        # bảng học đã có (BANG_KB_BU_2509, ca Ummie #77069 — "I buy 2" = Mua 2 tặng 2 159 SAR mà bảng chỉ có 109).
        _sl_co = set(_bang.values())
        for _g, _sl in bang_gia_kich_ban(record.get("page_id")).items():
            if _sl not in _sl_co and _g not in _bang:
                _bang[_g] = _sl
    gia = None
    _goi_kh = goi_cua_page(record.get("page_id"))
    gia_kh, luc_kh, ly_do_kh = gia_theo_loi_khach(khach_msgs, _bang, _goi_kh,      # HOP_POS_2509: page GÓI → kịch bản phân xử
                                                  bang_gia_kich_ban(record.get("page_id")) if _goi_kh else None)
    _nhieu_sl = gia_kh is None and str(ly_do_kh or "").startswith((NHIEU_SL, SL_CHUA_RO))   # 22/09 NHIEU_SL · 24/09 SL_CHUA_RO
    gia_shop, luc_shop = None, ""
    for m in reversed(shop_msgs):
        _chi_moi_cai = False
        for rx in PRICE_RES:
            # GIA_MOI_CAI_2609: "…best price, only 119.5 SAR each" là giá MỖI CÁI → bỏ; tin mới nhất nêu tiền mà CHỈ có giá
            # mỗi cái thì dừng ở đó (không lùi về câu báo giá cũ hơn — tổng tiền để lời khách / bảng giá / sale quyết)
            _hs = list(rx.finditer(m["noi_dung"]))
            hit = next((h for h in _hs if not gia_moi_cai(m["noi_dung"], h)), None)
            if hit:
                gia_shop, luc_shop = P.parse_money(hit.group(1)), str(m.get("luc") or "")
                break
            if _hs:
                _chi_moi_cai = True
                break
        if _chi_moi_cai:
            break
        if gia_shop is not None:
            break
    if gia_kh is not None and (gia_shop is None or str(luc_kh) >= str(luc_shop)):
        gia = gia_kh
        _bao_lai = gia_page_bao_lai(shop_msgs, luc_kh, gia_kh, _bang)      # 23/09, ca Jhomar #76371
        if _bao_lai:
            gia = _bao_lai[0]
            canh_bao.append(f"giá chốt {P.fmt_money(gia)} — page báo lại sau lời khách {_bao_lai[1]}; "
                            f"khách từng nhắc {P.fmt_money(gia_kh)} ({ly_do_kh})")
        else:
            canh_bao.append(f"giá chốt {P.fmt_money(gia)} theo lời khách ({ly_do_kh})")
    elif gia_shop is not None and not (_nhieu_sl and str(luc_shop) < str(luc_kh or "")):
        gia = gia_shop
    # KHÁCH TRẢ GIÁ ≥ SÀN mà AI/sale ĐÃ NHẬN (AI Sale truyền record["gia_mac_ca"] — chủ shop 19/09, ca Rinku Ray: giá
    # 109, khách "100 được không" → nhận 100). Thắng mọi con số page báo (Botcake nhắc lại promo không tính — sale mặc cả
    # ngược thì ai_sale đã không truyền); khách chốt mức khác SAU lúc nhận thì mức mới thắng.
    _mc = record.get("gia_mac_ca") or {}
    gia_mc = P.parse_money(str(_mc["gia"])) if _mc.get("gia") else None
    if gia_mc is not None and (gia_kh is None or str(_mc.get("luc") or "") >= str(luc_kh or "")) \
            and not (_nhieu_sl and str(_mc.get("luc") or "") < str(luc_kh or "")):
        gia = gia_mc
        canh_bao.append(f"giá chốt {P.fmt_money(gia)} — khách trả giá, page đã nhận "
                        f"(gói {_mc.get('goc')}, sàn {_mc.get('san')})")
    if gia is None:
        # PRICE_RES đòi chữ khoá (order/total/price...) đứng trước số. AI Sale hay sale nói
        # "It's 109 AED for 1 necklace" → không khớp → đơn 0 AED (ca Rolando 10/09/2026).
        # Vớt lại bằng cách NEO vào bảng giá đã học của page: chỉ nhận con số có kèm tên
        # tiền tệ VÀ trùng đúng một mức giá page từng bán — "5.3g", "750" hallmark không lọt.
        # Tin shop nêu NHIỀU mức (promo "99 / 159") mà khách chưa chọn → KHÔNG đoán, để THIẾU
        # cho sale hỏi (chủ shop 11/09: đoán mức cao là đơn sai số lượng).
        if _bang:
            _tu = MK.get("tu_tien_te") or ""          # markets.json: chuỗi regex "aed|dhs|dirhams?|درهم"
            if isinstance(_tu, (list, tuple)):
                _tu = "|".join(map(re.escape, _tu))
            _rx = re.compile(r"(\d[\d.,]*)\s*(?:" + _tu + r")\b", re.I | re.U) if _tu else None
            for m in reversed(shop_msgs):
                if not _rx:
                    break
                if _nhieu_sl and str(m.get("luc") or "") < str(luc_kh or ""):
                    break                      # câu báo giá cũ hơn tin khách liệt kê nhiều dòng — không dùng
                _hs = [(P.parse_money(h.group(1)), gia_moi_cai(m["noi_dung"], h)) for h in _rx.finditer(m["noi_dung"])]
                _mc = list(dict.fromkeys(g for g, mc in _hs if mc and g is not None and str(g) in _bang))
                if _mc:
                    # GIA_MOI_CAI_2609: giá MỖI CÁI trùng một mức bảng giá — hoặc là lựa chọn ("Each set is 199 SAR, or 2 sets
                    # for 299"), hoặc là đơn giá của đơn nhiều cái ("2 Golden Buddha — 149 AED bawat isa") → KHÔNG đoán tổng
                    thieu.append("giá chốt (page nêu giá mỗi cái " + " / ".join(P.fmt_money(g) for g in _mc)
                                 + " — chưa có tổng, sale tính theo số lượng)")
                    break
                cac = [g for g, mc in _hs if not mc]
                cac = list(dict.fromkeys(g for g in cac if g is not None and str(g) in _bang))
                if len(cac) == 1:
                    gia = cac[0]
                    canh_bao.append(f"giá chốt {P.fmt_money(gia)} lấy từ câu báo giá (không có chữ 'total') — khớp bảng giá page")
                    break
                if len(cac) > 1:
                    thieu.append("giá chốt (page báo nhiều mức "
                                 + " / ".join(P.fmt_money(g) for g in cac)
                                 + " — khách chưa chọn combo nào)")
                    break
    if gia is None and _nhieu_sl:
        if str(ly_do_kh).startswith(NHIEU_SL):
            thieu.append(f"giá chốt — {str(ly_do_kh)[len(NHIEU_SL):]} — sale cộng tổng rồi lên giá")
        elif not any(x.startswith("giá chốt") for x in thieu):
            thieu.append(f"giá chốt — {str(ly_do_kh)[len(SL_CHUA_RO):]} — sale hỏi lại khách chọn gói")
    if gia is None and not any(t.startswith("giá chốt") for t in thieu):
        thieu.append("giá chốt (shop chưa nhắn xác nhận tổng tiền)")

    # 5. Sản phẩm + số lượng — bảng đã học của page
    page_id = str(record.get("page_id"))
    variation_id = qty = None
    mapping = products.get(page_id)
    if mapping and _bang and _bang != (mapping.get("gia_qty") or {}):
        mapping = dict(mapping, gia_qty=_bang)       # tra số lượng theo bảng đã bù kịch bản (BANG_KB_2409 + BANG_KB_BU_2509)
    # Bảng đã học còn dính đơn test -> TREO đơn cho nhân viên check,
    # KHÔNG đẩy sản phẩm rác sang vận chuyển (vẫn ghi tên vào note để nhân viên biết đường lần)
    sp_test = bool(mapping) and la_sp_test(mapping.get("ten"))
    if sp_test:
        thieu.append(f"sản phẩm nghi là hàng TEST ({mapping.get('ten')}) — "
                     f"nhân viên chọn SP đúng, rồi xoá đơn test và chạy lại hoc-san-pham")
    elif mapping:
        variation_id = mapping["variation_id"]
        # Sản phẩm nhiều mẫu mã -> phải chọn ĐÚNG mẫu khách chốt (tìm trong tin của khách)
        mau_ma = mapping.get("mau_ma") or []
        if len(mau_ma) > 1:
            # Tên mẫu mã trong kho hay sai chính tả ("Aprill", "Decemberr") -> rút gọn chữ lặp
            # ở CẢ HAI phía để khách gõ đúng vẫn khớp
            gon = lambda s: re.sub(r"(.)\1+", r"\1", P.norm_ascii(s))
            loi_khach = gon(" ".join(m["noi_dung"] for m in khach_msgs))
            khop = [mm for mm in mau_ma
                    if re.search(r"\b" + re.escape(gon(mm["ten"])) + r"\b", loi_khach)]
            if len(khop) == 1:
                variation_id = khop[0]["id"]
                canh_bao.append(f"mẫu mã: {khop[0]['ten']}")
            else:
                variation_id = None
                thieu.append("mẫu mã ({}) — khách chọn: {}".format(
                    "chưa rõ" if not khop else "khớp nhiều mẫu",
                    ", ".join(m["ten"] for m in khop) or "?"))
        if gia is not None:
            qty = mapping["gia_qty"].get(str(gia))
            if qty is None and gia_duoi_9_don(gia) != gia:
                qty = mapping["gia_qty"].get(str(gia_duoi_9_don(gia)))   # Kuwait: bảng chỉ có 12,9, chat báo 13
            if qty is None and gia_mc is not None and gia == gia_mc:
                # giá mặc cả không có trong bảng đã học → số lượng theo GÓI khách mặc cả
                qty = mapping["gia_qty"].get(str(P.parse_money(str(_mc.get("goc")))))
            if qty is None:
                if len(set(mapping["gia_qty"].values())) == 1:
                    qty = next(iter(mapping["gia_qty"].values()))
                    canh_bao.append(f"giá {P.fmt_money(gia)} chưa gặp trên page, số lượng theo mặc định page")
                else:
                    thieu.append(f"số lượng (giá {P.fmt_money(gia)} chưa từng gặp trên page này)")
        else:
            thieu.append("số lượng (chưa biết giá chốt)")
    else:
        thieu.append("sản phẩm (page chưa chốt được SKU — xem: auto_len_don.py bao-cao)")

    # 6. Kuwait để đuôi ,9 (xem DUOI_9_DON_THI_TRUONG) — đổi SAU khi tra số lượng. Dòng "giá chốt …" ghi cả
    # giá gốc để sale đối được với câu đã nhắn khách ("Your order is 19 KWD").
    _g9 = gia_duoi_9_don(gia)
    if _g9 != gia:
        _cu = f"giá chốt {P.fmt_money(gia)}"
        canh_bao = [c.replace(_cu, f"giá chốt {P.fmt_money(_g9)} (gốc {P.fmt_money(gia)}, Kuwait để ,9)", 1)
                    if c.startswith(_cu) else c for c in canh_bao]
        gia = _g9

    return {"ten": ten, "sdt": sdt, "diachi": diachi, "variation_id": variation_id,
            "qty": qty, "gia": gia, "ten_sp": (mapping or {}).get("ten"),
            "them_hop": bool(MK.get("hop_id")) and MK.get("dung_hop", True) and bool(
                (mapping or {}).get("co_hop") or la_trang_suc((mapping or {}).get("ten"))),
            "thieu": thieu, "canh_bao": canh_bao}


# ═════════════════════════════════════════════════════════════════════════════
# POS TỰ GẮN HÀNG vào nháp máy (HOP_POS_2509 — chủ shop 25/09 "Noor Hossain Zakir Hossain bán trà thảo dược nhưng AI lên
# đơn lại thêm hộp trang sức", #77377 · Nature's Daily Care in Saudi)
# ═════════════════════════════════════════════════════════════════════════════
# Máy chưa rõ số lượng thì tạo nháp KHÔNG gửi dòng hàng; POS tự gắn hàng theo hội thoại / bài QC khách bấm. Đo 10 ngày:
# ~1.000 nháp được gắn đúng SP page (sale giữ). Ca SAI LOẠI: "BOX" vào đơn trà (#77377, #77111 — khách gõ "1box"), "010 -
# Birth Stone Set" vào page trà / kem / gel / thuốc nhỏ răng (10 nháp Saudi, sale phải xoá tay). Page bán SP KHÔNG phải
# trang sức (không kèm hộp) → bỏ các dòng HỘP / TRANG SỨC khác SP page. Page trang sức, SP page chưa rõ → không đụng.
R_TEN_HOP = re.compile(r"\bbox(?:es)?\b|hộp|盒", re.I)


def hang_pos_gan_thua(items, ex):
    """Dòng hàng HỘP / TRANG SỨC khác SP page trên nháp của page bán SP không phải trang sức → [dòng cần bỏ]."""
    ten = ex.get("ten_sp") or ""
    if not ex.get("variation_id") or not ten or ex.get("them_hop") or la_trang_suc(ten) or R_TEN_HOP.search(ten):
        return []
    bo = []
    for it in items or []:
        t = (it.get("variation_info") or {}).get("name") or ""
        if it.get("variation_id") != ex["variation_id"] and (
                it.get("variation_id") == MK.get("hop_id") or R_TEN_HOP.search(t) or la_trang_suc(t)):
            bo.append(it)
    return bo


def _ten_dong(ds):
    return [f"{(it.get('variation_info') or {}).get('name') or it.get('variation_id')} x{it.get('quantity')}" for it in ds]


def _giu_dong(items, bo):
    """Dòng hàng còn lại sau khi bỏ `bo`, đúng dạng body PUT (giá SP để 0 — tiền thu nằm ở phí vận chuyển)."""
    bo_id = {id(x) for x in bo}
    return [{"variation_id": it.get("variation_id"), "quantity": it.get("quantity") or 1, "variation_info": {"retail_price": 0}}
            for it in items or [] if id(it) not in bo_id]


def items_va_ship(ex):
    """Quy ước của shop: TIỀN THU nằm ở PHÍ VẬN CHUYỂN, giá sản phẩm để 0.
    Trang sức thì kèm hộp 008."""
    items = [{"variation_id": ex["variation_id"], "quantity": ex["qty"],
              "variation_info": {"retail_price": 0}}]
    if ex.get("them_hop"):
        # Số lượng hộp = số lượng hàng, không phải cứ 1 hộp/đơn: đo 425 đơn có hộp trong
        # 30 ngày thì 410 đơn đi đúng tỉ lệ 1:1 (x1/x1 285 đơn, x2/x2 118 đơn).
        items.append({"variation_id": MK["hop_id"], "quantity": ex["qty"] or 1,
                      "variation_info": {"retail_price": 0}})
    return items


# ---------------- Chống trùng + tạo/sửa đơn ----------------

# Đơn đã đi xa (gửi hàng/nhận/hoàn/hủy) = thương vụ CŨ đã xong.
# Khách nhắn lại trong chính hội thoại đó là mua ĐỢT MỚI -> phải lên đơn mới, không sửa đơn cũ.
TRANG_THAI_DA_XONG = {2, 3, 16, 4, 15, 5, 6, 7}


# ═════════════════════════════════════════════════════════════════════════════
# SỔ NHỚ: HỘI THOẠI NÀO → ĐƠN NÀO
# ═════════════════════════════════════════════════════════════════════════════
# Chủ shop chốt 2026-09-08: *"khách mới cho SĐT, sale hoặc bạn tự tạo trước đó trong cùng 1
# page → tạo đơn mới; khi khách cung cấp thêm thông tin thì UPDATE TIẾP ĐƠN ĐÓ, không tạo lại
# một đơn khác."*
#
# Trước đây muốn biết "hội thoại này đã có đơn chưa" phải hỏi POS và lật 300 đơn gần nhất —
# vừa chậm (12 giây cho một hội thoại) vừa mong manh: đơn tạo quá 14 ngày là rơi khỏi cửa
# sổ tìm kiếm, tool tưởng chưa có đơn rồi tạo thêm cái nữa.
# Sổ này nhớ thẳng: hội thoại ↔ đơn. Nhớ rồi thì lần sau đi đúng vào đơn đó.
#
# Sổ chỉ là ĐƯỜNG TẮT, không phải nguồn sự thật: nhớ nhầm/đơn bị xoá thì vẫn rơi về đường
# hỏi POS như cũ. Mất sổ cũng không sinh đơn trùng.

def _f_so_don():
    return os.path.join(Q.STATE_DIR, "don_theo_hoi_thoai.json")


def nho_don(conv_id, order):
    """Ghi nhớ hội thoại này đã gắn với đơn nào."""
    if not (conv_id and order):
        return
    try:
        d = Q.load_json(_f_so_don(), {})
        d[str(conv_id)] = {"id": order.get("id"),
                           "ma": order.get("display_id") or order.get("id"),
                           "page_id": str(order.get("page_id") or ""),
                           "luc": int(time.time())}
        Q.save_json(_f_so_don(), d)
    except Exception as e:                               # noqa: BLE001 — sổ hỏng không giết vòng
        log(f"  ⚠️  không ghi được sổ đơn: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# KHÁCH ĐÃ MUA Ở PAGE NÀY CHƯA — cửa chặn mạnh nhất
# ═════════════════════════════════════════════════════════════════════════════
# Chủ shop chốt 2026-09-09: *"chỉ tư vấn khi khách CHƯA có lịch sử mua hàng của page đó.
# Khách đã mua, chốt đơn xong thì AI không vào rep nữa, toàn bộ sau thời điểm đó nhân viên
# xử lý — đỡ tốn chi phí và tránh tạo thêm đơn vô lý."*
#
# CA THẬT ĐẺ RA LUẬT NÀY (09/09/2026): vòng quét không-cần-tag tạo đơn #49313 cho khách
# Clarito Nacario, trong khi CHÍNH hội thoại đó đã có đơn #47600 của sale từ 24/08, đã thu
# tiền. Ba lỗi chồng nhau:
#   ① `find_existing` chỉ nhìn lại 14 ngày — đơn 16 ngày tuổi nằm ngoài tầm.
#   ② Đơn "Đã thu tiền" bị xếp vào "khách mua đợt mới" nên vẫn tạo đơn mới. Luật đó ĐÚNG với
#      luồng cũ (sale phải gắn lại tag mới có đơn mới) nhưng SAI khi bỏ tag.
#   ③ Tìm theo SĐT mà KÈM mốc thời gian chỉ ra 1 đơn; bỏ mốc ra đủ 5 đơn.
# Nên cửa này KHÔNG dùng cửa sổ thời gian, và coi MỌI đơn — kể cả đơn đã đi xong — là bằng
# chứng "khách này đã mua ở page này rồi".

# ═════════════════════════════════════════════════════════════════════════════
# THẺ HỘI THOẠI — cửa RẺ NHẤT và CHẮC NHẤT
# ═════════════════════════════════════════════════════════════════════════════
# Chủ shop giải nghĩa thẻ, 2026-09-09:
#   · "Đã gửi"   = CHỐT ĐƠN THÀNH CÔNG, đã tạo đơn  -> DỪNG, không đụng hội thoại nữa
#   · "Mua hàng" = khách tiềm năng sắp ra đơn        -> KHÔNG phải thẻ dừng, đây là tín hiệu TỐT
#
# Vì sao lớp này quý hơn mọi lớp khác: nó là kết luận của NGƯỜI, đọc miễn phí (đi kèm danh
# sách hội thoại, không tốn thêm lượt gọi API nào), và không suy diễn từ SĐT hay tên.
# Đo trên 4 ca thật: Arlene Cantero và Elle Chim (đều đã có đơn) mang thẻ "Đã gửi";
# Jori Khan và MD Ahasan (khách mới) không mang thẻ nào.
#
# Thêm thẻ dừng thì sửa danh sách này. Đừng thêm "Mua hàng" vào — nó nghĩa ngược lại.

THE_DUNG = {"đã gửi", "da gui"}


def _chuan_the(t):
    return " ".join(str(t or "").lower().split())


def co_don_bat_ky(conv_id=None, sdt_list=None, ten=None):
    """POS có BẤT KỲ đơn nào (mọi trạng thái, kể cả hủy / nháp) cho hội thoại / SĐT / tên này không?

    Dùng RIÊNG cho cửa thẻ "Đã gửi" (chủ shop 2026-09-14, ca Sarah Nak Rantau — Kreain Nature PH
    in Uae): khách gửi tên + địa chỉ + SĐT 12:52:51, sale Thu Hiền gửi tin "Your order is 99 AED"
    và gắn thẻ "Đã gửi" 12:53:10 — TRƯỚC khi có đơn. AI Sale và daemon đều tin thẻ = đã có đơn nên
    bỏ qua; 13:32 sale Từ Trang mới tự tạo. *"sao đơn này b k lên đơn"*.
    Nên thẻ chỉ là "xong" khi POS có đơn thật. Cố ý RỘNG hơn da_mua_o_page: tính cả đơn hủy
    (sale đã xử, không đẻ lại đơn — đo 14/09: 2/104 hội thoại thẻ Đã gửi chỉ có đơn hủy) và không
    đòi cùng page. Rộng = dừng như luật cũ; chỉ khi KHÔNG ra đơn nào mới coi là thẻ gắn sớm.
    Tra lỗi → trả True (giữ luật cũ: thà chậm một đơn còn hơn đẻ đơn trùng).
    """
    try:
        # Sổ của tool (hội thoại → đơn đã tạo/bổ sung), đọc thẳng file — KHÔNG gọi don_da_nho():
        # hàm đó trả một cặp (luôn "đúng") và bỏ qua đơn đã đi xong.
        if conv_id and (Q.load_json(_f_so_don(), {}).get(str(conv_id)) or {}).get("id"):
            return True
        import unicodedata as _u
        def chu(t):
            t = "".join(c for c in _u.normalize("NFKD", str(t or "")) if not _u.combining(c))
            return {w for w in re.findall(r"[^\W\d_]{2,}", t.lower())}
        # POS KHÔNG tìm theo mã hội thoại (đo 14/09: đơn #49916 mang conversation_id mà search ra 0)
        # — khoá thật là SĐT + tên; mã hội thoại chỉ đi qua sổ don_theo_hoi_thoai.json ở trên.
        khoas = [("sdt", re.sub(r"\D", "", str(x or ""))) for x in (sdt_list or [])]
        if ten:
            khoas.append(("ten", str(ten).strip()))
        for loai, khoa in dict.fromkeys(khoas):
            if not khoa or len(khoa) < 4:
                continue
            for o in P.fetch_orders({"page_size": 50, "page_number": 1, "search": khoa}):
                if loai == "conv" and str(o.get("conversation_id") or "") != str(conv_id):
                    continue
                if loai == "ten" and not (chu(ten) and chu(ten) <= (chu(o.get("bill_full_name"))
                                                                     | chu((o.get("customer") or {}).get("name")))):
                    continue
                return True
        return False
    except Exception:                                    # noqa: BLE001
        return True


def so_cua_hoi_thoai(conv):
    """Mọi SĐT API từng ghi nhận trong hội thoại (recent_phone_numbers của hội thoại + khách)."""
    so = [x.get("captured") or x.get("phone_number") for x in (conv.get("recent_phone_numbers") or [])]
    for c2 in (conv.get("customers") or []):
        so += [x.get("phone_number") for x in (c2.get("recent_phone_numbers") or [])]
    return [x for x in so if x]


def the_noi_da_xong(conv):
    """Hội thoại có thẻ nói 'đã chốt đơn xong' không? Trả tên thẻ, hoặc None."""
    for t in (conv.get("tags") or []):
        if t and _chuan_the(t.get("text")) in THE_DUNG:
            return t.get("text")
    return None


def _chu_ten(t):
    t = "".join(c for c in unicodedata.normalize("NFKD", str(t or "")) if not unicodedata.combining(c))
    return {w for w in re.findall(r"[^\W\d_]{2,}", t.lower())}


def _ten_khop_du(ten_fb, o):
    """Mọi chữ (≥2 ký tự) của tên Facebook đều có trong tên trên đơn."""
    can = _chu_ten(ten_fb)
    co = _chu_ten(o.get("bill_full_name")) | _chu_ten((o.get("customer") or {}).get("name"))
    return bool(can) and can <= co


def _page_tu_ma_khach(o):
    """Page của đơn suy từ mã khách Facebook / hội thoại dạng "<page_id>_<psid>"; không có thì ""."""
    for v in ((o.get("customer") or {}).get("fb_id"), o.get("conversation_id")):
        m = re.match(r"^(\d{10,20})_\d+$", str(v or ""))
        if m:
            return m.group(1)
    return ""


def da_mua_o_page(page_id, conv_id=None, sdt=None, ten=None, sdt_them=None):
    """Khách này đã từng có đơn chưa? Trả (rồi?, mô tả đơn gần nhất).

    Tra bằng BA khoá, khoá nào ra đơn cũng tính:
      · conversation_id — chắc nhất
      · SĐT khách vừa cho
      · TÊN khách trên Facebook

    ⚠️ VÌ SAO PHẢI CÓ TÊN VÀ MỌI SỐ (đo thật 09/09/2026): khách hay cho NHIỀU số trong cùng
    một tin — Arlene Cantero nhắn "Contact number: 0506051046 / 0565979121 watsapp". Sale lên
    đơn #48962 bằng số ĐẦU, bộ trích của tool bắt số SAU, nên tra theo số của tool là không ra
    đơn nào, và vòng quét định tạo đơn thứ tư cho khách đã có ba đơn.
    Chủ shop chốt: *"phải xem nguồn đơn — đơn đã được tạo rồi thì không tạo nữa, dù sale dùng
    số khác. Tạo bằng số khác của cùng khách, cùng page là trùng lặp đơn."*

    Nên `sdt_them` nhận TOÀN BỘ số hội thoại từng ghi nhận (`recent_phone_numbers` của API),
    không phải mỗi số bộ trích chọn ra.

    KHÔNG giới hạn thời gian: khách mua 3 tháng trước vẫn là khách đã mua.
    """
    try:
        ds, da, loai_khoa = [], set(), {}
        khoas = [("conv", str(conv_id or "")), ("sdt", str(sdt or "")), ("ten", str(ten or "").strip())]
        khoas += [("sdt", str(x)) for x in (sdt_them or []) if x]
        for loai, khoa in dict.fromkeys(khoas):  # bỏ trùng, giữ thứ tự
            if not khoa or len(khoa) < 4:
                continue
            for o in P.fetch_orders({"page_size": 100, "page_number": 1, "search": khoa}):
                loai_khoa.setdefault(o.get("id"), set()).add(loai)
                if o.get("id") not in da:
                    da.add(o.get("id"))
                    ds.append(o)
        for o in ds:
            # KHỚP CHỈ BẰNG TÊN phải khớp ĐỦ từng chữ (chủ shop 2026-09-14, ca Dai Sy / Veloura Collection):
            # POS tìm "Dai Sy" bỏ dấu cách → ra đơn #49140 của "Daisy montemayor" (page khác) → AI im với
            # khách mới hỏi "Ilang days po delivery?". *"sao khách này b k rep"*. Mọi chữ của tên Facebook
            # phải là một chữ trong tên trên đơn (tên bill / tên khách POS).
            if loai_khoa.get(o.get("id")) == {"ten"} and not _ten_khop_du(ten, o):
                continue
            # Đơn ĐÃ HỦY / ĐÃ XÓA không tính là "khách đã mua": thương vụ không thành, khách
            # vẫn là khách mới. Tính chúng vào là khoá AI vĩnh viễn chỉ vì một đơn hỏng.
            if o.get("status") in (6, 7):
                continue
            # Đơn NHÁP do chính tool tạo lúc khách mới cho SĐT/địa chỉ (còn "Mới", note "[Tự động]")
            # cũng KHÔNG phải "đã mua": thương vụ đang chốt dở. Chủ shop 2026-09-11: có SĐT hoặc
            # địa chỉ là tạo trước, phần thiếu bổ sung sau — nếu tính nháp là "đã mua" thì AI im
            # ngay sau khi tạo nháp, không ai hỏi tiếp khách phần còn thiếu. Nháp lên "Đã xác
            # nhận" (đủ thông tin) hay sale đụng vào rồi thì lại tính là đã mua như cũ.
            if o.get("status") == 0 and la_don_nhap_cua_tool(o):
                continue
            # Đơn không ghi page_id vẫn thường mang mã khách Facebook "<page_id>_<psid>" (đơn sale tạo từ
            # hội thoại) → lấy page từ đó. Ra page KHÁC thì không phải "đã mua ở page này" (ca Dai Sy 14/09:
            # #49140 mang fb_id của Golden Buddha Blessings, khách đang hỏi ở Veloura Collection).
            don_page = str(o.get("page_id") or "") or _page_tu_ma_khach(o)
            if don_page and page_id and don_page != str(page_id) and not (
                    conv_id and str(o.get("conversation_id") or "") == str(conv_id)):
                continue
            cung_conv = conv_id and str(o.get("conversation_id") or "") == str(conv_id)
            cung_page = page_id and don_page == str(page_id)
            # ⚠️ KHÔNG RÕ PAGE THÌ CHẶN, KHÔNG THẢ. Đơn sale tạo tay và đơn từ trang bán hàng
            # KHÔNG mang `page_id` — đo thật 09/09: khách Felsa Babor có 10 đơn, trong đó
            # #48510 đang "Chờ in", nhưng 8/10 đơn có page_id = None nên cửa đòi "cùng page"
            # thả qua hết, và vòng quét định tạo thêm đơn thứ 11.
            # Chặn nhầm chỉ mất một cơ hội tư vấn; thả nhầm là đẻ đơn rác trên POS thật.
            khong_ro_page = not don_page
            if cung_conv or cung_page or khong_ro_page:
                vi = ("cùng hội thoại" if cung_conv else
                      "cùng page" if cung_page else "đơn không ghi page — chặn cho chắc")
                vi += f", khách {(o.get('bill_full_name') or '?')[:22]}"
                return True, (f"#{o.get('display_id') or o.get('id')} "
                              f"({P.STATUS_BY_CODE.get(o.get('status'), o.get('status'))}, "
                              f"{(o.get('inserted_at') or '')[:10]}, {vi})")
    except Exception as e:                               # noqa: BLE001
        log(f"  ⚠️  không tra được lịch sử mua: {e}")
    return False, None


def don_da_nho(conv_id):
    """Đơn đã nhớ cho hội thoại này — đọc thẳng từ POS đúng MỘT đơn.

    Trả (đơn, lý do) hoặc (None, None). Đơn đã đi xong (đã gửi/nhận/hoàn/huỷ) thì coi như
    thương vụ cũ — trả None để khách mua đợt mới vẫn lên được đơn mới.
    """
    try:
        d = Q.load_json(_f_so_don(), {}).get(str(conv_id))
        if not d or not d.get("id"):
            return None, None
        o = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{d['id']}")
        o = (o or {}).get("data") or o
        if not isinstance(o, dict) or not o.get("id"):
            return None, None
        if o.get("status") in TRANG_THAI_DA_XONG:
            return None, None
        return o, f"đã nhớ: hội thoại này gắn đơn #{d.get('ma')}"
    except Exception:                                    # noqa: BLE001
        return None, None


# LANDING_TRUNG_2909 — chủ shop 29/09 (ca Mary Wisdom): khách đã có đơn LANDING còn sống / đang đi mà vào chat
# thì máy lên đơn KHÔNG tạo đơn chat cùng khách (cùng SĐT) + cùng mã SP, cũng KHÔNG tự xác nhận đơn chat trùng mã.
# #77425 (chat) được tạo + tự xác nhận khi #77000 (landing, cùng mã 260) đang đi → suýt gửi 2 lần.
TT_LANDING_HET = {3, 16, 4, 15, 5, 6, 7}     # đã nhận / thu tiền / hoàn / huỷ / xoá → không còn tính


def _la_don_chat(o):
    return bool(o.get("conversation_id") or o.get("page_id")
                or (o.get("note") or "").lstrip().startswith("[Tự động] Từ hội thoại"))


def _ma_chat(order, ex):
    """Mã SP ('260') của thương vụ chat: tên SP extract đoán + dòng hàng đang có trên đơn (bỏ hộp)."""
    ma = set()
    m = re.match(r"\s*(\d{2,5})\b", str((ex or {}).get("ten_sp") or ""))
    if m:
        ma.add(m.group(1))
    hop = (MK or {}).get("hop_id")
    for it in (order or {}).get("items") or []:
        if hop and it.get("variation_id") == hop:
            continue
        m = re.match(r"\s*(\d{2,5})\b", str((it.get("variation_info") or {}).get("name") or ""))
        if m:
            ma.add(m.group(1))
    return ma


R_HUY_TRUNG_LP = re.compile(r"ĐÃ HỦY \(TRÙNG\)[^#]*#(\d+)")


def _don_landing_cua_hoi_thoai(conv):
    """Đơn landing (shop hiện tại) mà landing_vao_chat đã ghép với hội thoại `conv` (sổ da_ghi / canh_bao).
    Ca Mary Wisdom: SĐT chat 0568536348 ≠ SĐT landing 0568535348, tên khác — chỉ sổ ghép mới nối được."""
    if not conv:
        return []
    try:
        so = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "chung",
                                         "landing_vao_chat.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    khoa = [k for k, v in (so.get("da_ghi") or {}).items() if (v or {}).get("conv") == str(conv)]
    khoa += [k.split("|", 1)[0] for k in (so.get("canh_bao") or {}) if k.endswith("|" + str(conv))]
    return [k.split(":", 1)[1] for k in dict.fromkeys(khoa) if k.split(":", 1)[0] == str(P.SHOP_ID)]


def don_landing_trung(sdt, ma, bo_id=None, conv=None):
    """Đơn LANDING của cùng khách + chung mã SP, chưa nhận/hoàn/huỷ → (đơn, câu) hoặc (None, None).
    Cùng khách = cùng SĐT (9 số cuối) HOẶC đã được ghép với chính hội thoại này (landing_vao_chat).
    Đơn ghép mà đã HỦY vì trùng → lần sang đơn đang đi được ghi trong ghi chú hủy."""
    if not ma:
        return None, None
    s9 = re.sub(r"\D", "", str(sdt or ""))[-9:]
    try:
        import don_landing as L
        L.A.set_market(MK["key"])      # daemon: don_landing nhập BẢN THỨ HAI của module này — MK có thể kẹt nước khác
        now = int(time.time())
        ung = []
        if len(s9) >= 8:
            ung += [(o, "cùng SĐT") for o in P.fetch_orders({"startDateTime": now - 30 * 86400, "endDateTime": now,
                                                              "page_size": 50, "page_number": 1, "search": s9})
                    if re.sub(r"\D", "", str(o.get("bill_phone_number") or ""))[-9:] == s9]
        for oid in _don_landing_cua_hoi_thoai(conv):
            for _ in range(3):                           # hủy trùng → đơn đang đi (tối đa 3 bước)
                r = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
                o = (r or {}).get("data") if isinstance((r or {}).get("data"), dict) else r
                if not isinstance(o, dict) or not o.get("id"):
                    break
                m = R_HUY_TRUNG_LP.search(o.get("note") or "") if o.get("status") in (6, 7) else None
                if not m:
                    ung.append((o, "hội thoại này đã ghép với đơn landing"))
                    break
                oid = m.group(1)
        for o, vi in ung:
            if (o.get("id") == bo_id or _la_don_chat(o) or o.get("status") in TT_LANDING_HET
                    or str(o.get("order_sources")) not in ("None", "-7", "")):
                continue
            chung = set(ma) & L.ma_san_pham(o)
            if chung:
                return o, (f"khách đã có đơn LANDING #{o.get('display_id') or o.get('id')} "
                           f"({P.STATUS_BY_CODE.get(o.get('status'), o.get('status'))}, "
                           f"{(o.get('inserted_at') or '')[:10]}, {vi}) cùng mã SP {', '.join(sorted(chung))}")
    except Exception as e:                               # noqa: BLE001
        log(f"  ⚠️  không tra được đơn landing trùng: {e}")
    return None, None


def find_existing(conv_id, sdt, days=14, gio_tay=24, page_id=None):
    """Tìm đơn đã có của CHÍNH thương vụ này.

    LUẬT CHỦ SHOP 2026-09-08: *"cùng 1 page, không tạo lại khi đã tạo trước đó, chỉ bổ sung
    thông tin. Đặc biệt nếu SALE có tạo trước thì không được tạo đơn nào nữa, chỉ sửa thêm
    thông tin ở đơn của sale."*

    Thứ tự xét:
    - Cùng hội thoại                      -> chắc chắn trùng, sửa đơn cũ.
    - Cùng SĐT **trên cùng page**, đơn chưa đi -> TRÙNG, dù đơn tạo lâu rồi, dù đơn không gắn
      hội thoại nào. Đây là đơn sale tạo tay cho chính khách này.
      ⚠️ Trước 2026-09-08 chỗ này chỉ tính khi đơn tạo trong `gio_tay`=24 giờ. Sale tạo hôm kia
      là tool tạo thêm một đơn nữa — đúng cái chủ shop cấm. Nay bỏ hẳn ràng buộc thời gian
      khi CÙNG PAGE; giữ cửa 24 giờ cho trường hợp không biết page.
    - Cùng SĐT nhưng khác page (khách mua sản phẩm khác) -> KHÔNG chặn, vẫn lên đơn mới,
      chỉ ghi chú nhắc kiểm tra.
    Trả về (đơn_trùng, lý_do, danh_sách_đơn_khác_cùng_sđt).
    """
    now = int(time.time())
    common = {"startDateTime": now - days * 86400, "endDateTime": now, "page_size": 100}
    trung = None
    khac = []
    for pg in (1, 2, 3):
        data = P.fetch_orders({**common, "page_number": pg})
        for o in data:
            if str(o.get("conversation_id") or "") == str(conv_id):
                if o.get("status") in TRANG_THAI_DA_XONG:
                    khac.append(o)          # đơn cũ đã xong -> khách mua đợt mới
                    continue
                return o, "cùng hội thoại", khac
        if len(data) < 100:
            break
    if sdt:
        for o in P.fetch_orders({**common, "page_number": 1, "search": sdt}):
            conv_cua_don = str(o.get("conversation_id") or "")
            if conv_cua_don and conv_cua_don != str(conv_id):
                khac.append(o)                       # thương vụ khác của cùng khách
                continue
            tuoi = now - _tuoi_don(o)
            if o.get("status") in TRANG_THAI_DA_XONG:
                khac.append(o)               # đơn cũ đã gửi/hủy -> không phải deal đang chốt
                continue
            cung_page = page_id and str(o.get("page_id") or "") == str(page_id)
            if trung is None and cung_page:
                trung = (o, "cùng SĐT trên CÙNG PAGE — đơn sale đã tạo, chỉ bổ sung")
            elif trung is None and not conv_cua_don and tuoi <= gio_tay * 3600:
                trung = (o, "cùng SĐT, sale vừa tạo tay")
            else:
                khac.append(o)
    da_co, gon = set(), []          # bỏ đơn bị lặp (vừa khớp hội thoại vừa khớp SĐT)
    for o in khac:
        if o.get("id") not in da_co:
            da_co.add(o.get("id"))
            gon.append(o)
    if trung:
        return trung[0], trung[1], gon
    return None, None, gon


def _tuoi_don(o):
    """Thời điểm tạo đơn (epoch giây); trả 0 nếu không đọc được."""
    import datetime
    s = (o.get("inserted_at") or "").split(".")[0]
    try:
        return int(datetime.datetime.fromisoformat(s).timestamp())
    except (ValueError, TypeError):
        return 0


def _giu_khoi_dia_chi(order, body):
    """Gửi kèm địa chỉ + phí chuyển đang có mỗi khi body đụng tới SĐT hoặc ô địa chỉ.

    POS phản chiếu bill_phone_number xuống shipping_address: PUT chỉ mỗi SĐT là nó thay
    nguyên khối địa chỉ bằng object rỗng (mất số nhà + tỉnh + quận) và xóa luôn phí
    chuyển về 0 — đo được trên đơn thật qatar #6095, uae #46692, saudi #67605.
    """
    if "bill_phone_number" not in body and "shipping_address" not in body:
        return
    if "shipping_address" not in body:
        cu = order.get("shipping_address") or {}
        giu = {k: cu.get(k) for k in ("full_name", "phone_number", "address",
                                      "province_id", "district_id", "commune_id") if cu.get(k)}
        if giu:
            if giu.get("province_id"):
                giu["country_code"] = cu.get("country_code") or P.COUNTRY_CODE
            body["shipping_address"] = giu
    if "shipping_fee" not in body and (order.get("shipping_fee") or 0):
        body["shipping_fee"] = order["shipping_fee"]


def la_don_nhap_cua_tool(o):
    """Đơn do tool tự tạo từ hội thoại (note mở đầu '[Tự động] Từ hội thoại')."""
    return (o.get("note") or "").lstrip().startswith("[Tự động] Từ hội thoại")


# Note đơn có SĐT / địa chỉ máy ĐỌC TỪ ẢNH (chữ extract ghi: "SĐT … máy ĐỌC TỪ ẢNH", "số hiện có là máy đọc từ ảnh",
# "địa chỉ … máy đọc từ ảnh"). Tên đọc từ ảnh KHÔNG tính — không chặn xác nhận.
R_NOTE_TU_ANH = re.compile(r"(?:sđt|số|địa chỉ)[^\n;]{0,40}máy đọc từ ảnh", re.I)


def bo_sung_don_cu(order, ly_do, ex, record, dry):
    """Sale đã tạo đơn: chỉ điền trường trống + nối note. Không ghi đè."""
    oid = order.get("id")
    body, filled = {}, []
    if not order.get("bill_phone_number") and ex["sdt"]:
        body["bill_phone_number"] = ex["sdt"]; filled.append("SĐT")
    addr = order.get("shipping_address") or {}
    if not (addr.get("address") or addr.get("full_address")) and ex["diachi"]:
        body["shipping_address"] = {"full_name": order.get("bill_full_name") or ex["ten"],
                                    "phone_number": order.get("bill_phone_number") or ex["sdt"] or "",
                                    "address": ex["diachi"]}
        em = P.detect_emirate(ex["diachi"])
        if em:
            body["shipping_address"]["province_id"] = em
            body["shipping_address"]["country_code"] = P.COUNTRY_CODE
        filled.append("địa chỉ")
        _dien_dia_gioi(body["shipping_address"], ex["diachi"], filled)      # DIA_GIOI_2509
    # ĐƠN DO CHÍNH TOOL TẠO, còn Mới và còn THIẾU → được phép ĐIỀN TIẾP (chủ shop chốt
    # 2026-09-10: "khách cung cấp thông tin → update tiếp đơn đó chứ k tạo lại"; đủ tên/SĐT/
    # địa chỉ/số lượng/tiền thì mới chuyển Đã xác nhận). Đơn của SALE thì tuyệt đối giữ như cũ.
    # Ca thật: #49457 (Rolando, Flat Jewelry) tạo với 0 AED + "Sharjah uae" vì bộ nhận giá/địa
    # chỉ hỏng; sửa xong bộ nhận mà đơn vẫn nằm đó 0 AED thì sửa để làm gì.
    cua_tool = la_don_nhap_cua_tool(order)
    if cua_tool and order.get("status") == 0:
        if not (order.get("money_to_collect") or order.get("shipping_fee")) and ex["gia"]:
            body["shipping_fee"] = ex["gia"]; filled.append(f"tiền thu {P.fmt_money(ex['gia'])}")
        elif (record.get("gia_mac_ca") and ex["gia"] and order.get("shipping_fee") and order["shipping_fee"] != ex["gia"]
              and any(c.startswith("giá chốt") and "trả giá" in c for c in ex.get("canh_bao") or [])):
            # nháp của tool tạo TRƯỚC lúc khách mặc cả xong → sửa về giá page đã nhận (chủ shop 19/09)
            filled.append(f"tiền thu {P.fmt_money(order['shipping_fee'])} → {P.fmt_money(ex['gia'])} "
                          f"(khách trả giá, page đã nhận)")
            body["shipping_fee"] = ex["gia"]
        co_sp_cu = any((it.get("quantity") or 0) > 0 and it.get("variation_id") != MK.get("hop_id")
                       for it in (order.get("items") or []))
        if ex["variation_id"] and ex["qty"] and (not co_sp_cu or not order.get("money_to_collect")):
            body["items"] = items_va_ship(ex); filled.append(f"SP x{ex['qty']}")
        else:
            _bo = hang_pos_gan_thua(order.get("items"), ex)       # HOP_POS_2509: POS tự gắn hộp / trang sức vào page trà…
            if _bo:
                body["items"] = _giu_dong(order.get("items"), _bo)
                filled.append(f"bỏ {', '.join(_ten_dong(_bo))} POS tự gắn (page bán {ex['ten_sp']}, không kèm hộp/trang sức)")
        dc_cu = (addr.get("address") or addr.get("full_address") or "")
        so_sai = len(re.sub(r"\d+", "", dc_cu).split()) < 3 or _dc_la_cau_hoi(dc_cu)
        rac_cu = bool(dc_cu) and bool(R_CAU_XIN_TT.search(dc_cu))   # DIA_CHI_TIN_XIN_2509: ô địa chỉ đang là câu xin / cửa hàng
        if ex["diachi"] and (so_sai or rac_cu or not dc_cu) and (rac_cu or len(ex["diachi"].split()) > len(dc_cu.split())):
            body["shipping_address"] = {"full_name": order.get("bill_full_name") or ex["ten"],
                                        "phone_number": order.get("bill_phone_number") or ex["sdt"] or "",
                                        "address": ex["diachi"]}
            em = P.detect_emirate(ex["diachi"])
            if em:
                body["shipping_address"]["province_id"] = em
                body["shipping_address"]["country_code"] = P.COUNTRY_CODE
            elif addr.get("province_id"):
                # DIA_CHI_TIN_XIN_2509: địa chỉ mới không ghi tỉnh (vd "định vị: <link Google Maps>") → giữ tỉnh đang có
                body["shipping_address"]["province_id"] = addr["province_id"]
                body["shipping_address"]["country_code"] = addr.get("country_code") or P.COUNTRY_CODE
            if "địa chỉ" not in filled:
                filled.append("địa chỉ đầy đủ hơn")
            _dien_dia_gioi(body["shipping_address"], ex["diachi"], filled)  # DIA_GIOI_2509
        # Nháp của tool đã có ô địa chỉ mà chưa có quận → điền nốt từ chính ô đó (DIA_GIOI_2509)
        if "shipping_address" not in body and not addr.get("district_id") and (addr.get("address") or addr.get("full_address")):
            _sa = {k: addr.get(k) for k in ("full_name", "phone_number", "address", "province_id", "commune_id") if addr.get(k)}
            if _dien_dia_gioi(_sa, addr.get("address") or addr.get("full_address"), filled):
                body["shipping_address"] = _sa
        # Khách đưa tên người nhận sau khi nháp đã tạo bằng tên FB → đổi sang "<tên khách> - <tên FB>".
        # Chỉ khi tên mới vẫn chứa đủ tên đang trên đơn (tức đơn đang mang tên FB, chưa ai sửa tay).
        if (ex["ten"] and _chu_ten(ex["ten"]) != _chu_ten(order.get("bill_full_name"))
                and _chu_ten(order.get("bill_full_name")) <= _chu_ten(ex["ten"])):
            body["bill_full_name"] = ex["ten"]
            if "shipping_address" not in body:
                body["shipping_address"] = {k: addr.get(k) for k in ("full_name", "phone_number", "address",
                                            "province_id", "district_id", "commune_id") if addr.get(k)}
                if body["shipping_address"].get("province_id"):
                    body["shipping_address"]["country_code"] = addr.get("country_code") or P.COUNTRY_CODE
            body["shipping_address"]["full_name"] = ex["ten"]
            filled.append(f"tên người nhận {ex['ten']}")
        # Nơi gọi KHÔNG thấy ảnh (daemon: record không có "sdt_anh") mà đơn mở bằng SĐT / địa chỉ máy ĐỌC TỪ ẢNH → không
        # tự xác nhận; AI Sale (thấy ảnh, extract phân biệt được) hoặc sale xác nhận (24/09, ca Audrey #77053).
        _anh_mu = "sdt_anh" not in record and bool(R_NOTE_TU_ANH.search(order.get("note") or ""))
        if not ex["thieu"] and not record.get("khong_tu_xac_nhan") and not _anh_mu:
            _lt, _ly = (don_landing_trung(order.get("bill_phone_number") or ex.get("sdt"), _ma_chat(order, ex),
                                          order.get("id"), record.get("conversation_id"))
                        if _la_don_chat(order) else (None, None))   # LANDING_TRUNG_2909
            if _lt:
                filled.append(f"⚠ KHÔNG tự xác nhận — {_ly}; sale kiểm có phải đơn trùng")
            else:
                body["status"] = 1; filled.append("→ Đã xác nhận (đủ thông tin)")
    # Khách hẹn giao ngày lương (AI Sale, chủ shop 14/09) — nối vào note ĐÚNG MỘT lần cho mỗi
    # nội dung (khách nói ngày ở lượt sau thì dòng mới có ngày, nối thêm một lần nữa).
    hen = record.get("hen_giao")
    if hen and hen not in (order.get("note") or ""):
        filled.append(f"hẹn giao: {hen}")
    _giu_khoi_dia_chi(order, body)
    mau_thuan = ""
    if (ex["gia"] and order.get("money_to_collect") and order["money_to_collect"] != ex["gia"]
            and "shipping_fee" not in body):
        mau_thuan = (f" ⚠ LỆCH GIÁ: chat chốt {P.fmt_money(ex['gia'])}, "
                     f"đơn đang {P.fmt_money(order['money_to_collect'])} — kiểm tra lại!")
    if record.get("im_neu_khong_doi") and not filled:
        # AI Sale gọi vào MỖI lượt khách nhắn (nhịp 15s): không có gì mới thì đừng nối thêm một
        # dòng "không có gì" vào note đơn mỗi lượt. Lệch giá thì chỉ nói ra log, không sửa đơn.
        log(f"  · đơn #{order.get('display_id') or oid} ({ly_do}): không có gì mới để bổ sung{mau_thuan}")
        return f"đơn {oid} đã có, không có gì mới"
    if cua_tool:
        note_them = (f"[Tự động] Khách bổ sung thông tin ({record['page_name']}). "
                     f"Điền tiếp: {', '.join(filled) or 'không có gì'}.{mau_thuan}")
    else:
        note_them = (f"[Tự động] Hội thoại gắn tag Lên đơn ({record['page_name']}) — sale đã tạo đơn ({ly_do}), "
                     f"không tạo trùng. Bổ sung: {', '.join(filled) or 'không có gì'}.{mau_thuan}")
    body["note"] = ((order.get("note") or "").strip() + "\n" + note_them).strip()
    if dry:
        log(f"  [THỬ] Sẽ bổ sung đơn #{order.get('display_id') or oid}: {', '.join(filled) or 'chỉ note'}{mau_thuan}")
        return f"(thử) bổ sung đơn {oid}"
    P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body=body)
    log(f"  ✔ Bổ sung đơn có sẵn #{order.get('display_id') or oid} ({ly_do}): {', '.join(filled) or 'chỉ note'}{mau_thuan}")
    return f"sale đã tạo đơn {oid}, đã bổ sung: {', '.join(filled) or 'note'}"


def tao_don_moi(ex, record, dry):
    du = not ex["thieu"]
    # AI Sale tạo nháp sớm ở thị trường THU TIỀN SAU (Mỹ/Úc): đủ thông tin vẫn ĐỂ "Mới" — phải
    # qua chốt 1 + chốt 2 của mục 9b (xác minh nhà, phương thức thanh toán) rồi AI mới chọn
    # "len_don" để xác nhận. Note viết "còn thiếu" chữ thường để `hoan_thien_don_thieu` (chỉ bắt
    # chữ "THIẾU") không điền rồi tự xác nhận hộ; phần điền tiếp do AI Sale làm ở lượt sau.
    giu_moi = bool(record.get("khong_tu_xac_nhan"))
    co_sp = bool(ex["variation_id"] and ex["qty"])
    dvvc = chon_dvvc(ex.get("ten_sp"), record.get("page_id"))   # ĐVVC theo page (dvvc_theo_page) trước
    note = f"[Tự động] Từ hội thoại [{record['page_name']}]"
    if giu_moi:
        du = False
        note += (" — nháp AI Sale (thị trường thu tiền sau): "
                 + (f"còn thiếu: {'; '.join(ex['thieu'])}; " if ex["thieu"] else "đủ thông tin nhưng ")
                 + "chờ AI xác minh nhà + phương thức thanh toán rồi mới xác nhận (mục 9b).")
    elif du:
        note += " — ĐỦ thông tin, đã tự xác nhận. Nhân viên check rồi chuyển Chờ in."
    else:
        note += f" — THIẾU: {'; '.join(ex['thieu'])}. Bổ sung xong mới xác nhận."
    if ex["canh_bao"]:
        note += f" (Lưu ý: {'; '.join(ex['canh_bao'])})"
    if ex["ten_sp"] and not co_sp:
        note += f" — SP dự đoán: {ex['ten_sp']}"
        if ex["gia"]:
            note += f", tiền thu {P.fmt_money(ex['gia'])}"
    if record.get("ghi_chu_them"):
        # AI Sale thấy khách đã gõ số/địa chỉ mà bộ trích không đọc được (gõ sai) → vẫn tạo đơn,
        # chép nguyên chữ khách gõ vào đây cho sale sửa (chủ shop 2026-09-11: tạo trước, sửa sau).
        note += f" — {record['ghi_chu_them']}"
    if record.get("hen_giao"):
        # Khách đợi lương (AI Sale, chủ shop 14/09): ngày hẹn giao phải nằm ngay trên đơn.
        note += f" — {record['hen_giao']}"

    if dry:
        log(f"  [THỬ] Sẽ tạo đơn {'ĐỦ (tự xác nhận)' if du else ('nháp Mỹ/Úc (để Mới chờ chốt 9b)' if giu_moi else 'THIẾU (để Mới)')}: "
            f"{ex['ten']} | {ex['sdt']} | {ex['diachi']} | SP {ex['ten_sp']} x{ex['qty']}"
            f"{' + hộp' if ex.get('them_hop') else ''} | thu {P.fmt_money(ex['gia'])} "
            f"| ĐVVC {(dvvc or {}).get('ten', '-')} | thiếu: {ex['thieu'] or 'không'}")
        return "(thử) sẽ tạo đơn"

    # Quy ước shop: tiền thu -> shipping_fee, giá sản phẩm để 0
    body = P.build_order_body(ex["ten"], ex["sdt"] or "", ex["diachi"] or "", [],
                              None, ex["gia"], note, False)
    _dien_dia_gioi(body.get("shipping_address"), ex["diachi"])      # DIA_GIOI_2509: đủ tỉnh → quận → xã
    if co_sp:
        body["items"] = items_va_ship(ex)
    else:
        body.pop("items", None)
    if dvvc:
        body["partner"] = {"partner_id": dvvc["id"], "custom_partner_id": dvvc["id"],
                           "partner_name": dvvc["ten"]}
    body["conversation_id"] = record["conversation_id"]
    body["page_id"] = str(record["page_id"])
    res = _post_don(body, record)                     # TRAM_DON_2709 — page trạm: POS không nhận page → tạo không page
    order = res.get("data") if isinstance(res.get("data"), dict) else res
    oid = order.get("id")
    if not oid:
        raise RuntimeError(f"Không đọc được mã đơn: {str(res)[:200]}")
    if du:
        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body={"status": 1})
    if not co_sp:
        # HOP_POS_2509: nháp KHÔNG gửi dòng hàng → POS tự gắn theo hội thoại; page không bán trang sức mà POS gắn hộp /
        # trang sức (ca #77377: trà + "BOX") → bỏ ngay. Hỏng thì chỉ báo log — đơn đã tạo, nho_don phía dưới PHẢI chạy.
        try:
            _its = order.get("items")
            if _its is None:
                _r = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{oid}")
                _its = ((_r.get("data") if isinstance(_r.get("data"), dict) else _r) or {}).get("items")
            _bo = hang_pos_gan_thua(_its, ex)
            if _bo:
                P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body={
                    "items": _giu_dong(_its, _bo),
                    "note": (order.get("note") or note).strip() + f"\n[Tự động] Bỏ {', '.join(_ten_dong(_bo))} POS tự gắn — "
                                                                  f"page bán {ex['ten_sp']}, không kèm hộp/trang sức."})
                log(f"  ✂ #{order.get('display_id') or oid}: bỏ {', '.join(_ten_dong(_bo))} POS tự gắn (page bán {ex['ten_sp']})")
        except Exception as e:
            log(f"  ⚠ #{order.get('display_id') or oid}: chưa bỏ được hàng POS tự gắn: {e}")
    log(f"  ✔ Tạo đơn #{order.get('display_id') or oid} {'(ĐỦ — Đã xác nhận)' if du else ('(nháp Mỹ/Úc — Mới)' if giu_moi else '(THIẾU — Mới)')}: "
        f"{ex['ten']} | {ex['sdt'] or '-'} | thu {P.fmt_money(ex['gia'] or 0)} | "
        f"ĐVVC {(dvvc or {}).get('ten', '-')}{' | +hộp' if ex.get('them_hop') and co_sp else ''}"
        f"{' | thiếu: ' + '; '.join(ex['thieu']) if ex['thieu'] else ''}")
    # Nhớ ngay: hội thoại này từ giờ gắn với đơn vừa tạo. Lần sau khách nhắn thêm là
    # đi thẳng vào đơn này để bổ sung, không bao giờ tạo đơn thứ hai (luật chủ shop 08/09).
    nho_don(record.get("conversation_id"), order)
    return f"đã tạo đơn {oid} " + ("đủ, tự xác nhận" if du else f"thiếu: {'; '.join(ex['thieu'])}")


def danh_dau_chua_doc(page_id, conv_id, dry=False):
    """Đưa hội thoại về CHƯA ĐỌC sau khi tool đụng vào đơn — chủ shop chốt 2026-09-10:
    *"rep cái nào, lên đơn cái nào đều phải đánh dấu chưa đọc lên cho tôi check."*

    AI chat đã làm việc này từ đầu (mục 9b, luật xuyên suốt), nhưng luồng LÊN ĐƠN thì chưa —
    nó chỉ ghi vào sổ `da_xu_ly.json` trên máy, sale mở Pancake không thấy dấu hiệu gì.
    Hậu quả: tool tạo đơn cho một hội thoại mà không ai biết để soát.

    Hỏng thì KÊU TO chứ không nuốt: không đánh dấu được nghĩa là đơn đó trôi, không ai kiểm.
    """
    if dry:
        log(f"     [THỬ] sẽ đánh dấu CHƯA ĐỌC hội thoại {conv_id}")
        return
    try:
        tok = (Q.load_json(Q.TOKENS_FILE, {}).get(str(page_id)) or {}).get("token")
        if not tok:
            # 7+ page (UAE/Saudi) CHƯA CÓ token page vì thiếu quyền Admin — AI vẫn chạy trên
            # chúng bằng TÀI KHOẢN Pancake. Bản cũ bó tay ngay đây, nên mọi đơn tạo từ các page
            # đó không có nổi một dấu chưa đọc: ca Merl Esteban · HairGlow Beauty (17/09) tạo
            # đơn #74762 xong in "không có token page — KHÔNG đánh dấu chưa đọc được", hội thoại
            # nằm im ở trạng thái đã đọc, khách "I order im here in jeddah" không ai rep.
            try:
                import ai_sale as _A
                r_, e_ = _A._post(
                    f"{_A.WEB_API}/pages/{page_id}/conversations/{conv_id}/mark_unread",
                    {"access_token": _A._tok_user()})
            except Exception as ex_:                     # noqa: BLE001
                r_, e_ = None, str(ex_)
            if r_ and not e_:
                return log("     ✔ đã đánh dấu CHƯA ĐỌC bằng TÀI KHOẢN Pancake "
                           f"(page {page_id} không có token page)")
            return log(f"     ⚠️  page {page_id} không có token page, đánh dấu bằng tài khoản "
                       f"cũng hỏng ({e_}) — KHÔNG đánh dấu chưa đọc được")
        # KHÔNG tin mã trả về: đo 2026-09-10, API `/unread` báo success nhưng Pancake
        # lật lại "đã đọc" vài giây sau (xem ai_sale.danh_dau_chua_doc). Đánh xong phải
        # đọc lại cờ `seen`, còn "đã đọc" thì đánh lại.
        loi = None
        for _ in range(3):
            res, err = Q.http_json(
                "POST", f"{Q.BASE_PAGE_V1}/pages/{page_id}/conversations/{conv_id}/unread",
                {"page_access_token": tok})
            if err or res is None:
                loi = err or "API không trả gì"
                time.sleep(4)
                continue
            time.sleep(4)
            now = int(time.time())
            r2, e2 = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{page_id}/conversations",
                                 {"page_access_token": tok, "since": now - 3 * 86400,
                                  "until": now, "order_by": "updated_at"})
            c = [k for k in ((r2 or {}).get("conversations") or [])
                 if str(k.get("id")) == str(conv_id)]
            if c and not c[0].get("seen"):
                return                      # tận mắt thấy: đang chưa đọc
            loi = e2 or ("Pancake lật lại thành ĐÃ ĐỌC" if c else "không thấy hội thoại")
        log(f"     🚨 ĐÁNH DẤU CHƯA ĐỌC HỎNG ({loi}) — đơn này sẽ trôi, phải soát tay!")
    except Exception as e:                               # noqa: BLE001
        log(f"     🚨 ĐÁNH DẤU CHƯA ĐỌC HỎNG ({e}) — đơn này sẽ trôi, phải soát tay!")


# ═════════════════════════════════════════════════════════════════════════════
# KHOÁ THEO HỘI THOẠI — hai tiến trình không được cùng lên đơn cho một hội thoại
# ═════════════════════════════════════════════════════════════════════════════
# CA THẬT (Anabelle Magbanua, Kreain Nature PH in Uae, 14/09/2026): khách gửi SĐT + địa chỉ
# lúc 04:49:15. Daemon (vòng "lên đơn không tag", 30s) và AI Sale (bước "lên đơn sớm", 8s)
# CÙNG thấy tin đó, CÙNG hỏi POS "đã có đơn chưa" (mất 10-15s) khi chưa bên nào tạo → cả hai
# đều tin là chưa có → #49886 lúc 04:50:18 rồi #49887 lúc 04:50:27, cách nhau 9 giây.
# Sổ don_theo_hoi_thoai và find_existing đều đúng — chỉ là hai bên kiểm CÙNG LÚC.
# Nên: mỗi hội thoại một khoá file (flock). Bên đến sau phải ĐỢI bên trước làm xong (kiểm +
# tạo + ghi sổ), rồi mới vào — lúc đó sổ đã có đơn, nó chỉ bổ sung vào đúng đơn đó.
# Khoá nằm trong state/<tt>/khoa/ nên daemon và AI Sale (cùng máy, cùng thị trường) dùng chung.

class _KhoaHoiThoai:
    def __init__(self, conv_id):
        self.conv_id = str(conv_id or "")
        self.fh = None

    def __enter__(self):
        if not self.conv_id:
            return self
        try:
            import fcntl
            d = os.path.join(Q.STATE_DIR, "khoa")
            os.makedirs(d, exist_ok=True)
            ten = re.sub(r"[^0-9A-Za-z_.-]", "_", self.conv_id)[:150]
            self.fh = open(os.path.join(d, ten + ".lock"), "a+")
            t0 = time.time()
            fcntl.flock(self.fh, fcntl.LOCK_EX)
            if time.time() - t0 > 1:
                log(f"  🔒 hội thoại {self.conv_id} đang được tiến trình khác lên đơn — "
                    f"đã đợi {time.time()-t0:.0f}s rồi mới vào (chỉ bổ sung, không tạo thêm)")
        except Exception as e:                           # noqa: BLE001 — không khoá được thì vẫn chạy
            log(f"  ⚠️  không khoá được hội thoại {self.conv_id}: {e}")
            self.fh = None
        return self

    def __exit__(self, *a):
        if self.fh:
            try:
                import fcntl
                fcntl.flock(self.fh, fcntl.LOCK_UN)
                self.fh.close()
            except Exception:                            # noqa: BLE001
                pass
        return False


# ═════════════════════════════════════════════════════════════════════════════
# SALE ĐÃ HỦY ĐƠN → KHÔNG TỰ TẠO LẠI (chủ shop 17/09/2026)
# ═════════════════════════════════════════════════════════════════════════════
# *"sao chúng tôi đã huỷ đơn rồi mà bạn vẫn tạo mới vậy, đã vậy khách k có thông tin gì mà vẫn
# tạo mới"* — ca محمد ناصر محمد (ChunHo Golden Jewerly, Saudi): sale hủy #74895 lúc 15:05 giờ VN
# ("k có tm"), daemon tạo #74899 lúc 15:10; sale hủy #74899 lúc 17:14, AI Sale tạo #74941 lúc
# 17:17. Cả hai lần chỉ dựa vào SĐT/địa chỉ khách gõ TỪ TRƯỚC lúc hủy.
# Gốc: TRANG_THAI_DA_XONG gộp "hủy" chung với "đã giao" → coi là thương vụ cũ đã xong → đơn mới.
# Đo 7 ngày (uae/saudi/kuwait): tool tạo lại 11 lần sau khi đơn bị hủy, 7 lần thành đơn rác.
# Luật: sale hủy là đã xét hết những gì khách nói TỚI lúc đó. Chỉ tin khách gửi SAU lúc hủy mà
# có SĐT/địa chỉ mới được mở đơn mới; AI Sale chốt đơn (len_don) thì chỉ cần khách có nhắn sau
# lúc hủy. Cái giá (cùng đợt đo): 3 đơn thật khách chỉ nhắn "Only 99 pls" / "why until now not
# come" / "nhắn khi có số" (#49489, #49867 uae, #14490 kuwait) — nay để sale tự lên.
# Đơn giao xong (2/3/16/4/15/5) vẫn giữ luật cũ: khách mua đợt mới thì lên đơn mới.

TT_HUY = {6, 7}


def _epoch_utc(s):
    """Giờ POS / pages.fm ('2026-09-17T10:14:07', không ghi múi = UTC) → epoch; đọc hỏng thì 0."""
    import datetime
    if isinstance(s, (int, float)):
        return int(s / 1000 if s > 1e11 else s)
    s = re.sub(r"\.\d+", "", str(s or "").strip().replace("Z", "+00:00"))
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        return 0
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return int(d.timestamp())


def _luc_huy(o):
    """(epoch, người hủy) của lần chuyển sang hủy/xóa gần nhất."""
    moc, ai = 0, None
    for h in o.get("status_history") or []:
        t = _epoch_utc(h.get("updated_at"))
        if h.get("status") in TT_HUY and t >= moc:
            moc, ai = t, h.get("name")
    return (moc or _epoch_utc(o.get("updated_at"))), (ai or "tool/hệ thống")


def don_huy_cua_thuong_vu(record, khac):
    """Đơn MỚI NHẤT của thương vụ này (cùng hội thoại, hoặc cùng page) đang bị hủy/xóa?

    Trả (epoch lúc hủy, người hủy, đơn) hoặc None. `khac` là danh sách find_existing trả về.
    """
    conv = str(record.get("conversation_id") or "")
    pid = str(record.get("page_id") or "")
    ung = {o.get("id"): o for o in khac or [] if o.get("id")}
    # Đơn sổ đã nhớ cho hội thoại — don_da_nho bỏ qua vì đơn đã xong, có khi cũ hơn cửa sổ 14 ngày.
    try:
        d = Q.load_json(_f_so_don(), {}).get(conv) or {}
        if d.get("id") and d["id"] not in ung:
            o = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{d['id']}")
            o = (o or {}).get("data") or o
            if isinstance(o, dict) and o.get("id"):
                ung[o["id"]] = o
    except Exception:                                    # noqa: BLE001
        pass
    # POS tìm theo mã hội thoại ra RỖNG (đo 17/09) nhưng tìm theo tên khách thì ra → tìm theo tên
    # rồi chỉ giữ đơn ĐÚNG hội thoại này. Bắt được đơn sale tạo tay không ghi SĐT.
    ten = str(record.get("khach") or ((record.get("ho_so_khach") or [{}])[0] or {}).get("ten") or "").strip()
    if conv and len(ten) >= 4:
        try:
            for o in P.fetch_orders({"page_size": 100, "page_number": 1, "search": ten}):
                if str(o.get("conversation_id") or "") == conv:
                    ung.setdefault(o.get("id"), o)
        except Exception:                                # noqa: BLE001
            pass
    cung = [o for o in ung.values()
            if (conv and str(o.get("conversation_id") or "") == conv)
            or (pid and (str(o.get("page_id") or "") or _page_tu_ma_khach(o)) == pid)]
    if not cung:
        return None
    moi_nhat = max(cung, key=lambda o: (_epoch_utc(o.get("inserted_at")), o.get("id") or 0))
    if moi_nhat.get("status") not in TT_HUY:
        return None
    moc, ai = _luc_huy(moi_nhat)
    return moc, ai, moi_nhat


def tin_khach_sau(record, moc):
    return [m for m in record.get("tin_nhan") or []
            if m.get("ai") == "khach" and _epoch_utc(m.get("luc")) > moc]


def sdt_dia_chi_trong(tins):
    """Mấy tin khách này có SĐT hoặc địa chỉ đủ tin không? Trả mô tả ngắn, không có thì ''."""
    import ho_so as HS
    for m in tins:
        t = str(m.get("noi_dung") or "")
        ts = _van_sdt(t)                                  # "055,9138041" — số tách bằng dấu phẩy
        if (PHONE_RE and PHONE_RE.search(ts)) or any(
                phan_loai_sdt(u)[0] != "hong" for u in SDT_UNG_VIEN_RE.findall(ts)):
            return f"SĐT ({t[:40]!r})"
        if HS.dia_chi_du_tin(t, MK["key"])[0] and not HS.khong_phai_dia_chi(t, MK["key"]):
            return f"địa chỉ ({t[:40]!r})"
    return ""


def xu_ly_mot(record, products, dry):
    """Trả "chan_sau_huy" (sale đã hủy đơn của thương vụ) / "chua_du_tin" (chưa SĐT, địa chỉ
    chưa đủ 3 cấp) khi KHÔNG tạo đơn; còn lại None."""
    with _KhoaHoiThoai(record.get("conversation_id")):
        return _xu_ly_mot_da_khoa(record, products, dry)


def _xu_ly_mot_da_khoa(record, products, dry):
    ex = extract(record, products)
    # ĐƯỜNG TẮT: hội thoại này đã gắn đơn nào chưa? Nhớ rồi thì đi thẳng vào đơn đó,
    # khỏi lật 300 đơn, và chắc chắn không đẻ đơn thứ hai.
    # (đọc sổ SAU KHI đã cầm khoá — bên kia vừa tạo xong thì sổ đã có đơn của nó)
    order, ly_do = don_da_nho(record["conversation_id"])
    khac = []
    if not order:
        order, ly_do, khac = find_existing(record["conversation_id"], ex["sdt"],
                                           page_id=record.get("page_id"))
    if order:
        ghi_chu = bo_sung_don_cu(order, ly_do, ex, record, dry)
        if not dry:
            nho_don(record["conversation_id"], order)    # nhớ lại cho chắc
    else:
        # Chốt chung cho MỌI đường tạo đơn: chưa có SĐT thì địa chỉ phải đủ 3 cấp (chủ shop 17/09).
        # AI Sale đưa SĐT khách gõ sai khuôn / địa chỉ hồ sơ đã kiểm qua record (len_don_som).
        if not (ex.get("sdt") or record.get("sdt_khach_go") or record.get("dia_chi_3_cap")
                or (ex.get("diachi") and dia_chi_3_cap(ex["diachi"])[0])):
            log(f"  {'[THỬ] ' if dry else ''}⛔ {record.get('page_name') or ''} · "
                f"{record.get('khach') or ex.get('ten') or '?'}: chưa có SĐT, địa chỉ chưa đủ 3 cấp "
                f"({dia_chi_3_cap(ex.get('diachi'))[1]}: {str(ex.get('diachi') or '')[:60]}) → KHÔNG tạo đơn")
            return "chua_du_tin"
        # Sale đã hủy đơn của thương vụ này → chỉ tạo lại khi khách cho SĐT/địa chỉ SAU lúc hủy.
        huy = don_huy_cua_thuong_vu(record, khac)
        if huy:
            moc, ai_huy, o_huy = huy
            sau = tin_khach_sau(record, moc)
            moi = sdt_dia_chi_trong(sau)
            if not moi and record.get("chot_that") and sau:
                moi = f"tin chốt lại với AI ({str(sau[-1].get('noi_dung') or '')[:40]!r})"
            ma_huy = f"#{o_huy.get('display_id') or o_huy.get('id')}"
            luc = time.strftime("%d/%m %H:%M", time.localtime(moc))
            if not moi:
                ly = (f"đơn {ma_huy} đã bị {ai_huy} hủy lúc {luc} — khách chưa gửi SĐT/địa chỉ mới "
                      f"sau lúc hủy → KHÔNG tạo lại, để sale xử")
                log(f"  {'[THỬ] ' if dry else ''}⛔ {record.get('page_name') or ''} · "
                    f"{record.get('khach') or ex.get('ten') or '?'}: {ly}")
                if not dry:
                    Q.cmd_mark(record["page_id"], record["conversation_id"], ly)
                return "chan_sau_huy"
            ex["canh_bao"].append(f"đơn {ma_huy} đã bị {ai_huy} hủy lúc {luc}, sau đó khách gửi "
                                  f"{moi} nên lên đơn mới")
        _lt, _ly = don_landing_trung(ex.get("sdt") or record.get("sdt_khach_go"), _ma_chat(None, ex),
                                     conv=record.get("conversation_id"))  # LANDING_TRUNG_2909
        if _lt:
            ly = f"{_ly} → KHÔNG tạo đơn chat, sale xem/sửa đơn landing trong POS"
            log(f"  {'[THỬ] ' if dry else ''}⛔ {record.get('page_name') or ''} · "
                f"{record.get('khach') or ex.get('ten') or '?'}: {ly}")
            if not dry:
                Q.cmd_mark(record["page_id"], record["conversation_id"], ly)
            return "chan_trung_landing"
        if khac:   # khách mua lại / mua ở page khác -> vẫn lên đơn mới, chỉ nhắc kiểm tra
            ma = ", ".join(f"#{o.get('display_id') or o.get('id')}" for o in khac[:3])
            ex["canh_bao"].append(f"khách còn đơn khác cùng SĐT ({ma}) — kiểm tra không phải đơn trùng")
        ghi_chu = tao_don_moi(ex, record, dry)
    if not dry:
        Q.cmd_mark(record["page_id"], record["conversation_id"], ghi_chu)
    # Mọi lần tool ĐỤNG vào đơn — tạo mới hay bổ sung — đều trả hội thoại về CHƯA ĐỌC.
    danh_dau_chua_doc(record["page_id"], record["conversation_id"], dry)


# ═════════════════════════════════════════════════════════════════════════════
# LÊN ĐƠN KHÔNG CẦN TAG — chủ shop chốt 2026-09-08
# ═════════════════════════════════════════════════════════════════════════════
# Luật cũ: sale phải gắn tag "Lên đơn" thì đơn mới được tạo.
# Luật mới: *"không cần gắn tag gì cả, tạo đơn khi khách cho SĐT hoặc địa chỉ luôn, nó sẽ ở
# trạng thái Mới. Còn khi chốt xong số lượng, tiền hàng, địa chỉ và SĐT đầy đủ thì lúc đó mới
# chuyển sang Đã xác nhận."*
#
# Hai nửa của luật này ĐÃ CÓ SẴN, không phải viết mới:
#   · `tao_don_moi`         — thiếu thông tin thì tạo đơn và ĐỂ Ở "Mới"; đủ thì tự xác nhận
#   · `hoan_thien_don_thieu`— quay lại đọc hội thoại, điền nốt chỗ trống, ĐỦ thì chuyển "Đã xác nhận"
# Thứ duy nhất còn thiếu là CÁI CÒ: vòng quét cũ hỏi API chỉ những hội thoại có tag.
# Hàm dưới đây quét MỌI hội thoại gần đây rồi tự lọc "có SĐT hoặc địa chỉ".
#
# ⚠️ LỌC RẺ TRƯỚC, ĐỌC ĐẮT SAU. Bản đầu đọc tin nhắn của TỪNG hội thoại để tìm SĐT —
# 67 page UAE × 40 hội thoại = gần 2.700 lượt gọi API, chạy 20 phút chưa xong, không thể
# nhét vào vòng daemon 30 giây.
# Đo lại thấy API danh sách hội thoại ĐÃ TRẢ SẴN `has_phone` và `recent_phone_numbers`
# (kiểm chứng 2026-09-08 trên page Liali Jewellery UAE) — tức biết khách đã cho số hay chưa
# mà KHÔNG cần đọc tin nhắn. Nên nay: một lượt gọi cho cả page, lọc bằng `has_phone`, chỉ
# hội thoại nào qua cửa mới đọc tin nhắn. Từ 2.700 lượt xuống còn vài lượt.
#
# Địa chỉ không có trong danh sách, nhưng khách gần như luôn cho SĐT cùng lúc hoặc trước
# địa chỉ. Ai đã lưu địa chỉ trong hồ sơ khách thì cũng lọt qua cửa `has_phone` vì hồ sơ
# đó sinh ra từ đơn cũ.
#
# ⚠️ MẶC ĐỊNH TẮT. Bật bằng LEN_DON_KHONG_TAG=1 trong .env, hoặc chạy tay lệnh
# `quet-khong-tag`. Cố ý bắt phải bật: nó tạo đơn THẬT trên POS cho những hội thoại mà
# trước đây không ai đụng tới.

_TRAM_D = {"luc": 0.0, "cfg": {}, "chu": {}}


def _tram_bo_daemon(pid, cid):
    """TRAM_LANDING_2409 — page trạm landing (state/chung/page_gan_them.json khoá "tram_landing": một page, khách
    nhiều nước): daemon nước X chỉ lên nháp hội thoại mà sổ chủ state/chung/tram_landing_chu.json ghi đúng X.
    Chưa ai nhận = chưa rõ khách ở nước nào → để AI Sale hỏi nước, AI nước đó lên nháp (lên sớm là nháp rơi nhầm shop).
    Đọc hỏng → không bỏ (đường cũ)."""
    try:
        now = time.time()
        if now - _TRAM_D["luc"] > 5:
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "chung")
            try:
                _TRAM_D["cfg"] = json.load(open(os.path.join(base, "page_gan_them.json"),
                                                encoding="utf-8")).get("tram_landing") or {}
            except Exception:                            # noqa: BLE001
                pass
            try:
                _TRAM_D["chu"] = json.load(open(os.path.join(base, "tram_landing_chu.json"), encoding="utf-8")) or {}
            except FileNotFoundError:
                _TRAM_D["chu"] = {}
            except Exception:                            # noqa: BLE001 — đang ghi dở: giữ bản cũ
                pass
            _TRAM_D["luc"] = now
        if str(pid) not in _TRAM_D["cfg"]:
            return False
        mkey = os.path.basename(os.path.normpath(Q.STATE_DIR))
        v = _TRAM_D["chu"].get(str(cid)) or _TRAM_D["chu"].get(f"{pid}_{cid}") or {}
        return (v.get("nuoc") if isinstance(v, dict) else None) != mkey
    except Exception:                                    # noqa: BLE001
        return False


# ══ PAGE TRẠM LANDING: POS KHÔNG NHẬN PAGE → TẠO ĐƠN KHÔNG GẮN PAGE (TRAM_DON_2709) ═══════════════════════════════════
# 5 page trạm nằm ở shop Saudi; khách UAE / Qatar / Kuwait lên đơn ở shop nước đó → POS trả {'message': 'page_id is invalid',
# 'error_code': 104}. Ca Lalaine Alcoran · Yuki Store 26/09: AI chốt, khách nhận "Your order has been received" mà không có đơn
# (cùng ngày Mely Baldoviso, Vicky Tayag Pedere; daemon UAE hỏng 6 lần). Chỉ page trạm mới tạo lại — page thường nằm nhầm shop
# vẫn báo lỗi như cũ (tạo đơn không page ở shop sai tiền tệ còn tệ hơn).
_TRAM_DON = {"luc": 0.0, "cfg": {}}


def _tram_la_page(pid):
    try:
        if time.time() - _TRAM_DON["luc"] > 30:
            f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "chung", "page_gan_them.json")
            _TRAM_DON["cfg"] = json.load(open(f, encoding="utf-8")).get("tram_landing") or {}
            _TRAM_DON["luc"] = time.time()
        return str(pid) in _TRAM_DON["cfg"]
    except Exception:                                    # noqa: BLE001
        return False


def _post_don(body, record):
    """POST đơn; page trạm mà POS không nhận page_id → tạo lại không page / hội thoại, link hội thoại vào note."""
    res = P.api("POST", f"/shops/{P.SHOP_ID}/orders", body=body)
    co_id = isinstance(res, dict) and (res.get("id") or (isinstance(res.get("data"), dict) and res["data"].get("id")))
    if (not co_id and isinstance(res, dict) and "page_id is invalid" in str(res.get("message") or "")
            and _tram_la_page(record.get("page_id"))):
        body.pop("page_id", None)
        body.pop("conversation_id", None)
        body["note"] = ((body.get("note") or "").rstrip() + "\n[Tự động] Page trạm landing (page thuộc shop khác, đơn không gắn "
                        f"page) — hội thoại: https://pancake.vn/{record.get('page_id')}?c_id={record.get('conversation_id')}").strip()
        log(f"  🧭 page trạm {record.get('page_id')}: POS shop này không nhận page — tạo đơn không gắn page, link hội thoại vào note")
        res = P.api("POST", f"/shops/{P.SHOP_ID}/orders", body=body)
    return res


def quet_khong_tag(gio=2, dry=True, so=40, page_loc=None):
    """Quét hội thoại KHÔNG cần tag: có SĐT hoặc địa chỉ là lên đơn (trạng thái Mới).

    Trả (số hội thoại đã đọc, số hội thoại đủ điều kiện lên đơn).
    """
    tokens = Q.load_json(Q.TOKENS_FILE, {})
    products = Q.load_json(PRODUCTS_FILE, {})
    try:
        import ket_nap_page as K
        products = dict(K.ho_so_page(), **products)
    except Exception:                                    # noqa: BLE001
        pass
    processed = Q.load_json(Q.PROCESSED_FILE, {})
    doc = ra_don = bo_qua = xet = da_mua = 0

    # ── HỎI CÁC PAGE SONG SONG ───────────────────────────────────────────────
    # Đo thật 09/09: quét UAE mất 80 giây KỂ CẢ khi không có hội thoại nào để xử — thuần là
    # thời gian gọi 67 page lần lượt, mỗi page chờ mạng khoảng một giây. Đó là SÀN của cách
    # hỏi tuần tự, và nó khiến khách phải chờ hơn một phút dù nhịp chạy có dày tới đâu.
    # Hỏi song song thì phần chờ mạng chồng lên nhau. CHỈ song song ở bước ĐỌC danh sách;
    # phần tạo đơn vẫn chạy tuần tự — hai luồng cùng tạo đơn cho một khách là đẻ đơn trùng,
    # đúng thứ cả buổi hôm nay đi chữa.
    can = [(p, st) for p, st in tokens.items()
           if st.get("token") and not st.get("token_hong")
           and not (page_loc and str(p) != str(page_loc))]
    moc_tu = int(time.time()) - int(float(gio) * 3600)
    moc_den = int(time.time())

    def _lay(pst):
        p, st = pst
        r, e = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{p}/conversations",
                           # type=INBOX: chủ shop 16/09 *"k đọc cmt, để sale xử lý, đừng động vào"*.
                           # Không có tham số này, danh sách trả về CẢ bình luận bài đăng (type
                           # COMMENT) — bình luận có SĐT là daemon lên đơn + ghi sổ trên đó.
                           {"page_access_token": st["token"], "type": "INBOX", "since": moc_tu,
                            "until": moc_den, "order_by": "updated_at"})
        return p, st, (None if e else r)

    ket = []
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as bom:
            ket = list(bom.map(_lay, can))
    except Exception as e:                               # noqa: BLE001 — hỏng thì quay về tuần tự
        log(f"  ⚠️  chạy song song hỏng ({e}) — quay về hỏi lần lượt")
        ket = [_lay(x) for x in can]

    for pid, st, convs in ket:
        if convs is None:
            continue
        for conv in (convs.get("conversations") or [])[:so]:
            xet += 1
            cid = str(conv.get("id"))
            if _tram_bo_daemon(pid, cid):                # TRAM_LANDING_2409 — nháp do AI nước của khách lo
                continue
            if processed.get(f"{pid}_{cid}"):
                continue                                 # đã xét rồi, đừng đọc lại
            # ── CỬA RẺ NHẤT: sale đã đánh dấu hội thoại này xong chưa ───────
            # Đặt TRƯỚC mọi thứ: không tốn lượt gọi nào, và là kết luận của người.
            # ── THẺ "Đã gửi" → KHÔNG ĐỌC, KHÔNG ĐỤNG (chủ shop 16/09) ──────────────
            # *"không đọc thẻ đã gửi, để sale xử lý nhé, đừng động vào"*. Bỏ theo lưới 14/09
            # "thẻ gắn SỚM mà POS chưa có đơn thì vẫn xét lên đơn" (ca Sarah Nak Rantau) —
            # chủ shop chốt bỏ 16/09, cùng lúc bỏ ở AI Sale. Thẻ là kết luận của người.
            the = the_noi_da_xong(conv)
            if the:
                da_mua += 1
                log(f"  ⏭  {st.get('name','?')[:28]} · "
                    f"{((conv.get('customers') or [{}])[0].get('name') or '?')[:22]} — "
                    f"thẻ {the!r}: sale đã chốt đơn xong, không đụng")
                if not dry:
                    Q.cmd_mark(pid, cid, f"hội thoại mang thẻ {the!r} — sale đã chốt đơn xong")
                continue

            # ── CỬA RẺ: API đã nói sẵn khách có cho SĐT hay chưa ────────────
            cus = (conv.get("customers") or [{}])[0]
            co_dc_luu = bool(cus.get("shop_customer_addresses"))
            if not (conv.get("has_phone") or conv.get("recent_phone_numbers") or co_dc_luu):
                continue
            bo_qua += 1 * 0                              # (chỉ để đọc dễ: đã lọt cửa rẻ)
            rec = Q.extract_conversation(pid, st.get("name", pid), st["token"], conv)
            doc += 1
            ex = extract(rec, products)
            # ĐIỀU KIỆN CÒ: chỉ cần MỘT trong hai. Đúng lời chủ shop — địa chỉ phải đủ 3 cấp (17/09).
            if not (ex.get("sdt") or (ex.get("diachi") and dia_chi_3_cap(ex["diachi"])[0])):
                continue
            # ── CỬA MẠNH NHẤT: khách đã mua ở page này thì KHÔNG đụng nữa ──
            # MỌI số hội thoại từng ghi nhận, không chỉ số bộ trích chọn.
            so_hthoai = [x.get("captured") or x.get("phone_number")
                         for x in (conv.get("recent_phone_numbers") or [])]
            for c2 in (conv.get("customers") or []):
                so_hthoai += [x.get("phone_number")
                              for x in (c2.get("recent_phone_numbers") or [])]
            roi, mo_ta = da_mua_o_page(pid, cid, ex.get("sdt"),
                                       rec.get("khach") or ex.get("ten"),
                                       sdt_them=so_hthoai)
            if roi:
                da_mua += 1
                log(f"  ⏭  {st.get('name','?')[:28]} · {rec.get('khach') or '?'} — "
                    f"ĐÃ MUA ở page này ({mo_ta}) → nhân viên xử, không tạo đơn, không tư vấn")
                if not dry:
                    Q.cmd_mark(pid, cid, f"khách đã có đơn {mo_ta} ở page này — để nhân viên xử")
                continue
            ra_don += 1
            log(f"  {'[THỬ] ' if dry else ''}{st.get('name','?')[:30]} · {rec.get('khach') or '?'}"
                f" — có {'SĐT' if ex.get('sdt') else ''}{' + ' if ex.get('sdt') and ex.get('diachi') else ''}"
                f"{'địa chỉ' if ex.get('diachi') else ''}"
                f" · thiếu: {'; '.join(ex['thieu']) if ex['thieu'] else 'không → sẽ XÁC NHẬN luôn'}")
            xu_ly_mot(rec, products, dry)
            time.sleep(0.1)
    return xet, doc, ra_don, da_mua


def hoan_thien_don_thieu(dry=False, moi_giay=300, so_ngay=3):
    """Đơn tự động tạo lúc THIẾU thông tin -> quay lại đọc hội thoại, điền nốt phần còn trống,
    đủ thì tự chuyển 'Đã xác nhận'. Chỉ đụng đơn còn ở trạng thái 'Mới' (nhân viên chưa xử lý)
    và chỉ ĐIỀN CHỖ TRỐNG, không ghi đè dữ liệu có sẵn."""
    meta = Q.load_json(Q.META_FILE, {})
    now = int(time.time())
    if now - meta.get("lan_hoan_thien", 0) < moi_giay:
        return
    meta["lan_hoan_thien"] = now
    Q.save_json(Q.META_FILE, meta)

    orders = P.fetch_orders({"startDateTime": now - so_ngay * 86400, "endDateTime": now,
                             "page_size": 100, "page_number": 1})
    cho_xu_ly = [o for o in orders
                 if o.get("status") == 0 and "[Tự động]" in (o.get("note") or "")
                 and "THIẾU" in (o.get("note") or "")
                 and o.get("conversation_id") and o.get("page_id")]
    if not cho_xu_ly:
        return
    tokens = Q.load_json(Q.TOKENS_FILE, {})
    products = Q.load_json(PRODUCTS_FILE, {})
    for o in cho_xu_ly:
        oid, pid, cid = o.get("id"), str(o.get("page_id")), o.get("conversation_id")
        st = tokens.get(pid) or {}
        if not st.get("token"):
            continue
        try:
            rec = Q.extract_conversation(pid, st.get("name", pid), st["token"],
                                         {"id": cid, "from": {"name": o.get("bill_full_name")}})
            if rec.get("error"):
                continue
            ex = extract(rec, products)
            addr = o.get("shipping_address") or {}
            co_sdt = bool(o.get("bill_phone_number"))
            co_diachi = bool(addr.get("address") or addr.get("full_address"))
            co_sp = bool(o.get("items"))

            body, them = {}, []
            if not co_sdt and ex["sdt"]:
                body["bill_phone_number"] = ex["sdt"]; them.append("SĐT")
            if not co_diachi and ex["diachi"]:
                body["shipping_address"] = {
                    "full_name": o.get("bill_full_name") or ex["ten"],
                    "phone_number": o.get("bill_phone_number") or ex["sdt"] or "",
                    "address": ex["diachi"]}
                prov = P.detect_emirate(ex["diachi"])
                if prov:
                    body["shipping_address"]["province_id"] = prov
                    body["shipping_address"]["country_code"] = P.COUNTRY_CODE
                them.append("địa chỉ")
                _dien_dia_gioi(body["shipping_address"], ex["diachi"], them)      # DIA_GIOI_2509
            elif not (o.get("shipping_address") or {}).get("district_id"):
                _cu = o.get("shipping_address") or {}
                _sa = {k: _cu.get(k) for k in ("full_name", "phone_number", "address", "province_id", "commune_id") if _cu.get(k)}
                if (_cu.get("address") or _cu.get("full_address")) and \
                        _dien_dia_gioi(_sa, _cu.get("address") or _cu.get("full_address"), them):
                    body["shipping_address"] = _sa                  # DIA_GIOI_2509: nháp có địa chỉ mà chưa có quận
            _giu_khoi_dia_chi(o, body)
            if not co_sp and ex["variation_id"] and ex["qty"]:
                body["items"] = items_va_ship(ex)
                them.append("sản phẩm" + (" + hộp" if ex.get("them_hop") else ""))
            if not o.get("shipping_fee") and ex["gia"] is not None:
                body["shipping_fee"] = ex["gia"]     # quy ước shop: tiền thu nằm ở phí vận chuyển
                them.append(f"tiền thu {P.fmt_money(ex['gia'])}")
            if not (o.get("partner") or {}).get("partner_id"):
                dv = chon_dvvc(ex.get("ten_sp"), rec.get("page_id") or o.get("page_id"))   # ĐVVC theo page trước
                if dv:
                    body["partner"] = {"partner_id": dv["id"], "custom_partner_id": dv["id"],
                                       "partner_name": dv["ten"]}
                    them.append(f"ĐVVC {dv['ten']}")
            if not them:
                continue

            du = (co_sdt or "SĐT" in them) and (co_diachi or "địa chỉ" in them) and \
                 (co_sp or any(t.startswith("sản phẩm") for t in them)) and \
                 (bool(o.get("shipping_fee")) or any(t.startswith("tiền thu") for t in them))
            # Địa chỉ vừa điền mà lấy từ tin shop/bot (khách chưa tự gõ) thì KHÔNG tự xác nhận.
            # Bản cũ bỏ qua ex["thieu"] nên đơn #74140 (Carpio Jake, 14/09/2026) lấy tin mẫu page
            # "Ngayon, sabihin mo… 3. Kompletong address…" làm địa chỉ rồi lên thẳng Đã xác nhận.
            dc_tu_shop = "địa chỉ" in them and any(t.startswith("sale xác nhận địa chỉ") for t in ex["thieu"])
            if dc_tu_shop:
                du = False
            # Đơn mở bằng SĐT / địa chỉ máy ĐỌC TỪ ẢNH: lượt quét này không thấy ảnh, không biết khách đã tự gõ lại chưa →
            # KHÔNG tự xác nhận (24/09, ca Audrey C. Capitle #77053); AI Sale (thấy ảnh) hoặc sale xác nhận.
            _tu_anh = bool(R_NOTE_TU_ANH.search(o.get("note") or ""))
            if _tu_anh:
                du = False
            # Cửa này trước chỉ hỏi "ô địa chỉ có chữ không" (co_diachi) nên đơn địa chỉ mới có
            # mỗi tên tỉnh — hoặc TRỐNG TRƠN — vẫn lên "Đã xác nhận" (chủ shop 17/09). Nay đo
            # đúng cái ô sẽ nằm trên đơn sau lượt cập nhật này.
            _dc_sau = ((body.get("shipping_address") or {}).get("address")
                       or addr.get("full_address") or addr.get("address"))
            _li_dc = dia_chi_du_giao(_dc_sau)
            if not _li_dc:
                # xác nhận đòi đủ 3 cấp (chủ shop 18/09); tỉnh lấy từ ô tỉnh của đơn nếu chữ không lặp lại
                _ok3, _li3 = dia_chi_3_cap(_dc_sau, ((body.get("shipping_address") or {}).get("province_id")
                                                     or addr.get("province_id")))
                if not _ok3:
                    _li_dc = f"chưa đủ 3 cấp — {_li3}"
            # Ô tỉnh của đơn trống (địa chỉ AI Sale ghi từ lời khách không có tên tỉnh — 19/09) thì
            # dia_chi_3_cap còn đoán tỉnh từ tên khu, có thể SAI tỉnh ("Khalid" → Yanbu) → không tự xác nhận.
            if not _li_dc and not ((body.get("shipping_address") or {}).get("province_id") or addr.get("province_id")):
                _li_dc = "đơn chưa có tỉnh/thành"
            if _li_dc:
                du = False
            _li_trung = None                                 # LANDING_TRUNG_2909
            if du:
                _lt, _li_trung = don_landing_trung(o.get("bill_phone_number") or ex.get("sdt"),
                                                   _ma_chat({"items": o.get("items")}, ex), o.get("id"), cid)
                if _lt:
                    du = False
            ghi = f"[Tự động] Khách nhắn thêm — đã bổ sung: {', '.join(them)}."
            if dc_tu_shop:
                ghi += " ⚠ Địa chỉ lấy từ tin shop/bot, khách chưa tự gõ — sale đọc lại."
            if du:
                body["status"] = 1
                ghi += " Đủ thông tin → chuyển Đã xác nhận."
            else:
                _con = list(ex["thieu"])
                if _tu_anh:
                    _con.append("SĐT/địa chỉ máy đọc từ ảnh — sale kiểm rồi xác nhận")
                if _li_dc:
                    _con.insert(0, f"địa chỉ chưa đủ để giao — {_li_dc}")
                if _li_trung:
                    _con.insert(0, f"⚠ {_li_trung} — sale kiểm có phải đơn trùng rồi mới xác nhận")
                ghi += f" Vẫn thiếu: {'; '.join(_con)}."
            body["note"] = ((o.get("note") or "").strip() + "\n" + ghi).strip()

            if dry:
                log(f"  [THỬ] Sẽ hoàn thiện đơn #{o.get('display_id') or oid}: {', '.join(them)}"
                    f"{' → xác nhận' if du else ''}")
                continue
            P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{oid}", body=body)
            log(f"  ✔ Hoàn thiện đơn #{o.get('display_id') or oid} ({o.get('bill_full_name')}): "
                f"{', '.join(them)}{' → ĐÃ XÁC NHẬN' if du else ' (vẫn chờ thêm)'}")
        except (SystemExit, Exception) as e:  # noqa: BLE001 — 1 đơn lỗi không giết cả vòng
            log(f"  ✖ Lỗi hoàn thiện đơn {oid}: {e}")
        time.sleep(0.1)


def bao_loi_quet(pend, moi_giay=3600):
    """Đưa lỗi của vòng quét vào nhat_ky.log — nhưng đừng lặp lại mỗi 30 giây.

    Lỗi hay gặp nhất là TOKEN PAGE CHẾT: pages.fm vẫn trả HTTP 200 nên trước đây cả vòng
    quét im lặng, sale gắn tag "Lên đơn" mà không đơn nào được tạo và không ai biết.
    Chỉ ghi khi danh sách lỗi ĐỔI, hoặc mỗi giờ nhắc lại một lần.
    """
    loi = sorted(pend.get("loi") or [])
    meta = Q.load_json(Q.META_FILE, {})
    cu = meta.get("loi_quet") or {}
    if not loi:
        if cu:
            log("✔ Hết lỗi quét: mọi page đều đọc được hội thoại")
            meta["loi_quet"] = {}
            Q.save_json(Q.META_FILE, meta)
        return
    if loi == (cu.get("ds") or []) and time.time() - (cu.get("luc") or 0) < moi_giay:
        return
    hong = [e for e in loi if Q.LOI_TOKEN in e]
    log(f"⚠ Vòng quét lỗi {len(loi)} chỗ"
        + (f" — {len(hong)} page TOKEN HỎNG, hội thoại gắn tag ở đó KHÔNG lên đơn được" if hong else "")
        + ":")
    for e in loi[:5]:
        log(f"    - {e}")
    if len(loi) > 5:
        log(f"    ... và {len(loi) - 5} chỗ nữa (xem {Q.PENDING_FILE})")
    if hong:
        log(f"  → Cấp lại token: python3 auto_len_don.py setup {MK['key']} --force-token --hong")
    meta["loi_quet"] = {"ds": loi[:60], "luc": int(time.time())}
    Q.save_json(Q.META_FILE, meta)


# ═════════════════════════════════════════════════════════════════════════════
# VÒNG LÊN ĐƠN KHÔNG CẦN TAG — chạy trong daemon
# ═════════════════════════════════════════════════════════════════════════════
# HAI CÔNG TẮC, phải bật CẢ HAI mới chạy. Cố ý làm phiền:
#   LEN_DON_KHONG_TAG=1          bật tính năng
#   LEN_DON_KHONG_TAG_TT=uae     khai RÕ từng thị trường, cách nhau dấu phẩy
# Thiếu công tắc thứ hai thì không thị trường nào chạy, kể cả khi công tắc một đã bật.
# Lý do: nó tạo đơn THẬT cho hội thoại mà trước đây không ai đụng tới — mở rộng phải là
# hành động có ý thức cho từng nước, không phải hệ quả của một biến môi trường.
#
# Nhịp: mỗi VONG_KHONG_TAG_PHUT (mặc định 10) chứ không phải mỗi vòng daemon 30 giây.
# Cửa sổ 2 giờ: đủ rộng để không sót hội thoại nào giữa hai lần chạy, đủ hẹp để nhẹ.

def vong_khong_tag(dry=False):
    if (os.environ.get("LEN_DON_KHONG_TAG") or Q.load_env().get("LEN_DON_KHONG_TAG")) != "1":
        return
    ds = (os.environ.get("LEN_DON_KHONG_TAG_TT")
          or Q.load_env().get("LEN_DON_KHONG_TAG_TT") or "")
    bat = {x.strip().lower() for x in ds.split(",") if x.strip()}
    if MK["key"] not in bat:
        return
    phut = float(os.environ.get("VONG_KHONG_TAG_PHUT")
                 or Q.load_env().get("VONG_KHONG_TAG_PHUT") or 10)
    gio_nhin = float(os.environ.get("VONG_KHONG_TAG_GIO")
                     or Q.load_env().get("VONG_KHONG_TAG_GIO") or 2)
    meta = Q.load_json(Q.META_FILE, {})
    now = int(time.time())
    if now - meta.get("lan_khong_tag", 0) < phut * 60:
        return
    meta["lan_khong_tag"] = now
    Q.save_json(Q.META_FILE, meta)
    t0 = time.time()
    xet, doc, ra, da_mua = quet_khong_tag(gio_nhin, dry)
    if ra or da_mua:
        log(f"  🧾 Lên đơn không tag: soi {xet} hội thoại trong {time.time()-t0:.0f}s · "
            f"{da_mua} đã có đơn (bỏ qua) · {ra} lên đơn"
            + ("  [CHẠY THỬ]" if dry else ""))


# ═════════════════════════════════════════════════════════════════════════════
# ĐVVC BỊ XOÁ KHI SỬA ĐỊA CHỈ TAY (DVVC_BI_XOA_2509 — kho báo 25/09, đơn #14643 Kuwait "AI ko báo lỗi thiếu đvvc")
# ═════════════════════════════════════════════════════════════════════════════
# POS tự đưa ĐVVC về trống khi lưu tay ô địa chỉ: 14 ngày tới 25/09 có 14 lần (UAE 6, Saudi 5, Mỹ 2, Kuwait 1), lần nào cũng đi
# kèm sửa địa chỉ, 10/14 là đơn chat máy tạo; đơn đi Chờ in → Đang đóng hàng mà trống ĐVVC tới khi kho phát hiện (#14643 ~37 giờ).
# Máy gắn lại ĐÚNG ĐVVC vừa bị xoá (lấy từ lịch sử đơn) khi đơn đã qua "Mới", chưa gửi, đã trống ≥10 phút (khỏi giành với sale
# đang sửa dở), và máy CHƯA từng gắn lại đơn đó (bị xoá lần nữa sau khi máy gắn → người cố ý, để yên). Chờ hàng (11) không đụng.
TT_CAN_DVVC = {1, 12, 13, 8, 9}          # Đã xác nhận · Chờ in · Đã in · Đang đóng hàng · Chờ chuyển hàng
DVVC_TRONG_TOI_THIEU = 600
GHI_GAN_LAI_DVVC = "[Tự động] Gắn lại ĐVVC"


def dvvc_can_gan_lai(o, now=None):
    """(partner_id bị xoá, lúc xoá epoch) nếu đơn này cần máy gắn lại ĐVVC, không thì None."""
    now = now or int(time.time())
    if o.get("status") not in TT_CAN_DVVC or (o.get("partner") or {}).get("partner_id"):
        return None
    if GHI_GAN_LAI_DVVC in (o.get("note") or ""):
        return None
    xoa = [h for h in (o.get("histories") or [])
           if (h.get("partner_id") or {}).get("old") and not (h.get("partner_id") or {}).get("new")]
    if not xoa:
        return None                          # chưa từng có ĐVVC (vd đơn Chờ hàng của landing) — không phải việc này
    luc = _epoch_utc(xoa[-1].get("updated_at"))
    if not luc or now - luc < DVVC_TRONG_TOI_THIEU:
        return None
    return xoa[-1]["partner_id"]["old"], luc


def gan_lai_dvvc_bi_xoa(dry=False, moi_giay=600, so_ngay=3):
    """Mỗi 10 phút / thị trường: đơn đã qua "Mới" mà ĐVVC bị lần sửa tay xoá mất → gắn lại đúng ĐVVC cũ + 1 dòng ghi chú."""
    meta = Q.load_json(Q.META_FILE, {})
    now = int(time.time())
    if now - meta.get("lan_gan_lai_dvvc", 0) < moi_giay:
        return
    meta["lan_gan_lai_dvvc"] = now
    Q.save_json(Q.META_FILE, meta)
    seen, orders = set(), []
    for pg in range(1, 40):
        r = P.fetch_orders({"startDateTime": now - so_ngay * 86400, "endDateTime": now,
                            "page_size": 100, "page_number": pg})
        moi = [o for o in r if o.get("id") not in seen]
        for o in moi:
            seen.add(o.get("id"))
            orders.append(o)
        if len(r) < 100 or not moi:
            break
    ten_dv = {(o.get("partner") or {}).get("partner_id"): (o.get("partner") or {}).get("partner_name")
              for o in orders if (o.get("partner") or {}).get("partner_name")}
    for v in [MK.get("dvvc")] + list(MK.get("dvvc_dac_biet") or []) + list(MK.get("dvvc_theo_page") or []):
        if isinstance(v, dict) and v.get("id"):
            ten_dv.setdefault(v["id"], v.get("ten"))
    for o in orders:
        can = dvvc_can_gan_lai(o, now)
        if not can:
            continue
        dv, luc = can
        ten = ten_dv.get(dv) or dv
        gio = time.strftime("%H:%M %d/%m", time.gmtime(luc + 7 * 3600))
        ma = o.get("display_id") or o.get("id")
        tt = P.STATUS_BY_CODE.get(o.get("status"), o.get("status"))
        if dry:
            log(f"  [THỬ] Sẽ gắn lại ĐVVC {ten} cho đơn #{ma} ({tt}) — bị xoá lúc {gio} VN")
            continue
        body = {"partner": {"partner_id": dv, "custom_partner_id": dv, "partner_name": ten},
                "note": ((o.get("note") or "").strip() + "\n"
                         + f"{GHI_GAN_LAI_DVVC} {ten} — lần sửa địa chỉ lúc {gio} (giờ VN) làm POS xoá mất").strip()}
        if o.get("shipping_fee"):
            body["shipping_fee"] = o["shipping_fee"]   # giữ tiền thu — POS hay đưa phí về 0 khi PUT thiếu ô này
        P.api("PUT", f"/shops/{P.SHOP_ID}/orders/{o.get('id')}", body=body)
        sau = P.api("GET", f"/shops/{P.SHOP_ID}/orders/{o.get('id')}")
        sau = sau.get("data") if isinstance(sau.get("data"), dict) else sau
        ok = (sau.get("partner") or {}).get("partner_id") == dv
        lech = (sau.get("cod") or 0) != (o.get("cod") or 0)
        log(f"  {'✔' if ok else '✖'} Gắn lại ĐVVC {ten} cho đơn #{ma} ({tt}) — bị xoá lúc {gio} VN"
            + (f" ⚠ COD đổi {P.fmt_money(o.get('cod'))} → {P.fmt_money(sau.get('cod'))}" if lech else ""))


def chay_mot_vong(dry=False, gio=None):
    """Chạy 1 vòng cho THỊ TRƯỜNG HIỆN TẠI (đã set_market).
    gio = quét bù ngược lại N giờ (dùng khi vừa bật thêm page: hội thoại gắn tag từ
    trước đó nằm ngoài cửa sổ quét thường ngày nên sẽ bị bỏ sót vĩnh viễn)."""
    try:
        hoan_thien_don_thieu(dry)   # đơn cũ còn thiếu: khách nhắn thêm thì điền nốt
    except (SystemExit, Exception) as e:  # noqa: BLE001
        log(f"✖ Lỗi hoàn thiện đơn thiếu: {e}")
    try:
        gan_lai_dvvc_bi_xoa(dry)    # DVVC_BI_XOA_2509: sửa địa chỉ tay làm POS xoá mất ĐVVC → gắn lại đúng ĐVVC cũ
    except (SystemExit, Exception) as e:  # noqa: BLE001
        log(f"✖ Lỗi gắn lại ĐVVC: {e}")
    try:
        vong_khong_tag(dry)         # lên đơn KHÔNG cần tag (mặc định TẮT — xem hàm)
    except (SystemExit, Exception) as e:  # noqa: BLE001
        log(f"✖ Lỗi vòng lên đơn không tag: {e}")
    try:
        dong_bo_kich_ban(dry)       # kéo "Trả lời nhanh" mới từ Pancake — không dính AI
    except (SystemExit, Exception) as e:  # noqa: BLE001
        log(f"✖ Lỗi đồng bộ kịch bản: {e}")
    old = Q.load_json(Q.PENDING_FILE, {}).get("quet_luc")
    try:
        Q.cmd_scan(gio)
    except SystemExit:
        return  # thị trường chưa có page sẵn sàng (chưa setup / chưa có tag) — bỏ qua
    pend = Q.load_json(Q.PENDING_FILE, {})
    if pend.get("quet_luc") == old:
        return  # bị LOCKED — phiên khác đang xử lý
    bao_loi_quet(pend)
    records = pend.get("cho_xu_ly") or []
    if not records:
        return
    # Bảng học từ đơn THẬT là chuẩn; hồ sơ suy luận của ket_nap_page chỉ lấp chỗ trống
    # cho page mới chưa có đơn nào (nên nó nằm dưới, học được là ghi đè).
    products = Q.load_json(PRODUCTS_FILE, {})
    try:
        import ket_nap_page as K   # nhập trong hàm: ket_nap_page nhập ngược lại module này
        products = dict(K.ho_so_page(), **products)
    except (SystemExit, Exception) as e:  # noqa: BLE001 — thiếu hồ sơ không chặn vòng lên đơn
        log(f"⚠ Không đọc được hồ sơ page: {e}")
    if not products:
        log("⚠ Chưa có bảng sản phẩm — chạy: python3 auto_len_don.py hoc-san-pham " + MK["key"])
    attempts = Q.load_json(ATTEMPTS_FILE, {})
    try:
        for r in records:
            key = f"{r['page_id']}_{r['conversation_id']}"
            try:
                xu_ly_mot(r, products, dry)
                attempts.pop(key, None)
            except (SystemExit, Exception) as e:  # noqa: BLE001 — 1 hội thoại lỗi không giết cả vòng
                attempts[key] = attempts.get(key, 0) + 1
                log(f"  ✖ Lỗi hội thoại {key} (lần {attempts[key]}): {e}")
                if attempts[key] >= 5 and not dry:
                    Q.cmd_mark(r["page_id"], r["conversation_id"], f"LỖI 5 lần, cần xử lý tay: {e}")
                    attempts.pop(key, None)
    finally:
        Q.save_json(ATTEMPTS_FILE, attempts)
        Q.release_lock()


# ═════════════════════════════════════════════════════════════════════════════
# ĐỒNG BỘ KỊCH BẢN — chạy trong daemon, KHÔNG dính gì tới AI
# ═════════════════════════════════════════════════════════════════════════════
# Kịch bản là mục "Trả lời nhanh" marketer cài trên Pancake. Kéo nó về chỉ là ĐỌC CẤU HÌNH
# bằng PANCAKE_USER_TOKEN — không gọi model, không tốn xu nào.
#
# ⚠️ Trước 2026-09-09 lệnh đồng bộ này nằm TRONG `ai_sale.py chay`, nên nó chỉ chạy khi AI
# Sale chạy. AI Sale chưa có tiền model là kịch bản đứng im: marketer sửa giá trên Pancake mà
# máy chủ vẫn dùng bản chụp cũ. Đặt nhầm chỗ chứ không phải phụ thuộc kỹ thuật — chủ shop chỉ
# ra 09/09. Nay nó ở đây, chạy độc lập.
#
# Rất nhẹ nhờ mẹo `client_version` của Pancake: gửi đúng số phiên bản đang giữ thì API trả
# vỏn vẹn {"data":"data_up_to_date"} (~100 byte) thay vì 20.000 byte. Nên hỏi cả trăm page
# mỗi 15 phút vẫn không đáng kể.

def dong_bo_kich_ban(dry=False, moi_giay=900):
    meta = Q.load_json(Q.META_FILE, {})
    if time.time() - meta.get("lan_dong_bo_kb", 0) < moi_giay:
        return
    meta["lan_dong_bo_kb"] = int(time.time())
    Q.save_json(Q.META_FILE, meta)
    if dry:
        return
    mkey = MK["key"]
    try:
        import kich_ban as KB
    except Exception as e:                               # noqa: BLE001
        return log(f"  ✖ không nạp được kich_ban: {e}")
    try:
        n, doi, loi, chua = KB.dong_bo(mkey)
    except Exception as e:                               # noqa: BLE001
        return log(f"  ✖ Lỗi đồng bộ kịch bản: {e}")
    if doi:
        log(f"  📋 Kịch bản mới: {len(doi)} page — {', '.join(x[:26] for x in doi[:4])}"
            + (f" …+{len(doi)-4}" if len(doi) > 4 else ""))

    # Page MỚI chưa từng có kịch bản: `dong_bo` chỉ soi page đã có bản chụp, nên phải kéo
    # riêng. Không có bước này thì page mkt vừa lên nằm mãi ở bậc "chưa có kịch bản".
    if not chua:
        return
    tok = Q.load_env().get("PANCAKE_USER_TOKEN", "")
    f = os.path.join(Q.STATE_DIR, "kich_ban.json")
    f_hong = os.path.join(Q.STATE_DIR, "kich_ban_hong.json")
    kb = Q.load_json(f, {})
    hong = Q.load_json(f_hong, {})
    now = int(time.time())
    them = 0
    for pid, st in Q.load_json(Q.TOKENS_FILE, {}).items():
        if pid in kb or not st.get("token") or st.get("token_hong"):
            continue
        # Kéo hỏng thì NGHỈ 24 GIỜ mới thử lại. Không có bước này, 66 page hỏng bị hỏi lại
        # mỗi 15 phút — khoảng 6.300 lượt API vô ích mỗi ngày, và không ai biết vì sao hỏng.
        cu_hong = hong.get(pid) or {}
        if now - (cu_hong.get("luc") or 0) < 86400:
            continue
        m, err = KB.tai_1_page(pid, tok)
        if err or not m or not m.get("mau"):
            hong[pid] = {"luc": now, "ten": st.get("name"),
                         "ly_do": ("hết gói cước Pancake" if err and "success=false" in str(err)
                                   else "chưa cài Trả lời nhanh" if not err
                                   else str(err)[:70])}
            continue
        hong.pop(pid, None)
        kb[pid] = {"ten_page": st.get("name"), "phien_ban": m["phien_ban"],
                   "chu_de": [{"id": c.get("id"), "ten": c.get("name")} for c in m["chu_de"]],
                   "mau": [KB._gon(x) for x in m["mau"]], "tai_luc": int(time.time())}
        them += 1
        time.sleep(0.12)
    Q.save_json(f_hong, hong)
    if them:
        Q.save_json(f, kb)
        log(f"  📋 Kéo kịch bản cho {them} page mới")


def ket_nap_dinh_ky(dry=False, moi_giay=3600):
    """Kết nạp page mới (token + chốt SKU) — mỗi thị trường tối đa 1 lần/giờ.

    Tốn khá nhiều lệnh API nên không chạy mỗi vòng 30s. Page mới trong vòng 1 giờ
    chưa kịp có khách chốt đơn, nên nhịp này thoải mái.
    """
    meta = Q.load_json(Q.META_FILE, {})
    if time.time() - meta.get("lan_ket_nap", 0) < moi_giay:
        return
    import ket_nap_page as K   # nhập trong hàm: ket_nap_page nhập ngược lại module này
    K.ket_nap(dry)
    if not dry:
        meta = Q.load_json(Q.META_FILE, {})   # đọc lại: ket_nap có thể đã ghi meta
        meta["lan_ket_nap"] = int(time.time())
        Q.save_json(Q.META_FILE, meta)


def chay_tat_ca(dry=False, only=None, landing=True, gio=None):
    """Một vòng quét: ĐƠN LANDING của cả 11 thị trường trước, rồi mới tới việc nặng.

    THỨ TỰ NÀY LÀ CỐ Ý (đổi 2026-08-23, đo từ log server). Trước đây mỗi thị trường chạy
    trọn gói kết nạp page -> quét hội thoại -> landing rồi mới sang thị trường sau; hai
    bước đầu ngốn ~20 phút/thị trường nên một vòng mất gần 2 TIẾNG và đơn landing của
    thị trường xếp sau phải nằm chờ hết chừng đó (đơn saudi về 15:51 tới 19:43 mới lên).
    Đơn landing là thứ nhạy thời gian nhất — khách vừa bấm form xong — nên cho đi trước;
    việc nặng chạy sau, chậm vài chục phút không ai thấy.
    """
    import don_landing as L  # nhập trong hàm: don_landing cũng nhập ngược lại module này
    ds_mkt = list(only or enabled_markets())
    if landing:
        for mkey in ds_mkt:
            try:
                set_market(mkey)
                L.chay_thi_truong(mkey, dry)   # đơn landing đổ về POS của chính thị trường đó
            except (SystemExit, Exception) as e:  # noqa: BLE001 — 1 thị trường lỗi không giết cả vòng
                log(f"✖ Lỗi landing page {mkey}: {e}")
            time.sleep(0.2)
    for mkey in ds_mkt:
        try:
            set_market(mkey)
            try:
                ket_nap_dinh_ky(dry)
            except (SystemExit, Exception) as e:  # noqa: BLE001 — kết nạp lỗi không chặn lên đơn
                log(f"✖ Lỗi kết nạp page {mkey}: {e}")
            chay_mot_vong(dry, gio)
        except (SystemExit, Exception) as e:  # noqa: BLE001 — 1 thị trường lỗi không giết thị trường khác
            log(f"✖ Lỗi thị trường {mkey}: {e}")
            Q.release_lock()
        time.sleep(0.2)


def daemon(interval=30):
    log(f"🚀 Daemon đa thị trường khởi động — chu kỳ {interval}s, thị trường: {', '.join(enabled_markets())}")
    for mkey in enabled_markets():  # nhả khóa cũ (khóa của tiến trình trước thuộc về mình)
        Q.set_state_dir(os.path.join(BASE_STATE, mkey))
        Q.release_lock()
    # 23/09/2026: luồng NỀN ghi số đơn landing vào hội thoại Messenger của khách (khung "Đơn hàng"
    # cạnh chat không hiện được đơn landing). Chạy 60s/lượt, không chờ vòng dưới. Hỏng không chặn lên đơn.
    try:
        import landing_vao_chat
        landing_vao_chat.chay_nen()
    except Exception as e:  # noqa: BLE001
        log(f"✖ Không bật được luồng ghi đơn landing vào chat: {e}")
    while True:
        chay_tat_ca()
        time.sleep(interval)


def cmd_thi_truong():
    print(f"\n🌍 Thị trường ({len(MARKETS)}):")
    for mkey, m in MARKETS.items():
        trang_thai = "BẬT" if m.get("bat", True) else "tắt"
        tokens = Q.load_json(os.path.join(BASE_STATE, mkey, "page_tokens.json"), {})
        ready = sum(1 for st in tokens.values() if st.get("token") and Q.tag_ids_of(st))
        print(f"  • {mkey:<10} {m['ten']:<14} shop {m['shop_id']:<12} {m['tien_te']:<4} [{trang_thai}] — page sẵn sàng: {ready}")
    print("\nSetup thị trường mới: python3 auto_len_don.py setup <thị trường>")


def bao_page_hong(hong, tong):
    """In danh sách page không đọc được hội thoại. Token hỏng thì pages.fm trả HTTP 200
    rỗng, rất dễ tưởng nhầm thành 'khách này không có hội thoại nào'."""
    if not hong:
        return
    print(f"\n⚠ {len(hong)}/{tong} page KHÔNG đọc được hội thoại (không phải là khách không có):")
    for h in hong[:8]:
        print(f"    - {h}")
    if len(hong) > 8:
        print(f"    ... và {len(hong) - 8} page nữa")
    print(f"    → Cấp lại token: python3 auto_len_don.py setup {MK['key']} --force-token --hong")


def cmd_lam_lai(mkey, tu_khoa, ngay=3):
    """Xoá dấu 'đã xử lý' của hội thoại theo tên khách -> vòng quét sau sẽ lên đơn lại.
    Dùng khi hội thoại bị bỏ sót vì luật cũ (vd bị chặn nhầm do trùng SĐT)."""
    set_market(mkey)
    processed = Q.load_json(Q.PROCESSED_FILE, {})
    tokens = Q.load_json(Q.TOKENS_FILE, {})
    now = int(time.time())
    xoa, hong, doc_duoc = 0, [], 0
    for pid, st in tokens.items():
        if not st.get("token"):
            continue
        res, err = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{pid}/conversations",
                               {"page_access_token": st["token"], "type": "INBOX",
                                "since": now - ngay * 86400, "until": now})
        if err:
            hong.append(f"{st.get('name', pid)} ({pid}): {err}")
            continue
        doc_duoc += 1
        for conv in (res or {}).get("conversations") or []:
            name = ((conv.get("from") or {}).get("name") or "")
            if tu_khoa.lower() not in name.lower():
                continue
            key = f"{pid}_{conv.get('id')}"
            if key in processed:
                cu = processed.pop(key)
                xoa += 1
                print(f"  ✔ Cho quét lại: {name} — page {st.get('name')} (trước đó: {cu.get('ghi_chu', cu)})")
            else:
                print(f"  • {name} — page {st.get('name')}: chưa từng xử lý, vòng quét sau sẽ tự lên đơn")
        time.sleep(0.05)
    Q.save_json(Q.PROCESSED_FILE, processed)
    bao_page_hong(hong, doc_duoc + len(hong))
    print(f"\nĐã bỏ dấu 'đã xử lý' cho {xoa} hội thoại. Chờ tối đa 30 giây, xem log:")
    print("  tail -20 /opt/pancake-tool/state/nhat_ky.log")


def cmd_soi(mkey, tu_khoa, ngay=3):
    """Soi 1 hội thoại: in tin nhắn + hệ thống trích được gì / thiếu gì.
    Dùng để chẩn đoán 'sao khách X chưa lên đơn'. CHỈ ĐỌC, không tạo/sửa gì."""
    set_market(mkey)
    print(f"\n🔧 Cấu hình đang dùng: SĐT {MK['sdt_regex']}  |  tiền {MK['tien_te']} x{MK.get('scale', 100)}")
    tokens = Q.load_json(Q.TOKENS_FILE, {})
    ready = {p: st for p, st in tokens.items() if st.get("token")}
    print(f"   Quét {len(ready)} page có token, tìm {tu_khoa!r} trong {ngay} ngày...")
    now = int(time.time())
    products = Q.load_json(PRODUCTS_FILE, {})
    processed = Q.load_json(Q.PROCESSED_FILE, {})
    thay, hong = 0, []
    for pid, st in ready.items():
        res, err = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{pid}/conversations",
                               {"page_access_token": st["token"], "since": now - ngay * 86400, "until": now})
        if err:
            hong.append(f"{st.get('name', pid)} ({pid}): {err}")
            continue
        for conv in (res or {}).get("conversations") or []:
            name = ((conv.get("from") or {}).get("name") or "")
            if tu_khoa.lower() not in name.lower():
                continue
            thay += 1
            tags = [t.get("text") for t in (conv.get("tags") or []) if t]
            key = f"{pid}_{conv.get('id')}"
            print(f"\n{'='*70}\n📄 {name} — page {st.get('name')} ({pid})")
            print(f"   Conversation: {conv.get('id')}")
            print(f"   TAGS: {tags or '(chưa có tag nào)'}")
            muon = set(Q.tag_ids_of(st))
            dang_gan = {t.get("id") for t in (conv.get("tags") or []) if t}
            print(f"   Tag 'Lên đơn' của page này: id {sorted(muon) or '(chưa dò được)'} — "
                  f"{'✔ ĐANG GẮN' if (muon & dang_gan) else '✖ CHƯA GẮN'}")
            print(f"   Đã xử lý: {processed.get(key, '✖ chưa')}")
            rec = Q.extract_conversation(pid, st.get("name", pid), st["token"], conv)
            print(f"\n   --- TIN NHẮN ({len(rec.get('tin_nhan') or [])}) ---")
            for m in rec.get("tin_nhan") or []:
                print(f"   [{m['ai']:>5}] {m['noi_dung'][:150]}")
            ex = extract(rec, products)
            print(f"\n   --- HỆ THỐNG TRÍCH ĐƯỢC ---")
            print(f"   Tên      : {ex['ten']}")
            print(f"   SĐT      : {ex['sdt'] or '✖ KHÔNG BẮT ĐƯỢC'}")
            print(f"   Địa chỉ  : {ex['diachi'] or '✖ KHÔNG BẮT ĐƯỢC'}")
            print(f"   Giá      : {P.fmt_money(ex['gia']) if ex['gia'] else '✖ KHÔNG BẮT ĐƯỢC'}")
            print(f"   Sản phẩm : {ex['ten_sp'] or '✖ page chưa có bảng SP'} x{ex['qty']}")
            print(f"   THIẾU    : {'; '.join(ex['thieu']) if ex['thieu'] else '✔ ĐỦ HẾT'}")
            if ex["canh_bao"]:
                print(f"   Lưu ý    : {'; '.join(ex['canh_bao'])}")
        time.sleep(0.05)
    bao_page_hong(hong, len(ready))
    if not thay:
        print(f"\n✖ Không thấy hội thoại nào tên chứa {tu_khoa!r} trong {ngay} ngày "
              f"trên {len(ready) - len(hong)} page đọc được.")
        print("   → Page của khách này có thể chưa setup được (hết gói cước), token hỏng "
              "(xem cảnh báo trên) hoặc thuộc thị trường khác.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1].lower(), sys.argv[2:]
    mkey_args = [a for a in args if not a.startswith("--") and not a.isdigit()]
    if cmd == "thi-truong":
        cmd_thi_truong()
    elif cmd == "lam-lai":
        if len(mkey_args) < 2:
            raise SystemExit('Dùng: lam-lai <thị trường> "<tên khách>"   (vd: lam-lai uae "Jame Rus")')
        ngay = int([a for a in args if a.isdigit()][0]) if any(a.isdigit() for a in args) else 3
        cmd_lam_lai(mkey_args[0], " ".join(mkey_args[1:]), ngay)
    elif cmd == "soi":
        if len(mkey_args) < 2:
            raise SystemExit('Dùng: soi <thị trường> "<tên khách>"   (vd: soi kuwait "Amani")')
        ngay = int([a for a in args if a.isdigit()][0]) if any(a.isdigit() for a in args) else 3
        cmd_soi(mkey_args[0], " ".join(mkey_args[1:]), ngay)
    elif cmd == "setup":
        if not mkey_args:
            raise SystemExit("Dùng: setup <thị trường>  (xem danh sách: thi-truong)")
        set_market(mkey_args[0])
        only = None
        if "--only" in args:
            only = set(args[args.index("--only") + 1].split(","))
        Q.cmd_setup(only, "--force-token" in args, "--hong" in args)
    elif cmd in ("quet-khong-tag", "quet_khong_tag"):
        if not mkey_args:
            raise SystemExit("Dùng: quet-khong-tag <thị trường> [--gio 2] [--thu] [--page ID]")
        set_market(mkey_args[0])
        gio = float(args[args.index("--gio") + 1]) if "--gio" in args else 2
        page_loc = args[args.index("--page") + 1] if "--page" in args else None
        dry = "--thu" in args
        if not dry and os.environ.get("LEN_DON_KHONG_TAG") != "1" \
                and (Q.load_env().get("LEN_DON_KHONG_TAG") != "1"):
            raise SystemExit(
                "⛔ Luật 'lên đơn không cần tag' đang TẮT. Nó tạo đơn THẬT cho những hội thoại\n"
                "   trước đây không ai đụng tới, nên phải bật có ý thức:\n"
                "     · xem thử   : thêm --thu\n"
                "     · bật thật  : thêm LEN_DON_KHONG_TAG=1 vào .env")
        x, d, n, m = quet_khong_tag(gio, dry, page_loc=page_loc)
        print(f"\n  soi {x} hội thoại · {d} qua cửa rẻ · {m} BỎ QUA vì khách đã mua ở page này"
              f" · {n} đủ điều kiện lên đơn"
              + ("  — CHẠY THỬ, chưa tạo đơn nào" if dry else ""))
    elif cmd == "pages":
        if not mkey_args:
            raise SystemExit("Dùng: pages <thị trường>")
        set_market(mkey_args[0])
        Q.cmd_pages()
    elif cmd == "ket-nap":
        import ket_nap_page as K
        for mkey in (mkey_args or enabled_markets()):
            try:
                set_market(mkey)
                K.ket_nap(dry="--thu" in args)
            except (SystemExit, Exception) as e:  # noqa: BLE001
                log(f"✖ Lỗi kết nạp page {mkey}: {e}")
    elif cmd == "bao-cao":
        import ket_nap_page as K
        K.cmd_bao_cao(mkey_args or None)
    elif cmd == "hoc-san-pham":
        for mkey in (mkey_args or enabled_markets()):
            try:
                set_market(mkey)
                hoc_san_pham()
            except (SystemExit, Exception) as e:  # noqa: BLE001
                log(f"✖ Lỗi học sản phẩm {mkey}: {e}")
    elif cmd == "chay":
        gio = int(args[args.index("--gio") + 1]) if "--gio" in args else None
        chay_tat_ca(dry="--thu" in args, only=mkey_args or None, gio=gio)
    elif cmd == "daemon":
        giay = int(args[args.index("--giay") + 1]) if "--giay" in args else 30
        daemon(giay)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

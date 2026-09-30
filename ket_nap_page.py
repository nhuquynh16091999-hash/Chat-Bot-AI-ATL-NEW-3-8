#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KẾT NẠP PAGE MỚI — chạy TRƯỚC vòng lên đơn, mỗi thị trường 1 lần/giờ.

Vấn đề nó giải: mỗi ngày shop đẻ thêm page mới, mỗi page bán 1 sản phẩm (1 SKU).
Page mới thì (1) chưa có page token nên hệ thống không nhìn thấy hội thoại,
(2) chưa có đơn cũ nên bảng học sản phẩm (hoc_san_pham) trống -> đơn tạo ra thiếu
sản phẩm và số lượng, nằm im ở "Mới".

Module này lấp đúng 2 lỗ đó:
  1. Phát hiện page mới trong shop -> tự tạo page token (CHỈ page chưa có token).
  2. Chốt SKU cho page bằng thang tín hiệu:
       a. mã sản phẩm ("227 - ...") xuất hiện trong bài post / tin bot
       b. khớp tên sản phẩm trong catalog với tên page + post + tin bot
       c. hỏi AI 1 lần (Haiku) -> cache vĩnh viễn
  3. Đọc bảng giá->số lượng từ chính lời chào hàng của bot
     ("Buy 1 Get 1 FREE – 99 AED" -> 99 AED = 2 cái), không cần đơn cũ.

Kết quả ghi vào state/<thị trường>/page_ho_so.json, cùng khuôn với page_products.json
nên auto_len_don dùng thẳng. Bảng học từ đơn THẬT luôn thắng hồ sơ suy luận.

Lệnh:
  python3 ket_nap_page.py ket-nap <thị trường> [--thu] [--sl 20]
  python3 ket_nap_page.py ho-so <thị trường>            # xem đã chốt được gì
  python3 ket_nap_page.py bao-cao [thị trường ...]      # báo cáo hằng ngày
"""

import json
import os
import re
import sys
import time

import auto_len_don as A
import pancake_order as P
import quet_hoi_thoai as Q

# Tạo page token là thao tác GHI: tạo lại token của 1 page sẽ VÔ HIỆU token cũ.
# Máy Mac và server giữ 2 bộ token khác nhau -> chạy kết nạp từ Mac sẽ giết token
# của server. Chỉ mở khóa khi biến môi trường nói rõ đây là server.
LA_SERVER = (os.environ.get("PANCAKE_SERVER") or P.ENV.get("PANCAKE_SERVER")) == "1"

# Thư viện riêng của tool (chỉ có anthropic cho tầng chốt SKU bằng AI). Debian 12 trở đi
# chặn `pip3 install` vào python hệ thống (PEP 668 "externally-managed-environment"), nên
# cài bằng --target vào đây rồi tự nối vào sys.path — khỏi phải dựng venv và sửa file
# systemd, cũng không đụng gì tới python của hệ điều hành.
# Nối vào CUỐI sys.path chứ không phải đầu: thư mục này kéo theo cả pydantic, anyio,
# httpx, idna... đặt lên đầu là chúng che mất bản của hệ điều hành cho TOÀN BỘ daemon.
# Để cuối thì chỉ khi hệ thống không có mới lấy bản ở đây.
_THU_VIEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
if os.path.isdir(_THU_VIEN) and _THU_VIEN not in sys.path:
    sys.path.append(_THU_VIEN)

# Lỗi gói cước Pancake (121/122): page không cấp được token, không phải lỗi tạm thời
# -> đánh dấu bỏ qua vĩnh viễn, không thử lại mỗi giờ và không báo cáo cho user nữa.
LOI_GOI_CUOC = re.compile(r"\b12[12]\b|gói cước|goi cuoc|package|subscription|expired", re.I)

MAX_PAGE_MOI = 20      # số page chốt SKU mỗi lượt (chặn chi phí + thời gian 1 vòng)
MAX_HOI_THOAI = 6      # số hội thoại đọc để dò offer/sản phẩm
# Page đã thử mà KHÔNG chốt được sản phẩm thì nghỉ ngần này rồi hãy hỏi lại.
# Mỗi page tốn ~20-40 giây đọc post + tin nhắn; đo log server 2026-08-22: uae 20 page +
# romania 20 page chốt hụt, vòng nào cũng đọc lại đúng chừng đó = ~9 PHÚT/vòng vứt đi,
# trong khi nội dung page không đổi trong vài tiếng. Page MỚI vẫn được thử ngay lượt đầu.
NGHI_CHUA_CHOT = 24 * 3600
CACHE_CATALOG_NGAY = 1 / 24   # 19/09 tối: 7 ngày → 1 giờ — SP mới tạo trên POS (263 MIUCO) chờ cả tuần mới khớp


# ---------------- Đường dẫn state ----------------

def _thu_muc():
    return os.path.join(A.BASE_STATE, A.MK["key"])


def _f(ten):
    return os.path.join(_thu_muc(), ten)


# ---------------- Catalog sản phẩm của shop ----------------

def tai_catalog(bat_buoc=False):
    """Danh sách sản phẩm của thị trường hiện tại (cache 7 ngày).

    Trả về list [{product_id, ten, ma, variations:[{id, ten}]}] — 'ma' là số đầu
    tên sản phẩm theo quy ước của shop ("227 - Varicose Vein Relief Cream" -> "227").
    """
    cache = _f("catalog.json")
    cu = Q.load_json(cache, None)
    if cu and not bat_buoc and time.time() - cu.get("luc", 0) < CACHE_CATALOG_NGAY * 86400:
        return cu["san_pham"]

    rows = []
    for pg in range(1, 9):
        try:
            r = P.api("GET", f"/shops/{P.SHOP_ID}/products/variations",
                      {"page_number": pg, "page_size": 100})
        except (SystemExit, Exception) as e:  # noqa: BLE001 — lỗi 1 trang không hủy cả catalog
            A.log(f"⚠ Lỗi tải catalog trang {pg} ({e})")
            break
        d = r.get("data") or []
        rows += d
        if len(d) < 100:
            break
        time.sleep(0.2)

    gom = {}
    for v in rows:
        if v.get("is_removed"):
            continue
        pid = v.get("product_id") or (v.get("product") or {}).get("id")
        ten = (v.get("product") or {}).get("name")
        if not (pid and ten):
            continue
        sp = gom.setdefault(str(pid), {"product_id": str(pid), "ten": ten,
                                       "ma": _ma_sp(ten), "variations": []})
        sp["variations"].append({"id": v.get("id"), "ten": v.get("display_id")})

    san_pham = [sp for sp in gom.values() if sp["variations"] and not A.la_sp_test(sp["ten"])]
    Q.save_json(cache, {"luc": int(time.time()), "san_pham": san_pham})
    return san_pham


def _ma_sp(ten):
    """Mã đầu tên sản phẩm theo quy ước shop: '227 - Varicose...' -> '227'."""
    m = re.match(r"\s*(\d{2,4})\s*[-–—.]", str(ten or ""))
    return m.group(1) if m else None


# ---------------- 1. Phát hiện page mới + tạo token ----------------

def phat_hien_page_moi(dry=False):
    """So danh sách page của shop với page_tokens.json; page mới thì tạo token.

    Trả về (số page mới có token, danh sách tên page hết gói cước, số page thiếu tag).
    """
    tokens = Q.load_json(Q.TOKENS_FILE, {})
    try:
        pages = Q.get_pages()
    except SystemExit as e:
        A.log(f"⚠ Không lấy được danh sách page: {e}")
        return 0, [], 0

    # "Mới" KHÔNG chỉ là page chưa có ô trong file. Cấp token HỤT (hết gói cước mã 121/122,
    # hoặc "Thiếu quyền Admin") vẫn ghi một ô {"name": ...} vào tokens — nên lần sau page đó
    # không còn `not in tokens` nữa và KHÔNG BAO GIỜ được thử lại. Mà shop cho page lên/xuống
    # hàng ngày: page vừa gia hạn gói, hoặc user vừa nâng quyền Admin, sẽ nằm im vĩnh viễn —
    # AI Sale lẫn daemon lên đơn đều không nhìn thấy page đó, không một dòng log.
    # Đo UAE 2026-09-11: 68 page hết gói + 18 page thiếu quyền Admin (7 trong đó CÒN gói cước,
    # Botcake đang chạy, khách đang inbox) đều kẹt đúng kiểu này.
    # Nên: ô nào chưa có token thì thử lại, mỗi page nhiều nhất 1 lần/ngày.
    def _cho_token(p):
        st = tokens.get(str(p.get("id")))
        if st is None:
            return True                       # page mới tinh
        if st.get("token"):
            return False                      # đang chạy được rồi
        try:
            lan_truoc = float(st.get("thu_luc") or 0)
        except (TypeError, ValueError):
            lan_truoc = 0
        return time.time() - lan_truoc > 86400

    moi = [p for p in pages if _cho_token(p)]
    if moi and not LA_SERVER:
        A.log(f"⚠ Có {len(moi)} page mới nhưng KHÔNG tạo token: máy này không phải server. "
              f"Tạo token ở đây sẽ vô hiệu token của server. Đặt PANCAKE_SERVER=1 trên VPS.")
        moi = []

    them, het_goi = 0, []
    for p in moi[:60]:                       # chặn số lần gọi API mỗi vòng
        pid, ten = str(p.get("id")), p.get("name", "?")
        if dry:
            A.log(f"  [thử] page mới: {ten}")
            them += 1
            continue
        res, err = Q.http_json("POST", f"{Q.BASE_USER}/pages/{pid}/generate_page_access_token",
                               {"access_token": Q.USER_TOKEN})
        token = ((res or {}).get("page_access_token")
                 or ((res or {}).get("data") or {}).get("page_access_token"))
        st = dict(tokens.get(pid) or {})     # giữ dấu vết cũ, đừng xoá trắng ô
        st["name"] = ten
        if not token:
            loi = str(err or (res or {}).get("message") or res)
            st["thu_luc"] = time.time()         # mốc để 24h nữa _cho_token cho thử lại
            if LOI_GOI_CUOC.search(loi):
                st["bo_qua"] = "het_goi_cuoc"   # user đã chốt: page hết gói thì không chạy tự động
                st.pop("loi", None)             # chỉ giữ dấu của LẦN HỤT NÀY, đừng cộng dồn
                het_goi.append(ten)
            else:
                st["loi"] = loi[:200]
                st.pop("bo_qua", None)          # lần này hụt vì lý do KHÁC hết gói cước
        else:
            st["token"] = token
            for _k in ("bo_qua", "loi", "thu_luc"):
                st.pop(_k, None)                # page quay lại được thì xoá sạch dấu lần hụt
            them += 1
            A.log(f"  ✔ Kết nạp page mới: {ten}")
        tokens[pid] = st
        Q.save_json(Q.TOKENS_FILE, tokens)     # lưu từng page, gián đoạn không mất tiến độ
        time.sleep(0.2)

    # Dò tag "Lên đơn" cho page có token mà chưa có tag (page mới, hoặc user vừa
    # đồng bộ thiết lập trong Pancake). API Pancake KHÔNG tạo được tag -> chỉ dò.
    thieu_tag = token_hong = 0
    for pid, st in tokens.items():
        if not st.get("token") or st.get("bo_qua"):
            continue
        if Q.tag_ids_of(st):
            continue
        ids, loi = Q.find_tag_ids(pid, st["token"])   # chỉ đọc, chạy cả ở chế độ --thu
        # Gọi được API (dù page không có tag) là bằng chứng token còn sống -> xoá dấu hỏng.
        Q.danh_dau_token(st, None if (ids or loi == Q.KHONG_CO_TAG) else loi)
        if ids:
            st["tag_ids"] = ids
            st["tag_id"] = ids[0]
            A.log(f"  ✔ Page {st.get('name')} đã có tag {Q.TAG_NAME!r}")
        elif Q.la_loi_token(loi):
            token_hong += 1     # KHÔNG phải thiếu tag: token chết nên không đọc nổi tag
        else:
            thieu_tag += 1
        time.sleep(0.12)
    if token_hong:
        A.log(f"⚠ {token_hong} page TOKEN HỎNG — không đọc được tag, hội thoại gắn tag "
              f"{Q.TAG_NAME!r} ở đó sẽ KHÔNG lên đơn. Cấp lại token: "
              f"python3 auto_len_don.py setup {A.MK['key']} --force-token --hong")
    if not dry:
        Q.save_json(Q.TOKENS_FILE, tokens)
    return them, het_goi, thieu_tag


# ---------------- 2. Đọc nội dung page (post + tin bot) ----------------

def doc_noi_dung(pid, token, so_hoi_thoai=MAX_HOI_THOAI):
    """Gom chữ mô tả sản phẩm của page: TAG của page + bài post + tin của shop/bot.

    Trả về (chữ_mô_tả, danh_sách_tin_shop, lỗi_token). Token chết thì cả 3 lệnh gọi
    đều trả rỗng — phải nói ra, nếu không chỗ gọi tưởng page "không đủ căn cứ chốt SKU".
    """
    now = int(time.time())
    posts = []

    # Tag của page là chỗ đánh dấu mã SP KÍN ĐÁO nhất: khách không bao giờ nhìn thấy.
    # Tag tên nhân viên / "bỏ qua" / "bị block" không có số nên không gây nhiễu.
    res, loi_tag = Q.http_json("GET", f"{Q.BASE_PAGE_V1}/pages/{pid}/tags",
                               {"page_access_token": token})
    the = [str(t.get("text") or "") for t in ((res or {}).get("tags") or [])]
    if the:
        posts.append("TAG: " + " | ".join(the))
    res, loi_post = Q.http_json("GET", f"{Q.BASE_PAGE_V1}/pages/{pid}/posts",
                                {"page_access_token": token, "since": now - 60 * 86400,
                                 "until": now, "page_number": 1, "page_size": 5})
    for p in ((res or {}).get("posts") or (res or {}).get("data") or []):
        t = p.get("message") or p.get("content") or ""
        if t:
            posts.append(t)

    tin_shop = []
    res, loi_conv = Q.http_json("GET", f"{Q.BASE_PAGE_V2}/pages/{pid}/conversations",
                                {"page_access_token": token, "since": now - 30 * 86400,
                                 "until": now, "order_by": "updated_at"})
    for conv in ((res or {}).get("conversations") or [])[:so_hoi_thoai]:
        rec = Q.extract_conversation(pid, "", token, conv, max_tin=40)
        for m in (rec or {}).get("tin_nhan") or []:
            if m.get("ai") == "shop" and len(m.get("noi_dung", "")) > 30:
                tin_shop.append(m["noi_dung"])
        time.sleep(0.15)
    loi = next((e for e in (loi_tag, loi_post, loi_conv) if Q.la_loi_token(e)), None)
    return "\n".join(posts), tin_shop, loi


# ---------------- 3. Đọc bảng giá -> số lượng từ lời chào hàng của bot ----------------

# "Buy 1 Get 1 FREE", "buy 2 get 2", "mua 1 tặng 1", "買1送1"
# 19/09 tối: thêm "take" (Buy 1 Take 1 — cách nói của page PH) và "beli X gratis Y" (Indonesia). Thiếu thì
# "BUY 2 TAKE 2 – ONLY 159 SAR / 4 BOTTLES" rơi xuống DON_VI_RE, nhặt "2 BOTTLES" của dòng trên → 159 = 2 chai.
MUA_TANG_RE = re.compile(
    r"buy\s*(\d)\s*(?:,|and)?\s*(?:get|take)\s*(\d)|beli\s*(\d)\s*gratis\s*(\d)"
    r"|mua\s*(\d)\s*t[ăa]ng\s*(\d)|買\s*(\d)\s*送\s*(\d)", re.I)
# "4 Bottles", "2 pcs", "x2", "共4件", "2点"
# CỐ Ý KHÔNG nhận "set"/"pack"/"combo": đo trên đơn thật thấy 1 "Set" mà shop chào
# được nhân viên nhập thành 3 dòng SL (page Malabar Gold: "139 AED - 1 Set" nhưng
# POS ghi SL 3). Đơn vị gộp như vậy đọc ra là SAI số lượng — thà để trống, đơn treo
# cho nhân viên điền 1 lần rồi hoc_san_pham học lại vĩnh viễn.
DON_VI_RE = re.compile(
    r"\b(\d{1,2})\s*(?:x\s*)?(?:pcs?|pieces?|bottles?|tubes?|jars?|boxes?|pairs?|cái|chiếc)\b"
    r"|\bx\s*(\d{1,2})\b"
    r"|(\d{1,2})\s*(?:件|點|点|個|个|瓶|盒|支|入)", re.I)


def _qty_tu_chu(s, cuoi=False):
    """Số lượng nêu trong chuỗi. cuoi=True lấy lần khớp GẦN GIÁ NHẤT (cuối chuỗi)."""
    ms = list(MUA_TANG_RE.finditer(s)) or list(DON_VI_RE.finditer(s))
    if not ms:
        return None
    m = ms[-1] if cuoi else ms[0]
    so = [int(g) for g in m.groups() if g]
    q = sum(so) if m.re is MUA_TANG_RE else so[0]
    return q if 1 <= q <= 12 else None


def doc_offer(tin_shop):
    """Bảng {tiền: số lượng} suy từ chính lời chào hàng của bot trên page.

    Bot luôn nói rõ khuyến mãi kèm giá ("🎁 Buy 1 Get 1 FREE – 99 AED",
    "Buy 2 Get 2 FREE – 149 AED ✔ 4 Bottles") nên page CHƯA CÓ ĐƠN NÀO vẫn suy được
    số lượng — đúng bằng bảng mà hoc_san_pham học được từ đơn thật.

    Một tin thường chào 2-3 gói liền nhau, nên cửa sổ đọc quanh mỗi giá phải CẮT ở
    giá liền trước/liền sau, không thì gói này nuốt số lượng của gói kia.
    """
    tu_tien = A.MK.get("tu_tien_te") or ""
    res = []
    if A.MK.get("ky_hieu_truoc"):                 # ưu tiên dạng "NT$1290" / "¥6999"
        res.append(re.compile(r"(?:" + A.MK["ky_hieu_truoc"] + r")\s*(\d[\d.,]*)", re.I))
    if tu_tien:
        # (?!\s*\d): "買1送1 NT$1290" — chữ NT$ ở đây là tiền tố của 1290, không phải
        # hậu tố của số 1 trong "送1", nếu không sẽ đọc thành giá 1 đồng.
        res.append(re.compile(r"(\d[\d.,]*)\s*(?:" + tu_tien + r")(?!\s*\d)", re.I))

    phieu = {}                                    # {tiền: {số lượng: số phiếu}}
    for text in tin_shop:
        moc, cuoi_truoc = [], -1
        for m in sorted((m for rx in res for m in rx.finditer(text)), key=lambda m: m.start()):
            if m.start() >= cuoi_truoc:           # bỏ khớp chồng lấn giữa 2 kiểu viết giá
                moc.append(m)
                cuoi_truoc = m.end()
        for i, m in enumerate(moc):
            gia = P.parse_money(m.group(1))
            if not gia or gia <= 0:
                continue
            dau = max(moc[i - 1].end() if i else 0, m.start() - 100)
            het = min(moc[i + 1].start() if i + 1 < len(moc) else len(text), m.end() + 70)
            qty = _qty_tu_chu(text[dau:m.start()], cuoi=True) or _qty_tu_chu(text[m.end():het])
            if not qty:
                continue
            phieu.setdefault(str(gia), {})
            phieu[str(gia)][qty] = phieu[str(gia)].get(qty, 0) + 1

    return {gia: max(c.items(), key=lambda kv: kv[1])[0] for gia, c in phieu.items()}


# ---------------- 4. Chốt SKU cho page ----------------

BO_TU = {"uae", "ksa", "ph", "in", "the", "dubai", "store", "shop", "official", "emirates",
         "kuwait", "qatar", "oman", "bahrain", "saudi", "usa", "japan", "taiwan", "and",
         "for", "of", "new", "best", "buy", "get", "free", "now", "your", "our", "with"}


def _tu(s):
    return {w for w in P.norm_ascii(s).split() if len(w) > 2 and w not in BO_TU}


def _nhan_ma_sp(chu):
    """Mã sản phẩm do người viết kịch bản CỐ Ý đánh dấu.

    Nhận mọi kiểu quen tay: [227] / (227) / #227 / SP227 / SKU 227 / mã 227 / code 227.
    Đây là tín hiệu chắc chắn nhất và rẻ nhất: người lập page đã biết SKU sẵn, chỉ cần
    ghi 1 nhãn vào kịch bản chào hàng là khỏi cần đoán mò hay gọi AI.

    CỐ Ý không nhận dạng trần "227 - Tên": tin chào hàng đầy giá kiểu "99 – Free
    Delivery" sẽ bị đọc nhầm thành mã. Dạng đó đã được tầng khớp tên lo (tên sản phẩm
    xuất hiện nguyên vẹn thì cộng điểm mạnh).
    """
    ra = set()
    for m in re.finditer(
            r"[\[(]\s*(\d{2,4})\s*[\])]"                              # [227]  (227)
            r"|#\s*(\d{2,4})\b"                                       # #227
            r"|\b(?:sp|sku|mã|ma|code|mahang|mã hàng)\s*[:#.\-]?\s*(\d{2,4})\b",  # SP227, mã 227
            chu, re.I):
        ra.add(next(g for g in m.groups() if g))
    return ra


# Mẫu CHÀO HÀNG / BÁO GIÁ — nơi kịch bản gọi đúng tên sản phẩm page đang bán.
# Chủ shop chỉ ra 2026-09-09: *"thường ở phần chào hàng, tên sản phẩm sẽ như này."*
# Đo thật cùng ngày, đây là chỗ phân biệt page THẬT với page chỉ nhắc tên trong câu kể:
#   DermaCare UAE     — "Varicose Vein Relief Cream" nằm ở mẫu /chaohang   -> page thật bán
#   Comfort Joint UAE — "Synovial Meniscus Cream" nằm ở mẫu KHÔNG TÊN,
#                        trong một câu chứng thực khách hàng                -> page đang thử
# Nếu quét cả kịch bản thì hai ca này giống hệt nhau, và page thử bị gán nhầm SKU.
MAU_CHAO = ("chaohang", "chao_hang", "chào_hàng", "chàohàng", "chao", "chào",
            "bao_gia", "báo_giá", "baogia", "báogiá", "bao-gia", "báo-giá",
            "gia", "giá", "price", "p", "pr", "promo", "intro", "sp", "product")


def chu_kich_ban(pid, chi_chao_hang=True):
    """Toàn bộ chữ trong kịch bản ("Trả lời nhanh") của page — nguồn ĐOÁN SKU TỐT NHẤT.

    Chủ shop chỉ ra 2026-09-09: *"trong phần kịch bản chào hàng, bạn cũng nắm được sản phẩm
    đó để lên đúng SKU."* Đúng — và đo thật ngay hôm đó: trong 33 page chưa chốt được SKU,
    riêng kịch bản chốt thêm được 17 page (51%), MIỄN PHÍ.

    Vì sao nó tốt hơn bài quảng cáo: kịch bản là bài shop viết ĐỂ BÁN chính món đó, nên gọi
    thẳng tên sản phẩm. Tên page thì hay đặt kiểu thương hiệu ("BodyFirm Essentials UAE",
    "Lunar Blessings Store") — không có chữ nào khớp kho.

    `ket_nap_page` viết trước khi có `kich_ban.py` (03/09) nên chưa từng dùng nguồn này.
    """
    try:
        f = os.path.join(Q.STATE_DIR, "kich_ban.json")
        v = (Q.load_json(f, {}) or {}).get(str(pid)) or {}
        mau = v.get("mau") or []
        if chi_chao_hang:
            mau = [m for m in mau
                   if (m.get("tu_khoa") or "").strip().lower().replace(" ", "") in MAU_CHAO]
        return "\n".join(t for m in mau for t in (m.get("tin") or []))[:6000]
    except Exception:                                    # noqa: BLE001
        return ""


def tin_kich_ban(pid):
    """Mọi tin trong kịch bản của page (>30 ký tự) — thay cho "tin của shop" ở page không có token page.

    doc_offer đọc bảng giá→SL từ đây (mẫu /p, /chaohang: "BUY 1 TAKE 1 – ONLY 109 SAR / 2 BOTTLES").
    chot_sku_bang_luat tự ghép riêng phần chào hàng (chu_kich_ban) để khớp tên SP như cũ.
    """
    try:
        v = (Q.load_json(os.path.join(Q.STATE_DIR, "kich_ban.json"), {}) or {}).get(str(pid)) or {}
        return [t for m in (v.get("mau") or []) for t in (m.get("tin") or []) if len(t or "") > 30]
    except Exception:                                    # noqa: BLE001
        return []


def chot_sku_bang_luat(ten_page, chu_post, tin_shop, catalog, pid=None):
    """Tầng 1-2 của thang tín hiệu: mã sản phẩm trong chữ, rồi khớp tên.

    Kịch bản page được ghép vào cùng bài post — nó là nguồn mạnh nhất, xem `chu_kich_ban`.
    """
    chu_kb = chu_kich_ban(pid) if pid else ""
    chu_post = (chu_post or "") + ("\n" + chu_kb if chu_kb else "")
    chu = " ".join([ten_page, chu_post] + tin_shop[:12])
    chu_norm = P.norm_ascii(chu)

    # Tầng 1: mã sản phẩm được đánh dấu trong tên page / bài post / kịch bản chào hàng
    ma_thay = _nhan_ma_sp(chu)
    if ma_thay:
        khop = [sp for sp in catalog if sp.get("ma") in ma_thay]
        if len(khop) == 1:
            return khop[0], "cao", f"mã sản phẩm {khop[0]['ma']} ghi trong nội dung page"
        if len(khop) > 1:
            return None, None, ("nội dung page ghi nhiều mã sản phẩm ("
                                + ", ".join(sp["ma"] for sp in khop) + ") — không dám chọn")

    # Tầng 2: KHỚP NGUYÊN TÊN SẢN PHẨM, không khớp từ lẻ.
    #
    # ⚠️ SIẾT 2026-09-09 sau khi chủ shop bắt lỗi. Bản cũ chấm điểm theo SỐ TỪ TRÙNG
    # (3 điểm mỗi từ), nên chỉ cần hai từ chung là đủ 6 điểm để chốt. Hậu quả thật:
    #   BodyFirm Essentials UAE  -> gán nhầm "162 - Kreain Soothing Massage Gel"
    #   Comfort Joint UAE        -> gán nhầm "165 - Synovial Meniscus Cream"
    # mà hai page đó CHƯA CÓ SẢN PHẨM, chỉ đang chạy thử. Gán nhầm SKU là đơn ra sai hàng.
    #
    # Cách đúng, chủ shop chỉ ra: bài chào hàng luôn gọi ĐÚNG TÊN sản phẩm —
    #   "Thank you for your interest in our Varicose Vein Relief Cream"
    #   kho có "227 - Varicose Vein Relief Cream"
    # Nên chỉ nhận khi TOÀN BỘ tên sản phẩm nằm gọn trong chữ. Trùng vài từ rời KHÔNG tính.
    # Thà bỏ sót để sale chọn tay, còn hơn gán nhầm rồi giao sai hàng.
    khop = []
    for sp in catalog:
        ten_sp = P.norm_ascii(re.sub(r"^\s*\d+\s*[-–—.]", "", sp["ten"])).strip()
        if len(ten_sp) >= 8 and ten_sp in chu_norm:
            khop.append((len(ten_sp), sp))       # tên dài hơn = cụ thể hơn, ưu tiên
    if khop:
        khop.sort(key=lambda x: -x[0])
        if len(khop) == 1 or khop[0][0] > khop[1][0]:
            return khop[0][1], "cao", ("kịch bản gọi đúng tên sản phẩm" if chu_kb
                                       else "bài post gọi đúng tên sản phẩm")
        return None, None, ("nội dung page gọi tên nhiều sản phẩm ("
                            + ", ".join(sp["ten"][:26] for _, sp in khop[:3]) + ") — không dám chọn")
    return None, None, None


def chot_sku_bang_ai(ten_page, chu_post, tin_shop, catalog):
    """Tầng 3: hỏi Claude Haiku 1 lần cho page này, kết quả cache vĩnh viễn.

    Trả None nếu chưa cài SDK / chưa có ANTHROPIC_API_KEY / gọi lỗi — khi đó page
    rơi về luồng cũ (đơn vẫn tạo, treo cờ thiếu sản phẩm cho nhân viên).
    """
    try:
        import anthropic
    except ImportError:
        A.log(f"  ⚠ Chưa cài SDK — cài riêng cho tool, không đụng python hệ thống: "
              f"pip3 install --break-system-packages --target={_THU_VIEN} anthropic "
              f"— lượt này bỏ qua bước chốt SKU bằng AI")
        return None, None, None
    if not (os.environ.get("ANTHROPIC_API_KEY") or P.ENV.get("ANTHROPIC_API_KEY")):
        A.log("  ⚠ Chưa có ANTHROPIC_API_KEY trong .env — bỏ qua bước chốt SKU bằng AI")
        return None, None, None

    danh_sach = "\n".join(f"{i}. {sp['ten']}" for i, sp in enumerate(catalog))
    mo_ta = (f"TÊN PAGE: {ten_page}\n\n"
             f"BÀI ĐĂNG QUẢNG CÁO:\n{chu_post[:2500]}\n\n"
             f"TIN NHẮN CỦA SHOP GỬI KHÁCH:\n" + "\n---\n".join(t[:400] for t in tin_shop[:6]))

    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY") or P.ENV.get("ANTHROPIC_API_KEY"))
    chung = dict(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=("Bạn phân loại page bán hàng Facebook. Mỗi page chỉ bán ĐÚNG MỘT sản phẩm. "
                "Dựa vào tên page, bài quảng cáo và tin nhắn của shop, chọn sản phẩm khớp "
                "trong danh sách kho. Nếu không đủ căn cứ thì trả chi_so = -1, đừng đoán bừa."),
        messages=[{"role": "user", "content":
                   f"DANH SÁCH SẢN PHẨM TRONG KHO:\n{danh_sach}\n\n{mo_ta}"}],
    )
    khuon = {"type": "object",
             "properties": {
                 "chi_so": {"type": "integer",
                            "description": "Số thứ tự sản phẩm trong danh sách, -1 nếu không rõ"},
                 "chac_chan": {"type": "boolean", "description": "true nếu bằng chứng rõ ràng"},
                 "ly_do": {"type": "string", "description": "Một câu tiếng Việt"}},
             "required": ["chi_so", "chac_chan", "ly_do"],
             "additionalProperties": False}
    try:
        r = client.messages.create(
            output_config={"format": {"type": "json_schema", "schema": khuon}}, **chung)
    except Exception as e:  # noqa: BLE001 — SDK cũ chưa có output_config -> hỏi lại kiểu thường
        A.log(f"  ⚠ Không dùng được structured output ({e}) — hỏi lại kiểu thường")
        chung["messages"][0]["content"] += (
            '\n\nTrả về DUY NHẤT một JSON: '
            '{"chi_so": <số thứ tự, -1 nếu không rõ>, "chac_chan": true|false, "ly_do": "..."}')
        try:
            r = client.messages.create(**chung)
        except Exception as e2:  # noqa: BLE001 — AI lỗi thì rơi về luồng cũ, không chặn kết nạp
            A.log(f"  ⚠ Lỗi gọi AI chốt SKU: {e2}")
            return None, None, None

    try:
        chu = next(b.text for b in r.content if b.type == "text")
        kq = json.loads(re.search(r"\{.*\}", chu, re.S).group(0))
    except (StopIteration, AttributeError, ValueError) as e:
        A.log(f"  ⚠ AI trả về không đọc được: {e}")
        return None, None, None

    i = kq.get("chi_so", -1)
    if not isinstance(i, int) or not 0 <= i < len(catalog):
        return None, None, kq.get("ly_do")
    return catalog[i], ("cao" if kq.get("chac_chan") else "thap"), f"AI: {kq.get('ly_do')}"


def chot_sku(ten_page, chu_post, tin_shop, catalog, pid=None):
    sp, do_tin, ly_do = chot_sku_bang_luat(ten_page, chu_post, tin_shop, catalog, pid)
    if sp:
        return sp, do_tin, ly_do
    return chot_sku_bang_ai(ten_page, chu_post, tin_shop, catalog)


# ---------------- 5. Vòng kết nạp ----------------

def _dong_bo_thi_truong():
    """Bản auto_len_don mà module này nhập có thể KHÁC bản __main__ của daemon (xem đầu va_ket_nap_dong_bo.py):
    MK của nó kẹt ở nước khác (hoặc None khi chạy tay). Q.STATE_DIR dùng chung nên luôn đúng nước đang chạy →
    đồng bộ theo nó trước khi đọc catalog / tiền tệ / file hồ sơ."""
    tt = os.path.basename(os.path.normpath(getattr(Q, "STATE_DIR", "") or ""))
    if tt in (getattr(A, "MARKETS", None) or {}) and (not A.MK or A.MK.get("key") != tt):
        A.set_market(tt)


def ket_nap(dry=False, so_page=MAX_PAGE_MOI):
    """Chạy 1 lượt kết nạp cho THỊ TRƯỜNG HIỆN TẠI (đã A.set_market)."""
    _dong_bo_thi_truong()        # 20/09: daemon từng học Saudi bằng catalog + file hồ sơ của Bulgaria
    trong = {"page_moi": 0, "het_goi": [], "thieu_tag": 0, "chot_duoc": 0, "chua_chot": 0}
    # Chạy tay đúng lúc daemon đang kết nạp thì 2 tiến trình cùng gọi
    # generate_page_access_token cho 1 page -> lần sau vô hiệu token lần trước, lưu
    # sai thứ tự là page chết token. Dùng chung khóa với vòng quét hội thoại.
    if not dry and not Q.acquire_lock():
        A.log("Kết nạp: đang có phiên khác chạy — bỏ lượt này")
        return trong
    try:
        return _ket_nap(dry, so_page)
    finally:
        if not dry:
            Q.release_lock()


def _con_nghi(muc):
    """Page chốt hụt lần trước và còn trong hạn nghỉ -> lượt này đừng đọc lại.

    Muốn ép hỏi lại ngay (vd vừa cài xong SDK anthropic để bật tầng AI) thì xoá mục
    'chua_chot' tương ứng trong state/<thị trường>/page_ho_so.json.
    """
    if (muc or {}).get("khoa"):
        return True       # chủ shop KHOÁ TAY (BANG_KB_2409 — 24/09 gỡ mã 200 khỏi Luxentra Gold Jewelry Bahrain): không tự học lại
    return (bool(muc) and muc.get("nguon") == "chua_chot"
            and time.time() - (muc.get("cap_nhat") or 0) < NGHI_CHUA_CHOT)


def _ket_nap(dry, so_page):
    them, het_goi, thieu_tag = phat_hien_page_moi(dry)

    tokens = Q.load_json(Q.TOKENS_FILE, {})
    hoc = Q.load_json(_f("page_products.json"), {})    # bảng học từ đơn THẬT
    ho_so = Q.load_json(_f("page_ho_so.json"), {})

    chua = [(pid, st) for pid, st in tokens.items()
            if st.get("token") and not st.get("bo_qua")
            and pid not in hoc and not (ho_so.get(pid) or {}).get("variation_id")]
    # 19/09 tối (chủ shop: "sản phẩm đã có từ chào hàng rồi mà"): page chạy bằng TÀI KHOẢN Pancake không có
    # token page nên bản cũ không bao giờ xét (MIUCO Empress Feminine in Saudi → đơn #75519 thiếu SKU + giá).
    # Kịch bản chào hàng (kich_ban.json, AI Sale đã kéo sẵn) gọi đúng tên SP + bảng giá — học từ đó.
    # Page không thuộc shop này (kich_ban.json có cả page nước khác) bị bộ lọc cua_shop ngay dưới loại.
    _co_ = {pid for pid, _ in chua}
    for pid, v in (Q.load_json(os.path.join(Q.STATE_DIR, "kich_ban.json"), {}) or {}).items():
        st_ = tokens.get(pid) or {}
        if (pid in _co_ or st_.get("token") or st_.get("bo_qua") or pid in hoc
                or (ho_so.get(pid) or {}).get("variation_id") or not (v or {}).get("mau")):
            continue
        chua.append((pid, {"name": (v or {}).get("ten_page") or st_.get("name") or pid, "token": None,
                           "kenh_tai_khoan": True}))
    # CHỈ giữ page THỰC SỰ thuộc shop của thị trường này. page_tokens.json còn sót page
    # của shop khác — setup lần đầu chạy khi chưa có bộ lọc theo shop, mà phát hiện page
    # mới chỉ THÊM chứ không bao giờ dọn. Hậu quả: đem page của shop này so với danh mục
    # sản phẩm của shop kia thì không đời nào chốt được SKU. Đo trên log server
    # 2026-08-22: lượt gắn nhãn [UAE] đang đọc 'Golden Noor KSA', 'Timeless Skin Saudi'
    # (hỏi POS: thuộc shop SAUDI), lượt [SAUDI] đọc 'Jode Jewelry Kuwait' (shop KUWAIT).
    # Không lấy được danh sách page thì THÔI lọc — đừng để lỗi mạng chặn cả lượt.
    try:
        cua_shop = {str(p.get("id")) for p in Q.get_pages()}
    except (SystemExit, Exception):    # noqa: BLE001
        cua_shop = set()
    if cua_shop:
        lac = [pid for pid, _ in chua if pid not in cua_shop]
        if lac:
            A.log(f"Kết nạp: bỏ qua {len(lac)} page KHÔNG thuộc shop {A.MK['ten']} "
                  f"(còn sót trong page_tokens.json từ đợt setup cũ)")
        chua = [(pid, st) for pid, st in chua if pid in cua_shop]
    can_chot = [(pid, st) for pid, st in chua if not _con_nghi(ho_so.get(pid))]
    nghi = len(chua) - len(can_chot)
    if nghi:
        A.log(f"Kết nạp: {nghi} page chốt hụt lần trước, nghỉ "
              f"{NGHI_CHUA_CHOT // 3600}h rồi hỏi lại — lượt này bỏ qua")
    if not can_chot:
        if them or het_goi:
            A.log(f"Kết nạp: +{them} page mới, {len(het_goi)} page hết gói cước")
        return {"page_moi": them, "het_goi": het_goi, "thieu_tag": thieu_tag,
                "chot_duoc": 0, "chua_chot": 0}

    catalog = tai_catalog()
    if not catalog:
        A.log("⚠ Không tải được catalog sản phẩm — bỏ lượt kết nạp")
        return {"page_moi": them, "het_goi": het_goi, "thieu_tag": thieu_tag,
                "chot_duoc": 0, "chua_chot": len(can_chot)}

    chot_duoc = chua_chot = 0
    # 20/09: page chạy bằng tài khoản chỉ đọc kịch bản trong máy (0 lệnh API) → không tính vào trần so_page
    for pid, st in ([x for x in can_chot if x[1].get("kenh_tai_khoan")]
                    + [x for x in can_chot if not x[1].get("kenh_tai_khoan")][:so_page]):
        ten_page = st.get("name", pid)
        try:
            if st.get("kenh_tai_khoan"):
                chu_post, tin_shop, loi = "", tin_kich_ban(pid), None
            else:
                chu_post, tin_shop, loi = doc_noi_dung(pid, st["token"])
        except (SystemExit, Exception) as e:  # noqa: BLE001 — 1 page lỗi không giết cả lượt
            A.log(f"  ✖ Lỗi đọc page {ten_page}: {e}")
            continue
        if loi:
            # Token chết -> đọc được 0 chữ. Ghi "chưa chốt được sản phẩm" là chẩn đoán SAI,
            # lại còn bắt page nghỉ mấy tiếng mới hỏi lại. Báo lỗi thật rồi để lượt sau.
            A.log(f"  ✖ {ten_page}: {loi} — bỏ qua lượt này")
            continue

        sp, do_tin, ly_do = chot_sku(ten_page, chu_post, tin_shop, catalog, pid)
        gia_qty = doc_offer(tin_shop)

        if not sp:
            chua_chot += 1
            ho_so[pid] = {"ten_page": ten_page, "gia_qty": gia_qty, "nguon": "chua_chot",
                          "ly_do": ly_do or "không đủ căn cứ trong post/tin nhắn",
                          "cap_nhat": int(time.time())}
            A.log(f"  ? {ten_page}: chưa chốt được sản phẩm ({ho_so[pid]['ly_do']})")
        else:
            mau_ma = sp["variations"]
            muc = {"ten_page": ten_page,
                   "variation_id": mau_ma[0]["id"],
                   "ten": sp["ten"],
                   "product_id": sp["product_id"],
                   "gia_qty": gia_qty,
                   "co_hop": bool(A.MK.get("hop_id")) and A.la_trang_suc(sp["ten"]),
                   "nguon": "ho_so", "do_tin": do_tin, "ly_do": ly_do,
                   "cap_nhat": int(time.time())}
            if len(mau_ma) > 1:
                muc["mau_ma"] = mau_ma          # extract() sẽ bắt khách chọn đúng mẫu
            ho_so[pid] = muc
            chot_duoc += 1
            A.log(f"  ✔ {ten_page} -> {sp['ten']} ({do_tin}, {ly_do}) | giá->SL: "
                  f"{gia_qty or 'chưa đọc được offer'}")

        if not dry:
            Q.save_json(_f("page_ho_so.json"), ho_so)
        time.sleep(0.2)

    A.log(f"Kết nạp: +{them} page mới | chốt SKU {chot_duoc} page | chưa chốt {chua_chot} | "
          f"thiếu tag {thieu_tag} | hết gói cước {len(het_goi)}")
    return {"page_moi": them, "het_goi": het_goi, "thieu_tag": thieu_tag,
            "chot_duoc": chot_duoc, "chua_chot": chua_chot}


def ho_so_page():
    """Hồ sơ suy luận, khuôn giống page_products.json để auto_len_don dùng thẳng."""
    return {pid: v for pid, v in Q.load_json(_f("page_ho_so.json"), {}).items()
            if v.get("variation_id")}


# ---------------- Lệnh ----------------

def cmd_ho_so(mkey):
    A.set_market(mkey)
    ho_so = Q.load_json(_f("page_ho_so.json"), {})
    hoc = Q.load_json(_f("page_products.json"), {})
    print(f"\n📋 {A.MK['ten']} — hồ sơ page suy luận: {len(ho_so)} "
          f"(bảng học từ đơn thật: {len(hoc)} page)")
    for pid, v in sorted(ho_so.items(), key=lambda kv: str(kv[1].get("ten_page"))):
        if v.get("variation_id"):
            print(f"  ✔ {str(v.get('ten_page'))[:38]:<38} -> {str(v.get('ten'))[:34]:<34} "
                  f"[{v.get('do_tin')}] giá->SL {v.get('gia_qty') or '{}'}")
        else:
            print(f"  ? {str(v.get('ten_page'))[:38]:<38} -- {v.get('ly_do')}")


def cmd_bao_cao(mkeys=None):
    print(f"\n📊 BÁO CÁO KẾT NẠP PAGE — {time.strftime('%Y-%m-%d %H:%M')}")
    for mkey in (mkeys or A.enabled_markets()):
        try:
            A.set_market(mkey)
        except SystemExit as e:
            print(f"  {mkey}: {e}")
            continue
        tokens = Q.load_json(Q.TOKENS_FILE, {})
        hoc = Q.load_json(_f("page_products.json"), {})
        ho_so = Q.load_json(_f("page_ho_so.json"), {})
        # Page hết gói cước KHÔNG tính vào báo cáo (user đã chốt: bỏ, không chạy tự động)
        song = {p: s for p, s in tokens.items() if s.get("token") and not s.get("bo_qua")}
        # Page token hỏng KHÔNG chạy được: API vẫn trả HTTP 200 nên vòng quét đọc thành
        # "không có hội thoại gắn tag" — đếm vào 'chạy được' là báo cáo sai sự thật.
        hong = [s.get("name") for p, s in song.items() if s.get("token_hong")]
        song = {p: s for p, s in song.items() if not s.get("token_hong")}
        thieu_tag = [s.get("name") for p, s in song.items() if not Q.tag_ids_of(s)]
        chua_sku = [s.get("name") for p, s in song.items()
                    if p not in hoc and not (ho_so.get(p) or {}).get("variation_id")]
        print(f"\n  {A.MK['ten']}: {len(song)} page chạy được "
              f"({len(hoc)} có đơn thật, {len(ho_so_page())} chốt bằng hồ sơ)")
        if hong:
            print(f"    ⚠ {len(hong)} page TOKEN HỎNG — sale gắn tag {Q.TAG_NAME!r} ở đó KHÔNG "
                  f"lên đơn: {', '.join(t or '?' for t in hong[:5])}"
                  + (" ..." if len(hong) > 5 else ""))
            print(f"      → python3 auto_len_don.py setup {mkey} --force-token --hong")
        if thieu_tag:
            print(f"    ⚠ {len(thieu_tag)} page CHƯA CÓ tag {Q.TAG_NAME!r} — đồng bộ thiết lập "
                  f"trong Pancake: {', '.join(t or '?' for t in thieu_tag[:5])}"
                  + (" ..." if len(thieu_tag) > 5 else ""))
        if chua_sku:
            print(f"    ⚠ {len(chua_sku)} page chưa chốt được sản phẩm: "
                  f"{', '.join(t or '?' for t in chua_sku[:5])}"
                  + (" ..." if len(chua_sku) > 5 else ""))
        if not hong and not thieu_tag and not chua_sku:
            print("    ✔ Không có gì cần làm tay")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1].lower(), sys.argv[2:]
    mkeys = [a for a in args if not a.startswith("--") and not a.isdigit()]
    if cmd == "ket-nap":
        if not mkeys:
            raise SystemExit("Dùng: ket-nap <thị trường> [--thu]")
        so = int(args[args.index("--sl") + 1]) if "--sl" in args else MAX_PAGE_MOI
        A.set_market(mkeys[0])
        ket_nap(dry="--thu" in args, so_page=so)
    elif cmd == "ho-so":
        if not mkeys:
            raise SystemExit("Dùng: ho-so <thị trường>")
        cmd_ho_so(mkeys[0])
    elif cmd == "bao-cao":
        cmd_bao_cao(mkeys or None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

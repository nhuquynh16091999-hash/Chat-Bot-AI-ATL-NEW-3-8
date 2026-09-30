"""CHỌN ẢNH "CÁC MẪU BÊN MÌNH ĐANG CÓ" cho từng page, từ kết quả phân loại (chỉ đọc, không gửi gì).

Kiểu hàng CHÍNH của page lấy từ chính page (không lấy số đông bộ sưu tập — bộ sưu tập lẫn hàng page khác, vd
Mint Breeze UAE đa số là ảnh vòng tay): (1) số đông kiểu của ẢNH SẢN PHẨM TRONG KỊCH BẢN; (2) không có thì dò chữ
tên sản phẩm POS + câu chào kịch bản. Chỉ bật cho hàng trang sức / phụ kiện (khách xin "mẫu khác" gần như chỉ ở
đây); page mỹ phẩm, trà, răng… giữ cách cũ.
Dùng: python3 chon_mau.py <file phân loại.json> <tt> [--page=pid,pid] [--ra=state/<tt>/mau_khac.json]
Kết quả: {pid: {"kieu", "bat", "anh": [≤8 url], "dh": {url: dHash}, …}} — ai_sale.anh_bo_suu_tap_cho_khach đọc.
"""
import collections
import json
import re
import sys

sys.path.insert(0, "/opt/pancake-tool")
import ai_sale as a  # noqa: E402

KQ = json.load(open(sys.argv[1], encoding="utf-8"))
TT = sys.argv[2]
CHI_PAGE = next((x.split("=", 1)[1].split(",") for x in sys.argv if x.startswith("--page=")), None)
RA = next((x.split("=", 1)[1] for x in sys.argv if x.startswith("--ra=")), None)
TOI_DA = 8                                   # lưu 8, lúc chạy gửi 4 ảnh khách CHƯA xem

KIEU_PHU_KIEN = {"jewelry_set", "necklace", "earrings", "ring", "bracelet", "anklet", "chain", "watch", "wallet",
                 "bag", "glasses", "statue"}
# Dò chữ khi kịch bản không có ảnh sản phẩm (ca Mario: 2 ảnh kịch bản là giấy chứng nhận + móc khoá).
TU_KHOA = [
    (r"\b(?:jewel(?:ry|lery)?\s+sets?|sets?\b.{0,40}(?:necklace|earring|ring)|(?:necklace|earrings?)\s*(?:&|and|\+)"
     r"\s*(?:earrings?|necklace|ring))", "jewelry_set"),
    (r"\b(?:bracelets?|bangles?)\b|سوار|اسورة|أسورة", "bracelet"),
    (r"\b(?:necklaces?|pendants?)\b|قلادة|سلسال", "necklace"),
    (r"\bearrings?\b|حلق", "earrings"),
    (r"\brings?\b|خاتم", "ring"),
    (r"\banklets?\b", "anklet"),
    (r"\bwatch(?:es)?\b|ساعة", "watch"),
    (r"\bwallets?\b|محفظة", "wallet"),
    (r"\b(?:glasses|eyewear|eyeglasses)\b|نظارة", "glasses"),
    (r"\b(?:statue|figurine)\b|تمثال", "statue"),
]


NHOM = {"jewelry_set": {"jewelry_set", "necklace", "earrings", "ring"}, "necklace": {"necklace", "jewelry_set", "chain"},
        "earrings": {"earrings", "jewelry_set"}, "ring": {"ring", "jewelry_set"}, "bracelet": {"bracelet", "chain", "anklet"},
        "chain": {"chain", "necklace", "bracelet"}, "anklet": {"anklet", "bracelet"}, "watch": {"watch"},
        "wallet": {"wallet", "bag"}, "bag": {"bag", "wallet"}, "glasses": {"glasses"}, "statue": {"statue"}}
DICH = {"jewelry_set": "a matching jewelry SET: two or more pieces of the same design shown together (e.g. necklace "
                       "with earrings, with or without a ring)",
        "necklace": "a necklace or pendant necklace", "earrings": "a pair of earrings", "ring": "a ring",
        "bracelet": "a bracelet or bangle (beaded, string, charm or metal)",
        "chain": "a plain gold chain (necklace chain or bracelet chain)", "anklet": "an anklet",
        "watch": "a wristwatch", "wallet": "a wallet", "bag": "a handbag or bag",
        "glasses": "eyeglasses or sunglasses", "statue": "a statue or figurine"}
KIEM2 = ("Answer with JSON only, no other text: {{\"dung\": true|false, \"man_hinh\": true|false, "
         "\"giay_to\": true|false}}.\n"
         "dung = the MAIN subject of this photo is {muc}, photographed as a product a shop would show a customer "
         "(on a surface, in a box, in a hand or worn by a model).\n"
         "man_hinh = the photo is a screenshot of a phone or computer screen, a chat, an app or a social media post.\n"
         "giay_to = a certificate, card or document is one of the main elements of the photo.")
F_KIEM2 = sys.argv[1].replace(".json", "") + "_kiem2.json"
try:
    K2 = json.load(open(F_KIEM2, encoding="utf-8"))
except Exception:                                      # noqa: BLE001
    K2 = {}


def kiem2(u, k):
    """Hỏi lại 1 câu hẹp cho ảnh ứng viên. Nhớ theo (url, kiểu)."""
    import time, urllib.request
    khoa = u + "|" + k
    if khoa in K2:
        return K2[khoa]
    nha, key, api, model, _dem = a.nha_cung_cap()
    b64 = a._anh_nen(u)
    than = {"model": model, "max_tokens": 80, "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": KIEM2.format(muc=DICH[k])}]}]}
    dau = {"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(api, data=json.dumps(than).encode(), method="POST",
                                                       headers=dau), timeout=40) as r:
        res = json.loads(r.read().decode())
    a._ghi_so_doc_anh(nha, model, res.get("usage") or {}, round(time.time() - t0, 1))
    txt = " ".join(c.get("text", "") for c in (res.get("content") or []) if c.get("type") == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    d = json.loads(m.group(0)) if m else {}
    K2[khoa] = {"dung": bool(d.get("dung")), "man_hinh": bool(d.get("man_hinh")), "giay_to": bool(d.get("giay_to"))}
    return K2[khoa]


# Chữ XÁC NHẬN loại hàng (tên SP POS + câu chào kịch bản phải có ít nhất một chữ của đúng nhóm) — ảnh kịch bản có
# khi lạc sang hàng page khác: page trà "Cloves Tea with Alingatong Roots UAE" có đúng 1 ảnh bộ trang sức trong kịch
# bản → bị nhận là page trang sức, 8 ảnh vòng cổ suýt được gửi cho khách hỏi trà; "Feng Shui keychain US" (móc khoá)
# bị nhận là dây chuyền. Không dùng chữ "set" trơn: page nào cũng có "Buy 2 sets".
CHU_XAC_NHAN = {
    "jewelry_set": r"necklace|earring|jewel|kwintas|hikaw|طقم|قلادة|حلق|اقراط|أقراط|مجوهرات",
    "necklace": r"necklace|pendant|\bchains?\b|kwintas|rosary|قلادة|سلسال|سلسلة|مسبحة",   # "keychain" không tính
    "chain": r"\bchains?\b|necklace|bracelet|kwintas|سلسلة|سلسال",
    "earrings": r"earring|hikaw|حلق|اقراط|أقراط",
    "ring": r"\bring|singsing|خاتم",
    "bracelet": r"bracelet|bangle|pulseras?|\bcharm|\bbeads?\b|gelang|سوار|اسورة|أسورة|خرز",
    "anklet": r"anklet|خلخال",
    "watch": r"\bwatch|relo|ساعة",
    "wallet": r"wallet|pitaka|محفظة",
    "bag": r"\bbags?\b|bolsa|حقيبة|شنطة",
    "glasses": r"glasses|eyewear|salamin|نظارة",
    "statue": r"statue|figurine|buddha|rebulto|تمثال",
}


def chu_cua_page(pid, kb):
    try:
        pp = json.load(open(f"/opt/pancake-tool/state/{TT}/page_products.json", encoding="utf-8")).get(pid) or {}
    except Exception:                                  # noqa: BLE001
        pp = {}
    mau = kb.get("mau") or []
    chao = next((m for m in mau if (m.get("tu_khoa") or "").lower() == "chaohang"), mau[0] if mau else {})
    return (pp.get("ten") or "") + " | " + (kb.get("ten_page") or "") + " | " + ((chao.get("tin") or [""])[0] or "")[:600]


def kieu_chinh(pid, kb):
    """Kiểu hàng chính: ≥2 ảnh sản phẩm trong kịch bản cùng kiểu thì tin ảnh; chỉ 1 ảnh thì phải có chữ xác nhận
    (ca Cloves Tea: đúng 1 ảnh bộ trang sức lạc vào kịch bản page trà); không có ảnh thì dò chữ (TU_KHOA)."""
    k, nguon, n_anh = _kieu_chinh_tho(pid, kb)
    if n_anh == 1 and k in CHU_XAC_NHAN and not re.search(CHU_XAC_NHAN[k], chu_cua_page(pid, kb), re.I | re.U):
        return None, f"chỉ 1 ảnh kịch bản nói '{k}' mà chữ kịch bản/POS không có"
    return k, nguon


def _kieu_chinh_tho(pid, kb):
    kb_urls = [u for m in (kb.get("mau") or []) for u in (m.get("anh") or []) if isinstance(u, str)]
    dem = collections.Counter(KQ[u]["kieu"] for u in kb_urls
                              if u in KQ and KQ[u]["loai"] == "san_pham" and KQ[u]["kieu"] not in ("packaging", "other"))
    if dem:
        k0, n0 = dem.most_common(1)[0]
        return k0, "ảnh kịch bản " + str(dict(dem)), n0
    chu = chu_cua_page(pid, kb)
    for mau_re, k in TU_KHOA:
        if re.search(mau_re, chu, re.I | re.U):
            return k, "chữ: " + chu[:90].replace("\n", " "), 0
    return None, "không rõ: " + chu[:90].replace("\n", " "), 0


# Ảnh mà chủ thể là NGƯỜI (ảnh ghép nhiều khách đeo vòng, selfie nhóm) — mô tả bước 1 nói rõ, lọc bằng chữ.
# "woman / model wearing …" thì GIỮ: đó là ảnh sản phẩm đeo trên người mẫu.
_NGUOI = re.compile(r"\bpeople\b|\bgroup\b|\bcustomers?\b|\bselfies?\b|\bcrowd\b|\bfamily\b", re.I)


def ham(x, y):
    return bin(int(x, 16) ^ int(y, 16)).count("1")


tm = json.load(open(f"/opt/pancake-tool/state/{TT}/thu_muc_anh.json", encoding="utf-8"))
# Kiểm lần 2 SONG SONG cho mọi ứng viên trước (mỗi ảnh ~1 giây, tuần tự thì cả nước mất cả chục phút).
_ung_vien = []
for pid, v in tm.items():
    if CHI_PAGE and pid not in CHI_PAGE:
        continue
    kb = a.nap_kich_ban(TT, pid)
    if not kb or not kb.get("mau"):
        continue
    k, _ng = kieu_chinh(pid, kb)
    if k not in KIEU_PHU_KIEN:
        continue
    for x in (v.get("anh") or []):
        r = KQ.get(x["u"])
        if r and r["loai"] == "san_pham" and r["kieu"] in NHOM[k] and not r["chu_de"] and x["u"] + "|" + k not in K2:
            _ung_vien.append((x["u"], k))
if _ung_vien:
    from concurrent.futures import ThreadPoolExecutor

    def _k2(t):
        try:
            kiem2(*t)
        except Exception as e:                          # noqa: BLE001
            print("   ✖ kiểm lần 2 hỏng", str(e)[:80])
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(_k2, list(dict.fromkeys(_ung_vien))))
    print(f"  (kiểm lần 2: {len(_ung_vien)} ảnh mới)")
ra = {}
for pid, v in tm.items():
    if CHI_PAGE and pid not in CHI_PAGE:
        continue
    kb = a.nap_kich_ban(TT, pid)
    if not kb or not kb.get("mau"):
        continue
    k, nguon = kieu_chinh(pid, kb)
    chon = []
    bo_k2 = []
    if k in KIEU_PHU_KIEN:
        for x in (v.get("anh") or []):
            r = KQ.get(x["u"])
            if not (r and r["loai"] == "san_pham" and r["kieu"] in NHOM[k] and not r["chu_de"]):
                continue
            if _NGUOI.search(r.get("mo_ta") or ""):
                continue                                # ảnh ghép khách đeo hàng (Madam Jane UAE) = feedback
            if not all(ham(r["dh"], KQ[c]["dh"]) > 6 for c in chon):
                continue
            try:
                q = kiem2(x["u"], k)
            except Exception as e:                      # noqa: BLE001
                print("   ✖ kiểm lần 2 hỏng", str(e)[:80])
                continue
            if q["dung"] and not q["man_hinh"] and not q["giay_to"]:
                chon.append(x["u"])
            else:
                bo_k2.append(x["u"])
    ra[pid] = {"ten": v.get("ten_page"), "kieu": k, "nguon": nguon, "bat": k in KIEU_PHU_KIEN,
               "anh": chon[:TOI_DA], "du": len(chon), "bo_k2": bo_k2,
               "dh": {u: KQ[u]["dh"] for u in chon[:TOI_DA]}, "luc": int(__import__("time").time())}
    print(f"{pid} {str(v.get('ten_page'))[:34]:34s} kiểu={k} ({nguon[:70]}) → {'BẬT' if k in KIEU_PHU_KIEN else 'tắt'}"
          f" · chọn {len(chon)}")
json.dump(K2, open(F_KIEM2, "w", encoding="utf-8"), ensure_ascii=False)
if RA:
    json.dump(ra, open(RA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

"""PHÂN LOẠI ẢNH BỘ SƯU TẬP (thư mục ảnh) CỦA PAGE — để AI gửi "các mẫu bên mình đang có" khi khách xin mẫu khác.

Chủ shop 21/09 (ca Lanie Antonio Jacinto · Mario Jewelry UAE): *"phần bộ sưu tập k có mẫu khác cho bạn gửi sao"*.
Bộ sưu tập LẪN LỘN (giấy tờ, ảnh chat, cửa hàng, ảnh cận, ảnh sản phẩm khác) nên phải lọc trước. Thử 21/09: model
KHÔNG phân biệt nổi "sản phẩm chính vs mẫu khác" (gọi bộ Knot là mẫu khác) — nên chỉ hỏi 3 điều nó làm được:
ảnh sản phẩm sạch không · đúng LOẠI hàng page bán không · có chữ đè không. Chủ shop chọn: gửi mọi ảnh sản phẩm sạch.

Mỗi URL hỏi 1 lần (~$0,0001), nhớ trong file ra; chạy lại chỉ hỏi ảnh mới. Kèm mã băm dHash để bỏ ảnh trùng
(cùng ảnh tải lên 2 lần = 2 URL).
Dùng: python3 phan_loai_bo_suu_tap.py <file ra.json> <tt> [tt …] [--page=<pid>,<pid>] [--luong=3]
"""
import base64
import io
import json
import os
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/opt/pancake-tool")
import ai_sale as a  # noqa: E402
from PIL import Image  # noqa: E402

RA = sys.argv[1]
TTS = [x for x in sys.argv[2:] if not x.startswith("--")]
CHI_PAGE = next((x.split("=", 1)[1].split(",") for x in sys.argv if x.startswith("--page=")), None)
LUONG = int(next((x.split("=", 1)[1] for x in sys.argv if x.startswith("--luong=")), "3"))

KIEU = ("jewelry_set", "necklace", "earrings", "ring", "bracelet", "anklet", "chain", "watch", "statue", "wallet",
        "bag", "bottle", "jar", "tube", "box_pack", "denture", "glasses", "clothing", "device", "packaging", "other")
NHAC = (
    "You are sorting the photo library of an online shop (its sales script starts: \"{sp}\").\n"
    "Look at the photo and answer with JSON only, no other text:\n"
    "{{\"loai\": \"san_pham\" | \"giay_to\" | \"feedback\" | \"cua_hang\" | \"can_chi_tiet\" | \"khac\", "
    "\"kieu\": one of " + " | ".join('"%s"' % k for k in KIEU) + ", "
    "\"chu_de\": true | false, \"mo_ta\": \"<max 12 words>\"}}\n"
    "loai: san_pham = a clear photo of a product itself (on a surface, in a box, in a hand, or worn by a model) that "
    "a seller could show a customer; giay_to = certificate, document, lab report, receipt, invoice (also a product "
    "photographed together with a certificate); feedback = chat or app screenshot, customer review card, star "
    "ratings, a customer's own photo or selfie, parcel or delivery proof; cua_hang = store interior or exterior; "
    "can_chi_tiet = extreme close-up of a clasp, stamp, label or small detail where the whole item is not visible; "
    "khac = anything else (banner, price list, collage with text, poster, people without the product).\n"
    "kieu: the type of the MAIN item shown. jewelry_set = two or more matching jewelry pieces shown together "
    "(e.g. necklace with earrings, with or without a ring); necklace = a necklace or pendant alone; chain = a plain "
    "chain without pendant; bracelet = any bracelet or bangle (beaded, string, charm); statue = figurine or "
    "ornament; bottle = serum, oil or liquid bottle; jar = cream jar or tub; box_pack = product in a retail box or "
    "pack; packaging = an empty box, pouch or bag without the product.\n"
    "chu_de: true if prominent text is printed over the photo (a price, promo banner, caption, month name, big "
    "label, review text); a small corner watermark or logo does not count.")

_KHOA = threading.Lock()
try:
    KQ = json.load(open(RA, encoding="utf-8"))
except Exception:                                      # noqa: BLE001
    KQ = {}


def _luu():
    with _KHOA:
        tam = RA + ".tam"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(KQ, f, ensure_ascii=False)
        os.replace(tam, RA)


def _dhash(b64):
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("L").resize((9, 8))
    px = list(im.getdata())
    bits = "".join("1" if px[r * 9 + c] > px[r * 9 + c + 1] else "0" for r in range(8) for c in range(8))
    return "%016x" % int(bits, 2)


def _tom_tat_sp(kb):
    mau = kb.get("mau") or []
    chao = next((m for m in mau if (m.get("tu_khoa") or "").lower() in ("chaohang", "chao", "gioithieu")), None)
    chao = chao or (mau[0] if mau else {})
    t = " ".join(((chao.get("tin") or [""])[0] or "").split())
    return re.sub(r"#\{[A-Z_]+\}", "", t)[:300] or (kb.get("ten_page") or "")


def _hoi(url, sp):
    nha, key, api, model, _dem = a.nha_cung_cap()
    b64 = a._anh_nen(url)
    than = {"model": model, "max_tokens": 200,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": NHAC.format(sp=sp.replace('"', "'"))}]}]}
    if nha in ("kimi", "deepseek"):
        than["thinking"] = {"type": "disabled"}
    dau = {"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(api, data=json.dumps(than).encode(), method="POST",
                                                       headers=dau), timeout=40) as r:
        res = json.loads(r.read().decode())
    a._ghi_so_doc_anh(nha, model, res.get("usage") or {}, round(time.time() - t0, 1))
    txt = " ".join(c.get("text", "") for c in (res.get("content") or []) if c.get("type") == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    d = json.loads(m.group(0)) if m else {}
    return {"loai": str(d.get("loai") or "?"), "kieu": str(d.get("kieu") or "other"),
            "chu_de": bool(d.get("chu_de")), "mo_ta": str(d.get("mo_ta") or "")[:120], "dh": _dhash(b64)}


viec = []                                               # (url, pid, tt, sp)
for tt in TTS:
    tm = json.load(open(f"/opt/pancake-tool/state/{tt}/thu_muc_anh.json", encoding="utf-8"))
    for pid, v in tm.items():
        if CHI_PAGE and pid not in CHI_PAGE:
            continue
        kb = a.nap_kich_ban(tt, pid)
        if not kb or not kb.get("mau"):
            continue
        sp = _tom_tat_sp(kb)
        urls = [x["u"] for x in (v.get("anh") or [])]
        for m in kb["mau"]:                              # ảnh kịch bản cũng phân loại: biết mẫu nào là ảnh sp thật
            urls += [u for u in (m.get("anh") or []) if isinstance(u, str)]
        for u in dict.fromkeys(urls):
            if re.search(r"\.(mp3|mp4|m4a|wav|ogg|mov|pdf|webm)(\?|$)", u, re.I):
                continue
            if u not in KQ:
                viec.append((u, pid, tt, sp))
viec = list({v[0]: v for v in viec}.values())
print(f"cần hỏi {len(viec)} ảnh mới · đã có {len(KQ)}", flush=True)
dem = {"xong": 0, "hong": 0}


def _lam(v):
    u, pid, tt, sp = v
    try:
        r = _hoi(u, sp)
    except Exception as e:                              # noqa: BLE001
        with _KHOA:
            dem["hong"] += 1
        return f"✖ {u[-40:]} {str(e)[:80]}"
    r.update({"pid": pid, "tt": tt, "luc": int(time.time())})
    with _KHOA:
        KQ[u] = r
        dem["xong"] += 1
        n = dem["xong"]
    if n % 50 == 0:
        _luu()
        print(f"  … {n}/{len(viec)}", flush=True)
    return None


with ThreadPoolExecutor(LUONG) as ex:
    for loi in ex.map(_lam, viec):
        if loi:
            print(" ", loi, flush=True)
_luu()
print(f"xong {dem['xong']} · hỏng {dem['hong']} · tổng trong file {len(KQ)}")

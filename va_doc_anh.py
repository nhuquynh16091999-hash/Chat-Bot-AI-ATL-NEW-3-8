"""VÁ: cho AI ĐỌC ẢNH khách gửi (2026-09-20).

Đo 24h ngày 20/09 trên 261 page: 54/1.689 tin khách là ẢNH, và CẢ 54 tin không có lấy một chữ.
Tin rỗng nên mọi cổng coi là "không có gì để trả lời" → TREO. Ca JhanShylle AB (Veloura
Collection 18:07) khách gửi đúng ảnh bộ RUBY của page — tức là CHỈ MẪU MUỐN MUA — mà AI treo.

Model đang chạy đọc được ảnh: deepseek-flash qua endpoint định dạng Anthropic nhận khối
{"type": "image"}. Đo thật 4 ảnh khách: 1,0s và $0,00013 mỗi ảnh (768px, thinking TẮT).

Chạy: python3 va_doc_anh.py            (xem trước)
      python3 va_doc_anh.py --that     (ghi thật, có sao lưu)
"""
import os
import shutil
import sys
import time

F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_sale.py")

KHOI_MOI = '''

def url_anh(m):
    """URL các ẢNH khách gửi trong tin này. Bỏ sticker, voice và các "đính kèm" Pancake tự bóc.

    Đo 20/09 trên 261 page: ảnh về Pancake là attachment {'type': 'photo', 'url':
    'https://content.pancake.vn/…'}. Sticker mang type 'sticker' (đọc không ra gì, không đáng
    tiền: 57 sticker/ngày, nhiều hơn cả ảnh). Pancake còn nhét cả type 'address' (ô địa chỉ nó
    tự bóc ra từ câu khách) và 'replied_message' vào cùng danh sách attachments.
    """
    u = [x.get("url") for x in (m.get("photos") or []) if isinstance(x, dict) and x.get("url")]
    for a in (m.get("attachments") or []):
        if not isinstance(a, dict) or not a.get("url"):
            continue
        if (str(a.get("type") or "").lower() == "photo"
                or str(a.get("mime_type") or "").lower().startswith("image/")):
            u.append(a["url"])
    return u


# ───────────────────────── ĐỌC ẢNH KHÁCH GỬI (2026-09-20) ─────────────────────────
# Khách gửi ảnh thì gần như KHÔNG gõ kèm chữ: đo 24h ngày 20/09 trên 261 page — 54/1.689 tin
# khách là ảnh, CẢ 54 tin không có một chữ nào. Tin rỗng nên `vo_nghia` bật, cổng treo bật,
# AI bỏ lượt (ca JhanShylle AB · Veloura Collection 18:07: ảnh bộ RUBY của chính page = khách
# chỉ mẫu muốn mua, AI treo cho sale).
#
# Đo thật 4 ảnh khách 20/09 (deepseek-flash, 768px, thinking TẮT): 1,0s · $0,00013 mỗi ảnh —
# 54 ảnh/ngày ≈ $0,007/ngày. Đọc cả cũng không đáng kể so với tiền soạn tin.
#   · thinking BẬT thì nó đốt 500 token vào phần nghĩ rồi trả về RỖNG (3/4 ảnh) — phải tắt.
#   · Kimi cùng endpoint MÙ ảnh: vào chỉ 7-74 token, trả rỗng.
#   · ANTHROPIC_API_KEY trong .env đang chết (401).
# Nên chỉ đọc khi nhà là deepseek/anthropic; nhà khác thì bỏ qua y như trước, không báo lỗi.
ANH_CANH = 768                        # cạnh dài tối đa khi nén trước khi gửi model
ANH_MOI_LUOT = 2                      # một lượt nhiều ảnh: chỉ đọc 2 ảnh mới nhất
ANH_NHO_TOI_DA = 5000                 # sổ mô tả giữ tối đa chừng này ảnh (cũ nhất rơi trước)
ANH_NHA_DOC_DUOC = ("deepseek", "anthropic")
_NHAC_DOC_ANH = (
    "A customer sent this photo to an online shop on Messenger. Reply with ONE short English line "
    "(max 25 words) telling the shop what the photo shows. If it is a screenshot, say which app and "
    "quote the key text. If it shows a product, name it (type, colour, material). Describe ONLY what "
    "is visible - no guessing why they sent it, no advice.")
_MO_TA_ANH = {}                       # url -> mô tả (nhớ trong tiến trình)
_MO_TA_DA_NAP = []                    # rỗng = chưa nạp sổ từ đĩa
import threading as _thr_anh          # noqa: E402 — _threading ở dưới, khối này cần khoá riêng
_KHOA_MO_TA = _thr_anh.Lock()


def _f_mo_ta_anh():
    return os.path.join(SCRIPT_DIR, "state", "chung", "anh_da_doc.json")


def _nap_mo_ta():
    """Nạp sổ mô tả từ đĩa MỘT lần cho cả tiến trình (mọi thị trường dùng chung: cùng một URL
    ảnh của Pancake, đọc lại là tốn tiền lần nữa)."""
    if _MO_TA_DA_NAP:
        return
    _MO_TA_DA_NAP.append(1)
    try:
        for u, t in (qht.load_json(_f_mo_ta_anh(), {}) or {}).items():
            _MO_TA_ANH.setdefault(u, t)
    except Exception:                                    # noqa: BLE001 — sổ hỏng thì đọc lại từ đầu
        pass


def _anh_nen(url, canh=ANH_CANH):
    """Tải ảnh về, xoay đúng chiều theo EXIF, thu nhỏ còn `canh` px rồi trả base64 JPEG.

    Ảnh khách hay là ảnh chụp điện thoại 2048px: gửi nguyên là tốn token vô ích. Đo 20/09:
    768px và 512px cho mô tả ngang nhau, nhưng ảnh CHỤP MÀN HÌNH (chữ nhỏ) thì 768 chắc hơn.
    """
    import base64
    import io
    from PIL import Image, ImageOps
    raw = urllib.request.urlopen(url, timeout=20).read()
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    w, h = im.size
    if max(w, h) > canh:
        r = canh / max(w, h)
        im = im.resize((max(1, int(w * r)), max(1, int(h * r))))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    return base64.b64encode(b.getvalue()).decode()


def _ghi_so_doc_anh(nha, model, u, giay):
    """Cộng token lượt đọc ảnh vào sổ ngày + ghi một dòng goi_model.jsonl (viec="doc_anh").

    Không ghi thì tiền đọc ảnh thành khoản chênh giữa sổ và số dư thật — đúng cái bẫy đã mất
    công truy hồi 17/09.
    """
    with _KHOA_DEM_TOKEN:
        DEM_TOKEN["luot"] += 1
        DEM_TOKEN["vao"] += u.get("input_tokens") or 0
        DEM_TOKEN["ra"] += u.get("output_tokens") or 0
    (gv, _gd, _gg, gr), _khop = gia_theo_model(nha, model)
    ban = {"nha": nha, "model": model, "viec": "doc_anh",
           "vao": u.get("input_tokens") or 0, "doc_dem": 0, "ghi_dem": 0,
           "ra": u.get("output_tokens") or 0, "giay": giay}
    ban["tien"] = round((ban["vao"] * gv + ban["ra"] * gr) / 1e6, 8)
    try:
        f = os.path.join(SCRIPT_DIR, "state", "chung", "goi_model.jsonl")
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                 "t": round(time.time(), 2), **ban}, ensure_ascii=False) + "\\n")
    except Exception:                                    # noqa: BLE001 — sổ hỏng không giết vòng
        pass


def doc_mot_anh(url):
    """Mô tả MỘT ảnh bằng model (một câu tiếng Anh), hoặc None. Nhớ theo URL nên chỉ tốn lần đầu."""
    if url in _MO_TA_ANH:
        return _MO_TA_ANH[url]
    nha, key, api, model, _dem = nha_cung_cap()
    if not key or nha not in ANH_NHA_DOC_DUOC:
        return None
    try:
        b64 = _anh_nen(url)
    except Exception as e:                               # noqa: BLE001 — ảnh hỏng không giết lượt
        log(f"   ⚠️  không tải được ảnh khách: {str(e)[:100]}")
        return None
    than = {"model": model, "max_tokens": 150,
            "messages": [{"role": "user", "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": _NHAC_DOC_ANH}]}]}
    if nha in ("kimi", "deepseek"):
        than["thinking"] = {"type": "disabled"}          # bật thì đốt hết trần chữ vào phần nghĩ
    dau = {"content-type": "application/json"}
    if nha == "kimi":
        dau["Authorization"] = f"Bearer {key}"
    else:
        dau["x-api-key"] = key
        dau["anthropic-version"] = "2023-06-01"
    t0 = time.time()
    try:
        req = urllib.request.Request(api, data=json.dumps(than).encode(),
                                     method="POST", headers=dau)
        with urllib.request.urlopen(req, timeout=_so_env("AI_DOC_ANH_TIMEOUT", 25)) as r:
            res = json.loads(r.read().decode())
    except Exception as e:                               # noqa: BLE001 — đọc ảnh hỏng = quay về như cũ
        log(f"   ⚠️  đọc ảnh hỏng: {str(e)[:120]}")
        return None
    u = res.get("usage") or {}
    _ghi_so_doc_anh(nha, model, u, round(time.time() - t0, 1))
    txt = " ".join(c.get("text", "") for c in (res.get("content") or [])
                   if c.get("type") == "text").strip()
    if not txt:
        return None
    txt = " ".join(txt.split())[:220]
    _MO_TA_ANH[url] = txt
    return txt


def doc_anh_khach(msgs):
    """Gắn `mo_ta` (câu máy đọc được từ ảnh) vào các tin ẢNH khách gửi ở CUỐI hội thoại.

    Chỉ đọc ảnh nằm SAU tin cuối của page — đúng những ảnh lượt này phải xử; ảnh cũ hơn đã có
    người xử rồi, đọc lại chỉ tốn tiền. Tối đa ANH_MOI_LUOT ảnh mới nhất. Mô tả nhớ theo URL
    (state/chung/anh_da_doc.json) nên các vòng dò sau xét lại cùng hội thoại là miễn phí.
    Tắt bằng AI_DOC_ANH=0 → quay về y như trước, không cần sửa code.
    """
    if not msgs or int(_so_env("AI_DOC_ANH", 1)) != 1:
        return 0
    can = []
    for m in reversed(msgs):
        if m.get("boi") in ("botcake", "nguoi", "ai"):
            break                                        # page đã đáp sau đó → ảnh cũ, không phải việc lượt này
        if m.get("boi") == "khach" and not m.get("voice") and m.get("anh"):
            can.append(m)
    if not can:
        return 0
    _nap_mo_ta()
    xong = 0
    for m in can[:ANH_MOI_LUOT]:
        t = doc_mot_anh(m["anh"][0])
        if t:
            m["mo_ta"] = t
            xong += 1
    if xong:
        with _KHOA_MO_TA:
            try:
                d = _MO_TA_ANH
                if len(d) > ANH_NHO_TOI_DA:              # cũ nhất rơi trước (dict giữ thứ tự thêm vào)
                    d = dict(list(d.items())[-ANH_NHO_TOI_DA:])
                    _MO_TA_ANH.clear()
                    _MO_TA_ANH.update(d)
                qht.save_json(_f_mo_ta_anh(), dict(_MO_TA_ANH))
            except Exception:                            # noqa: BLE001 — sổ hỏng thì đọc lại lần sau
                pass
    return xong

'''

VA = [
    # ── 1. thêm url_anh + khối đọc ảnh, ngay trước tin_cua_hoi_thoai ────────────────
    ("""            return True
    return False


def tin_cua_hoi_thoai(page_id, conv_id, token, max_tin=60):""",
     """            return True
    return False
""" + KHOI_MOI + """
def tin_cua_hoi_thoai(page_id, conv_id, token, max_tin=60):"""),

    # ── 2. giữ URL ảnh lại trong bản ghi tin (trước nay vứt, chỉ còn cờ co_dinh_kem) ──
    ("""            "co_dinh_kem": bool(m.get("attachments")),
            "voice": la_voice(m),""",
     """            "co_dinh_kem": bool(m.get("attachments")),
            "voice": la_voice(m),
            "anh": url_anh(m),""") ,

    # ── 3. ảnh ĐÃ ĐỌC ĐƯỢC thì không còn là "không có gì để trả lời" ────────────────
    ("""    if all(vo_nghia(m["text"], m.get("co_dinh_kem")) and not (
            _tu_go and HOI_GIA.search(lam_sach(m["text"]).lower())) for m in _chuoi_kh):""",
     """    # `mo_ta` = máy đã đọc được ảnh khách gửi (doc_anh_khach) → tin có nội dung, không treo nữa.
    if all(vo_nghia(m["text"], m.get("co_dinh_kem")) and not m.get("mo_ta") and not (
            _tu_go and HOI_GIA.search(lam_sach(m["text"]).lower())) for m in _chuoi_kh):"""),

    # ── 4. đưa mô tả ảnh vào bản ghi hội thoại gửi model ────────────────────────────
    ("""        dong.append(f"{dau.get(m['boi'], m['boi'])}: {t}"
                    + ("  [TIN NHẮN THOẠI — voice]" if m.get("voice")
                       else "  [có ảnh/file]" if m["co_dinh_kem"] else ""))""",
     """        dong.append(f"{dau.get(m['boi'], m['boi'])}: {t}"
                    + ("  [TIN NHẮN THOẠI — voice]" if m.get("voice")
                       else f"  [ẢNH KHÁCH GỬI — máy mô tả, KHÔNG phải lời khách: {m['mo_ta']}]"
                       if m.get("mo_ta")
                       else "  [có ảnh/file]" if m["co_dinh_kem"] else ""))"""),

    # ── 5. lệnh soi cũng hiện mô tả, để soi được ca ảnh ─────────────────────────────
    ("""                print(f"  {dau.get(m['boi'], m['boi']):12s} {m['text'][:96]}"
                      f"{'  [có ảnh/file]' if m['co_dinh_kem'] else ''}")""",
     """                print(f"  {dau.get(m['boi'], m['boi']):12s} {m['text'][:96]}"
                      f"{'  [ẢNH: ' + m['mo_ta'] + ']' if m.get('mo_ta') else ''}"
                      f"{'  [có ảnh/file]' if m['co_dinh_kem'] and not m.get('mo_ta') else ''}")"""),

    # ── 6. đọc ảnh TRƯỚC khi phán, để chính cổng quyết định nhìn thấy nội dung ảnh ──
    ("""            quyet, ly_do = ai_co_vao_cuoc(msgs)
            # 19/09 (ca Fatima Miftah · ChunHo Golden Jewerly)""",
     """            # Đọc ảnh khách gửi TRƯỚC khi phán: cổng treo bên dưới xét theo nội dung tin,
            # ảnh chưa đọc thì tin rỗng → treo oan (ca JhanShylle AB 20/09).
            if doc_anh_khach(msgs):
                log(f"     [{(((c.get('customers') or [{}])[0].get('name')) or '?')[:20]:22s}] "
                    f"👁 đã đọc ảnh khách gửi")
            quyet, ly_do = ai_co_vao_cuoc(msgs)
            # 19/09 (ca Fatima Miftah · ChunHo Golden Jewerly)"""),
]


def main():
    that = "--that" in sys.argv
    s = open(F, encoding="utf-8").read()
    for i, (cu, moi) in enumerate(VA, 1):
        n = s.count(cu)
        assert n == 1, f"vá {i}: tìm thấy {n} chỗ khớp (phải đúng 1) — bản ai_sale.py đã đổi"
        assert moi not in s, f"vá {i}: đã vá rồi"
        s = s.replace(cu, moi, 1)
        print(f"  ✓ vá {i}/{len(VA)}")
    import ast
    ast.parse(s)
    print("  ✓ cú pháp hợp lệ")
    if not that:
        print("\n(xem trước — thêm --that để ghi thật)")
        return
    bak = f"{F}.bak-{time.strftime('%Y%m%d-%H%M')}-truoc-doc-anh"
    shutil.copy2(F, bak)
    with open(F, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"\n  ✓ đã ghi {F}\n  ✓ sao lưu {bak}")


main()

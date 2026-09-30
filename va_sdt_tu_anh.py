"""VÁ: SĐT / địa chỉ khách gửi BẰNG ẢNH thì cũng vào được đơn (2026-09-21).

Từ 20/09 AI đọc được ảnh (doc_anh_khach), nhưng khâu lên đơn chỉ dò số trong CHỮ, nên ca khách
chụp màn hình danh bạ ("Don Alam, mobile 054 671 2826") vẫn không mở ra đơn nháp nào.

ĐO TRƯỚC KHI LÀM (21/09, 12 ảnh thật có dấu hiệu liên hệ, mỗi ảnh đọc HAI lần):
  · 7 ảnh hai lần ra GIỐNG HỆT (màn hình danh bạ, hồ sơ WhatsApp/Telegram, nhãn Posta Plus…)
  · 4 ảnh cả hai lần đều trả None — ảnh sản phẩm, meme: KHÔNG bịa ra số nào
  · 1 ảnh LỆCH HẲN: nhãn iMile chữ nhỏ, lần 1 "+9665001240053 / HARADH", lần 2
    "+966 55713 6957 / 3588 Al Sulaymaniyah" — model đọc không ra thì BỊA.
⇒ Luật: ĐỌC HAI LẦN, hai lần khớp mới nhận. Đúng một ca bịa bị chặn, không mất ca đúng nào.

Cách nối — CỘNG THÊM, không đổi đường cũ:
  · chỉ đọc kỹ khi câu mô tả có dấu hiệu liên hệ (số dài / phone / contact / address…), để ảnh
    sản phẩm (phần lớn) không tốn lượt gọi nào;
  · số/địa chỉ đọc từ ảnh CHỈ dùng khi chữ trong chat và hồ sơ lưu đều không có — lấp chỗ trống,
    không tranh với số khách tự gõ;
  · đơn vẫn nằm "Mới": tính là THIẾU nên KHÔNG tự xác nhận (đúng cách Kuwait xử số nước ngoài),
    kèm ghi chú để sale gọi kiểm trước khi giao.

Chạy: python3 va_sdt_tu_anh.py [--that]
"""
import ast
import os
import shutil
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
F_AI = os.path.join(D, "ai_sale.py")
F_DON = os.path.join(D, "auto_len_don.py")

AI_1_CU = '''def doc_anh_khach(msgs):'''
AI_1_MOI = '''# Câu mô tả có dấu hiệu LIÊN HỆ thì mới đọc kỹ lần hai. Ảnh sản phẩm (phần lớn) không khớp
# nên không tốn thêm lượt gọi nào.
_ANH_CO_LIEN_HE = re.compile(
    r"\\d{6,}|\\bphone\\b|\\bmobile\\b|\\bnumber\\b|\\bcontact\\b|\\bwhats ?app\\b|\\baddress\\b"
    r"|\\blocation\\b|\\bmap\\b|\\bshipping label\\b|\\bwaybill\\b", re.I)
_TT_ANH = {}                          # url -> {"sdt": …, "dia_chi": …}
_NHAC_TT_ANH = (
    "Look at this image. Copy out ONLY what is literally written in it.\\n"
    "Answer with JSON and nothing else:\\n"
    "{\\"phone\\": \\"<the phone number exactly as shown, keep digits and spacing, or null>\\", "
    "\\"address\\": \\"<a postal or delivery address exactly as shown, or null>\\"}\\n"
    "Rules: copy digit by digit, never guess a missing digit, never invent, never complete a "
    "partial number. If there is no phone number in the image, phone must be null.")


def _f_tt_anh():
    return os.path.join(SCRIPT_DIR, "state", "chung", "anh_thong_tin.json")


def _doc_tt_mot_lan(b64):
    """Một lượt hỏi model: chữ ghi trong ảnh. Trả (sdt_thô, địa_chỉ_thô) hoặc (None, None)."""
    nha, key, api, model, _dem = nha_cung_cap()
    than = {"model": model, "max_tokens": 200,
            "messages": [{"role": "user", "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": _NHAC_TT_ANH}]}]}
    if nha in ("kimi", "deepseek"):
        than["thinking"] = {"type": "disabled"}
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
    except Exception as e:                               # noqa: BLE001
        log(f"   ⚠️  đọc SĐT trong ảnh hỏng: {str(e)[:110]}")
        return None, None
    _ghi_so_doc_anh(nha, model, res.get("usage") or {}, round(time.time() - t0, 1))
    txt = " ".join(c.get("text", "") for c in (res.get("content") or [])
                   if c.get("type") == "text")
    m = re.search(r"\\{.*\\}", txt, re.S)
    if not m:
        return None, None
    try:
        d = json.loads(m.group(0))
    except Exception:                                    # noqa: BLE001 — model trả không phải JSON
        return None, None
    return d.get("phone"), d.get("address")


def doc_tt_anh(url):
    """SĐT / địa chỉ ghi TRONG ảnh — ĐỌC HAI LẦN, hai lần khớp mới nhận.

    Đo 21/09 trên 12 ảnh thật: 7 ảnh hai lần ra giống hệt, 4 ảnh cả hai lần đều "không có",
    và 1 ảnh (nhãn iMile chữ nhỏ) hai lần ra HAI SỐ KHÁC HẲN — model đọc không ra thì bịa.
    Đọc hai lần chặn đúng ca bịa đó mà không mất ca đúng nào. Giá: $0,00013 mỗi lượt, chỉ chạy
    trên ảnh có dấu hiệu liên hệ (~1/5 số ảnh) nên cả ngày chưa tới nửa xu.
    """
    if url in _TT_ANH:
        return _TT_ANH[url]
    if not _TT_ANH:
        try:
            _TT_ANH.update(qht.load_json(_f_tt_anh(), {}) or {})
        except Exception:                                # noqa: BLE001
            pass
        if url in _TT_ANH:
            return _TT_ANH[url]
    nha, key, _api, _model, _dem = nha_cung_cap()
    if not key or nha not in ANH_NHA_DOC_DUOC:
        return {}
    try:
        b64 = _anh_nen(url)
    except Exception:                                    # noqa: BLE001
        return {}
    p1, d1 = _doc_tt_mot_lan(b64)
    p2, d2 = _doc_tt_mot_lan(b64)
    ra = {}
    s1, s2 = (re.sub(r"\\D", "", str(p1 or "")), re.sub(r"\\D", "", str(p2 or "")))
    # 7-15 chữ số là khuôn số điện thoại mọi nước; ngắn hơn là giá / mã đơn, dài hơn là dãy số
    # dính nhau (mã vận đơn) — không nhận.
    if s1 and s1 == s2 and 7 <= len(s1) <= 15:
        ra["sdt"] = " ".join(str(p1).split())[:30]
    else:
        if s1 and s2 and s1 != s2:
            log(f"   ⛔ ảnh: hai lần đọc ra hai SỐ khác nhau ({s1} / {s2}) — bỏ, không dùng")
    a1, a2 = (" ".join(str(d1 or "").split()), " ".join(str(d2 or "").split()))
    if len(a1) >= 12 and len(a2) >= 12:
        import difflib
        _g = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
        if difflib.SequenceMatcher(None, _g(a1), _g(a2)).ratio() >= 0.9:
            ra["dia_chi"] = (a1 if len(a1) >= len(a2) else a2)[:250]
        else:
            log("   ⛔ ảnh: hai lần đọc ra hai ĐỊA CHỈ khác nhau — bỏ, không dùng")
    _TT_ANH[url] = ra
    try:
        cu = qht.load_json(_f_tt_anh(), {}) or {}
        cu.update(_TT_ANH)
        tam = f"{_f_tt_anh()}.tam-{os.getpid()}"
        os.makedirs(os.path.dirname(tam), exist_ok=True)
        with open(tam, "w", encoding="utf-8") as fh:
            json.dump(cu, fh, ensure_ascii=False)
        os.replace(tam, _f_tt_anh())
    except Exception:                                    # noqa: BLE001
        pass
    return ra


def tt_tu_anh_da_doc(msgs):
    """SĐT / địa chỉ đã đọc được từ ảnh khách trong hội thoại này (tra SỔ, không gọi model).

    Dùng ở khâu lên đơn: ảnh có thể đã đọc từ lượt trước, lúc đó msgs khác nên tin không còn
    `anh_thong_tin` — nhưng sổ theo URL thì còn.
    """
    ra = {}
    if not _TT_ANH:
        try:
            _TT_ANH.update(qht.load_json(_f_tt_anh(), {}) or {})
        except Exception:                                # noqa: BLE001
            pass
    for m in msgs or []:
        if m.get("boi") != "khach" or m.get("voice"):
            continue
        for u in (m.get("anh") or []):
            for k, v in (_TT_ANH.get(u) or {}).items():
                if v:
                    ra[k] = v                            # ảnh mới hơn đè ảnh cũ
    return ra


def doc_anh_khach(msgs):'''

AI_2_CU = '''        t = doc_mot_anh(m["anh"][0])
        if t:
            m["mo_ta"] = t
            xong += 1'''
AI_2_MOI = '''        t = doc_mot_anh(m["anh"][0])
        if t:
            m["mo_ta"] = t
            xong += 1
            # Ảnh có dấu hiệu chứa SĐT / địa chỉ → đọc kỹ lấy đúng chữ trong ảnh, để khâu lên
            # đơn dùng được (khách chụp màn hình danh bạ, ảnh vận đơn).
            if _ANH_CO_LIEN_HE.search(t):
                tt = doc_tt_anh(m["anh"][0])
                if tt:
                    m["anh_thong_tin"] = tt
                    log("   📇 ảnh khách có " + " + ".join(
                        x for x in ("SĐT" if tt.get("sdt") else "",
                                    "địa chỉ" if tt.get("dia_chi") else "") if x))'''

AI_3_CU = '''    record["hen_giao"] = dong_hen_giao(msgs, mkey)'''
AI_3_MOI = '''    record["hen_giao"] = dong_hen_giao(msgs, mkey)
    # SĐT / địa chỉ khách gửi BẰNG ẢNH (21/09). extract() chỉ dùng khi chữ trong chat và hồ sơ
    # lưu đều không có — lấp chỗ trống, không tranh với số khách tự gõ.
    try:
        _tt_anh = tt_tu_anh_da_doc(msgs)
        record["sdt_anh"] = _tt_anh.get("sdt")
        record["dia_chi_anh"] = _tt_anh.get("dia_chi")
    except Exception as e:                  # noqa: BLE001 — sổ ảnh hỏng thì đơn đi đường cũ
        print(f"     ⚠️  tra sổ ảnh hỏng: {e!r}")'''

DON_1_CU = '''    if not sdt:
        thieu.append("SĐT")'''
DON_1_MOI = '''    if not sdt and record.get("sdt_anh"):
        # Khách gửi số BẰNG ẢNH (chụp màn hình danh bạ, hồ sơ WhatsApp, ảnh vận đơn) — 21/09.
        # Ghi vào đơn để sale thấy mà gọi, nhưng vẫn tính là THIẾU: số này máy đọc từ ảnh chứ
        # khách chưa gõ, mà sai một chữ số trong đơn COD là đơn giao hụt. Giống hệt cách Kuwait
        # xử số nước ngoài ở trên. (Đã qua cửa đọc-hai-lần-phải-khớp ở ai_sale.doc_tt_anh.)
        sdt = normalize_phone(record["sdt_anh"])
        canh_bao.append(f"SĐT {sdt} máy ĐỌC TỪ ẢNH khách gửi — gọi kiểm trước khi giao")
        thieu.append("SĐT khách tự gõ (số hiện có là máy đọc từ ảnh — chưa tự xác nhận được)")
    if not sdt:
        thieu.append("SĐT")'''

DON_2_CU = '''    if not diachi:
        thieu.append("địa chỉ (phải có tên tỉnh/bang)" + ('''
DON_2_MOI = '''    if not diachi and record.get("dia_chi_anh"):
        # Địa chỉ khách gửi BẰNG ẢNH (21/09) — cùng lý lẽ với SĐT: ghi vào đơn, nhưng THIẾU.
        diachi = record["dia_chi_anh"]
        canh_bao.append("địa chỉ máy ĐỌC TỪ ẢNH khách gửi — sale kiểm lại")
        thieu.append("địa chỉ khách tự gõ (địa chỉ hiện có là máy đọc từ ảnh)")
    if not diachi:
        thieu.append("địa chỉ (phải có tên tỉnh/bang)" + ('''

VA = [(F_AI, AI_1_CU, AI_1_MOI), (F_AI, AI_2_CU, AI_2_MOI), (F_AI, AI_3_CU, AI_3_MOI),
      (F_DON, DON_1_CU, DON_1_MOI), (F_DON, DON_2_CU, DON_2_MOI)]


def main():
    that = "--that" in sys.argv
    ban = {}
    for i, (f, cu, moi) in enumerate(VA, 1):
        s = ban.get(f) or open(f, encoding="utf-8").read()
        n = s.count(cu)
        assert n == 1, f"va {i} ({os.path.basename(f)}): {n} cho khop (phai dung 1)"
        assert moi not in s, f"va {i}: da va roi"
        ban[f] = s.replace(cu, moi, 1)
        print(f"  ✓ vá {i}/{len(VA)} — {os.path.basename(f)}")
    for f, s in ban.items():
        ast.parse(s)
    print("  ✓ cú pháp cả hai file hợp lệ")
    if not that:
        print("(xem trước — thêm --that để ghi thật)")
        return
    for f, s in ban.items():
        bak = f"{f}.bak-{time.strftime('%Y%m%d-%H%M')}-truoc-sdt-tu-anh"
        shutil.copy2(f, bak)
        open(f, "w", encoding="utf-8").write(s)
        print(f"  ✓ ghi {os.path.basename(f)} · lưu {os.path.basename(bak)}")


main()

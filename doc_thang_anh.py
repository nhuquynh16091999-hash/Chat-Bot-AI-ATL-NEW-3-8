#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ĐỌC THÁNG IN TRÊN ẢNH BẰNG MODEL — cho page bán theo tháng sinh (đá sinh tháng).

Chủ shop 2026-09-21: *"bạn nhìn trong ảnh cũng được mà, nhiều khi tôi không đặt tên"*.

Trước đó tháng của một tấm ảnh chỉ biết được nhờ: chữ Vision (macOS) đọc ra — phải chạy tay trên
máy Mac, hoặc TÊN file / tên mẫu — chủ shop không phải lúc nào cũng đặt. File này lấp nốt: model
(cùng nhà đang chạy AI Sale) nhìn thẳng vào ảnh và trả lời tháng nào đang IN trên đó.

Đọc HAI LẦN, hai lần khớp mới nhận (cùng cách `doc_tt_anh` chống model bịa). Ảnh đọc rồi thì nhớ
luôn — kể cả ảnh KHÔNG có tháng (ghi 0) — nên lần chạy sau gần như miễn phí, chỉ đụng ảnh mới.

Dùng:
    python3 doc_thang_anh.py            # đọc ảnh chưa biết tháng của các page bán theo tháng
    python3 doc_thang_anh.py --quet     # quét lại thư mục ảnh các page đó trước khi đọc
    python3 doc_thang_anh.py --so 20    # giới hạn số ảnh (chạy thử)
"""
import json
import os
import sys
import time

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
os.chdir(GOC)
import quet_hoi_thoai as qht          # noqa: E402
import ai_sale as A                   # noqa: E402
import quet_thu_muc_anh as QT         # noqa: E402

# ⚠️ BÀI HỌC 21/09: hỏi trống "ảnh này có chữ tháng nào" thì model gắn tháng cho CẢ giấy chứng
# nhận ("Date: 06 May 2025"), séc ngân hàng, tin báo giao hàng ("30 August 2026"), ảnh chụp màn
# hình khen hàng — 38/103 nhãn đầu tiên sai kiểu đó. Ở đó chữ tháng là NGÀY, không phải nhãn mẫu.
# Nên: (1) hỏi luôn có phải ẢNH MÓN HÀNG không, (2) dặn thẳng bỏ ngày tháng trong giấy tờ.
NHAC = (
    "Look at this image. Answer with JSON and nothing else:\n"
    '{"product": <true if this is a photo of a piece of jewellery being sold, false otherwise>, '
    '"month": <1-12 if the NAME OF A MONTH is printed on it as a label, else null>, '
    '"word": "<the month word exactly as it appears, or null>"}\n'
    "Rules: answer with a month ONLY if that month word is printed on the photo as a LABEL for "
    "the item (for example January, june, OCTOBER, Tháng 7). Answer null when the month is part "
    "of a DATE (for example '06 May 2025', 'Date of Issue', '30 August 2026'), and answer null "
    "for certificates, receipts, bank cheques, shipping notices, chat or review screenshots. "
    "Never infer the month from the gemstone or its colour. If a chart shows every month, "
    "answer null.")


NGUONG_CHU = 20          # Vision đọc ra nhiều hơn chừng này ký tự = ảnh chữ, không phải nhãn tháng


def _f():
    return os.path.join(GOC, "state", "anh_thang.json")


def _doc_mot_lan(b64):
    """Một lượt hỏi model -> tháng (1-12), 0 = ảnh không có tên tháng, None = hỏng."""
    nha, key, api, model, _ = A.nha_cung_cap()
    than = {"model": model, "max_tokens": 120,
            "messages": [{"role": "user", "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": NHAC}]}]}
    if nha in ("kimi", "deepseek"):
        than["thinking"] = {"type": "disabled"}
    dau = {"content-type": "application/json"}
    if nha == "kimi":
        dau["Authorization"] = f"Bearer {key}"
    else:
        dau["x-api-key"] = key
        dau["anthropic-version"] = "2023-06-01"
    import re
    import urllib.request
    t0 = time.time()
    try:
        req = urllib.request.Request(api, data=json.dumps(than).encode(), method="POST", headers=dau)
        with urllib.request.urlopen(req, timeout=40) as r:
            res = json.loads(r.read().decode())
    except Exception as e:                                # noqa: BLE001
        print("   ⚠️ ", str(e)[:110])
        return None
    A._ghi_so_doc_anh(nha, model, res.get("usage") or {}, round(time.time() - t0, 1))
    txt = " ".join(c.get("text", "") for c in (res.get("content") or []) if c.get("type") == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:                                     # noqa: BLE001
        return None
    th, tu = d.get("month"), str(d.get("word") or "").lower()
    if th is None or not d.get("product"):
        return 0                                          # không phải ảnh món hàng → coi như không có tháng
    try:
        th = int(th)
    except Exception:                                     # noqa: BLE001
        return None
    if not 1 <= th <= 12:
        return 0
    # chữ model chép ra phải ĐÚNG là tên tháng (chặn ca nó suy từ "04/03/2025")
    ten = ["january", "february", "march", "april", "may", "june", "july", "august",
           "september", "october", "november", "december", "thang", "tháng"]
    return th if any(x[:4] in tu for x in ten) else 0


def doc_thang(url):
    """Tháng in trên ảnh — hai lượt khớp nhau mới nhận. None = không đọc được."""
    try:
        b64 = A._anh_nen(url)
    except Exception as e:                                # noqa: BLE001
        print("   ⚠️  tải ảnh hỏng:", str(e)[:90])
        return None
    a = _doc_mot_lan(b64)
    if a is None:
        return None
    b = _doc_mot_lan(b64)
    return a if a == b else None


def page_ban_theo_thang(mk, kb):
    """Page nào cần đọc: kịch bản nói đá sinh tháng · đã có ảnh gắn nhãn tháng · hoặc trong thư
    mục ảnh có file đặt tên kiểu Tháng7/month7 (chủ shop đặt tên thì bắt luôn, không đặt tên thì
    hai cửa trên lo)."""
    import re
    ra = []
    for pid, p in (kb or {}).items():
        if not isinstance(p, dict):
            continue
        s = (json.dumps(p, ensure_ascii=False) + " " + (p.get("ten_page") or "")).lower()
        ten_file = " ".join((x.get("ten") or "") for x in A.thu_muc_anh(mk, pid)).lower()
        if ("birthstone" in s or "birth stone" in s or "birth month" in s
                or "kapanganakan" in s or "đá sinh tháng" in s or "sinh tháng" in s
                or re.search(r"th[áa]ng\s*\d{1,2}|month\s*\d{1,2}", ten_file)
                or A._anh_theo_thang_page(p, mk, pid)):
            ra.append((pid, p))
    return ra


def don_nhan_sai():
    """Xoá nhãn tháng model gán cho ảnh NHIỀU CHỮ (giấy tờ, séc, tin giao hàng, ảnh chat) — ở đó
    chữ tháng là NGÀY. Ghi lại 0 để không bao giờ hỏi lại."""
    d = qht.load_json(_f(), {}) or {}
    u = d.get("theo_url") or {}
    bo = 0
    for k, v in list(u.items()):
        if v and len((A.chu_trong_anh(k) or "").strip()) > NGUONG_CHU:
            u[k] = 0
            bo += 1
    d["theo_url"] = u
    d.setdefault("theo_chu", d.get("theo_chu") or {})
    qht.save_json(_f(), d)
    print(f"  🧹 bỏ {bo} nhãn tháng gán cho ảnh nhiều chữ (giấy tờ / chat / feedback)")
    return bo


def main():
    if "--don" in sys.argv:
        don_nhan_sai()
        return 0
    gioi_han = 0
    if "--so" in sys.argv:
        gioi_han = int(sys.argv[sys.argv.index("--so") + 1])
    tok = qht.load_env().get("PANCAKE_USER_TOKEN", "")
    import glob
    d = qht.load_json(_f(), {}) or {}
    theo_url = d.get("theo_url") or {}
    can = []
    for f in sorted(glob.glob(os.path.join(GOC, "state", "*", "kich_ban.json"))):
        mk = os.path.basename(os.path.dirname(f))
        kb = qht.load_json(f, {})
        ds = page_ban_theo_thang(mk, kb)
        if not ds:
            continue
        if "--quet" in sys.argv and tok:                  # ảnh mới chủ shop vừa tải lên
            tm = qht.load_json(os.path.join(GOC, "state", mk, "thu_muc_anh.json"), {}) or {}
            for pid, p in ds:
                anh, err = QT.quet_page(pid, tok)
                if not err:
                    tm[pid] = {"ten_page": p.get("ten_page"), "luc": int(time.time()), "anh": anh}
            qht.save_json(os.path.join(GOC, "state", mk, "thu_muc_anh.json"), tm)
        for pid, p in ds:
            thay = set()
            for m in p.get("mau") or []:
                for u in m.get("anh") or []:
                    thay.add((u, (m.get("tu_khoa") or "").strip()))
            for x in A.thu_muc_anh(mk, pid):
                thay.add((x.get("u"), x.get("ten") or ""))
            for u, ten in thay:
                if not u or u in theo_url or A.thang_cua_anh(u, ten):
                    continue
                # Ảnh Vision ĐÃ đọc ra nhiều chữ thì luật nhãn-tháng đã xử rồi (và nó là giấy tờ /
                # feedback / bảng giá) — hỏi model chỉ tổ nhận nhầm NGÀY trong giấy tờ thành tháng.
                if len((A.chu_trong_anh(u) or "").strip()) > NGUONG_CHU:
                    theo_url[u] = 0
                    continue
                can.append((mk, p.get("ten_page"), u, ten))
    # một ảnh dùng ở nhiều page: chỉ đọc một lần
    xong, thay_url = set(), {}
    can = [c for c in can if not (c[2] in xong or xong.add(c[2]))]
    if gioi_han:
        can = can[:gioi_han]
    print(f"cần đọc {len(can)} ảnh chưa biết tháng")
    co = 0
    for i, (mk, ten_page, u, ten) in enumerate(can, 1):
        th = doc_thang(u)
        if th is None:
            continue
        thay_url[u] = th
        if th:
            co += 1
            print(f"  [{i}/{len(can)}] {ten_page} · {ten or '(không tên)'} → THÁNG {th}")
        if i % 10 == 0 or i == len(can):
            d["theo_url"] = dict(theo_url, **thay_url)
            d.setdefault("theo_chu", d.get("theo_chu") or {})
            qht.save_json(_f(), d)
    d["theo_url"] = dict(theo_url, **thay_url)
    d.setdefault("theo_chu", d.get("theo_chu") or {})
    qht.save_json(_f(), d)
    print(f"XONG — đọc {len(thay_url)} ảnh, {co} ảnh có tháng (state/anh_thang.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

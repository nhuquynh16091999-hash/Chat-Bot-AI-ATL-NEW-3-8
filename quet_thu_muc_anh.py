#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QUÉT THƯ MỤC ẢNH CỦA PAGE (pancake.vn → "Thư mục ảnh") về state/<tt>/thu_muc_anh.json.

Vì sao có file này (chủ shop 2026-09-21): AI chỉ nhìn thấy ảnh nằm trong KỊCH BẢN (mẫu Trả lời
nhanh). Page Glamora Jewelry có đủ 12 ảnh đá sinh tháng (bt1…bt12) trong THƯ MỤC ẢNH của page mà
kịch bản chỉ đính mỗi ảnh tháng 1 — nên khách hỏi tháng 4 vẫn nhận ảnh tháng 1.

Đường đi: GET pancake.vn/api/v1/pages/<pid>/contents (PANCAKE_USER_TOKEN, đúng đường giao diện
web). Kết quả là file TĨNH, AI đọc thẳng, không gọi API trong vòng chạy.

Dùng:
    python3 quet_thu_muc_anh.py             # quét mọi page trong kịch bản
    python3 quet_thu_muc_anh.py uae saudi   # chỉ vài thị trường
"""
import glob
import json
import re
import os
import sys
import time
import urllib.parse
import urllib.request

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
import quet_hoi_thoai as qht  # noqa: E402

WEB_API = "https://pancake.vn/api/v1"
SO_MOI_TRANG = 100
TOI_DA_TRANG = 3                                  # 300 ảnh/page là quá đủ


def _contents(pid, tok, trang):
    u = f"{WEB_API}/pages/{pid}/contents?" + urllib.parse.urlencode(
        {"access_token": tok, "page_number": trang, "page_size": SO_MOI_TRANG})
    try:
        with urllib.request.urlopen(u, timeout=40) as r:
            return json.loads(r.read().decode() or "{}").get("data") or [], None
    except Exception as e:                                        # noqa: BLE001
        return [], str(e)


def quet_page(pid, tok):
    """Mọi ảnh trong thư mục ảnh của page -> [{"u": url, "ten": tên file}]."""
    ra, thay = [], set()
    for trang in range(1, TOI_DA_TRANG + 1):
        ds, err = _contents(pid, tok, trang)
        if err:
            return ra, err
        for x in ds:
            u = x.get("url") or x.get("path") or x.get("preview_url")
            if u and u not in thay:
                thay.add(u)
                ra.append({"u": u, "ten": x.get("name") or ""})
        if len(ds) < SO_MOI_TRANG:
            break
    return ra, None


# ── BẢN ĐỒ ẢNH → THÁNG (state/anh_thang.json) ────────────────────────────────────────────────
# Cùng MỘT tấm ảnh dùng chung cho nhiều page (URL content.pancake.vn là mã băm nội dung). Ảnh
# tháng 6 của bộ đá sinh tháng bị Vision đọc thành "aunf" — không page nào đọc ra chữ, NHƯNG page
# BirthStone Jewelry USUS đặt tên nó là "Tháng6.jpeg" và mẫu /THANG6. Nên gom tên từ MỌI page rồi
# dùng chung: ảnh nào một nơi gọi đích danh tháng thì mọi page dùng ảnh đó đều biết là tháng ấy.
def ban_do_thang():
    """{url: tháng} suy từ TÊN mẫu kịch bản + TÊN file thư mục ảnh của mọi page."""
    import ai_sale as A
    d = {}
    for f in sorted(glob.glob(os.path.join(GOC, "state", "*", "kich_ban.json"))):
        tt = os.path.basename(os.path.dirname(f))
        for pid, p in (qht.load_json(f, {}) or {}).items():
            if not isinstance(p, dict):
                continue
            for m in p.get("mau") or []:
                th = A._thang_cua_ten_mau(m.get("tu_khoa") or "")
                for u in m.get("anh") or []:
                    if th and u:
                        d.setdefault(u, th)
        for pid, v in (qht.load_json(os.path.join(GOC, "state", tt, "thu_muc_anh.json"), {}) or {}).items():
            for x in v.get("anh") or []:
                th = A._thang_cua_ten_mau(x.get("ten") or "")
                if th and x.get("u"):
                    d.setdefault(x["u"], th)
    # CÙNG MỘT TẤM ẢNH TẢI LÊN NHIỀU LẦN = URL KHÁC NHAU (mã băm nội dung khác vì file khác byte).
    # Nên học thêm theo CHỮ ĐỌC ĐƯỢC: ảnh tháng 6 bị Vision đọc thành "aunf" ở cả 4 page; page Mỹ
    # đặt tên nó là "Tháng6.jpeg" → mọi ảnh đọc ra đúng chuỗi lạ ấy đều là tháng 6.
    oc = qht.load_json(os.path.join(GOC, "state", "anh_chu.json"), {}) or {}
    chu_th, bo = {}, set()
    for u, th in d.items():
        c = ((oc.get(u) or {}).get("chu") or "").strip().lower()
        if len(c) < 4 or len(c) > 24 or not re.search(r"[a-z]{3}", c):
            continue
        if chu_th.get(c, th) != th:                   # hai nơi gọi khác tháng → bỏ, không đoán
            bo.add(c)
        chu_th[c] = th
    chu_th = {c: t for c, t in chu_th.items() if c not in bo}
    qht.save_json(os.path.join(GOC, "state", "anh_thang.json"),
                  {"theo_url": d, "theo_chu": chu_th})
    print(f"  🗺  bản đồ ảnh→tháng: {len(d)} ảnh theo url, {len(chu_th)} chữ đọc được"
          " (state/anh_thang.json)")
    return d


def main():
    if "--ban-do" in sys.argv:                        # chỉ dựng lại bản đồ (chạy sau khi OCR xong)
        ban_do_thang()
        return 0
    tt_chon = [x.lower() for x in sys.argv[1:] if not x.startswith("-")]
    tok = qht.load_env().get("PANCAKE_USER_TOKEN", "")
    if not tok:
        print("⛔ thiếu PANCAKE_USER_TOKEN trong .env")
        return 1
    tong_page = tong_anh = loi = 0
    for f in sorted(glob.glob(os.path.join(GOC, "state", "*", "kich_ban.json"))):
        tt = os.path.basename(os.path.dirname(f))
        if tt_chon and tt not in tt_chon:
            continue
        kb = qht.load_json(f, {})
        cu = qht.load_json(os.path.join(GOC, "state", tt, "thu_muc_anh.json"), {})
        moi = {}
        for pid, p in kb.items():
            if not isinstance(p, dict):
                continue
            ds, err = quet_page(pid, tok)
            if err:
                loi += 1
                print(f"  ⚠️  [{tt}] {p.get('ten_page')} — {err}")
                if pid in cu:                                     # lỗi thì giữ bản cũ, đừng xoá
                    moi[pid] = cu[pid]
                continue
            moi[pid] = {"ten_page": p.get("ten_page"), "luc": int(time.time()), "anh": ds}
            tong_page += 1
            tong_anh += len(ds)
        qht.save_json(os.path.join(GOC, "state", tt, "thu_muc_anh.json"), moi)
        print(f"  ✅ {tt}: {len(moi)} page")
    ban_do_thang()
    print(f"XONG — {tong_page} page, {tong_anh} ảnh, {loi} page lỗi")
    return 0


if __name__ == "__main__":
    sys.exit(main())

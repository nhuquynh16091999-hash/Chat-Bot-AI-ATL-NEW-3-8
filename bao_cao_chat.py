#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BÁO CÁO CHAT — trang "💬 Báo cáo chat" của trang quản lý (chủ shop 12/11/2026: "dashboard thiếu báo cáo
về các tin nhắn đã xử lí, tin nhắn chốt và các số liệu khác").

Chỉ ĐỌC sổ có sẵn trên đĩa, không gọi Pancake / model:
  state/<tt>/so_chi_phi.jsonl — mỗi lượt khách nhắn mà AI xét: cửa (tra_loi / xet / im / treo), hành động,
                                câu khách hỏi, gửi thật hay chạy thử
  state/<tt>/so_viec.jsonl    — mỗi lần AI ĐỘNG vào hội thoại: câu AI soạn, cổng chặn, gửi thật / hỏng
  state/<tt>/ho_so.db         — hồ sơ khách AI gom được: tên, SĐT, địa chỉ, số lượng, bước (du_dieu_kien = đủ để chốt)

Ngày tính theo GIỜ VIỆT NAM (UTC+7). Sổ ghi giờ máy chủ (UTC).

Chạy tay:  python3 bao_cao_chat.py vietnam [số ngày]
"""
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VN = timezone(timedelta(hours=7))
BUOC_CHOT = ("du_dieu_kien", "da_len_don", "cho_xac_minh_nha")


def _dong(f):
    try:
        with open(f, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    try:
                        yield json.loads(ln)
                    except ValueError:
                        continue
    except OSError:
        return


def _giay(x):
    """Mốc thời gian trong sổ → giây epoch. Nhận số epoch (chuỗi/số) hoặc ISO không múi giờ (= UTC)."""
    if x in (None, ""):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        pass
    try:
        d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.timestamp()
    except ValueError:
        return None


def _ngay_vn(giay):
    return datetime.fromtimestamp(giay, VN).strftime("%Y-%m-%d")


def _gio_vn(giay):
    return datetime.fromtimestamp(giay, VN).strftime("%d/%m %H:%M")


_CHU_MAY = re.compile(r"\s*\((?:tên Facebook|model|mục|máy|AI)[^)]*\)\s*", re.I)


def _sach(x):
    """Bỏ ghi chú máy dính trong hồ sơ: "Vui Khỏe (tên Facebook — mục 1 coi là đã đủ)" → "Vui Khỏe"."""
    return _CHU_MAY.sub(" ", str(x or "")).strip()


def _ket_cuc(r):
    """Kết cục một việc AI làm (so_viec): gui · thu · chan · treo · gui_hong · viet_lai."""
    if r.get("chan") == "chan":
        return "chan"
    if str(r.get("gui_hong") or "").strip():
        return "gui_hong"
    if r.get("hd") in ("treo", "tra_loi_treo") and not (r.get("tin") or "").strip():
        return "treo"
    if not (r.get("tin") or "").strip():
        return "treo"
    return "gui" if str(r.get("that")) == "1" else "thu"


def bao_cao_chat(mkey, ngay=7):
    ngay = max(1, min(int(ngay or 7), 90))
    now = time.time()
    hom_nay = datetime.now(VN).date()
    cac_ngay = [(hom_nay - timedelta(days=i)).isoformat() for i in range(ngay - 1, -1, -1)]
    tu = datetime.combine(hom_nay - timedelta(days=ngay - 1), datetime.min.time(), VN).timestamp()
    d = os.path.join(SCRIPT_DIR, "state", mkey)

    bang = {n: {"ngay": n, "luot_khach": 0, "hoi_thoai": set(), "ai_tra_loi": 0, "ai_bo_sung": 0,
                "im_da_du": 0, "im_khac": 0, "treo": 0, "gui": 0, "thu": 0, "chan": 0, "gui_hong": 0,
                "chot": set()} for n in cac_ngay}

    # ── 1) Lượt khách nhắn mà AI xét (so_chi_phi) ──
    hoi_cua = {}                                   # conv -> [(giây, câu khách hỏi)]
    for r in _dong(os.path.join(d, "so_chi_phi.jsonl")):
        g = _giay(r.get("luc"))
        if g is None:
            continue
        conv = str(r.get("conv") or "")
        if r.get("hoi"):
            hoi_cua.setdefault(conv, []).append((g, str(r["hoi"])))
        if g < tu:
            continue
        b = bang.get(_ngay_vn(g))
        if not b:
            continue
        cua, hd = r.get("cua"), r.get("hd")
        b["luot_khach"] += 1
        b["hoi_thoai"].add(conv)
        if hd in ("tra_loi", "len_don", "tra_loi_treo", "xac_minh_nha"):
            if cua == "xet":
                b["ai_bo_sung"] += 1          # Botcake / sale đã trả lời nhưng chưa đủ ý → AI bổ sung
            else:
                b["ai_tra_loi"] += 1
        elif hd == "im":
            if cua == "xet":
                b["im_da_du"] += 1            # Botcake / sale trả lời đủ rồi → AI im
            else:
                b["im_khac"] += 1             # sale đang chat, tin cũ, tin quảng cáo… → AI không vào
        elif hd == "treo":
            b["treo"] += 1

    # ── 2) Việc AI làm (so_viec) — câu AI soạn + kết cục ──
    viec = []
    for r in _dong(os.path.join(d, "so_viec.jsonl")):
        g = _giay(r.get("luc"))
        if g is None or g < tu:
            continue
        kc = _ket_cuc(r)
        b = bang.get(_ngay_vn(g))
        if b and kc in ("gui", "thu", "chan", "gui_hong"):
            b[kc] += 1
        conv = str(r.get("conv") or "")
        if b and r.get("hd") == "len_don":
            b["chot"].add(conv)
        hoi = ""
        for gh, cau in sorted(hoi_cua.get(conv, []), key=lambda x: x[0]):
            if gh <= g + 5:
                hoi = cau
        ma = r.get("ma") or []
        if isinstance(ma, str):
            try:
                ma = json.loads(ma.replace("'", '"'))
            except ValueError:
                ma = [ma] if ma not in ("", "[]") else []
        viec.append({"luc": g, "gio": _gio_vn(g), "khach": r.get("khach") or "", "page": r.get("page") or "",
                     "conv": conv, "kc": kc, "chot": r.get("hd") == "len_don", "hoi": hoi,
                     "tin": r.get("tin") or "", "ma": ma, "ghi_chu": (r.get("gc") or "").strip(),
                     "anh": int(r.get("anh") or 0)})
    viec.sort(key=lambda x: -x["luc"])

    # ── 3) Khách đủ thông tin để chốt (ho_so.db) ──
    chot = []
    f_db = os.path.join(d, "ho_so.db")
    if os.path.exists(f_db):
        try:
            c = sqlite3.connect(f"file:{f_db}?mode=ro", uri=True, timeout=5)
            c.row_factory = sqlite3.Row
            for r in c.execute("SELECT * FROM ho_so WHERE buoc IN (?,?,?) ORDER BY cap_nhat DESC", BUOC_CHOT):
                g = _giay(r["cap_nhat"])
                if g is None or g < tu:
                    continue
                b = bang.get(_ngay_vn(g))
                if b:
                    b["chot"].add(str(r["conv_id"]))
                chot.append({"gio": _gio_vn(g), "luc": g, "khach": r["ten_khach"] or "", "ten": _sach(r["ten"]),
                             "sdt": _sach(r["sdt"]), "dia_chi": _sach(r["dia_chi"]), "so_luong": _sach(r["so_luong"]),
                             "thanh_toan": r["thanh_toan"] or "", "buoc": r["buoc"], "so_tin": r["so_tin"] or 0,
                             "conv": r["conv_id"]})
            c.close()
        except sqlite3.Error:
            pass

    theo_ngay = []
    for n in cac_ngay:
        b = bang[n]
        theo_ngay.append(dict(b, hoi_thoai=len(b["hoi_thoai"]), chot=len(b["chot"])))
    tong = {k: sum(x[k] for x in theo_ngay) for k in theo_ngay[0] if k != "ngay"}
    tong["hoi_thoai"] = len(set().union(*(bang[n]["hoi_thoai"] for n in cac_ngay)))
    tong["chot"] = len(set().union(*(bang[n]["chot"] for n in cac_ngay)))
    return {"tt": mkey, "ngay": ngay, "tu": cac_ngay[0], "den": cac_ngay[-1],
            "luc": datetime.now(VN).strftime("%d/%m/%Y %H:%M"), "tong": tong,
            "theo_ngay": theo_ngay[::-1], "chot": chot, "viec": viec[:400], "so_viec": len(viec)}


if __name__ == "__main__":
    tt = sys.argv[1] if len(sys.argv) > 1 else "vietnam"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    k = bao_cao_chat(tt, n)
    print(json.dumps({"tong": k["tong"], "theo_ngay": k["theo_ngay"][:3], "so_chot": len(k["chot"]),
                      "so_viec": k["so_viec"], "viec_dau": k["viec"][:2]}, ensure_ascii=False, indent=1)[:3000])

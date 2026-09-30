#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toàn cảnh mọi thị trường trên MỘT màn — tab "Toàn cảnh" của giao diện AI Sale.

Chủ shop 14/09/2026: "tổng quan chung luôn các nước đi, đừng bắt tôi ấn từng nước".

Chỉ đọc file trên đĩa, không gọi model, không gọi Pancake (trừ 1 lượt hỏi POS mỗi 15 phút để
đếm page thuộc shop, và số dư Kimi nhớ 5 phút). Nguồn số:
  state/<tt>/so_chi_phi.jsonl   — mỗi lượt AI xét 1 hội thoại: tiền, gọi model hay im
  state/<tt>/so_viec.jsonl      — mỗi lần AI ĐỘNG vào hội thoại: gửi / ghi chú / treo / chặn
  state/<tt>/don_theo_hoi_thoai.json — đơn tool lên từ chat
  state/<tt>/page_bi_fb_chan.json, pending.json (token hỏng)
  systemctl + /var/log/aisale-chat[-tt].log — service còn chạy không, lượt dò gần nhất

  python3 toan_canh.py [--gio 24]      in bản chữ
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
STATE = os.path.join(SCRIPT_DIR, "state")

TEN_NHA = {"kimi": "Kimi", "deepseek": "DeepSeek", "anthropic": "Claude"}

_NHO = {"luc": 0, "gio": None, "kq": None}
_SHOP = {"luc": 0, "kq": {}}
_KHOA = threading.Lock()


def _doc_json(f, mac_dinh):
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:                                     # noqa: BLE001
        return mac_dinh


def _dong(f):
    if not os.path.exists(f):
        return
    with open(f, encoding="utf-8", errors="replace") as fh:
        for s in fh:
            s = s.strip()
            if not s:
                continue
            try:
                yield json.loads(s)
            except Exception:                             # noqa: BLE001
                continue


def _ten_unit(tt):
    return "aisale-chat.service" if tt == "uae" else f"aisale-chat-{tt}.service"


def _f_log(tt):
    return "/var/log/aisale-chat.log" if tt == "uae" else f"/var/log/aisale-chat-{tt}.log"


def _service(tt):
    """Service chat của nước này còn chạy không + lượt dò gần nhất.

    Log không có dấu giờ từng dòng nên 'lỗi gần đây' đếm trong 20 lượt dò cuối (dòng ⏱),
    không đếm cả file — lỗi trước lần restart đã vá thì không được báo lại.
    """
    ra = {"unit": _ten_unit(tt), "chay": None, "log_giay": None, "luot_do": None,
          "loi_gan": 0, "tong_ket": ""}
    try:
        r = subprocess.run(["systemctl", "is-active", ra["unit"]], capture_output=True,
                           text=True, timeout=5)
        ra["chay"] = r.stdout.strip() == "active"
        ra["trang_thai"] = r.stdout.strip()
    except Exception:                                     # noqa: BLE001
        ra["chay"] = None                                 # máy không có systemd (chạy ở Mac)
    f = _f_log(tt)
    if not os.path.exists(f):
        return ra
    ra["log_giay"] = int(time.time() - os.path.getmtime(f))
    try:
        with open(f, "rb") as fh:
            fh.seek(0, 2)
            n = fh.tell()
            fh.seek(max(0, n - 250_000))
            duoi = fh.read().decode("utf-8", errors="replace").splitlines()
    except Exception:                                     # noqa: BLE001
        return ra
    moc = [i for i, s in enumerate(duoi) if "⏱" in s]
    tu = moc[-21] if len(moc) > 20 else 0
    ra["loi_gan"] = sum(1 for s in duoi[tu:] if "lượt xử lỗi" in s)
    if moc:
        m = re.search(r"lượt dò (\d+)s", duoi[moc[-1]])
        ra["luot_do"] = int(m.group(1)) if m else None
    for s in reversed(duoi):
        if "trả lời" in s and "lỗi" in s and "·" in s:
            ra["tong_ket"] = s.strip()
            break
    return ra


def _so_page_shop(dstt):
    """Số page CÓ TOKEN thuộc đúng shop POS từng nước (page_tokens.json chứa lẫn page nước khác).
    Hỏi POS song song, nhớ 15 phút. Hỏi hỏng thì trả None — giao diện hiện số chưa lọc."""
    if time.time() - _SHOP["luc"] < 900 and _SHOP["kq"]:
        return _SHOP["kq"]
    import ai_sale as A

    def mot(tt):
        tok = _doc_json(os.path.join(STATE, tt, "page_tokens.json"), {})
        co = {p for p, st in tok.items() if isinstance(st, dict) and st.get("token")}
        try:
            thuoc = A._pages_cua_shop(tt)
        except Exception:                                 # noqa: BLE001
            thuoc = None
        return tt, {"token": len(co), "shop": None if thuoc is None else len(co & thuoc),
                    "shop_tong": None if thuoc is None else len(thuoc)}
    with ThreadPoolExecutor(8) as ex:
        kq = dict(ex.map(mot, dstt))
    _SHOP.update(luc=time.time(), kq=kq)
    return kq


def _mot_nuoc(tt, tu_ep, now):
    tu_chu = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(tu_ep))
    so_gio = max(1, round((now - tu_ep) / 3600))
    x = {"tt": tt, "hoi_thoai": 0, "goi": 0, "im": 0, "tien": 0.0, "tien_thu": 0.0,
         "page_co_khach": 0, "gui": 0, "ghi_chu": 0, "gui_hong": 0, "treo": 0, "chan": 0,
         "chot": 0, "don": 0, "khach_gan_nhat": None}
    conv, pid_khach = set(), set()
    tp = defaultdict(lambda: {"goi": 0, "tien": 0.0, "hoi_thoai": set()})
    for r in _dong(os.path.join(STATE, tt, "so_chi_phi.jsonl")):
        if (r.get("luc") or "") < tu_chu:
            continue
        t = float(r.get("tien") or 0)
        if not r.get("that"):
            x["tien_thu"] += t
        x["tien"] += t
        if r.get("goi"):
            x["goi"] += 1
        if r.get("cua") == "im":
            x["im"] += 1
        c = r.get("conv")
        if c:
            conv.add(c)
        if r.get("pid"):
            pid_khach.add(r["pid"])
            p = tp[r["pid"]]
            p["ten"] = r.get("page") or r["pid"]
            p["goi"] += 1 if r.get("goi") else 0
            p["tien"] += t
            if c:
                p["hoi_thoai"].add(c)
        kl = r.get("khach_luc") or ""
        if kl and (x["khach_gan_nhat"] or "") < kl:
            x["khach_gan_nhat"] = kl[:19]
    x["hoi_thoai"], x["page_co_khach"] = len(conv), len(pid_khach)

    theo_gio = [0] * so_gio
    gan_day = []
    pv = defaultdict(Counter)
    for r in _dong(os.path.join(STATE, tt, "so_viec.jsonl")):
        luc = r.get("luc") or 0
        if luc < tu_ep or not r.get("that"):
            continue
        hd, tin = r.get("hd"), (r.get("tin") or "").strip()
        if r.get("chan") == "chan":
            kc = "chan"
        elif hd == "treo":
            kc = "treo"
        elif tin and r.get("gui_hong"):
            kc = "ghi_chu" if r.get("gc") else "gui_hong"
        elif tin:
            kc = "gui"
        else:
            kc = "khac"
        if kc in x:
            x[kc] += 1
        if hd == "len_don" and kc in ("gui", "ghi_chu"):
            x["chot"] += 1
        if kc == "gui":
            i = min(so_gio - 1, int((luc - tu_ep) // 3600))
            theo_gio[i] += 1
        pv[r.get("pid") or ""][kc] += 1
        if r.get("pid") and r.get("page"):
            tp[r["pid"]]["ten"] = r["page"]
        gan_day.append({"luc": luc, "tt": tt, "page": r.get("page") or "", "khach": r.get("khach") or "",
                        "kc": kc, "hd": hd or "", "tin": (tin or r.get("gc") or "")[:220],
                        "ma": r.get("ma") or []})

    don = _doc_json(os.path.join(STATE, tt, "don_theo_hoi_thoai.json"), {})
    x["don"] = sum(1 for v in don.values() if isinstance(v, dict) and (v.get("luc") or 0) >= tu_ep)

    chan = _doc_json(os.path.join(STATE, tt, "page_bi_fb_chan.json"), {})
    x["fb_chan"] = sum(1 for v in chan.values()
                       if isinstance(v, dict) and (v.get("luc") or 0) >= now - 86400)
    pend = _doc_json(os.path.join(STATE, tt, "pending.json"), {})
    x["token_hong"] = sum(1 for s in (pend.get("loi") or []) if "token hỏng" in str(s))
    x["theo_gio"] = theo_gio
    tin_toi = x["gui"]
    x["tien_moi_tin"] = (x["tien"] / tin_toi) if tin_toi else None

    page = []
    for pid, p in tp.items():
        c = pv.get(pid, Counter())
        page.append({"tt": tt, "pid": pid, "ten": p.get("ten") or pid, "hoi_thoai": len(p["hoi_thoai"]),
                     "goi": p["goi"], "tien": p["tien"], "gui": c["gui"], "ghi_chu": c["ghi_chu"],
                     "treo": c["treo"], "chan": c["chan"],
                     "fb_chan": pid in chan and (chan[pid].get("luc") or 0) >= now - 86400})
    return x, page, gan_day


def toan_canh(gio=24):
    gio = max(1, min(int(gio or 24), 24 * 14))
    with _KHOA:
        if _NHO["kq"] and _NHO["gio"] == gio and time.time() - _NHO["luc"] < 30:
            return _NHO["kq"]
    import quan_ly as QL
    import quet_hoi_thoai as q
    import bao_cao_tien as BC
    import chi_phi

    now = time.time()
    tu_ep = now - gio * 3600
    mk = _doc_json(os.path.join(SCRIPT_DIR, "markets.json"), {})
    dstt = QL.thi_truong()

    with ThreadPoolExecutor(8) as ex:
        sv = dict(zip(dstt, ex.map(_service, dstt)))
        so = list(ex.map(lambda t: _mot_nuoc(t, tu_ep, now), dstt))
    try:
        shop = _so_page_shop(dstt)
    except Exception:                                     # noqa: BLE001
        shop = {}

    nuoc, page, feed = [], [], []
    for (x, pg, gd), tt in zip(so, dstt):
        m = mk.get(tt) or {}
        x["ten"] = m.get("ten") or tt.upper()
        x["tien_te"] = m.get("tien_te") or ""
        x["service"] = sv.get(tt) or {}
        x["page"] = shop.get(tt) or {}
        x["co_chay"] = bool(x["service"].get("chay")) or bool(x["hoi_thoai"])
        nuoc.append(x)
        page += pg
        feed += gd

    # Nước đang chạy lên trước, đông khách lên trước; nước chưa chạy xuống cuối.
    nuoc.sort(key=lambda x: (not x["co_chay"], -x["hoi_thoai"], x["tt"]))
    khoa = ["hoi_thoai", "goi", "im", "tien", "tien_thu", "page_co_khach", "gui", "ghi_chu",
            "gui_hong", "treo", "chan", "chot", "don", "fb_chan", "token_hong"]
    tong = {k: sum(x[k] for x in nuoc) for k in khoa}
    tong["tien_moi_tin"] = tong["tien"] / tong["gui"] if tong["gui"] else None
    tong["nuoc_chay"] = sum(1 for x in nuoc if x["service"].get("chay"))

    # Việc cần người: page nào dồn nhiều ca AI không tự lo xong (ghi chú + treo + chặn).
    page.sort(key=lambda p: -(p["ghi_chu"] + p["treo"] + p["chan"]) * 1000 - p["hoi_thoai"])
    can_nguoi = [p for p in page if p["ghi_chu"] + p["treo"] + p["chan"]][:15]
    dong_khach = sorted(page, key=lambda p: -p["hoi_thoai"])[:15]

    canh = []
    for x in nuoc:
        s = x["service"]
        if not x["co_chay"] and not os.path.exists(_f_log(x["tt"])):
            continue                                      # nước chưa từng mở AI — không kêu
        if s.get("chay") is False:
            canh.append(("nang", f"{x['ten']}: service {s.get('unit')} KHÔNG chạy ({s.get('trang_thai', '')})"))
        elif s.get("chay") and s.get("log_giay") is not None and s["log_giay"] > 600:
            canh.append(("nang", f"{x['ten']}: service chạy nhưng log im {s['log_giay'] // 60} phút — có thể đang treo"))
        if s.get("loi_gan"):
            canh.append(("canh", f"{x['ten']}: {s['loi_gan']} lượt xử lỗi trong 20 lượt dò gần nhất — khách trong lượt lỗi bị bỏ sót"))
    # FB chặn / token hỏng là tình trạng kéo dài, đã có cột riêng trong bảng — gộp 1 dòng cho khỏi ngợp.
    fb = [x for x in nuoc if x["co_chay"] and x["fb_chan"]]
    th = [x for x in nuoc if x["co_chay"] and x["token_hong"]]
    if fb:
        canh.append(("canh", f"{sum(x['fb_chan'] for x in fb)} page bị Facebook chặn gửi (#2022) ở {len(fb)} nước — "
                             "câu AI vào ghi chú, sale gửi tay: " + ", ".join(f"{x['ten']} {x['fb_chan']}" for x in fb)))
    if th:
        canh.append(("canh", f"{sum(x['token_hong'] for x in th)} page token hỏng (thường là hết gói Pancake) — "
                             "AI không đọc được hội thoại: " + ", ".join(f"{x['ten']} {x['token_hong']}" for x in th)))

    env = q.load_env()
    nha = (env.get("AI_PROVIDER") or "kimi").strip().lower()
    so_du = BC.so_du_kimi(env)       # đã theo AI_PROVIDER
    nap = sum(float(n.get("so_tien") or 0) for n in chi_phi.doc_nap() if (n.get("nha") or nha) == nha)

    feed.sort(key=lambda r: -r["luc"])
    kq = {"luc": time.strftime("%d/%m/%Y %H:%M:%S"), "gio": gio, "nuoc": nuoc, "tong": tong,
          "canh": canh, "can_nguoi": can_nguoi, "dong_khach": dong_khach, "gan_day": feed[:40],
          "kimi": {"nha": nha, "nap": nap, "so_du": so_du, "model": env.get("AI_MODEL") or "",
                   "tran_ngay": env.get("AI_NGAN_SACH_NGAY") or ""}}
    with _KHOA:
        _NHO.update(luc=time.time(), gio=gio, kq=kq)
    return kq


if __name__ == "__main__":
    a = sys.argv[1:]
    g = int(a[a.index("--gio") + 1]) if "--gio" in a else 24
    k = toan_canh(g)
    t = k["tong"]
    print(f"\n  TOÀN CẢNH {g} giờ tới {k['luc']} — {t['nuoc_chay']} nước đang chạy\n")
    print(f"  {'Nước':<12}{'svc':>5}{'hộithoại':>10}{'gửi':>6}{'ghichú':>8}{'treo':>6}{'chặn':>6}"
          f"{'đơn':>5}{'tiền$':>8}{'FBchặn':>8}{'lỗi':>5}")
    for x in k["nuoc"] + [dict(t, ten="TỔNG", service={})]:
        s = x.get("service") or {}
        print(f"  {x['ten'][:11]:<12}{('ok' if s.get('chay') else ('—' if s.get('chay') is None else 'TẮT')):>5}"
              f"{x['hoi_thoai']:>10}{x['gui']:>6}{x['ghi_chu']:>8}{x['treo']:>6}{x['chan']:>6}"
              f"{x['don']:>5}{x['tien']:>8.2f}{x['fb_chan']:>8}{s.get('loi_gan', ''):>5}")
    for muc, c in k["canh"]:
        print(f"  {'🚨' if muc == 'nang' else '⚠️ '} {c}")
    sd = k["kimi"]["so_du"]
    if sd.get("co"):
        _tn = TEN_NHA.get(k["kimi"].get("nha"), "Nhà model")
        print(f"\n  {_tn} còn ${sd['con']:.2f} (đã nạp ${k['kimi']['nap']:.2f})")
    print()

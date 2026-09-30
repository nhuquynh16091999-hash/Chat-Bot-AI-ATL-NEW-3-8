#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Học BẢNG PHẢN XẠ CỦA BOTCAKE từ hội thoại thật — mục 12.2 trong LUAT_AI_SALE.md.

Vì sao cần: 49% hội thoại rơi vào cửa "Botcake đã trả lời — trúng hay lạc?". Không biết
Botcake bắt từ khoá nào thì AI phải đoán, đoán sai là nhắn đè lên câu bot đã trả lời đúng.

Cách làm: KHÔNG đọc cấu hình Botcake (nằm ở botcake.io, không mở API). Thay vào đó đo
HÀNH VI THẬT: quét hội thoại, ghép từng cặp (tin cuối của khách → tin Botcake ngay sau đó),
rồi gom theo nội dung câu bot. Kết quả đáng tin hơn cấu hình vì đúng cái bot ĐANG làm.

Đọc ra:
  · mỗi câu trả lời cố định của bot + những câu khách đã kích hoạt nó
  · những tin khách mà bot IM (không có phản xạ) -> đây là chỗ AI phải vào cuộc

Lệnh:
  python3 botcake.py hoc <thị trường> [--gio 72] [--so 30]   # quét & lưu state/<tt>/botcake.json
  python3 botcake.py xem <thị trường> [--it 2]               # in bảng phản xạ đã học
  python3 botcake.py im <thị trường>                         # in các tin khách mà bot IM
"""

import json
import os
import re
import sys
import time
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import ai_sale as A


def _state(mkey, f):
    return os.path.join(SCRIPT_DIR, "state", mkey, f)


def chuan(t):
    """Chuẩn hoá câu bot để gom nhóm: bỏ tên khách, số, khoảng trắng thừa."""
    t = re.sub(r"\s+", " ", (t or "")).strip()
    t = re.sub(r"\d+", "#", t)
    return t[:220]


def cmd_hoc(mkey, gio=72, so=30):
    tok = json.load(open(_state(mkey, "page_tokens.json"), encoding="utf-8"))
    pages = [(p, s) for p, s in tok.items() if s.get("token")]
    phan_xa = defaultdict(lambda: {"mau_bot": "", "kich_hoat": [], "so_lan": 0})
    bot_im, tong_conv, hong = [], 0, 0
    print(f"\n🔬 Học phản xạ Botcake — {mkey}, {len(pages)} page, {gio}h gần đây\n")
    for pid, st in pages:
        convs, err = A.hoi_thoai_gan_day(pid, st["token"], so=so, gio=gio)
        if err:
            hong += 1
            continue
        if not convs:
            continue
        n_page = 0
        for c in convs:
            msgs, _, e = A.tin_cua_hoi_thoai(pid, c["id"], st["token"])
            if e or not msgs:
                continue
            tong_conv += 1
            n_page += 1
            for i, m in enumerate(msgs):
                if m["boi"] != "khach":
                    continue
                sau = msgs[i + 1:]
                # tin đầu tiên của page sau câu khách này
                tra = next((x for x in sau if x["boi"] in ("botcake", "nguoi", "ai")), None)   # "ai" tách khỏi "nguoi" từ 14/09
                hoi = A.lam_sach(m["text"])
                if not hoi:
                    continue
                if tra is None or tra["boi"] != "botcake":
                    if tra is None:
                        bot_im.append({"page": st.get("name"), "khach": hoi[:160]})
                    continue
                k = chuan(tra["text"])
                if not k:
                    continue
                p = phan_xa[k]
                p["mau_bot"] = p["mau_bot"] or A.lam_sach(tra["text"])[:400]
                p["so_lan"] += 1
                if len(p["kich_hoat"]) < 12:
                    p["kich_hoat"].append(hoi[:120])
            time.sleep(0.05)
        print(f"  · {st.get('name','?')[:42]:44s} {n_page:3d} hội thoại", flush=True)
        time.sleep(0.05)

    out = {
        "thi_truong": mkey, "quet_luc": int(time.time()), "so_hoi_thoai": tong_conv,
        "phan_xa": sorted(phan_xa.values(), key=lambda x: -x["so_lan"]),
        "bot_im": bot_im[:400],
    }
    f = _state(mkey, "botcake.json")
    json.dump(out, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lap = [p for p in out["phan_xa"] if p["so_lan"] >= 2]
    print(f"\n💾 {f}")
    print(f"   {tong_conv} hội thoại | {len(out['phan_xa'])} câu bot khác nhau "
          f"({len(lap)} câu lặp ≥2 lần = phản xạ cố định) | {len(bot_im)} lượt bot IM")
    if hong:
        print(f"   ⚠ bỏ qua {hong} page token hỏng")


def cmd_xem(mkey, it=2):
    d = json.load(open(_state(mkey, "botcake.json"), encoding="utf-8"))
    px = [p for p in d["phan_xa"] if p["so_lan"] >= it]
    print(f"\n═══ Phản xạ Botcake — {mkey} ({d['so_hoi_thoai']} hội thoại, "
          f"{len(px)} phản xạ lặp ≥{it} lần) ═══\n")
    for p in px:
        print(f"── ({p['so_lan']} lần) BOT: {p['mau_bot'][:150]}")
        for k in p["kich_hoat"][:6]:
            print(f"     ← khách: {k}")
        print()


def cmd_im(mkey):
    d = json.load(open(_state(mkey, "botcake.json"), encoding="utf-8"))
    print(f"\n═══ Tin khách mà Botcake IM — {mkey} ({len(d['bot_im'])} lượt) ═══")
    print("   (đây là cửa AI phải trả lời — mục 0b)\n")
    for b in d["bot_im"][:80]:
        print(f"  [{(b['page'] or '?')[:26]:28s}] {b['khach']}")


def main():
    a = sys.argv[1:]
    g = lambda c, m: int(a[a.index(c) + 1]) if c in a else m
    if len(a) >= 2 and a[0] == "hoc":
        cmd_hoc(a[1], g("--gio", 72), g("--so", 30))
    elif len(a) >= 2 and a[0] == "xem":
        cmd_xem(a[1], g("--it", 2))
    elif len(a) >= 2 and a[0] == "im":
        cmd_im(a[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

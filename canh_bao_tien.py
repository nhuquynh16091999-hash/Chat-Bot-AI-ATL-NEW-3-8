# -*- coding: utf-8 -*-
"""TRẠM CANH TIỀN — nhắn cho chủ shop TRƯỚC khi AI Sale hết tiền và đứng.

Vì sao có file này: 5 lần hệ đứng vì hết tiền (17/09, 18/09, 19/09, 21/09…) đều do chủ shop
TỰ THẤY khách không được trả lời rồi mới biết. Phanh chống âm chạy đúng nhưng chỉ IN RA LOG,
không báo cho ai. File này chạy riêng (systemd timer, 5 phút/lần) nên vẫn báo được cả khi 6
service AI đã dừng.

Đo cái gì: `chi_phi.con_an_toan()` cho số tiền CÒN CHẮC (đã trừ phần tiêu chưa kịp lên bảng),
`chi_phi.chi_tu()` cho NHỊP TIÊU thật mấy giờ qua → còn đủ tiêu bao nhiêu GIỜ nữa trước khi
chạm sàn `AI_SO_DU_TOI_THIEU`. Nhịp lấy số LỚN NHẤT của 3 cửa sổ (1h/3h/24h) — hệ vừa bị dừng
thì 1h gần nhất tiêu $0, lấy trung bình sẽ ru ngủ.

Mức báo (đổi bằng .env, giờ):
    CANH_BAO_KHAN_GIO=6      còn dưới 6 giờ  → 🔴 khẩn
    CANH_BAO_SOM_GIO=24      còn dưới 24 giờ → 🟠 báo sớm
Đã chạm sàn (hệ đang đứng) → ⛔ báo ngay, nhắc lại mỗi CANH_BAO_NHAC_DUNG_PHUT (mặc định 60).
Nạp tiền xong, mức về an toàn → nhắn một câu "đã chạy lại" rồi im.

Gửi đi đâu: WhatsApp, dùng chung phiên đăng nhập của hệ aicloser (/opt/aicloser/src/wa.js).
Khai `CANH_BAO_WA_JID` trong .env (JID nhóm `...@g.us` hoặc số riêng `84xxxxxxxxx@s.whatsapp.net`).
Chưa khai thì vẫn chạy và ghi log, chỉ không gửi được.

Chạy tay:  python3 canh_bao_tien.py            (báo nếu tới ngưỡng)
           python3 canh_bao_tien.py --xem      (chỉ in tình hình, không gửi, không ghi sổ)
           python3 canh_bao_tien.py --thu      (gửi thử một tin để xem WhatsApp có tới không)
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import chi_phi                                          # noqa: E402

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "chung")
F_SO = os.path.join(STATE, "canh_bao_tien.json")
NODE_GUI = "/opt/aicloser/src/gui-canh-bao.js"
NOI_NAP = {"kimi": "platform.kimi.ai/console/account",
           "deepseek": "platform.deepseek.com/top_up"}


def _env():
    return chi_phi._env_file()


def _so(e, k, md):
    try:
        v = (e.get(k) or "").strip()
        return float(v) if v else md
    except (ValueError, AttributeError):
        return md


def gio_vn(t=None):
    """Giờ Việt Nam (VPS chạy giờ Berlin) — chủ shop đọc giờ VN."""
    return time.strftime("%H:%M %d/%m", time.localtime((t or time.time()) + 5 * 3600))


def nhip_tieu(nha):
    """Tiền tiêu MỖI GIỜ — lấy cửa sổ 'đói' nhất trong 1h/3h/24h gần đây."""
    gio = time.time()
    cac = []
    for h in (1, 3, 24):
        chi = chi_phi.chi_tu(gio - h * 3600, nha)
        if chi > 0:
            cac.append(chi / h)
    return max(cac) if cac else 0.0


def nhip_that(mau, con, gio_it_nhat=0.5):
    """Nhịp tiêu đo bằng SỐ DƯ THẬT tụt đi (sổ goi_model.jsonl đếm THIẾU — các bản thử trong
    /root dùng chung API key nhưng ghi sổ riêng). Bỏ qua đoạn có NẠP TIỀN (số dư đi lên)."""
    if con is None:
        return 0.0
    gio = time.time()
    dau = None
    for t, c in reversed(mau or []):                    # lùi dần, dừng ngay trước lần nạp gần nhất
        if c is None or c < con - 1e-9:                 # số dư từng THẤP hơn bây giờ = đã nạp
            break
        dau = (t, c)
    if not dau:
        return 0.0
    h = (gio - dau[0]) / 3600.0
    if h < gio_it_nhat:
        return 0.0
    return max(0.0, (dau[1] - con) / h)


def tinh(e=None):
    """Tình hình tiền lúc này: dict(nha, con, san, con_tieu, nhip, gio_con, muc)."""
    e = e or _env()
    nha = (e.get("AI_PROVIDER") or "kimi").strip().lower()
    san = _so(e, "AI_SO_DU_TOI_THIEU", 0.50)
    ca = chi_phi.con_an_toan(nha, e=e)
    con = float(ca.get("con") or 0) if ca.get("co") else None
    nhip_so = nhip_tieu(nha)
    nhip_sd = nhip_that((doc_so() or {}).get("mau") or [], con)
    nhip = max(nhip_so, nhip_sd)                        # cái nào ĐÓI hơn thì tin cái đó
    kq = dict(nha=nha, san=san, nhip=nhip, nhip_so=nhip_so, nhip_sd=nhip_sd,
              con=None, con_tieu=None, gio_con=None,
              loi=ca.get("loi") or ca.get("loi_api"))
    if not ca.get("co"):
        kq["muc"] = "mu"                                # không đọc được số dư → phanh chạy mù
        return kq
    con_tieu = con - san                                # phần còn được phép tiêu trước khi dừng
    kq.update(con=con, con_tieu=con_tieu,
              gio_con=(con_tieu / nhip) if nhip > 0 else None)
    khan = _so(e, "CANH_BAO_KHAN_GIO", 6)
    som = _so(e, "CANH_BAO_SOM_GIO", 24)
    if con <= san:
        kq["muc"] = "dung"
    elif kq["gio_con"] is not None and kq["gio_con"] <= khan:
        kq["muc"] = "khan"
    elif kq["gio_con"] is not None and kq["gio_con"] <= som:
        kq["muc"] = "som"
    else:
        kq["muc"] = "on"
    return kq


def _gio_chu(g):
    if g is None:
        return "chưa đo được nhịp tiêu"
    if g < 1:
        return f"~{int(g * 60)} phút nữa"
    if g < 48:
        return f"~{g:.1f} giờ nữa"
    return f"~{g / 24:.1f} ngày nữa"


def soan(t):
    """Câu nhắn cho chủ shop — ngắn, nói ngay phải làm gì."""
    nha = t["nha"].upper()
    nap = NOI_NAP.get(t["nha"], "trang nạp tiền của nhà model")
    if t["muc"] == "mu":
        return (f"⚠️ AI SALE — KHÔNG ĐỌC ĐƯỢC SỐ DƯ {nha} ({t.get('loi') or 'API không trả lời'}).\n"
                f"Phanh chống hết tiền đang chạy mù, có thể đứng mà không báo. Nhờ anh xem hộ bảng "
                f"{nap}.\n(lúc {gio_vn()})")
    if t["muc"] == "dung":
        return (f"⛔ AI SALE ĐÃ DỪNG — HẾT TIỀN {nha}.\n"
                f"Còn chắc ${t['con']:.2f} ≤ sàn dừng ${t['san']:.2f}. Khách nhắn tới KHÔNG ai trả lời "
                f"(tin vẫn giữ dấu chưa đọc cho sale).\n"
                f"👉 Nạp tại {nap} — nạp xong hệ TỰ chạy lại sau ~1 phút, không phải sửa gì.\n"
                f"(lúc {gio_vn()})")
    dau = "🔴 AI SALE SẮP DỪNG" if t["muc"] == "khan" else "🟠 AI SALE SẮP HẾT TIỀN"
    return (f"{dau} — {nha} còn ${t['con']:.2f}, tiêu ${t['nhip']:.2f}/giờ → hết "
            f"{_gio_chu(t['gio_con'])} là hệ tự dừng trả lời khách.\n"
            f"👉 Nạp trước tại {nap}.\n"
            f"(sàn dừng ${t['san']:.2f} · lúc {gio_vn()})")


def doc_so():
    try:
        return json.load(open(F_SO, encoding="utf-8"))
    except Exception:                                   # noqa: BLE001
        return {}


def ghi_so(d):
    os.makedirs(STATE, exist_ok=True)
    tam = F_SO + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tam, F_SO)


def gui_wa(text, e=None):
    """Gửi WhatsApp qua phiên của hệ aicloser. Trả (ok, lời lỗi)."""
    e = e or _env()
    jid = (e.get("CANH_BAO_WA_JID") or "").strip()
    if not jid:
        return False, "chưa khai CANH_BAO_WA_JID trong .env"
    if not os.path.exists(NODE_GUI):
        return False, f"thiếu {NODE_GUI}"
    moi = dict(os.environ, WA_JID=jid)
    try:
        r = subprocess.run(["node", NODE_GUI, text], cwd="/opt/aicloser", env=moi,
                           capture_output=True, text=True, timeout=120)
    except Exception as ex:                             # noqa: BLE001
        return False, str(ex)
    ra = (r.stdout or "").strip().splitlines()
    cuoi = ra[-1] if ra else ""
    if r.returncode == 0:
        return True, ""
    return False, (cuoi or (r.stderr or "").strip()[-200:] or f"node thoát mã {r.returncode}")


NHAC = {"dung": "CANH_BAO_NHAC_DUNG_PHUT", "khan": "CANH_BAO_NHAC_KHAN_PHUT",
        "som": "CANH_BAO_NHAC_SOM_PHUT", "mu": "CANH_BAO_NHAC_MU_PHUT"}
NHAC_MD = {"dung": 60, "khan": 60, "som": 360, "mu": 360}
NANG = {"on": 0, "som": 1, "mu": 2, "khan": 3, "dung": 4}


def nen_bao(t, so, e):
    """Có nhắn lượt này không, và vì sao (để ghi log)."""
    muc, truoc = t["muc"], so.get("muc") or "on"
    if muc == "on":
        return (bool(so.get("da_bao")), "đã nạp/đã ổn trở lại" if so.get("da_bao")
                else "vẫn ổn, không có gì để báo")
    if NANG[muc] > NANG[truoc]:
        return True, f"nặng thêm ({truoc} → {muc})"
    cho = _so(e, NHAC[muc], NHAC_MD[muc]) * 60
    lan = so.get("lan_bao") or 0
    if time.time() - lan >= cho:
        return True, f"nhắc lại sau {int((time.time() - lan) / 60)} phút"
    return False, "đã báo rồi, chưa tới hạn nhắc"


def main():
    e = _env()
    t = tinh(e)
    xem = "--xem" in sys.argv
    if "--thu" in sys.argv:
        ok, loi = gui_wa(f"🔔 Thử cảnh báo tiền AI Sale — {gio_vn()}. "
                         f"Nhận được tin này là kênh báo đã thông.", e)
        print("gửi thử:", "OK" if ok else f"HỎNG — {loi}")
        return 0 if ok else 1
    print(f"[{gio_vn()}] nhà {t['nha']} · còn chắc "
          f"{('$%.4f' % t['con']) if t['con'] is not None else '?'} · sàn ${t['san']:.2f} · "
          f"nhịp ${t['nhip']:.4f}/giờ (sổ {t.get('nhip_so') or 0:.4f} · số dư "
          f"{t.get('nhip_sd') or 0:.4f}) · còn {_gio_chu(t['gio_con'])} · MỨC {t['muc'].upper()}")
    if xem:
        if t["muc"] != "on":
            print("--- câu sẽ nhắn ---\n" + soan(t))
        return 0
    so = doc_so()
    # Ghi mẫu số dư MỖI LƯỢT (kể cả lượt không nhắn) — nhịp tiêu thật đo bằng chuỗi mẫu này.
    mau = [x for x in (so.get("mau") or []) if isinstance(x, list) and len(x) == 2
           and x[0] > time.time() - 26 * 3600]
    mau.append([time.time(), t["con"]])
    so["mau"] = mau[-400:]
    bao, vi_sao = nen_bao(t, so, e)
    if not bao:
        ghi_so(so)
        return 0
    if t["muc"] == "on":
        text = (f"✅ AI Sale chạy lại bình thường — {t['nha'].upper()} còn ${t['con']:.2f}, "
                f"đủ tiêu {_gio_chu(t['gio_con'])}. (lúc {gio_vn()})")
    else:
        text = soan(t)
    ok, loi = gui_wa(text, e)
    print(f"→ NHẮN ({vi_sao}): {'đã gửi WhatsApp' if ok else 'GỬI HỎNG — ' + loi}")
    print(text)
    so.update(muc=t["muc"], lan_bao=time.time() if ok else (so.get("lan_bao") or 0),
              da_bao=(t["muc"] != "on") and ok, con=t["con"], nhip=t["nhip"],
              gui_hong=None if ok else loi, luc=gio_vn())
    ghi_so(so)
    return 0


if __name__ == "__main__":
    sys.exit(main())

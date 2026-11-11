#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Giao diện web quản lý AI Sale — API JSON + một trang ứng dụng, chạy tại máy.

  python3 ai_sale.py dashboard usa --phuc-vu        (hoặc: python3 giao_dien.py usa)

Khác trang tĩnh `bang_dieu_khien.py` ở chỗ: trang này SỬA ĐƯỢC. Lưu là gọi API, không nạp lại
trang. Sửa được model, độ sáng tạo, trần chi, API key, và cả BỘ HƯỚNG DẪN gửi cho model.

Tám màn:
  Tổng quan · Page & kịch bản · Sổ cổng chặn · Hàng chờ sale
  Cấu hình · Hướng dẫn trả lời · Tiền nong · Đo lại
Bốn màn giữa (thêm 2026-09-08) đọc dữ liệu từ `quan_ly.py` và trả lời bốn câu phải trả lời
TRƯỚC khi cho AI gửi tin thật: page nào bật được · kịch bản page ra sao · cổng chặn đã chặn
gì · ca nào đang chờ người.

Máy chủ CHỈ nghe ở 127.0.0.1 và còn kiểm header Host — không ai ngoài mạng gọi vào được.
Trên VPS thì mở đường hầm:  ssh -L 8765:127.0.0.1:8765 root@<IP server>

Cố ý KHÔNG có ở đây:
  · nút gửi tin cho khách — gửi thật vẫn chỉ chạy bằng `ai_sale.py chay <tt> --that`
  · sửa PANCAKE_* — token hỏng là cả hệ thống lên đơn chết, phải làm có ý thức bằng tay
"""

import json
import os
import re
import sys
import threading
import urllib.parse
import time
import webbrowser

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import chi_phi
import bao_cao_tien
import bang_dieu_khien as BD
import quan_ly as QL

F_ENV = os.path.join(SCRIPT_DIR, ".env")

# Khoá được phép sửa từ giao diện. PANCAKE_* cố ý không có trong danh sách này.
KHOA_SUA = ["AI_PROVIDER", "AI_MODEL", "AI_TEMPERATURE",
            "AI_NGAN_SACH_NGAY", "AI_NGAN_SACH_TONG",
            "KIMI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]
KHOA_KEY = ("KIMI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY")


def ghi_env(thay):
    """Ghi đè vài khoá trong .env, GIỮ NGUYÊN mọi dòng khác kể cả chú thích.

    Bản cũ luôn chép sang .env.bak trước khi ghi — sửa nhầm còn đường lùi.
    """
    thay = {k: v for k, v in thay.items() if k in KHOA_SUA and v is not None}
    if not thay:
        return []
    cu = open(F_ENV, encoding="utf-8").read() if os.path.exists(F_ENV) else ""
    open(F_ENV + ".bak", "w", encoding="utf-8").write(cu)
    dong, da = [], set()
    for ln in cu.splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln)
        if m and m.group(1) in thay:
            da.add(m.group(1))
            dong.append(f"{m.group(1)}={thay[m.group(1)]}")
        else:
            dong.append(ln)
    con = [k for k in thay if k not in da]
    if con:
        dong.append("")
        dong += [f"{k}={thay[k]}" for k in con]
    open(F_ENV, "w", encoding="utf-8").write("\n".join(dong) + "\n")
    return sorted(thay)


# ───────────────────────── Dữ liệu cho giao diện ─────────────────────────

def trang_thai_bot(mkey):
    """Bot nước này GỬI THẬT hay CHẠY THỬ, service có chạy không — đọc thẳng file service (12/11/2026).

    Chủ shop cần nhìn một phát là biết bot có đang nhắn khách thật không; trước đây chỉ biết bằng SSH."""
    import subprocess
    if not mkey:
        return {}
    unit = "aisale-chat" if mkey == "uae" else f"aisale-chat-{mkey}"
    that = None
    try:
        with open(f"/etc/systemd/system/{unit}.service", encoding="utf-8") as f:
            that = any(ln.startswith("ExecStart=") and ln.rstrip().endswith("--that") for ln in f)
    except Exception:                                    # noqa: BLE001
        pass
    try:
        chay = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True,
                              timeout=3).stdout.strip()
    except Exception:                                    # noqa: BLE001
        chay = ""
    return {"unit": unit, "that": that, "chay": chay}


def du_lieu(mkey):
    import ai_sale as A
    import quet_hoi_thoai as q
    e = q.load_env()
    d = BD.thu_thap(mkey)
    cf = d["cf"]
    return {
        "mkey": mkey, "luc": d["luc"],
        "cf": {
            "nha": cf["nha"], "model": cf["model"], "model_env": e.get("AI_MODEL", ""),
            "khop_gia": cf["khop_gia"], "nhiet_do": cf["nhiet_do"],
            "ns_ngay": cf["ns_ngay"] or "", "ns_tong": cf["ns_tong"] or "",
            "co_key": {"kimi": bool(e.get("KIMI_API_KEY")),
                       "deepseek": bool(e.get("DEEPSEEK_API_KEY")),
                       "anthropic": bool(e.get("ANTHROPIC_API_KEY"))},
        },
        "db": d["db"],
        "so_page": d["so_page"], "so_page_bat": d["so_page_bat"],
        "cua": d["cua"],
        "hoi": d["hoi_tat"].most_common(9), "n_hoi": d["n_hoi_tat"],
        "tien": {"nap": d["nap"], "da_chi": d["da_chi"], "hom_nay": d["hom_nay"],
                 "so_du": bao_cao_tien.so_du_kimi(e),
                 "theo_ngay": d["theo_ngay"], "theo_page": d["theo_page"],
                 "co_chi": d["co_chi_that"]},
        "nap_ds": chi_phi.doc_nap()[-12:],
        "luat": A.tai_luat(),
        "luat_goc": A.LUAT_DU_PHONG,
        "bot": trang_thai_bot(mkey),
    }


DO = {"chay": False, "log": "", "xong": "", "gio": 24}

# Xem trước câu AI ĐỊNH gửi — chạy `ai_sale.py chay` ở chế độ THỬ (không có --that).
# Cố ý dùng đúng lệnh thật chứ không viết đường riêng: xem trước mà đi đường khác đường gửi
# thì cái xem được không bảo đảm là cái sẽ gửi.
THU = {"chay": False, "log": "", "xong": "", "page": ""}


def _chay_thu(mkey, pid, gio, so):
    import subprocess
    THU.update(chay=True, log="", xong="", page=pid or "mọi page")
    lenh = [sys.executable, "-u", "ai_sale.py", "chay", mkey, "--gio", str(gio), "--so", str(so)]
    if pid:
        lenh += ["--page", str(pid)]
    try:
        pr = subprocess.Popen(lenh, cwd=SCRIPT_DIR, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        for dong in pr.stdout:
            THU["log"] = (THU["log"] + dong)[-24000:]
        pr.wait()
        THU["xong"] = f"Xong lúc {time.strftime('%H:%M')} — KHÔNG gửi gì cho khách"
    except Exception as ex:                            # noqa: BLE001
        THU["xong"] = f"Hỏng: {ex}"
    finally:
        THU["chay"] = False


def _chay_do(mkey, gio):
    import subprocess
    DO.update(chay=True, log="", xong="", gio=gio)
    try:
        pr = subprocess.Popen([sys.executable, "-u", "ai_sale.py", "du_bao", mkey,
                               "--gio", str(gio), "--so", "40"],
                              cwd=SCRIPT_DIR, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        for dong in pr.stdout:
            DO["log"] = (DO["log"] + dong)[-9000:]
        pr.wait()
        DO["xong"] = f"Đo xong lúc {time.strftime('%H:%M')}"
    except Exception as ex:                        # noqa: BLE001
        DO["xong"] = f"Đo hỏng: {ex}"
    finally:
        DO["chay"] = False


# Đo hiệu suất (hieu_suat.py do): quét hội thoại thật trên API ~6 phút, chỉ đọc, không gọi model.
# Chạy đúng lệnh terminal, không viết đường riêng — số trên web phải là số terminal in ra.
HS = {"chay": False, "log": "", "xong": "", "tt": ""}


def _chay_hs(tt, gio, chay_that):
    import subprocess
    HS.update(chay=True, log="", xong="", tt=tt)
    lenh = [sys.executable, "-u", "hieu_suat.py", "do", tt, "--gio", str(gio), "--luong", "6"]
    if chay_that:
        lenh.append("--chay-that")
    try:
        pr = subprocess.Popen(lenh, cwd=SCRIPT_DIR, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        for dong in pr.stdout:
            HS["log"] = (HS["log"] + dong)[-30000:]
        pr.wait()
        HS["xong"] = f"Đo xong lúc {time.strftime('%H:%M')}"
    except Exception as ex:                            # noqa: BLE001
        HS["xong"] = f"Đo hỏng: {ex}"
    finally:
        HS["chay"] = False


def doc_hieu_suat(tt):
    f = os.path.join(SCRIPT_DIR, "state", tt, "hieu_suat.json")
    if not os.path.exists(f):
        return None
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:                                  # noqa: BLE001
        return None


def kiem_key():
    """Gọi model ĐÚNG MỘT lượt cực ngắn để biết key có thật sự dùng được không.

    Có tốn tiền, nhưng cỡ vài phần nghìn xu — rẻ hơn nhiều so với nạp tiền rồi mới phát hiện
    key hỏng. Trả cả số token thật đo được, đây là con số thật đầu tiên thay cho ước lượng.
    """
    import ai_sale as A
    nha, key, _u, model, _d = A.nha_cung_cap()
    if not key:
        return {"ok": False, "loi": f"chưa dán key cho {nha}"}
    qd, err = A.soan_bang_model(
        'Trả lời đúng JSON này, không thêm gì: '
        '{"hanh_dong":"im","tin_nhan":"","ghi_chu":"","ly_do":"thử key"}')
    g = dict(A.LAN_GOI_CUOI)
    return {"ok": bool(qd), "loi": err or "", "nha": nha, "model": model,
            "token": g, "tien": g.get("tien", 0)}


# ───────────────────────── Trang ứng dụng ─────────────────────────

TRANG = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Sale — Bảng điều khiển</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;600&display=swap">
<link rel="icon" href="/logo.png">
<meta name="theme-color" content="#FFFFEF">
<style>
/* ═══ Giao diện theo app ANTALO (12/11/2026) ═══════════════════════════════════════════
   Màu lấy từ logo ANTALO (giống dashboard-ui/tailwind.config.ts của app Antalo):
     đỏ #FF3131 · xanh lá #00BF63 · cam #FF7312 · nền kem #FFFFEF · đen ấm #221F1B
   Tên biến giữ nguyên như bản cũ (--nen, --mat, --nhan…) để mọi màn đang dùng tự đổi màu:
     --nhan = TỐT (xanh lá) · --canh = CHÚ Ý (cam) · --nang = NẶNG (đỏ).
   Chữ xanh/cam/đỏ dùng bậc đậm (700) cho đủ tương phản trên nền trắng; mảng màu (thanh,
   chấm, cột) dùng đúng màu logo (--xanh, --cam, --do). */
:root{
  --nen:#FFFFEF; --mat:#FFFFFF; --muc:#221F1B; --nhat:#6E6A5E; --vien:#EBE9E0; --mo:#F6F5EE;
  --nhan:#008545; --nhan-mo:#E8FCF3; --nhan-vien:#97F7C8;
  --canh:#AE5313; --canh-mo:#FFF3EB; --canh-vien:#FDCCAA;
  --nang:#C01B1B; --nang-mo:#FFF0F0; --nang-vien:#FDC3C3;
  --canh-ben:#FFFFFF; --chon:#FFF3EB; --luot:#FAF9F4;
  --xanh:#00BF63; --cam:#FF7312; --do:#FF3131;
  --grad:linear-gradient(135deg,#FF3131,#FF7312);
  --bong:0 1px 2px rgba(34,31,27,.06),0 1px 3px rgba(34,31,27,.04);
  --bong-to:0 4px 14px rgba(34,31,27,.08);
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --nen:#131210; --mat:#1B1A17; --muc:#F6F5EE; --nhat:#A8A491; --vien:#2E2C27; --mo:#24221E;
  --nhan:#3BDB8E; --nhan-mo:#11261B; --nhan-vien:#1F5A3B;
  --canh:#FFA060; --canh-mo:#2A1D12; --canh-vien:#5C3A1E;
  --nang:#FF7070; --nang-mo:#2C1716; --nang-vien:#5E2523;
  --canh-ben:#131210; --chon:#2A1D12; --luot:#211F1B;
  --xanh:#00D670; --cam:#FF9042; --do:#FF5252;
  --grad:linear-gradient(135deg,#FF5252,#FF9042);
  --bong:none; --bong-to:0 4px 18px rgba(0,0,0,.35);
  color-scheme:dark;
}}
:root[data-theme="dark"]{
  --nen:#131210; --mat:#1B1A17; --muc:#F6F5EE; --nhat:#A8A491; --vien:#2E2C27; --mo:#24221E;
  --nhan:#3BDB8E; --nhan-mo:#11261B; --nhan-vien:#1F5A3B;
  --canh:#FFA060; --canh-mo:#2A1D12; --canh-vien:#5C3A1E;
  --nang:#FF7070; --nang-mo:#2C1716; --nang-vien:#5E2523;
  --canh-ben:#131210; --chon:#2A1D12; --luot:#211F1B;
  --xanh:#00D670; --cam:#FF9042; --do:#FF5252;
  --grad:linear-gradient(135deg,#FF5252,#FF9042);
  --bong:none; --bong-to:0 4px 18px rgba(0,0,0,.35);
  color-scheme:dark;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--nen);color:var(--muc);font-size:14.5px;line-height:1.6;
  font-family:"Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  -webkit-font-smoothing:antialiased;font-feature-settings:"calt" 1}
.so{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

/* ── Khung ứng dụng: thanh bên trắng + cột nội dung (thanh trên dính + nội dung) ── */
#app{display:grid;grid-template-columns:256px minmax(0,1fr);min-height:100%}
aside{background:var(--canh-ben);border-right:1px solid var(--vien);box-shadow:var(--bong);
  display:flex;flex-direction:column;position:sticky;top:0;height:100vh;z-index:20}
.hieu{padding:16px;border-bottom:1px solid var(--vien);display:flex;flex-direction:column;gap:10px}
.logo{display:flex;align-items:center;gap:11px;background:#FFFFEF;border:1px solid var(--vien);
  border-radius:12px;padding:9px 11px}
.logo img{width:34px;height:34px;object-fit:contain;flex:0 0 auto}
.logo b{display:block;font-size:15.5px;font-weight:800;letter-spacing:-.01em;color:#221F1B;line-height:1.2}
.logo small{display:block;font-size:11px;font-weight:600;color:#8A8675;letter-spacing:.02em}
#pv{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--nhat)}
#pv select{font:inherit;font-size:12.5px;font-weight:600;color:var(--muc);background:var(--mo);
  border:1px solid var(--vien);border-radius:8px;padding:4px 8px;max-width:150px}
nav{flex:1 1 auto;min-height:0;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:2px}
nav .nhom{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:var(--nhat);padding:12px 12px 5px;opacity:.85}
nav .nhom:first-child{padding-top:2px}
nav button{all:unset;box-sizing:border-box;cursor:pointer;display:flex;align-items:center;gap:11px;
  width:100%;padding:9px 12px;border-radius:10px;border:1px solid transparent;font-size:14px;
  font-weight:600;color:var(--nhat);transition:background .15s,color .15s}
nav button .ic{width:20px;text-align:center;font-size:15px;flex:0 0 auto}
nav button .ten{flex:1 1 auto}
nav button:hover{background:var(--luot);color:var(--muc)}
nav button[aria-current="page"]{background:linear-gradient(90deg,var(--canh-mo),var(--nang-mo));
  border-color:var(--canh-vien);color:var(--canh);box-shadow:var(--bong)}
nav button:focus-visible{outline:2px solid var(--cam);outline-offset:1px}
nav button .cham{width:7px;height:7px;border-radius:50%;background:var(--cam);flex:0 0 auto}
.trangthai{border-top:1px solid var(--vien);padding:12px}
.trangthai .hop-tt{background:var(--mo);border-radius:10px;padding:10px 12px;display:flex;
  flex-direction:column;gap:5px;font-size:12px;color:var(--nhat)}
.trangthai .hop-tt div{display:flex;justify-content:space-between;gap:8px}
.trangthai b{color:var(--muc);font-weight:700}

.cot{min-width:0;display:flex;flex-direction:column}
header#dau{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:12px;min-height:60px;
  padding:10px 28px;background:color-mix(in srgb,var(--mat) 82%,transparent);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--vien);
  box-shadow:var(--bong)}
#mo_menu{display:none}
.vet{display:flex;align-items:center;gap:8px;min-width:0;font-size:13px;color:var(--nhat)}
.vet b{font-size:17px;font-weight:700;color:var(--muc);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vet .ic{font-size:18px}
header .phai{margin-left:auto;display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}
.pill{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:700;padding:5px 12px;
  border-radius:999px;border:1px solid var(--vien);background:var(--mat);white-space:nowrap}
.pill i{width:8px;height:8px;border-radius:50%;background:var(--nhat);flex:0 0 auto}
.pill.that{background:var(--nhan-mo);border-color:var(--nhan-vien);color:var(--nhan)}
.pill.that i{background:var(--xanh);box-shadow:0 0 0 3px color-mix(in srgb,var(--xanh) 25%,transparent);
  animation:nhip 2s ease-in-out infinite}
.pill.thu{background:var(--canh-mo);border-color:var(--canh-vien);color:var(--canh)}
.pill.thu i{background:var(--cam)}
.pill.tat{background:var(--nang-mo);border-color:var(--nang-vien);color:var(--nang)}
.pill.tat i{background:var(--do)}
@keyframes nhip{50%{box-shadow:0 0 0 6px color-mix(in srgb,var(--xanh) 0%,transparent)}}
.nut-tron{all:unset;cursor:pointer;width:34px;height:34px;border-radius:10px;display:grid;place-items:center;
  border:1px solid var(--vien);background:var(--mat);font-size:15px}
.nut-tron:hover{background:var(--luot)}
.nut-tron:focus-visible{outline:2px solid var(--cam);outline-offset:1px}

main{padding:26px 28px 70px;max-width:1240px;width:100%}
/* Tổng quan (báo cáo cho sếp) mở hết chiều rộng — chủ shop 13/09: "không muốn phải kéo sang" */
main.rong{max-width:none}
main.rong th,main.rong td{padding:9px 11px;font-size:13.5px}
main.rong td:first-child{white-space:normal;min-width:180px}
main.rong .cuon table{width:100%}
.dau-trang{display:flex;flex-direction:column;gap:6px;margin-bottom:22px}
h1{font-size:23px;font-weight:800;letter-spacing:-.02em;margin:0;line-height:1.25;text-wrap:balance}
h2{font-size:16px;font-weight:700;letter-spacing:-.005em;color:var(--muc);margin:0 0 12px;
  display:flex;align-items:center;gap:8px}
h2::before{content:"";width:4px;height:16px;border-radius:2px;background:var(--grad);flex:0 0 auto}
p{margin:0}.phu{color:var(--nhat);font-size:13.5px}
section{margin-bottom:28px}
a{color:var(--canh);font-weight:600}

/* ── Thẻ & lưới số (kiểu ô KPI của Antalo) ── */
.the-lon{background:var(--mat);border:1px solid var(--vien);border-radius:14px;padding:22px 24px;
  box-shadow:var(--bong);display:flex;flex-direction:column;gap:18px;position:relative;overflow:hidden}
.the-lon::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--grad)}
.doi{display:flex;flex-wrap:wrap;gap:26px}
.o{flex:1 1 190px;display:flex;flex-direction:column;gap:2px}
.nhan-o{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--nhat);font-weight:700}
.to{font-size:28px;font-weight:800;letter-spacing:-.025em;line-height:1.15;font-variant-numeric:tabular-nums}
.to.xanh{color:var(--nhan)}
.ghi{font-size:12.5px;color:var(--nhat)}

.luoi{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:12px}
.the{background:var(--mat);border:1px solid var(--vien);border-radius:12px;padding:14px 17px;
  box-shadow:var(--bong);display:flex;flex-direction:column;gap:3px;transition:box-shadow .15s}
.the:hover{box-shadow:var(--bong-to)}
.the .so-to{font-size:24px;font-weight:800;letter-spacing:-.025em;line-height:1.2;font-variant-numeric:tabular-nums}

/* ── Bảng ── */
.cuon{overflow-x:auto;border:1px solid var(--vien);border-radius:12px;background:var(--mat);box-shadow:var(--bong)}
/* Bảng nhiều cột được phép tràn khỏi cột đọc để khỏi phải kéo ngang (xem ghi chú bản cũ). */
.cuon.rong{width:max-content;min-width:100%;max-width:calc(100vw - 320px)}
.cuon.rong th,.cuon.rong td{padding-left:11px;padding-right:11px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:right;padding:10px 14px;border-bottom:1px solid var(--vien);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--nhat);
  font-weight:700;background:var(--mo);position:sticky;top:0}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--luot)}
tr.chon td{background:var(--chon);font-weight:600}
.chip{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.03em;
  text-transform:uppercase;padding:2px 8px;border-radius:999px;margin-left:8px;
  background:var(--nhan-mo);color:var(--nhan)}

/* ── Form ── */
.hop{background:var(--mat);border:1px solid var(--vien);border-radius:14px;padding:22px;box-shadow:var(--bong)}
.hang{display:grid;grid-template-columns:repeat(auto-fit,minmax(212px,1fr));gap:17px}
label{display:flex;flex-direction:column;gap:5px;font-size:13px;font-weight:600}
label .gt{font-weight:400;color:var(--nhat);font-size:12.5px}
input,select,textarea{font-family:inherit;font-size:14px;color:var(--muc);background:var(--mat);
  border:1px solid var(--vien);border-radius:10px;padding:8px 11px;width:100%}
input[type=number],input[type=text],input[type=password],textarea{
  font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:13.5px}
textarea{line-height:1.65;resize:vertical;min-height:420px;font-size:13px}
input:focus-visible,select:focus-visible,textarea:focus-visible,button:focus-visible{
  outline:2px solid var(--cam);outline-offset:1px}
.nut{font-family:inherit;font-size:14px;font-weight:700;color:#fff;background:var(--grad);
  border:1px solid transparent;border-radius:10px;padding:9px 18px;cursor:pointer;box-shadow:var(--bong);
  transition:filter .15s,box-shadow .15s}
.nut:hover{filter:brightness(1.05);box-shadow:var(--bong-to)}
.nut.vien{background:var(--mat);color:var(--muc);border-color:var(--vien)}
.nut.nhe{background:transparent;color:var(--nhat);border-color:var(--vien);box-shadow:none}
.nut:disabled{opacity:.45;cursor:default;filter:none}
.thanh-nut{display:flex;gap:10px;align-items:center;margin-top:19px;flex-wrap:wrap}

/* ── Hộp thông báo ── */
.canh-bao,.tot,.xau{border-radius:12px;padding:12px 16px;font-size:13.5px;font-weight:600;border:1px solid}
.canh-bao{background:var(--canh-mo);color:var(--canh);border-color:var(--canh-vien)}
.tot{background:var(--nhan-mo);color:var(--nhan);border-color:var(--nhan-vien)}
.xau{background:var(--nang-mo);color:var(--nang);border-color:var(--nang-vien)}
.trong{background:var(--mat);border:1px dashed var(--vien);border-radius:12px;padding:22px;
  color:var(--nhat);font-size:14px;text-align:center}
code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;background:var(--mo);
  border:1px solid var(--vien);border-radius:6px;padding:1px 6px}
pre.log{background:var(--mat);border:1px solid var(--vien);border-radius:12px;padding:15px;
  font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;line-height:1.55;
  max-height:400px;overflow:auto;white-space:pre-wrap;margin:0}

/* Bậc sẵn sàng — màu mã hoá mức nghiêm trọng, không phải trang trí */
.bac{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;
  letter-spacing:.03em;text-transform:uppercase;padding:3px 9px;border-radius:999px;white-space:nowrap}
.bac0{background:var(--nang-mo);color:var(--nang);box-shadow:inset 0 0 0 1px var(--nang-vien)}
.bac1{background:var(--nang-mo);color:var(--nang)}
.bac2{background:var(--canh-mo);color:var(--canh)}
.bac3{background:var(--canh-mo);color:var(--canh);opacity:.85}
.bac4{background:var(--nhan-mo);color:var(--nhan)}
tbody tr.bam{cursor:pointer}
tbody tr.bam:hover td{background:var(--chon)}
td.trai,th.trai{text-align:left}
.loc{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.loc button{all:unset;cursor:pointer;font-size:12.5px;font-weight:600;color:var(--nhat);
  padding:6px 13px;border-radius:999px;border:1px solid var(--vien);background:var(--mat);transition:background .15s}
.loc button:hover{background:var(--luot);color:var(--muc)}
.loc button[aria-pressed="true"]{background:linear-gradient(90deg,var(--canh-mo),var(--nang-mo));
  color:var(--canh);border-color:var(--canh-vien)}
.loc button:focus-visible{outline:2px solid var(--cam);outline-offset:1px}
.mau{border:1px solid var(--vien);border-radius:12px;background:var(--mat);padding:14px 16px;
  margin-bottom:10px;box-shadow:var(--bong)}
.mau .tk{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:600;color:var(--canh)}
.mau .noi{font-size:13.5px;white-space:pre-wrap;margin-top:7px;color:var(--muc);max-height:190px;overflow:auto}
.mau .meta{font-size:11.5px;color:var(--nhat);margin-top:6px}
.sos{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.sos span{font-variant-numeric:tabular-nums;font-size:12px;font-weight:600;background:var(--mo);
  border:1px solid var(--vien);border-radius:999px;padding:1px 9px}
.viec{border:1px solid var(--vien);border-left:4px solid var(--cam);border-radius:12px;
  background:var(--mat);padding:14px 16px;margin-bottom:10px;box-shadow:var(--bong)}
.viec.chan{border-left-color:var(--do)}
.viec .dinh{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:13px;font-weight:700}
.viec .gcv{font-size:13px;color:var(--nhat);margin-top:6px;white-space:pre-wrap}
.viec .cau{font-size:13px;margin-top:6px;padding:9px 12px;background:var(--mo);border-radius:10px;border:1px solid var(--vien)}

/* Toàn cảnh — main.toan co lại được, bảng rộng cuộn trong khung chứ không đẩy cả trang */
main.toan{min-width:0}
main.toan .luoi{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}
main.toan td .ghi{white-space:nowrap}
main.toan th,main.toan td{padding-left:9px;padding-right:9px}
.hai-dong{display:block;font-size:11.5px;color:var(--nhat);font-weight:500}
.tc-dong{cursor:pointer}
.tc-dong:hover td{background:var(--chon)}
.den{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;vertical-align:1px}
.den.chay{background:var(--xanh)}.den.tat{background:var(--do)}.den.cham{background:var(--cam)}
.kc{display:flex;gap:2px;height:10px;width:120px;min-width:120px}
.kc i{display:block;height:100%;border-radius:3px;min-width:2px}
.kc .g{background:var(--xanh)}.kc .n{background:var(--cam)}.kc .t{background:var(--nhat)}.kc .c{background:var(--do)}
.chu-giai{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--nhat);margin-top:9px}
.chu-giai span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:3px;
  margin-right:6px;vertical-align:-1px;background:var(--mau)}
.sparks{display:block;width:120px;height:18px;margin-top:5px}
.sparks rect{fill:var(--xanh)}
tr.tong td{font-weight:700;background:var(--mo)}
.hai-cot{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:22px}
.feed{display:flex;flex-direction:column;border:1px solid var(--vien);border-radius:12px;
  background:var(--mat);max-height:640px;overflow:auto;box-shadow:var(--bong)}
.feed div.m{display:grid;grid-template-columns:52px 118px 1fr;gap:10px;padding:11px 14px;
  border-bottom:1px solid var(--vien);font-size:13px;align-items:start}
.feed div.m:hover{background:var(--luot)}
.feed div.m:last-child{border-bottom:none}
.feed .ai{color:var(--nhat);font-size:12px;font-weight:600}
/* Câu AI gửi: cho xuống 2 dòng thay vì cắt cụt một dòng — chủ shop cần ĐỌC được AI nói gì */
.feed .cau{color:var(--muc);white-space:normal;overflow:hidden;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical;margin-top:2px}
.nhan-kc{font-size:10.5px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
  padding:2px 8px;border-radius:999px;white-space:nowrap}
.nhan-kc.gui{background:var(--nhan-mo);color:var(--nhan)}
.nhan-kc.ghi_chu,.nhan-kc.gui_hong{background:var(--canh-mo);color:var(--canh)}
.nhan-kc.treo{background:var(--mo);color:var(--nhat);box-shadow:inset 0 0 0 1px var(--vien)}
.nhan-kc.chan{background:var(--nang-mo);color:var(--nang)}
.canh-ds{display:flex;flex-direction:column;gap:8px}

/* Thanh câu hỏi */
.thanhds{display:flex;flex-direction:column;gap:9px}
.dong{display:grid;grid-template-columns:1fr 46px;gap:12px;align-items:center}
.ray{height:8px;background:var(--mo);border-radius:999px;overflow:hidden;margin-top:5px}
.ray i{display:block;height:100%;background:var(--grad);border-radius:999px}
.pt{font-size:13px;color:var(--nhat);text-align:right}

/* Thông báo nổi */
#bao{position:fixed;right:20px;bottom:20px;display:flex;flex-direction:column;gap:9px;z-index:50}
.bao-mot{background:var(--muc);color:var(--nen);padding:11px 17px;border-radius:12px;
  font-size:13.5px;font-weight:600;box-shadow:var(--bong-to);animation:vao .18s ease-out}
.bao-mot.xau{background:var(--nang);color:#fff}
@keyframes vao{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.quay{display:inline-block;width:13px;height:13px;border:2px solid currentColor;
  border-right-color:transparent;border-radius:50%;animation:xoay .7s linear infinite;
  vertical-align:-2px;margin-right:7px}
@keyframes xoay{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.bao-mot,.pill.that i{animation:none}}

/* ── Điện thoại: thanh bên thành ngăn kéo, mở bằng nút ☰ ── */
#man{display:none}
@media(max-width:860px){
  #app{grid-template-columns:minmax(0,1fr)}
  aside{position:fixed;inset:0 auto 0 0;width:280px;max-width:85vw;transform:translateX(-102%);
    transition:transform .2s ease;box-shadow:var(--bong-to)}
  body.mo-menu aside{transform:none}
  body.mo-menu #man{display:block;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:15}
  #mo_menu{display:grid}
  header#dau{padding:10px 16px}
  .vet>span{display:none}
  main{padding:18px 16px 60px}
  .cuon.rong{width:auto;max-width:100%}
  .feed div.m{grid-template-columns:44px 1fr}
  .feed div.m>span:nth-child(2){grid-column:2}
  .feed div.m>div{grid-column:1/-1}
  #capnhat{display:none}
}
</style></head><body>
<div id="app">
  <aside>
    <div class="hieu">
      <div class="logo"><img src="/logo.png" alt="" onerror="this.remove()">
        <div><b>AI Sale</b><small>ANTALO · chat bán hàng</small></div></div>
      <div id="pv">đang tải…</div>
    </div>
    <nav id="nav"></nav>
    <div class="trangthai" id="tt"></div>
  </aside>
  <div class="cot">
    <header id="dau">
      <button class="nut-tron" id="mo_menu" aria-label="Mở menu">☰</button>
      <div class="vet"><span>AI Sale ›</span><span class="ic" id="ic_tab"></span><b id="ten_tab">Đang tải…</b></div>
      <div class="phai"><span id="pill"></span><span class="ghi so" id="capnhat"></span>
        <button class="nut-tron" id="doi_nen" title="Đổi nền sáng / tối" aria-label="Đổi nền sáng tối">🌓</button></div>
    </header>
    <main id="main"><p class="phu">Đang tải…</p></main>
  </div>
</div>
<div id="man"></div>
<div id="bao"></div>
<script>
const $ = s => document.querySelector(s);
const H = s => String(s==null?'':s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n0 = x => Math.round(x).toLocaleString('en-US');
const usd = x => !x ? '$0'
  : '$' + (Math.abs(x) >= 10 ? n0(x) : x.toFixed(Math.abs(x) < 1 ? 4 : 2));
const kr = (a,b) => b < 10 ? `$${a.toFixed(2)}–${b.toFixed(2)}` : `$${n0(a)}–${n0(b)}`;

let S = null, TAB = 'toan', BAN = false, TIMER = null, TC_GIO = 24, TC_HEN = null;
let PAGE = null, PCHON = null, LOC = -1, CHAN = null, CHO = null;
const TABS = [['toan','Toàn cảnh'],['tong','Tổng quan'],['page','Page & kịch bản'],['chan','Sổ cổng chặn'],
              ['hangcho','Hàng chờ sale'],['cauhinh','Cấu hình'],['luat','Hướng dẫn trả lời'],
              ['tien','Tiền nong'],['hieusuat','Hiệu suất'],['do','Đo lại']];
/* 12/11/2026 — thanh bên kiểu app ANTALO: biểu tượng + nhóm */
const ICON = {toan:'🌏', tong:'📋', page:'📄', chan:'🛡️', hangcho:'🙋', cauhinh:'⚙️', luat:'📝',
              tien:'💰', hieusuat:'📈', do:'🔁'};
const NHOM = [['Theo dõi', ['toan','tong','hangcho','chan']], ['Thiết lập', ['page','luat','cauhinh']],
              ['Chi phí & đo', ['tien','hieusuat','do']]];
const TEN_TAB = Object.fromEntries(TABS);
/* Nền sáng / tối: nhớ trên máy này (lỗi bộ nhớ trình duyệt thì thôi, vẫn chạy) */
(function(){
  try{ const t = localStorage.getItem('aisale_nen'); if(t) document.documentElement.dataset.theme = t; }catch(e){}
  document.addEventListener('click', ev => {
    if(ev.target.closest('#doi_nen')){
      const r = document.documentElement, toi = r.dataset.theme ? r.dataset.theme === 'dark'
        : matchMedia('(prefers-color-scheme: dark)').matches;
      r.dataset.theme = toi ? 'light' : 'dark';
      try{ localStorage.setItem('aisale_nen', r.dataset.theme); }catch(e){}
    }
    if(ev.target.closest('#mo_menu')) document.body.classList.add('mo-menu');
    if(ev.target.closest('#man') || ev.target.closest('nav button')) document.body.classList.remove('mo-menu');
  });
})();
/* Bot đang GỬI THẬT hay CHẠY THỬ — đọc từ file service trên máy chủ (S.bot) */
function veTrangThaiBot(){
  const b = S.bot || {};
  const [lop, chu] = b.chay && b.chay !== 'active' ? ['tat', 'Bot đang tắt']
    : b.that === true ? ['that', 'Đang gửi thật'] : b.that === false ? ['thu', 'Chạy thử — chưa gửi khách']
    : ['', 'Không rõ trạng thái bot'];
  $('#pill').innerHTML = `<span class="pill ${lop}" title="${H(b.unit || '')}"><i></i>${chu}</span>`;
}
const BACTEN = ['token hỏng','chưa có kịch bản','chưa có SKU','chưa có giá sàn','đủ'];

function bao(t, xau){
  const d = document.createElement('div');
  d.className = 'bao-mot' + (xau ? ' xau' : ''); d.textContent = t;
  $('#bao').append(d); setTimeout(() => d.remove(), 4200);
}
let TT = '';                       // thị trường đang xem; rỗng = cái mở lúc đầu
async function api(du, than){
  if(!than && TT){ du += (du.includes('?') ? '&' : '?') + 'tt=' + encodeURIComponent(TT); }
  const r = await fetch('/api/' + du, than ? {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(than)} : {});
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}
async function tai(){ S = await api('du-lieu'); ve(); }

/* Tiền mỗi tháng cho một model bất kỳ, tính ngay trên trình duyệt từ số token đo được */
function tinh(ma, luot_ngay, dem){
  const g = S.db && S.db.gia[ma]; if(!g || !S.db) return null;
  const [gv, gd, , gr] = g, {tok_lap:L, tok_moi:M, ra_token:R} = S.db;
  return [0,1].map(i => ((dem ? L[i]*gd : L[i]*gv) + M[i]*gv + R*gr) / 1e6 * luot_ngay * 30);
}
const khoaGia = m => Object.keys(S.db ? S.db.gia : {}).sort((a,b)=>b.length-a.length)
  .find(k => (m||'').startsWith(k));

/* Tên nhà model đang chạy. 20/09 chủ shop đổi Kimi → DeepSeek mà mọi ô tiền vẫn ghi cứng
   "Kimi còn" — nhìn là tưởng hỏng. Nhãn nay đi theo AI_PROVIDER trong .env. */
const TEN_NHA = {kimi:'Kimi', deepseek:'DeepSeek', anthropic:'Claude'};
const NT = n => { const x = String(n || (S.cf && S.cf.nha) || '').toLowerCase();
  return TEN_NHA[x] || (x ? x[0].toUpperCase() + x.slice(1) : 'nhà model'); };

function chuyen(t){
  if(BAN && !confirm('Còn thay đổi chưa lưu. Rời đi và bỏ thay đổi?')) return;
  BAN = false; TAB = t; ve();
}
function ve(){
  $('#pv').innerHTML = `<span>Thị trường</span><select id="chontt" aria-label="Chọn thị trường"></select>`;
  $('#ic_tab').textContent = ICON[TAB] || '';
  $('#ten_tab').textContent = TEN_TAB[TAB] || '';
  $('#capnhat').textContent = S.luc ? 'cập nhật ' + S.luc : '';
  veTrangThaiBot();
  (async () => {
    const t = await (await fetch('/api/thi-truong')).json();
    const sel = $('#chontt'); if(!sel) return;
    sel.innerHTML = t.ds.map(x =>
      `<option value="${x.tt}"${(TT||S.mkey)===x.tt?' selected':''}>${H(x.ten || x.tt)}</option>`
    ).join('');
    sel.onchange = async () => {
      TT = sel.value; PAGE = null; PCHON = null; LOC = -1; CHAN = null; CHO = null;
      bao('Đang đổi sang ' + TT + '…');
      await tai();
    };
  })();
  $('#nav').innerHTML = NHOM.map(([ten, ds]) => `<div class="nhom">${ten}</div>` + ds.map(k =>
    `<button data-t="${k}"${TAB===k?' aria-current="page"':''}><span class="ic" aria-hidden="true">${ICON[k]}</span>`
    + `<span class="ten">${TEN_TAB[k]}</span>`
    + (k==='cauhinh' && cangBao() ? '<span class="cham" title="cấu hình còn thiếu"></span>' : '')
    + (k==='do' && S.dochay ? '<span class="cham" title="đang đo"></span>' : '') + '</button>').join('')).join('');
  $('#nav').querySelectorAll('button').forEach(b =>
    b.onclick = () => chuyen(b.dataset.t));
  const c = S.cf;
  $('#tt').innerHTML = '<div class="hop-tt">' + [
    ['Model', H(c.model)],
    ['Sáng tạo', c.nhiet_do==null ? 'mặc định 1.0' : c.nhiet_do],
    ['Trần ngày', c.ns_ngay ? usd(+c.ns_ngay) : 'không có'],
    ['Key', c.co_key[c.nha] ? 'đã dán' : 'THIẾU'],
  ].map(([a,b]) => `<div><span>${a}</span><b>${b}</b></div>`).join('') + '</div>';
  $('#main').classList.toggle('rong', TAB === 'tong' || TAB === 'toan');
  $('#main').classList.toggle('toan', TAB === 'toan');
  $('#main').innerHTML = ({toan:veToan, tong:veTong, page:vePage, chan:veChan, hangcho:veCho,
                           cauhinh:veCauHinh, luat:veLuat, tien:veTien, do:veDo, hieusuat:veHS})[TAB]();
  ({toan:sauToan, cauhinh:sauCauHinh, luat:sauLuat, tien:sauTien, do:sauDo, tong:sauTong,
    page:sauPage, chan:sauChan, hangcho:sauCho, hieusuat:sauHS}[TAB] || (()=>{}))();
}
const cangBao = () => !S.cf.co_key[S.cf.nha] || !(S.cf.ns_ngay || S.cf.ns_tong)
  || S.cf.nhiet_do == null;

/* ═══════════════════════════════════════════════════════════════════════
   MÀN: TOÀN CẢNH CÁC NƯỚC  (chủ shop 14/09: "đừng bắt tôi ấn từng nước")
   Một bảng mọi thị trường + việc cần người + việc AI vừa làm. Số đọc từ sổ trên
   đĩa (toan_canh.py), không gọi model. Bấm một nước để vào báo cáo riêng nước đó.
   ═══════════════════════════════════════════════════════════════════════ */
const KC_TEN = {gui:'tới khách', ghi_chu:'vào ghi chú', gui_hong:'gửi hỏng', treo:'treo cho sale', chan:'cổng chặn giữ', khac:'khác'};
function veToan(){
  return `<div id="tc"><p class="phu"><span class="quay"></span>Đang gộp sổ của mọi nước…</p></div>`;
}
function gioChu(g){ return g < 48 ? g + ' giờ' : Math.round(g/24) + ' ngày'; }
function tuoi(giay){
  if(giay == null) return '';
  return giay < 90 ? giay + ' giây trước' : giay < 5400 ? Math.round(giay/60) + ' phút trước' : Math.round(giay/3600) + ' giờ trước';
}
function thanhKc(x){
  const t = x.gui + x.ghi_chu + x.treo + x.chan;
  if(!t) return '<span class="ghi">—</span>';
  const o = (k, c, v) => v ? `<i class="${c}" style="flex:${v}" title="${v} ${KC_TEN[k]} (${pct(v,t)})"></i>` : '';
  return `<div class="kc">${o('gui','g',x.gui)}${o('ghi_chu','n',x.ghi_chu)}${o('treo','t',x.treo)}${o('chan','c',x.chan)}</div>`;
}
function sparks(ds){
  const n = ds.length, mx = Math.max(1, ...ds);
  const dinh = ds.indexOf(Math.max(...ds));
  return `<svg class="sparks" viewBox="0 0 ${n} 24" preserveAspectRatio="none" role="img">
    <title>Tin tới khách theo giờ — cao nhất ${mx} tin (${n - dinh} giờ trước)</title>
    ${ds.map((v,i) => v ? `<rect x="${i+0.12}" width="0.76" y="${24 - Math.max(2, v/mx*24)}" height="${Math.max(2, v/mx*24)}"/>` : '').join('')}</svg>`;
}
async function sauToan(){
  clearTimeout(TC_HEN);
  let k;
  try{ k = await api('toan-canh?gio=' + TC_GIO); }
  catch(e){ if($('#tc')) $('#tc').innerHTML = `<div class="xau">Không gộp được số: ${H(e.message)}</div>`; return; }
  if(TAB !== 'toan' || !$('#tc')) return;
  const t = k.tong, sd = k.kimi.so_du || {};
  const chay = k.nuoc.filter(x => x.co_chay), nghi = k.nuoc.filter(x => !x.co_chay);
  const the = (a,b,c,mau) => `<div class="the"><span class="nhan-o">${a}</span>
    <span class="so-to so"${mau ? ` style="color:var(--${mau})"` : ''}>${b}</span><span class="ghi">${c}</span></div>`;
  const nang = k.canh.filter(c => c[0] === 'nang'), nhe = k.canh.filter(c => c[0] !== 'nang');
  const dongNuoc = x => {
    const s = x.service || {}, pg = x.page || {};
    const den = s.chay === false ? 'tat' : (s.log_giay > 600 || s.loi_gan) ? 'cham' : 'chay';
    const ttSvc = s.chay === false ? 'service TẮT'
      : s.chay == null ? 'không rõ service' : `${s.luot_do != null ? s.luot_do + 's/lượt dò · ' : ''}log ${tuoi(s.log_giay)}`;
    return `<tr class="tc-dong" data-tt="${H(x.tt)}">
      <td class="trai"><span class="den ${den}"></span><b>${H(x.ten)}</b>
        <div class="ghi" style="font-size:11.5px;padding-left:15px">${H(ttSvc)}${s.loi_gan ? ` · <b style="color:var(--nang)">${s.loi_gan} lượt lỗi</b>` : ''}</div></td>
      <td class="so">${x.page_co_khach}<span class="ghi"> / ${pg.shop != null ? pg.shop : (pg.token || '?')}</span></td>
      <td class="so"><b>${n0(x.hoi_thoai)}</b></td>
      <td class="so" style="color:var(--nhan);font-weight:700">${x.gui}</td>
      <td class="so">${x.ghi_chu || '–'}</td>
      <td class="so">${x.treo || '–'}</td>
      <td class="so"${x.chan ? ' style="color:var(--nang)"' : ''}>${x.chan || '–'}</td>
      <td class="so"><b>${x.don || '–'}</b></td>
      <td class="so">${usd2(x.tien)}<span class="hai-dong">${x.tien_moi_tin != null ? vnd(x.tien_moi_tin * 26300) + '/tin' : ''}</span></td>
      <td class="so">${x.fb_chan ? `<span style="color:var(--canh);font-weight:700">${x.fb_chan} FB chặn</span>` : '–'}
        ${x.token_hong ? `<span class="hai-dong">${x.token_hong} token hỏng</span>` : ''}</td>
      <td title="tới khách theo giờ">${thanhKc(x)}${sparks(x.theo_gio)}</td></tr>`;
  };
  const bangPage = (ds, cot) => `<div class="cuon"><table><thead><tr><th class="trai">Page</th><th class="trai">Nước</th>
      ${cot.map(c => `<th>${c[0]}</th>`).join('')}</tr></thead><tbody>
      ${ds.map(p => `<tr><td class="trai" style="white-space:normal">${H(p.ten)}${p.fb_chan ? ' <span class="chip" style="background:var(--canh-mo);color:var(--canh)">FB chặn</span>' : ''}</td>
        <td class="trai">${H((k.nuoc.find(x => x.tt === p.tt) || {}).ten || p.tt)}</td>
        ${cot.map(c => `<td class="so">${c[1](p)}</td>`).join('')}</tr>`).join('')
        || `<tr><td colspan="${cot.length + 2}" class="trai phu">Không có.</td></tr>`}</tbody></table></div>`;

  $('#tc').innerHTML = `
  <div class="dau-trang"><h1>Toàn cảnh ${chay.length} nước đang chạy AI</h1>
    <p class="phu">${gioChu(k.gio)} gần nhất, tới ${H(k.luc)} (giờ máy chủ) · tự làm mới mỗi 60 giây ·
      bấm tên một nước để xem báo cáo riêng nước đó.</p>
    <div class="loc" style="margin:8px 0 0">${[6,24,72,168].map(g =>
      `<button data-g="${g}"${TC_GIO===g?' aria-pressed="true"':''}>${gioChu(g)}</button>`).join('')}
      <button id="tc_lai" style="margin-left:auto">Làm mới</button></div></div>

  <section><div class="luoi">
    ${the('Hội thoại AI xét', n0(t.hoi_thoai), `${n0(t.page_co_khach)} page có khách · gọi model ${n0(t.goi)} lần`)}
    ${the('Tin tới tay khách', n0(t.gui), `${pct(t.gui, t.gui + t.ghi_chu + t.treo + t.chan)} việc AI làm`, 'nhan')}
    ${the('Vào ghi chú', n0(t.ghi_chu), `page bị FB chặn — sale gửi tay`, t.ghi_chu ? 'canh' : '')}
    ${the('Treo cho sale', n0(t.treo), 'AI không tự lo được, đã đánh chưa đọc')}
    ${the('Cổng chặn giữ', n0(t.chan), 'câu sai luật, khách chưa được trả lời', t.chan ? 'nang' : '')}
    ${the('Đơn tool lên từ chat', n0(t.don), `${t.chot} lượt AI chốt đơn`)}
    ${the('Tiền model (tool tính)', usd2(t.tien), t.tien_moi_tin ? vnd(t.tien_moi_tin*26300) + '/tin tới khách' : '')}
    ${sd.co ? the(NT(k.kimi.nha) + ' còn', usd2(sd.con),
                  k.kimi.nap ? `nạp ${usd2(k.kimi.nap)} · đã trừ thật ${usd2(k.kimi.nap - sd.con)}`
                             : `số dư thật, hỏi API ${NT(k.kimi.nha)} · chưa khai tiền nạp`,
                  sd.con < 3 ? 'nang' : 'nhan')
            : the(NT(k.kimi.nha) + ' còn', '?', H(sd.loi || 'không hỏi được số dư'))}
  </div></section>

  ${k.canh.length ? `<section><h2>Cần để ý</h2><div class="canh-ds">
    ${nang.map(c => `<div class="xau">${H(c[1])}</div>`).join('')}
    ${nhe.length ? `<div class="canh-bao" style="font-weight:500"><ul style="margin:0;padding-left:18px">
      ${nhe.map(c => `<li>${H(c[1])}</li>`).join('')}</ul></div>` : ''}
  </div></section>` : `<section><div class="tot">Mọi service đang chạy, không lỗi trong 20 lượt dò gần nhất.</div></section>`}

  <section><h2>Từng nước</h2>
    <div class="cuon"><table>
      <thead><tr><th class="trai">Nước</th><th title="page có khách / page có token thuộc shop">Page</th><th>Hội thoại</th><th>Tới khách</th>
        <th>Ghi chú</th><th>Treo</th><th>Chặn</th><th>Đơn</th><th>Tiền</th>
        <th>Page lỗi</th><th class="trai" title="thanh màu = kết cục việc AI làm; cột nhỏ = tin tới khách theo giờ">Kết cục</th></tr></thead>
      <tbody>${chay.map(dongNuoc).join('')}
        <tr class="tong"><td class="trai">TỔNG ${chay.length} nước</td><td class="so">${t.page_co_khach}</td>
          <td class="so">${n0(t.hoi_thoai)}</td><td class="so">${t.gui}</td><td class="so">${t.ghi_chu}</td>
          <td class="so">${t.treo}</td><td class="so">${t.chan}</td><td class="so">${t.don}</td>
          <td class="so">${usd2(t.tien)}<span class="hai-dong">${t.tien_moi_tin != null ? vnd(t.tien_moi_tin*26300) + '/tin' : ''}</span></td>
          <td class="so">${t.fb_chan} FB chặn<span class="hai-dong">${chay.reduce((a,x) => a + x.token_hong, 0)} token hỏng</span></td>
          <td>${thanhKc(t)}</td></tr>
      </tbody></table></div>
    <div class="chu-giai"><span style="--mau:var(--nhan)">tới khách</span><span style="--mau:var(--canh)">vào ghi chú (FB chặn)</span>
      <span style="--mau:var(--nhat)">treo cho sale</span><span style="--mau:var(--nang)">cổng chặn giữ</span></div>
    <p class="phu" style="margin-top:8px">“Hội thoại” = số hội thoại có khách nhắn mà AI đã xét (gồm cả lượt AI cố ý im vì Botcake/sale đã rep).
      “Đơn” = đơn tool tự lên từ chat (cả chat AI lẫn chat sale). “Tiền” = tool đếm token × giá niêm yết, cao hơn số ${NT(k.kimi.nha)} trừ thật —
      dùng để so các nước với nhau. Số đ/tin dưới cột tiền = tiền chia số tin tới khách, tỉ giá 26.300đ. “Page” = page có khách / page có token thuộc shop.
      ${nghi.length ? `<br>Chưa chạy AI: ${nghi.map(x => H(x.ten)).join(', ')} — không có page dùng được.` : ''}</p>
  </section>

  <section class="hai-cot">
    <div><h2>Page cần người vào</h2>
      ${bangPage(k.can_nguoi, [['Ghi chú', p => p.ghi_chu || '–'], ['Treo', p => p.treo || '–'], ['Chặn', p => p.chan || '–'], ['Hội thoại', p => p.hoi_thoai]])}
      <p class="phu" style="margin-top:8px">Page dồn nhiều ca AI không tự xong: câu nằm trong ghi chú chờ sale gửi tay, ca treo, câu bị cổng chặn giữ.</p></div>
    <div><h2>Page đông khách nhất</h2>
      ${bangPage(k.dong_khach, [['Hội thoại', p => p.hoi_thoai], ['Tới khách', p => p.gui || '–'], ['Gọi model', p => p.goi], ['Tiền', p => usd2(p.tien)]])}</div>
  </section>

  <section><h2>AI vừa làm gì — mọi nước</h2>
    <div class="feed">${k.gan_day.map(r => `<div class="m">
      <span class="ai so">${new Date(r.luc*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'})}</span>
      <span><span class="nhan-kc ${r.kc}">${H(KC_TEN[r.kc] || r.kc)}</span></span>
      <div style="min-width:0"><div><b>${H((k.nuoc.find(x => x.tt === r.tt) || {}).ten || r.tt)}</b> · ${H(r.page)} · ${H(r.khach || 'khách')}
        ${(r.ma||[]).length ? (r.ma).map(m => `<code>${H(m)}</code>`).join(' ') : ''}</div>
        <div class="cau" title="${H(r.tin)}">${H(r.tin) || '<span class="ghi">—</span>'}</div></div></div>`).join('')
      || '<div class="trong">Chưa có việc nào trong khoảng này.</div>'}</div>
    <p class="phu" style="margin-top:8px">Giờ theo múi giờ máy đang mở trang.</p></section>`;

  $('#tc').querySelectorAll('.loc button[data-g]').forEach(b =>
    b.onclick = () => { TC_GIO = +b.dataset.g; $('#tc').insertAdjacentHTML('afterbegin', '<p class="phu"><span class="quay"></span>Đang gộp…</p>'); sauToan(); });
  $('#tc_lai').onclick = () => sauToan();
  $('#tc').querySelectorAll('tr.tc-dong').forEach(r => r.onclick = async () => {
    TT = r.dataset.tt; PAGE = null; PCHON = null; LOC = -1; CHAN = null; CHO = null;
    TAB = 'tong'; bao('Đang mở ' + r.querySelector('b').textContent + '…'); await tai();
  });
  TC_HEN = setTimeout(() => { if(TAB === 'toan' && !document.hidden) sauToan(); }, 60000);
}

/* ═══════════════════════════════════════════════════════════════════════
   MÀN: PAGE & KỊCH BẢN
   Bảng sẵn sàng của mọi page có token, sắp theo mức nghiêm trọng của thứ còn
   thiếu. Bấm một dòng để mở kịch bản + bộ ba giá + tập số AI được phép nói.
   ═══════════════════════════════════════════════════════════════════════ */
function canMkey(ten){
  return `<div class="dau-trang"><h1>${ten}</h1></div>
    <div class="canh-bao">Màn này cần biết đang xem thị trường nào. Mở lại kèm tên thị trường:
    <code>python3 ai_sale.py dashboard usa --phuc-vu</code></div>`;
}
function vePage(){
  if(!S.mkey) return canMkey('Page &amp; kịch bản');
  return `<div class="dau-trang"><h1>Page &amp; kịch bản</h1>
    <p class="phu">Page nào bật AI được rồi, page nào còn thiếu gì — và thiếu thì sửa ở đâu.
    Bấm một dòng để mở kịch bản của page đó.</p></div>
    <div id="noidung"><p class="phu"><span class="quay"></span>Đang đọc kịch bản…</p></div>`;
}
async function sauPage(){
  if(PCHON) return veChiTiet();
  if(!PAGE){ try{ PAGE = await api('page'); }
             catch(e){ return $('#noidung').innerHTML = `<div class="xau">${H(e.message)}</div>`; } }
  const d = PAGE, ds = LOC < 0 ? d.page : d.page.filter(p => p.bac === LOC);
  const tk = d.token_kiem_luc
    ? new Date(d.token_kiem_luc*1000).toLocaleString('vi-VN',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})
    : null;
  $('#noidung').innerHTML = `
  ${d.ngung ? `<p class="phu" style="margin-bottom:16px">Đang xét <b>${d.tong} page</b>.
     ${d.ngung} page đã cho xuống (token chết) — không tính vào bảng.
     ${tk ? `Kiểm token lần cuối ${H(tk)}.` : ''}</p>`
   : `<div class="canh-bao" style="margin-bottom:16px"><b>Chưa kiểm token lần nào.</b>
     Chạy <code>python3 ai_sale.py token ${H(d.mkey)}</code> để loại các page đã cho xuống
     ra khỏi bảng.</div>`}
  <section><div class="luoi">
    ${[4,3,2,1].map(b => `<div class="the">
        <span class="so-to">${d.theo_bac[b] || 0}</span>
        <span class="ghi">bậc ${b} · ${BACTEN[b]}</span></div>`).join('')}
  </div></section>
  <section>
    <div class="loc">
      <button data-b="-1"${LOC<0?' aria-pressed="true"':''}>Tất cả ${d.tong}</button>
      ${[1,2,3,4].filter(b => d.theo_bac[b]).map(b =>
        `<button data-b="${b}"${LOC===b?' aria-pressed="true"':''}>${BACTEN[b]} ${d.theo_bac[b]}</button>`).join('')}
    </div>
    <div class="cuon"><table>
      <thead><tr><th class="trai">Page</th><th>Còn thiếu</th><th>Mẫu câu</th><th>Ảnh</th>
        <th>Giá thực</th><th>Giá sàn</th><th>SKU</th></tr></thead>
      <tbody>${ds.map(p => `<tr class="bam" data-p="${H(p.pid)}">
        <td class="trai"><b>${H(p.ten)}</b></td>
        <td><span class="bac bac${p.bac}">${H(p.thieu)}</span>${
          p.bac===1 && p.kb_ly_do ? `<div class="ghi" style="font-size:11px;margin-top:3px">${H(p.kb_ly_do)}</div>` : ''}</td>
        <td class="so">${p.so_mau}</td><td class="so">${p.so_anh || '—'}</td>
        <td class="so">${p.gia_thuc ? p.gia_thuc : '—'}</td>
        <td class="so">${p.gia_san ? p.gia_san : '—'}</td>
        <td>${p.co_sku ? '✔' : '—'}</td></tr>`).join('')}</tbody>
    </table></div>
    ${ds.length && ds[0].cach_sua ? `<p class="phu" style="margin-top:11px">
      <b>Sửa bậc ${ds[0].bac}:</b> ${H(ds[0].cach_sua)}</p>` : ''}
  </section>`;
  $('#noidung').querySelectorAll('.loc button').forEach(b =>
    b.onclick = () => { LOC = +b.dataset.b; sauPage(); });
  $('#noidung').querySelectorAll('tr.bam').forEach(t =>
    t.onclick = () => { PCHON = t.dataset.p; sauPage(); });
}

async function veChiTiet(){
  $('#noidung').innerHTML = `<p class="phu"><span class="quay"></span>Đang mở kịch bản…</p>`;
  let k; try{ k = await api('kich-ban?pid=' + encodeURIComponent(PCHON)); }
  catch(e){ return $('#noidung').innerHTML = `<div class="xau">${H(e.message)}</div>`; }
  if(!k) return $('#noidung').innerHTML = `<div class="canh-bao">Page này chưa có kịch bản.</div>`;
  $('#noidung').innerHTML = `
  <p><button class="nut nhe" id="quaylai">← Về bảng page</button></p>
  <div class="dau-trang" style="margin-top:16px"><h1>${H(k.ten)}</h1>
    <p class="phu">${k.mau.length} mẫu câu · phiên bản kịch bản ${k.phien_ban ?? '—'} ·
      tiền tệ ${H(k.tien_te)}</p></div>
  <section><h2>Giá và sàn</h2>
    ${(k.gia.gia_neo||[]).length || k.gia.gia_thuc ? `<div class="luoi" style="margin-bottom:12px">
      ${(k.gia.gia_neo||[]).length ? `<div class="the">
        <span class="so-to so">${k.gia.gia_neo.join(' · ')}</span>
        <span class="ghi">Giá neo — chỉ để so sánh, <b>không bán</b></span></div>` : ''}
      ${k.gia.gia_thuc ? `<div class="the"><span class="so-to so">${k.gia.gia_thuc}</span>
        <span class="ghi">Giá thực (từ mẫu /Giảm_giá)</span></div>` : ''}</div>` : ''}
    ${Object.keys(k.gia.san_theo_gia||{}).length ? `<div class="cuon"><table>
      <thead><tr><th class="trai">Mức page bán</th><th>Sàn (−10%, làm tròn lên)</th>
        <th class="trai"></th></tr></thead>
      <tbody>${Object.entries(k.gia.san_theo_gia).sort((a,b)=>a[0]-b[0]).map(([g,s]) =>
        `<tr><td class="trai so">${H(k.tien_te)} ${g}</td><td class="so">${s}</td>
         <td class="trai">${+s === k.gia.san_thap_nhat
            ? '<span class="chip">ngưỡng cổng chặn</span>' : ''}</td></tr>`).join('')}
      </tbody></table></div>
      <p class="phu" style="margin-top:10px">Mỗi combo một sàn riêng. Cổng chặn dùng
        <b>sàn thấp nhất (${k.gia.san_thap_nhat})</b> làm ngưỡng cứng — thấp hơn số đó là chặn,
        vì chắc chắn dưới sàn của mọi combo.</p>`
     : `<div class="canh-bao">Không rút được mức giá nào từ kịch bản page này → cổng chặn
        <b>không canh được giá sàn</b>. Kiểm lại mẫu báo giá trên Pancake.</div>`}
  </section>
  <section><h2>${k.duoc_noi.length} con số AI được phép nói</h2>
    <p class="phu" style="margin-bottom:9px">Cổng chặn cho đúng những số này đi qua. Con số nào
      AI nói ra ngoài danh sách sẽ bị chặn với mã <code>bia_tien</code>.</p>
    <div class="sos">${k.duoc_noi.map(x => `<span>${x}</span>`).join('')}</div></section>
  <section><h2>Mẫu câu</h2>
    ${k.mau.map(m => `<div class="mau">
      <span class="tk">/${H(m.tu_khoa)}</span>
      ${m.chu_de ? `<span class="chip">${H(m.chu_de)}</span>` : ''}
      ${m.so_anh ? `<span class="chip">${m.so_anh} ảnh</span>` : ''}
      <div class="noi">${H(m.tin.join('\n\n'))}</div>
      ${m.tien.length ? `<div class="meta">Tiền trong mẫu: ${m.tien.join(' · ')}</div>` : ''}
    </div>`).join('')}</section>`;
  $('#quaylai').onclick = () => { PCHON = null; sauPage(); };
}

/* ═══════════════════════════════════════════════════════════════════════
   MÀN: SỔ CỔNG CHẶN
   ═══════════════════════════════════════════════════════════════════════ */
function veChan(){
  if(!S.mkey) return canMkey('Sổ cổng chặn');
  return `<div class="dau-trang"><h1>Sổ cổng chặn</h1>
    <p class="phu">Mọi câu AI soạn đều đi qua một cửa luật trước khi tới khách. Đây là những câu
    cửa đó không cho qua — và vì sao.</p></div>
    <div id="noidung"><p class="phu"><span class="quay"></span>Đang đọc sổ…</p></div>`;
}
async function sauChan(){
  let d; try{ d = CHAN = await api('chan'); }
  catch(e){ return $('#noidung').innerHTML = `<div class="xau">${H(e.message)}</div>`; }
  if(!d.tong_luot) return $('#noidung').innerHTML = `<div class="trong">Sổ còn trống.
    Sang tab <b>Hàng chờ sale</b> bấm <b>Xem trước câu AI</b> để chạy một vòng thử —
    vòng thử cũng ghi sổ, và không gửi gì cho khách.</div>`;
  $('#noidung').innerHTML = `
  <section><div class="luoi">
    <div class="the"><span class="so-to">${d.tong_luot}</span><span class="ghi">lượt AI đã động vào</span></div>
    <div class="the"><span class="so-to" style="color:var(--nhan)">${d.sach}</span><span class="ghi">sạch, gửi thẳng</span></div>
    <div class="the"><span class="so-to" style="color:var(--canh)">${d.viet_lai + d.nhac}</span><span class="ghi">có lỗi văn phong</span></div>
    <div class="the"><span class="so-to" style="color:var(--nang)">${d.chan}</span><span class="ghi">BỊ CHẶN — khách chưa được trả lời</span></div>
  </div></section>
  ${d.theo_ma.length ? `<section><h2>Vì lý do gì</h2><div class="cuon"><table>
    <thead><tr><th class="trai">Mã lỗi</th><th>Lần</th><th>Trong đó chặn</th>
      <th class="trai">Nghĩa là gì</th></tr></thead>
    <tbody>${d.theo_ma.map(m => `<tr><td class="trai"><code>${H(m.ma)}</code></td>
      <td class="so">${m.so}</td>
      <td class="so"${m.chan ? ' style="color:var(--nang);font-weight:700"' : ''}>${m.chan || '—'}</td>
      <td class="trai">${H(m.y_nghia)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
  ${d.theo_page.length ? `<section><h2>Page hay bị chặn nhất</h2><div class="cuon"><table>
    <thead><tr><th class="trai">Page</th><th>Lần bị chặn</th></tr></thead>
    <tbody>${d.theo_page.map(p => `<tr><td class="trai">${H(p.ten || p.pid)}</td>
      <td class="so">${p.so}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
  <section><h2>Gần đây</h2>
    ${d.gan_day.slice(0,60).map(x => `<div class="viec${x.chan==='chan'?' chan':''}">
      <div class="dinh"><span>${H(x.page || x.pid)} · ${H(x.khach || 'khách')}</span>
        <span>${(x.ma||[]).map(m=>`<code>${H(m)}</code>`).join(' ')}
          ${x.that ? '<span class="chip">vòng thật</span>' : ''}</span></div>
      ${x.tin ? `<div class="cau">${H(x.tin)}</div>` : ''}
    </div>`).join('') || '<div class="trong">Chưa có phán quyết nào.</div>'}</section>`;
}

/* ═══════════════════════════════════════════════════════════════════════
   MÀN: HÀNG CHỜ SALE  (+ nút xem trước câu AI)
   ═══════════════════════════════════════════════════════════════════════ */
function veCho(){
  if(!S.mkey) return canMkey('Hàng chờ sale');
  return `<div class="dau-trang"><h1>Hàng chờ sale</h1>
    <p class="phu">Ca AI đã dừng và giao lại cho người: treo, chờ xác minh nhà, hoặc bị cổng
    chặn giữ tin lại. Không ca nào ở đây được để trôi.</p></div>
    <section class="hop"><h2 style="margin-bottom:9px">Xem trước câu AI định gửi</h2>
      <p class="phu">Chạy đúng lệnh gửi thật nhưng <b>bỏ cờ --that</b> — quét hội thoại thật,
      soạn câu thật, đi qua cổng chặn thật, nhưng <b>không gửi gì cho khách</b>. Có gọi model
      nên có tốn tiền.</p>
      <div class="thanh-nut">
        <button class="nut" id="thu">Chạy thử một vòng</button>
        <label style="flex-direction:row;align-items:center;gap:7px;font-weight:400">
          <span class="gt">giờ nhìn lại</span>
          <input type="number" id="thugio" value="24" min="1" max="168" style="width:78px"></label>
        <label style="flex-direction:row;align-items:center;gap:7px;font-weight:400">
          <span class="gt">hội thoại/page</span>
          <input type="number" id="thuso" value="20" min="1" max="60" style="width:78px"></label>
        <span id="thutt" class="phu"></span>
      </div>
      <pre class="log" id="thulog" style="margin-top:14px;display:none"></pre>
    </section>
    <div id="noidung"><p class="phu"><span class="quay"></span>Đang đọc hàng chờ…</p></div>`;
}
async function sauCho(){
  $('#thu').onclick = async () => {
    try{ await api('thu', {gio: +$('#thugio').value || 24, so: +$('#thuso').value || 20,
                           pid: PCHON || ''}); bao('Đang chạy thử — không gửi gì cho khách'); }
    catch(e){ bao(e.message, 1); }
    theoDoiThu();
  };
  theoDoiThu();
  let d; try{ d = CHO = await api('hang-cho'); }
  catch(e){ return $('#noidung').innerHTML = `<div class="xau">${H(e.message)}</div>`; }
  $('#noidung').innerHTML = `
  <section><div class="luoi">
    <div class="the"><span class="so-to">${d.tong}</span><span class="ghi">việc đang chờ người</span></div>
    <div class="the"><span class="so-to">${d.xac_nha}</span><span class="ghi">chờ sale xác minh nhà — AI đang ĐỨNG ĐỢI</span></div>
    <div class="the"><span class="so-to">${d.treo}</span><span class="ghi">treo cho sale</span></div>
    <div class="the"><span class="so-to"${d.qua_24h?' style="color:var(--nang)"':''}>${d.qua_24h}</span>
      <span class="ghi">chờ quá 24h — quá cửa sổ nhắn của Facebook</span></div>
  </div></section>
  <section>${d.viec.map(v => `<div class="viec${v.chan==='chan'?' chan':''}">
    <div class="dinh"><span>${H(v.khach || 'khách')} · ${H(v.page || v.pid)}</span>
      <span>${H(v.loai)} · <span class="so">${v.cho_gio}h</span></span></div>
    ${(v.thieu||[]).length ? `<div class="gcv"><b>Còn thiếu:</b> ${v.thieu.map(H).join(' · ')}</div>`
      : (Object.keys(v.da_co||{}).length ? `<div class="gcv"><b>Đủ 5 trường</b> — lên đơn được</div>` : '')}
    ${Object.keys(v.da_co||{}).length ? `<div class="gcv" style="font-size:12px">
      ${Object.entries(v.da_co).map(([k,x])=>`${H(k)}: ${H(String(x).slice(0,60))}`).join(' · ')}</div>` : ''}
    ${v.gc ? `<div class="gcv">${H(v.gc)}</div>` : ''}
    ${v.tin ? `<div class="cau">${H(v.tin)}</div>` : ''}
  </div>`).join('') || '<div class="trong">Không có ca nào đang chờ.</div>'}</section>`;
}
async function theoDoiThu(){
  const t = await api('thu');
  if(TAB !== 'hangcho') return;
  $('#thutt').innerHTML = t.chay
    ? '<span class="quay"></span>đang chạy…' : H(t.xong || '');
  if(t.log){ $('#thulog').style.display = 'block'; $('#thulog').textContent = t.log;
             $('#thulog').scrollTop = $('#thulog').scrollHeight; }
  $('#thu').disabled = t.chay;
  if(t.chay) setTimeout(theoDoiThu, 1100);
  else if(t.log){ CHAN = CHO = null; }
}

/* ── Tổng quan ──
   Chủ shop 13/09: "báo cáo tổng, càng chi tiết càng tốt, để báo cáo lại sếp đã tiêu 20 đô
   cho những gì, sao hết nhanh, tối ưu được gì". Số do bao_cao_tien.py tính từ sổ chi phí +
   số dư Kimi thật + số đo hieu_suat.py; trang chỉ vẽ lại. */
function veTong(){
  return `<div id="bc_noi"><p class="phu"><span class="quay"></span>Đang đọc sổ chi phí và hỏi số dư ${NT()}…</p></div>
    ${veTongUoc()}`;
}
async function sauTong(){
  let k;
  try{ k = await api('bao-cao'); }
  catch(e){ $('#bc_noi').innerHTML = `<div class="xau">Không đọc được báo cáo: ${H(e.message)}</div>`; return; }
  $('#bc_noi').innerHTML = veBaoCao(k);
  const nut = $('#bc_chep');
  if(nut) nut.onclick = async () => {
    try{ await navigator.clipboard.writeText(k.van_ban); bao('Đã chép báo cáo dạng chữ — dán vào Zalo/email được ngay'); }
    catch(e){ const ta = $('#bc_vb'); ta.hidden = false; ta.select(); bao('Trình duyệt không cho chép tự động — chọn ô chữ bên dưới rồi Ctrl/Cmd+C'); }
  };
}
const pct = (a,b) => b ? Math.round(a/b*100) + '%' : '–';
const usd2 = x => '$' + (+x).toFixed(2);
const vnd = x => Math.round(x).toLocaleString('vi-VN') + 'đ';
function veBaoCao(k){
  if(k.loi) return `<div class="xau">${H(k.loi)}</div>`;
  const sd = k.so_du || {};
  if(!k.co_so) return `<div class="dau-trang"><h1>Báo cáo chi phí AI Sale</h1>
    <p class="phu">Sổ chi phí của ${H(k.mkey)} còn trống — chưa lượt nào gọi model.
    ${sd.co ? 'Tài khoản ' + NT(k.nha) + ' đang còn ' + usd(sd.con) + '.' : ''}</p></div>`;
  const the = (a,b,c,x) => `<div class="the"><span class="nhan-o">${a}</span>
    <span class="so-to so${x?' '+x:''}">${b}</span><span class="ghi">${H(c)}</span></div>`;
  const kimi = !sd.co
    ? the(NT(k.nha) + ' thực trừ', '?', 'không hỏi được số dư: ' + (sd.loi||''))
    : k.kimi_tru == null
      ? the(NT(k.nha) + ' còn', usd2(sd.con), 'số dư thật; chưa khai tiền nạp cho nhà này nên chưa tính được đã trừ bao nhiêu', 'xanh')
      : the(NT(k.nha) + ' thực trừ', usd2(k.kimi_tru), 'còn ' + usd2(sd.con) + ' trong tài khoản (số dư thật, hỏi API ' + NT(k.nha) + ')'
             + (k.gio_nha && k.gio_nha < 48 ? ' · mới chạy ' + k.gio_nha + ' giờ' : ''), 'xanh');
  return `<div class="dau-trang"><h1>Báo cáo chi phí AI Sale — ${H(k.mkey.toUpperCase())}</h1>
    <p class="phu">Lập ${H(k.luc)} · chạy từ ${H(k.tu)} đến ${H(k.den)} (${k.so_ngay} ngày) ·
    model ${H(k.model||'?')} của ${H(k.nha)}. Mọi con số lấy từ sổ chi phí ghi mỗi lượt gọi,
    số dư thật của tài khoản ${NT(k.nha)} và số đo hieu_suat.py — không ước lượng.</p>
    <div class="thanh-nut" style="margin-top:8px"><button class="nut" id="bc_chep">Chép báo cáo dạng chữ</button>
    <span class="phu">để dán vào Zalo / email gửi sếp</span></div>
    <textarea id="bc_vb" hidden style="min-height:220px;margin-top:10px">${H(k.van_ban)}</textarea></div>

  ${veHoiDap(k)}

  <section><h2>Tóm tắt</h2><div class="luoi">
    ${the('Đã nạp', usd(k.nap), 'ngày ' + H((k.nap_ds[0]||{}).luc||'?'))}
    ${the('Tool tự tính (giá niêm yết)', usd(k.chi), k.goi.toLocaleString() + ' lượt gọi model · ' + usd(k.chi/k.goi) + '/lượt'
          + (k.goi_nha && k.goi_nha < k.goi ? ' · riêng ' + NT(k.nha) + ' ' + usd(k.chi_nha) + ' / ' + k.goi_nha.toLocaleString() + ' lượt từ ' + k.tu_nha : ''))}
    ${kimi}
    ${the('Khách AI đã đụng', k.khach.toLocaleString(), k.luot_khach.toLocaleString() + ' lượt khách nhắn · ' + k.hoi_thoai_goi.toLocaleString() + ' hội thoại có gọi model')}
    ${the('Câu AI soạn cho khách', k.tra_loi.toLocaleString(), usd(k.tien_tra_loi) + ' · ' + k.len_don + ' lượt chốt đơn')}
    ${k.hieu_suat ? the('Tin gửi thật tới khách', k.hieu_suat.gui.toLocaleString(), 'đo ' + k.hieu_suat.gio + ' giờ · ' + k.hieu_suat.ghi_chu + ' câu chỉ vào ghi chú (page bị chặn)') : ''}
  </div>
  ${sd.co && k.kimi_tru != null ? `<div class="the-lon" style="margin-top:12px"><p><b>Tiền chưa hết.</b> Tool tự tính
    <b>${usd(k.chi)}</b> bằng cách đếm token mỗi lượt gọi rồi nhân với giá niêm yết ghi trong code;
    còn tài khoản ${NT(k.nha)} thực tế mới trừ <b>${usd2(k.kimi_tru)}</b> và đang còn <b>${usd2(sd.con)}</b>.
    Số tool tự tính dùng để chia tỉ lệ “tiền đi đâu”, còn số tuyệt đối thì lấy theo ${NT(k.nha)}. Con số
    “còn lại” trong log và “trần ngày” ở cột trái là ngân sách tự đặt theo số tool tự tính,
    không phải số dư thật.</p></div>` : ''}
  </section>

  <section><h2>Chi theo ngày</h2><div class="cuon"><table>
    <thead><tr><th>Ngày</th><th>Lượt gọi</th><th>Tiền</th><th>TB/lượt</th><th>Trả lời</th>
    <th>Đọc lại bot</th><th>Im</th><th>Treo</th><th>Chốt đơn</th><th>Thử tay</th>
    <th>Token/lượt (vào + đệm + ra)</th><th>Lượt khách</th></tr></thead><tbody>
    ${k.theo_ngay.map(d => `<tr><td>${H(d.ngay)}</td><td class="so">${d.goi}</td>
      <td class="so"><b>${usd(d.tien)}</b></td><td class="so">${usd(d.tb)}</td>
      <td class="so">${d.tra_loi}</td><td class="so">${d.xet}</td><td class="so">${d.im}</td>
      <td class="so">${d.treo}</td><td class="so">${d.len_don}</td>
      <td class="so">${d.thu ? d.thu + ' (' + usd(d.tien_thu) + ')' : '–'}</td>
      <td class="so">${n0(d.vao)} + ${n0(d.dem)} + ${n0(d.ra)}</td><td class="so">${n0(d.luot_khach)}</td></tr>`).join('')}
    </tbody></table></div>
    <p class="phu" style="margin-top:8px">“Đọc lại bot” = Botcake đã rep, model đọc xem trúng chưa.
    “Thử tay” = vòng soát câu trước khi gửi thật, tốn tiền nhưng không gửi tin.</p></section>

  <section><h2>Tiền đi đâu — theo kết cục của từng lượt gọi</h2><div class="thanhds">
    ${k.ket_cuc.map(x => `<div class="dong"><div><div><b>${H(x.ten)}</b> — ${x.luot.toLocaleString()} lượt · ${usd(x.tien)}</div>
      <div class="ray"><i style="width:${x.tien/k.chi*100}%"></i></div>
      <div class="phu">${H(x.giai_thich)}</div></div>
      <div class="pt so">${pct(x.tien,k.chi)}</div></div>`).join('')}
  </div></section>

  <section><h2>Cấu phần token — vì sao một lượt tốn ${usd(k.chi/k.goi)}</h2><div class="luoi">
    ${the('Vào, không đệm', n0(k.token.vao), usd(k.token.tien_vao) + ' · $' + k.token.gia.vao + '/1 triệu')}
    ${the('Đọc từ bộ đệm', n0(k.token.dem), usd(k.token.tien_dem) + ' · $' + k.token.gia.dem + '/1 triệu')}
    ${the('Ra (câu trả lời + JSON)', n0(k.token.ra), usd(k.token.tien_ra) + ' · $' + k.token.gia.ra + '/1 triệu')}
    ${the('Trung bình mỗi lượt', n0((k.token.vao+k.token.dem)/k.goi) + ' vào', n0(k.token.ra/k.goi) + ' ra — gói mang kịch bản page + luật + hồ sơ khách + hội thoại')}
  </div></section>

  <section><h2>Theo page — ${k.so_page} page có gọi model, ${k.so_page_chan} đang bị Facebook chặn gửi</h2>
    <div class="cuon"><table><thead><tr><th>Page</th><th>Lượt gọi</th><th>Khách</th><th>Câu soạn</th>
    <th>Đơn</th><th>Tiền</th><th>%</th></tr></thead><tbody>
    ${k.theo_page.slice(0,15).map(p => `<tr><td>${p.chan ? '<span class="chip xau">chặn</span> ' : ''}${H(p.page)}</td>
      <td class="so">${p.goi}</td><td class="so">${p.khach}</td><td class="so">${p.tra_loi}</td>
      <td class="so">${p.don}</td><td class="so"><b>${usd(p.tien)}</b></td><td class="so">${pct(p.tien,k.chi)}</td></tr>`).join('')}
    </tbody></table></div></section>

  ${k.hieu_suat ? `<section><h2>Số đo hiệu suất thật (hieu_suat.py, ${k.hieu_suat.gio} giờ tới ${H(k.hieu_suat.luc)})</h2><div class="luoi">
    ${the('Tin AI gửi thật', k.hieu_suat.gui, 'qua API, tới khách')}
    ${the('Chỉ vào ghi chú', k.hieu_suat.ghi_chu, 'page bị chặn, sale chép gửi tay')}
    ${the('Cổng chặn giữ lại', k.hieu_suat.chan, 'bịa tiền / bịa cửa hàng / sai luật')}
    ${the('Giá mỗi tin gửi thẳng', usd(k.hieu_suat.moi_tin.gui||0), 'mỗi tin soạn ' + usd(k.hieu_suat.moi_tin.soan||0))}
    ${k.hieu_suat.tong.luot ? the('AI xử lý / lượt khách', pct(k.hieu_suat.tong.ai_xu_ly, k.hieu_suat.tong.luot), k.hieu_suat.tong.ai_xu_ly + ' / ' + k.hieu_suat.tong.luot + ' lượt khách nhắn') : ''}
  </div></section>` : ''}

  ${k.gia_that ? `<section><h2>Giá thật mỗi tin — theo số ${NT(k.nha)} trừ, tỉ giá ${k.gia_that.ty_gia.toLocaleString('vi-VN')}đ/USD</h2><div class="luoi">
    ${the('Mỗi lượt gọi model', vnd(k.gia_that.moi_luot*k.gia_that.ty_gia), '$' + k.gia_that.moi_luot.toFixed(4) + ' · ' + (k.gia_that.luot_tk||k.goi).toLocaleString() + ' lượt cả tài khoản')}
    ${k.gia_that.moi_cau_soan ? the('Mỗi câu AI soạn', vnd(k.gia_that.moi_cau_soan*k.gia_that.ty_gia), '$' + k.gia_that.moi_cau_soan.toFixed(4) + ' · ' + (k.tra_loi_nha||k.tra_loi).toLocaleString() + ' câu, gánh cả lượt im/treo') : ''}
    ${k.gia_that.moi_tin_gui ? the('Mỗi tin gửi thật tới khách', vnd(k.gia_that.moi_tin_gui*k.gia_that.ty_gia), '$' + k.gia_that.moi_tin_gui.toFixed(4) + (k.gia_that.uoc_gui ? ' · ước theo số tin của ' + k.gio_nha + ' giờ chạy' : ' · ' + k.hieu_suat.gui + ' tin, gánh cả câu vào ghi chú')) : ''}
  </div><p class="phu" style="margin-top:8px">Số tool tự tính cao hơn ~4 lần: $${(k.hieu_suat ? k.hieu_suat.moi_tin.gui : 0).toFixed(4)}/tin gửi. Mục tiêu chủ shop 11/09: ~65đ/tin.</p></section>` : ''}

  ${k.bot_so_sai && k.bot_so_sai.length ? `<section><h2>Page nào Botcake đỡ ít → AI phải gánh</h2>
    <p class="phu" style="margin-bottom:10px">Xếp theo % lượt khách nhắn mà Botcake im (page từ 15 lượt trở lên, số đo hieu_suat.py).
    % im cao = kịch bản Botcake của page đó sơ sài, nên set thêm từ khoá để AI khỏi phải gọi model.</p>
    <div class="cuon"><table><thead><tr><th>Page</th><th>Lượt khách</th><th>Botcake rep</th><th>Botcake im</th>
    <th>% im</th><th>AI xử lý</th><th>AI gửi</th><th>Tiền</th></tr></thead><tbody>
    ${k.bot_so_sai.map(r => `<tr><td>${H(r.page)}${r.co_botcake ? '' : ' <span class="chip xau">không có Botcake</span>'}</td>
      <td class="so">${r.luot}</td><td class="so">${r.bot}</td><td class="so">${r.bot_im}</td>
      <td class="so"><b>${Math.round(r.ty_le_im*100)}%</b></td><td class="so">${r.ai_xu_ly}</td>
      <td class="so">${r.tin_gui}</td><td class="so">${usd(r.tien)}</td></tr>`).join('')}
    </tbody></table></div></section>` : ''}

  <section><h2>Vì sao tiền đi nhanh</h2><ol style="margin:0;padding-left:22px;display:flex;flex-direction:column;gap:8px">
    ${k.nguyen_nhan.map(s => `<li>${H(s)}</li>`).join('')}</ol></section>

  <section><h2>Đã tối ưu — nhật ký thay đổi</h2><div class="cuon"><table>
    <thead><tr><th>Ngày</th><th style="text-align:left">Việc</th><th>Loại</th></tr></thead><tbody>
    ${k.nhat_ky.map(([n,v,l]) => `<tr><td>${H(n)}</td><td style="text-align:left;white-space:normal">${H(v)}</td><td><span class="chip">${H(l)}</span></td></tr>`).join('')}
    </tbody></table></div>
    <p class="phu" style="margin-top:8px">Đối chiếu bảng theo ngày: lượt “đọc lại bot” và token ra mỗi lượt giảm sau 11/09;
    token vào mỗi lượt tăng vì hồ sơ khách và kịch bản dài hơn — đó là lý do TB/lượt chưa giảm.</p></section>

  <section><h2>Còn tối ưu được gì</h2><div class="cuon"><table>
    <thead><tr><th style="text-align:left">Việc</th><th style="text-align:left">Vì sao / thế nào</th><th>Ước</th></tr></thead><tbody>
    ${k.con_lam.map(([t,m,u]) => `<tr><td style="text-align:left;white-space:normal"><b>${H(t)}</b></td>
      <td style="text-align:left;white-space:normal">${H(m)}</td><td class="so" style="white-space:normal">${H(u)}</td></tr>`).join('')}
    </tbody></table></div></section>

  ${k.du_bao.con_ngay_so ? `<section><h2>Dự báo</h2><div class="the-lon"><p>
    Theo số tool tự tính (${usd(k.du_bao.tb_ngay_so)}/ngày) số dư hiện tại đủ khoảng <b>${Math.round(k.du_bao.con_ngay_so)} ngày</b>${
    k.du_bao.con_ngay_that ? `; theo mức ${NT(k.nha)} thực trừ (${usd(k.du_bao.tb_ngay_that)}/ngày) đủ khoảng <b>${Math.round(k.du_bao.con_ngay_that)} ngày</b>` : ''}.
    ${k.nha === 'deepseek' ? 'Đang chạy DeepSeek Flash — mức rẻ nhất đã đo.' : 'Đổi sang DeepSeek Flash thì nhân thêm 4–7 lần.'}</p></div></section>` : ''}`;
}
/* Bốn câu chủ shop hỏi 13/09 — giữ nguyên cách trình bày đã duyệt ("chi tiết quá, tôi ưng"):
   bảng số + chữ giải thích ngay dưới. Số tính động từ báo cáo, không ghi cứng. */
function veHoiDap(k){
  const sd = k.so_du || {}, g = k.gia_that, h = k.hieu_suat, tg = g ? g.ty_gia : 26300;
  const bang = (cot, dong) => `<div class="cuon"><table><thead><tr>${cot.map((c,i) =>
      `<th${i?'':' style="text-align:left"'}>${H(c)}</th>`).join('')}</tr></thead><tbody>${
      dong.map(r => `<tr>${r.map((x,i) => `<td${i?' class="so"':''}>${x}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const doan = t => `<p style="margin-top:10px">${t}</p>`;
  let ra = `<section><h2>Bốn câu hỏi của chủ shop — trả lời bằng số thật</h2>`;

  // 1. Nhà model thực trừ
  ra += `<h3 style="font-size:16px;margin:14px 0 8px">1. “${NT(k.nha)} thực trừ” là gì, tài khoản còn bao nhiêu?</h3>`;
  if(sd.co && k.kimi_tru != null){
    ra += doan(`Đó là số tiền ${NT(k.nha)} đã lấy khỏi tài khoản: tiền nạp trừ số dư hiện tại, số dư hỏi thẳng API của ${NT(k.nha)} lúc ${H(k.luc)}.`)
      + bang(['', 'Số'], [['Nạp ngày ' + H((k.nap_ds[0]||{}).luc||'?'), usd2(k.nap)],
                          ['Còn trong tài khoản lúc này', '<b>' + usd2(sd.con) + '</b>'],
                          [NT(k.nha) + ' đã trừ', '<b>' + usd2(k.kimi_tru) + '</b>']])
      + doan(`Số dư là của cả tài khoản nên phải so với sổ của mọi thị trường: chạy bằng ${NT(k.nha)} từ ${H(k.tu_nha||k.tu)} tới giờ là ${(k.goi_nha_tk||0).toLocaleString()} lượt, tool tự tính ${usd2(k.chi_nha_tk)} — cao hơn số ${NT(k.nha)} trừ thật khoảng ${(k.chi_nha_tk/k.kimi_tru).toFixed(1)} lần. Riêng ${H(k.mkey.toUpperCase())} là ${(k.goi_nha||0).toLocaleString()} lượt / ${usd2(k.chi_nha)}; cả sổ ${usd2(k.chi)} gộp cả thời Kimi. Dùng số tool để chia tỉ lệ “tiền đi đâu”; số tuyệt đối lấy theo ${NT(k.nha)}.`);
  } else if(sd.co){
    ra += doan(`Tài khoản ${NT(k.nha)} đang còn <b>${usd2(sd.con)}</b> — hỏi thẳng API lúc ${H(k.luc)}. Chưa khai lần nạp nào cho nhà này (tab <b>Tiền nong</b>) nên chưa tính được đã trừ bao nhiêu; tool tự tính ${usd2(k.chi)}.`);
  } else ra += doan(`Không hỏi được số dư ${NT(k.nha)}: ` + H(sd.loi||''));

  // 2. Một tin mấy tiền
  ra += `<h3 style="font-size:16px;margin:18px 0 8px">2. Một tin mấy tiền?</h3>`;
  if(g){
    ra += doan(`Theo số ${NT(k.nha)} thực trừ, tỉ giá ${tg.toLocaleString('vi-VN')}đ/USD:`)
      + bang(['', 'USD', 'VNĐ'], [
          ['Mỗi lượt gọi model (' + (g.luot_tk||k.goi).toLocaleString() + ' lượt cả tài khoản)', '$' + g.moi_luot.toFixed(4), '<b>' + vnd(g.moi_luot*tg) + '</b>'],
          g.moi_cau_soan ? ['Mỗi câu AI soạn (' + (k.tra_loi_nha||k.tra_loi).toLocaleString() + ' câu)', '$' + g.moi_cau_soan.toFixed(4), '<b>' + vnd(g.moi_cau_soan*tg) + '</b>'] : null,
          g.moi_tin_gui ? ['Mỗi tin gửi thật tới khách (' + h.gui + ' tin)', '$' + g.moi_tin_gui.toFixed(4), '<b>' + vnd(g.moi_tin_gui*tg) + '</b>'] : null,
        ].filter(Boolean))
      + doan(`Tin gửi thật đắt hơn vì phải gánh cả tiền các lượt AI im, treo, và các câu soạn ra nhưng chỉ vào ghi chú do page bị Facebook chặn. Mục tiêu chủ shop đặt hôm 11/09 là 65đ/tin: hiện ${g.moi_cau_soan ? vnd(g.moi_cau_soan*tg) + '/câu soạn' : ''}${g.moi_tin_gui ? ' nhưng ' + vnd(g.moi_tin_gui*tg) + '/tin tới tay khách' : ''}. Gỡ chặn Facebook là cách kéo hai số này về gần nhau.`);
  } else ra += doan('Chưa có số ' + NT(k.nha) + ' trừ nên chưa tính được giá thật mỗi tin.');

  // 3. AI xử lý bao nhiêu tin
  ra += `<h3 style="font-size:16px;margin:18px 0 8px">3. AI xử lý bao nhiêu tin?</h3>`;
  ra += doan(`Trong ${k.so_ngay} ngày (${H(k.tu)} → ${H(k.den)}), AI quét <b>${k.luot_khach.toLocaleString()}</b> lượt khách nhắn ở <b>${k.khach.toLocaleString()}</b> hội thoại, gọi model <b>${k.goi.toLocaleString()}</b> lần, soạn <b>${k.tra_loi.toLocaleString()}</b> câu, chốt đơn ${k.len_don} lượt.`);
  if(h && h.tong && h.tong.luot){
    const t = h.tong;
    ra += bang(['Theo số đo hiệu suất ' + h.gio + ' giờ gần nhất', 'Lượt', 'Tỉ lệ'], [
        ['Khách nhắn', t.luot, '100%'],
        ['Botcake đỡ được', t.bot, pct(t.bot, t.luot)],
        ['Botcake im', t.bot_im, pct(t.bot_im, t.luot)],
        ['AI xử lý (trả lời / treo / ghi chú)', '<b>' + t.ai_xu_ly + '</b>', '<b>' + pct(t.ai_xu_ly, t.luot) + '</b>'],
        ['— trong đó tin đi thẳng tới khách', h.gui, pct(h.gui, t.luot)],
        ['— chỉ vào ghi chú vì page bị chặn', h.ghi_chu, pct(h.ghi_chu, t.luot)],
        ['Sale người thật trả lời', t.sale, pct(t.sale, t.luot)]])
      + doan(`Botcake im ${pct(t.bot_im, t.luot)} lượt khách nhắn — đó là khoảng trống AI đang lấp. Botcake đỡ được nhiều hơn thì AI gọi model ít hơn, tiền giảm theo.`);
  }

  // 4. Page nào Botcake sơ sài
  if(k.bot_so_sai && k.bot_so_sai.length){
    const ds = k.bot_so_sai;
    const nen = [...ds].sort((a,b) => b.ai_xu_ly - a.ai_xu_ly).slice(0,3);
    const nho = ds.filter(r => r.luot < 40 && r.ty_le_im >= 0.9);
    ra += `<h3 style="font-size:16px;margin:18px 0 8px">4. Page nào Botcake sơ sài → nên set thêm?</h3>`
      + doan(`Xếp theo tỉ lệ lượt khách nhắn mà Botcake im, chỉ tính page từ 15 lượt trở lên (số đo hiệu suất ${h ? h.gio : ''} giờ). % im cao = kịch bản Botcake thiếu từ khoá, AI phải gọi model thay.`)
      + bang(['Page', 'Lượt khách', 'Botcake rep', 'Botcake im', '% im', 'AI phải xử lý', 'AI gửi', 'Tiền'],
          ds.map(r => [H(r.page) + (r.co_botcake ? '' : ' <span class="chip xau">không có Botcake</span>'),
                       r.luot, r.bot, r.bot_im, '<b>' + Math.round(r.ty_le_im*100) + '%</b>', '<b>' + r.ai_xu_ly + '</b>', r.tin_gui, usd(r.tien)]))
      + doan(`Đáng set bot nhất là <b>${nen.map(r => H(r.page) + ' (AI gánh ' + r.ai_xu_ly + ' lượt, ' + r.luot + ' khách)').join('</b>, <b>')}</b> — lượng khách lớn nên mỗi từ khoá thêm vào cắt được nhiều lượt gọi model nhất.`
        + (nho.length ? ` Các page nhỏ Botcake gần như không có (${nho.map(r => H(r.page)).join(', ')}) ít khách nên để sau.` : ''));
  }
  // 5. Page xử lý được / không
  const pk = k.page_kk || {};
  if(pk.nhom){
    ra += `<h3 style="font-size:16px;margin:18px 0 8px">5. Đã xử lý được bao nhiêu page, bao nhiêu page không, lý do cụ thể?</h3>`
      + doan(`Tài khoản Pancake có <b>${pk.tong_tai_khoan}</b> page. Thuộc shop ${H(k.mkey.toUpperCase())} và có token: <b>${pk.tong_shop}</b> page, chia như sau ${pk.gio ? '(lưu lượng đo ' + pk.gio + ' giờ gần nhất)' : '(nước này chưa đo lưu lượng khách — cột Có khách / Lượt khách chưa có số)'}:`)
      + bang(['Nhóm', 'Page', 'Có khách', 'Lượt khách', 'FB chặn', 'Vì sao / sửa thế nào'],
          pk.nhom.map(n => [`<b>${H(n.ten)}</b>`, n.so, n.co_khach, n.luot.toLocaleString(), n.chan, `<span style="white-space:normal;display:block;text-align:left;min-width:260px">${H(n.giai)}</span>`])
          .concat([[`<b>Token hỏng — AI không đọc được hội thoại</b>`, pk.token_hong.length, '?', '?', '–', `<span style="white-space:normal;display:block;text-align:left;min-width:260px">Đã thử cấp lại 13/09: Pancake trả lỗi 121 “không tìm thấy gói cước” — page hết gói, không phải lỗi tool. Gia hạn gói Pancake là tự chạy lại. ${H(pk.token_hong.slice(0,16).join(', '))}</span>`],
                   [`<b>Không đụng được</b>`, pk.het_goi + pk.thieu_quyen.length, '–', '–', '–', `<span style="white-space:normal;display:block;text-align:left;min-width:260px">${pk.het_goi} page khác của shop hết gói cước Pancake (không đọc được hội thoại), ${pk.thieu_quyen.length} page thiếu quyền Admin nên không cấp được token${pk.thieu_quyen.length ? ': ' + H(pk.thieu_quyen.slice(0,10).join(', ')) : ''}.</span>`]]));
    for(const n of pk.nhom){
      const ds = n.ds.filter(x => x.luot);
      if(!ds.length) continue;
      ra += doan(`<b>${H(n.ten)}</b> — page có khách nhiều nhất:`)
        + bang(['Page', 'Lượt khách', 'Botcake im', 'AI xử lý', 'AI gửi', ''],
            ds.map(x => [H(x.ten), x.luot, x.bot_im, x.ai_xu_ly, x.tin_gui, x.chan ? '<span class="chip xau">FB chặn</span>' : '']));
    }
    ra += doan(`${pk.chan} page đang bị Facebook chặn gửi qua API (#2022): AI vẫn soạn nhưng câu vào ghi chú, sale phải gửi tay. Đây là lý do lớn nhất khiến “xử lý được” không đồng nghĩa “tới tay khách”.`);
  } else if(pk.loi) ra += doan('Không kiểm kê được page: ' + H(pk.loi));

  // 6. Sao chốt ít đơn
  const dn = k.don || {};
  if(dn.nguon){
    ra += `<h3 style="font-size:16px;margin:18px 0 8px">6. Sao chốt được ít đơn?</h3>`
      + doan(`Đơn thật trên POS từ ${H(dn.tu)} tới giờ: <b>${dn.tong}</b> đơn. Nguồn phân theo ghi chú đơn và hội thoại gắn với đơn:`)
      + bang(['Nguồn', 'Đơn', 'Đã hủy', 'Còn “Mới”', 'Trạng thái'],
          dn.nguon.map(n => [`<b>${H(n.ten)}</b>`, `<b>${n.so}</b>`, n.huy, n.moi, `<span style="white-space:normal;display:block;text-align:left">${H(n.trang_thai.slice(0,7).map(([t,c]) => t + ' ' + c).join(' · '))}</span>`]))
      + doan(`Theo ngày: ${dn.nguon.map(n => H(n.ten) + ' — ' + n.theo_ngay.map(([d,c]) => d.slice(8,10) + '/' + d.slice(5,7) + ': ' + c).join(', ')).join('; ')}.`);
    if(dn.theo_page && dn.theo_page.length)
      ra += bang(['Page', 'Tổng đơn chat', 'AI chat → đơn', 'Tool lên trên chat sale', 'Sale tự lên'],
          dn.theo_page.map(r => [H(r.page), `<b>${r.tong}</b>`, r['AI chat rồi tool tự lên đơn'], r['Tool tự lên đơn trên chat của sale'], r['Sale tự lên từ chat']]));
    const p = dn.pheu, h = dn.ho_so || {};
    ra += doan(`<b>Phễu của AI:</b> ${p.ai_soan} hội thoại AI gửi câu thật → <b>${p.khach_rep}</b> khách nhắn lại (${pct(p.khach_rep, p.ai_soan)}) → <b>${p.co_don}</b> hội thoại ra đơn (${pct(p.co_don, p.ai_soan)}).`);
    if(h.tong) ra += doan(`Hồ sơ khách AI theo dõi: ${h.tong} — có SĐT ${h.sdt}, có địa chỉ ${h.dia_chi}, đủ cả hai ${h.ca_hai}; có SĐT mà chưa có đơn ${h.sdt_chua_don}. Bước đang đứng: ${H(h.buoc.map(([b,c]) => b + ' ' + c).join(', '))}.`);
    ra += `<p style="margin-top:10px"><b>Vì sao ít:</b></p><ol style="margin:4px 0 0;padding-left:22px;display:flex;flex-direction:column;gap:6px">
      <li>${100 - Math.round(p.khach_rep/Math.max(p.ai_soan,1)*100)}% khách không nhắn lại sau câu AI. Một phần lớn vì câu chỉ nằm trong ghi chú do page bị Facebook chặn — khách không hề nhận được, nên không thể trả lời.</li>
      <li>Khách từ quảng cáo phần lớn hỏi giá rồi im. Botcake im thì AI mới vào; AI trả lời được câu hỏi chứ không tạo ra nhu cầu mua.</li>
      <li>Đơn AI lên đang nằm ở trạng thái “Mới” chờ sale xác nhận (${dn.nguon[0].moi} đơn) — chưa được tính là chốt, không phải AI không lên.</li>
      <li>Page chưa có SKU: AI chat xong không lên đơn được (xem mục 5). Gắn SKU là có đơn ngay từ những hội thoại đang treo.</li>
      <li>Tỉ lệ hủy của đơn AI (${dn.nguon[0].huy}/${dn.nguon[0].so}) thấp hơn đơn sale tự lên (${dn.nguon[2].huy}/${dn.nguon[2].so}) — đơn ít nhưng chắc.</li></ol>`;
  } else if(dn.loi) ra += doan('Không đọc được đơn POS: ' + H(dn.loi));
  // 7. Phủ toàn bộ page tài khoản
  const tb = k.toan_bo;
  if(tb){
    const hs = tb.he_so, ds = tb.theo_tt.filter(r => r[4]);
    const t = i => ds.reduce((a, r) => a + (r[i] || 0), 0);
    ra += `<h3 style="font-size:16px;margin:18px 0 8px">7. Nếu AI phủ toàn bộ ${tb.so_page} page của tài khoản (mọi thị trường) thì tốn bao nhiêu?</h3>`
      + doan(`Quét thống kê Pancake “khách nhắn inbox” 7 ngày cho từng page lúc ${H(tb.luc)}. Hệ số đo từ UAE 10–12/09: mỗi khách nhắn tốn ${hs.goi_moi_khach.toFixed(2)} lượt gọi model, Kimi thật $${hs.kimi_moi_khach.toFixed(4)}, tool tính $${hs.tool_moi_khach.toFixed(4)}.${hs.nay_moi_khach ? ` Nhà đang chạy <b>${NT(hs.nha_nay)}</b> đo lại hôm nay trên ${(hs.luot_do_nay||0).toLocaleString()} lượt: $${hs.gia_luot_nay.toFixed(6)}/lượt → $${hs.nay_moi_khach.toFixed(6)}/khách nhắn, rẻ hơn Kimi ${(hs.kimi_moi_khach/hs.nay_moi_khach).toFixed(1)} lần.` : ''} Nhân lên cho từng thị trường:`)
      + bang(['Thị trường', 'Page', 'Còn gói', 'Có khách', 'Khách nhắn/ngày', 'Gọi model/ngày',
              hs.nay_moi_khach ? NT(hs.nha_nay) + ' thật $/tháng' : 'Kimi thật $/tháng',
              'Kimi thật $/tháng', 'Tool tính $/tháng', hs.nay_moi_khach ? NT(hs.nha_nay) + ' thật đ/tháng' : 'Kimi thật đ/tháng'],
          ds.map(r => [`<b>${H(r[0])}</b>`, r[1], r[2], r[3], Math.round(r[5]), Math.round(r[6]),
                       `<b>${(r[9] != null ? r[9] : r[7]).toFixed(1)}</b>`, r[7].toFixed(1), r[8].toFixed(1),
                       vnd((r[9] != null ? r[9] : r[7])*26300)])
            .concat([[`<b>TỔNG</b>`, t(1), t(2), t(3), Math.round(t(5)), Math.round(t(6)),
                      `<b>${(ds[0] && ds[0][9] != null ? t(9) : t(7)).toFixed(1)}</b>`, t(7).toFixed(1), t(8).toFixed(1),
                      `<b>${vnd((ds[0] && ds[0][9] != null ? t(9) : t(7))*26300)}</b>`]]))
      + doan(`Chỉ <b>${tb.con_goi}</b> page còn gói Pancake là đọc được hội thoại; ${tb.so_page - tb.con_goi} page hết gói thì AI không đụng được dù trả bao nhiêu tiền model. Saudi chiếm hơn nửa lưu lượng. Gỡ chặn Facebook làm khách trả lời nhiều hơn, cộng khoảng 30%; đổi DeepSeek Flash thì chia thêm 4–7 lần.`)
      + doan(`Page đông khách nhất 7 ngày: ${tb.top.slice(0,10).map(([n,tt,ib,g]) => H(n) + ' (' + tt + ', ' + ib + (g ? '' : ', hết gói') + ')').join('; ')}.`);
  }
  return ra + `</section>`;
}
function veTongUoc(){
  const db = S.db;
  if(!db) return `<section><h2>Ước lượng khi chạy đầy tải</h2><div class="trong">Chưa có số đo —
    sang tab <b>Đo lại</b> và bấm Đo (quét hội thoại thật, không gọi model, không tốn xu nào).</div></section>`;
  const dang = khoaGia(S.cf.model) || khoaGia(S.cf.nha === 'deepseek' ? 'deepseek-flash' : 'kimi-k3') || 'kimi-k3';
  const re = Object.keys(db.gia).reduce((a,b) =>
    tinh(b, db.tran_ngay)[1] < tinh(a, db.tran_ngay)[1] ? b : a);
  const td = tinh(dang, db.tran_ngay), tr = tinh(re, db.tran_ngay);
  const nap = Math.max(10, Math.round(tinh(re, db.tran_ngay)[1]/3/5)*5);
  return `<section><h2>Ước lượng khi chạy đầy tải — nạp bao nhiêu thì đủ?</h2>
    <p class="phu">Đo hội thoại thật ${db.gio} giờ gần nhất — ${S.so_page} page có khách nhắn
    trên tổng ${S.so_page_bat} page đang bật. Không gọi model nên chưa tốn xu nào.</p></div>
  <section><div class="the-lon">
    <p style="font-size:18px;font-weight:700">Chạy đầy tải: khoảng
      <b>${n0(db.tran_ngay)} lượt gọi model mỗi ngày</b>.</p>
    <div class="doi">
      <div class="o"><span class="nhan-o">Giữ ${H(dang)}</span>
        <span class="to so">${kr(td[0],td[1])}</span><span class="ghi">mỗi tháng</span></div>
      <div class="o"><span class="nhan-o">Đổi sang ${H(re)}</span>
        <span class="to xanh so">${kr(tr[0],tr[1])}</span><span class="ghi">mỗi tháng</span></div>
      <div class="o"><span class="nhan-o">Nên nạp lần đầu</span>
        <span class="to so">$${n0(nap)}</span>
        <span class="ghi">đủ ~10 ngày đầy tải với ${H(re)}</span></div>
    </div>
    <p class="phu">Đây là <b>khoảng</b>, không phải con số chốt: máy không có bộ tách token của
    Kimi/DeepSeek/Claude nên chỉ ước từ số ký tự. Muốn số thật ngay: tab <b>Cấu hình</b> → <b>Thử key</b>.
    </p></div></section>
  <section><h2>Vì sao có hai con số</h2><div class="cuon"><table><tbody>
    <tr><td><b>SÀN — ${n0(db.san_ngay)} lượt/ngày</b><br>
      <span class="phu">Chỉ những lượt AI buộc phải vào cuộc lúc đo: Botcake im, hoặc Botcake
      đã trả lời mà AI phải đọc lại xem có trúng không.</span></td>
      <td class="so">${kr(...tinh(dang, db.san_ngay))}<br><span class="phu">mỗi tháng</span></td></tr>
    <tr><td><b>TRẦN — ${n0(db.tran_ngay)} lượt/ngày</b><br>
      <span class="phu">Cộng ${n0(db.n_im)} lượt hôm nay sale thật đã trả lời trước. Chạy thật
      thì AI chỉ đợi Botcake ~90 giây rồi nhắn, tức vào <b>trước</b> sale.
      <b>Lấy cột trần mà quyết ngân sách.</b></span></td>
      <td class="so">${kr(td[0],td[1])}<br><span class="phu">mỗi tháng</span></td></tr>
  </tbody></table></div></section>
  <section><h2>Lưu lượng đo được</h2><div class="luoi">
    ${[['Lượt khách / ngày', n0(db.quet_ngay), db.quet + ' lượt trong ' + db.gio + ' giờ'],
       ['Page có khách nhắn', S.so_page, 'trên tổng ' + S.so_page_bat + ' page đang bật'],
       ['Sàn — gọi model/ngày', n0(db.san_ngay), Math.round(db.san/db.quet*100) + '% lượt quét'],
       ['Trần — gọi model/ngày', n0(db.tran_ngay), Math.round(db.tran/db.quet*100) + '% lượt quét'],
       ['Gói prompt / lượt', n0(db.ky_tu_goi), 'ký tự → ' + n0(db.tok_vao[0]) + '–'
         + n0(db.tok_vao[1]) + ' token']
      ].map(([a,b,c]) => `<div class="the"><span class="nhan-o">${a}</span>
        <span class="so-to so">${b}</span><span class="ghi">${H(c)}</span></div>`).join('')}
  </div></section>
  ${S.n_hoi ? `<section><h2>Khách hỏi gì</h2><div class="thanhds">${
    S.hoi.map(([t,k]) => `<div class="dong"><div><div>${H(t)}</div>
      <div class="ray"><i style="width:${k/S.hoi[0][1]*100}%"></i></div></div>
      <div class="pt so">${Math.round(k/S.n_hoi*100)}%</div></div>`).join('')}</div>
    <p class="phu" style="margin-top:12px">Trên ${n0(S.n_hoi)} tin cuối của khách. Nhóm nào cao
    mà kịch bản “Trả lời nhanh” của page chưa có mẫu thì AI phải tự xoay — đó là chỗ đáng bổ
    sung trước khi cho chạy thật.</p></section>` : ''}`;
}

/* ── Cấu hình ── */
function veCauHinh(){
  const c = S.cf, dsm = S.db ? Object.keys(S.db.gia) : ['kimi-k2','kimi-k3','claude-haiku'];
  return `<div class="dau-trang"><h1>Cấu hình</h1>
    <p class="phu">Lưu là ghi thẳng vào <code>.env</code>. Bản cũ chép sang
    <code>.env.bak</code> mỗi lần lưu.</p></div>
  <section><div class="hop"><div class="hang">
    <label>Nhà cung cấp<select id="f_nha">${['kimi','deepseek','anthropic'].map(x =>
      `<option${c.nha===x?' selected':''}>${x}</option>`).join('')}</select>
      <span class="gt">Đổi nhà thì nhớ dán key tương ứng</span></label>
    <label>Model<input id="f_model" list="dsm" value="${H(c.model_env)}"
      placeholder="trống = mặc định của nhà">
      <datalist id="dsm">${dsm.map(x=>`<option value="${x}">`).join('')}</datalist>
      <span class="gt" id="gt_model"></span></label>
    <label>Độ sáng tạo<input id="f_nd" type="number" min="0" max="1" step="0.1"
      value="${c.nhiet_do==null?'':c.nhiet_do}" placeholder="trống = mặc định 1.0">
      <span class="gt">0.3 cho câu bám kịch bản · 1.0 là bay nhất</span></label>
    <label>Trần chi mỗi ngày (USD)<input id="f_nsn" type="number" min="0" step="0.5"
      value="${c.ns_ngay}" placeholder="trống = không chặn">
      <span class="gt">Vượt là vòng chạy tự dừng giữa chừng</span></label>
    <label>Trần chi cộng dồn (USD)<input id="f_nst" type="number" min="0" step="1"
      value="${c.ns_tong}" placeholder="trống = không chặn">
      <span class="gt">Chặn tổng, tính từ sổ chi phí</span></label>
    <label>Key Kimi<input id="f_kk" type="password" autocomplete="off"
      placeholder="${c.co_key.kimi?'đã có — để trống là giữ nguyên':'chưa dán'}">
      <span class="gt">${c.co_key.kimi?'Đang có key':'Chưa có key'} · chỉ lưu vào .env máy này</span></label>
    <label>Key DeepSeek<input id="f_kd" type="password" autocomplete="off"
      placeholder="${c.co_key.deepseek?'đã có — để trống là giữ nguyên':'chưa dán'}">
      <span class="gt">${c.co_key.deepseek?'Đang có key':'Chưa có key'} · lấy ở platform.deepseek.com → API keys</span></label>
    <label>Key Anthropic<input id="f_ka" type="password" autocomplete="off"
      placeholder="${c.co_key.anthropic?'đã có — để trống là giữ nguyên':'chưa dán'}">
      <span class="gt">${c.co_key.anthropic?'Đang có key':'Chưa có key'}</span></label>
  </div>
  <div id="uoc" style="margin-top:19px"></div>
  <div class="thanh-nut">
    <button class="nut" id="luu" disabled>Lưu cấu hình</button>
    <button class="nut vien" id="thu">Thử key</button>
    <span class="phu" id="tt_luu">Chưa có thay đổi nào</span>
  </div>
  <p class="phu" style="margin-top:14px"><b>Thử key</b> gọi model đúng một lượt cực ngắn — tốn
  cỡ vài phần nghìn xu, nhưng cho biết ngay key có dùng được không và <b>số token thật</b> thay
  cho ước lượng. Không sửa được <code>PANCAKE_*</code> ở đây: token Pancake hỏng là cả hệ thống
  lên đơn chết, việc đó phải làm có ý thức bằng tay.</p>
  <div id="kq_thu" style="margin-top:14px"></div>
  </div></section>`;
}
function sauCauHinh(){
  const ids = ['f_nha','f_model','f_nd','f_nsn','f_nst','f_kk','f_kd','f_ka'];
  const goc = JSON.stringify(ids.map(i => $('#'+i).value));
  const doi = () => {
    const ban = JSON.stringify(ids.map(i => $('#'+i).value)) !== goc;
    BAN = ban; $('#luu').disabled = !ban;
    $('#tt_luu').textContent = ban ? 'Có thay đổi chưa lưu' : 'Chưa có thay đổi nào';
    veUoc();
  };
  ids.forEach(i => $('#'+i).oninput = doi);
  $('#f_nha').onchange = doi;
  veUoc();
  $('#luu').onclick = async () => {
    $('#luu').disabled = true;
    try{
      await api('cau-hinh', {AI_PROVIDER:$('#f_nha').value, AI_MODEL:$('#f_model').value.trim(),
        AI_TEMPERATURE:$('#f_nd').value.trim(), AI_NGAN_SACH_NGAY:$('#f_nsn').value.trim(),
        AI_NGAN_SACH_TONG:$('#f_nst').value.trim(), KIMI_API_KEY:$('#f_kk').value,
        DEEPSEEK_API_KEY:$('#f_kd').value, ANTHROPIC_API_KEY:$('#f_ka').value});
      BAN = false; bao('Đã lưu vào .env'); await tai();
    }catch(e){ bao('Lưu hỏng: ' + e.message, 1); $('#luu').disabled = false; }
  };
  $('#thu').onclick = async () => {
    const b = $('#thu'); b.disabled = true;
    b.innerHTML = '<span class="quay"></span>Đang gọi model…';
    try{
      const r = await api('kiem-key', {});
      const t = r.token || {};
      $('#kq_thu').innerHTML = r.ok
        ? `<div class="tot">Key dùng được. ${H(r.nha)} / ${H(r.model)} — token thật lượt này:
           vào ${n0(t.vao||0)} · đọc đệm ${n0(t.doc_dem||0)} · ra ${n0(t.ra||0)} ·
           tốn ${usd(r.tien||0)}.` + ((t.doc_dem||0)===0
             ? ' Đọc đệm bằng 0 ở lượt đầu là bình thường — phải chạy vài lượt liên tiếp mới biết đệm có chạy không.' : '')
           + '</div>'
        : `<div class="xau">Key KHÔNG dùng được — ${H(r.loi)}</div>`;
      await tai();
    }catch(e){ $('#kq_thu').innerHTML = `<div class="xau">${H(e.message)}</div>`; }
    b.disabled = false; b.textContent = 'Thử key';
  };
}
function veUoc(){
  const db = S.db, ma = khoaGia($('#f_model').value.trim() ||
    ({kimi:'kimi-k3', deepseek:'deepseek-flash', anthropic:'claude-opus-5'}[$('#f_nha').value] || 'claude-opus-5'));
  $('#gt_model').textContent = ma ? 'Khớp bảng giá: ' + ma
    : 'Chưa có trong bảng giá — tiền sẽ tính theo bậc đắt nhất';
  if(!db || !ma){ $('#uoc').innerHTML = ''; return; }
  const t = tinh(ma, db.tran_ngay), s = tinh(ma, db.san_ngay), d = tinh(ma, db.tran_ngay, 1);
  $('#uoc').innerHTML = `<div class="luoi">
    <div class="the"><span class="nhan-o">Sàn / tháng</span>
      <span class="so-to so">${kr(s[0],s[1])}</span><span class="ghi">${n0(db.san_ngay)} lượt/ngày</span></div>
    <div class="the"><span class="nhan-o">Trần / tháng</span>
      <span class="so-to so">${kr(t[0],t[1])}</span><span class="ghi">${n0(db.tran_ngay)} lượt/ngày</span></div>
    <div class="the"><span class="nhan-o">Trần nếu đệm chạy</span>
      <span class="so-to so">${kr(d[0],d[1])}</span><span class="ghi">Claude và DeepSeek có đệm tự chạy; Kimi chưa đo được</span></div>
    <div class="the"><span class="nhan-o">Trần / ngày</span>
      <span class="so-to so">${usd(t[1]/30)}</span><span class="ghi">gợi ý cho ô trần chi mỗi ngày</span></div>
  </div>`;
}

/* ── Hướng dẫn trả lời ── */
function veLuat(){
  return `<div class="dau-trang"><h1>Hướng dẫn trả lời</h1>
    <p class="phu">Đây là <b>thứ duy nhất gửi cho model</b> mỗi lượt, cùng với kịch bản
    “Trả lời nhanh” của từng page trên Pancake. Lưu ở <code>luat_model.md</code>.
    File <code>LUAT_AI_SALE.md</code> là sổ luật cho người đọc — sửa mình nó thì AI
    <b>không</b> đổi hành vi.</p></div>
  <section><div class="hop">
    <label>Nội dung<textarea id="f_luat" spellcheck="false">${H(S.luat)}</textarea>
      <span class="gt" id="dem_luat"></span></label>
    <div class="thanh-nut">
      <button class="nut" id="luu_luat" disabled>Lưu hướng dẫn</button>
      <button class="nut nhe" id="goc_luat">Khôi phục bản gốc</button>
      <span class="phu" id="tt_luat">Chưa có thay đổi nào</span>
    </div>
    <p class="phu" style="margin-top:14px">Vòng chạy sau đọc ngay bản mới, không cần khởi động
    lại gì. Bản cũ chép sang <code>luat_model.md.bak</code>. Sửa xong nên chạy
    <code>ai_sale.py chay ${H(S.mkey||'usa')} --so 5</code> (chạy thử, không gửi) để xem AI
    soạn ra câu gì trước khi cho gửi thật.</p>
  </div></section>`;
}
function sauLuat(){
  const t = $('#f_luat'), goc = t.value;
  const dem = () => {
    const ban = t.value !== goc;
    BAN = ban; $('#luu_luat').disabled = !ban;
    $('#tt_luat').textContent = ban ? 'Có thay đổi chưa lưu' : 'Chưa có thay đổi nào';
    $('#dem_luat').textContent = n0(t.value.length) + ' ký tự · phần này đi kèm MỌI lượt gọi '
      + 'model, dài thêm là tốn thêm tiền mỗi lượt';
  };
  t.oninput = dem; dem();
  $('#luu_luat').onclick = async () => {
    $('#luu_luat').disabled = true;
    try{ await api('luat', {noi_dung: t.value}); BAN = false;
         bao('Đã lưu luat_model.md'); await tai(); }
    catch(e){ bao('Lưu hỏng: ' + e.message, 1); $('#luu_luat').disabled = false; }
  };
  $('#goc_luat').onclick = () => {
    if(!confirm('Thay nội dung đang soạn bằng bản gốc nhúng trong code?')) return;
    t.value = S.luat_goc; dem(); bao('Đã đưa về bản gốc — nhớ bấm Lưu');
  };
}

/* ── Tiền nong ── */
function veTien(){
  const t = S.tien, con = t.nap - t.da_chi, sd = t.so_du || {};
  return `<div class="dau-trang"><h1>Tiền nong</h1>
    <p class="phu">Kimi và DeepSeek có API trả số dư thật — ô <b>Số dư thật</b> hỏi thẳng nhà model,
    đó là con số phanh chi tiêu dùng. Anthropic không có API nên phải tự khai. Tiền chi
    thì tự ghi sổ mỗi lượt gọi model.</p></div>
  <section><div class="luoi">
    ${[sd.co ? ['Số dư thật', usd2(sd.con), 'hỏi API ' + NT() + (sd.voucher ? ' · voucher ' + usd2(sd.voucher) : '')]
             : ['Số dư thật', '?', H(sd.loi || 'nhà này không có API số dư')],
       ['Đã nạp', usd(t.nap), 'nhà ' + S.cf.nha], ['Đã chi', usd(t.da_chi), 'cộng dồn'],
       ['Còn lại', usd(con), 'theo số đã khai'],
       ['Hôm nay', usd(t.hom_nay), S.cf.ns_ngay ? 'trần ' + usd(+S.cf.ns_ngay) : 'chưa đặt trần']
      ].map(([a,b,c]) => `<div class="the"><span class="nhan-o">${a}</span>
        <span class="so-to so">${b}</span><span class="ghi">${H(c)}</span></div>`).join('')}
  </div></section>
  <section><h2>Khai tiền vừa nạp</h2><div class="hop"><div class="hang">
    <label>Số tiền (USD)<input id="n_so" type="number" min="0" step="1" placeholder="20"></label>
    <label>Nhà<select id="n_nha">${['kimi','deepseek','anthropic'].map(x =>
      `<option${S.cf.nha===x?' selected':''}>${x}</option>`).join('')}</select></label>
    <label>Ghi chú<input id="n_gc" type="text" placeholder="nạp lần 1"></label>
  </div><div class="thanh-nut"><button class="nut" id="n_luu">Ghi vào sổ</button></div></div>
  </section>
  <section><h2>Đã khai</h2>${S.nap_ds.length ? `<div class="cuon"><table>
    <thead><tr><th>Lúc</th><th>Nhà</th><th>Số tiền</th><th>Ghi chú</th></tr></thead><tbody>
    ${S.nap_ds.map(x => `<tr><td>${H(x.luc)}</td><td>${H(x.nha)}</td>
      <td class="so">${usd(x.so_tien)}</td><td>${H(x.ghi_chu||'')}</td></tr>`).join('')}
    </tbody></table></div>` : '<div class="trong">Chưa khai lần nạp nào.</div>'}</section>
  ${t.theo_page.length ? `<section><h2>Đã chi theo page</h2><div class="cuon"><table>
    <thead><tr><th>Page</th><th>Đã chi</th></tr></thead><tbody>
    ${t.theo_page.map(([p,v]) => `<tr><td>${H(p)}</td><td class="so">${usd(v)}</td></tr>`).join('')}
    </tbody></table></div></section>`
   : `<section><h2>Đã chi theo page</h2><div class="trong">Chưa tiêu đồng nào — chưa có vòng
      <code>ai_sale.py chay</code> nào gọi model.</div></section>`}`;
}
function sauTien(){
  $('#n_luu').onclick = async () => {
    const so = parseFloat($('#n_so').value);
    if(!(so > 0)) return bao('Nhập số tiền đã', 1);
    $('#n_luu').disabled = true;
    try{ await api('nap', {so_tien: so, nha: $('#n_nha').value, ghi_chu: $('#n_gc').value});
         bao('Đã ghi vào sổ'); await tai(); }
    catch(e){ bao('Hỏng: ' + e.message, 1); $('#n_luu').disabled = false; }
  };
}

/* ── Hiệu suất ──
   Ba câu chủ shop hỏi 10/09: một tin tốn bao nhiêu · AI xử lý bao nhiêu / tổng lượt khách ·
   page nào Botcake im nhiều. Số lấy nguyên từ state/<tt>/hieu_suat.json do hieu_suat.py ghi —
   trang chỉ vẽ lại, không tính gì thêm để web và terminal không bao giờ lệch nhau. */
function veHS(){
  if(!(TT||S.mkey)) return canMkey('Hiệu suất');
  return `<div class="dau-trang"><h1>Hiệu suất AI</h1>
    <p class="phu">Một tin AI tốn bao nhiêu · AI xử lý bao nhiêu trên tổng lượt khách nhắn ·
    page nào Botcake im nhiều nên AI và sale phải gánh. Đọc lại hội thoại thật trên Pancake —
    không gọi model, không tốn xu nào — quét khoảng 6 phút.</p></div>
  <section><div class="hop"><div class="hang">
    <label>Cửa sổ đo<select id="hs_gio">
      <option value="24">24 giờ gần nhất</option><option value="12">12 giờ gần nhất</option>
      <option value="48">48 giờ gần nhất</option><option value="72">72 giờ gần nhất</option></select>
      <span class="gt">Luôn có thêm dòng riêng “từ lúc AI gửi thật”</span></label>
    <label>Bắt đầu tính từ<select id="hs_that">
      <option value="0">đủ cửa sổ</option>
      <option value="1">lúc AI gửi thật lần đầu trong cửa sổ</option></select>
      <span class="gt">Chọn dòng dưới khi muốn bảng page chỉ tính đoạn AI có mặt</span></label>
  </div><div class="thanh-nut"><button class="nut" id="hs_chay">Đo ngay</button>
    <span class="phu" id="hs_tt"></span></div></div></section>
  <div id="hs_noi"><p class="phu"><span class="quay"></span>Đang đọc lần đo gần nhất…</p></div>
  <section><h2>Nhật ký lần đo</h2><pre class="log" id="hs_log">chưa chạy lần nào trong phiên này</pre>
  </section>`;
}
function veHSKq(kq){
  if(!kq) return `<div class="trong">Chưa đo lần nào cho thị trường này — bấm <b>Đo ngay</b>.</div>`;
  const T = kq.tong_that || kq.tong, tien = kq.tien, th = tien.that, mt = tien.moi_tin, v = tien.viec;
  const gioVN = ts => ts ? new Date(ts*1000).toLocaleString('vi-VN',
    {timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : '?';
  const pct = (a,b) => b ? Math.round(a/b*100)+'%' : '—';
  const usd4 = x => x==null ? '—' : '$'+Number(x).toFixed(4);
  const giay = x => x==null ? '—' : x<120 ? Math.round(x)+'s' : x<7200 ? Math.round(x/60)+' phút'
    : (x/3600).toFixed(1)+' giờ';
  const L = T.luot, xl = T.xu_ly||{}, xb = T.xu_ly_bot_im||{}, sd = T.sale_do||{}, tr = T.tre||{};
  const moiGio = th.gio_co_chay ? th.tien/th.gio_co_chay : 0;
  const bang = (kq.bang_that || kq.bang || []).filter(p => p.luot);
  const chip = dg => { const c = dg.startsWith('Botcake KÉM') ? 'bac0' : dg.startsWith('Botcake trung') ? 'bac2'
    : dg.startsWith('Botcake tốt') ? 'bac4' : dg.startsWith('chưa') ? 'bac1' : 'bac3';
    return `<span class="bac ${c}">${H(dg)}</span>`; };
  const kem = bang.filter(p => p.danh_gia.startsWith('Botcake KÉM')).sort((a,b) => b.bot_im-a.bot_im).slice(0,10);
  const loi = (T.page_loi||[]);
  return `
  <p class="phu" style="margin-bottom:16px">Đo lúc <b>${gioVN(kq.luc)}</b> giờ VN · cửa sổ ${gioVN(kq.tu)} → ${gioVN(kq.den)}
    ${kq.tong_that ? ` · mục 2 và 3 tính <b>từ lúc AI gửi thật</b> (${gioVN(kq.tu_that)}), mục 1 tính trọn cửa sổ` : ''}
    · ${T.page} page đọc được, ${T.page_co_botcake} có Botcake · quét mất ${kq.mat_giay}s.</p>
  ${loi.length ? `<div class="canh-bao" style="margin-bottom:16px">${loi.length} page không đọc được (token hỏng):
    ${H(loi.map(x => x.split(':')[0]).join(' · '))} — chữa: <code>auto_len_don.py setup ${H(kq.mkey)} --force-token --hong</code></div>` : ''}
  ${T.anh_tro ? `<div class="xau" style="margin-bottom:16px">${T.anh_tro} ảnh AI gửi KHÔNG kèm chữ — page bị Facebook
    chặn chữ (#2022) nhưng ảnh mẫu vẫn đi, khách nhận ảnh trơ.</div>` : ''}
  ${T.api_la ? `<div class="canh-bao" style="margin-bottom:16px">${T.api_la} tin “Public API” không khớp sổ việc của AI Sale —
    hệ khác đang gửi tin qua API bằng cùng tài khoản.</div>` : ''}
  <section><h2>1 · Một tin tốn bao nhiêu — vòng thật</h2><div class="luoi">
    ${[['1 tin gửi tới khách', usd4(mt.gui), v.gui + ' tin gửi thẳng'],
       ['1 tin AI soạn ra', usd4(mt.soan), 'kể cả ' + v.ghi_chu + ' tin soạn vào ghi chú (page bị FB chặn)'],
       ['1 lượt gọi model', usd4(mt.goi), th.goi + ' lượt · ' + (th.model||'')],
       ['1 lượt khách AI xét', usd4(mt.su_kien), th.su_kien + ' lượt xét, phần lớn im không tốn'],
       ['Đã chi trong cửa sổ', usd4(th.tien), 'vòng thử tốn thêm ' + usd4(tien.thu.tien) + ' (' + tien.thu.goi + ' lượt, không gửi)'],
       ['Gọi rồi quyết định im', pct(th.tien_im, th.tien), th.goi_im + ' lượt = ' + usd4(th.tien_im) + ' — chủ yếu cửa “Botcake đã rep, đọc lại”'],
       ['Đọc từ bộ nhớ đệm', pct(th.doc_dem, th.vao + th.doc_dem), n0((th.vao + th.doc_dem)/Math.max(th.goi,1)) + ' vào + ' + n0(th.ra/Math.max(th.goi,1)) + ' ra mỗi lượt'],
       ['Ước theo nhịp hiện tại', '$' + (moiGio*24).toFixed(2) + '/ngày', '≈ $' + (moiGio*24*30).toFixed(0) + '/tháng · ' + th.gio_co_chay + ' giờ có chạy thật · ước thô'],
      ].map(([a,b,c]) => `<div class="the"><span class="nhan-o">${a}</span><span class="so-to so">${b}</span>
        <span class="ghi">${H(c)}</span></div>`).join('')}
  </div></section>
  <section><h2>2 · AI xử lý bao nhiêu trên ${n0(L)} lượt khách nhắn</h2>
    <div class="thanhds">${[['Botcake trả lời trong 5 phút', T.bot], ['AI xử lý', T.ai_xu_ly],
        ['Sale trả lời', T.sale], ['Không ai trả lời', T.trong]
      ].map(([t,k]) => `<div class="dong"><div><div>${t} <span class="phu">· ${n0(k)}</span></div>
        <div class="ray"><i style="width:${L ? k/L*100 : 0}%"></i></div></div>
        <div class="pt so">${pct(k,L)}</div></div>`).join('')}</div>
    <p class="phu" style="margin-top:12px">AI xử lý ${n0(T.ai_xu_ly)} lượt = nhắn thẳng ${n0(xl.nhan||0)} ·
      soạn vào ghi chú vì page bị FB chặn ${n0(xl.ghi_chu||0)} · treo cho sale ${n0(xl.treo||0)} ·
      cổng chặn giữ lại ${n0(xl.chan||0)}. Nhắn đè lên Botcake ${n0(T.bot_va_ai)} · nhắn sau hơn 10 phút
      ${n0(T.ai_muon)} · đang chờ ${n0(T.cho)}. Một lượt có thể được nhiều bên trả lời nên các thanh cộng lại có thể quá 100%.</p>
    <div class="cuon" style="margin-top:16px"><table><thead><tr>
      <th>Botcake im ở ${n0(T.bot_im)} lượt (${pct(T.bot_im,L)}) — AI đã làm gì với chúng</th><th>Lượt</th><th>Tỉ lệ</th>
      </tr></thead><tbody>
      ${[['AI xử lý (nhắn · ghi chú · treo · cổng chặn)', T.ai_xu_ly_bot_im],
         ['AI cố ý im theo luật — thẻ Đã gửi, khách đã mua, sale đã vào (0 token)', xb.im_luat||0],
         ['AI không thấy — sale rep trước khi vòng dò 15 giây bắt được', xb.khong_thay||0],
         ['Model đọc rồi quyết định im (có tốn tiền)', xb.im_model||0],
         ['<b>AI bỏ lọt</b> — không thấy hoặc model im, mà sale phải vào sau 5 phút hoặc không ai trả lời', T.bo_lot]
        ].map(([t,k]) => `<tr><td style="white-space:normal">${t}</td><td class="so">${n0(k)}</td>
          <td class="so">${pct(k,T.bot_im)}</td></tr>`).join('')}
    </tbody></table></div>
    <p class="phu" style="margin-top:12px">Sale vào khi AI không làm gì: dưới 1 phút ${n0(sd.duoi_1p||0)} (nhanh hơn AI)
      · 1–5 phút ${n0(sd['1_5p']||0)} · 5–30 phút ${n0(sd['5_30p']||0)} · sau 30 phút ${n0(sd.tren_30p||0)}.
      Tốc độ trả lời (trung vị / p95): Botcake ${giay(tr.botcake&&tr.botcake.p50)} / ${giay(tr.botcake&&tr.botcake.p95)}
      · AI ${giay(tr.ai&&tr.ai.p50)} / ${giay(tr.ai&&tr.ai.p95)} · sale ${giay(tr.nguoi&&tr.nguoi.p50)} / ${giay(tr.nguoi&&tr.nguoi.p95)}.</p>
  </section>
  <section><h2>3 · Theo page — AI đang phải gánh ở đâu</h2>
    <div class="cuon rong"><table><thead><tr><th>Page</th><th>Botcake</th><th>Lượt</th><th>Botcake im</th>
      <th>AI xử lý</th><th>AI nhắn</th><th>Sale</th><th>Trống</th><th>Tiền AI</th><th class="trai">Đánh giá</th></tr></thead><tbody>
      ${bang.map(p => `<tr><td>${H(p.page)}</td><td>${p.co_botcake ? 'có' : 'không'}</td><td class="so">${p.luot}</td>
        <td class="so">${pct(p.bot_im,p.luot)}</td><td class="so">${pct(p.ai_xu_ly,p.luot)}</td>
        <td class="so">${(p.xu_ly||{}).nhan||0}</td><td class="so">${pct(p.sale,p.luot)}</td>
        <td class="so">${pct(p.trong,p.luot)}</td><td class="so">${usd4(p.tien)}</td>
        <td class="trai">${chip(p.danh_gia)}</td></tr>`).join('')}
    </tbody></table></div>
    <p class="phu" style="margin-top:12px">Botcake im = không trả lời trong 5 phút (tin bot đến sau hàng giờ là
      follow-up tự động, không tính). AI xử lý = nhắn thẳng + soạn vào ghi chú + treo + cổng chặn giữ.
      Page có Botcake mà im quá nửa lượt là Botcake set chưa hiệu quả — AI và sale đang gánh phần đó.</p>
  </section>
  ${kem.length ? `<section><h2>Botcake set chưa hiệu quả — ${kem.length} page, câu khách hỏi mà bot im</h2>
    ${kem.map(p => `<div class="mau"><div class="tk">${H(p.page)}</div>
      <div class="meta">Botcake im ${p.bot_im}/${p.luot} lượt · AI xử lý ${p.ai_xu_ly} · sale ${p.sale} · tiền AI ${usd4(p.tien)}</div>
      <div class="noi">${(p.vi_du_bot_im||[]).slice(0,4).map(x => `[${H(x.ai)}] ${H(x.khach)}: ${H(x.tin)}`).join('\n')}</div></div>`).join('')}
    <p class="phu">Đây là những câu cần thêm từ khoá vào Botcake của page đó. Nhãn trong ngoặc là ai đã đỡ câu này.</p>
  </section>` : ''}`;
}
async function sauHS(){
  const ve1 = st => {
    const b = $('#hs_chay'); if(!b) return;
    b.disabled = st.chay;
    b.innerHTML = st.chay ? '<span class="quay"></span>Đang đo…' : 'Đo ngay';
    $('#hs_tt').textContent = st.chay ? 'đang quét hội thoại thật, trang tự cập nhật khi xong' : (st.xong || '');
    if(st.log){ const p = $('#hs_log'); const duoi = p.scrollTop + p.clientHeight >= p.scrollHeight - 30;
      p.textContent = st.log; if(duoi) p.scrollTop = p.scrollHeight; }
  };
  let truoc = null;
  const dieu = async () => {
    if(TAB !== 'hieusuat' || !$('#hs_noi')) return;
    let d;
    try{ d = await api('hieu-suat'); }
    catch(e){ $('#hs_noi').innerHTML = `<div class="xau">${H(e.message)}</div>`; return; }
    ve1(d.trang_thai);
    if(truoc === null || truoc !== d.trang_thai.chay){ $('#hs_noi').innerHTML = veHSKq(d.kq); }
    truoc = d.trang_thai.chay;
    clearTimeout(TIMER);
    if(d.trang_thai.chay) TIMER = setTimeout(dieu, 2500);
  };
  $('#hs_chay').onclick = async () => {
    try{
      await api('hieu-suat', {gio: $('#hs_gio').value, chay_that: $('#hs_that').value === '1', tt: TT || S.mkey});
      bao('Bắt đầu đo — khoảng 6 phút'); truoc = null; dieu();
    } catch(e){ bao('Không chạy được: ' + e.message, 1); }
  };
  dieu();
}

/* ── Đo lại ── */
function veDo(){
  return `<div class="dau-trang"><h1>Đo lại dự báo</h1>
    <p class="phu">Quét hội thoại thật, chạy đủ bộ luật, dựng đúng gói prompt sẽ gửi rồi
    <b>dừng ngay trước lượt gọi model</b>. Chỉ đọc — không tốn xu nào. Chạy vài phút.</p></div>
  <section><div class="hop"><div class="hang">
    <label>Cửa sổ đo<select id="d_gio">
      <option value="24">24 giờ gần nhất</option><option value="6">6 giờ gần nhất</option>
      <option value="72">72 giờ gần nhất</option></select>
      <span class="gt">Cửa sổ càng dài, tỉ lệ “sale đã vào trước” càng cao</span></label>
  </div><div class="thanh-nut"><button class="nut" id="d_chay">Đo ngay</button>
    <span class="phu" id="d_tt"></span></div></div></section>
  <section><h2>Nhật ký</h2><pre class="log" id="d_log">chưa chạy lần nào trong phiên này</pre>
  </section>`;
}
function sauDo(){
  const ve1 = st => {
    $('#d_chay').disabled = st.chay;
    $('#d_chay').innerHTML = st.chay ? '<span class="quay"></span>Đang đo…' : 'Đo ngay';
    $('#d_tt').textContent = st.chay ? 'đang quét, trang tự cập nhật' : (st.xong || '');
    if(st.log){ const p = $('#d_log'); const duoi = p.scrollTop + p.clientHeight >= p.scrollHeight - 30;
      p.textContent = st.log; if(duoi) p.scrollTop = p.scrollHeight; }
  };
  const dieu = async () => {
    const st = await api('do');
    S.dochay = st.chay; ve1(st);
    if(st.chay) TIMER = setTimeout(dieu, 1800);
    else { clearTimeout(TIMER); if(st.xong){ const l = $('#d_log').textContent; await tai();
           if(TAB === 'do'){ $('#d_log').textContent = l; $('#d_tt').textContent = st.xong; } } }
  };
  $('#d_chay').onclick = async () => {
    try{ await api('do', {gio: $('#d_gio').value}); bao('Bắt đầu đo'); dieu(); }
    catch(e){ bao('Không chạy được: ' + e.message, 1); }
  };
  dieu();
}

addEventListener('keydown', e => {
  if((e.metaKey || e.ctrlKey) && e.key === 's'){
    e.preventDefault();
    const b = $('#luu') || $('#luu_luat'); if(b && !b.disabled) b.click();
  }
});
addEventListener('beforeunload', e => { if(BAN){ e.preventDefault(); e.returnValue = ''; } });
tai().catch(e => $('#main').innerHTML = '<p class="xau">Không tải được: ' + H(e.message) + '</p>');
</script></body></html>
"""


# ───────────────────────── Máy chủ ─────────────────────────

def chay(mkey=None, cong=8765, mo=True):
    import http.server

    class Xu(http.server.BaseHTTPRequestHandler):
        def _tu_may_nay(self):
            # Chỉ nhận yêu cầu từ chính máy này — chặn cả kiểu DNS rebinding.
            return (self.headers.get("Host") or "").split(":")[0] in (
                "127.0.0.1", "localhost", "[::1]", "::1")

        def _tra(self, ma, noi, kieu="text/html; charset=utf-8"):
            b = noi if isinstance(noi, bytes) else str(noi).encode("utf-8")
            self.send_response(ma)
            self.send_header("Content-Type", kieu)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(b)

        def _js(self, obj, ma=200):
            self._tra(ma, json.dumps(obj, ensure_ascii=False, default=str),
                      "application/json; charset=utf-8")

        def _than(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

        def _tt(self):
            """Thị trường cho lượt gọi này — lấy từ ?tt=, không có thì dùng cái mở lúc đầu.

            Cố ý để mỗi lượt gọi tự khai, không giữ trạng thái trên máy chủ: hai người mở
            hai thị trường cùng lúc thì không giẫm lên nhau.
            """
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            xin = (q.get("tt") or [""])[0].strip().lower()
            return xin if xin in QL.thi_truong() else mkey

        def do_GET(self):
            if not self._tu_may_nay():
                return self._tra(403, "chỉ mở được từ chính máy này")
            if self.path.split("?")[0] == "/api/thi-truong":
                ra = []
                for tt in QL.thi_truong():
                    f = os.path.join(SCRIPT_DIR, "state", tt, "page_tokens.json")
                    try:
                        d = json.load(open(f, encoding="utf-8"))
                        n = sum(1 for x in d.values() if x.get("token"))
                    except Exception:                    # noqa: BLE001
                        n = 0
                    try:
                        ten = json.load(open(os.path.join(SCRIPT_DIR, "markets.json"),
                                             encoding="utf-8")).get(tt, {}).get("ten") or tt
                    except Exception:                    # noqa: BLE001
                        ten = tt
                    ra.append({"tt": tt, "so_page": n, "ten": ten})
                return self._js({"ds": ra, "dang_mo": mkey})
            if self.path in ("/", "/index.html"):
                return self._tra(200, TRANG)
            if self.path in ("/logo.png", "/favicon.ico"):
                # Logo ANTALO cho thanh bên — chép tay vào static/ (không đưa lên git công khai).
                f = os.path.join(SCRIPT_DIR, "static", "antalo-mark.png")
                if os.path.exists(f):
                    return self._tra(200, open(f, "rb").read(), "image/png")
                return self._tra(404, "chưa có logo")
            if self.path.split("?")[0] == "/api/du-lieu":
                try:
                    d = du_lieu(self._tt())
                except Exception as ex:            # noqa: BLE001
                    return self._js({"loi": str(ex)}, 500)
                d["dochay"] = DO["chay"]
                return self._js(d)
            if self.path.split("?")[0] == "/api/bao-cao":
                tt = self._tt()
                if not tt:
                    return self._js({"loi": "màn này cần thị trường"}, 400)
                try:
                    return self._js(bao_cao_tien.bao_cao(tt))
                except Exception as ex:                # noqa: BLE001
                    return self._js({"loi": str(ex)}, 500)
            if self.path.split("?")[0] == "/api/toan-canh":
                import toan_canh
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    return self._js(toan_canh.toan_canh(int((q.get("gio") or ["24"])[0] or 24)))
                except Exception as ex:                # noqa: BLE001
                    return self._js({"loi": str(ex)}, 500)
            if self.path == "/api/do":
                return self._js(DO)
            if self.path == "/api/thu":
                return self._js(THU)

            if self.path.split("?")[0] == "/api/hieu-suat":
                tt = self._tt()
                if not tt:
                    return self._js({"loi": "màn này cần thị trường — mở lại bằng "
                                            "`ai_sale.py dashboard usa --phuc-vu`"}, 400)
                return self._js({"trang_thai": HS, "kq": doc_hieu_suat(tt)})

            # ── Bốn màn quản lý. Thiếu thị trường thì báo rõ chứ không trả rỗng ──
            duong = self.path.split("?")[0]
            if duong in ("/api/page", "/api/kich-ban", "/api/chan", "/api/hang-cho"):
                tt = self._tt()
                if not tt:
                    return self._js({"loi": "màn này cần thị trường — mở lại bằng "
                                            "`ai_sale.py dashboard usa --phuc-vu`"}, 400)
                try:
                    if duong == "/api/page":
                        return self._js(QL.bang_page(tt))
                    if duong == "/api/kich-ban":
                        pid = urllib.parse.parse_qs(
                            urllib.parse.urlparse(self.path).query).get("pid", [""])[0]
                        return self._js(QL.chi_tiet_page(tt, pid))
                    if duong == "/api/chan":
                        return self._js(QL.so_chan(tt))
                    return self._js(QL.hang_cho(tt))
                except Exception as ex:                # noqa: BLE001
                    return self._js({"loi": str(ex)}, 500)
            return self._tra(404, "không có đường này")

        def do_POST(self):
            if not self._tu_may_nay():
                return self._tra(403, "chỉ mở được từ chính máy này")
            try:
                t = self._than()
            except Exception:
                return self._js({"loi": "dữ liệu gửi lên không đọc được"}, 400)
            p = self.path

            if p == "/api/cau-hinh":
                thay = {k: (t.get(k) or "").strip() for k in KHOA_SUA}
                # Ô key để TRỐNG = giữ nguyên key cũ, không phải xoá. Trang không bao giờ
                # in key ra nên người dùng không thể "gõ lại cho giống".
                for k in KHOA_KEY:
                    if not thay[k]:
                        thay.pop(k)
                return self._js({"da_luu": ghi_env(thay)})

            if p == "/api/luat":
                noi = t.get("noi_dung")
                if not isinstance(noi, str) or len(noi.strip()) < 200:
                    return self._js({"loi": "hướng dẫn ngắn bất thường (<200 ký tự) — "
                                            "không lưu để tránh xoá nhầm cả bộ luật"}, 400)
                import ai_sale as A
                if os.path.exists(A.F_LUAT):
                    open(A.F_LUAT + ".bak", "w", encoding="utf-8").write(
                        open(A.F_LUAT, encoding="utf-8").read())
                open(A.F_LUAT, "w", encoding="utf-8").write(noi)
                return self._js({"ky_tu": len(noi)})

            if p == "/api/nap":
                try:
                    so = float(str(t.get("so_tien")).replace("$", "").replace(",", "."))
                except (TypeError, ValueError):
                    return self._js({"loi": "số tiền không đọc được"}, 400)
                chi_phi.nap_them(so, t.get("nha") or "kimi", t.get("ghi_chu") or "")
                return self._js({"ok": 1})

            if p == "/api/kiem-key":
                return self._js(kiem_key())

            if p == "/api/thu":
                # KHÔNG có nhánh nào ở đây gửi tin cho khách: `_chay_thu` cố ý không truyền
                # cờ --that. Gửi thật vẫn chỉ chạy được bằng tay ở terminal.
                if THU["chay"]:
                    return self._js({"loi": "đang chạy thử rồi"}, 409)
                if not mkey:
                    return self._js({"loi": "phải mở kèm thị trường, ví dụ: "
                                            "ai_sale.py dashboard usa --phuc-vu"}, 400)
                threading.Thread(target=_chay_thu,
                                 args=(mkey, str(t.get("pid") or ""),
                                       str(t.get("gio") or 24), str(t.get("so") or 20)),
                                 daemon=True).start()
                time.sleep(0.3)
                return self._js({"ok": 1})

            if p == "/api/do":
                if DO["chay"]:
                    return self._js({"loi": "đang đo rồi"}, 409)
                if not mkey:
                    return self._js({"loi": "phải mở kèm thị trường, ví dụ: "
                                            "ai_sale.py dashboard usa --phuc-vu"}, 400)
                threading.Thread(target=_chay_do, args=(mkey, str(t.get("gio") or 24)),
                                 daemon=True).start()
                time.sleep(0.3)
                return self._js({"ok": 1})
            if p == "/api/hieu-suat":
                if HS["chay"]:
                    return self._js({"loi": "đang đo rồi — đợi xong lượt này"}, 409)
                tt = str(t.get("tt") or mkey or "").strip().lower()
                if tt not in QL.thi_truong():
                    return self._js({"loi": "phải chọn thị trường trước"}, 400)
                threading.Thread(target=_chay_hs,
                                 args=(tt, str(t.get("gio") or 24), bool(t.get("chay_that"))),
                                 daemon=True).start()
                time.sleep(0.3)
                return self._js({"ok": 1})
            return self._tra(404, "không có đường này")

        def log_message(self, *a):
            pass

    dc = f"http://127.0.0.1:{cong}/"
    print(f"\n  🖥  Bảng điều khiển AI Sale: {dc}")
    print(f"     Thị trường: {mkey or '(chưa chọn — không đo lại được)'}")
    print("     Chỉ nghe ở máy này. Dừng bằng Ctrl+C.")
    print(f"     Trên VPS thì mở đường hầm từ máy Mac:")
    print(f"       ssh -L {cong}:127.0.0.1:{cong} root@<IP server>\n")
    if mo:
        try:
            webbrowser.open(dc)
        except Exception:
            pass
    try:
        http.server.ThreadingHTTPServer(("127.0.0.1", cong), Xu).serve_forever()
    except KeyboardInterrupt:
        print("\n  đã dừng.\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    chay(a[0] if a and not a[0].startswith("--") else None,
         cong=int(a[a.index("--cong") + 1]) if "--cong" in a else 8765,
         mo=("--khong-mo" not in a))

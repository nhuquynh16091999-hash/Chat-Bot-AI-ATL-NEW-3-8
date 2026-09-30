#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Đo HIỆU SUẤT AI Sale — ba câu chủ shop hỏi 2026-09-10:

  1. Một tin AI gửi tốn bao nhiêu tiền?
  2. AI xử lý bao nhiêu tin trên tổng tin khách đang nhắn?
  3. Page nào AI phải gánh nhiều tin nhất → Botcake của page đó set chưa hiệu quả.

Ba nguồn số, KHÔNG nguồn nào ghi gì lên Pancake:
  · API Pancake (chỉ đọc): mọi hội thoại có cập nhật trong cửa sổ đo, đọc ĐỦ tin (phân trang
    `current_count`, mỗi trang 30 tin — đo 10/09: gọi mặc định chỉ trả 30 tin mới nhất) rồi xếp
    từng LƯỢT KHÁCH NHẮN theo ai trả lời: Botcake / AI / sale / không ai.
    Tin của AI nhận ra bằng `from.admin_name == "Public API"` — mọi tin gửi qua API bằng token
    của tài khoản đều mang tên này (soi thật 10/09 trên 4 page). Vì thế còn đối chiếu ngược với
    sổ việc: tin "Public API" nào KHÔNG có trong sổ là do hệ khác gửi (aicloser…), báo riêng.
  · state/<tt>/so_chi_phi.jsonl — tiền + token từng lượt gọi model, và QUYẾT ĐỊNH của AI ở từng
    lượt khách (im theo luật / treo / trả lời) — nhờ đó biết AI "không nhắn" là cố ý hay bỏ lọt.
  · state/<tt>/so_viec.jsonl   — mỗi lần AI động vào hội thoại: gửi được / bị FB chặn / cổng chặn.

Định nghĩa (in kèm báo cáo để ai đọc cũng hiểu cùng một nghĩa):
  · LƯỢT KHÁCH  = chuỗi tin liên tiếp của khách, chưa bị tin nào của page (bot/AI/sale) chen vào.
                  Tin hệ thống Facebook ("đã trả lời quảng cáo", lời chào tự động) không tính.
  · Botcake TRẢ LỜI = có tin Botcake trong 5 phút sau tin cuối của lượt. Bot phản xạ tức thì
                  (p95 đo được 12s); tin bot đến sau hàng giờ là follow-up phát tự động, không
                  phải trả lời câu khách hỏi → tính là "Botcake im".
  · AI / sale TRẢ LỜI = có tin AI / sale trước lượt khách kế tiếp, không giới hạn thời gian.
  · AI XỬ LÝ   = AI nhắn thẳng cho khách, HOẶC soạn câu vào ghi chú vì page bị FB chặn (sale
                  chép gửi), HOẶC treo cho sale (ghi chú + chưa đọc), HOẶC câu bị cổng chặn giữ
                  lại (vẫn có ghi chú). Bốn việc này đều là AI đã đụng vào và để lại vết.
  · AI CỐ Ý IM = luật 0 token bảo im: thẻ "Đã gửi", khách đã mua ở page, sale thật đã vào,
                  Botcake đã trả lời đủ. Không phải lỗi, không tính là bỏ lọt.
  · AI KHÔNG THẤY = lượt không có dòng nào trong sổ chi phí — thường vì sale rep trước khi vòng
                  dò 15s bắt được (tin cuối đã là của sale → không "nóng").
  · AI BỎ LỌT  = Botcake im, AI không xử lý và không cố ý im (không thấy / model đọc rồi im /
                  lỗi), mà sale phải vào sau ≥5 phút hoặc không ai trả lời.
  · KHÔNG AI   = không có bot/AI/sale. Lượt cuối hội thoại mà mới dưới 15 phút → "đang chờ".
  Một lượt có thể có nhiều người trả lời (AI nhắn đè lên Botcake) nên các cột cộng lại có thể
  vượt 100% — cố ý để lộ ra chỗ nhắn đè.

Lệnh:
  python3 hieu_suat.py do <thị trường> [--gio 24] [--chay-that] [--luong 4]
        quét API + đọc hai sổ, in báo cáo, lưu state/<tt>/hieu_suat.json
        và state/<tt>/hieu_suat_luot.jsonl (từng lượt khách — để soi lại từng ca)
        --chay-that: cửa sổ bắt đầu từ lúc AI GỬI THẬT lần đầu (dòng that=1 đầu tiên trong sổ
        chi phí) thay vì đủ --gio giờ — đo đúng phần AI có mặt
  python3 hieu_suat.py xem <thị trường>                          # in lại báo cáo đã lưu
"""

import calendar
import datetime
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import ai_sale as A  # noqa: E402 — dùng lại API đọc + lọc page theo shop

try:
    from zoneinfo import ZoneInfo
    VN = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:                                        # noqa: BLE001
    VN = datetime.timezone(datetime.timedelta(hours=7))

BOT_NHANH = 300      # giây — quá mốc này tin Botcake là follow-up, không phải trả lời
DANG_CHO = 900       # giây — lượt cuối mới hơn mốc này thì chưa kết luận "bỏ trống"
AI_MUON = 600        # giây — AI nhắn sau mốc này là đáng ngờ (trả lời câu cũ / gửi lại sau FB chặn)
SALE_MUON = 300      # giây — sale vào sau mốc này mà AI không làm gì = AI bỏ lọt
ANH_KEM_CHU = 90     # giây — ảnh AI gửi mà trong 90s không có chữ đi kèm = "ảnh trơ"
TRANG_TIN = 30       # API trả tối đa 30 tin một lần
TRAN_HOI_THOAI = 60  # API trả tối đa 60 hội thoại một lần → phải chẻ cửa sổ khi chạm trần

XU_LY = ("nhan", "ghi_chu", "treo", "chan")                     # bốn việc = "AI xử lý"
TEN_XU_LY = {"nhan": "AI nhắn thẳng", "ghi_chu": "soạn vào ghi chú (FB chặn)",
             "treo": "treo cho sale", "chan": "cổng chặn giữ lại",
             "im_luat": "AI cố ý im theo luật (0 token)", "im_model": "model đọc rồi im",
             "khong_thay": "AI không thấy (sale vào trước)", "loi": "lỗi model", "khac": "khác"}


# ───────────────────────── Thời gian ─────────────────────────

def _utc(s):
    """'2026-09-10T10:08:32.000000' (API, giờ UTC) → epoch."""
    if not s:
        return None
    try:
        return calendar.timegm(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None


def _may(s):
    """'2026-09-10T12:18:55' (so_chi_phi.luc, GIỜ MÁY VPS) → epoch. Phải chạy trên cùng máy ghi sổ."""
    try:
        return time.mktime(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None


def vn(ts, dang="%d/%m %H:%M"):
    return datetime.datetime.fromtimestamp(ts, VN).strftime(dang) if ts else "?"


def _pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "—"


def _p(ds, q):
    if not ds:
        return None
    ds = sorted(ds)
    return ds[min(len(ds) - 1, int(round(q * (len(ds) - 1))))]


def _giay(x):
    if x is None:
        return "—"
    return f"{x:.0f}s" if x < 120 else f"{x / 60:.0f} phút" if x < 7200 else f"{x / 3600:.1f} giờ"


# ───────────────────────── Đọc API ─────────────────────────

def _goi(url, params, lan=3):
    """GET có thử lại khi Pancake chặn nhịp (429) — vòng theo_doi đang chạy song song cùng tài khoản."""
    res, err = None, None
    for i in range(lan):
        res, err = A._get(url, params)
        if err and ("429" in err or "many" in err.lower()) and i < lan - 1:
            time.sleep(2 * (i + 1))
            continue
        return res, err
    return res, err


# Từ 14/09/2026 AI còn gửi bằng TÀI KHOẢN Pancake riêng (ai_sale.gui_tin_qua_user) → tin mang
# admin_name là tên tài khoản đó, không phải "Public API". Đổi tên tài khoản thì sửa .env.
# Nhiều tên cách nhau dấu phẩy: tài khoản đổi tên (14/09: "PHƯƠNG ANH LEADER 2" → "AI LEADER") thì tin cũ
# vẫn mang tên cũ, tin mới mang tên mới — phải nhận cả hai.
TEN_TAI_KHOAN_AI = {t.strip() for t in (os.environ.get("AI_TEN_TAI_KHOAN") or "AI LEADER,PHƯƠNG ANH LEADER 2").split(",") if t.strip()}


def ai_gui(m, pid):
    """'khach' | 'botcake' | 'ai' | 'nguoi' | 'hethong'.

    Khác ai_sale.nguoi_gui ở một điểm: tách 'ai' (admin_name "Public API") ra khỏi 'nguoi'.
    Bên vòng chạy gộp chung là cố ý (AI đã nhắn thì coi như đã có người, không nhắn nữa);
    bên đo lường mà gộp thì tin AI bị đếm thành tin sale — sai đúng chỗ cần đo.
    """
    f = m.get("from") or {}
    if str(f.get("id")) != str(pid):
        return "khach"
    ten = (f.get("admin_name") or "").strip()
    if not ten:
        return "hethong"
    if ten.lower() == "botcake":
        return "botcake"
    if ten == "Public API" or ten in TEN_TAI_KHOAN_AI:
        return "ai"
    return "nguoi"


def hoi_thoai_trong(pid, token, tu, den, sau=0):
    """Mọi hội thoại cập nhật trong [tu, den]. Chạm trần 60 thì chẻ đôi cửa sổ (đo 10/09: page
    bận nhất 24h có 35, 72h chạm trần 60 và không tham số phân trang nào có tác dụng)."""
    res, err = _goi(f"{A.BASE_V2}/pages/{pid}/conversations",
                    {"page_access_token": token, "type": "INBOX",
                     "since": int(tu), "until": int(den), "order_by": "updated_at"})
    if err or A.loi_token(res):
        return None, err or A.loi_token(res)
    convs = res.get("conversations") or []
    if len(convs) >= TRAN_HOI_THOAI and den - tu > 1800 and sau < 6:
        giua = (tu + den) / 2
        a, e1 = hoi_thoai_trong(pid, token, tu, giua, sau + 1)
        b, e2 = hoi_thoai_trong(pid, token, giua, den, sau + 1)
        if a is None or b is None:
            return None, e1 or e2
        gop_ = {c["id"]: c for c in a}
        gop_.update({c["id"]: c for c in b})
        return list(gop_.values()), None
    return convs, None


def tin_du(pid, cid, token, tu, toi_da=8):
    """Đọc tin của hội thoại lùi dần cho tới khi qua mốc `tu` (tối đa 8 trang = 240 tin).

    `current_count` = số tin đã lấy tính từ tin mới nhất — API trả trang 30 tin kế tiếp về quá khứ.
    """
    out, thay, cur = [], set(), 0
    for _ in range(toi_da):
        p = {"page_access_token": token}
        if cur:
            p["current_count"] = cur
        res, err = _goi(f"{A.BASE_V1}/pages/{pid}/conversations/{cid}/messages", p)
        if err or A.loi_token(res):
            return (out if out else None), err or A.loi_token(res)
        ms = res.get("messages") or []
        moi = [m for m in ms if m.get("id") not in thay]
        if not moi:
            break
        out += moi
        thay.update(m.get("id") for m in moi)
        cur += len(ms)
        cu_nhat = min((_utc(m.get("inserted_at")) or 0) for m in moi)
        if len(ms) < TRANG_TIN or cu_nhat < tu:
            break
        time.sleep(0.05)
    out.sort(key=lambda m: m.get("inserted_at") or "")
    return out, None


# ───────────────────────── Xếp lượt khách ─────────────────────────

def xep_luot(msgs, pid):
    """Từ tin thô → danh sách LƯỢT KHÁCH, mỗi lượt biết ai trả lời lúc nào.

    `luot[i]['tra']` = {loại người trả lời: epoch tin đầu tiên của loại đó sau lượt}.
    """
    luot = []
    mo = False           # đang trong chuỗi tin khách liên tiếp?
    for m in msgs:
        boi = ai_gui(m, pid)
        t = _utc(m.get("inserted_at"))
        if t is None or boi == "hethong":
            continue
        txt = A.lam_sach(m.get("original_message") or m.get("message"))
        if boi == "khach":
            if mo and luot:
                luot[-1]["den"] = t
                luot[-1]["n"] += 1
                if txt and not luot[-1]["tin"]:
                    luot[-1]["tin"] = txt[:120]
            else:
                luot.append({"tu": t, "den": t, "n": 1, "tin": txt[:120], "tra": {}})
            mo = True
        else:
            mo = False
            if luot:
                luot[-1]["tra"].setdefault(boi, t)
                if boi == "ai" and txt:
                    luot[-1].setdefault("tin_ai", txt[:100])
    return luot


def ket_luan(l, bay_gio):
    """Gắn cờ cho một lượt: bot / ai / sale / trong / cho. Xem định nghĩa đầu file."""
    tra = l["tra"]
    l["bot"] = "botcake" in tra and tra["botcake"] - l["den"] <= BOT_NHANH
    l["bot_muon"] = "botcake" in tra and not l["bot"]
    l["ai"] = "ai" in tra
    l["ai_muon"] = l["ai"] and tra["ai"] - l["den"] > AI_MUON
    l["sale"] = "nguoi" in tra
    l["trong"] = not (l["bot"] or l["ai"] or l["sale"])
    l["cho"] = l["trong"] and (bay_gio - l["den"] < DANG_CHO)
    if l["cho"]:
        l["trong"] = False
    l["tre"] = {k: round(v - l["den"]) for k, v in tra.items()}
    return l


def anh_tro(msgs, pid):
    """Ảnh AI gửi mà không có chữ AI nào đi kèm trong 90s — khách nhận ảnh trơ.

    Vì sao đo: page bị Facebook chặn kênh API (#2022) thì `gui_tin` hỏng nhưng ảnh mẫu
    (`gui_anh_mau`) đi TRƯỚC câu chữ và đi bằng đường khác — có thể vẫn lọt. Sổ việc ghi
    "AI KHÔNG GỬI ĐƯỢC" nhưng khách vẫn thấy một tấm ảnh không lời.
    """
    ra = []
    ai_ms = [(_utc(m.get("inserted_at")) or 0, m) for m in msgs if ai_gui(m, pid) == "ai"]
    for t, m in ai_ms:
        txt = A.lam_sach(m.get("original_message") or m.get("message"))
        if txt or not m.get("attachments"):
            continue
        co_chu = any(t <= t2 <= t + ANH_KEM_CHU
                     and A.lam_sach(m2.get("original_message") or m2.get("message"))
                     for t2, m2 in ai_ms)
        if not co_chu:
            ra.append(t)
    return ra


# ───────────────────────── Hai sổ ─────────────────────────

def _doc_jsonl(f):
    if not os.path.exists(f):
        return []
    ra = []
    with open(f, encoding="utf-8") as fh:
        for d in fh:
            d = d.strip()
            if d:
                try:
                    ra.append(json.loads(d))
                except Exception:                        # noqa: BLE001
                    pass
    return ra


def doc_so(mkey, tu, den):
    """Dòng sổ chi phí + sổ việc rơi trong cửa sổ. Trả (chi_phi_rows, viec_rows)."""
    d = os.path.join(SCRIPT_DIR, "state", mkey)
    cp = [r for r in _doc_jsonl(os.path.join(d, "so_chi_phi.jsonl"))
          if tu <= (_may(r.get("luc")) or 0) <= den]
    vc = [r for r in _doc_jsonl(os.path.join(d, "so_viec.jsonl"))
          if tu <= (r.get("luc") or 0) <= den]
    return cp, vc


def phan_loai_viec(r):
    """Một dòng sổ việc là gì: 'gui' (tới khách) | 'ghi_chu' (FB chặn, soạn vào ghi chú)
    | 'chan' (cổng chặn) | 'hong' (gửi hỏng lý do khác) | 'khac' (treo/xác minh nhà, không có tin)."""
    if r.get("chan") == "chan":
        return "chan"
    if not (r.get("tin") or "").strip():
        return "khac"
    gh = r.get("gui_hong") or ""
    if not gh:
        return "gui"
    return "ghi_chu" if "#2022" in gh or "chặn kênh API" in gh else "hong"


def lap_chi_muc(cp, vc):
    """Chỉ mục để tra 'AI đã làm gì với lượt này': sổ chi phí theo hội thoại (dòng that=1),
    sổ việc theo hội thoại. Trả dict."""
    so = defaultdict(list)
    for r in cp:
        if r.get("that") == 1:
            t = _utc(r.get("khach_luc"))
            if t:
                so[str(r.get("conv"))].append((t, _may(r.get("luc")) or 0, r))
    viec = defaultdict(list)
    for r in vc:
        if r.get("that") == 1:
            viec[str(r.get("conv"))].append((r.get("luc") or 0, phan_loai_viec(r)))
    return {"so": so, "viec": viec}


def xu_ly_cua_ai(l, den_ke, cm):
    """AI đã làm gì với lượt này — xem nhóm định nghĩa đầu file. Trả một khoá của TEN_XU_LY."""
    if l["ai"]:
        return "nhan"
    kinds = {k for t, k in cm["viec"].get(l["conv"], []) if l["den"] <= t < den_ke + 1}
    if "ghi_chu" in kinds:
        return "ghi_chu"
    if "chan" in kinds:
        return "chan"
    # dòng sổ chi phí có khach_luc là MỘT tin trong lượt (khách có thể nhắn thêm sau khi AI xét)
    rows = [(luc, r) for t, luc, r in cm["so"].get(l["conv"], []) if l["tu"] <= t <= l["den"]]
    if not rows:
        return "khong_thay"
    r = max(rows, key=lambda x: x[0])[1]
    hd = r.get("hd")
    if hd == "treo":
        return "treo"
    if hd == "im":
        return "im_luat" if not r.get("goi") else "im_model"
    if hd == "loi":
        return "loi"
    return "khac"


def tinh_tien(cp, vc):
    """Mục 1 — tiền. Mọi con số tách THẬT / THỬ vì vòng thử cũng gọi model (tốn thật) mà không gửi gì."""
    kq = {"that": {}, "thu": {}}
    for nhan, that in (("that", 1), ("thu", 0)):
        rows = [r for r in cp if r.get("that") == that]
        # Dòng cửa 'im' mà có token là DÒNG MA: nhánh "thẻ Đã gửi" / "đã mua ở page" trong
        # ai_sale.cmd_chay ghi sổ mà không xoá LAN_GOI_CUOI, nên chép lại số của lượt gọi
        # trước đó (phát hiện 10/09 khi đo: 36 dòng, ~5% tiền). Cửa 'im' không bao giờ gọi model.
        goi = [r for r in rows if r.get("goi") and r.get("cua") != "im"]
        tien = sum(r.get("tien") or 0 for r in goi)
        su_kien = {(r.get("conv"), r.get("khach_luc")) for r in rows}
        im_goi = [r for r in goi if r.get("hd") == "im"]
        theo_cua = defaultdict(float)
        for r in goi:
            theo_cua[r.get("cua") or "?"] += r.get("tien") or 0
        kq[nhan] = {
            "tien": tien, "goi": len(goi), "su_kien": len(su_kien),
            "hoi_thoai": len({r.get("conv") for r in rows}),
            "tien_im": sum(r.get("tien") or 0 for r in im_goi), "goi_im": len(im_goi),
            "tien_theo_cua": dict(theo_cua),
            "vao": sum(r.get("vao") or 0 for r in goi),
            "doc_dem": sum(r.get("doc_dem") or 0 for r in goi),
            "ra": sum(r.get("ra") or 0 for r in goi),
            "loi": sum(1 for r in rows if r.get("hd") == "loi"),
            "treo": len({(r.get("conv"), r.get("khach_luc")) for r in rows if r.get("hd") == "treo"}),
            "model": Counter(r.get("model") for r in goi).most_common(1)[0][0] if goi else None,
            "gio_co_chay": len({(r.get("luc") or "")[:13] for r in rows}),
        }
    v = [r for r in vc if r.get("that") == 1]
    loai = Counter(phan_loai_viec(r) for r in v)
    kq["viec"] = {"gui": loai["gui"], "ghi_chu": loai["ghi_chu"], "chan": loai["chan"],
                  "hong": loai["hong"], "khac": loai["khac"],
                  "len_don": sum(1 for r in v if r.get("hd") == "len_don"),
                  "thu": sum(1 for r in vc if r.get("that") == 0)}
    t = kq["that"]
    soan = loai["gui"] + loai["ghi_chu"]
    kq["moi_tin"] = {
        "gui": t["tien"] / loai["gui"] if loai["gui"] else None,
        "soan": t["tien"] / soan if soan else None,
        "goi": t["tien"] / t["goi"] if t["goi"] else None,
        "su_kien": t["tien"] / t["su_kien"] if t["su_kien"] else None,
    }
    return kq


def luc_chay_that_dau(mkey, tu, den):
    """Epoch của dòng that=1 sớm nhất trong cửa sổ — mốc AI bắt đầu gửi thật. None = chưa gửi thật."""
    cp, _ = doc_so(mkey, tu, den)
    ds = [_may(r.get("luc")) for r in cp if r.get("that") == 1]
    ds = [x for x in ds if x]
    return min(ds) if ds else None


# ───────────────────────── Gộp số ─────────────────────────

def danh_gia(p):
    """Nhãn cho từng page — cố ý thô để chủ shop liếc là biết phải đụng page nào.

    Chỉ chấm khi đủ mẫu (≥ 5 lượt). Page không có Botcake thì không phải "set sai", là chưa bật.
    """
    if p["luot"] < 5:
        return "ít mẫu"
    if not p["co_botcake"]:
        return "chưa bật Botcake"
    r = p["ty_le_bot_im"]
    if r >= 0.5:
        return "Botcake KÉM — im quá nửa"
    if r >= 0.25:
        return "Botcake trung bình"
    return "Botcake tốt"


def gop(ket, tok, tien_page, goi_page, viec_page, cm, tu_loc=0):
    """Từ kết quả quét từng page → (tong, bang). `tu_loc` = chỉ tính lượt có tin cuối ≥ mốc này
    (dùng để đo riêng đoạn AI đã chạy thật mà không phải quét API lần hai)."""
    CO = ("luot", "bot", "bot_muon", "ai", "ai_muon", "sale", "trong", "cho", "bot_va_ai",
          "bot_im", "ai_xu_ly", "ai_xu_ly_bot_im", "bo_lot", "anh_tro")
    tong = {k: 0 for k in CO}
    tong.update({"tin": Counter(), "hoi_thoai": 0, "page_loi": [], "api_khop": 0, "api_la": 0,
                 "xu_ly": Counter(), "xu_ly_bot_im": Counter(), "sale_do": Counter()})
    tre = {"botcake": [], "ai": [], "nguoi": []}
    bang = []
    for pid, convs, err, ra in ket:
        ten = (tok.get(pid) or {}).get("name") or pid
        if convs is None:
            tong["page_loi"].append(f"{ten[:40]}: {err}")
            continue
        p = {k: 0 for k in CO}
        p.update({"pid": pid, "page": ten, "hoi_thoai": 0, "tin": Counter(), "xu_ly": Counter(),
                  "co_botcake": any(x["bot_lich_su"] for x in ra),
                  "tien": round(tien_page.get(pid, 0), 4), "goi": goi_page.get(pid, 0),
                  "tin_gui": viec_page[pid]["gui"], "tin_ghi_chu": viec_page[pid]["ghi_chu"],
                  "tin_chan": viec_page[pid]["chan"], "vi_du_bot_im": []})
        for x in ra:
            luot = [l for l in x["luot"] if l["den"] >= tu_loc]
            if not luot and not any(t >= tu_loc for t in x["luc_tin"]):
                continue
            p["hoi_thoai"] += 1
            for b, t in zip(x["boi_tin"], x["luc_tin"]):
                if t >= tu_loc:
                    p["tin"][b] += 1
            p["anh_tro"] += sum(1 for t in x["anh_tro"] if t >= tu_loc)
            tong["api_khop"] += x["api_khop"]
            tong["api_la"] += x["api_la"]
            for l in luot:
                p["luot"] += 1
                for k in ("bot", "bot_muon", "ai", "ai_muon", "sale", "trong", "cho"):
                    p[k] += 1 if l[k] else 0
                if l["bot"] and l["ai"]:
                    p["bot_va_ai"] += 1
                xl = l["xu_ly"]
                p["xu_ly"][xl] += 1
                da_xu_ly = xl in XU_LY
                p["ai_xu_ly"] += 1 if da_xu_ly else 0
                if not l["bot"]:
                    p["bot_im"] += 1
                    tong["xu_ly_bot_im"][xl] += 1
                    if da_xu_ly:
                        p["ai_xu_ly_bot_im"] += 1
                    else:
                        s = l["tre"].get("nguoi")
                        if l["sale"]:
                            tong["sale_do"]["duoi_1p" if s < 60 else "1_5p" if s < SALE_MUON
                                            else "5_30p" if s < 1800 else "tren_30p"] += 1
                        muon = l["trong"] or (l["sale"] and s is not None and s >= SALE_MUON)
                        if muon and xl in ("khong_thay", "im_model", "loi", "khac"):
                            p["bo_lot"] += 1
                    if l["tin"] and len(l["tin"].split()) >= 2 and len(p["vi_du_bot_im"]) < 6:
                        p["vi_du_bot_im"].append(
                            {"khach": x["khach"][:20], "tin": l["tin"][:90],
                             "ai": TEN_XU_LY.get(xl, xl) if da_xu_ly else
                                   "sale" if l["sale"] else "đang chờ" if l["cho"] else "TRỐNG"})
                for k, v in l["tre"].items():
                    if k == "botcake" and not l["bot"]:
                        continue                 # follow-up muộn không phải "tốc độ trả lời"
                    if k in tre and v >= 0:
                        tre[k].append(v)
        p["ty_le_ai"] = p["ai"] / p["luot"] if p["luot"] else 0
        p["ty_le_ai_xu_ly"] = p["ai_xu_ly"] / p["luot"] if p["luot"] else 0
        p["ty_le_bot_im"] = p["bot_im"] / p["luot"] if p["luot"] else 0
        p["ty_le_trong"] = p["trong"] / p["luot"] if p["luot"] else 0
        p["danh_gia"] = danh_gia(p)
        p["tin"] = dict(p["tin"])
        p["xu_ly"] = dict(p["xu_ly"])
        bang.append(p)
        tong["hoi_thoai"] += p["hoi_thoai"]
        for k in CO:
            tong[k] += p[k]
        tong["tin"].update(p["tin"])
        tong["xu_ly"].update(p["xu_ly"])
    for k in ("tin", "xu_ly", "xu_ly_bot_im", "sale_do"):
        tong[k] = dict(tong[k])
    tong["page_co_botcake"] = sum(1 for p in bang if p["co_botcake"])
    tong["page"] = len(bang)
    tong["tre"] = {k: {"p50": _p(v, 0.5), "p95": _p(v, 0.95), "n": len(v)} for k, v in tre.items()}
    bang.sort(key=lambda p: (-p["ty_le_ai_xu_ly"], -p["ai_xu_ly"], -p["ty_le_bot_im"], -p["luot"]))
    return tong, bang


# ───────────────────────── Quét ─────────────────────────

def quet(mkey, gio=24, luong=4, chay_that=False, in_ra=True):
    t0 = time.time()
    bay_gio = t0
    tu, den = bay_gio - gio * 3600, bay_gio
    tu_that = luc_chay_that_dau(mkey, tu, den)
    if chay_that:
        if not tu_that:
            sys.exit(f"❌ {mkey}: trong {gio} giờ qua chưa có vòng gửi thật nào (that=1) — bỏ --chay-that")
        tu = tu_that
    pages = A._pages_cua_thi_truong(mkey)
    if not pages:
        sys.exit(f"❌ {mkey}: không có page nào token sống")
    tok = {str(p): st for p, st in pages}
    if in_ra:
        print(f"\n🔎 Đo hiệu suất {mkey}: {len(pages)} page · {vn(tu)} → {vn(den)} giờ VN"
              f" ({(den - tu) / 3600:.1f} giờ{' — từ lúc AI gửi thật' if chay_that else ''})", flush=True)

    cp, vc = doc_so(mkey, tu, den)
    cm = lap_chi_muc(cp, vc)
    # Tin AI đã gửi thật theo sổ việc — để đối chiếu với tin "Public API" nhìn thấy trên API
    da_gui = defaultdict(list)
    for r in vc:
        if r.get("that") == 1 and phan_loai_viec(r) == "gui":
            da_gui[str(r.get("conv"))].append(A.lam_sach(r.get("tin"))[:60])

    def _mot_page(cap):
        pid, st = cap
        pid = str(pid)
        convs, err = hoi_thoai_trong(pid, st["token"], tu, den)
        if convs is None:
            return pid, None, err, [], [], []
        ra, la, tro = [], [], []
        for c in convs:
            msgs, e = tin_du(pid, c["id"], st["token"], tu)
            if not msgs:
                continue
            khach = ((c.get("customers") or [{}])[0].get("name")
                     or (c.get("from") or {}).get("name") or "?")
            luot = [ket_luan(l, bay_gio) for l in xep_luot(msgs, pid) if tu <= l["den"] <= den]
            for i, l in enumerate(luot):
                l.update({"pid": pid, "page": st.get("name") or pid, "conv": str(c["id"]),
                          "khach": khach[:30]})
                l["xu_ly"] = xu_ly_cua_ai(l, luot[i + 1]["den"] if i + 1 < len(luot) else 9e12, cm)
            boi_tin, luc_tin = [], []
            api_khop = api_la = 0
            for m in msgs:
                t = _utc(m.get("inserted_at")) or 0
                if t < tu:
                    continue
                b = ai_gui(m, pid)
                boi_tin.append(b)
                luc_tin.append(t)
                if b == "ai":
                    txt = A.lam_sach(m.get("original_message") or m.get("message"))[:60]
                    if not txt and m.get("attachments"):
                        continue                 # ảnh mẫu AI gửi kèm — sổ việc ghi số ảnh, không ghi tin
                    if any(txt and txt[:40] == x[:40] for x in da_gui.get(str(c["id"]), [])):
                        api_khop += 1
                    else:
                        api_la += 1
                        if len(la) < 30:
                            la.append({"page": (st.get("name") or pid)[:30], "conv": str(c["id"]),
                                       "khach": khach[:20], "luc": vn(t, "%d/%m %H:%M:%S"),
                                       "tin": txt[:80], "dinh_kem": bool(m.get("attachments"))})
            at = [t for t in anh_tro(msgs, pid) if t >= tu]
            for t in at[:3]:
                tro.append({"page": (st.get("name") or pid)[:30], "khach": khach[:20],
                            "luc": vn(t, "%d/%m %H:%M:%S"), "conv": str(c["id"])})
            ra.append({"conv": str(c["id"]), "luot": luot, "boi_tin": boi_tin, "luc_tin": luc_tin,
                       "bot_lich_su": any(ai_gui(m, pid) == "botcake" for m in msgs),
                       "api_khop": api_khop, "api_la": api_la, "khach": khach, "anh_tro": at})
            time.sleep(0.05)
        return pid, convs, None, ra, la, tro

    with ThreadPoolExecutor(max_workers=luong) as bom:
        ket_day = list(bom.map(_mot_page, pages))
    ket = [(pid, convs, err, ra) for pid, convs, err, ra, _, _ in ket_day]
    api_la_ds = [x for *_, la, _ in ket_day for x in la][:30]
    anh_tro_ds = [x for *_, tro in ket_day for x in tro][:30]

    tien_page, goi_page = defaultdict(float), Counter()
    for r in cp:
        if r.get("that") == 1 and r.get("goi"):
            tien_page[str(r.get("pid"))] += r.get("tien") or 0
            goi_page[str(r.get("pid"))] += 1
    viec_page = defaultdict(Counter)
    for r in vc:
        if r.get("that") == 1:
            viec_page[str(r.get("pid"))][phan_loai_viec(r)] += 1

    tong, bang = gop(ket, tok, tien_page, goi_page, viec_page, cm)
    tong_that, bang_that = None, None
    if tu_that and tu_that > tu + 60:
        tong_that, bang_that = gop(ket, tok, tien_page, goi_page, viec_page, cm, tu_loc=tu_that)

    kq = {"mkey": mkey, "luc": bay_gio, "tu": tu, "den": den, "gio": (den - tu) / 3600,
          "chay_that": bool(chay_that), "tu_that": tu_that,
          "tong": tong, "tong_that": tong_that, "tien": tinh_tien(cp, vc),
          "bang": bang, "bang_that": bang_that,
          "api_la_ds": api_la_ds, "anh_tro_ds": anh_tro_ds, "mat_giay": round(time.time() - t0),
          "dinh_nghia": {"bot_nhanh": BOT_NHANH, "dang_cho": DANG_CHO, "ai_muon": AI_MUON,
                         "sale_muon": SALE_MUON}, "ten_xu_ly": TEN_XU_LY}
    d = os.path.join(SCRIPT_DIR, "state", mkey)
    f = os.path.join(d, "hieu_suat.json")
    try:
        json.dump(kq, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # Từng lượt — để soi lại từng ca bằng grep/python, không phải quét API lần nữa
        with open(os.path.join(d, "hieu_suat_luot.jsonl"), "w", encoding="utf-8") as fh:
            for _, convs, _, ra in ket:
                for x in (ra or []):
                    for l in x["luot"]:
                        r = {k: l[k] for k in ("pid", "page", "conv", "khach", "n", "tin", "bot",
                                               "bot_muon", "ai", "ai_muon", "sale", "trong", "cho",
                                               "tre", "xu_ly")}
                        r["luc_vn"] = vn(l["den"], "%d/%m %H:%M:%S")
                        r["den"] = l["den"]
                        if l.get("tin_ai"):
                            r["tin_ai"] = l["tin_ai"]
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception as e:                               # noqa: BLE001
        print(f"  ⚠️  không lưu được {f}: {e}")
    if in_ra:
        in_bao_cao(kq)
        print(f"\n  💾 {f}  · từng lượt: {os.path.join(d, 'hieu_suat_luot.jsonl')}"
              f"\n  ⏱  quét mất {kq['mat_giay']}s   (xem lại: python3 hieu_suat.py xem {mkey})\n")
    return kq


# ───────────────────────── In ─────────────────────────

def _usd(x, so=4):
    return "—" if x is None else f"${x:,.{so}f}"


def _khoi_luot(T, dn):
    L = T["luot"]
    xl, xb = T["xu_ly"], T["xu_ly_bot_im"]
    ra = [f"  {L:,} lượt khách nhắn (từ {T['tin'].get('khach', 0):,} tin khách)",
          f"     Botcake trả lời (≤{dn['bot_nhanh'] // 60} phút): {T['bot']:,} ({_pct(T['bot'], L)})"
          f" · bot chỉ follow-up muộn: {T['bot_muon']:,}",
          f"     AI XỬ LÝ                   : {T['ai_xu_ly']:,} ({_pct(T['ai_xu_ly'], L)})"
          f" = nhắn thẳng {xl.get('nhan', 0):,} · soạn vào ghi chú (FB chặn) {xl.get('ghi_chu', 0):,}"
          f" · treo cho sale {xl.get('treo', 0):,} · cổng chặn giữ {xl.get('chan', 0):,}",
          f"         (AI nhắn đè lên Botcake: {T['bot_va_ai']:,} · nhắn sau >{dn['ai_muon'] // 60} phút: {T['ai_muon']:,})",
          f"     Sale trả lời               : {T['sale']:,} ({_pct(T['sale'], L)})",
          f"     Không ai trả lời           : {T['trong']:,} ({_pct(T['trong'], L)})"
          f" · đang chờ (<{dn['dang_cho'] // 60} phút): {T['cho']:,}"]
    bi = T["bot_im"]
    ra.append(f"  Botcake IM ở {bi:,} lượt ({_pct(bi, L)}) — AI đã làm gì với chúng:")
    ra.append(f"     AI xử lý {T['ai_xu_ly_bot_im']:,} ({_pct(T['ai_xu_ly_bot_im'], bi)})"
              f" · cố ý im theo luật {xb.get('im_luat', 0):,} ({_pct(xb.get('im_luat', 0), bi)})"
              f" · không thấy vì sale vào trước {xb.get('khong_thay', 0):,} ({_pct(xb.get('khong_thay', 0), bi)})"
              f" · model đọc rồi im {xb.get('im_model', 0):,} · lỗi {xb.get('loi', 0):,}")
    sd = T.get("sale_do") or {}
    ra.append(f"     Sale vào khi AI không làm gì: dưới 1 phút {sd.get('duoi_1p', 0):,} (nhanh hơn AI)"
              f" · 1–5 phút {sd.get('1_5p', 0):,} · 5–30 phút {sd.get('5_30p', 0):,} · sau 30 phút {sd.get('tren_30p', 0):,}")
    ra.append(f"     → AI BỎ LỌT (không thấy / model im, mà sale phải vào sau ≥{dn['sale_muon'] // 60} phút"
              f" hoặc trống): {T['bo_lot']:,} lượt ({_pct(T['bo_lot'], bi)})")
    tr = T["tre"]
    ra.append(f"  Tốc độ trả lời (trung vị / p95): Botcake {_giay(tr['botcake']['p50'])} / {_giay(tr['botcake']['p95'])}"
              f" · AI {_giay(tr['ai']['p50'])} / {_giay(tr['ai']['p95'])}"
              f" · sale {_giay(tr['nguoi']['p50'])} / {_giay(tr['nguoi']['p95'])}")
    if T.get("anh_tro"):
        ra.append(f"  ⚠️  {T['anh_tro']} ảnh AI gửi KHÔNG kèm chữ (page bị FB chặn chữ nhưng ảnh vẫn đi) — khách nhận ảnh trơ")
    return "\n".join(ra)


def in_bao_cao(kq):
    T, M, B, dn = kq["tong"], kq["tien"], kq["bang"], kq["dinh_nghia"]
    th, thu, v, mt = M["that"], M["thu"], M["viec"], M["moi_tin"]
    tin = T["tin"]
    print(f"\n{'═' * 78}\n  HIỆU SUẤT AI SALE — {kq['mkey']} — {kq['gio']:.1f} giờ "
          f"({vn(kq['tu'])} → {vn(kq['den'])} giờ VN)"
          f"{' — TỪ LÚC AI GỬI THẬT' if kq.get('chay_that') else ''}\n{'═' * 78}")
    print(f"  {T['page']} page đọc được ({T['page_co_botcake']} có Botcake) · "
          f"{T['hoi_thoai']:,} hội thoại có tin · tin khách {tin.get('khach', 0):,} · "
          f"Botcake {tin.get('botcake', 0):,} · AI {tin.get('ai', 0):,} · sale {tin.get('nguoi', 0):,}")
    if T["page_loi"]:
        print(f"  ⚠️  {len(T['page_loi'])} page không đọc được: "
              + " · ".join(x.split(":")[0] for x in T["page_loi"][:6])
              + (" …" if len(T["page_loi"]) > 6 else "") + f" — {T['page_loi'][0].split(': ', 1)[-1][:60]}")
    if T["api_la"]:
        print(f"  ⚠️  {T['api_la']} tin 'Public API' KHÔNG khớp sổ việc AI Sale ({T['api_khop']} tin khớp)"
              f" — hệ khác gửi qua API, hoặc câu bị sửa trước khi gửi:")
        for x in kq.get("api_la_ds", [])[:5]:
            print(f"       {x['luc']} [{x['page']}] {x['khach']}: {x['tin'] or '(chỉ đính kèm)'}")

    print(f"\n  ── 1. MỘT TIN TỐN BAO NHIÊU ─────────────────────────────────────────")
    print(f"  Vòng THẬT: {_usd(th['tien'])} cho {th['goi']} lượt gọi model"
          f" ({th['model'] or '?'}) trên {th['su_kien']} lượt khách AI đã xét / {th['hoi_thoai']} hội thoại")
    print(f"     → ra {v['gui']} tin gửi tới khách · {v['ghi_chu']} tin soạn vào ghi chú (page bị FB chặn)"
          f" · {v['chan']} bị cổng chặn · {v['hong']} gửi hỏng khác · {v['len_don']} lượt chốt đơn")
    print(f"     💵 {_usd(mt['gui'])} / tin gửi tới khách · {_usd(mt['soan'])} / tin AI soạn ra"
          f" · {_usd(mt['goi'])} / lượt gọi model · {_usd(mt['su_kien'])} / lượt khách AI xét")
    if th["goi"]:
        print(f"     Gọi model rồi quyết định IM: {th['goi_im']} lượt = {_usd(th['tien_im'])}"
              f" ({_pct(th['tien_im'], th['tien'])} tiền vòng thật)"
              + (f" — cửa 'xet' (Botcake đã rep, đọc lại) tốn {_usd(th['tien_theo_cua'].get('xet', 0))}"
                 if th["tien_theo_cua"].get("xet") else ""))
        tong_vao = th["vao"] + th["doc_dem"]
        print(f"     Token: vào {th['vao']:,} · đọc đệm {th['doc_dem']:,}"
              f" ({_pct(th['doc_dem'], tong_vao)} — {'đệm có chạy' if th['doc_dem'] else 'KHÔNG có đệm'})"
              f" · ra {th['ra']:,} → trung bình {tong_vao // max(th['goi'], 1):,} vào + "
              f"{th['ra'] // max(th['goi'], 1):,} ra mỗi lượt")
        if th["gio_co_chay"]:
            moi_gio = th["tien"] / th["gio_co_chay"]
            print(f"     Nhịp hiện tại: {_usd(moi_gio)}/giờ có chạy thật ({th['gio_co_chay']} giờ)"
                  f" → ước {_usd(moi_gio * 24, 2)}/ngày · {_usd(moi_gio * 24 * 30, 2)}/tháng"
                  f" (ước thô, đêm ít khách hơn)")
    if thu["goi"]:
        print(f"  Vòng THỬ (gọi model, không gửi): {_usd(thu['tien'])} / {thu['goi']} lượt"
              f" — tiền này không sinh ra tin nào")
    print(f"  Cách tính: tiền = sổ chi phí (token thật × giá model); tin = sổ việc. "
          f"'Tin AI soạn ra' gồm cả câu ghi vào ghi chú cho sale chép khi page bị FB chặn.")

    print(f"\n  ── 2. AI XỬ LÝ BAO NHIÊU TIN ────────────────────────────────────────")
    print(_khoi_luot(T, dn))
    if kq.get("tong_that"):
        print(f"\n  Riêng TỪ LÚC AI GỬI THẬT ({vn(kq['tu_that'])} giờ VN → nay):")
        print(_khoi_luot(kq["tong_that"], dn))
    if kq.get("anh_tro_ds"):
        print("  Ảnh trơ ở:")
        for x in kq["anh_tro_ds"][:5]:
            print(f"       {x['luc']} [{x['page']}] {x['khach']}")
    print(f"  Sổ chi phí cùng cửa sổ: AI xét {th['su_kien']:,} lượt, treo cho sale {th['treo']:,} lượt"
          f" (ghi chú + chưa đọc, không tốn tiền)")

    bang_in = kq.get("bang_that") or B
    print(f"\n  ── 3. THEO PAGE — AI đang phải gánh ở đâu"
          f"{' (từ lúc AI gửi thật)' if kq.get('bang_that') else ''} ─────────────────")
    print(f"  {'page':<32}{'Botcake':>8}{'lượt':>6}{'bot im%':>9}{'AI xử lý':>13}{'sale%':>7}"
          f"{'trống%':>8}{'tiền AI':>9}  đánh giá")
    for p in bang_in:
        if not p["luot"]:
            continue
        nhan = p["xu_ly"].get("nhan", 0)
        o_ai = f"{_pct(p['ai_xu_ly'], p['luot'])} ({nhan} nhắn)"
        print(f"  {p['page'][:31]:<32}{('có' if p['co_botcake'] else 'không'):>8}{p['luot']:>6}"
              f"{_pct(p['bot_im'], p['luot']):>9}{o_ai:>13}"
              f"{_pct(p['sale'], p['luot']):>7}{_pct(p['trong'], p['luot']):>8}"
              f"{_usd(p['tien']):>9}  {p['danh_gia']}")
    kem = [p for p in bang_in if p["danh_gia"].startswith("Botcake KÉM")]
    kem.sort(key=lambda p: -p["bot_im"])
    if kem:
        print(f"\n  Botcake set chưa hiệu quả ({len(kem)} page) — câu khách hỏi mà bot im, ai phải đỡ:")
        for p in kem[:8]:
            print(f"   • {p['page'][:40]} — im {p['bot_im']}/{p['luot']} lượt")
            for vd in p["vi_du_bot_im"][:3]:
                print(f"       [{vd['ai'][:14]:>14}] {vd['khach']}: {vd['tin']}")
    print(f"\n  Đọc cột: bot im% = Botcake KHÔNG trả lời trong 5 phút · AI xử lý = nhắn + ghi chú + treo + cổng chặn"
          f" · trống% = không ai trả lời (đã trừ lượt đang chờ). Cột có thể cộng quá 100% vì một lượt có thể được cả bot lẫn AI trả lời.")


def cmd_xem(mkey):
    f = os.path.join(SCRIPT_DIR, "state", mkey, "hieu_suat.json")
    if not os.path.exists(f):
        sys.exit(f"Chưa đo lần nào — chạy: python3 hieu_suat.py do {mkey}")
    kq = json.load(open(f, encoding="utf-8"))
    in_bao_cao(kq)
    print(f"\n  (đo lúc {vn(kq['luc'], '%d/%m %H:%M')} giờ VN)\n")


def main():
    a = sys.argv[1:]
    g = lambda c, m: a[a.index(c) + 1] if c in a else m
    if len(a) >= 2 and a[0] == "do":
        quet(a[1], gio=float(g("--gio", 24)), luong=int(g("--luong", 4)),
             chay_that=("--chay-that" in a))
    elif len(a) >= 2 and a[0] == "xem":
        cmd_xem(a[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

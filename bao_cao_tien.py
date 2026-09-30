#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Báo cáo tổng TIỀN AI Sale — cho chủ shop báo cáo lên cấp trên.

Chủ shop 13/09/2026: *"báo cáo tổng cho tôi, càng chi tiết càng tốt để tôi báo cáo lại sếp tôi
đã tiêu 20 đô cho những gì, cụ thể ra sao, sao lại hết 20 đô nhanh thế, tối ưu được cái gì"*.

Nguồn số — KHÔNG bịa, không ước lượng mới:
  state/<tt>/so_chi_phi.jsonl      mỗi lượt quét 1 dòng (token, tiền theo bảng giá trong code)
  state/nap_tien.json              tiền đã nạp (tự khai)
  api.moonshot.ai .../balance      số dư THẬT của tài khoản Kimi (gọi từ máy chủ, nhớ 5 phút)
  state/<tt>/hieu_suat.json        số đo hieu_suat.py: tin gửi thật / vào ghi chú / bị chặn
  state/<tt>/page_bi_fb_chan.json  page đang bị Facebook chặn gửi (#2022)
Phần "đã tối ưu" là nhật ký thay đổi có ngày, đối chiếu với số đo theo ngày ở trên.

Dùng:  python3 bao_cao_tien.py uae          # in ra terminal
       giao_dien.py gọi bao_cao(mkey) → tab Tổng quan
"""

import json
import os
import sys
import time
import urllib.request
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
STATE = os.path.join(SCRIPT_DIR, "state")

import chi_phi                                            # noqa: E402

def so_du_kimi(env):
    """Số dư thật của tài khoản Kimi. Nhớ 5 phút để không gọi mỗi lần mở tab.

    17/09: bản đọc số dư dọn về MỘT chỗ duy nhất là chi_phi.so_du_that(). Trước đó chỉ tab
    Tổng quan biết số dư thật, còn phanh chi tiêu trong ai_sale lại chạy theo sổ tự cộng —
    nên sổ và bảng lệch dần mà không cái nào chặn. Giữ tên hàm để chỗ gọi cũ khỏi sửa.
    """
    _nha = (env.get("AI_PROVIDER") or "kimi").strip().lower()
    return chi_phi.so_du_that(_nha, e=env, moi_giay=300)


def _doc_json(f, mac_dinh):
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:                                     # noqa: BLE001
        return mac_dinh


def _tien(rs):
    return sum(r.get("tien") or 0 for r in rs)


def _dd(ngay):
    return f"{ngay[8:10]}/{ngay[5:7]}" if len(ngay) >= 10 else ngay


# Nhật ký tối ưu — ngày là ngày ÁP DỤNG, hiệu quả đọc ở bảng theo ngày.
NHAT_KY = [
    ("10/09", "Bắt đầu gửi thật ở UAE (11:24 giờ VN). Sáng cùng ngày chạy THỬ bằng tay để soát câu "
              "AI định gửi — tốn tiền model nhưng không gửi tin nào.", "khởi động"),
    ("10/09", "Hai luật cứng 'Botcake đã rep thì AI im' (bot rep 2 tin liền / bot đã báo giá bằng "
              "con số) — chạy trước khi gọi model, 0 token.", "giảm lượt gọi"),
    ("11/09", "TẮT cửa 'đọc lại câu Botcake xem trúng hay lạc' — hôm 10/09 cửa này 250 lượt, "
              "203 lượt đọc xong rồi im (thuần lãng phí).", "giảm lượt gọi"),
    ("11/09", "Gọn bản ghi hội thoại đưa model: bỏ tin hệ thống Facebook, cắt tin Botcake còn 120 "
              "ký tự, bỏ tin bot trùng, tin sale 300 ký tự.", "giảm token vào"),
    ("11/09", "JSON trả về gọn (lý do ≤ 8 chữ, ghi chú chỉ khi treo/lên đơn) — token ra mỗi lượt "
              "giảm dần theo ngày.", "giảm token ra"),
    ("11/09", "Page bị Facebook chặn (#2022): chỉ soạn 1 câu / 15 phút / hội thoại vào ghi chú, "
              "không soạn lại mỗi lượt. Giãn nhịp gửi 20s, tắt gửi ảnh, không lặp SĐT — chống chặn.",
     "giảm lượt gọi"),
    ("12/09", "Tự điền tên khách thay ô #{FULL_NAME}; regex SĐT nhận số gõ có dấu cách; lên đơn "
              "không cần thẻ ở 12 nước.", "chất lượng"),
    ("13/09", "Nhận 'khách xin nói tiếng X' (Hindi/Urdu/Bengali…) và bắt buộc trả lời đúng tiếng; "
              "bật lại cửa đọc lại Botcake NHƯNG chỉ khi tin khách có nội dung thật, kèm định nghĩa "
              "trúng/lạc; đọc lại hội thoại ngay trước khi gửi để nhường sale vừa rep; dò 8s, đợi "
              "Botcake 15s (rep ~30s thay vì ~55s).", "chất lượng"),
]

CON_LAM = [
    ("Đổi bậc model rẻ hơn (DeepSeek V4.1-Flash)", "rẻ hơn Kimi K2.6 khoảng 4–7 lần với đúng gói "
     "prompt hiện tại (giá niêm yết 09/2026). Code đã sẵn (so_model.py chạy A/B cùng một mẻ hội "
     "thoại), chỉ chờ dán DEEPSEEK_API_KEY ở tab Cấu hình rồi so chất lượng trước khi đổi thật.",
     "−70…85% tiền/lượt"),
    ("Gỡ chặn Facebook (#2022) cho các page", "phần lớn tiền soạn câu đang chảy vào GHI CHÚ vì page "
     "bị chặn gửi qua API; sale chỉ chép ~35% số câu đó. Thoát bằng tài khoản sạch / gửi từ giao "
     "diện Pancake là tiền soạn ra tới khách gần như 100%.", "tăng tiền hữu ích, không giảm chi"),
    ("Botcake học thêm từ khoá", "khoảng 15% lượt AI vào cuộc là khách hỏi giá, ~10% hỏi ship/COD/còn "
     "hàng — Botcake trả lời được thì AI không phải gọi model. Ước cắt 20–25% lượt gọi.",
     "−20…25% lượt gọi"),
    ("Gọn gói prompt", "mỗi lượt gửi model ~10–11 nghìn token (kịch bản page + luật + hồ sơ khách + "
     "hội thoại), 2/3 đọc từ bộ đệm giá rẻ. Cắt kịch bản thừa, rút luật — ước −10…15%.",
     "−10…15% tiền/lượt"),
    ("Hiệu chỉnh bảng giá theo hoá đơn Kimi thật", "sổ nội bộ tính theo giá niêm yết trong code; "
     "tài khoản Kimi trừ ít hơn nhiều (xem ô 'Kimi thực trừ'). Nếu lệch bền thì sửa bảng giá để "
     "dự báo và trần ngày khỏi báo động sớm.", "số đúng để quyết định"),
]


_DON = {"luc": 0, "mkey": None, "kq": None}


def kiem_ke_page(mkey):
    """Câu chủ shop 13/09: "đã xử lý được bao nhiêu page, bao nhiêu page không xử lý được, lý do cụ thể".
    Nguồn: state/<tt>/page_tokens.json (token / hỏng / hết gói / thiếu quyền), quan_ly.bang_page
    (bậc sẵn sàng: kịch bản, SKU, giá sàn), hieu_suat.json (lưu lượng 72h), page_bi_fb_chan.json."""
    import quan_ly as QL
    pt = _doc_json(os.path.join(STATE, mkey, "page_tokens.json"), {})
    hs = _doc_json(os.path.join(STATE, mkey, "hieu_suat.json"), {})
    luot = {r["pid"]: r for r in (hs.get("bang_that") or hs.get("bang") or [])}
    chan = _doc_json(os.path.join(STATE, mkey, "page_bi_fb_chan.json"), {})
    try:
        b = QL.bang_page(mkey)
    except Exception:                                     # noqa: BLE001
        b = {"page": [], "tong": 0, "ngung": 0}
    ps = b.get("page") or []
    def dong(p):
        l = luot.get(p["pid"], {})
        return {"ten": p["ten"].strip(), "luot": l.get("luot", 0), "bot_im": l.get("bot_im", 0),
                "ai_xu_ly": l.get("ai_xu_ly", 0), "tin_gui": l.get("tin_gui", 0),
                "chan": p["pid"] in chan, "thieu": p.get("thieu", "")}
    nhom = []
    for bac, ten, giai in [
        (4, "Đủ điều kiện — AI đang chạy", "có kịch bản, SKU và giá sàn. AI trả lời và lên đơn được."),
        (2, "Chưa có SKU — AI chat được, KHÔNG lên đơn được", "kịch bản có nhưng sản phẩm chưa gắn SKU trên POS, "
            "tool không biết lên đơn mặt hàng nào. Sửa: gắn SKU ở tab Page & kịch bản."),
        (1, "Chưa có kịch bản — AI không chạy", "không có nguồn giá / chính sách để trả lời, AI bỏ qua page. "
            "Sửa: tạo mẫu 'Trả lời nhanh' trên Pancake cho page."),
    ]:
        grp = [dong(p) for p in ps if p.get("bac") == bac]
        grp.sort(key=lambda x: -x["luot"])
        nhom.append({"ten": ten, "giai": giai, "so": len(grp),
                     "co_khach": len([x for x in grp if x["luot"]]),
                     "luot": sum(x["luot"] for x in grp), "chan": len([x for x in grp if x["chan"]]),
                     "ds": grp[:10]})
    # page_tokens.json chứa page của MỌI thị trường (bẫy đã ghi trong bộ nhớ) → lọc theo shop POS.
    # Thử 13/09: 16 page "token hỏng" thì 11 thuộc TW/Saudi/Kuwait/Qatar/US; 5 page UAE cấp lại
    # không được vì Pancake trả lỗi 121 "không tìm thấy gói cước" = hết gói, không phải lỗi mình.
    try:
        import ai_sale as A
        trong_shop = A._pages_cua_shop(mkey)
    except Exception:                                     # noqa: BLE001
        trong_shop = None
    def cua_shop(pid):
        return trong_shop is None or str(pid) in {str(x) for x in trong_shop}
    hong = [v.get("name") for pid, v in pt.items() if v.get("token_hong") and cua_shop(pid)]
    het_goi = [v.get("name") for pid, v in pt.items() if v.get("bo_qua") == "het_goi_cuoc" and cua_shop(pid)]
    thieu_quyen = [v.get("name") for pid, v in pt.items()
                   if "Thiếu quyền Admin" in str(v.get("loi") or "") and cua_shop(pid)]
    return {"tong_shop": len(ps) + len(hong), "nhom": nhom,
            "token_hong": hong, "het_goi": len(het_goi), "thieu_quyen": thieu_quyen,
            "tong_tai_khoan": len(pt), "chan": len(chan), "gio": hs.get("gio")}


def pheu_don(mkey, rows):
    """Câu chủ shop 13/09: "sao chốt được ít đơn vậy". Đơn lấy THẬT từ POS (từ ngày đầu chạy),
    phân nguồn theo note + conversation_id; phễu từ sổ chi phí và hồ sơ khách."""
    goi_that = [r for r in rows if r.get("that") and r.get("goi")]
    if not goi_that:
        return None
    ngay_dau = min(r["luc"][:10] for r in goi_that)
    if _DON["kq"] and _DON["mkey"] == mkey and time.time() - _DON["luc"] < 600:
        don = _DON["kq"]
    else:
        import pancake_order as PO
        PO.load_env()
        tu = int(time.mktime(time.strptime(ngay_dau, "%Y-%m-%d"))) - 7 * 3600 - 2 * 3600
        don = []
        try:
            for pn in range(1, 60):
                ps = PO.fetch_orders({"startDateTime": tu, "endDateTime": int(time.time()),
                                      "page_size": 100, "page_number": pn, "updateStatus": "inserted_at"})
                if not ps:
                    break
                don += ps
        except Exception as e:                            # noqa: BLE001
            return {"loi": f"không đọc được đơn POS: {str(e)[:100]}"}
        _DON.update(luc=time.time(), mkey=mkey, kq=don)
    import pancake_order as PO
    ten_tt = {c: n for c, n, _ in PO.STATUSES}
    ai_conv = {r["conv"] for r in goi_that if r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo")}
    pt = _doc_json(os.path.join(STATE, mkey, "page_tokens.json"), {})
    def loai(o):
        n, conv = (o.get("note") or ""), (o.get("conversation_id") or "")
        if n.lstrip().startswith("[Tự động]"):
            return "AI chat rồi tool tự lên đơn" if conv in ai_conv else "Tool tự lên đơn trên chat của sale"
        return "Sale tự lên từ chat" if conv else "Landing / nguồn khác"
    thu_tu = ["AI chat rồi tool tự lên đơn", "Tool tự lên đơn trên chat của sale", "Sale tự lên từ chat", "Landing / nguồn khác"]
    nguon = []
    for l in thu_tu:
        os_ = [o for o in don if loai(o) == l]
        tt = Counter(ten_tt.get(o.get("status"), str(o.get("status"))) for o in os_)
        huy = sum(1 for o in os_ if o.get("status") in (6, 7))
        nguon.append({"ten": l, "so": len(os_), "huy": huy,
                      "moi": sum(1 for o in os_ if o.get("status") == 0),
                      "trang_thai": tt.most_common(),
                      "theo_ngay": sorted(Counter((o.get("inserted_at") or "")[:10] for o in os_).items())})
    theo_page = defaultdict(Counter)
    for o in don:
        cv = o.get("conversation_id") or ""
        if cv:
            theo_page[(pt.get(cv.split("_")[0]) or {}).get("name") or cv.split("_")[0]][loai(o)] += 1
    bang_page = [{"page": p, "tong": sum(c.values()), **{l: c.get(l, 0) for l in thu_tu[:3]}}
                 for p, c in sorted(theo_page.items(), key=lambda x: -sum(x[1].values()))[:12]]
    # phễu
    convs = defaultdict(list)
    for r in rows:
        if r.get("that"):
            convs[r["conv"]].append(r)
    n_ai = n_rep = 0
    for cv, rs in convs.items():
        rs.sort(key=lambda r: r.get("khach_luc") or "")
        idx = [i for i, r in enumerate(rs) if r.get("goi") and r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo")]
        if not idx:
            continue
        n_ai += 1
        first = rs[idx[0]].get("khach_luc") or ""
        if any((r.get("khach_luc") or "") > first for r in rs):
            n_rep += 1
    don_conv = {o.get("conversation_id") for o in don if o.get("conversation_id")}
    ho_so = {}
    try:
        import sqlite3
        con = sqlite3.connect(os.path.join(STATE, mkey, "ho_so.db"))
        hr = con.execute("select conv_id,sdt,dia_chi,buoc from ho_so").fetchall()
        ho_so = {"tong": len(hr), "sdt": sum(1 for r in hr if r[1]), "dia_chi": sum(1 for r in hr if r[2]),
                 "ca_hai": sum(1 for r in hr if r[1] and r[2]),
                 "buoc": Counter(r[3] for r in hr).most_common(),
                 "sdt_chua_don": sum(1 for r in hr if r[1] and r[0] not in don_conv)}
    except Exception:                                     # noqa: BLE001
        pass
    return {"tu": _dd(ngay_dau), "tong": len(don), "nguon": nguon, "theo_page": bang_page,
            "pheu": {"ai_soan": n_ai, "khach_rep": n_rep, "co_don": len(ai_conv & don_conv)},
            "ho_so": ho_so}


TEN_NHA = {"kimi": "Kimi", "deepseek": "DeepSeek", "anthropic": "Claude"}

_NHO_CHI_NHA = {"luc": 0, "nha": None, "kq": None}


def chi_moi_nuoc(nha, moi_giay=60):
    """Tổng tiền sổ (tool tự tính) + số lượt của MỘT nhà model, gộp MỌI thị trường.

    Số dư API là của cả tài khoản, 6 nước dùng chung một key — muốn so "thực trừ" với sổ thì
    phải cộng sổ mọi nước. Lọc bằng chuỗi trước rồi mới json.loads: 29MB sổ quét hết ~0,2s.
    """
    import glob
    now = time.time()
    if _NHO_CHI_NHA["kq"] and _NHO_CHI_NHA["nha"] == nha and now - _NHO_CHI_NHA["luc"] < moi_giay:
        return _NHO_CHI_NHA["kq"]
    dau, tien, luot, som = f'"nha": "{nha}"', 0.0, 0, None
    for f in glob.glob(os.path.join(STATE, "*", "so_chi_phi.jsonl")):
        try:
            with open(f, encoding="utf-8") as fh:
                for d in fh:
                    if dau not in d:
                        continue
                    try:
                        r = json.loads(d)
                    except Exception:                    # noqa: BLE001
                        continue
                    if not r.get("goi"):
                        continue
                    tien += float(r.get("tien") or 0)
                    luot += 1
                    if r.get("luc") and (som is None or r["luc"] < som):
                        som = r["luc"]
        except OSError:
            continue
    kq = {"tien": tien, "luot": luot, "tu": som}
    _NHO_CHI_NHA.update(luc=now, nha=nha, kq=kq)
    return kq


def bao_cao(mkey, env=None):
    if env is None:
        import quet_hoi_thoai as q
        env = q.load_env()
    rows = list(chi_phi.doc(mkey))
    goi = [r for r in rows if r.get("goi")]
    nha = (env.get("AI_PROVIDER") or "kimi").strip().lower()
    model = (env.get("AI_MODEL") or "").strip()
    nap_ds = [x for x in chi_phi.doc_nap() if (x.get("nha") or nha) == nha]
    nap = sum(float(x.get("so_tien") or 0) for x in nap_ds)
    so_du = so_du_kimi(env)          # đã theo AI_PROVIDER; nhà chưa có endpoint thì co=False
    chan = _doc_json(os.path.join(STATE, mkey, "page_bi_fb_chan.json"), {})
    hs = _doc_json(os.path.join(STATE, mkey, "hieu_suat.json"), {})

    kq = {"mkey": mkey, "nha": nha, "model": model, "luc": time.strftime("%d/%m/%Y %H:%M"),
          "co_so": bool(goi)}
    if not goi:
        kq["nap"] = nap
        kq["so_du"] = so_du
        return kq

    # ── Tổng ─────────────────────────────────────────────────────────────
    chi = _tien(goi)
    ngay_co = sorted({r["luc"][:10] for r in goi})
    tu, den = ngay_co[0], ngay_co[-1]
    tra_loi = [r for r in goi if r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo")]
    kimi_tru = (nap - so_du["con"]) if (so_du.get("co") and nap) else None

    # 20/09: sổ có cả lượt của Kimi (10–20/09) lẫn DeepSeek (từ 20/09 05:09). "Thực trừ" là của
    # NHÀ ĐANG CHẠY, nên giá mỗi lượt / mỗi câu cũng chỉ được chia cho lượt của nhà đó.
    goi_nha = [r for r in goi if (r.get("nha") or "kimi").strip().lower() == nha]
    tk_nha = chi_moi_nuoc(nha)                          # cả tài khoản, mọi thị trường
    chi_nha = _tien(goi_nha)
    tra_loi_nha = [r for r in goi_nha if r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo")]
    ngay_nha = sorted({r["luc"][:10] for r in goi_nha})
    gio_nha = None
    if goi_nha:
        try:
            _t0 = time.mktime(time.strptime(goi_nha[0]["luc"][:19], "%Y-%m-%dT%H:%M:%S"))
            gio_nha = max(0.1, (time.time() - _t0) / 3600)
        except Exception:                                # noqa: BLE001
            gio_nha = None

    # ── Theo ngày ────────────────────────────────────────────────────────
    theo_ngay = []
    for d in ngay_co:
        rs = [r for r in goi if r["luc"][:10] == d]
        n = len(rs)
        theo_ngay.append({
            "ngay": _dd(d), "goi": n, "tien": _tien(rs), "tb": _tien(rs) / n,
            "vao": sum(r.get("vao") or 0 for r in rs) // n,
            "dem": sum(r.get("doc_dem") or 0 for r in rs) // n,
            "ra": sum(r.get("ra") or 0 for r in rs) // n,
            "thu": len([r for r in rs if not r.get("that")]),
            "tien_thu": _tien([r for r in rs if not r.get("that")]),
            "xet": len([r for r in rs if r.get("cua") == "xet"]),
            "tra_loi": len([r for r in rs if r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo")]),
            "im": len([r for r in rs if r.get("hd") == "im"]),
            "treo": len([r for r in rs if r.get("hd") == "treo"]),
            "len_don": len([r for r in rs if r.get("hd") == "len_don"]),
            "luot_khach": len({(r["conv"], r.get("khach_luc")) for r in rows if r["luc"][:10] == d}),
            "khach": len({r["conv"] for r in rows if r["luc"][:10] == d}),
        })

    # ── Tiền đi đâu theo KẾT CỤC của lượt gọi ─────────────────────────────
    thu = [r for r in goi if not r.get("that")]
    that = [r for r in goi if r.get("that")]
    xet_im = [r for r in that if r.get("cua") == "xet" and r.get("hd") == "im"]
    xet_rep = [r for r in that if r.get("cua") == "xet" and r.get("hd") != "im"]
    im_khac = [r for r in that if r.get("cua") != "xet" and r.get("hd") == "im"]
    treo = [r for r in that if r.get("hd") == "treo"]
    loi = [r for r in that if r.get("hd") == "loi"]
    tl_that = [r for r in that if r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo")]
    tl_chan = [r for r in tl_that if str(r.get("pid")) in chan]
    tl_thong = [r for r in tl_that if str(r.get("pid")) not in chan]
    ket_cuc = [
        {"ten": "Soạn câu trả lời cho khách — page HIỆN đang bị Facebook chặn gửi",
         "luot": len(tl_chan), "tien": _tien(tl_chan),
         "giai_thich": "AI vẫn soạn nhưng API không gửi được (#2022); câu nằm trong ghi chú cho "
                       "sale chép gửi tay. Chủ shop 11/09 chọn GIỮ dù biết tốn. Tính theo page đang "
                       "chặn lúc lập báo cáo — số đo hieu_suat.py bên dưới là số tin thật đã đi."},
        {"ten": "Soạn câu trả lời cho khách — page gửi được",
         "luot": len(tl_thong), "tien": _tien(tl_thong),
         "giai_thich": "Tin đi thẳng tới khách qua API (gồm cả lượt chốt đơn)."},
        {"ten": "Đọc lại câu Botcake rồi IM", "luot": len(xet_im), "tien": _tien(xet_im),
         "giai_thich": "Botcake đã rep, model đọc xem trúng chưa, kết luận trúng → không nhắn. "
                       "Đây là phần lãng phí rõ nhất, đã tắt 11/09, bật lại 13/09 có siết."},
        {"ten": "Đọc lại câu Botcake rồi trả lời lại", "luot": len(xet_rep), "tien": _tien(xet_rep),
         "giai_thich": "Model phán bot lạc đề và nhắn lại."},
        {"ten": "Treo cho sale (kèm ghi chú)", "luot": len(treo), "tien": _tien(treo),
         "giai_thich": "Khách hỏi ngoài kịch bản / xin ảnh / khiếu nại — AI ghi chú, đánh dấu chưa "
                       "đọc, không nhắn."},
        {"ten": "Gọi model nhưng kết cục im (ngoài cửa đọc lại)", "luot": len(im_khac),
         "tien": _tien(im_khac), "giai_thich": "Khách chào/cảm ơn/kết thúc — model tự chọn im."},
        {"ten": "Chạy THỬ bằng tay (không gửi gì)", "luot": len(thu), "tien": _tien(thu),
         "giai_thich": "Vòng soát câu trước khi bật gửi thật, sáng 10/09."},
        {"ten": "Lỗi (model trả sai khuôn / 429)", "luot": len(loi), "tien": _tien(loi),
         "giai_thich": "Tốn lượt gọi mà không có câu."},
    ]
    ket_cuc = [k for k in ket_cuc if k["luot"]]

    # ── Lặp: cùng một tin khách gọi model nhiều lần ───────────────────────
    c = Counter((r["conv"], r.get("khach_luc")) for r in goi)
    lap_luot = sum(v - 1 for v in c.values() if v > 1)
    lap_tien = 0.0
    for k, v in c.items():
        if v > 1:
            t = _tien([r for r in goi if (r["conv"], r.get("khach_luc")) == k])
            lap_tien += t * (v - 1) / v
    cc = Counter(r["conv"] for r in goi)
    ht_nhieu = [k for k, v in cc.items() if v >= 4]
    ht_nhieu_tien = _tien([r for r in goi if cc[r["conv"]] >= 4])

    # ── Token ────────────────────────────────────────────────────────────
    import ai_sale as A
    (gv, gd, gg, gr), _ = A.gia_theo_model(nha, model or (goi[-1].get("model") or ""))
    vao = sum(r.get("vao") or 0 for r in goi)
    dem = sum(r.get("doc_dem") or 0 for r in goi)
    ra = sum(r.get("ra") or 0 for r in goi)
    token = {"vao": vao, "dem": dem, "ra": ra, "luot": len(goi),
             "tien_vao": vao * gv / 1e6, "tien_dem": dem * gd / 1e6, "tien_ra": ra * gr / 1e6,
             "gia": {"vao": gv, "dem": gd, "ra": gr}}

    # ── Theo page ────────────────────────────────────────────────────────
    pg = defaultdict(lambda: {"goi": 0, "tien": 0.0, "tra_loi": 0, "don": 0, "khach": set()})
    for r in goi:
        p = pg[r.get("page") or r.get("pid")]
        p["goi"] += 1
        p["tien"] += r.get("tien") or 0
        p["khach"].add(r["conv"])
        p["pid"] = str(r.get("pid"))
        if r.get("hd") in ("tra_loi", "len_don", "tra_loi_treo"):
            p["tra_loi"] += 1
        if r.get("hd") == "len_don":
            p["don"] += 1
    theo_page = [{"page": k, "goi": v["goi"], "tien": v["tien"], "tra_loi": v["tra_loi"],
                  "don": v["don"], "khach": len(v["khach"]), "chan": v["pid"] in chan}
                 for k, v in sorted(pg.items(), key=lambda x: -x[1]["tien"])]

    # ── Hiệu suất (số đo thật của hieu_suat.py, nếu có) ──────────────────
    hs_tom = None
    hs_tien = hs.get("tien") or {}                       # hieu_suat.py xếp viec/moi_tin dưới "tien"
    if hs_tien.get("viec"):
        v = hs_tien["viec"]
        hs_tom = {"gio": hs.get("gio"), "luc": time.strftime("%d/%m %H:%M", time.localtime(hs.get("luc", 0))),
                  "gui": v.get("gui", 0), "ghi_chu": v.get("ghi_chu", 0), "chan": v.get("chan", 0),
                  "len_don": v.get("len_don", 0), "hong": v.get("hong", 0),
                  "moi_tin": hs_tien.get("moi_tin") or {},
                  "tong": {k: (hs.get("tong_that") or hs.get("tong") or {}).get(k)
                           for k in ("luot", "bot", "ai", "sale", "ai_xu_ly", "bot_im", "hoi_thoai")}}

    # ── Page nào Botcake đỡ ít → AI phải gánh (chủ shop 13/09: "xem page nào phải xử lý
    #    nhiều tin nhắn => set bot sơ sài") — số từ bảng theo page của hieu_suat.py ──────────
    bot_so_sai = []
    for r in (hs.get("bang_that") or hs.get("bang") or []):
        if (r.get("luot") or 0) < 15:
            continue
        bot_so_sai.append({"page": r.get("page"), "luot": r["luot"], "bot": r.get("bot", 0),
                           "bot_im": r.get("bot_im", 0), "ty_le_im": r["bot_im"] / r["luot"],
                           "ai_xu_ly": r.get("ai_xu_ly", 0), "tin_gui": r.get("tin_gui", 0),
                           "tien": r.get("tien", 0), "co_botcake": r.get("co_botcake", True)})
    bot_so_sai.sort(key=lambda x: -x["ty_le_im"])

    # ── Nguyên nhân tiền đi nhanh (viết bằng số thật) ─────────────────────
    ngay_dau = theo_ngay[0]
    nguyen_nhan = []
    if tl_chan:
        nguyen_nhan.append(
            f"{len(chan)} trên {len(pg)} page có gọi model đang bị Facebook chặn gửi qua API. "
            f"{len(tl_chan):,} lượt soạn câu ({round(_tien(tl_chan) / chi * 100)}% "
            f"tổng tiền) rơi vào ghi chú cho sale gửi tay thay vì tới khách. Tiền vẫn mất, hiệu "
            f"quả phụ thuộc sale có chép hay không (đo 11/09: chép ~35%). Nhiều page mới bị chặn "
            f"SAU khi AI đã gửi được một thời gian, nên con số này là mức trần"
            + (f"; số đo thật hieu_suat.py {hs_tom['gio']:.0f} giờ gần nhất: {hs_tom['gui']} tin "
               f"gửi thẳng tới khách, {hs_tom['ghi_chu']} câu chỉ vào ghi chú." if hs_tom else "."))
    if xet_im:
        nguyen_nhan.append(
            f"Cửa 'đọc lại câu Botcake': {len(xet_im) + len(xet_rep):,} lượt = "
            f"${_tien(xet_im) + _tien(xet_rep):.2f}, trong đó {len(xet_im):,} lượt đọc xong rồi im. "
            f"Riêng ngày {ngay_dau['ngay']} là {ngay_dau['xet']:,} lượt. Đã tắt 11/09, bật lại "
            f"13/09 kèm luật chặn tin chào/ok/emoji.")
    if thu:
        nguyen_nhan.append(
            f"Chạy thử bằng tay sáng 10/09: {len(thu):,} lượt = ${_tien(thu):.2f} "
            f"({round(_tien(thu) / chi * 100)}% tổng) — soát câu, không gửi tin nào.")
    nguyen_nhan.append(
        f"Mỗi lượt gọi gửi model trung bình {(vao + dem) // len(goi):,} token vào "
        f"(trong đó {dem // len(goi):,} đọc từ bộ đệm giá rẻ) + {ra // len(goi):,} token ra "
        f"= ${chi / len(goi):.4f}/lượt. Gói lớn vì mang cả kịch bản page, bộ luật, hồ sơ khách và "
        f"hội thoại. Tiền vào-không-đệm chiếm {round(token['tien_vao'] / chi * 100)}%, "
        f"đệm {round(token['tien_dem'] / chi * 100)}%, ra {round(token['tien_ra'] / chi * 100)}%.")
    if lap_luot:
        nguyen_nhan.append(
            f"{lap_luot:,} lượt gọi lặp cho cùng một tin khách (${lap_tien:.2f}) và "
            f"{len(ht_nhieu):,} hội thoại tốn từ 4 lượt trở lên (${ht_nhieu_tien:.2f}) — phần lớn "
            f"là page bị chặn: AI soạn, không gửi được, khách hỏi lại, AI soạn tiếp.")
    if kimi_tru is not None:
        nguyen_nhan.append(
            f"LƯU Ý QUAN TRỌNG: tool tự tính ${tk_nha['tien']:.2f} cho {tk_nha['luot']:,} lượt chạy bằng "
            f"{TEN_NHA.get(nha, nha)} ở mọi thị trường (đếm token × giá niêm yết trong code), nhưng tài khoản "
            f"{TEN_NHA.get(nha, nha)} thực tế mới trừ ${kimi_tru:.2f} (còn ${so_du['con']:.2f} trên "
            f"${nap:.2f} đã nạp). Tiền CHƯA hết — con số 'còn lại' trong log và trần ngày là tính "
            f"theo sổ nội bộ, không phải số dư thật.")

    # ── Dự báo ──────────────────────────────────────────────────────────
    tb_ngay = chi / len(ngay_co)
    du_bao = {"tb_ngay_so": tb_ngay,
              "con_ngay_so": (so_du["con"] / tb_ngay) if so_du.get("co") and tb_ngay else None}
    if kimi_tru is not None and kimi_tru > 0:
        # Chia cho số ngày CỦA NHÀ ĐANG CHẠY; nhà mới chạy chưa hết ngày thì quy về 1 ngày đủ
        # (gio_nha < 24 → nhân 24/gio_nha) để "đủ mấy ngày nữa" không bị thổi phồng.
        tb_that = kimi_tru / max(1, len(ngay_nha))
        if gio_nha and gio_nha < 24:
            tb_that = kimi_tru * 24 / gio_nha
        du_bao["tb_ngay_that"] = tb_that
        du_bao["con_ngay_that"] = so_du["con"] / tb_that if tb_that else None
        du_bao["uoc_ngay_that"] = bool(gio_nha and gio_nha < 24)

    try:
        kq["page_kk"] = kiem_ke_page(mkey)
    except Exception as e:                                # noqa: BLE001
        kq["page_kk"] = {"loi": str(e)[:120]}
    try:
        kq["don"] = pheu_don(mkey, rows)
    except Exception as e:                                # noqa: BLE001
        kq["don"] = {"loi": str(e)[:120]}
    # Mục 7: ước chi phí nếu AI phủ TOÀN BỘ page của tài khoản (mọi thị trường). Số từ
    # luu_luong.py (quét thống kê Pancake customer_engagements 7 ngày, ~20 phút) + tinh_chi_phi.py
    # (hệ số tiền/khách nhắn đo từ UAE). Chạy tay khi cần cập nhật:
    #   python3 luu_luong.py && python3 tinh_chi_phi.py
    tb = _doc_json(os.path.join(STATE, "chi_phi_toan_bo.json"), None)
    if tb:
        f = os.path.join(STATE, "chi_phi_toan_bo.json")
        ps = tb.get("page") or []
        kq["toan_bo"] = {"luc": time.strftime("%d/%m/%Y %H:%M", time.localtime(os.path.getmtime(f))),
                         "he_so": tb.get("he_so"), "so_page": len(ps),
                         "con_goi": sum(1 for p in ps if p.get("goi_con")),
                         "theo_tt": sorted(tb.get("theo_tt", {}).values(), key=lambda r: -r[4]),
                         "top": [(p["ten"], p["tt"], p["inbox"], bool(p.get("goi_con"))) for p in sorted(ps, key=lambda p: -p.get("inbox", 0))[:15]]}
    kq.update({
        "nap": nap, "nap_ds": nap_ds, "so_du": so_du, "kimi_tru": kimi_tru,
        "chi": chi, "goi": len(goi), "tu": _dd(tu), "den": _dd(den), "so_ngay": len(ngay_co),
        "chi_nha": chi_nha, "goi_nha": len(goi_nha), "tra_loi_nha": len(tra_loi_nha),
        "chi_nha_tk": tk_nha["tien"], "goi_nha_tk": tk_nha["luot"],
        "ngay_nha": len(ngay_nha), "tu_nha": _dd(ngay_nha[0]) if ngay_nha else None,
        "gio_nha": round(gio_nha, 1) if gio_nha else None,
        "tra_loi": len(tra_loi), "tien_tra_loi": _tien(tra_loi),
        "khach": len({r["conv"] for r in rows}), "luot_khach": len({(r["conv"], r.get("khach_luc")) for r in rows}),
        "hoi_thoai_goi": len(cc), "len_don": len([r for r in goi if r.get("hd") == "len_don"]),
        "theo_ngay": theo_ngay, "ket_cuc": ket_cuc, "token": token,
        "lap": {"luot": lap_luot, "tien": lap_tien, "ht_nhieu": len(ht_nhieu), "ht_nhieu_tien": ht_nhieu_tien},
        "theo_page": theo_page, "so_page": len(pg), "so_page_chan": len([p for p in theo_page if p["chan"]]),
        "hieu_suat": hs_tom, "bot_so_sai": bot_so_sai[:20], "nguyen_nhan": nguyen_nhan,
        "nhat_ky": NHAT_KY, "con_lam": CON_LAM, "du_bao": du_bao,
    })
    if kimi_tru is not None and kimi_tru > 0 and goi_nha:
        # Tin gửi thật chỉ đo được trong cửa sổ hiệu suất (thường 24h). Nhà mới chạy ngắn hơn cửa
        # sổ đó thì chia theo tỉ lệ giờ và bật cờ "uoc_gui" để trang nói rõ đấy là ước.
        _gui = hs_tom.get("gui") if hs_tom else None
        _uoc = False
        if _gui and gio_nha and hs_tom.get("gio") and gio_nha < hs_tom["gio"]:
            _gui, _uoc = _gui * gio_nha / hs_tom["gio"], True
        # Giá mỗi lượt = tiền nhà model trừ thật ÷ số lượt của CẢ TÀI KHOẢN (cùng phạm vi).
        # Giá mỗi câu / mỗi tin của thị trường này = giá mỗi lượt × số lượt phải bỏ ra cho một câu.
        _luot_tk = tk_nha["luot"] or len(goi_nha)
        _moi_luot = kimi_tru / _luot_tk
        kq["gia_that"] = {"moi_luot": _moi_luot,
                          "moi_cau_soan": _moi_luot * len(goi_nha) / len(tra_loi_nha) if tra_loi_nha else None,
                          "moi_tin_gui": (_moi_luot * len(goi_nha) / _gui) if _gui else None,
                          "uoc_gui": _uoc, "luot_tk": _luot_tk, "ty_gia": 26300}
    kq["van_ban"] = van_ban(kq)
    return kq


def _usd(x):
    return f"${x:,.2f}" if abs(x) >= 1 else f"${x:,.4f}"


def van_ban(k):
    """Bản chữ để chép dán vào báo cáo / Zalo / email."""
    L = []
    L.append(f"BÁO CÁO CHI PHÍ AI SALE — thị trường {k['mkey'].upper()} — lập {k['luc']}")
    L.append("=" * 70)
    L.append(f"Đã nạp {k['nha']}: {_usd(k['nap'])}. Chạy từ {k['tu']} đến {k['den']} ({k['so_ngay']} ngày).")
    L.append(f"Tool tự tính (đếm token × giá niêm yết): {_usd(k['chi'])} cho {k['goi']:,} lượt gọi model "
             f"({k['model'] or '?'}), trung bình {_usd(k['chi'] / k['goi'])}/lượt.")
    if k.get("so_du", {}).get("co"):
        _tn = TEN_NHA.get(k["nha"], k["nha"])
        L.append(f"Tài khoản {_tn} thực tế: còn {_usd(k['so_du']['con'])}"
                 + (f" → thực trừ {_usd(k['kimi_tru'])} cho {k.get('goi_nha_tk', 0):,} lượt chạy bằng {_tn} "
                    f"ở mọi thị trường (tool tự tính {_usd(k.get('chi_nha_tk') or 0)} phần đó; "
                    f"riêng {k['mkey'].upper()} {k.get('goi_nha', 0):,} lượt / {_usd(k.get('chi_nha') or 0)})." if k.get("kimi_tru") is not None
                    else " (chưa khai tiền nạp cho nhà này nên chưa tính được đã trừ bao nhiêu)."))
    L.append(f"Khách được AI đụng tới: {k['khach']:,} hội thoại / {k['luot_khach']:,} lượt khách nhắn; "
             f"{k['hoi_thoai_goi']:,} hội thoại có gọi model; AI soạn {k['tra_loi']:,} câu trả lời, "
             f"{k['len_don']} lượt chốt đơn.")
    g, h = k.get("gia_that"), k.get("hieu_suat")
    L.append("")
    L.append("BỐN CÂU HỎI CỦA CHỦ SHOP")
    _tn = TEN_NHA.get(k["nha"], k["nha"])
    L.append(f"1. {_tn} thực trừ là gì, tài khoản còn bao nhiêu?")
    if k.get("so_du", {}).get("co") and k.get("kimi_tru") is not None:
        _cn = k.get("chi_nha_tk") or 0
        L.append(f"   Tiền nạp {_usd(k['nap'])} − số dư hiện tại {_usd(k['so_du']['con'])} (hỏi API {_tn}) = {_tn} đã trừ {_usd(k['kimi_tru'])}. "
                 f"Tool tự tính {_usd(_cn)} cho phần chạy bằng {_tn} ở mọi thị trường"
                 + (f", cao hơn ~{_cn/k['kimi_tru']:.1f} lần" if k["kimi_tru"] else "")
                 + " — dùng để chia tỉ lệ, số tuyệt đối lấy theo nhà model.")
    if g:
        tg = g["ty_gia"]
        L.append(f"2. Một tin mấy tiền? (theo {TEN_NHA.get(k['nha'], k['nha'])} thực trừ trên {k.get('goi_nha_tk', 0):,} lượt cả tài khoản, {tg:,}đ/USD)")
        L.append(f"   Mỗi lượt gọi model ${g['moi_luot']:.4f} ≈ {g['moi_luot']*tg:,.0f}đ"
                 + (f" · mỗi câu AI soạn ${g['moi_cau_soan']:.4f} ≈ {g['moi_cau_soan']*tg:,.0f}đ" if g.get("moi_cau_soan") else "")
                 + (f" · mỗi tin gửi thật tới khách ${g['moi_tin_gui']:.4f} ≈ {g['moi_tin_gui']*tg:,.0f}đ" if g.get("moi_tin_gui") else ""))
        L.append("   Tin gửi thật đắt hơn vì gánh cả lượt im/treo và câu soạn chỉ vào ghi chú do page bị chặn. Mục tiêu 11/09: 65đ/tin.")
    L.append("3. AI xử lý bao nhiêu tin?")
    L.append(f"   {k['so_ngay']} ngày: quét {k['luot_khach']:,} lượt khách nhắn / {k['khach']:,} hội thoại, gọi model {k['goi']:,} lần, soạn {k['tra_loi']:,} câu, chốt đơn {k['len_don']} lượt.")
    if h and h.get("tong", {}).get("luot"):
        t = h["tong"]
        L.append(f"   Số đo {h['gio']:.0f} giờ: {t['luot']:,} lượt khách nhắn → Botcake đỡ {t['bot']:,} ({t['bot']*100//t['luot']}%), "
                 f"Botcake im {t['bot_im']:,} ({t['bot_im']*100//t['luot']}%), AI xử lý {t['ai_xu_ly']:,} ({t['ai_xu_ly']*100//t['luot']}%): "
                 f"{h['gui']} tin đi thẳng tới khách, {h['ghi_chu']} câu chỉ vào ghi chú; sale người thật {t['sale']:,}.")
    if k.get("bot_so_sai"):
        ds = k["bot_so_sai"]; nen = sorted(ds, key=lambda r: -r["ai_xu_ly"])[:3]
        L.append("4. Page nào Botcake sơ sài → nên set thêm? (xem bảng PAGE NÀO BOTCAKE ĐỠ ÍT bên dưới)")
        L.append("   Đáng set bot nhất: " + "; ".join(f"{r['page']} (AI gánh {r['ai_xu_ly']} lượt / {r['luot']} khách)" for r in nen)
                 + " — lượng khách lớn, mỗi từ khoá thêm vào cắt được nhiều lượt gọi model nhất.")
    pk, dn = k.get("page_kk") or {}, k.get("don") or {}
    if pk.get("nhom"):
        L.append("5. Đã xử lý được bao nhiêu page, bao nhiêu page không, lý do?")
        L.append(f"   Tài khoản có {pk['tong_tai_khoan']} page; thuộc shop {k['mkey'].upper()} và có token: {pk['tong_shop']} page.")
        for n in pk["nhom"]:
            # Chỉ nước nào đã chạy hieu_suat.py mới có "gio" (19/09: chỉ UAE) — thiếu thì nói chưa đo, đừng in 0 khách.
            kh = (f"{n['co_khach']} page có khách {pk['gio']:.0f}h qua ({n['luot']:,} lượt)" if pk.get("gio")
                  else "chưa đo lưu lượng khách nước này")
            L.append(f"   • {n['so']} page {n['ten']} — {kh}, {n['chan']} đang bị FB chặn. {n['giai']}")
            for x in n["ds"][:5]:
                if x["luot"]:
                    L.append(f"       {x['ten']}: {x['luot']} lượt khách, Botcake im {x['bot_im']}, AI xử lý {x['ai_xu_ly']}, gửi {x['tin_gui']}{' (FB chặn)' if x['chan'] else ''}")
        L.append(f"   • {len(pk['token_hong'])} page token hỏng, cấp lại không được vì Pancake báo hết gói cước (lỗi 121) — AI không đọc được hội thoại: {', '.join(pk['token_hong'][:16])}")
        L.append(f"   • Không đụng được: {pk['het_goi']} page khác của shop hết gói cước Pancake, {len(pk['thieu_quyen'])} page thiếu quyền Admin nên không cấp được token{': ' + ', '.join(pk['thieu_quyen'][:10]) if pk['thieu_quyen'] else ''}.")
        L.append(f"   • {pk['chan']} page đang bị Facebook chặn gửi qua API (#2022): AI soạn vào ghi chú, sale gửi tay.")
    if dn.get("nguon"):
        L.append("6. Sao chốt được ít đơn?")
        L.append(f"   Đơn thật trên POS từ {dn['tu']}: {dn['tong']} đơn, chia theo nguồn:")
        for n in dn["nguon"]:
            L.append(f"   • {n['so']:>3} {n['ten']} — hủy {n['huy']}, còn Mới chưa xác nhận {n['moi']}; trạng thái: " + ", ".join(f"{t} {c}" for t, c in n["trang_thai"][:6]))
        p, h = dn["pheu"], dn.get("ho_so") or {}
        L.append(f"   Phễu AI: {p['ai_soan']} hội thoại AI gửi câu thật → {p['khach_rep']} khách nhắn lại ({p['khach_rep']*100//max(p['ai_soan'],1)}%) → {p['co_don']} hội thoại ra đơn ({p['co_don']*100//max(p['ai_soan'],1)}%).")
        if h:
            L.append(f"   Hồ sơ khách AI theo dõi: {h['tong']} — có SĐT {h['sdt']}, có địa chỉ {h['dia_chi']}, đủ cả hai {h['ca_hai']}; có SĐT mà chưa có đơn {h['sdt_chua_don']}. Bước: " + ", ".join(f"{b} {c}" for b, c in h["buoc"]))
        L.append("   Vì sao ít: (1) 61% khách không nhắn lại sau câu AI — một phần vì câu chỉ vào ghi chú do page bị FB chặn, khách không hề nhận được; "
                 "(2) khách từ quảng cáo phần lớn hỏi giá rồi im, Botcake im nên AI mới vào, chứ AI không tạo ra nhu cầu; "
                 "(3) đơn AI lên đang nằm ở 'Mới' chờ sale xác nhận — chưa tính là chốt; (4) page chưa có SKU thì AI chat xong không lên đơn được.")
    tb = k.get("toan_bo")
    if tb:
        hs_ = tb["he_so"]; con = [r for r in tb["theo_tt"]]
        L.append(f"7. Nếu AI phủ toàn bộ {tb['so_page']} page của tài khoản (quét thống kê Pancake 7 ngày, lúc {tb['luc']}) thì tốn bao nhiêu?")
        L.append(f"   Hệ số đo từ UAE: mỗi khách nhắn inbox tốn {hs_['goi_moi_khach']:.2f} lượt gọi model, Kimi thật ${hs_['kimi_moi_khach']:.4f}, tool tính ${hs_['tool_moi_khach']:.4f}.")
        L.append(f"   {'thị trường':<14}{'page':>5}{'còn gói':>8}{'có khách':>9}{'khách/ngày':>11}{'Kimi $/th':>10}{'tool $/th':>10}")
        for r in con:
            if r[4]: L.append(f"   {r[0]:<14}{r[1]:>5}{r[2]:>8}{r[3]:>9}{r[5]:>11.0f}{r[7]:>10.1f}{r[8]:>10.1f}")
        t = [sum(r[i] for r in con) for i in range(1, 9)]
        L.append(f"   {'TỔNG':<14}{t[0]:>5}{t[1]:>8}{t[2]:>9}{t[4]:>11.0f}{t[6]:>10.1f}{t[7]:>10.1f}")
        L.append(f"   Chỉ {tb['con_goi']} page còn gói Pancake là đọc được hội thoại; {tb['so_page']-tb['con_goi']} page hết gói thì AI không đụng được dù trả bao nhiêu tiền model. Đổi DeepSeek Flash: chia thêm 4-7 lần.")
    L.append("")
    L.append("THEO NGÀY")
    for d in k["theo_ngay"]:
        L.append(f"  {d['ngay']}: {d['goi']:>4} lượt gọi = {_usd(d['tien'])} (TB {_usd(d['tb'])}/lượt) · "
                 f"trả lời {d['tra_loi']} · đọc lại bot {d['xet']} · im {d['im']} · treo {d['treo']} · "
                 f"chốt đơn {d['len_don']} · thử tay {d['thu']} ({_usd(d['tien_thu'])}) · "
                 f"token/lượt vào {d['vao']:,} + đệm {d['dem']:,} + ra {d['ra']:,}")
    L.append("")
    L.append("TIỀN ĐI ĐÂU (theo kết cục của từng lượt gọi)")
    for x in k["ket_cuc"]:
        L.append(f"  {_usd(x['tien']):>9}  {x['luot']:>5} lượt  {round(x['tien'] / k['chi'] * 100):>3}%  {x['ten']}")
        L.append(f"             → {x['giai_thich']}")
    t = k["token"]
    L.append("")
    L.append(f"CẤU PHẦN TOKEN: vào không đệm {t['vao']:,} ({_usd(t['tien_vao'])}) · đọc đệm {t['dem']:,} "
             f"({_usd(t['tien_dem'])}) · ra {t['ra']:,} ({_usd(t['tien_ra'])}). "
             f"Giá {k['nha']} {k['model']}: ${t['gia']['vao']}/1tr vào, ${t['gia']['dem']}/1tr đệm, "
             f"${t['gia']['ra']}/1tr ra.")
    L.append("")
    L.append(f"THEO PAGE (top 12 / {k['so_page']} page có gọi, {k['so_page_chan']} đang bị FB chặn)")
    for p in k["theo_page"][:12]:
        L.append(f"  {_usd(p['tien']):>8}  {p['goi']:>4} lượt  {p['khach']:>4} khách  "
                 f"{p['tra_loi']:>4} câu  {p['don']:>2} đơn  {'⛔ chặn ' if p['chan'] else '        '}{p['page']}")
    if k.get("hieu_suat"):
        h = k["hieu_suat"]
        L.append("")
        L.append(f"SỐ ĐO HIỆU SUẤT (hieu_suat.py, {h['gio']:.0f} giờ tới {h['luc']}): tin AI GỬI THẬT {h['gui']} · "
                 f"vào ghi chú vì page chặn {h['ghi_chu']} · cổng chặn giữ lại {h['chan']} · chốt đơn {h['len_don']}. "
                 f"Giá mỗi tin gửi thẳng {_usd(h['moi_tin'].get('gui', 0))}, mỗi tin soạn {_usd(h['moi_tin'].get('soan', 0))}.")
    if k.get("gia_that"):
        g = k["gia_that"]; tg = g["ty_gia"]
        L.append("")
        L.append(f"GIÁ THẬT MỖI TIN (theo số Kimi trừ, tỉ giá {tg:,}đ/USD): mỗi lượt gọi model "
                 f"${g['moi_luot']:.4f} ≈ {g['moi_luot']*tg:,.0f}đ"
                 + (f" · mỗi câu soạn ${g['moi_cau_soan']:.4f} ≈ {g['moi_cau_soan']*tg:,.0f}đ" if g.get('moi_cau_soan') else "")
                 + (f" · mỗi tin gửi thật tới khách ${g['moi_tin_gui']:.4f} ≈ {g['moi_tin_gui']*tg:,.0f}đ (gánh cả tiền các lượt im/treo/ghi chú)" if g.get('moi_tin_gui') else ""))
    if k.get("bot_so_sai"):
        L.append("")
        L.append("PAGE NÀO BOTCAKE ĐỠ ÍT → AI PHẢI GÁNH (xếp theo % lượt khách Botcake im; chỉ page ≥15 lượt)")
        for r in k["bot_so_sai"][:12]:
            L.append(f"  {round(r['ty_le_im']*100):>3}% im  {r['luot']:>4} lượt khách  bot rep {r['bot']:>3}  AI xử lý {r['ai_xu_ly']:>3}  "
                     f"AI gửi {r['tin_gui']:>3}  {_usd(r['tien']):>8}  {r['page']}{'' if r['co_botcake'] else '  (KHÔNG có Botcake)'}")
    L.append("")
    L.append("VÌ SAO TIỀN ĐI NHANH")
    for i, s in enumerate(k["nguyen_nhan"], 1):
        L.append(f"  {i}. {s}")
    L.append("")
    L.append("ĐÃ TỐI ƯU (nhật ký)")
    for ngay, viec, loai in k["nhat_ky"]:
        L.append(f"  {ngay} [{loai}] {viec}")
    L.append("")
    L.append("CÒN LÀM ĐƯỢC")
    for ten, mo_ta, uoc in k["con_lam"]:
        L.append(f"  • {ten} ({uoc}): {mo_ta}")
    db = k["du_bao"]
    L.append("")
    if db.get("con_ngay_so"):
        L.append(f"DỰ BÁO: theo sổ nội bộ {_usd(db['tb_ngay_so'])}/ngày → số dư hiện tại đủ ~{db['con_ngay_so']:.0f} ngày"
                 + (f"; theo mức Kimi thực trừ {_usd(db['tb_ngay_that'])}/ngày → ~{db['con_ngay_that']:.0f} ngày."
                    if db.get("con_ngay_that") else "."))
    return "\n".join(L)


if __name__ == "__main__":
    mk = sys.argv[1] if len(sys.argv) > 1 else "uae"
    k = bao_cao(mk)
    print(k.get("van_ban") or json.dumps(k, ensure_ascii=False, indent=1))

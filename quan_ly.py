#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lớp dữ liệu cho 4 màn QUẢN LÝ của giao diện web (giao_dien.py).

Trước file này, giao diện chỉ trả lời được câu "tốn bao nhiêu tiền". Bốn màn dưới đây trả lời
bốn câu còn lại, và đều là câu phải trả lời TRƯỚC khi cho AI gửi tin thật:

  bang_page()    — page nào bật AI được rồi, page nào còn thiếu gì
  chi_tiet_page()— kịch bản page này ra sao, bộ ba giá là bao nhiêu, AI được nói số nào
  so_chan()      — cổng chặn đã chặn những câu gì, vì lý do gì, page nào hay hỏng
  hang_cho()     — ca nào đang chờ sale (treo / chờ xác minh nhà), AI để lại ghi chú gì

Tất cả đều ĐỌC FILE, không gọi API nào — trừ `bang_page(tra_shop=True)` phải hỏi POS một lần
để biết page nào thật sự thuộc shop của thị trường (state/<tt>/page_tokens.json chứa TOÀN BỘ
page của tài khoản, không lọc theo thị trường — xem ai_sale._pages_cua_shop).

  python3 quan_ly.py page <thị trường>     # in bảng sẵn sàng ra terminal
  python3 quan_ly.py chan <thị trường>     # tóm tắt sổ cổng chặn
  python3 quan_ly.py cho  <thị trường>     # hàng chờ sale
"""

import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import chan_gui as CG

# ═════════════════════════════════════════════════════════════════════════════
# Tiện ích đọc file — thiếu file KHÔNG được ném lỗi, giao diện phải mở được kể
# cả khi thị trường mới toanh chưa có gì.
# ═════════════════════════════════════════════════════════════════════════════

def _f(mkey, ten):
    return os.path.join(SCRIPT_DIR, "state", mkey, ten)


def _doc(duong_dan, mac_dinh):
    try:
        with open(duong_dan, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                    # noqa: BLE001
        return mac_dinh


def _doc_dong(duong_dan, toi_da=4000):
    """Đọc sổ .jsonl, bỏ qua dòng hỏng. Chỉ lấy `toi_da` dòng cuối cho nhẹ."""
    try:
        with open(duong_dan, encoding="utf-8") as fh:
            dong = fh.readlines()[-toi_da:]
    except Exception:                                    # noqa: BLE001
        return []
    ra = []
    for d in dong:
        try:
            ra.append(json.loads(d))
        except Exception:                                # noqa: BLE001
            continue
    return ra


def thi_truong():
    """Danh sách thị trường đang bật, theo markets.json."""
    mk = _doc(os.path.join(SCRIPT_DIR, "markets.json"), {})
    return [k for k, v in mk.items()
            if not k.startswith("_") and isinstance(v, dict) and v.get("bat", True)]


# ═════════════════════════════════════════════════════════════════════════════
# MÀN 1 — BẢNG SẴN SÀNG
# ═════════════════════════════════════════════════════════════════════════════
# Câu hỏi: "page nào bật AI được rồi?". Trước đây phải chạy 4 lệnh khác nhau rồi tự ghép
# trong đầu (`ai_sale.py token`, `kich_ban.py thieu`, `auto_len_don.py hoc-san-pham`,
# `chan_gui.py thu`). Đây là chỗ ghép sẵn.
#
# ⚠️ TOKEN CHẾT KHÔNG PHẢI LỖI — chủ shop chốt 2026-09-08: token chết là do page đã cho xuống
# hoặc thôi không chạy nữa. Nên page token chết bị LOẠI HẲN khỏi bảng, không tính vào tỉ lệ,
# không hiện việc phải sửa. Bảng này chỉ nói về những page ĐANG chạy.
#
# BẬC SẴN SÀNG — thang 3 bậc, mỗi bậc là một thứ thiếu là AI làm bậy chứ không phải làm kém:
#   1 · chưa có kịch bản -> AI không có nguồn giá/chính sách, mục 10 cấm bịa
#   2 · chưa có SKU    -> lên đơn ra dạng "THIẾU, để Mới", sale phải sửa tay từng đơn
#   3 · không rút được giá -> cổng chặn không canh được giá sàn
#   4 · đủ

BAC = {
    0: ("token đã chết", "page đã cho xuống — không tính"),
    1: ("chưa có kịch bản", "AI không có nguồn giá/chính sách — xem cột lý do"),
    2: ("chưa có SKU", "Đơn sẽ tạo dạng THIẾU. Chạy: auto_len_don.py hoc-san-pham <tt>"),
    3: ("không rút được giá", "Kịch bản page không có con số giá nào đọc được — mục 4 không canh được. Việc của marketer"),
    4: ("đủ", ""),
}


def bang_page(mkey, tra_shop=False):
    """Một dòng cho mỗi page CÓ TOKEN của thị trường này.

    `tra_shop=True` hỏi POS xem page nào thật sự thuộc shop (một lần gọi mạng, ~1-2s) và đánh
    dấu những page nằm nhầm thư mục. Mặc định tắt để mở màn hình cho nhanh.
    """
    tok = _doc(_f(mkey, "page_tokens.json"), {})
    kb = _doc(_f(mkey, "kich_ban.json"), {})
    sp = _doc(_f(mkey, "page_products.json"), {})
    kb_hong = _doc(_f(mkey, "kich_ban_hong.json"), {})   # vì sao page chưa có kịch bản

    thuoc = None
    if tra_shop:
        try:
            import ai_sale as A
            thuoc = A._pages_cua_shop(mkey)
        except Exception:                                # noqa: BLE001
            thuoc = None

    import ai_sale as A
    ra, ngung = [], 0
    for pid, st in tok.items():
        if not st.get("token"):
            continue                                     # page không token = không thuộc tt này
        k = kb.get(pid) or {}
        mau = k.get("mau") or []
        gia = A.bo_gia(k, mkey) if mau else {"gia_chao": [], "gia_thuc": None, "gia_san": None,
                                       "gia_ban": [], "san_theo_gia": {}, "san_thap_nhat": None,
                                       "gia_neo": []}
        co_sku = bool((sp.get(pid) or {}).get("variation_id")
                      or (sp.get(pid) or {}).get("variations")
                      or (sp.get(pid) or {}).get("sku"))
        # ⚠️ Dấu token hỏng nằm NGAY TRONG page_tokens.json ở khoá `token_hong`
        # (quet_hoi_thoai.danh_dau_token ghi vào đó), KHÔNG phải file token_hong.json riêng.
        # Đọc nhầm chỗ thì bảng này báo "0 page token hỏng" trong khi thực tế 20/27 page Mỹ
        # đang hỏng — tức bảng sẵn sàng nói dối đúng cái nó sinh ra để canh.
        th = st.get("token_hong") or {}
        if th:
            ngung += 1
            continue                                     # page đã cho xuống — bỏ hẳn
        if not mau:
            bac = 1
        elif not co_sku:
            bac = 2
        elif not gia.get("san_thap_nhat"):
            bac = 3
        else:
            bac = 4

        ra.append({
            "pid": pid,
            "ten": st.get("name") or pid,
            "bac": bac,
            "thieu": BAC[bac][0],
            "cach_sua": BAC[bac][1].replace("<tt>", mkey),
            "so_mau": len(mau),
            "so_anh": sum(m.get("so_anh") or 0 for m in mau),
            "gia_chao": gia["gia_chao"],
            "gia_neo": gia.get("gia_neo") or [],
            "gia_thuc": gia["gia_thuc"],
            "gia_san": gia.get("san_thap_nhat") or gia["gia_san"],
            "gia_ban": gia.get("gia_ban") or [],
            "san_theo_gia": gia.get("san_theo_gia") or {},
            "co_sku": co_sku,
            "phien_ban": k.get("phien_ban"),
            "tai_luc": k.get("tai_luc"),
            "ngoai_shop": (thuoc is not None and pid not in thuoc),
        })
    ra.sort(key=lambda x: (x["bac"], -x["so_mau"], x["ten"].lower()))
    kiem_luc = max([(st.get("token_hong") or {}).get("luc") or 0
                    for st in tok.values()] or [0])
    return {
        "mkey": mkey, "tong": len(ra),
        "ngung": ngung,          # page đã cho xuống — chỉ để nói ra, không phải việc phải làm
        # Chỉ biết page nào hỏng ở lần `ai_sale.py token <tt>` gần nhất.
        "token_kiem_luc": kiem_luc or None,
        "theo_bac": {str(b): sum(1 for x in ra if x["bac"] == b) for b in range(5)},
        "ngoai_shop": sum(1 for x in ra if x["ngoai_shop"]),
        "da_tra_shop": thuoc is not None,
        "page": ra,
    }


# ═════════════════════════════════════════════════════════════════════════════
# MÀN 2 — KỊCH BẢN + GIÁ CỦA MỘT PAGE
# ═════════════════════════════════════════════════════════════════════════════

def chi_tiet_page(mkey, pid):
    """Toàn bộ kịch bản của 1 page + bộ ba giá + TẬP SỐ AI ĐƯỢC PHÉP NÓI.

    Tập số cuối cùng là thứ đáng nhìn nhất: đó chính xác là danh sách con số mà cổng chặn
    cho đi qua. Con số nào AI nói ra ngoài danh sách này sẽ bị chặn với mã `bia_tien`.
    """
    import ai_sale as A
    kb = _doc(_f(mkey, "kich_ban.json"), {}).get(str(pid))
    if not kb:
        return None
    gia = A.bo_gia(kb, mkey)
    ten_cd = {c.get("id"): c.get("ten") for c in kb.get("chu_de") or []}
    mau = [{
        "tu_khoa": m.get("tu_khoa") or "",
        "chu_de": ten_cd.get(m.get("chu_de_id")) or "",
        "tin": m.get("tin") or [],
        "so_anh": m.get("so_anh") or 0,
        "anh": (m.get("anh") or [])[:6],
        "tien": sorted(set(CG.tien_trong(" ".join(m.get("tin") or [])))),
    } for m in kb.get("mau") or []]
    return {
        "pid": str(pid), "ten": kb.get("ten_page"), "mkey": mkey,
        "phien_ban": kb.get("phien_ban"), "tai_luc": kb.get("tai_luc"),
        "tien_te": CG.TIEN_TE.get(mkey, ""),
        "gia": gia,
        "duoc_noi": sorted(CG.so_duoc_phep(kb, gia)),
        "mau": mau,
    }


# ═════════════════════════════════════════════════════════════════════════════
# MÀN 3 — SỔ CỔNG CHẶN
# ═════════════════════════════════════════════════════════════════════════════

# Mã lỗi nào là "AI suýt làm hỏng chuyện thật" — đây là danh sách cần nhìn hằng ngày.
GIAI_THICH = {
    "lot_tieng_viet": "AI trả lời khách bằng tiếng Việt",
    "bia_tien": "AI nói một con số tiền không có trong kịch bản page",
    "duoi_gia_san": "AI chào giá thấp hơn giá sàn (mục 4)",
    "tin_rong": "AI gửi tin không có chữ nào (khách chỉ nhận ảnh trơ)",
    "nhan_lap": "AI nhắn lại gần y hệt câu vừa gửi",
    "khong_duoc_nhan": "AI chọn im/treo/xác minh nhà nhưng vẫn soạn tin cho khách",
    "bia_khan_hiem": "AI hứa khan hiếm/hạn chót mà kịch bản không hề nói vậy",
    "bia_ma_don": "AI đọc mã đơn cho khách — mã thật do POS sinh sau",
    "lo_noi_bo": "AI để lộ chuyện bot/kịch bản, hoặc nhắc việc sale vừa tra địa chỉ",
    "doa_khach": "Câu mang tính doạ khách",
    "ky_tu_an": "Có ký tự Unicode vô hình (dấu hiệu né bộ lọc trùng của Meta)",
    "khong_chot": "Không kết bằng câu hỏi hướng tới mua hàng (mục 5b#2)",
    "dan_checklist": "Dán lại danh sách thông tin cần xin (mục 1)",
    "ket_thu_dong": "Kết lượt bằng câu chờ đợi thụ động (mục 5b#2)",
    "qua_dai": "Tin dài hơn mức mục 5b yêu cầu",
    "hoi_lap": "Lặp ý câu trước — mục 4 đòi mỗi lần một góc khác",
}


def so_chan(mkey, chi_that=False, so=300):
    """Tóm tắt + danh sách chi tiết các phán quyết của cổng chặn.

    `chi_that=True` chỉ đếm vòng chạy thật. Mặc định đếm cả vòng thử — vòng thử chính là chỗ
    rẻ nhất để thấy AI đang định nói bậy, bỏ nó đi là mất hết giá trị cảnh báo sớm.
    """
    ds = _doc_dong(_f(mkey, "so_viec.jsonl"))
    if chi_that:
        ds = [x for x in ds if x.get("that")]
    co_loi = [x for x in ds if x.get("ma")]

    theo_ma, theo_page = {}, {}
    for x in co_loi:
        for m in x.get("ma") or []:
            o = theo_ma.setdefault(m, {"ma": m, "so": 0, "chan": 0,
                                       "y_nghia": GIAI_THICH.get(m, "")})
            o["so"] += 1
            if x.get("chan") == "chan":
                o["chan"] += 1
        if x.get("chan") == "chan":
            t = theo_page.setdefault(x.get("pid"), {"pid": x.get("pid"),
                                                    "ten": x.get("page"), "so": 0})
            t["so"] += 1
    return {
        "mkey": mkey,
        "tong_luot": len(ds),
        "sach": sum(1 for x in ds if x.get("chan") == "qua"),
        "nhac": sum(1 for x in ds if x.get("chan") == "nhac"),
        "viet_lai": sum(1 for x in ds if x.get("chan") == "viet_lai"),
        "chan": sum(1 for x in ds if x.get("chan") == "chan"),
        "theo_ma": sorted(theo_ma.values(), key=lambda x: (-x["chan"], -x["so"])),
        "theo_page": sorted(theo_page.values(), key=lambda x: -x["so"])[:12],
        "gan_day": list(reversed(co_loi[-so:])),
    }


# ═════════════════════════════════════════════════════════════════════════════
# MÀN 4 — HÀNG CHỜ SALE
# ═════════════════════════════════════════════════════════════════════════════
# Ca treo và ca chờ xác minh nhà hiện chỉ nằm trong ghi chú Pancake — sale phải tự lần ra.
# Ở đây gom về một chỗ, GIỮ NGUYÊN ghi chú AI đã viết, và tính xem đã chờ bao lâu.
#
# Ca chờ xác minh nhà (mục 9b chốt 1 thì 1) là ca đáng lo nhất: AI cố ý KHÔNG nhắn gì và
# đứng đợi sale. Sale không làm thì hội thoại đứng im vô thời hạn, không ai báo.

def hang_cho(mkey, so=200):
    # Ghép thêm HỒ SƠ KHÁCH để mỗi ca chờ nói được "khách này còn thiếu gì" — trước đây sale
    # phải tự đọc ghi chú rồi tự suy ra.
    hs_theo_conv = {}
    try:
        import ho_so as HSO
        if os.path.exists(HSO.duong_db(mkey)):
            cn = HSO.mo(mkey)
            for r in cn.execute("SELECT * FROM ho_so").fetchall():
                d = dict(r)
                hs_theo_conv[str(d["conv_id"])] = {
                    "thieu": [HSO.TEN_TRUONG.get(k, k) for k in
                              HSO.thieu(HSO.chi_truong(d), mkey)],
                    "da_co": {HSO.TEN_TRUONG.get(k, k): d[k] for k in HSO.TRUONG if d.get(k)},
                    "buoc": d.get("buoc"),
                }
            cn.close()
    except Exception:                                    # noqa: BLE001 — thiếu hồ sơ không chặn màn
        hs_theo_conv = {}
    ds = _doc_dong(_f(mkey, "so_viec.jsonl"))
    moi_nhat = {}
    for x in ds:
        moi_nhat[x.get("conv")] = x                      # lần AI đụng gần nhất của hội thoại đó
    cho = [x for x in moi_nhat.values()
           if x.get("hd") in ("treo", "xac_minh_nha", "tra_loi_treo")
           or x.get("chan") == "chan"]
    gio = time.time()
    for x in cho:
        x["cho_gio"] = round((gio - (x.get("luc") or gio)) / 3600, 1)
        x["loai"] = ("Chờ sale xác minh nhà" if x.get("hd") == "xac_minh_nha"
                     else "AI rep 1 câu — sale tiếp" if x.get("hd") == "tra_loi_treo"
                     else "Treo cho sale" if x.get("hd") == "treo"
                     else "Cổng chặn — khách CHƯA được trả lời")
        h = hs_theo_conv.get(str(x.get("conv"))) or {}
        x["thieu"] = h.get("thieu") or []
        x["da_co"] = h.get("da_co") or {}
        x["buoc"] = h.get("buoc")
    cho.sort(key=lambda x: -(x.get("luc") or 0))
    return {
        "mkey": mkey,
        "tong": len(cho),
        "xac_nha": sum(1 for x in cho if x.get("hd") == "xac_minh_nha"),
        "treo": sum(1 for x in cho if x.get("hd") == "treo"),
        "rep_treo": sum(1 for x in cho if x.get("hd") == "tra_loi_treo"),
        "bi_chan": sum(1 for x in cho if x.get("chan") == "chan"
                       and x.get("hd") not in ("treo", "xac_minh_nha", "tra_loi_treo")),
        "qua_24h": sum(1 for x in cho if x["cho_gio"] > 24),
        "viec": cho[:so],
    }


# ═════════════════════════════════════════════════════════════════════════════
# Bản in ra terminal — để kiểm chứng nhanh mà không cần mở trình duyệt
# ═════════════════════════════════════════════════════════════════════════════

def _in_page(mkey):
    d = bang_page(mkey)
    print(f"\n═══ {mkey} — {d['tong']} page ĐANG CHẠY"
          + (f" ({d['ngung']} page đã cho xuống, không tính)" if d.get("ngung") else "")
          + " ═══\n")
    for b in range(5):
        n = d["theo_bac"][str(b)]
        if n:
            print(f"  bậc {b} · {BAC[b][0]:20s} {n:3d} page")
    print()
    for p in d["page"][:40]:
        g = f"{p['gia_ban']}/sàn {p['gia_san']}" if p["gia_san"] else "—"
        print(f"  {p['bac']} {p['ten'][:40]:42s} {p['so_mau']:3d} mẫu  {g:18s} {p['thieu']}")
    if d["tong"] > 40:
        print(f"  … còn {d['tong']-40} page")


def _in_chan(mkey):
    d = so_chan(mkey)
    if not d["tong_luot"]:
        return print(f"\nSổ việc của {mkey} còn trống — chạy `ai_sale.py chay {mkey}` một vòng.")
    print(f"\n═══ Sổ cổng chặn {mkey} — {d['tong_luot']} lượt ═══")
    print(f"  sạch {d['sach']} · nhắc {d['nhac']} · viết lại {d['viet_lai']} · CHẶN {d['chan']}\n")
    for m in d["theo_ma"]:
        print(f"  {m['ma']:18s} {m['so']:4d} lần (chặn {m['chan']:3d})  {m['y_nghia']}")


def _in_cho(mkey):
    d = hang_cho(mkey)
    print(f"\n═══ Hàng chờ sale {mkey} — {d['tong']} việc ═══")
    print(f"  xác minh nhà {d['xac_nha']} · treo {d['treo']} · bị chặn {d['bi_chan']}"
          f" · quá 24h {d['qua_24h']}\n")
    for v in d["viec"][:25]:
        print(f"  {v['cho_gio']:6.1f}h  {(v.get('khach') or '?')[:20]:22s}"
              f" {v['loai']:34s} {(v.get('gc') or '')[:60]}")


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "page":
        _in_page(a[1])
    elif len(a) >= 2 and a[0] == "chan":
        _in_chan(a[1])
    elif len(a) >= 2 and a[0] == "cho":
        _in_cho(a[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

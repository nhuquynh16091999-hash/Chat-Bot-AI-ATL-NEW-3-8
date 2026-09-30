#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PAGE MỚI THUỘC THỊ TRƯỜNG NÀO — đoán bằng ĐƠN VỊ TIỀN TỆ trong kịch bản của chính page đó.

Chủ shop chốt 2026-09-08: *"nếu đơn vị tiền tệ là nước nào thì là của thị trường đó."*
Đây là dấu hiệu tốt hơn hẳn cách cũ, vì:
  · Kịch bản đọc được bằng USER TOKEN — page mới toanh, chưa có page token, vẫn đọc được.
  · Giá là thứ marketer BẮT BUỘC phải viết đúng, không viết sai được như tên page.
    ("Saudi Gold Jewelry - TW" nằm ở thư mục Romania — tên page không đáng tin.)

HAI TẦNG DẤU HIỆU, và chỗ nào không chắc thì KHÔNG tự quyết:
  ① Mã tiền tệ RIÊNG   AED·SAR·KWD·QAR·OMR·BHD·TWD·JPY·USD·RON·BGN  -> ra ngay một thị trường
  ② Mã DÙNG CHUNG      EUR (Tây Ban Nha + Bulgaria) · ريال (Saudi/Qatar/Oman) ·
                       دينار (Kuwait/Bahrain)                      -> phải phân giải bằng tên page
Không phân giải được -> BÁO RA CHO NGƯỜI QUYẾT, tuyệt đối không đoán bừa. Gán nhầm thị trường
là bán giá nước này cho khách nước kia và đơn rơi vào sai shop — đúng thứ mục 3 của luật cấm.

⚖️ AI THẮNG KHI HAI NGUỒN NÓI KHÁC NHAU — chủ shop chốt 2026-09-08:
   *"vẫn cứ theo kịch bản báo giá nước nào là nước đó."*
Vẫn hỏi POS xem page có nằm trong shop của thị trường vừa đoán không, nhưng POS nói khác thì
chỉ là CẢNH BÁO để người soi lại, KHÔNG chặn. Lý do: giá là thứ khách thật sự nhìn thấy và trả
tiền theo; xếp shop chỉ là chuyện sổ sách bên trong, sai thì sửa được, còn báo sai tiền cho
khách thì mất đơn và mất page.

  python3 phan_thi_truong.py soi [--so 40]        # page CHƯA kết nạp — chỉ xem
  python3 phan_thi_truong.py soat                 # page ĐÃ kết nạp — tiền tệ có khớp thư mục không
  python3 phan_thi_truong.py ket-nap --that       # cấp token + lưu kịch bản vào đúng thư mục
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import quet_hoi_thoai as qht
import kich_ban as KB

# ── Mã tiền tệ RIÊNG: thấy là ra ngay thị trường ────────────────────────────
RIENG = {
    "uae":      r"\bAED\b|د\.إ|درهم|dirhams?",
    "saudi":    r"\bSAR\b|ر\.س",
    "kuwait":   r"\bKWD\b|د\.ك",
    "qatar":    r"\bQAR\b|ر\.ق",
    "oman":     r"\bOMR\b|ر\.ع",
    "bahrain":  r"\bBHD\b|د\.ب",
    "taiwan":   r"NT\$|\bTWD\b|新台幣",
    "japan":    r"\bJPY\b|円|¥",
    # ⚠️ CHỈ "USD" mới là dấu hiệu RIÊNG của Mỹ. Dấu "$" TRẦN thì KHÔNG — nó dùng chung cho
    # đô Mỹ, đô Úc, và cả những page Đài Loan viết tắt NT$ thành $. Đo thật 2026-09-08 trên
    # các page chưa kết nạp: "Prosperity Aura - TW" ghi "ONLY $199", "Gold Avenue Taiwan" ghi
    # "149$", "Aura Manila AU" ghi "$299" — xếp cả bốn vào Mỹ là bán giá Mỹ cho khách Đài Loan
    # và khách Úc, đúng thứ luật mục 3 cấm. Nên "$" trần rơi xuống tầng DÙNG CHUNG bên dưới.
    "usa":      r"\bUSD\b",
    "romania":  r"\bRON\b|\blei\b",
    "bulgaria": r"\bBGN\b|лв",
}
# ── Mã DÙNG CHUNG: một mã, nhiều nước -> phải phân giải thêm ────────────────
CHUNG = {
    r"(?<!NT)\$|\bdollars?\b": ("usa", "australia", "taiwan"),
    r"\bEUR\b|€|euros?":        ("spain", "bulgaria"),
    r"ريال|riyals?":             ("saudi", "qatar", "oman"),
    r"دينار|dinars?":            ("kuwait", "bahrain"),
}
# ── Tên page: CHỈ dùng để gỡ hoà, không bao giờ dùng một mình ───────────────
TEN_NUOC = {
    "uae": r"\buae\b|dubai|abu\s*dhabi|sharjah|ajman|emirat|الامارات|الإمارات",
    "saudi": r"\bksa\b|saudi|السعودية|riyadh|jeddah",
    "kuwait": r"kuwait|الكويت",
    "qatar": r"qatar|قطر|doha",
    "oman": r"\boman\b|عمان|muscat",
    "bahrain": r"bahrain|البحرين|manama",
    "taiwan": r"taiwan|\btw\b|台灣|台湾",
    "japan": r"japan|\bjp\b|日本",
    "usa": r"\busa?\b|u\.s|united\s*states|america",
    "australia": r"\bau\b|australia|\baus\b|sydney|melbourne",
    "spain": r"spain|españa|espana|\bes\b",
    "romania": r"romania|românia|\bro\b",
    "bulgaria": r"bulgaria|българия|\bbg\b",
}


def _thi_truong_bat():
    mk = json.load(open(os.path.join(SCRIPT_DIR, "markets.json"), encoding="utf-8"))
    return [k for k, v in mk.items()
            if not k.startswith("_") and isinstance(v, dict) and v.get("bat", True)]


def pages_tho(user_token):
    """TOÀN BỘ page user token nhìn thấy — KHÔNG lọc theo shop.

    Cố ý không dùng `qht.get_pages()`: hàm đó lọc theo shop của thị trường đang cấu hình,
    mà ở đây mình chưa biết page thuộc thị trường nào — đó chính là câu đang đi tìm.
    """
    u = "https://pages.fm/api/v1/pages?" + urllib.parse.urlencode({"access_token": user_token})
    with urllib.request.urlopen(u, timeout=60) as r:
        res = json.loads(r.read().decode() or "{}")
    return res.get("pages") or (res.get("categorized") or {}).get("activated") or []


def da_ket_nap():
    """{page_id: thị trường} — page nào đã có token ở thư mục nào."""
    ra = {}
    for tt in _thi_truong_bat():
        f = os.path.join(SCRIPT_DIR, "state", tt, "page_tokens.json")
        if not os.path.exists(f):
            continue
        for p, st in json.load(open(f, encoding="utf-8")).items():
            if st.get("token"):
                ra[str(p)] = tt
    return ra


def doan(kb, ten_page=""):
    """Đoán thị trường từ kịch bản. Trả (thị trường | None, lý do, bảng điểm).

    Đếm SỐ LẦN xuất hiện chứ không chỉ có/không: kịch bản hay nhắc tiền nước khác một hai lần
    (mẫu cảnh báo lừa đảo của page Saudi nhắc "pesos"), nhưng tiền của chính thị trường thì
    lặp trong mọi mẫu báo giá.
    """
    noi = "\n".join(t for m in (kb.get("mau") or []) for t in (m.get("tin") or []))
    if not noi.strip():
        return None, "kịch bản rỗng", {}
    diem = {}
    for tt, mau in RIENG.items():
        n = len(re.findall(mau, noi, re.I | re.U))
        if n:
            diem[tt] = n
    if diem:
        cao = max(diem.values())
        dan = [t for t, n in diem.items() if n == cao]
        if len(dan) == 1:
            return dan[0], f"mã tiền riêng ×{cao}", diem
        # Hoà giữa nhiều mã riêng -> gỡ bằng tên page
        ten = [t for t in dan if re.search(TEN_NUOC.get(t, r"$^"), ten_page, re.I | re.U)]
        if len(ten) == 1:
            return ten[0], f"hoà {dan}, gỡ bằng tên page", diem
        return None, f"hoà giữa {dan} — tên page không gỡ được", diem

    for mau, ds in CHUNG.items():
        if re.search(mau, noi, re.I | re.U):
            ten = [t for t in ds if re.search(TEN_NUOC.get(t, r"$^"), ten_page, re.I | re.U)]
            if len(ten) == 1:
                return ten[0], f"mã dùng chung {ds}, gỡ bằng tên page", {t: 0 for t in ds}
            return None, f"mã dùng chung {ds} — tên page không gỡ được", {t: 0 for t in ds}
    return None, "không thấy ký hiệu tiền tệ nào", {}


def _thuoc_shop(tt, pid):
    """Đối chiếu độc lập: POS có xếp page này vào shop của thị trường đó không?"""
    try:
        import ai_sale as A
        ds = A._pages_cua_shop(tt)
        return None if ds is None else (str(pid) in ds)
    except Exception:                                    # noqa: BLE001
        return None


_SHOP_DEM = {}


def thuoc_shop(tt, pid):
    if tt not in _SHOP_DEM:
        try:
            import ai_sale as A
            _SHOP_DEM[tt] = A._pages_cua_shop(tt)
        except Exception:                                # noqa: BLE001
            _SHOP_DEM[tt] = None
    ds = _SHOP_DEM[tt]
    return None if ds is None else (str(pid) in ds)


def quet(so=None, chi_moi=True):
    """Soi các page CHƯA kết nạp, đoán thị trường. Không đụng gì vào state."""
    tok = qht.load_env().get("PANCAKE_USER_TOKEN", "")
    if not tok:
        sys.exit("❌ Thiếu PANCAKE_USER_TOKEN trong .env")
    da = da_ket_nap()
    ds = pages_tho(tok)
    if chi_moi:
        ds = [p for p in ds if str(p.get("id")) not in da]
    if so:
        ds = ds[:so]
    ra = []
    for i, p in enumerate(ds, 1):
        pid, ten = str(p.get("id")), (p.get("name") or "?")
        kb, err = KB.tai_1_page(pid, tok)
        if kb:
            # ⚠️ `tai_1_page` trả kịch bản THÔ (mỗi mẫu có 'messages'), còn `doan` đọc theo
            # khuôn đã rút gọn (khoá 'tin'). Không chuyển thì mọi page đều ra "kịch bản rỗng".
            kb = {**kb, "mau": [KB._gon(m) for m in (kb.get("mau") or [])]}
        if err:
            ra.append({"pid": pid, "ten": ten, "tt": None, "vi_sao": f"không đọc được kịch bản: {err}",
                       "diem": {}, "khop_shop": None, "so_mau": 0})
        else:
            tt, vi_sao, diem = doan(kb, ten)
            if tt and tt not in _thi_truong_bat():
                # Đoán ra một nước CHƯA khai trong markets.json (hay gặp: Úc). Không kết nạp
                # được, nhưng phải nói ra — im lặng bỏ qua là page đó biến mất khỏi mọi báo cáo.
                vi_sao = f"thị trường {tt.upper()} chưa khai trong markets.json ({vi_sao})"
                tt = None
            ra.append({"pid": pid, "ten": ten, "tt": tt, "vi_sao": vi_sao, "diem": diem,
                       "khop_shop": thuoc_shop(tt, pid) if tt else None,
                       "so_mau": len(kb.get("mau") or [])})
        if i % 20 == 0:
            print(f"     …đã soi {i}/{len(ds)}", flush=True)
        time.sleep(0.12)
    return ra


def cmd_soi(so=None):
    ra = quet(so)
    # Tiền tệ quyết định. POS lệch chỉ ghi chú lại, không loại ra.
    chac = [x for x in ra if x["tt"]]
    lech = [x for x in ra if x["tt"] and x["khop_shop"] is False]
    bo = [x for x in ra if not x["tt"]]
    print(f"\n═══ Soi {len(ra)} page CHƯA kết nạp ═══\n")
    theo = {}
    for x in chac:
        theo.setdefault(x["tt"], []).append(x)
    for tt, ds in sorted(theo.items(), key=lambda kv: -len(kv[1])):
        print(f"  ▸ {tt.upper()} — {len(ds)} page")
        for x in ds[:8]:
            print(f"      {x['ten'][:44]:46s} {x['so_mau']:3d} mẫu · {x['vi_sao']}")
        if len(ds) > 8:
            print(f"      … còn {len(ds)-8} page")
        print()
    if lech:
        print(f"  ⚠️  {len(lech)} page POS xếp shop KHÁC — vẫn kết nạp theo TIỀN TỆ, "
              f"nhưng nên soi lại việc xếp shop:")
        for x in lech:
            print(f"      {x['ten'][:44]:46s} tiền tệ→{x['tt']} · POS bảo không thuộc shop đó")
        print()
    if bo:
        print(f"  ⚠️  {len(bo)} page KHÔNG quyết được:")
        for x in bo[:12]:
            print(f"      {x['ten'][:44]:46s} {x['vi_sao'][:60]}")
        if len(bo) > 12:
            print(f"      … còn {len(bo)-12} page")
    print(f"\n  → Kết nạp {len(chac)} page chắc chắn: python3 phan_thi_truong.py ket-nap --that")


def soat():
    """Page ĐÃ kết nạp: tiền tệ trong kịch bản có khớp thư mục đang nằm không?

    Đây là phép soi ngược của `soi`. Thước đo là CÓ TOKEN trong thư mục nào — không phải
    "kịch bản nằm ở file nào": `kich_ban.py tai <tt>` quét cả page không thuộc thị trường đó
    nên file kịch bản có nhiều bản chụp thừa, không nói lên page thuộc về đâu.
    """
    lech, ok, bo = [], 0, 0
    for tt in _thi_truong_bat():
        f = os.path.join(SCRIPT_DIR, "state", tt, "kich_ban.json")
        ft = os.path.join(SCRIPT_DIR, "state", tt, "page_tokens.json")
        if not (os.path.exists(f) and os.path.exists(ft)):
            continue
        tok = json.load(open(ft, encoding="utf-8"))
        for pid, v in json.load(open(f, encoding="utf-8")).items():
            if not v.get("mau") or not (tok.get(pid) or {}).get("token"):
                continue
            d, vs, diem = doan(v, v.get("ten_page") or "")
            if d == tt:
                ok += 1
            elif d is None:
                bo += 1
            else:
                lech.append((tt, d, v.get("ten_page") or pid, pid, vs, diem))
    return ok, bo, lech


def cmd_soat():
    ok, bo, lech = soat()
    tong = ok + bo + len(lech)
    print(f"\n═══ Soát {tong} page ĐANG chạy (có token) ═══\n")
    print(f"  ✅ tiền tệ khớp thư mục : {ok}")
    print(f"  ⚠️  không đọc được tiền  : {bo}")
    print(f"  🚨 LỆCH                 : {len(lech)}\n")
    for tt, d, ten, pid, vs, diem in lech:
        print(f"  {ten[:42]:44s} đang ở {tt:9s} → theo kịch bản phải là {d.upper()}")
        print(f"     {pid} · {vs} · {diem}")
    if lech:
        print("\n  → Luật chủ shop: kịch bản báo giá nước nào thì page thuộc nước đó.")
        print("     Chuyển thư mục là đổi cả shop POS đơn sẽ rơi vào — phải người quyết.")


def cmd_ket_nap(that=False, so=None):
    ra = quet(so)
    chac = [x for x in ra if x["tt"]]
    if not chac:
        return print("Không có page nào đủ chắc để kết nạp.")
    print(f"\n{'🚨 KẾT NẠP THẬT' if that else '🧪 CHẠY THỬ (không ghi gì)'} — {len(chac)} page\n")
    tok = qht.load_env().get("PANCAKE_USER_TOKEN", "")
    dem = {}
    for x in chac:
        tt = x["tt"]
        print(f"  {tt:9s} {x['ten'][:44]:46s} {x['vi_sao']}")
        if not that:
            continue
        qht.set_state_dir(os.path.join(SCRIPT_DIR, "state", tt))
        t, e = qht.cap_lai_token(x["pid"], x["ten"])
        if not t:
            print(f"            ✖ không cấp được token: {e}")
            continue
        # Lưu luôn kịch bản để vòng chạy dùng được ngay, khỏi phải chạy `kich_ban.py tai`.
        kb, err = KB.tai_1_page(x["pid"], tok)
        if kb:
            f = os.path.join(SCRIPT_DIR, "state", tt, "kich_ban.json")
            cu = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
            cu[x["pid"]] = {"ten_page": x["ten"], "phien_ban": kb["phien_ban"],
                            "chu_de": [{"id": c.get("id"), "ten": c.get("name")}
                                       for c in kb["chu_de"]],
                            "mau": [KB._gon(m) for m in (kb.get("mau") or [])],
                            "tai_luc": int(time.time())}
            json.dump(cu, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        dem[tt] = dem.get(tt, 0) + 1
        time.sleep(0.15)
    if that:
        print("\n  ✅ " + " · ".join(f"{k}: {v} page" for k, v in dem.items()))
        print("  → Chốt SKU cho các page vừa kết nạp: "
              + " ; ".join(f"python3 ket_nap_page.py ket-nap {k}" for k in dem))
    else:
        print("\n  (chạy thử — thêm --that để kết nạp thật)")


def main():
    a = sys.argv[1:]
    so = int(a[a.index("--so") + 1]) if "--so" in a else None
    if a and a[0] == "soi":
        cmd_soi(so)
    elif a and a[0] == "soat":
        cmd_soat()
    elif a and a[0] in ("ket-nap", "ket_nap"):
        cmd_ket_nap("--that" in a, so)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

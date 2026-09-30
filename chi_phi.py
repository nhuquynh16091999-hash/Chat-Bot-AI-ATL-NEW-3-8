#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sổ chi phí + thống kê AI Sale — để chủ shop kiểm soát tiền TRƯỚC khi nạp thêm.

Vì sao có file này: `ai_sale.py` vốn chỉ đếm token trong bộ nhớ rồi in ra cuối vòng chạy,
chạy xong là mất. Không ai biết tổng đã chi bao nhiêu, ngày nào tốn, page nào tốn.
Nay mỗi lượt quét ghi 1 dòng vào sổ; báo cáo đọc lại sổ đó.

Hai sổ:
  state/<thị trường>/so_chi_phi.jsonl   — mỗi dòng 1 hội thoại đã quét (token, tiền, kết quả)
  state/nap_tien.json                   — tiền đã nạp vào nhà cung cấp (tự khai bằng tay)

Lệnh:
  python3 chi_phi.py bao_cao [thị trường] [--ngay 30]   # thị trường trống = gộp tất cả
  python3 chi_phi.py nap <số tiền USD> [--nha kimi] [--ghi "chuyển khoản lần 1"]
  python3 chi_phi.py nap --xem
(gọi qua ai_sale.py bao_cao / ai_sale.py nap cũng ra đúng cái này)
"""

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(SCRIPT_DIR, "state")
F_NAP = os.path.join(STATE, "nap_tien.json")


# ───────────────────────── Ghi sổ ─────────────────────────

def _f_so(mkey):
    return os.path.join(STATE, mkey, "so_chi_phi.jsonl")


def ghi(mkey, rec):
    """Ghi 1 dòng vào sổ chi phí. Không bao giờ được làm chết vòng chạy."""
    try:
        rec.setdefault("luc", time.strftime("%Y-%m-%dT%H:%M:%S"))
        rec.setdefault("tt", mkey)
        os.makedirs(os.path.join(STATE, mkey), exist_ok=True)
        with open(_f_so(mkey), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:                       # noqa: BLE001 — sổ hỏng không được giết vòng
        print(f"   ⚠️  không ghi được sổ chi phí: {e}")


def cac_thi_truong():
    if not os.path.isdir(STATE):
        return []
    return sorted(d for d in os.listdir(STATE)
                  if os.path.exists(_f_so(d)))


def doc(mkey=None, tu_ngay=None):
    """Đọc sổ. mkey=None -> gộp mọi thị trường. tu_ngay dạng 'YYYY-MM-DD'."""
    for tt in ([mkey] if mkey else cac_thi_truong()):
        f = _f_so(tt)
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            for dong in fh:
                dong = dong.strip()
                if not dong:
                    continue
                try:
                    r = json.loads(dong)
                except Exception:
                    continue
                if tu_ngay and r.get("luc", "")[:10] < tu_ngay:
                    continue
                r.setdefault("tt", tt)
                yield r


def da_chi_hom_nay(nha=None):
    """Tổng USD đã chi hôm nay, mọi thị trường (ngân sách tính trên API key, không theo nước)."""
    hom_nay = time.strftime("%Y-%m-%d")
    return sum(r.get("tien") or 0 for r in doc(tu_ngay=hom_nay)
               if not nha or r.get("nha") == nha)


def da_chi_tong(nha=None):
    return sum(r.get("tien") or 0 for r in doc()
               if not nha or r.get("nha") == nha)


# ──────────────── Số dư THẬT bên nhà cung cấp (chuẩn để chặn) ────────────────
# Vì sao có khối này (chủ shop hỏi 17/09/2026: "sao không cho sổ và bảng khớp nhau"):
# sổ .jsonl phía trên chỉ cộng những lượt do CHÍNH bản /opt/pancake-tool ghi ra, nên nó là
# ƯỚC LƯỢNG chứ không phải tiền thật. Nó thiếu:
#   • các bản thử trong /root (thu_moi, thu_nhan_dinh, thu_niu5…) — gọi CÙNG API key nhưng
#     ghi vào state/ của chính nó, /opt không bao giờ thấy;
#   • $5 voucher Kimi tặng — không nằm trong sổ nạp nap_tien.json;
#   • lượt nào ghi sổ hỏng là mất luôn (ghi() cố tình nuốt lỗi để không giết vòng chạy).
# Đo 17/09: sổ nói đã chi $25.24 / trần $30 → tưởng còn $4.76, trong khi Kimi thật còn $0.44.
# Phanh chạy theo sổ nên không chặn kịp, 8 service chết bằng 429 giữa giờ bán (y sáng 15/09).
# Kimi trả đúng con số trên bảng qua API → TỪ NAY LẤY CÁI NÀY LÀM CHUẨN. Sổ .jsonl vẫn giữ,
# nhưng chỉ còn để bóc tách "tiêu vào page nào / cửa nào", không dùng để quyết định dừng.
import urllib.request                                  # noqa: E402

API_SO_DU = {"kimi": "https://api.moonshot.ai/v1/users/me/balance",
             # DeepSeek có endpoint riêng và KHUÔN TRẢ LỜI KHÁC HẲN — xem _doc_so_du().
             "deepseek": "https://api.deepseek.com/user/balance"}
KEY_SO_DU = {"kimi": "KIMI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}
F_SO_DU = os.path.join(STATE, "so_du_that.json")
_SO_DU = {"luc": 0.0, "kq": None, "moc_luc": None, "moc_chi": 0.0}


def _env_file():
    """Đọc .env cạnh file này. chi_phi KHÔNG được import ai_sale (ai_sale đã import chi_phi)."""
    e = {}
    try:
        with open(os.path.join(SCRIPT_DIR, ".env"), encoding="utf-8") as f:
            for d in f:
                d = d.strip()
                if d and not d.startswith("#") and "=" in d:
                    k, v = d.split("=", 1)
                    e[k.strip()] = v.strip()
    except Exception:                                   # noqa: BLE001
        pass
    return e


def _doc_so_du(nha, dd, e=None):
    """Đọc khuôn trả lời số dư của TỪNG nhà — mỗi nhà một kiểu, đừng gộp.

    kimi     : {"data":{"available_balance","cash_balance","voucher_balance"}} — luôn USD.
    deepseek : {"is_available":bool,"balance_infos":[{"currency","total_balance",
               "granted_balance","topped_up_balance"}]} — currency CÓ THỂ LÀ CNY.

    ⚠️ Tài khoản DeepSeek tính bằng CNY thì con số to gấp ~7 lần USD; đem so thẳng với sàn
    dừng $0.50 là phanh bật muộn 7 lần (hệt bẫy 18/09 nhưng tệ hơn). Quy về USD bằng
    AI_TY_GIA_USD_CNY (mặc định 7.1) và ghi `tien_te` để chỗ in ra nói rõ.
    `is_available:false` = DeepSeek đã khoá gọi API -> coi như còn $0 cho phanh dừng ngay.
    """
    if nha == "deepseek":
        ds = dd.get("balance_infos") or []
        b = next((x for x in ds if (x.get("currency") or "").upper() == "USD"), None)
        b = b or (ds[0] if ds else {})
        tt = (b.get("currency") or "USD").upper()
        try:
            ty = float((e or _env_file()).get("AI_TY_GIA_USD_CNY") or 7.1)
        except ValueError:
            ty = 7.1
        chia = ty if tt == "CNY" else 1.0

        def _f(k):
            try:
                return float(b.get(k) or 0) / chia
            except (TypeError, ValueError):
                return 0.0
        het = not dd.get("is_available", True)
        return {"co": True, "con": 0.0 if het else _f("total_balance"),
                "tien_mat": _f("topped_up_balance"), "voucher": _f("granted_balance"),
                "tien_te": tt, "khoa": het}
    d = dd.get("data") or {}
    return {"co": True, "con": float(d.get("available_balance") or 0),
            "tien_mat": float(d.get("cash_balance") or 0),
            "voucher": float(d.get("voucher_balance") or 0), "tien_te": "USD"}


def so_du_that(nha="kimi", e=None, moi_giay=45, da_chi=None):
    """Số dư THẬT trên bảng của nhà cung cấp — {"co": True, "con", "tien_mat", "voucher", "luc"}
    hoặc {"co": False, "loi": ...}.

    moi_giay: nhịp hỏi lại API. Nhớ ra FILE chứ không chỉ trong RAM vì giao diện, báo cáo và
              8 service là 8 tiến trình riêng — để mỗi cái tự hỏi thì vừa chậm vừa dễ bị chặn.
    da_chi:   nếu chỗ gọi đang tự đếm tiền trong RAM (ai_sale giữ `da_hom_nay`), truyền vào để
              trừ tiếp phần tiêu GIỮA 2 lần hỏi — không thì con số đứng im 45 giây rồi tụt một
              phát, phanh thấy quá muộn.
    Hỏi không được thì TRẢ CACHE CŨ kèm cờ `cu`, đừng trả rỗng: mất số dư là phanh rơi về trần
    sổ (số gõ tay, đã biết là sai) đúng lúc không nên sai.
    """
    url = API_SO_DU.get(nha)
    if not url:
        return {"co": False, "loi": f"nhà {nha} chưa có API số dư"}
    kq, luc = _SO_DU["kq"], _SO_DU["luc"]
    if kq is None or time.time() - luc >= moi_giay:
        # Xem cache TRÊN ĐĨA trước khi hỏi API: 6 service + giao diện + báo cáo là 8 tiến trình
        # riêng, đứa nào cũng tự hỏi mỗi 45 giây thì vừa phí vừa dễ bị nhà cung cấp chặn — mà
        # chặn đúng cái endpoint số dư thì phanh thành mù. Đứa nào vừa hỏi, cả nhà xài chung.
        try:
            d = json.load(open(F_SO_DU, encoding="utf-8"))
            if d.get("nha") == nha and d.get("luc", 0) > luc:
                kq, luc = d["kq"], d["luc"]
                _SO_DU.update(luc=luc, kq=kq)
        except Exception:                               # noqa: BLE001
            pass
    if kq is None or time.time() - luc >= moi_giay:
        key = ((e or _env_file()).get(KEY_SO_DU.get(nha, ""))
               or os.environ.get(KEY_SO_DU.get(nha, ""), "") or "").strip()
        if not key:
            return {"co": False, "loi": f"chưa có {KEY_SO_DU.get(nha)} trong .env"}
        try:
            rq = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
            with urllib.request.urlopen(rq, timeout=8) as r:
                dd = json.loads(r.read().decode())
            kq = _doc_so_du(nha, dd, e)
            luc = time.time()
            _SO_DU.update(luc=luc, kq=kq)
            try:
                os.makedirs(STATE, exist_ok=True)
                with open(F_SO_DU, "w", encoding="utf-8") as f:
                    json.dump({"nha": nha, "luc": luc, "kq": kq}, f, ensure_ascii=False)
            except Exception:                           # noqa: BLE001
                pass
        except Exception as ex:                         # noqa: BLE001
            if kq is None:
                return {"co": False, "loi": str(ex)[:120]}
            kq = dict(kq, cu=True, loi=str(ex)[:120])
    kq = dict(kq, luc=luc)
    if da_chi is not None and kq.get("co"):
        if _SO_DU.get("moc_luc") != luc:                # vừa hỏi lại -> đặt mốc trừ mới
            _SO_DU["moc_luc"], _SO_DU["moc_chi"] = luc, da_chi
        kq["con"] = max(0.0, kq["con"] - max(0.0, da_chi - _SO_DU["moc_chi"]))
    return kq


def lech(nha="kimi", e=None):
    """So SỔ với BẢNG. Trả (sổ tưởng còn, thật còn, lệch) — lệch > 0 là sổ đang đếm THIẾU.

    Để chỗ nào in tiền cũng nói thẳng độ lệch, đừng để nó âm thầm phình ra như hồi 15-17/09.
    """
    sd = so_du_that(nha, e=e)
    if not sd.get("co"):
        return None, None, None
    so = tong_nap(nha) - da_chi_tong(nha)
    return so, sd["con"], so - sd["con"]


# ──────────────── PHANH CHỐNG ÂM — không tin một mình số dư Kimi (19/09) ────────────────
# Chủ shop 18-19/09: "hết tiền là dừng, không để âm". API số dư Kimi báo TRỄ (17/09 đo tay: gọi
# thật 10k token mà 6 phút sau số dư không nhúc nhích), nên phanh nhìn số dư thì lúc nó chạm sàn,
# tiền thật đã tiêu sâu hơn — 18/09 âm $0,105. `da_chi` của so_du_that() không cứu được: mốc trừ
# đặt lại mỗi 45 giây khi hỏi lại API, dù API chưa trừ gì.
# Cách chặn:
#   MỐC = một lần đọc số dư lúc hệ đã NGHỈ ≥ AI_MOC_NGHI_PHUT phút (không lượt gọi nào) → số dư
#         đó đã chốt đủ. Lúc nạp tiền xong hệ luôn đang nghỉ (hết tiền thì phanh đã dừng) → mốc
#         tự đặt đúng, không phải làm tay.
#   còn chắc = MỐC − MỌI lượt gọi ghi trong state/chung/goi_model.jsonl sau mốc (sổ chung của
#         mọi tiến trình, ghi ngay khi Kimi trả usage — không phải đợi Kimi).
#   lấy thêm min với (số dư API − các lượt trong AI_SO_DU_TRE_PHUT phút gần nhất) để bắt tiền
#   tiêu NGOÀI sổ (bản thử trong /root dùng chung key) một khi Kimi đã trừ tới.
# Cuối tiền: phanh dừng → hệ nghỉ → sau AI_MOC_NGHI_PHUT phút mốc dời theo số dư đã chốt; còn dư
# trên sàn thì tự chạy tiếp. Nên tiêu sát được mà không bao giờ lố.
F_GOI = os.path.join(STATE, "chung", "goi_model.jsonl")
F_MOC = os.path.join(STATE, "chung", "moc_so_du.json")
_GOI = {"vi_tri": 0, "ino": None, "cac": []}          # (t, tiền, nhà) mọi lượt gọi đã đọc
_KHOA_GOI = __import__("threading").Lock()          # soạn song song nhiều luồng


def _t_dong(d):
    if d.get("t"):
        return float(d["t"])
    try:                                                # dòng cũ chưa có "t" — giờ VPS
        return time.mktime(time.strptime(d.get("luc", ""), "%Y-%m-%dT%H:%M:%S"))
    except Exception:                                   # noqa: BLE001
        return 0.0


def _doc_goi():
    """Đọc NỐI TIẾP sổ goi_model.jsonl (chỉ phần mới ghi thêm), trả list (t, tiền, nhà)."""
    with _KHOA_GOI:
        return list(_doc_goi_())


def _doc_goi_():
    try:
        st = os.stat(F_GOI)
    except OSError:
        return _GOI["cac"]
    if st.st_ino != _GOI["ino"] or st.st_size < _GOI["vi_tri"]:
        _GOI.update(vi_tri=0, ino=st.st_ino, cac=[])
    if st.st_size > _GOI["vi_tri"]:
        with open(F_GOI, "rb") as f:
            f.seek(_GOI["vi_tri"])
            khoi = f.read()
        cat = khoi.rfind(b"\n") + 1                    # chỉ nhận dòng đã ghi trọn
        for dong in khoi[:cat].splitlines():
            try:
                d = json.loads(dong)
            except Exception:                           # noqa: BLE001
                continue
            _GOI["cac"].append((_t_dong(d), float(d.get("tien") or 0), d.get("nha") or "kimi"))
        _GOI["vi_tri"] += cat
    return _GOI["cac"]


def chi_tu(tu, nha="kimi"):
    """Tổng tiền MỌI lượt gọi model (mọi tiến trình) sau thời điểm `tu` (epoch)."""
    return sum(x for t, x, n in _doc_goi() if t > tu and n == nha)


def doc_moc(nha="kimi"):
    try:
        d = json.load(open(F_MOC, encoding="utf-8"))
        return d if d.get("nha") == nha else None
    except Exception:                                   # noqa: BLE001
        return None


def dat_moc(nha, con, t, ly_do=""):
    os.makedirs(os.path.dirname(F_MOC), exist_ok=True)
    tmp = f"{F_MOC}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"nha": nha, "con": round(float(con), 6), "t": t,
                   "luc": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t)),
                   "ly_do": ly_do}, f, ensure_ascii=False)
    os.replace(tmp, F_MOC)


def con_an_toan(nha="kimi", e=None):
    """Số tiền CÒN CHẮC CHẮN tiêu được — cái phanh chống âm dựa vào (xem khối chú thích trên).

    Trả dict như so_du_that() nhưng "con" = còn chắc; kèm "con_api" (số trên bảng Kimi, có thể
    trễ), "uoc_moc", "uoc_api", "moc". Không hỏi được API mà đã có mốc thì VẪN phanh được theo mốc.
    """
    e = e or _env_file()

    def _so(k, md):
        try:
            return float(e.get(k) or md)
        except ValueError:
            return md
    nghi = _so("AI_MOC_NGHI_PHUT", 20) * 60
    tre = _so("AI_SO_DU_TRE_PHUT", 20) * 60
    he_so = _so("AI_HE_SO_GIA", 1.0)                    # sổ tính theo bảng giá; lệch thì nâng
    sd = so_du_that(nha, e=e)
    moc = doc_moc(nha)
    uoc_api = None
    if sd.get("co"):
        t_api, con_api = sd["luc"], sd["con"]
        # Dời mốc khi số dư được đọc lúc hệ đã nghỉ đủ lâu (lượt gọi cuối trước lúc đọc cách ≥ nghi)
        cuoi = max((t for t, x, n in _doc_goi() if n == nha and t <= t_api), default=0.0)
        if (not sd.get("cu") and t_api - cuoi >= nghi
                and (moc is None or t_api - moc.get("t", 0) >= 60)):
            try:
                dat_moc(nha, con_api, t_api, f"hệ nghỉ {int((t_api - cuoi) // 60)} phút")
                moc = doc_moc(nha)
            except Exception:                           # noqa: BLE001
                pass
        uoc_api = con_api - he_so * chi_tu(t_api - tre, nha)
    uoc_moc = (moc["con"] - he_so * chi_tu(moc["t"], nha)) if moc else None
    cac = [x for x in (uoc_moc, uoc_api) if x is not None]
    if not cac:
        return dict(sd)                                 # co=False: chưa có API lẫn mốc
    kq = dict(sd) if sd.get("co") else {"co": True, "voucher": 0.0, "luc": time.time(),
                                        "loi_api": sd.get("loi")}
    kq.update(co=True, con=min(cac), con_api=sd.get("con"), uoc_moc=uoc_moc, uoc_api=uoc_api,
              moc=moc)
    return kq


# ───────────────────────── Sổ DỰ BÁO (đo mà không tốn tiền) ─────────────────────────
# Vòng `du_bao` quét hội thoại thật bằng LUẬT (ai_co_vao_cuoc) và dựng đúng gói prompt sẽ gửi,
# nhưng KHÔNG gọi model. Nhờ vậy đo được lưu lượng + cỡ gói TRƯỚC khi nạp một xu nào.
# Để sổ riêng, không trộn vào sổ chi thật — dự báo mà nằm chung là sau này đọc nhầm thành đã chi.

def _f_du_bao(mkey):
    return os.path.join(STATE, mkey, "du_bao.jsonl")


def ghi_du_bao(mkey, rec):
    try:
        rec.setdefault("luc", time.strftime("%Y-%m-%dT%H:%M:%S"))
        os.makedirs(os.path.join(STATE, mkey), exist_ok=True)
        with open(_f_du_bao(mkey), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:                       # noqa: BLE001
        print(f"   ⚠️  không ghi được sổ dự báo: {e}")


def xoa_du_bao(mkey):
    """Mỗi lần đo lại thì bỏ số đo cũ — dự báo là ảnh chụp một lần quét, không cộng dồn."""
    try:
        os.remove(_f_du_bao(mkey))
    except FileNotFoundError:
        pass


def doc_du_bao(mkey=None):
    tts = [mkey] if mkey else sorted(
        d for d in (os.listdir(STATE) if os.path.isdir(STATE) else [])
        if os.path.exists(_f_du_bao(d)))
    for tt in tts:
        f = _f_du_bao(tt)
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            for dong in fh:
                try:
                    r = json.loads(dong)
                except Exception:
                    continue
                r.setdefault("tt", tt)
                yield r


def uoc_token(ky_tu_ascii, ky_tu_khac):
    """Ước số token từ số ký tự. Trả (thấp, cao) — CÓ CHỦ Ý trả khoảng, không trả một số.

    Không có bộ tách token của Kimi/Claude ở máy nên mọi con số đơn lẻ đều là số giả vờ chính xác.
    Khoảng thường dùng: chữ Latin ~4 ký tự/token, chữ có dấu / Ả Rập / CJK nặng hơn nhiều (~1,5).
    Số THẬT sẽ hiện ở cột token trong báo cáo ngay sau vòng chạy có tiền đầu tiên.
    """
    thap = ky_tu_ascii / 4.2 + ky_tu_khac / 2.0
    cao = ky_tu_ascii / 3.0 + ky_tu_khac / 1.2
    return thap, cao


def dem_ky_tu(s):
    """(số ký tự ASCII, số ký tự còn lại) — tách ra vì hai loại tốn token khác hẳn nhau."""
    s = s or ""
    a = sum(1 for ch in s if ord(ch) < 128)
    return a, len(s) - a


def bang_du_bao(mkey=None, ra_token=250, in_ra=True):
    """Từ số đo của vòng `du_bao`, chiếu ra tiền mỗi ngày / mỗi tháng cho từng model.

    HAI KỊCH BẢN, cố ý không gộp thành một số:

      SÀN  — chỉ những lượt AI phải vào cuộc NGAY LÚC ĐO: Botcake im, hoặc Botcake đã rep mà
             AI phải đọc lại xem có trúng không.
      TRẦN — cộng thêm những lượt hôm nay "sale thật đã vào nên AI tránh ra". Khi chạy thật,
             AI nhắn sau khi đợi Botcake ~90 giây, tức nó vào TRƯỚC sale — nên phần lớn số này
             sẽ chuyển thành lượt AI phải gọi model. Đây mới là con số để quyết nạp bao nhiêu.

    Cỡ gói prompt lấy trung bình từ những lượt đã dựng gói thật, tách hai phần vì giá khác
    nhau 10 lần: phần LẶP LẠI (luật + kịch bản page, nằm trong `system`, được đệm) và phần
    MỚI mỗi lượt (hội thoại của khách, luôn trả giá vào đầy đủ).
    """
    rows = list(doc_du_bao(mkey))
    meta = [r for r in rows if r.get("meta")]
    rows = [r for r in rows if not r.get("meta")]
    goi = [r for r in rows if r.get("cua") in ("xet", "tra_loi")]
    if not goi:
        return None
    gio = max([m.get("gio") or 24 for m in meta] or [24])
    luat_a = max([m.get("luat_a") or 0 for m in meta] or [0])
    luat_k = max([m.get("luat_k") or 0 for m in meta] or [0])
    quet = len({(r.get("conv"), r.get("khach_luc")) for r in rows})
    n_im = sum(1 for r in rows if r.get("cua") == "im")

    n = len(goi)
    lap = uoc_token(sum(r.get("od_a", 0) for r in goi) / n + luat_a,
                    sum(r.get("od_k", 0) for r in goi) / n + luat_k)
    moi = uoc_token(sum(r.get("nd_a", 0) for r in goi) / n,
                    sum(r.get("nd_k", 0) for r in goi) / n)
    he_so = 24.0 / gio
    san_ngay, tran_ngay = n * he_so, (n + n_im) * he_so

    kq = {"gio": gio, "quet": quet, "quet_ngay": quet * he_so,
          "san": n, "san_ngay": san_ngay, "tran": n + n_im, "tran_ngay": tran_ngay,
          "n_im": n_im, "model": {},
          "tok_vao": [lap[i] + moi[i] for i in (0, 1)],
          "tok_lap": list(lap), "tok_moi": list(moi), "ra_token": ra_token,
          "gia": {t: list(g) for t, g in GIA_MODEL_THAM_CHIEU},
          "ky_tu_goi": sum(r.get("od_a", 0) + r.get("od_k", 0)
                           + r.get("nd_a", 0) + r.get("nd_k", 0) for r in goi) / n
                       + luat_a + luat_k}
    for ten, (gv, gd, gg, gr) in GIA_MODEL_THAM_CHIEU:
        # /lượt, USD
        khong = [(lap[i] * gv + moi[i] * gv + ra_token * gr) / 1e6 for i in (0, 1)]
        co = [(lap[i] * gd + moi[i] * gv + ra_token * gr) / 1e6 for i in (0, 1)]
        kq["model"][ten] = {
            "luot": khong,
            "san_thang": [x * san_ngay * 30 for x in khong],
            "tran_thang": [x * tran_ngay * 30 for x in khong],
            "san_thang_dem": [x * san_ngay * 30 for x in co],
            "tran_thang_dem": [x * tran_ngay * 30 for x in co],
            "tran_ngay": [x * tran_ngay for x in khong],
        }
    if not in_ra:
        return kq

    print("\n  ── DỰ BÁO CHI PHÍ (đo bằng luật, KHÔNG gọi model — chưa tốn xu nào) ──")
    print(f"  Cửa sổ đo              : {gio} giờ" + (f" · {mkey}" if mkey else " · mọi thị trường"))
    print(f"  Lượt khách quét được   : {quet:,}   (~{quet*he_so:,.0f}/ngày)")
    print(f"  SÀN — AI phải gọi model: {n:,}   (~{san_ngay:,.0f}/ngày)")
    print(f"  TRẦN — cộng {n_im:,} lượt hôm nay sale thật đã vào trước"
          f"   (~{tran_ngay:,.0f}/ngày)")
    print(f"  Gói prompt trung bình  : {kq['ky_tu_goi']:,.0f} ký tự"
          f"  → ước {kq['tok_vao'][0]:,.0f}–{kq['tok_vao'][1]:,.0f} token vào/lượt")
    print(f"\n  {'model':<15}{'/lượt':>16}{'SÀN /tháng':>16}{'TRẦN /tháng':>16}"
          f"{'TRẦN nếu có đệm':>18}")
    for ten, v in kq["model"].items():
        c1 = f"${v['luot'][0]:.4f}-{v['luot'][1]:.4f}"
        c2 = f"${v['san_thang'][0]:,.0f}-{v['san_thang'][1]:,.0f}"
        c3 = f"${v['tran_thang'][0]:,.0f}-{v['tran_thang'][1]:,.0f}"
        c4 = f"${v['tran_thang_dem'][0]:,.0f}-{v['tran_thang_dem'][1]:,.0f}"
        print(f"  {ten:<15}{c1:>16}{c2:>16}{c3:>16}{c4:>18}")
    print("\n  Lấy cột TRẦN mà quyết: chạy thật thì AI nhắn trước sale, không phải nhặt phần thừa.")
    print("  Khoảng rộng vì máy không có bộ tách token của Kimi/Claude — số CHÍNH XÁC hiện ở")
    print("  cột token trong `bao_cao` ngay sau vòng chạy có tiền đầu tiên.")
    print("  Claude chắc chắn có đệm; Kimi CHƯA đo được — cứ tính theo cột KHÔNG đệm cho an toàn.")
    return kq


# Bảng model để so sánh khi dự báo — cố ý xếp từ đắt xuống rẻ để nhìn ra khoảng cách.
GIA_MODEL_THAM_CHIEU = [
    ("claude-opus-5", (5.00, 0.50, 6.25, 25.00)),
    ("kimi-k3",       (3.00, 0.30, 3.00, 15.00)),
    ("claude-sonnet", (3.00, 0.30, 3.75, 15.00)),
    ("claude-haiku",  (1.00, 0.10, 1.25, 5.00)),
    ("kimi-k2",       (0.95, 0.16, 0.95, 4.00)),
    # 20/09: đổi sang DeepSeek nên bảng dự báo phải có nó, không thì ô "giữ model đang chạy"
    # rơi về kimi-k3 và ước tiền sai gấp 10. Giá CAO ĐIỂM (thấp điểm rẻ một nửa) — ước theo
    # cao điểm cho an toàn, bảng này chỉ để so model với nhau.
    ("deepseek-v4-pro", (1.32, 0.044, 1.32, 3.96)),
    ("deepseek-flash", (0.30, 0.006, 0.30, 1.20)),
]


# ───────────────────────── Sổ nạp tiền ─────────────────────────

def doc_nap():
    if not os.path.exists(F_NAP):
        return []
    try:
        with open(F_NAP, encoding="utf-8") as f:
            return json.load(f).get("nap") or []
    except Exception:
        return []


def nap_them(so_tien, nha="kimi", ghi_chu=""):
    ds = doc_nap()
    ds.append({"luc": time.strftime("%Y-%m-%d %H:%M"), "nha": nha,
               "so_tien": round(float(so_tien), 4), "ghi_chu": ghi_chu})
    os.makedirs(STATE, exist_ok=True)
    with open(F_NAP, "w", encoding="utf-8") as f:
        json.dump({"nap": ds}, f, ensure_ascii=False, indent=1)
    return ds


def tong_nap(nha=None):
    return sum(x.get("so_tien") or 0 for x in doc_nap()
               if not nha or x.get("nha") == nha)


# ───────────────────────── Ngân sách (trần chi) ─────────────────────────

def ngan_sach(e):
    """Đọc trần chi trong .env. Trả (trần mỗi ngày, trần tổng) — 0 nghĩa là KHÔNG đặt."""
    def so(k):
        v = (e.get(k) or os.environ.get(k) or "").strip().replace("$", "").replace(",", ".")
        try:
            return float(v)
        except Exception:
            return 0.0
    return so("AI_NGAN_SACH_NGAY"), so("AI_NGAN_SACH_TONG")


# ───────────────────────── Phân loại câu hỏi của khách ─────────────────────────
# Gom câu hỏi thành nhóm để biết khách hay hỏi gì nhất -> biết phải bổ sung kịch bản chỗ nào.
# Đa ngữ vì 11 thị trường: Anh, Tagalog, Ả Rập, Tây Ban Nha, Rumani, Bungari, Nhật, Trung, Việt.
# Đây là ƯỚC LƯỢNG bằng từ khoá, không phải model đọc hiểu — đủ để xếp hạng, đừng coi là tuyệt đối.

NHOM = [
    ("Giá / bao nhiêu tiền",
     r"how much|price|pricing|cost|magkano|presyo|precio|cu[aá]nto|cât cost|pre[țt]|"
     r"цена|колко струва|بكم|السعر|كم سعر|كم الس|値段|いくら|価格|多少[钱錢]|價[钱錢]|"
     r"giá|bao nhiêu tiền"),
    ("Ship / bao lâu nhận / phí ship",
     r"\bship|shipping|deliver|delivery|how long|when.{0,12}(arrive|receive|get it)|"
     r"kailan|ilang araw|padala|env[ií]o|cu[aá]ndo llega|livrare|c[âa]nd ajunge|"
     r"доставк|кога ще|توصيل|الشحن|متى.{0,10}(يصل|الوصول)|配送|届く|発送|運費|送達|多久|"
     r"giao hàng|bao lâu|phí ship"),
    ("Thanh toán / COD",
     r"\bcod\b|cash on deliv|payment|how.{0,10}\bpay\b|gcash|paypal|credit card|"
     r"bayad|paano magbayad|pago|contra reembolso|plat[ăa]|ramburs|"
     r"наложен платеж|плащане|الدفع|الدفع عند|عند الاستلام|支払|代引|付款|貨到付款|货到付款|"
     r"thanh toán"),
    ("Còn hàng / muốn đặt",
     r"available|in stock|out of stock|do you have|want.{0,15}to (buy|order|get)|"
     r"gusto ko|bibili|kukunin|i'?ll take|send me (one|two|the)|place an order|"
     r"meron|mayroon|order po|disponible|hay stock|disponibil|"
     r"наличн|има ли|متوفر|متاح|أريد الطلب|الطلب|在庫|注文|有[货貨]|下[单單]|"
     r"còn hàng|đặt hàng|muốn mua"),
    ("Size / màu / mẫu",
     r"\bsize|sizes|colou?r|which model|sukat|kulay|talla|tama[ñn]o|m[ăa]rime|culoare|"
     r"размер|цвят|مقاس|لون|الألوان|サイズ|色|尺寸|[颜顏]色|"
     r"size|màu|mẫu nào"),
    ("Chất liệu / công dụng / cách dùng",
     r"material|made of|what.{0,10}(is it made|material)|ingredient|how to use|does it work|"
     r"paano gamitin|ano.{0,8}gamit|材質|素材|成分|使用方法|"
     r"ingrediente|c[oó]mo se usa|material|ingredient[e]?|cum se folose|"
     r"материал|съставк|как се използва|مادة|خامة|طريقة الاستخدام|المكونات|"
     r"chất liệu|công dụng|cách dùng"),
    ("Đổi trả / bảo hành",
     r"return|refund|exchange|warrant|guarantee|palit|garant[ií]a|garan[țt]ie|"
     r"гаранция|връщане|ضمان|استبدال|إرجاع|返品|保証|退[换換]|保固|"
     r"đổi trả|bảo hành|hoàn tiền"),
    ("Đơn cũ / vận đơn / khiếu nại",
     r"tracking|my order|the order i|parcel|courier|rider|not.{0,12}(received|delivered)|"
     r"already (paid|received)|still waiting|رقم التتبع|طلبي|لم يصل|追跡|物流|"
     r"đơn của (tôi|em|mình)|chưa nhận"),
    ("Địa chỉ / cửa hàng ở đâu",
     r"your address|where.{0,15}(located|are you|shop|store)|pick ?up|saan.{0,10}(kayo|located)|"
     r"d[ií]recci[oó]n|adresa|адрес|العنوان|أين موقع|住所|地址|"
     r"địa chỉ|ở đâu"),
    ("Gật đầu / trả lời tiếp giữa hội thoại",
     r"^\W*(yes|yeah|yep|yup|sure|ok(ay)?|no|nope|opo|oo|sige|hindi|s[ií]|nu|da|"
     r"да|не|نعم|لا|はい|いいえ|好|不用|đúng|vâng|không)\b.{0,20}$"),
    ("Chào hỏi / tin không có nội dung",
     r"^\W*(hi+|hey+|hello+|hallo|hola|yo|salam|assalam|مرحبا|اهلا|السلام|你好|こんにちは|"
     r"kumusta|kamusta|buna|bun[ăa]|здравей|ok|okay|yes|no|👍)\W*$"),
]
NHOM = [(ten, re.compile(rx, re.I)) for ten, rx in NHOM]


def phan_nhom(text):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t:
        return "Chào hỏi / tin không có nội dung"
    for ten, rx in NHOM:
        if rx.search(t):
            return ten
    return "Khác / khách nói tiếp giữa hội thoại"


# ───────────────────────── Báo cáo ─────────────────────────

def _ngay_truoc(n):
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - n * 86400))


def _dd(ngay):
    return ngay[8:10] + "/" + ngay[5:7]


def usd(x):
    """Tiền nhỏ hơn 1 xu vẫn phải nhìn thấy — $0.00 đọc thành 'không đặt trần' là hiểu sai."""
    return f"${x:,.2f}" if abs(x) >= 0.01 else f"${x:.4f}"


def _tien(x, rong=9):
    return f"${x:,.4f}".rjust(rong)


def bao_cao(mkey=None, ngay=30):
    tu = _ngay_truoc(ngay - 1)
    recs = list(doc(mkey, tu_ngay=tu))
    pham_vi = mkey or "TẤT CẢ thị trường"
    print(f"\n{'═'*74}\n  BÁO CÁO AI SALE — {pham_vi} — {ngay} ngày gần nhất "
          f"({_dd(tu)} → {_dd(time.strftime('%Y-%m-%d'))})\n{'═'*74}")
    if not recs:
        print("\n  Sổ chi phí còn trống — chưa có vòng `ai_sale.py chay` nào chạy sau khi bật"
              " ghi sổ.\n  Chạy thử một vòng rồi xem lại:  python3 ai_sale.py chay usa --so 20\n")
        _in_nap(mkey)
        return

    # Mỗi vòng quét quét lại cả cửa sổ --gio, nên MỘT lượt khách nhắn có thể sinh nhiều dòng.
    # TIỀN thì cộng hết (mỗi lượt gọi model là mất tiền thật), còn CHỈ SỐ HỘI THOẠI phải gộp
    # về dòng cuối cùng của mỗi (hội thoại, tin cuối của khách) — không gộp là đếm phồng.
    duy_nhat = {}
    for r in recs:
        duy_nhat[(r.get("conv"), r.get("khach_luc"))] = r
    luot_recs = list(duy_nhat.values())

    # ── Tiền ───────────────────────────────────────────────────────────────
    nhas = sorted({r.get("nha") for r in recs if r.get("nha")} |
                  {x.get("nha") for x in doc_nap()})
    chi_cua_so = sum(r.get("tien") or 0 for r in recs)
    print("\n  ── TIỀN ─────────────────────────────────────────────────────────────")
    print(f"  {'nhà cung cấp':<14}{'đã nạp':>12}{'đã chi (từ trước)':>20}{'còn lại':>12}")
    for nha in nhas:
        nap, chi = tong_nap(nha), da_chi_tong(nha)
        con = nap - chi
        canh = "  ⚠️ chưa khai tiền nạp" if nap == 0 else ("  🚨 ÂM" if con < 0 else "")
        print(f"  {nha:<14}{nap:>11,.2f}${chi:>19,.4f}${con:>11,.4f}${canh}")
    print(f"\n  Chi trong {ngay} ngày này: ${chi_cua_so:,.4f}")

    # ── Theo ngày ──────────────────────────────────────────────────────────
    theo_ngay = defaultdict(lambda: {"tien": 0.0, "goi": 0, "vao": 0, "ra": 0,
                                     "hoi_thoai": set(), "tra_loi": set()})
    for r in recs:
        d = theo_ngay[r.get("luc", "")[:10]]
        d["tien"] += r.get("tien") or 0
        d["goi"] += 1 if r.get("goi") else 0
        d["vao"] += (r.get("vao") or 0) + (r.get("doc_dem") or 0) + (r.get("ghi_dem") or 0)
        d["ra"] += r.get("ra") or 0
        khoa = (r.get("conv"), r.get("khach_luc"))
        d["hoi_thoai"].add(khoa)
        if r.get("hd") in ("tra_loi", "len_don"):
            d["tra_loi"].add(khoa)
    ngay_chay = [d for d in theo_ngay if theo_ngay[d]["tien"] > 0]
    tb_ngay_chay = chi_cua_so / len(ngay_chay) if ngay_chay else 0
    tb_ngay_lich = chi_cua_so / ngay

    print("\n  ── CHI THEO NGÀY ────────────────────────────────────────────────────")
    print(f"  {'ngày':<8}{'lượt gọi model':>16}{'token vào':>12}{'token ra':>10}"
          f"{'tiền':>11}{'lượt khách':>12}{'AI trả lời':>12}")
    for d in sorted(theo_ngay, reverse=True):
        v = theo_ngay[d]
        print(f"  {_dd(d):<8}{v['goi']:>16,}{v['vao']:>12,}{v['ra']:>10,}"
              f"{_tien(v['tien'], 11)}{len(v['hoi_thoai']):>12,}{len(v['tra_loi']):>12,}")
    print(f"\n  Chi TB / ngày CÓ CHẠY  : ${tb_ngay_chay:,.4f}   ({len(ngay_chay)} ngày có chạy)")
    print(f"  Chi TB / ngày lịch     : ${tb_ngay_lich:,.4f}   (chia đều {ngay} ngày)")

    # Còn chạy được bao lâu
    for nha in nhas:
        con = tong_nap(nha) - da_chi_tong(nha)
        chi_nha = sum(r.get("tien") or 0 for r in recs if r.get("nha") == nha)
        tb = chi_nha / len(ngay_chay) if ngay_chay else 0
        if tong_nap(nha) and tb > 0:
            con_ngay = con / tb
            het = time.strftime("%d/%m/%Y", time.localtime(time.time() + con_ngay * 86400))
            print(f"  → {nha}: với đà này còn chạy được ~{con_ngay:,.0f} ngày (hết khoảng {het})")
        elif tong_nap(nha) == 0:
            print(f"  → {nha}: chưa khai tiền nạp — chạy  python3 ai_sale.py nap <số tiền>"
                  f" --nha {nha}  để tính được số dư")

    # ── Theo page ──────────────────────────────────────────────────────────
    theo_page = defaultdict(lambda: {"tien": 0.0, "goi": 0, "hoi_thoai": set(),
                                     "tra_loi": set(), "don": set(), "tt": ""})
    for r in recs:
        p = theo_page[r.get("page") or r.get("pid") or "?"]
        khoa = (r.get("conv"), r.get("khach_luc"))
        p["tien"] += r.get("tien") or 0
        p["goi"] += 1 if r.get("goi") else 0
        p["hoi_thoai"].add(khoa)
        if r.get("hd") in ("tra_loi", "len_don"):
            p["tra_loi"].add(khoa)
        if r.get("hd") == "len_don":
            p["don"].add(khoa)
        p["tt"] = r.get("tt") or ""
    print("\n  ── CHI THEO PAGE (kênh) ─────────────────────────────────────────────")
    print(f"  {'page':<34}{'tt':<9}{'lượt khách':>11}{'AI trả lời':>11}{'đơn':>6}{'tiền':>11}")
    for ten, v in sorted(theo_page.items(), key=lambda x: -x[1]["tien"])[:25]:
        print(f"  {ten[:32]:<34}{v['tt'][:8]:<9}{len(v['hoi_thoai']):>11,}"
              f"{len(v['tra_loi']):>11,}{len(v['don']):>6,}{_tien(v['tien'], 11)}")
    if len(theo_page) > 25:
        print(f"  … và {len(theo_page)-25} page nữa")

    # ── Hội thoại & tỷ lệ phản hồi ─────────────────────────────────────────
    luot = luot_recs
    cua = Counter(r.get("cua") for r in luot_recs)
    hd = Counter(r.get("hd") for r in luot_recs)
    duoc_vao = cua["tra_loi"] + cua["xet"]
    da_gui = hd["tra_loi"] + hd["len_don"] + hd["tra_loi_treo"]
    print("\n  ── HỘI THOẠI & TỶ LỆ PHẢN HỒI ───────────────────────────────────────")
    print(f"  Lượt khách nhắn AI quét được : {len(luot):>6,}")
    print(f"  AI được phép vào cuộc        : {duoc_vao:>6,}"
          f"   ({duoc_vao/max(len(luot),1)*100:.0f}% số lượt quét)")
    print(f"     ├ Botcake im → AI trả lời : {cua['tra_loi']:>6,}")
    print(f"     └ Botcake đã rep → AI xét : {cua['xet']:>6,}")
    print(f"  Sale thật đã vào → AI im     : {cua['im']:>6,}")
    print(f"  Luật bắt treo cho sale       : {cua['treo']:>6,}")
    print(f"\n  AI ĐÃ GỬI TIN                : {da_gui:>6,}"
          f"   → tỷ lệ phản hồi {da_gui/max(len(luot),1)*100:.0f}% trên tổng lượt"
          f" · {da_gui/max(duoc_vao,1)*100:.0f}% trên phần được vào cuộc")
    print(f"     trong đó chốt đơn         : {hd['len_don']:>6,}")
    # Tách hai kiểu "im"/"treo": do LUẬT chặn từ đầu (không tốn tiền) và do MODEL đọc rồi quyết
    # (đã tốn tiền). Gộp chung là nhìn nhầm chỗ tốn tiền.
    im_model = sum(1 for r in luot_recs
                   if r.get("cua") in ("xet", "tra_loi") and r.get("hd") == "im")
    treo_model = sum(1 for r in luot_recs
                     if r.get("cua") in ("xet", "tra_loi") and r.get("hd") == "treo")
    print(f"  Model đọc rồi chọn IM        : {im_model:>6,}"
          f"   (bot đã rep trúng — lượt này VẪN tốn tiền)")
    print(f"  Treo cho sale (tổng)         : {hd['treo']:>6,}"
          f"   ({cua['treo']:,} do luật chặn sẵn · {treo_model:,} do model quyết)")
    print(f"  Rep 1 câu rồi giao sale      : {hd['tra_loi_treo']:>6,}")
    print(f"  Giao sale tra địa chỉ        : {hd['xac_minh_nha']:>6,}")
    print(f"  Lỗi (không soạn / gửi hỏng)  : {hd['loi']:>6,}")
    if hd["loi"]:
        print("     ⚠️  lỗi vẫn TỐN TIỀN nếu model đã trả lời rồi mới hỏng — xem cột lượt gọi")

    # ── Top câu hỏi ────────────────────────────────────────────────────────
    hoi = [r.get("hoi") for r in luot_recs if (r.get("hoi") or "").strip()]
    if hoi:
        nhom = Counter(phan_nhom(h) for h in hoi)
        print(f"\n  ── TOP CÂU HỎI CỦA KHÁCH (n={len(hoi):,}) ─────────────────────────────")
        for i, (ten, n) in enumerate(nhom.most_common(12), 1):
            thanh = "█" * max(1, round(n / max(nhom.most_common(1)[0][1], 1) * 24))
            print(f"  {i:>2}. {ten:<36}{n:>6,} {n/len(hoi)*100:>4.0f}%  {thanh}")
        print("     (xếp nhóm bằng TỪ KHOÁ đa ngữ, là ước lượng — không phải model đọc hiểu)")

        # Bảng trên là MỌI tin cuối của khách, gồm cả câu nói giữa hội thoại sale đã xử.
        # Muốn biết phải bổ sung kịch bản chỗ nào thì nhìn bảng dưới: chỉ những lượt AI
        # thật sự phải trả lời (Botcake im hoặc Botcake rep mà AI phải xét lại).
        hoi_ai = [r.get("hoi") for r in luot_recs
                  if r.get("cua") in ("xet", "tra_loi") and (r.get("hoi") or "").strip()]
        if hoi_ai:
            n_ai = Counter(phan_nhom(h) for h in hoi_ai)
            print(f"\n  Chỉ tính {len(hoi_ai):,} lượt AI PHẢI trả lời (đây là chỗ cần bổ sung kịch bản):")
            for i, (ten, n) in enumerate(n_ai.most_common(8), 1):
                print(f"  {i:>2}. {ten:<40}{n:>6,} {n/len(hoi_ai)*100:>4.0f}%")

        tho = Counter(re.sub(r"\s+", " ", h.lower().strip(" ?.!،؟")) for h in hoi)
        print("\n  Câu nguyên văn hay gặp nhất:")
        for i, (t, n) in enumerate(tho.most_common(10), 1):
            print(f"  {i:>2}. {n:>4,}×  {t[:64]}")

    _in_nap(mkey)
    print(f"\n  (Sổ: state/<thị trường>/so_chi_phi.jsonl · tiền nạp: state/nap_tien.json)\n")


def _in_nap(mkey=None):
    ds = doc_nap()
    if not ds:
        print("\n  ── TIỀN NẠP ─────────────────────────────────────────────────────────")
        print("  Chưa khai lần nạp nào. Mỗi lần nạp tiền vào Kimi/Anthropic, khai lại:")
        print("     python3 ai_sale.py nap 20 --nha kimi --ghi \"nạp lần 1\"")
        return
    print("\n  ── TIỀN NẠP ĐÃ KHAI ─────────────────────────────────────────────────")
    for x in ds[-10:]:
        print(f"  {x['luc']:<18}{x.get('nha','?'):<12}{x['so_tien']:>10,.2f}$"
              f"   {x.get('ghi_chu','')}")


# ───────────────────────── CLI riêng ─────────────────────────

def main(a):
    if not a:
        print(__doc__)
        return
    if a[0] == "bao_cao":
        tt = a[1] if len(a) > 1 and not a[1].startswith("--") else None
        ng = int(a[a.index("--ngay") + 1]) if "--ngay" in a else 30
        bao_cao(tt, ng)
    elif a[0] == "nap":
        if "--xem" in a or len(a) == 1:
            _in_nap()
            return
        nha = a[a.index("--nha") + 1] if "--nha" in a else "kimi"
        gc = a[a.index("--ghi") + 1] if "--ghi" in a else ""
        try:
            so = float(a[1].replace("$", "").replace(",", "."))
        except Exception:
            sys.exit("❌ Số tiền không đọc được. Ví dụ: python3 chi_phi.py nap 20 --nha kimi")
        nap_them(so, nha, gc)
        print(f"\n  ✅ Đã ghi: nạp {so:,.2f}$ vào {nha}."
              f"  Tổng đã nạp {nha}: {tong_nap(nha):,.2f}$ ·"
              f" đã chi {da_chi_tong(nha):,.4f}$ ·"
              f" còn {tong_nap(nha)-da_chi_tong(nha):,.4f}$\n")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

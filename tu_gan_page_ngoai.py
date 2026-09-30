#!/usr/bin/env python3
"""Page MỚI còn gói mà thuộc shop POS RIÊNG (không có trong markets.json) → TỰ GẮN vào thị trường
theo tiền tệ page báo giá, để AI Sale tự kéo kịch bản và chat khách mới — không đợi ai sửa tay.

Chủ shop 19/09: *"rõ ràng tôi bảo theo đơn vị tiền tệ mà gắn rồi còn gì"*; 20/09: *"page mới lên là
bạn chủ động tự học kịch bản để mà chát các khách mới đó nhé"*. Trước bản này
`state/chung/page_gan_them.json` phải sửa TAY: page mới nằm ngoài 12 shop thị trường thì AI không
thấy page → không kéo kịch bản → không chat, mà cũng không có dòng log nào.

Gắn thận trọng, vì gắn SAI = báo giá nước khác cho khách (mục 3 của luật cấm):
  · chỉ xét page CÒN GÓI (has_active_subscription và KHÔNG đếm ngược) — luật phạm vi 19/09
  · chỉ gắn page ĐÃ CÓ mẫu Trả lời nhanh (không mẫu thì AI cũng bỏ page đó, gắn vô nghĩa)
  · chỉ đếm chữ tiền tệ DÍNH SỐ trong tin của mẫu ("99 AED", "950 TWD", "$79"); cần ≥2 lần và
    thị trường nhất phải hơn thứ hai >1,5 lần — ngang nhau hoặc mơ hồ (ريال của Saudi/Qatar/Oman,
    "dinar" của Kuwait/Bahrain) thì KHÔNG gắn, chỉ ghi ra cho người chọn
  · KHÔNG đụng ô đã có trong file (gắn tay thắng), KHÔNG sửa markets.json

Đo hai chiều 20/09 (`/root/thu_gan.py`, 44 page đã biết thị trường thật, gồm 4 page người gắn tay
19/09): gắn ĐÚNG 39 · gắn SAI 0 · không dám gắn 5 (page không nêu giá trong mẫu). Bản đầu dump cả
JSON của mẫu nên id chủ đề "bd2727chaohang" khớp `bd` của Bahrain → 2 page bị gắn sai; nay chỉ đọc
chữ trong `tin`.

LỖI TỚI 22/09: `quet()` đưa mẫu THÔ của `KB.tai_1_page` vào `chon_thi_truong` (cần mẫu đã `KB._gon`) → chữ
rỗng → 0 page được gắn thật dù bộ đo 20/09 (đọc kich_ban.json, đã gọn) ra 39 đúng. Muốn đo lại thì đo
ĐÚNG ĐƯỜNG CHẠY THẬT (tai_1_page → _gon), đừng đọc bản lưu.

Chạy tay: python3 tu_gan_page_ngoai.py [--that]   (không có --that = chỉ xem)
Trong AI Sale: `ai_sale._tu_gan_page_moi()` gọi 30 phút/lần ngay trước lượt tra lại danh sách page.
"""
import json
import os
import re
import sys
import time

if __package__ is None and "/opt/pancake-tool" not in sys.path:
    sys.path.insert(0, "/opt/pancake-tool")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
F_GAN = os.path.join(SCRIPT_DIR, "state", "chung", "page_gan_them.json")


def _doc_gan():
    try:
        return json.load(open(F_GAN, encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return {}


def _ghi_gan(them):
    """Đọc LẠI rồi ghi bằng os.replace — AI Sale đọc file này mỗi lần tra danh sách page."""
    d = _doc_gan()
    for mkey, o in them.items():
        d.setdefault(mkey, {}).update(o)
    tam = f"{F_GAN}.{os.getpid()}.tmp"
    with open(tam, "w", encoding="utf-8") as g:
        json.dump(d, g, ensure_ascii=False, indent=1)
    os.replace(tam, F_GAN)
    return d


def _chu_trong_mau(mau):
    """CHỈ chữ trong tin nhắn của mẫu — bỏ `chu_de_id`/`tu_khoa`. Id chủ đề dạng hex
    ("bd2727chaohang") khớp `bd` của Bahrain 5 lần trên page UAE → gắn sai (đo 20/09)."""
    ra = []
    for m in mau:
        ra += [t for t in (m.get("tin") or []) if t]
    return "\n".join(ra)


def _dem_tien_te(text, mk):
    """{mkey: số lần thấy GIÁ mang tiền tệ của thị trường đó}.

    Chỉ tính chữ tiền tệ DÍNH SỐ ("99 AED", "AED 99", "950 TWD", "$79") — chữ tiền tệ trơ trọi
    trong đoạn mô tả không phải giá. Số phải đứng một mình (không dính chữ) để chuỗi
    "bd2727price" không bị đọc thành "BD 2727".
    """
    ra = {}
    for mkey, m in mk.items():
        if not isinstance(m, dict) or not m.get("bat"):
            continue
        tu = [x for x in (m.get("tu_tien_te"),) if x]
        for ma in (m.get("ma_tien_te"), m.get("tien_te")):
            if ma and re.fullmatch(r"[A-Za-z$€¥]{1,4}", ma):
                tu.append(re.escape(ma))
        alt = "|".join(tu)
        n = 0
        if alt:
            n += len(re.findall(rf"(?<![0-9a-z])(?:{alt})(?![a-z])[\s:]*\d[\d.,]*(?![\w])", text, re.I))
            n += len(re.findall(rf"(?<![\w])\d[\d.,]*\s*(?:{alt})(?![a-z])", text, re.I))
        kh = m.get("ky_hieu_truoc")
        if kh:
            # 24/09: "NT$1,699" của Đài từng bị đếm thành "$" của Mỹ (10/29 page Đài) → ký hiệu đứng sau chữ cái không tính
            n += len(re.findall(rf"(?<![A-Za-z]){kh}\s?\d[\d.,]*(?![\w])", text, re.I))
        if n:
            ra[mkey] = n
    return ra


def chon_thi_truong(mau, mk):
    """(mkey, số lần khớp, bảng đếm) — mkey=None là KHÔNG dám gắn."""
    dem = _dem_tien_te(_chu_trong_mau(mau), mk)
    xep = sorted(dem.items(), key=lambda x: -x[1])
    if not xep or xep[0][1] < 2 or (len(xep) > 1 and xep[0][1] <= xep[1][1] * 1.5):
        return None, 0, dem
    return xep[0][0], xep[0][1], dem


def quet(that=False, in_ra=None):
    """Tìm page còn gói ngoài shop thị trường và gắn. Trả (số page gắn, [dòng chờ người xử])."""
    noi = in_ra or (lambda *a: None)
    import ai_sale as A
    import kich_ban as KB
    tok = A.env().get("PANCAKE_USER_TOKEN", "")
    if not tok:
        noi("  ⚠ tự gắn page: thiếu PANCAKE_USER_TOKEN")
        return 0, []
    mk = json.load(open(os.path.join(SCRIPT_DIR, "markets.json"), encoding="utf-8"))
    shop_tt = {str(m["shop_id"]) for k, m in mk.items()
               if isinstance(m, dict) and m.get("shop_id")}
    con = [p for p in (A._ds_page_tai_khoan() or []) if A._con_goi_that(p)]
    da_gan = {pid for o in _doc_gan().values() if isinstance(o, dict) for pid in o}
    ngoai = [p for p in con if str(p.get("shop_id") or "") not in shop_tt
             and str(p["id"]) not in da_gan]
    them, cho_nguoi = {}, []
    # 23/09 — PAGE NẰM TRONG SHOP THỊ TRƯỜNG NHƯNG KỊCH BẢN BÁO GIÁ TIỀN NƯỚC KHÁC (ca Gold Avenue Taiwan: shop POS Mỹ,
    # mẫu 1290/1790 TWD). Chủ shop: *"kể cả nếu tôi không dời, bạn cứ tư vấn theo kịch bản chứ, vì tôi dặn bạn giá bán
    # thị trường nào tư vấn theo thị trường đó mà"* → gắn sang nước theo tiền tệ; ai_sale._page_gan_noi_khac() bỏ page
    # khỏi nước của shop POS. Mẫu đọc từ state/<tt>/kich_ban.json (AI nước đó đã kéo, dạng gọn — cùng dạng _chu_trong_mau
    # đọc) để khỏi hỏi Pancake ~135 page mỗi 30 phút; page chưa có bản lưu thì hỏi tối đa 5 page/lượt. Ngưỡng y hệt page
    # ngoài shop. Đo 23/09: 135 page còn gói trong shop → 125 khớp shop, 9 không rõ (giữ theo shop), 1 lệch = Gold Avenue.
    tt_cua_shop = {str(m["shop_id"]): k for k, m in mk.items() if isinstance(m, dict) and m.get("shop_id")}
    _kb_luu, hoi_them = {}, 0
    for p in con:
        pid, ten = str(p["id"]), (p.get("name") or pid)
        tt = tt_cua_shop.get(str(p.get("shop_id") or ""))
        if not tt or pid in da_gan:
            continue
        if tt not in _kb_luu:
            try:
                _kb_luu[tt] = json.load(open(os.path.join(SCRIPT_DIR, "state", tt, "kich_ban.json"), encoding="utf-8"))
            except Exception:                            # noqa: BLE001
                _kb_luu[tt] = {}
        v = _kb_luu[tt].get(pid)
        mau = list(v.get("mau") or []) if isinstance(v, dict) else []
        if not mau:
            if hoi_them >= 5:
                continue
            hoi_them += 1
            m, err = KB.tai_1_page(pid, tok)
            time.sleep(0.2)
            if err:
                continue
            mau = [KB._gon(x) for x in (m.get("mau") or [])]
            if not mau:
                continue
        mkey, n, dem = chon_thi_truong(mau, mk)
        if not mkey or mkey == tt:
            continue
        them.setdefault(mkey, {})[pid] = (
            f"{ten} — {mk[mkey].get('tien_te')} ({n} lần trong {len(mau)} mẫu) · LỆCH shop POS {tt} → {mkey} theo tiền tệ"
            f" · tự gắn {time.strftime('%d/%m/%Y')}")
        noi(f"  ➕ TỰ GẮN page {ten[:38]} (shop {tt}) → {mkey} theo tiền tệ ({mk[mkey].get('tien_te')}, {n} lần giá)"
            f" — AI {tt} bỏ page này" + ("" if that else " [chỉ xem]"))
    if not ngoai and not them:
        return 0, []
    for p in ngoai:
        pid, ten = str(p["id"]), (p.get("name") or pid)
        m, err = KB.tai_1_page(pid, tok)
        if err:
            cho_nguoi.append(f"{ten} — không kéo được kịch bản: {str(err)[:70]}")
            continue
        # 22/09 (ca Ellen Ella Make Up): tai_1_page trả mẫu THÔ {messages, shortcut…}; _chu_trong_mau đọc
        # dạng GỌN {tin, tu_khoa…} → bản cũ luôn ra chữ rỗng, chưa từng gắn được page nào. Gọn y như
        # ai_sale._keo_kich_ban_thieu.
        mau = [KB._gon(x) for x in (m.get("mau") or [])]
        if not mau:
            cho_nguoi.append(f"{ten} — 0 mẫu Trả lời nhanh (marketer soạn mẫu thì lượt sau tự gắn)")
            continue
        mkey, n, dem = chon_thi_truong(mau, mk)
        if not mkey:
            cho_nguoi.append(f"{ten} — {len(mau)} mẫu nhưng tiền tệ không rõ: "
                             + (str(dem) if dem else "không thấy giá mang tiền tệ"))
            continue
        them.setdefault(mkey, {})[pid] = (
            f"{ten} — {mk[mkey].get('tien_te')} ({n} lần trong {len(mau)} mẫu) · tự gắn "
            + time.strftime("%d/%m/%Y"))
        noi(f"  ➕ TỰ GẮN page mới {ten[:38]} → {mkey} ({mk[mkey].get('tien_te')}, {n} lần giá)"
            + ("" if that else " [chỉ xem]"))
        time.sleep(0.2)
    if them and that:
        _ghi_gan(them)
        noi(f"  ✅ ghi {sum(len(v) for v in them.values())} page vào page_gan_them.json — "
            "AI nhận ở lượt tra page kế tiếp rồi tự kéo kịch bản")
    for d in cho_nguoi:
        noi(f"  ⏸  page ngoài shop chưa gắn được: {d}")
    return (sum(len(v) for v in them.values()) if that else 0), cho_nguoi


def main():
    that = "--that" in sys.argv
    os.chdir(SCRIPT_DIR)
    print(f"[{time.strftime('%d/%m %H:%M')}] quét page mới ngoài shop thị trường"
          + (" — GHI THẬT" if that else " — chỉ xem"))
    n, _ = quet(that=that, in_ra=print)
    if not that:
        print("  (chạy lại với --that để ghi thật)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

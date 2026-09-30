"""Vá 19/09 — số trơn "1"/"2"/"وحده" trả lời ngay sau bảng giá = SỐ LƯỢNG khách chọn: ghi vào hồ sơ.

Chủ shop 19/09 (ca Fatima Miftah · ChunHo Golden Jewerly, khách "One" sau bảng giá): *"một ở đấy là số lượng khách muốn"*.
"One"/"Two"/"isa"/"واحد" thì HS.trich đã ghi so_luong; số trơn "1", "2", "٢", "وحده" thì KHÔNG (HS.trich chỉ đọc lời khách,
không biết ngữ cảnh) → AI rep nhưng hồ sơ trống số lượng → model có thể hỏi lại "chọn gói nào", đơn thiếu số lượng.
Sửa: hàm chung so_tron_sau_bang_gia(msgs); cmd_chay ghi co_moi["so_luong"] khi bắt được; cửa đổi treo→tra_loi dùng lại hàm.
Chạy: python3 va_so_tron_so_luong.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "def so_tron_sau_bang_gia" in src:
    sys.exit("đã vá rồi — không làm gì")
if "ca Fatima Miftah" not in src:
    sys.exit("thiếu vá va_chon_goi_ngan.py — vá cái đó trước")

HAM = r'''SO_TRON = re.compile(r"^\W*(?:[1-6]|[١-٦]|وحده|وحدة|واحده|واحدة|ثنتين|اثنين|اثنتين)\W*$")


def so_tron_sau_bang_gia(msgs):
    """19/09 (ca Fatima Miftah · ChunHo Golden Jewerly; chủ shop: "một ở đấy là số lượng khách muốn"): tin khách CUỐI
    là số trơn 1-6 / ١-٦ / "وحده"… và tin gần nhất phía page (Botcake/sale/AI) trước nó có bảng giá → trả nguyên chữ
    khách nói (= số lượng khách chọn), không thì None. HS.trich không bắt số trơn vì không có ngữ cảnh."""
    kh = [j for j, m in enumerate(msgs or []) if m.get("boi") == "khach"]
    if not kh:
        return None
    t = lam_sach(msgs[kh[-1]].get("text") or "").strip()
    if not SO_TRON.match(t):
        return None
    tr = next((m for m in reversed(msgs[:kh[-1]]) if m.get("boi") in ("botcake", "nguoi", "ai")), None)
    return t if tr is not None and CG.tien_trong(tr.get("text")) else None


def khach_vua_chon_goi(msgs, mkey, gia=None):
'''

VA = [
    ("def khach_vua_chon_goi(msgs, mkey, gia=None):\n", HAM),
    # cửa treo → tra_loi dùng lại hàm chung
    ('''                _tr_ = next((m for m in reversed(msgs) if m["boi"] in ("botcake", "nguoi", "ai")), None)
                _kh_ = next((lam_sach(m.get("text") or "").strip() for m in reversed(msgs) if m["boi"] == "khach"), "")
                if khach_vua_chon_goi(msgs, mkey, gia) or (
                        re.match(r"^\\W*(?:[1-6]|[١-٦]|وحده|وحدة|واحده|واحدة|ثنتين|اثنين|اثنتين)\\W*$", _kh_)
                        and _tr_ is not None and CG.tien_trong(_tr_.get("text"))):''',
     '''                if khach_vua_chon_goi(msgs, mkey, gia) or so_tron_sau_bang_gia(msgs):'''),
    # ghi số lượng vào hồ sơ
    ('''            co_moi = HS.trich(m_moi or msgs, mkey, gia, ten_khach)
''',
     '''            co_moi = HS.trich(m_moi or msgs, mkey, gia, ten_khach)
            # 19/09 (ca Fatima Miftah): số trơn "1"/"2"/"وحده" ngay sau bảng giá = số lượng khách chọn → ghi hồ sơ để
            # model khỏi hỏi lại "chọn gói nào" và đơn lên đúng số lượng (HS.trich chỉ đọc lời khách, không bắt số trơn).
            if "so_luong" not in co_moi:
                _sl_tron_ = so_tron_sau_bang_gia(msgs)
                if _sl_tron_:
                    co_moi["so_luong"] = f'khách nói: "{_sl_tron_}" (trả lời ngay sau bảng giá)'
'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:220]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ")

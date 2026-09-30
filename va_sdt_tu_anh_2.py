"""VÁ 3: mở đơn nháp từ ảnh DANH BẠ — nhưng KHÔNG từ ảnh vận đơn (2026-09-21).

Vá 2 đã đưa SĐT/địa chỉ đọc từ ảnh vào extract(), nhưng cửa mở đơn sớm chỉ xét hồ sơ dựng từ
chữ KHÁCH TỰ GÕ — khách chỉ gửi ảnh danh bạ rồi thôi thì vẫn không có đơn nào. Nối nốt cửa đó.

Rào — đo 21/09 trên 259 ảnh thật (Saudi 146 + UAE/Kuwait/Qatar/Bahrain 113):
  · 43 ảnh có SĐT. 5 ca số trong ảnh KHỚP số khách tự gõ (đáp án thật).
  · 22 ca khách CHƯA gõ số nào — đúng chỗ trước nay rơi mất.
  · nhưng nhiều ảnh trong đó là NHÃN VẬN ĐƠN của đơn ĐANG giao (iMile, Posta Plus, SMSA…):
    mở đơn mới từ đó là đơn TRÙNG. Nên ảnh vận đơn KHÔNG được mở đơn — số trong đó vẫn dùng
    để TRA POS chống trùng, và vẫn điền vào đơn nếu đơn đã mở vì lý do khác.

Chạy: python3 va_sdt_tu_anh_2.py [--that]
"""
import ast
import os
import shutil
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
F_AI = os.path.join(D, "ai_sale.py")

# ── 1. phân loại nguồn ảnh: danh bạ/hồ sơ (mở đơn được) hay vận đơn (không) ──────────
A1_CU = '''_TT_ANH = {}                          # url -> {"sdt": …, "dia_chi": …}'''
A1_MOI = '''# Ảnh NHÃN VẬN ĐƠN / bưu kiện: số trong đó có thể là của đơn ĐANG giao (hoặc của shipper),
# mở đơn mới từ đấy là đơn TRÙNG. Vẫn đọc số để TRA POS chống trùng, chỉ không cho mở đơn.
_ANH_VAN_DON = re.compile(
    r"shipping label|waybill|air ?way ?bill|courier|tracking|parcel|package|delivery label"
    r"|consignment|\\bimile\\b|posta|aramex|smsa|naqel|j&t|dhl|fedex|bosta", re.I)
_TT_ANH = {}                          # url -> {"sdt": …, "dia_chi": …, "nguon": "lien_he"|"van_don"}'''

A2_CU = '''def doc_tt_anh(url):'''
A2_MOI = '''def doc_tt_anh(url, mo_ta=""):'''

A3_CU = '''    _TT_ANH[url] = ra
    try:
        cu = qht.load_json(_f_tt_anh(), {}) or {}'''
A3_MOI = '''    if ra:
        ra["nguon"] = "van_don" if _ANH_VAN_DON.search(mo_ta or "") else "lien_he"
    _TT_ANH[url] = ra
    try:
        cu = qht.load_json(_f_tt_anh(), {}) or {}'''

A4_CU = '''                tt = doc_tt_anh(m["anh"][0])'''
A4_MOI = '''                tt = doc_tt_anh(m["anh"][0], t)'''

# ── 2. cửa mở đơn sớm: nhận cả SĐT/địa chỉ đọc từ ảnh DANH BẠ ────────────────────────
A5_CU = '''            if (not du_bao and cuoi and not khong_tao
                    and (ho_so_khach.get("sdt") or ho_so_khach.get("dia_chi"))
                    and som_dax.get(str(c["id"])) != cuoi["luc"]):'''
A5_MOI = '''            # Khách gửi SĐT/địa chỉ BẰNG ẢNH (21/09): hồ sơ dựng từ CHỮ nên rỗng, cửa này
            # đóng, không đơn nào mở ra. Nhận thêm thông tin đọc từ ảnh — nhưng chỉ ảnh DANH BẠ
            # / hồ sơ WhatsApp; ảnh NHÃN VẬN ĐƠN thì không (số của đơn đang giao → đơn trùng).
            try:
                _tt_a = tt_tu_anh_da_doc(msgs)
            except Exception:                            # noqa: BLE001 — sổ ảnh hỏng thì đi đường cũ
                _tt_a = {}
            _anh_mo_don = bool((_tt_a.get("sdt") or _tt_a.get("dia_chi"))
                               and _tt_a.get("nguon") != "van_don")
            if (not du_bao and cuoi and not khong_tao
                    and (ho_so_khach.get("sdt") or ho_so_khach.get("dia_chi") or _anh_mo_don)
                    and som_dax.get(str(c["id"])) != cuoi["luc"]):'''

# ── 3. tra POS chống trùng bằng cả số đọc từ ảnh (kể cả ảnh vận đơn) ─────────────────
A6_CU = '''                    # Tra POS ở đây CHỈ để chống đơn TRÙNG (daemon cũng dùng), không quyết chuyện chat.
                    roi_da_mua = da_mua_o_page(mkey, pid, c["id"], ho_so_khach.get("sdt"), ten_khach)'''
A6_MOI = '''                    # Tra POS ở đây CHỈ để chống đơn TRÙNG (daemon cũng dùng), không quyết chuyện chat.
                    # Tra bằng số khách gõ; không có thì bằng số ĐỌC TỪ ẢNH — đúng ca khách
                    # chụp nhãn vận đơn của đơn đang giao: tra ra đơn cũ thì không mở đơn mới.
                    roi_da_mua = da_mua_o_page(mkey, pid, c["id"],
                                               ho_so_khach.get("sdt") or _tt_a.get("sdt"), ten_khach)'''

VA = [A1_CU, A1_MOI], [A2_CU, A2_MOI], [A3_CU, A3_MOI], [A4_CU, A4_MOI], [A5_CU, A5_MOI], [A6_CU, A6_MOI]


def main():
    that = "--that" in sys.argv
    s = open(F_AI, encoding="utf-8").read()
    for i, (cu, moi) in enumerate(VA, 1):
        n = s.count(cu)
        assert n == 1, f"va {i}: {n} cho khop (phai dung 1)"
        s = s.replace(cu, moi, 1)
        print(f"  ✓ vá {i}/{len(VA)}")
    ast.parse(s)
    print("  ✓ cú pháp hợp lệ")
    if not that:
        print("(xem trước — thêm --that để ghi thật)")
        return
    bak = f"{F_AI}.bak-{time.strftime('%Y%m%d-%H%M')}-truoc-mo-don-tu-anh"
    shutil.copy2(F_AI, bak)
    open(F_AI, "w", encoding="utf-8").write(s)
    print(f"  ✓ ghi ai_sale.py · lưu {os.path.basename(bak)}")


main()

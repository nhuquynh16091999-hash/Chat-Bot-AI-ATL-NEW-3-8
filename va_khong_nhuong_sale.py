"""Vá 20/09 — KHÔNG NHƯỜNG SALE nữa. Chỉ nhường Botcake.

Chủ shop 20/09: *"k nhường sale, tôi dặn rồi"* — nhắc lại lời 17/09 tối: *"không nhường sale, bạn phụ sale,
phải trả lời thay sale; botcake trả lời đúng rồi thì mới không phải trả lời"*. ĐẢO lại lựa chọn 17/09
(AskUserQuestion mục 1: "sale gửi trước trong lúc AI soạn → AI VẪN BỎ câu") và cửa nhường của vá 19/09
(ca محمد جعفر · Al Shifa Denture Saudi).

Hai cửa nhường trong `_phan_hoi` (đều thuộc `ai_da_bi_vuot`):
  1. kiểm TRƯỚC khi gửi ảnh  — sale vừa rep trong lúc AI soạn
  2. kiểm SÁT lúc bấm gửi chữ — sale vừa rep lúc AI đợi nhịp gửi
Cả hai: sale → VẪN GỬI (đếm `khong_nhuong_sale`); Botcake → nhường như cũ; khách nhắn thêm → giữ nguyên
(hoãn, hoặc gửi chú thích nếu ảnh đã đi — vá va_anh_tro_khong_loi).

Đo log: nhường lúc soạn 340 lượt sale / 27 Botcake; lúc đợi nhịp gửi 3 lượt sale. Từ nay 343 lượt đó AI vẫn gửi.
KHÔNG đụng cửa "sale thật đã vào trả lời — không chen ngang" trong `ai_co_vao_cuoc` (sale đã rep TRƯỚC khi AI
vào cuộc; chủ shop chọn giữ 16/09) — muốn bỏ nốt thì phải sửa riêng.

Chạy: python3 va_khong_nhuong_sale.py ai_sale.py   (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "khong_nhuong_sale" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = [(
    # ── cửa 1: kiểm trước khi gửi ảnh ─────────────────────────────────────────
    '''        if vuot:
            print(f"{nhan} 🤝 {ai_vuot} vừa rep khách trong lúc AI soạn — nhường, không gửi")
            if dem is not None:
                dem["nhuong"] = dem.get("nhuong", 0) + 1
            if ai_vuot == "Botcake":
                _kh_ = [m for m in msgs_luc_soan if m.get("boi") == "khach"]
                danh_dau_da_xem(mkey, pid, conv_id, token, _kh_[-1] if _kh_ else None, that, nhan,
                                "Botcake rep trong lúc AI soạn", dang_doc=True)   # 19/09: qua cửa sale đã xem
            return True
''',
    '''        if vuot and ai_vuot == "Botcake":
            print(f"{nhan} 🤝 Botcake vừa rep khách trong lúc AI soạn — nhường, không gửi")
            if dem is not None:
                dem["nhuong"] = dem.get("nhuong", 0) + 1
            _kh_ = [m for m in msgs_luc_soan if m.get("boi") == "khach"]
            danh_dau_da_xem(mkey, pid, conv_id, token, _kh_[-1] if _kh_ else None, that, nhan,
                            "Botcake rep trong lúc AI soạn", dang_doc=True)       # 19/09: qua cửa sale đã xem
            return True
        if vuot:
            # KHÔNG NHƯỜNG SALE (chủ shop 20/09: *"k nhường sale, tôi dặn rồi"*, nhắc lại lời 17/09 tối
            # "bạn phụ sale, phải trả lời thay sale; botcake trả lời đúng rồi thì mới không phải trả lời").
            # Đảo lựa chọn 17/09 và cửa nhường của vá 19/09. Chỉ Botcake mới được nhường.
            print(f"{nhan} 🙋 {ai_vuot} vừa rep trong lúc AI soạn — KHÔNG nhường sale (chủ shop dặn), vẫn gửi")
            if dem is not None:
                dem["khong_nhuong_sale"] = dem.get("khong_nhuong_sale", 0) + 1
'''), (
    # ── cửa 2: kiểm sát lúc bấm gửi chữ ───────────────────────────────────────
    '''                else:
                    print(f"{nhan} 🤝 {ai_vuot} vừa rep khách lúc AI đợi nhịp gửi — nhường, không gửi chữ{_anh_}")
                    if dem is not None:
                        dem["nhuong"] = dem.get("nhuong", 0) + 1
                    if ai_vuot == "Botcake":
                        _kh_ = [m for m in msgs_luc_soan if m.get("boi") == "khach"]
                        danh_dau_da_xem(mkey, pid, conv_id, token, _kh_[-1] if _kh_ else None, that, nhan,
                                        "Botcake rep trong lúc AI soạn", dang_doc=True)
                    return True
''',
    '''                elif ai_vuot == "Botcake":
                    print(f"{nhan} 🤝 Botcake vừa rep khách lúc AI đợi nhịp gửi — nhường, không gửi chữ{_anh_}")
                    if dem is not None:
                        dem["nhuong"] = dem.get("nhuong", 0) + 1
                    _kh_ = [m for m in msgs_luc_soan if m.get("boi") == "khach"]
                    danh_dau_da_xem(mkey, pid, conv_id, token, _kh_[-1] if _kh_ else None, that, nhan,
                                    "Botcake rep trong lúc AI soạn", dang_doc=True)
                    return True
                else:
                    # sale chen vào lúc AI đợi nhịp gửi — chủ shop 20/09: không nhường sale, vẫn gửi câu đã soạn.
                    print(f"{nhan} 🙋 {ai_vuot} vừa rep lúc AI đợi nhịp gửi — KHÔNG nhường sale (chủ shop dặn), vẫn gửi")
                    if dem is not None:
                        dem["khong_nhuong_sale"] = dem.get("khong_nhuong_sale", 0) + 1
                    ok, e = gui_tin(pid, conv_id, token, tin, dry=not that, sau_anh=_da_gui_anh)
''')]

for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:150]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

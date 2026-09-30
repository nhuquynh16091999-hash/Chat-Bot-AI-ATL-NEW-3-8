"""Vá 20/09 — ẢNH ĐÃ ĐI thì chú thích phải đi theo, không được hoãn.

Ca Boqorada Banadir Al Banadir · Al Shifa Denture Saudi (chủ shop 20/09): lượt níu 2 gửi 6 ảnh mẫu
/Feedback lúc 10:32 rồi mới gửi câu "No worries at all 😊 Here's real feedback from customers who already
received theirs…". Giữa hai việc đó khách nhắn thêm "Ingalls", nên cửa `ai_da_bi_vuot` bắt được lúc
`gui_tin` kiểm lại → HOÃN CHỮ. Khách nhận đúng một chùm ảnh không một lời nào. *"sao gửi mỗi ảnh k dị"*.

Cửa kiểm "bị vượt" đã chạy TRƯỚC khi gửi ảnh (vá 14/09), nhưng gửi 6 ảnh mất ~12s — khe đó đủ để khách
nhắn thêm. Đã có luật "ảnh trơ không lời còn tệ hơn im" ở nhánh page bị FB chặn; nay áp cùng nguyên tắc
cho nhánh này: ảnh đã đi rồi thì vẫn gửi chú thích (một tin, đúng chùm ảnh vừa gửi), còn tin mới của khách
để lượt sau trả lời — hội thoại đã được đánh "cho" trong `_KHACH_NHAN_THEM` nên vòng sau đọc lại.
NHƯỜNG SALE/BOTCAKE giữ nguyên: sale vừa rep thì AI không chen, kể cả khi ảnh đã đi.

Đo log: 138 lượt gửi ảnh mẫu, 1 lượt rơi vào ca này (~0,7%).
Chạy: python3 va_anh_tro_khong_loi.py ai_sale.py   (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "chu_thich_theo_anh" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''                if ai_vuot == "khách":
                    print(f"{nhan} ✋ khách vừa nhắn thêm lúc AI đợi nhịp gửi — hoãn chữ, lượt sau trả lời gộp{_anh_}")
                    _nho_no_rep(mkey, conv_id, msgs_luc_soan, tin, nhan)
                    return True
                print(f"{nhan} 🤝 {ai_vuot} vừa rep khách lúc AI đợi nhịp gửi — nhường, không gửi chữ{_anh_}")
                if dem is not None:
                    dem["nhuong"] = dem.get("nhuong", 0) + 1
                if ai_vuot == "Botcake":
                    _kh_ = [m for m in msgs_luc_soan if m.get("boi") == "khach"]
                    danh_dau_da_xem(mkey, pid, conv_id, token, _kh_[-1] if _kh_ else None, that, nhan,
                                    "Botcake rep trong lúc AI soạn", dang_doc=True)
                return True
'''
MOI = '''                if ai_vuot == "khách" and _da_gui_anh:
                    # ẢNH ĐÃ ĐI: hoãn chữ nữa thì khách nhận mỗi chùm ảnh trơ không một lời nào (chủ shop
                    # 20/09, ca Boqorada Banadir · Al Shifa Denture Saudi: 6 ảnh /Feedback đi 10:32, chú
                    # thích bị hoãn vì khách nhắn "Ingalls" giữa chừng — *"sao gửi mỗi ảnh k dị"*). Cùng
                    # nguyên tắc "ảnh trơ không lời còn tệ hơn im" ở nhánh page bị FB chặn: chú thích đi
                    # theo ảnh, tin mới của khách để lượt sau (hội thoại đã vào _KHACH_NHAN_THEM → "cho").
                    print(f"{nhan} ✋🖼 khách nhắn thêm NHƯNG ảnh đã đi — vẫn gửi chú thích, lượt sau trả lời tin mới")
                    if dem is not None:
                        dem["chu_thich_theo_anh"] = dem.get("chu_thich_theo_anh", 0) + 1
                    ok, e = gui_tin(pid, conv_id, token, tin, dry=not that, sau_anh=True)
                elif ai_vuot == "khách":
                    print(f"{nhan} ✋ khách vừa nhắn thêm lúc AI đợi nhịp gửi — hoãn chữ, lượt sau trả lời gộp{_anh_}")
                    _nho_no_rep(mkey, conv_id, msgs_luc_soan, tin, nhan)
                    return True
                else:
                    print(f"{nhan} 🤝 {ai_vuot} vừa rep khách lúc AI đợi nhịp gửi — nhường, không gửi chữ{_anh_}")
                    if dem is not None:
                        dem["nhuong"] = dem.get("nhuong", 0) + 1
                    if ai_vuot == "Botcake":
                        _kh_ = [m for m in msgs_luc_soan if m.get("boi") == "khach"]
                        danh_dau_da_xem(mkey, pid, conv_id, token, _kh_[-1] if _kh_ else None, that, nhan,
                                        "Botcake rep trong lúc AI soạn", dang_doc=True)
                    return True
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

"""Vá 20/09 — page KHÔNG có ảnh feedback thì GHI CHÚ nhờ sale gửi.

Chủ shop 20/09: *"Nếu page nào k có note ghi chú bảo sale gửi ảnh feedback"*. Đo: 337 page có kịch bản,
164 page gửi được ảnh /Feedback → **173 page còn lại** khách xin feedback mà AI không có ảnh nào để gửi.

Khách xin feedback + AI không kèm được ảnh (page chưa có mẫu, hoặc có mẫu mà kênh ảnh tắt) → đặt
`qd["ghi_chu"]` để `_phan_hoi` ghi note cho sale. Câu note có chữ "gửi ảnh giúp" nên rơi đúng loại
`xin_anh` của `GHI_CHU_MOT_LAN` → mỗi hội thoại chỉ ghi MỘT lần, sale không phải đọc lại lời nhờ y hệt
([[ghi-chu-cung-loai-chi-1-lan]]). Khách vẫn nhận câu trả lời chữ như thường.

Chạy: python3 va_note_feedback.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "khách xin feedback, AI không có ảnh" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''                    qd = dict(qd, anh_mau=(_fbx_.get("tu_khoa") or "").strip())
                    print(f"{nhan} 🖼  khách xin feedback — kèm ảnh /{qd['anh_mau']}")
'''
MOI = '''                    qd = dict(qd, anh_mau=(_fbx_.get("tu_khoa") or "").strip())
                    print(f"{nhan} 🖼  khách xin feedback — kèm ảnh /{qd['anh_mau']}")
                # KHÔNG có ảnh để gửi → nhờ SALE gửi (chủ shop 20/09: *"nếu page nào k có note ghi chú bảo
                # sale gửi ảnh feedback"*). 173/337 page chưa có mẫu /Feedback nào dùng được. Câu note mang
                # chữ "gửi ảnh giúp" → loại `xin_anh`, mỗi hội thoại chỉ ghi một lần.
                if (not err_m and qd and khach_xin_feedback(msgs)
                        and not (qd.get("anh_mau") or "").strip() and not (qd.get("ghi_chu") or "").strip()):
                    _ly_ = ("kênh ảnh của page đang tắt" if mau_feedback(kb_page, msgs)
                            else "page chưa có mẫu ảnh Feedback")
                    qd = dict(qd, ghi_chu=f"khách xin feedback mà {_ly_} — sale gửi ảnh feedback giúp")
                    print(f"{nhan} 📝 khách xin feedback, AI không có ảnh — ghi chú nhờ sale ({_ly_})")
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

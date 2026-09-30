"""Vá 20/09 (nối va_note_feedback) — ghi chú 'sale gửi ảnh feedback giúp' phải là loại CHỈ GHI MỘT LẦN.

`GHI_CHU_MOT_LAN` chỉ có mẫu "xin ảnh" / "gửi ảnh giúp"; câu note mới có chữ "feedback" chen giữa
("sale gửi ảnh feedback giúp") nên `loai_ghi_chu` trả None → mỗi lượt khách nhắc lại là ghi thêm một note.
Thêm loại riêng `xin_feedback`.

Chạy: python3 va_loai_gc_fb.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "(\"xin_feedback\", re.compile" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''GHI_CHU_MOT_LAN = (
    ("xin_anh", re.compile(r"xin\\s*ảnh|gửi\\s*ảnh\\s*giúp", re.I)),
)
'''
MOI = '''GHI_CHU_MOT_LAN = (
    ("xin_anh", re.compile(r"xin\\s*ảnh|gửi\\s*ảnh\\s*giúp", re.I)),
    # 20/09: note nhờ sale gửi ảnh feedback (page chưa có mẫu /Feedback) — cùng kiểu "một lần/hội thoại".
    ("xin_feedback", re.compile(r"xin\\s*feedback|ảnh\\s*feedback", re.I)),
)
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

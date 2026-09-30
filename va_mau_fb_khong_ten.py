"""Vá 20/09 — nhận mẫu feedback cả khi câu trả lời nhanh KHÔNG đặt tên.

`mau_feedback` chỉ nhận mẫu có `tu_khoa` khớp "feedback". Nhưng Pancake trả `shortcut` rỗng cho rất nhiều
câu trả lời nhanh: đo 337 page — 176 page không có mẫu tên Feedback, trong đó 1.345 mẫu KHÔNG đặt tên.
Lọc theo nội dung + có ảnh thì tìm thêm được 4 mẫu feedback thật (Saudi 2, UAE 2).

Nhận thêm qua NỘI DUNG, và bắt buộc phải có ảnh: "feedback", "review", "happy/satisfied customers",
"received theirs", آراء/تقييم. KHÔNG lấy "lucky customers who can still secure…" (lời chào hàng).

Chạy: python3 va_mau_fb_khong_ten.py ai_sale.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_ND_FEEDBACK" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''def mau_feedback(kb_page, msgs):
    """Mẫu feedback CÓ ẢNH của page mà hội thoại chưa gửi (nhiều ảnh nhất trước), không có thì None."""
    ds = [m for m in (kb_page or {}).get("mau") or []
          if MAU_FEEDBACK.search(m.get("tu_khoa") or "") and m.get("anh") and (m.get("tu_khoa") or "").strip()]
    ds = [m for m in ds if not da_gui_huong_dan(msgs or [], m)]
    return max(ds, key=lambda m: len(m["anh"]), default=None)
'''
MOI = '''# Nội dung của một mẫu FEEDBACK khi câu trả lời nhanh không được đặt tên (Pancake trả shortcut rỗng cho
# 1.345 mẫu / 176 page — đo 20/09). Phải chặt: "lucky customers who can still secure…" là lời chào hàng.
_ND_FEEDBACK = re.compile(
    r"\\bfeed\\s*backs?\\b|\\breviews?\\b|\\btestimonial|\\b(?:happy|satisfied)\\s+(?:and\\s+|at\\s+)?(?:happy\\s+|satisfied\\s+)?"
    r"customers?\\b|\\breceived\\s+theirs\\b|آراء|تقييم", re.I | re.U)


def mau_feedback(kb_page, msgs):
    """Mẫu feedback CÓ ẢNH của page mà hội thoại chưa gửi (nhiều ảnh nhất trước), không có thì None.

    Ưu tiên mẫu ĐẶT TÊN "Feedback"; page không đặt tên mẫu thì dò theo NỘI DUNG (20/09, chủ shop:
    *"có thẻ feedback có nội dung và ảnh luôn r mà"* — đúng với 161/337 page, số còn lại mẫu không có tên).
    """
    mau = (kb_page or {}).get("mau") or []
    ds = [m for m in mau
          if MAU_FEEDBACK.search(m.get("tu_khoa") or "") and m.get("anh") and (m.get("tu_khoa") or "").strip()]
    if not ds:                       # không có mẫu đặt tên → dò nội dung, bắt buộc có ảnh
        ds = [m for m in mau if m.get("anh") and _ND_FEEDBACK.search(" ".join(m.get("tin") or []))]
    ds = [m for m in ds if not da_gui_huong_dan(msgs or [], m)]
    return max(ds, key=lambda m: len(m["anh"]), default=None)
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

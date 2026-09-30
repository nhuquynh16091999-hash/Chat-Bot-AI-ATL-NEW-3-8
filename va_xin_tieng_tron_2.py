"""Vá 20/09 (nối va_xin_tieng_tron) — "हिंदी" / "বাংলা" vẫn trượt: `[^\\w]` cắt luôn DẤU KẾT HỢP
(Unicode Mn) của chữ Devanagari/Bengali/Tamil… nên "हिंदी" vỡ thành "ह द" = 2 từ → không khớp bảng.
Giữ lại dấu kết hợp và chuẩn hoá NFC trước khi so.
Chạy: python3 va_xin_tieng_tron_2.py chan_gui.py
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "unicodedata" in src and "category(ch).startswith" in src:
    sys.exit("đã vá rồi — không làm gì")

CU = '''    s = re.sub(r"[\\u200b-\\u200f\\u0640\\u064b-\\u0652]", "", str(t or ""))
    goi = re.sub(r"[^\\w]+", " ", s, flags=re.U).strip().lower()
'''
MOI = '''    import unicodedata
    s = re.sub(r"[\\u200b-\\u200f\\u0640\\u064b-\\u0652]", "", unicodedata.normalize("NFC", str(t or "")))
    # Giữ DẤU KẾT HỢP (Mn): "हिंदी"/"বাংলা" mà cắt theo [^\\w] thì vỡ thành hai ba mảnh, không khớp bảng nào.
    goi = "".join(c if (c.isalnum() or unicodedata.category(c).startswith("M")) else " "
                  for c in s).strip().lower()
'''
n = src.count(CU)
if n != 1:
    sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì")
src = src.replace(CU, MOI)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá", f)

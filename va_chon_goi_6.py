"""Siết khach_vua_chon_goi — 3/3 lần 📦 chạy thật đầu tiên là bắt oan (khách còn hỏi/nghi ngờ)."""
import sys
f = "ai_sale.py"; s = open(f, encoding="utf-8").read()
a = ('    if not sau or any(HS.la_cau_hoi(x) or khach_dang_tu_choi(x) for x in sau):\n'
     '        return None\n'
     '    co = HS.trich([{"boi": "khach", "text": x} for x in sau], mkey, gia)\n'
     '    return " / ".join(sau)[:160] if co.get("so_luong") else None\n')
b = ('    if not sau or any(HS.la_cau_hoi(x) or khach_dang_tu_choi(x) or CON_NGHI.search(x) for x in sau):\n'
     '        return None\n'
     '    # Câu chọn gói phải NGẮN (≤ 8 từ) — đo chạy thật 14/09 chiều, 3/3 lần bắt đầu tiên là oan:\n'
     '    # "This one can use for fugal resh" (hỏi cách dùng), "1 bottle are you sure effective" (nghi ngờ),\n'
     '    # một câu Tigrinya 13 từ có "109" (hỏi cách dùng + hỏi giá). Khách còn hỏi/nghi thì để cửa khác trả lời.\n'
     '    chon = [x for x in sau if len(x.split()) <= 8\n'
     '            and HS.trich([{"boi": "khach", "text": x}], mkey, gia).get("so_luong")]\n'
     '    return " / ".join(sau)[:160] if chon else None\n')
c = 'TIN_CHOT_GOI_TOI_DA = 300\n'
d = ('TIN_CHOT_GOI_TOI_DA = 300\n'
     '# Khách còn HỎI cách dùng / NGHI hiệu quả → chưa phải chốt gói, dù có "1 bottle", "this one".\n'
     'CON_NGHI = re.compile(\n'
     '    r"\\b(?:use|used|using|usage|apply|question|options?|possible|show\\s+me|price|magkano|mgkano|mkano"\n'
     '    r"|halimbawa|haw|koto|effective|effect|results?|work(?:s|ing)?|sure|real|really|original|legit"\n'
     '    r"|fake|safe|side\\s*effects?|how|what|why|can|could|does|do\\s+you|is\\s+it|are\\s+you|ba|kaya|totoo"\n'
     '    r"|gamitin|gumagana|epektibo|hiyang)\\b|هل|كيف|فعال|مضمون|أصلي", re.I | re.U)\n')
for x, y in ((a, b), (c, d)):
    if s.count(x) != 1:
        sys.exit(f"✖ khớp {s.count(x)} lần — không ghi: {x[:60]!r}")
    s = s.replace(x, y)
open(f, "w", encoding="utf-8").write(s); print("✔ siết khach_vua_chon_goi")

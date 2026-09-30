"""Vá 20/09 — "কয় টাকা" (Bengali khẩu ngữ: bao nhiêu tiền), "koto real", "Dam koto vai", "magkanong po"
đều là HỎI GIÁ mà cả HOI_GIA lẫn _GIA_RE đều mù.

Ca Jahoir Islam · Nature's Daily Care in Saudi (chủ shop 20/09 10:19 VN): khách gõ "কয় টাকা"; luật chỉ
biết "কত টাকা" nên cổng "LƯỢT NÀY KHÔNG NÊU GIÁ" bật (page đã báo giá + khách "không hỏi giá") → AI dặn
model bỏ hết con số → câu trả lời không có giá nào, chỉ hỏi lại 1+1 hay 2+2. *"KHÁCH HỎI BAO NHIÊU TIỀN,
BẠN LẠI REP GÌ VẬY"*.

Quét cả HỌ biến thể trong sổ (bài học vá "how mych" 19/09), không vá mỗi chữ khách vừa gõ:
  Bengali  : কয় + đơn vị tiền · প্রাইজ (price gõ j) · দম (দাম gõ thiếu)
  Latin BN : koto/koy + taka/tk/real/riyal · "dam koto" (KHÔNG lấy "dam" trơn — khách Philippines gõ
             "dam" thay "ma'am": "Okay dam", "sa pinas po yan dam")
  Tagalog  : magkano gõ dính đuôi — "magkanong po?", "magkanonpoh", "mgkanonpo" (đuôi ≤4 chữ để không
             nuốt "magkanina" = lúc nãy)
Đo trên 108.785 dòng sổ so_chi_phi + so_viec: mẫu mới khớp thêm 14 lượt / 8 câu, soát tay 8/8 đúng là hỏi
giá, 0 câu oan.

Chạy: python3 va_gia_koy_taka.py /opt/pancake-tool/ai_sale.py /root/thu_gia_giao/khoi_gia_giao_v3.py
"""
import sys

f_ai, f_v3 = sys.argv[1], sys.argv[2]
src_ai = open(f_ai, encoding="utf-8").read()
src_v3 = open(f_v3, encoding="utf-8").read()
if "koy\\s*(?:taka" in src_ai:
    sys.exit("đã vá rồi — không làm gì")

_LATIN = (r"|magkano\w{0,4}|mgkano\w{0,4}|kot[oa]\s*(?:taka|tk|real|riyal|rial|riyel|dirham)"
          r"|koy\s*(?:taka|tk|real|riyal|rial)|(?:daam|dam)\s+kot[oa]")

VA_CHUNG = [(
    '''           r"|m[ae]?g\\s*k[ae]{0,2}\\s*n[ou0p]?|mgkno|magkno|mag\\s*kano|presyo|pila|harga\\w*|hrga|berapa|brapa|brpa|brp|berspa"
''',
    '''           r"|m[ae]?g\\s*k[ae]{0,2}\\s*n[ou0p]?|mgkno|magkno|mag\\s*kano|presyo|pila|harga\\w*|hrga|berapa|brapa|brpa|brp|berspa"
           # 20/09 (ca Jahoir Islam): Bengali gõ chữ Latinh + magkano dính đuôi. "dam" trơn KHÔNG tính —
           # khách Philippines gõ "dam" thay "ma'am" ("Okay dam", "sa pinas po yan dam").
           r"''' + _LATIN + '''"
'''), (
    '''                r"|দাম|মূল্য|প্রাইস|কতো|কত"
''',
    '''                r"|দাম|মূল্য|প্রাইস|প্রাইজ|কতো|কত|কয়\\s*(?:টাকা|টেকা|রিয়াল|রিয়েল|করে)"
''')]

VA_AI = [(
    '''    r"|দাম|মূল্য|প্রাইস|কতো?\\s*(?:টাকা|রিয়াল|রিয়েল|দিরহাম|করে)"
''',
    '''    r"|দাম|দম|মূল্য|প্রাইস|প্রাইজ|(?:কতো?|কয়)\\s*(?:টাকা|টেকা|রিয়াল|রিয়েল|দিরহাম|করে)"
'''), (
    '''    r"|pila|combo|promo|promos|offer|offers|deal|deals|package|packages|bundle|bundles"
''',
    '''    r"|pila''' + _LATIN + '''|combo|promo|promos|offer|offers|deal|deals|package|packages|bundle|bundles"
''')]

for f, src, va in ((f_ai, src_ai, VA_CHUNG + VA_AI), (f_v3, src_v3, VA_CHUNG)):
    for cu, moi in va:
        n = src.count(cu)
        if n != 1:
            sys.exit(f"❌ {f}: khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:120]}")
        src = src.replace(cu, moi)
    compile(src, f, "exec")
    open(f, "w", encoding="utf-8").write(src)
    print(f"✔ đã vá {f}")

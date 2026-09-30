"""Vá 20/09 — SALE REP RỒI: đủ ý thì thôi, chưa đủ thì AI BỔ SUNG; sale chưa gửi thì AI vẫn gửi.

Chủ shop 20/09: *"sale rep xong, đủ ý rồi thì thôi, nếu chưa đủ ý thì bạn bổ sung, còn ví dụ sale chưa gửi
thì bạn vẫn phải gửi chứ"*. Trước vá `ai_co_vao_cuoc` có một cửa CHẶN CỨNG ngay đầu hàm: có tin "nguoi" sau
tin khách cuối → "im — sale thật đã vào trả lời, không chen ngang" — im mù, không đọc câu sale.

Nay tin sale đi CÙNG ĐƯỜNG với tin Botcake: luật cứng chặn phần rõ ràng (tin khách không có gì cần đáp
riêng, page đã báo giá bằng con số, page đã xin tên/SĐT/địa chỉ, tin mẫu QC, chỉ hỏi giá), còn lại vào cửa
"xet" để model đọc — sale trúng ý thì im, thiếu thì bổ sung (không lặp lại điều sale đã nói).

Đo 24h/173 page: 771 hội thoại đang bị cửa cũ chặn — 382 ca luật cứng vẫn im (0 đồng), 389 ca sẽ vào "xet".
Ví dụ ca đáng bổ sung: khách "how much?" → sale "Will you choose the buy 1 get 1 or buy 2 get 2?" (không có
con số); khách "I want to know the price of Varicose Vein Relief Cream" → sale nói chuyện khan hiếm, không giá.

Chạy: python3 va_sale_du_y.py ai_sale.py   (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "SALE ĐÃ REP: KHÔNG im mù" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = [
    # 1. bỏ cửa chặn cứng đầu hàm
    ('''    if "nguoi" in sau:
        return "im", "sale thật đã vào trả lời — không chen ngang"
''',
     '''    # SALE ĐÃ REP: KHÔNG im mù nữa (chủ shop 20/09: *"sale rep xong, đủ ý rồi thì thôi, nếu chưa đủ ý
    # thì bạn bổ sung, còn ví dụ sale chưa gửi thì bạn vẫn phải gửi chứ"*). Tin sale đi cùng đường với tin
    # Botcake ở các cửa bên dưới: luật cứng chặn phần rõ ràng, còn lại model đọc xem sale đủ ý chưa.
'''),
    # 2. tin mẫu quảng cáo
    ('''        if "botcake" in sau:
            return "im", "tin mẫu quảng cáo (how much/start/hm) — Botcake đã rep, AI không vào"
''',
     '''        if "botcake" in sau or "nguoi" in sau:
            return "im", "tin mẫu quảng cáo (how much/start/hm) — page đã rep, AI không vào"
'''),
    # 3. chỉ hỏi giá / mấy ngày giao
    ('''        if "botcake" in sau:
            return "im", f"khách chỉ hỏi {_ten} — Botcake đã rep, AI không vào (chủ shop 19/09: tiết kiệm)"
''',
     '''        if "botcake" in sau or "nguoi" in sau:
            return "im", f"khách chỉ hỏi {_ten} — page đã rep, AI không vào (chủ shop 19/09: tiết kiệm)"
'''),
    # 4-5-6. các cửa "page chưa rep" phải tính cả sale
    ('''    _tc0 = tinh_huong_tu_choi(msgs) if "botcake" not in sau else None
''',
     '''    _tc0 = tinh_huong_tu_choi(msgs) if ("botcake" not in sau and "nguoi" not in sau) else None
'''),
    ('''    if HEN_SAU.search(chu) and "botcake" not in sau:
''',
     '''    if HEN_SAU.search(chu) and "botcake" not in sau and "nguoi" not in sau:
'''),
    ('''    if "botcake" not in sau and (TU_CHOI.search(hai_tin) or (page_vua_hoi(msgs, i)
''',
     '''    if "botcake" not in sau and "nguoi" not in sau and (TU_CHOI.search(hai_tin) or (page_vua_hoi(msgs, i)
'''),
    # 7. nhánh "page đã đáp" — nhận cả sale
    ('''    if "botcake" in sau:
        # Botcake đã đáp. TRƯỚC khi tốn một lượt model, chặn bằng hai luật chắc chắn.
''',
     '''    if "botcake" in sau or "nguoi" in sau:
        # Botcake HOẶC SALE đã đáp. TRƯỚC khi tốn một lượt model, chặn bằng hai luật chắc chắn.
'''),
    ('''        bot_sau = [m for m in msgs[i + 1:] if m["boi"] == "botcake"]
''',
     '''        bot_sau = [m for m in msgs[i + 1:] if m["boi"] == "botcake"]
        # 20/09: các luật "page đã báo giá / đã xin thông tin" xét CẢ tin sale — sale cũng là page.
        # Riêng luật "≥2 tin bot liên tiếp" vẫn chỉ đếm Botcake (nó chống chuỗi follow-up tự động).
        page_sau = [m for m in msgs[i + 1:] if m["boi"] in ("botcake", "nguoi")]
        _ai_rep = "sale" if "nguoi" in sau else "Botcake"
'''),
    ('''                CG.tien_trong(m.get("text")) for m in bot_sau) \\
                and not _nghi_gia:
            return "im", "khách hỏi giá / hỏi có phải mua không, Botcake đã báo giá bằng con số — không nhắn đè"
''',
     '''                CG.tien_trong(m.get("text")) for m in page_sau) \\
                and not _nghi_gia:
            return "im", f"khách hỏi giá / hỏi có phải mua không, {_ai_rep} đã báo giá bằng con số — không nhắn đè"
'''),
    ('''        if any(_bot_da_xin_tt(m.get("text")) for m in bot_sau) and not _khach_con_dieu_can_dap(_chuoi_kh):
            return "im", "Botcake đã xin tên/SĐT/địa chỉ, khách không hỏi gì thêm — AI không xin lại lần hai"
''',
     '''        if any(_bot_da_xin_tt(m.get("text")) for m in page_sau) and not _khach_con_dieu_can_dap(_chuoi_kh):
            return "im", f"{_ai_rep} đã xin tên/SĐT/địa chỉ, khách không hỏi gì thêm — AI không xin lại lần hai"
'''),
    ('''        if not _chuoi_co_nd and not _nghi_gia:
            return "im", "khách chỉ chào/đáp ngắn — Botcake đã rep là đủ, không cần đọc lại"
''',
     '''        if not _chuoi_co_nd and not _nghi_gia:
            return "im", f"khách chỉ chào/đáp ngắn — {_ai_rep} đã rep là đủ, không cần đọc lại"
'''),
    ('''        return "xet", "Botcake đã trả lời — đọc xem có trúng câu khách hỏi không"
''',
     '''        return "xet", f"{_ai_rep} đã trả lời — đọc xem đủ ý chưa; thiếu thì bổ sung, đủ thì im"
'''),
    # 8. prompt cửa "xet" — nói cho model biết người rep có thể là nhân viên sale
    ('''        "xet": "Botcake ĐÃ trả lời tin cuối của khách. Việc của bạn là PHÁN: câu bot có đụng tới "
''',
     '''        "xet": "PAGE (Botcake hoặc nhân viên sale) ĐÃ trả lời tin cuối của khách. Việc của bạn là PHÁN: câu đó có đụng tới "
'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:160]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ trong {f}")

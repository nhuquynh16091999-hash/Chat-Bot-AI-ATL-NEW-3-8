"""Vá cmd_theo_doi: bỏ lượt chỉ có tin sale + xếp hàng khách nhắn trước (14/09, ca EsOr Adz).

Chạy: python3 va_xep_hang.py ai_sale.py   — mỗi chỗ phải khớp ĐÚNG 1 lần, không thì thoát không ghi.
"""
import sys

f = sys.argv[1]
s = open(f, encoding="utf-8").read()
if "AI_XA_MOI_LUOT" in s:
    sys.exit("đã vá rồi — không làm gì")

VA = []

VA.append((
    "    da_thay, nong = {}, {}\n",
    "    da_thay, nong = {}, {}\n"
    "    dem_tin, loai, cho_xu = {}, {}, set()   # message_count lần thấy trước · ai gửi cuối · nóng mà chưa xử lần nào\n",
))

VA.append((
    "        moi = set()\n",
    "        moi = set()\n"
    "        bo_sale = 0\n",
))

VA.append((
    """                da_thay[cid] = moc
""",
    """                da_thay[cid] = moc
                n_tin, n_truoc = c.get("message_count"), dem_tin.get(cid)
                if isinstance(n_tin, int):
                    dem_tin[cid] = n_tin
                loai[cid] = ai_g
""",
))

VA.append((
    """                if ai_g != "nguoi" or c.get("has_phone") or c.get("recent_phone_numbers"):
                    moi.add(cid)
""",
    """                # CHỈ CÓ TIN SALE MỚI thì khỏi đọc (14/09, ca EsOr Adz — Saudi): hội thoại đổi mà
                # message_count chỉ nhích ≤1 và người gửi cuối là sale → cái mới duy nhất là câu của
                # sale (hoặc đổi thẻ), phía khách không có gì mới. Lượt khách nhắn trước đó đã được
                # đưa vào `nong` từ lúc nó tới. Trước vá: Saudi 203/464 lượt xét là loại này (khách
                # nhắn từ >10 phút trước, sale nhắn xác nhận đơn "Đã gửi" → AI đọc lại rồi im),
                # vòng dò phình 88-295s, khách mới phải đợi 5-7 phút. Nhích ≥2 (khách + sale lọt
                # cùng một nhịp — ca Barbara Sarmiento) thì vẫn đọc như cũ.
                if (ai_g == "nguoi" and isinstance(n_tin, int) and isinstance(n_truoc, int)
                        and n_tin - n_truoc <= 1):
                    bo_sale += 1
                    continue
                if ai_g != "nguoi" or c.get("has_phone") or c.get("recent_phone_numbers"):
                    moi.add(cid)
""",
))

VA.append((
    """        for cid in moi:
            nong[cid] = time.time()
        # hội thoại nóng quá 5 phút mà vẫn "cho" thì bỏ — Botcake/sale đã xử, đừng bám mãi
        for cid in [k for k, v in nong.items() if time.time() - v > 300]:
            nong.pop(cid, None)
        if nong:
            print(f"  🔥 {len(moi)} tin mới · đang theo {len(nong)} hội thoại", flush=True)
            try:
                kq = cmd_chay(mkey, gio=gio, so=so, that=that, cho=cho, dong_bo=False,
                              chi_hoi_thoai=set(nong), pages_san=pages,
""",
    """        for cid in moi:
            nong[cid] = time.time()
            cho_xu.add(cid)
        # hội thoại nóng quá 5 phút mà vẫn "cho" thì bỏ — Botcake/sale đã xử, đừng bám mãi.
        # Còn trong hàng chờ (chưa xử lần nào) thì KHÔNG bỏ, không thì rơi mất khách.
        for cid in [k for k, v in nong.items() if time.time() - v > 300 and k not in cho_xu]:
            nong.pop(cid, None)
        # XẾP HÀNG (14/09, ca EsOr Adz): cmd_chay xử tuần tự, 60 hội thoại/lượt thì khách hỏi giá
        # đứng sau 60 cái đó. Khách/bot gửi cuối ("gần") xử hết mỗi lượt; sale gửi cuối ("xa" — chỉ
        # còn việc lên đơn nháp, chat thì AI im) xử tối đa AI_XA_MOI_LUOT cái cũ nhất, lượt vắng
        # khách thì AI_XA_MOI_LUOT_RANH cái.
        gan = {k for k in nong if loai.get(k) != "nguoi"}
        xa = sorted((k for k in nong if k not in gan), key=lambda k: nong[k])
        tran_xa = int(_so_env("AI_XA_MOI_LUOT", 8) if gan else _so_env("AI_XA_MOI_LUOT_RANH", 25))
        lam = gan | set(xa[:tran_xa])
        if lam:
            print(f"  🔥 {len(moi)} tin mới · đang theo {len(nong)} hội thoại · lượt này {len(gan)} khách/bot"
                  f" + {min(len(xa), tran_xa)}/{len(xa)} sale vừa gửi"
                  + (f" · bỏ {bo_sale} lượt chỉ có tin sale" if bo_sale else ""), flush=True)
            cho_xu -= lam
            try:
                kq = cmd_chay(mkey, gio=gio, so=so, that=that, cho=cho, dong_bo=False,
                              chi_hoi_thoai=set(lam), pages_san=pages,
""",
))

for cu, moi in VA:
    n = s.count(cu)
    assert n == 1, f"khớp {n} lần (phải 1): {cu[:80]!r}"
    s = s.replace(cu, moi)
open(f, "w", encoding="utf-8").write(s)
print("✔ vá xong", len(VA), "chỗ")

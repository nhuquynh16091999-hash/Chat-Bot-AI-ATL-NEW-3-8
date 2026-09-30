"""Vá 19/09 — khách bị ĐẨY KHỎI TOP `so` khi page bắn tin hàng loạt thì AI rơi mất khách.

Ca Shiela Maromoto · ClearVision Eye Care Saudi: khách nhắn 10:01:57 VN "I'm in the Philippines now".
Cùng lúc page bắn tin quảng cáo hàng loạt (10:01-10:03, 40+ hội thoại). Vòng dò (API gộp, unread_first)
THẤY khách, giao cho cmd_chay. Nhưng cmd_chay hỏi lại danh sách của page theo updated_at rồi cắt
[:so]=12 → 12 hội thoại vừa bị bắn tin chiếm hết chỗ, Shiela nằm ngoài → bị lọc im lặng → cuối hàm
ket_qua.setdefault(cid, "xong") → vòng dò thôi theo, chốt chặn ⏰ 3 phút cũng không báo. Không một dòng
log, không một dòng sổ. Sale Từ Trang tự rep 10:06:41.

Vá: vòng dò gửi kèm bản ghi hội thoại của đúng những việc nó giao (ban_ghi_san); hội thoại nào được giao
mà danh sách hỏi lại không còn chứa thì lấy bản ghi đó để xử, không bỏ.
Chạy: python3 va_bi_day_khoi_top.py ai_sale.py   (khớp khác 1 lần ở bất kỳ chỗ nào → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "ban_ghi_san" in src:
    sys.exit("đã vá rồi (có ban_ghi_san) — không làm gì")

VA = [
    ("             cho_theo_page=None):",
     "             cho_theo_page=None, ban_ghi_san=None):"),
    ('''        convs, err = hoi_thoai_gan_day(pid, st["token"], so=so, gio=gio)
        if chi_hoi_thoai is not None:
            convs = [c for c in convs if c["id"] in chi_hoi_thoai]
        tin = {}''',
     '''        convs, err = hoi_thoai_gan_day(pid, st["token"], so=so, gio=gio)
        if chi_hoi_thoai is not None:
            convs = [c for c in convs if c["id"] in chi_hoi_thoai]
            # 19/09 (ca Shiela Maromoto · ClearVision Eye Care Saudi): page bắn tin quảng cáo hàng
            # loạt 40+ hội thoại trong 1 phút → hỏi lại danh sách theo updated_at rồi cắt [:so] thì
            # khách vừa nhắn bị đẩy ra ngoài, lọc im lặng, cuối hàm thành "xong" → không AI, không ⏰.
            # Việc vòng dò đã giao thì phải xử: không còn trong danh sách → dùng bản ghi của vòng dò.
            if not err and ban_ghi_san:
                _co_ = {c["id"] for c in convs}
                _bu_ = [dict(ban_ghi_san[k]) for k in chi_hoi_thoai
                        if k not in _co_ and k in ban_ghi_san and str(k).startswith(str(pid) + "_")]
                if _bu_:
                    print(f"  ↪ {st.get('name', '?')[:40]} — {len(_bu_)} hội thoại bị đẩy khỏi top {so} "
                          f"(page vừa bắn tin hàng loạt) — lấy bản ghi vòng dò để xử", flush=True)
                    convs += _bu_
        tin = {}'''),
    ("                                    cho_theo_page=cho_theo_page)] = (set(lam), time.time())",
     "                                    cho_theo_page=cho_theo_page,\n"
     "                                    ban_ghi_san={k: thong_tin[k] for k in lam if k in thong_tin}"
     ")] = (set(lam), time.time())"),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:120]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("✔ đã vá 3 chỗ")

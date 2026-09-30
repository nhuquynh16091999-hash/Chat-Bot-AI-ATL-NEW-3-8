import sys
f = sys.argv[1]
s = open(f, encoding="utf-8").read()
if "_THE_TEN_PAGE" in s:
    sys.exit("đã vá rồi")
cu = """    convs = res.get("conversations") or []
    for c in convs:
        cu = ((c.get("customers") or [{}])[0] or {}).get("id")
        if cu:
            _CUST[(str(page_id), str(c.get("id")))] = cu
"""
moi = """    convs = res.get("conversations") or []
    ten_the = _the_ten_page_user(page_id) if any(
        isinstance(t, int) for c in convs for t in (c.get("tags") or [])) else {}
    for c in convs:
        cu = ((c.get("customers") or [{}])[0] or {}).get("id")
        if cu:
            _CUST[(str(page_id), str(c.get("id")))] = cu
        # API nội bộ trả thẻ dạng SỐ ([-9, 3, 6, 44]) chứ không phải {id, text} như Public API →
        # the_noi_da_xong ném lỗi, cửa thẻ "Đã gửi" mù ở MỌI page chạy bằng tài khoản (14/09 ca
        # Sweetrose Torres, Mario Jewelry Kuwait: thẻ Đã gửi + đơn #14374 mà AI vẫn chat 10+ tin).
        # Đổi số ra {id, text} theo settings.tags của page.
        c["tags"] = [({"id": t, "text": ten_the.get(t)} if isinstance(t, int) else t)
                     for t in (c.get("tags") or [])]
"""
assert s.count(cu) == 1, s.count(cu)
s = s.replace(cu, moi)
cu2 = """def _customer_id_user(page_id, conv_id):"""
moi2 = """_THE_TEN_PAGE = {}    # pid -> ({id thẻ: tên}, lúc hỏi) — settings.tags qua API nội bộ


def _the_ten_page_user(page_id):
    cu = _THE_TEN_PAGE.get(str(page_id))
    if cu and time.time() - cu[1] < 600:
        return cu[0]
    res, err = _get(f"{WEB_API}/pages/{page_id}/settings", {"access_token": _tok_user()})
    tags = [] if (err or not res) else (res.get("tags") or (res.get("settings") or {}).get("tags") or [])
    bang = {t.get("id"): t.get("text") for t in tags if isinstance(t, dict)}
    if not bang and cu:
        return cu[0]                      # hỏi hỏng → dùng bảng cũ, đừng làm mù cửa thẻ
    if not bang:
        print(f"     ⚠️  không đọc được tên thẻ page {page_id}: {err} — cửa thẻ Đã gửi mù ở page này")
    _THE_TEN_PAGE[str(page_id)] = (bang, time.time())
    return bang


def _customer_id_user(page_id, conv_id):"""
assert s.count(cu2) == 1, s.count(cu2)
s = s.replace(cu2, moi2)
open(f, "w", encoding="utf-8").write(s)
print("vá xong")

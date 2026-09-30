"""Vá 18/09 — AI CHỈ TRÔNG PAGE CÒN GÓI CƯỚC (chủ shop: "hiện tại tôi đang có 168 page hoạt động ở pan, chỉ cần
xử lý các page tôi đang hoạt động là được"). Chạy: python3 va_chi_page_con_goi.py ai_sale.py"""
import sys
f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "def _bang_con_goi" in src:
    sys.exit("đã vá rồi — không làm gì")
VA = [(
    "def _pages_cua_thi_truong(mkey, page_loc=None):\n",
    "_CON_GOI = {\"luc\": 0.0, \"bang\": None}\n"
    "\n"
    "\n"
    "def _bang_con_goi():\n"
    "    \"\"\"{pid: còn gói cước?} theo danh sách page của tài khoản AI trên Pancake; nhớ 10 phút.\n"
    "    Hỏi hỏng → bảng cũ (hoặc None = không lọc gì, giữ như trước).\"\"\"\n"
    "    if _CON_GOI[\"bang\"] is not None and time.time() - _CON_GOI[\"luc\"] < 600:\n"
    "        return _CON_GOI[\"bang\"]\n"
    "    tok_user = env().get(\"PANCAKE_USER_TOKEN\", \"\")\n"
    "    if not tok_user:\n"
    "        return None\n"
    "    res, err = _get(\"https://pages.fm/api/v1/pages\", {\"access_token\": tok_user})\n"
    "    ps = [] if (err or not res) else (res.get(\"pages\") or (res.get(\"categorized\") or {}).get(\"activated\") or [])\n"
    "    if not ps:\n"
    "        return _CON_GOI[\"bang\"]\n"
    "    _CON_GOI.update(luc=time.time(), bang={str(p[\"id\"]): bool(p.get(\"has_active_subscription\")) for p in ps})\n"
    "    return _CON_GOI[\"bang\"]\n"
    "\n"
    "\n"
    "def _pages_cua_thi_truong(mkey, page_loc=None):\n",
), (
    "    if gui_qua_user_bat():\n"
    "        # Page thuộc shop, còn gói, tài khoản AI thấy nhưng KHÔNG có token page → chạy bằng tài khoản.\n",
    "    # 18/09 — CHỈ TRÔNG PAGE CÒN GÓI CƯỚC (chủ shop: \"hiện tại tôi đang có 168 page hoạt động ở pan, chỉ cần\n"
    "    # xử lý các page tôi đang hoạt động\"). page_tokens.json còn giữ token cũ của page hết gói: AI dò 304 page mà\n"
    "    # chỉ 167 còn gói — 137 page chết vẫn bị hỏi Pancake mỗi 6s. Nguồn: danh sách page của tài khoản AI\n"
    "    # (has_active_subscription). Page không có trong danh sách cũng bỏ. Hỏi hỏng thì KHÔNG lọc.\n"
    "    _goi = _bang_con_goi()\n"
    "    if _goi is not None:\n"
    "        _bo = [x for x in ds if not _goi.get(str(x[0]))]\n"
    "        if _bo:\n"
    "            ds = [x for x in ds if _goi.get(str(x[0]))]\n"
    "            print(f\"  ⏸  bỏ {len(_bo)} page hết gói cước / không còn trên Pancake — còn {len(ds)} page có token (page chạy bằng tài khoản tính riêng bên dưới)\")\n"
    "    if gui_qua_user_bat():\n"
    "        # Page thuộc shop, còn gói, tài khoản AI thấy nhưng KHÔNG có token page → chạy bằng tài khoản.\n",
)]
for cu, moi in VA:
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần (cần đúng 1) — KHÔNG ghi:\n{cu[:120]}"
for cu, moi in VA:
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"đã vá {len(VA)} chỗ")

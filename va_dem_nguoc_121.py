import sys, shutil, time
f = sys.argv[1]
s = open(f, encoding="utf-8").read()
if "def _con_goi_that(" in s:
    sys.exit("đã vá rồi — không làm gì")
thay = [
    ("def _bang_con_goi():\n",
     "def _con_goi_that(p):\n"
     "    \"\"\"Page còn gói VÀ tài khoản AI dùng được. 19/09 đo 478 page: 50 page has_active_subscription=true\n"
     "    nhưng có deactivation_days_left (3/6/7 ngày) — hỏi hội thoại cả 50 đều trả mã 121 \"Không tìm thấy gói\n"
     "    cước\". Chỉ tính page KHÔNG đếm ngược: ra 170 page, khớp chủ shop \"hơn 170 page hoạt động ở pan\".\"\"\"\n"
     "    return bool(p.get(\"has_active_subscription\")) and p.get(\"deactivation_days_left\") is None\n"
     "\n\n"
     "def _bang_con_goi():\n"),
    ("bang={str(p[\"id\"]): bool(p.get(\"has_active_subscription\")) for p in ps})",
     "bang={str(p[\"id\"]): _con_goi_that(p) for p in ps})"),
    ("str(p[\"id\"]) not in co and p.get(\"has_active_subscription\")]",
     "str(p[\"id\"]) not in co and _con_goi_that(p)]"),
]
for a, b in thay:
    n = s.count(a)
    assert n == 1, f"khớp {n} lần (cần 1): {a[:60]!r} — KHÔNG ghi"
    s = s.replace(a, b)
bak = f + time.strftime(".bak-%Y%m%d-%H%M-truoc-dem-nguoc-121")
shutil.copy2(f, bak)
open(f, "w", encoding="utf-8").write(s)
print("đã vá, bak:", bak)

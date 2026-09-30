import sys, re
s = open(sys.argv[1], encoding="utf-8").read()
CA = [
 ("1 · _get thử lại 429",
  r'def _get\(url, params, thu_lai=2\):[\s\S]{0,1400}?if lan < thu_lai and \("429" in loi or "Too Many Requests" in loi\):[\s\S]{0,120}?time\.sleep\(1 \+ lan\)'),
 ("2 · đọc tin hỏng giữ nóng + in lý do",
  r'if e or not msgs:[\s\S]{0,900}?ket_qua\[str\(c\["id"\]\)\] = "cho"[\s\S]{0,400}?không đọc được tin'),
 ("3 · số luồng đọc chỉnh được",
  r'max_workers=max\(1, int\(_so_env\("AI_LUONG_DOC", 5\)\)\)'),
 ("4 · cửa gác thôi nuốt lỗi",
  r'convs_pg, err_pg = \(da_doc\.get\(pid\) or \(\[\], None, \{\}\)\)\[:2\][\s\S]{0,200}?if chi_hoi_thoai is not None and not convs_pg and not err_pg:'),
 ("5 · lấy ds hỏng giữ nóng cả page",
  r'KHÔNG lấy được hội thoại[\s\S]{0,600}?for cid_ in \(chi_hoi_thoai or \(\)\):[\s\S]{0,200}?ket_qua\[str\(cid_\)\] = "cho"'),
]
xau = 0
for ten, pat in CA:
    ok = re.search(pat, s) is not None
    print(f"  {'✅' if ok else '❌'} {ten}")
    xau += (not ok)
# _post KHONG duoc thu lai
post_an_toan = "thu_lai" not in s.split("def _post")[1].split("def ")[0]
print(f"  {'✅' if post_an_toan else '❌'} 6 · _post KHÔNG thử lại (không gửi trùng cho khách)")
xau += (not post_an_toan)
print()
print("KET LUAN:", "ca 5 va con nguyen" if not xau else f"{xau} CHO HONG")
sys.exit(1 if xau else 0)

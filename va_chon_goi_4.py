import sys
def thay(f,a,b):
    s=open(f,encoding="utf-8").read()
    if s.count(a)!=1: sys.exit(f"✖ {f} khớp {s.count(a)}: {a[:60]!r}")
    open(f,"w",encoding="utf-8").write(s.replace(a,b))
thay("luat_model.md",
 'Khuôn đúng: "Noted <tên khách> 😊 <tên gói> — <số lượng nhận> for <giá đúng bảng>. Please send your full\n'
 'name, contact number and complete address so I can book your order." (viết bằng tiếng khách dùng)\n',
 'Khuôn đúng: "Noted <tên khách> 😊 <tên gói> — <số lượng nhận> for <giá đúng bảng>. Can you send your full\n'
 'name, contact number and complete address so I can book your order?" (viết bằng tiếng khách dùng, kết bằng câu hỏi)\n')
thay("ho_so.py",
 '                      r"|\\bb[1-4]\\s*[gt][1-4]\\b", re.I)\n',
 '                      r"|\\bb[1-4]\\s*[gt][1-4]\\b|\\b[1-4]\\s*(?:get|take)\\s*[1-4]\\b", re.I)\n')
thay("ai_sale.py",
 '"tin_nhan tối đa 2 câu, đúng tiếng khách: (1)',
 '"tin_nhan tối đa 2 câu, đúng tiếng khách, kết bằng câu hỏi: (1)')
print("✔")

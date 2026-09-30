import sys
f="luat_model.md"; s=open(f,encoding="utf-8").read()
a=('Ví dụ đúng: "Noted Gha 😊 Buy 1 Get 1 Free — 2 items for 109 SAR. Please send your full name, contact\n'
   'number and complete address so I can book your order."\n')
b=('Khuôn đúng: "Noted <tên khách> 😊 <tên gói> — <số lượng nhận> for <giá đúng bảng>. Please send your full\n'
   'name, contact number and complete address so I can book your order." (viết bằng tiếng khách dùng)\n')
if s.count(a)!=1: sys.exit(f"✖ khớp {s.count(a)}")
open(f,"w",encoding="utf-8").write(s.replace(a,b)); print("✔ đổi ví dụ thành khuôn")

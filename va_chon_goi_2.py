import sys
f="ai_sale.py"; s=open(f,encoding="utf-8").read()
cap=[('def khach_vua_chon_goi(msgs, gia=None):\n','def khach_vua_chon_goi(msgs, mkey, gia=None):\n'),
     ('    co = HS.trich([{"boi": "khach", "text": x} for x in sau], None, gia)\n','    co = HS.trich([{"boi": "khach", "text": x} for x in sau], mkey, gia)\n'),
     ('_goi_ = khach_vua_chon_goi(msgs, gia) if quyet','_goi_ = khach_vua_chon_goi(msgs, mkey, gia) if quyet')]
for a,b in cap:
    if s.count(a)!=1: sys.exit(f"✖ khớp {s.count(a)} lần: {a!r}")
    s=s.replace(a,b)
open(f,"w",encoding="utf-8").write(s); print("✔ sửa mkey")

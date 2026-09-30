#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Luật 20/09 (sửa gấp): không đưa số của mình KHÔNG có nghĩa là chối việc bên mình nhắn WhatsApp."""
import shutil

CU_VN = '- Khách hỏi "số kia có phải WhatsApp của shop không?" → đừng xác nhận số cũ; xin số của khách rồi mình nhắn trước.\n'
MOI_VN = ('- Khách nói "bên bạn vừa nhắn tôi trên WhatsApp" / hỏi "số kia có phải của shop không" → ĐỪNG CHỐI: nhân viên bên mình\n'
          '  CÓ nhắn khách qua WhatsApp. Công nhận ngắn gọn rồi làm tiếp việc đang dở ở đây (xin vị trí / SĐT / chốt gói); không\n'
          '  xác nhận số cụ thể, không đưa số mới.\n'
          '- ⛔ CẤM chối: "hindi po ako ang nag-message sa WhatsApp", "that wasn\'t me", "bên mình không dùng WhatsApp" — khách\n'
          '  đang nói chuyện với đúng shop mà bị chối thì mất tin ngay (ca Marry F Mamauag 20/09).\n')

CU_EN = '- Customer asks "is that number your WhatsApp?" → don\'t confirm the old number; ask for theirs and message them first.\n'
MOI_EN = ('- Customer says "you just messaged me on WhatsApp" / asks "is that number yours?" → DO NOT DENY IT: our staff DO message\n'
          '  customers on WhatsApp. Acknowledge it briefly, then carry on with what you were doing here (location / phone number /\n'
          '  bundle); don\'t confirm any specific number and don\'t hand out a new one.\n'
          '- ⛔ Never deny it: "hindi po ako ang nag-message sa WhatsApp", "that wasn\'t me", "we don\'t use WhatsApp" — the customer\n'
          '  is talking to the right shop; denying costs their trust instantly.\n')

for f, cu, moi in (("/opt/pancake-tool/luat/00_chung.md", CU_VN, MOI_VN),
                   ("/opt/pancake-tool/luat_en/00_chung.md", CU_EN, MOI_EN)):
    s = open(f, encoding="utf-8").read()
    n = s.count(cu)
    assert n == 1, f"{f}: mốc {n} lần — DỪNG"
    shutil.copy2(f, f + ".bak-20260920-truoc-khong-choi")
    open(f, "w", encoding="utf-8").write(s.replace(cu, moi, 1))
    print("  ✓", f)

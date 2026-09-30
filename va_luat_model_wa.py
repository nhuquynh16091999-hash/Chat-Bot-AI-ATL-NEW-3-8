#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bản luật nguyên khối (dùng khi AI_LUAT_TACH=0) cũng phải theo luật WhatsApp mới — 20/09."""
import shutil

F = "/opt/pancake-tool/luat_model.md"
CU = """- ✅ Xin khách GỬI ĐỊNH VỊ ngay: gửi vị trí Google Maps vào đây, HOẶC gửi qua WhatsApp — CHỈ đưa link/số WhatsApp khi kịch bản
  hoặc tin page trong hội thoại đã có (vd "https://wa.link/…", "wa.me/…"), không có thì chỉ xin gửi định vị ở đây. Kèm xin số
  điện thoại nếu còn thiếu. Một tin, 1-2 câu, đúng tiếng khách.
  Mẫu: "No problem 😊 Just send me your Google Maps location here (or on WhatsApp) with your contact number — I'll book it now so
  you don't miss today's promo."
"""
MOI = """- ✅ Xin khách GỬI ĐỊNH VỊ ngay: gửi vị trí Google Maps vào thẳng khung chat này, kèm xin số điện thoại nếu còn thiếu.
  Một tin, 1-2 câu, đúng tiếng khách.
  Mẫu: "No problem 😊 Just send me your Google Maps location here with your contact number — I'll book it now so
  you don't miss today's promo."
- ⛔ SỐ WHATSAPP CỦA SHOP ĐÃ NGƯNG (chủ shop 20/09): CẤM gửi khách link/số WhatsApp nào của mình, dù kịch bản hay tin page cũ có
  ("wa.me/…", "wa.link/…"). Khách xin WhatsApp → XIN SỐ WHATSAPP CỦA KHÁCH, nói mình nhắn cho khách ngay ở đó; cũng CẤM hứa
  "I'll send you my WhatsApp number".
  Mẫu: "Sure 😊 What's your WhatsApp number? I'll message you there right away so you can share your location — or just send it
  here, that works too."
"""
s = open(F, encoding="utf-8").read()
n = s.count(CU)
assert n == 1, f"mốc xuất hiện {n} lần — DỪNG"
shutil.copy2(F, F + ".bak-20260920-truoc-wa-ngung")
open(F, "w", encoding="utf-8").write(s.replace(CU, MOI, 1))
print("  ✓", F)

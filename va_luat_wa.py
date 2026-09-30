#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VÁ LUẬT 2026-09-20 — số WhatsApp của shop đã ngưng: không đưa số của mình, xin số của KHÁCH.

Cố ý KHÔNG viết số cụ thể vào luật: nêu ra là mồi cho model chép lại. Chặn số cụ thể là việc
của WA_SHOP trong ai_sale.py.
"""
import shutil

VN = "/opt/pancake-tool/luat/00_chung.md"
EN = "/opt/pancake-tool/luat_en/00_chung.md"

CU_VN = """  khách: xin gửi vị trí Google Maps vào đây, HOẶC qua WhatsApp — chỉ đưa link / số WhatsApp khi kịch bản hoặc tin page trong hội
  thoại đã có ("wa.link/…", "wa.me/…"); không có thì chỉ xin gửi định vị ở đây. Kèm xin contact number nếu còn thiếu.
  Mẫu: "No problem 😊 Just send me your Google Maps location here (or on WhatsApp) with your contact number — I'll book it now so
  you don't miss today's promo."
"""
MOI_VN = """  khách: xin gửi vị trí Google Maps ngay trong khung chat này, kèm xin contact number nếu còn thiếu.
  Mẫu: "No problem 😊 Just send me your Google Maps location here with your contact number — I'll book it now so
  you don't miss today's promo."

SỐ WHATSAPP CỦA SHOP ĐÃ NGƯNG (chủ shop 20/09) — CẤM gửi khách bất kỳ link / số WhatsApp nào của mình, dù kịch bản, tin page cũ
trong hội thoại hay khách đòi ("wa.me/…", "wa.link/…", số kèm chữ WhatsApp). Số đó không còn ai nhận: khách nhắn vào là mất đơn.
- Khách xin WhatsApp / muốn gửi vị trí qua WhatsApp → XIN SỐ WHATSAPP CỦA KHÁCH, nói mình sẽ nhắn cho khách ngay ở đó.
  Mẫu: "Sure 😊 What's your WhatsApp number? I'll message you there right away so you can share your location — or just send it
  here, that works too."
- ⛔ CẤM hứa "I'll send you my WhatsApp number" / "check ko po ang WhatsApp namin" — không còn số nào để đưa.
- Khách hỏi "số kia có phải WhatsApp của shop không?" → đừng xác nhận số cũ; xin số của khách rồi mình nhắn trước.
"""

CU_EN = """  sentences in the customer's language: ask them to send their Google Maps location here, OR via WhatsApp — give a WhatsApp link /
  number only if the script or the page's messages in this chat already have one ("wa.link/…", "wa.me/…"); otherwise only ask for
  the location here. Also ask for the contact number if still missing.
  Sample: "No problem 😊 Just send me your Google Maps location here (or on WhatsApp) with your contact number — I'll book it now so
  you don't miss today's promo."
"""
MOI_EN = """  sentences in the customer's language: ask them to send their Google Maps location right here in this chat, and the contact
  number too if it is still missing.
  Sample: "No problem 😊 Just send me your Google Maps location here with your contact number — I'll book it now so
  you don't miss today's promo."

THE SHOP'S WHATSAPP NUMBER IS DEAD (owner, 20/09) — NEVER give the customer any WhatsApp link or number of ours, no matter what
the script says, what older page messages in this chat say, or how hard the customer asks ("wa.me/…", "wa.link/…", any number
next to the word WhatsApp). Nobody reads it: a customer who writes there is a lost order.
- Customer asks for WhatsApp / wants to send the location on WhatsApp → ASK FOR THE CUSTOMER'S OWN WHATSAPP NUMBER and say you
  will message them there right away.
  Sample: "Sure 😊 What's your WhatsApp number? I'll message you there right away so you can share your location — or just send it
  here, that works too."
- ⛔ Never promise "I'll send you my WhatsApp number" / "check ko po ang WhatsApp namin" — there is no number left to give.
- Customer asks "is that number your WhatsApp?" → don't confirm the old number; ask for theirs and message them first.
"""

for f, cu, moi in ((VN, CU_VN, MOI_VN), (EN, CU_EN, MOI_EN)):
    s = open(f, encoding="utf-8").read()
    n = s.count(cu)
    assert n == 1, f"{f}: mốc xuất hiện {n} lần (phải đúng 1) — DỪNG"
    shutil.copy2(f, f + ".bak-20260920-truoc-wa-ngung")
    open(f, "w", encoding="utf-8").write(s.replace(cu, moi, 1))
    print(f"  ✓ {f}")

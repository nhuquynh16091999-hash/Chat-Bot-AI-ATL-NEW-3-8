#!/usr/bin/env python3
"""Tự gửi 1 tin XÁC NHẬN ĐƠN cho khách landing nhắn WhatsApp (kênh nối Pancake), thay tin chào mừng tự động trong app.

Chủ shop 29/09/2026: tin "Thank you for your order…" tự động trong APP bị ❗ (không gửi được) từ ~14:00 VN, dán y hệt cho
mọi khách → *"câu xác nhận đơn đó nên để AI chat với khách trên pan hơn là để tự động ở whatsapp"* → *"vậy bạn làm cho mình nhé"*.

Luật:
  - Chỉ kênh trong KENH (Xophia +84 357 407 840). Gửi qua API nội bộ Pancake (reply_inbox) bằng PANCAKE_USER_TOKEN → đi Cloud API.
  - Chỉ khi tin khách là tin landing (R_XN_LADI: "Order confirmation" / "confirm my order" / تأكيد الطلب),
    SAU tin đó page CHƯA gửi gì, tin đó ≥ CHO_GIAY (khách còn nhắn tiếp) và ≤ TOI_DA_GIO (còn trong 24 giờ của Meta).
  - Mỗi hội thoại 1 lần (sổ state/xac_nhan_wa.json) — không nhắn tiếp, không trả lời câu hỏi; phần sau nhân viên lo trong app.
  - Tin có tên khách + sản phẩm + tổng tiền + địa chỉ đọc từ tin landing, mỗi khách 1 câu hơi khác (không dán y hệt).
    Tin tiếng Ả Rập → trả lời tiếng Ả Rập. Không hứa số ngày giao.
PHẦN 2 — AI TRẢ LỜI TIẾP (chủ shop 29/09, ảnh khách "This is legit?" không ai đáp: *"sao b thả trôi tin nhắn vậy"* → chọn
  cho AI chat tiếp trên WhatsApp). Chỉ hội thoại CÓ tin landing (khách đã đặt), tin cuối là của khách, page chưa đáp, khách im
  ≥ CHO_GIAY, ≤ TOI_DA_GIO, không có thẻ AI CHAT (sale gắn = AI ngưng). Model (DeepSeek, .env AI_MODEL) chọn:
  reply (trả lời theo luật shop: hàng thật, COD tiền mặt, kiểm hàng trước khi trả, ngày giao theo nước…) ·
  handoff (đổi/huỷ đơn, khiếu nại, ảnh/voice, không chắc → để nhân viên, đánh lại chưa đọc) · none ("ok", "thanks").
  Tối đa AI_TOI_DA tin AI/hội thoại/ngày. Tắt riêng phần 2: XN_WA_AI_TAT=1.
  - Tắt nhanh: XN_WA_TAT=1 trong .env. Chạy: python3 xac_nhan_wa.py [--xem]  (--xem = chỉ in, không gửi, không ghi sổ).
"""
import os
import re
import sys
import json
import time
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import care_don_wa as C  # noqa: E402  (http_json, _env, WEB_API)

DIR = os.path.dirname(os.path.abspath(__file__))
KENH = ["waba_1344618785398918"]          # Xophia +84 357 407 840
SO = os.path.join(DIR, "state", "xac_nhan_wa.json")
LOG = os.path.join(DIR, "state", "xac_nhan_wa.log")
XEM = "--xem" in sys.argv
CHO_GIAY = 60
TOI_DA_GIO = 23
R_XN_LADI = re.compile(r"order\s*confirmation|confirm\s+my\s+order|تأكيد\s*(?:ال)?طلب", re.I)
R_ARAP = re.compile(r"[\u0600-\u06FF]")
THE_AI_CHAT_ID = 6                           # th\u1EBB "AI CHAT" tr\u00EAn k\u00EAnh Xophia \u2014 sale g\u1EAFn = AI ng\u01B0ng
AI_TOI_DA = 8
NGAY_GIAO = {"SAUDI": "3-7 days", "UAE": "2-5 days", "KUWAIT": "2-5 days", "QATAR": "2-5 days", "OMAN": "2-5 days",
             "BAHRAIN": "2-5 days"}
TIEN_NUOC = [(r"SAR|\u0631\.?\s?\u0633|\u0631\u064A\u0627\u0644\s*\u0633\u0639\u0648\u062F\u064A", "SAUDI"), (r"AED|Dhs?|\u062F\.?\s?\u0625|\u062F\u0631\u0647\u0645", "UAE"), (r"KWD|KD|\u062F\.?\s?\u0643", "KUWAIT"),
             (r"QAR|QR|\u0631\.?\s?\u0642", "QATAR"), (r"OMR|\u0631\.?\s?\u0639", "OMAN"), (r"BHD|BD|\u062F\.?\s?\u0628", "BAHRAIN")]
TIEN = r"SAR|AED|Dhs?|KWD|KD|QAR|QR|OMR|BHD|BD|ر\.?\s?س|د\.?\s?إ|د\.?\s?ك|ر\.?\s?ق|ر\.?\s?ع|د\.?\s?ب|ريال|درهم|دينار"


def ghi(s):
    dong = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {s}"
    print(dong)
    if not XEM:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(dong + "\n")


def post(url, params, body):
    import urllib.parse, urllib.request, urllib.error
    rq = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                data=urllib.parse.urlencode(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(rq, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8") or "{}")
        return d, (None if d.get("success", True) else str(d)[:200])
    except urllib.error.HTTPError as e:
        try:
            return None, f"HTTP {e.code} {e.read().decode('utf-8')[:200]}"
        except Exception:  # noqa: BLE001
            return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:120]


def _gio(s):
    try:
        return datetime.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=datetime.timezone.utc).timestamp()
    except Exception:  # noqa: BLE001
        return None


def truong(chu, *ten):
    """Giá trị dòng 'Tên: …' đầu tiên khớp (không phân biệt hoa thường)."""
    for t in ten:
        m = re.search(rf"^\W*{t}\s*\*?\s*[:：]\s*(.+)$", chu, re.I | re.M)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


def ten_goi(ten):
    """Tên để chào: chữ đầu của tên, bỏ nếu trông như gõ bừa ('gfbccbb')."""
    tu = (ten or "").split()
    if not tu:
        return ""
    t = tu[0].strip(".,'-")
    if R_ARAP.search(t):
        return t if len(t) >= 2 else ""
    if not re.fullmatch(r"[A-Za-zÀ-ÿ'-]{2,20}", t) or not re.search(r"[aeiouyAEIOUY]", t):
        return ""
    return t[:1].upper() + t[1:].lower()


def tong_tien(chu):
    """'Buy 1 Get 1: 109 SAR+ Free shipping (SALE 50%)' → ('Buy 1 Get 1', '109 SAR')."""
    t = truong(chu, "Total Amount", "Total", "المجموع", "الإجمالي", "المبلغ الإجمالي")
    m = re.search(rf"(\d[\d.,]*)\s*({TIEN})|({TIEN})\s*(\d[\d.,]*)", t, re.I)
    if not m:
        return "", ""
    tien = f"{m.group(1)} {m.group(2)}" if m.group(1) else f"{m.group(4)} {m.group(3)}"
    goi = t.split(":")[0].strip() if ":" in t[: m.start()] else ""
    return (goi if re.search(r"buy|get|\d", goi, re.I) and len(goi) <= 30 else ""), tien.upper() if not R_ARAP.search(tien) else tien


def dia_chi(chu):
    dc = truong(chu, "Address", "العنوان")
    if not dc:
        phan = [truong(chu, k) for k in ("Building / Villa / House No.", "House / Apartment", "Street", "Block No.",
                                          "District / Area", "City", "Governorate")]
        m = re.search(r"^Building / Villa / House No\.?\s*(.+)$", chu, re.I | re.M)   # dòng này hay thiếu dấu ':'
        if m and not phan[0]:
            phan[0] = m.group(1).strip()
        dc = ", ".join(p for p in phan if p)
    return re.sub(r"\s+", " ", dc)[:160]


def soan(chu, khoa):
    """Tin xác nhận từ tin landing của khách. Không đủ sản phẩm → None (để nhân viên lo)."""
    sp = re.sub(r"^\d{2,4}\s*[-–]\s*", "", truong(chu, "Product", "المنتج"))[:80]
    if not sp:
        return None
    ten = ten_goi(truong(chu, "Name", "الاسم"))
    goi, tien = tong_tien(chu)
    dc = dia_chi(chu)
    k = int(hashlib.md5(khoa.encode()).hexdigest(), 16)
    if len(R_ARAP.findall(chu)) > len(re.findall(r"[A-Za-z]", chu)):          # tin landing tiếng Ả Rập
        chao = f"مرحباً {ten} 🌷" if ten else "مرحباً 🌷"
        dong = [chao, f"شكراً لطلبك، لقد استلمنا طلبك بنجاح ✅", f"المنتج: {sp}"]
        if tien:
            dong.append(f"المبلغ: {tien}" + (f" ({goi})" if goi else "") + " — شحن مجاني")
        if dc:
            dong.append(f"العنوان: {dc}")
        dong += ["", "الدفع نقداً عند الاستلام 💵 وسيتصل بك المندوب قبل التوصيل 📞",
                 "إذا أردت تعديل أي معلومة، فقط أرسل لنا هنا.", "يرجى حفظ رقمنا للتواصل بسهولة ❤️"]
        return "\n".join(dong)
    chao = [f"Hi {ten}! 😊" if ten else "Hi! 😊", f"Hello {ten} 🌷" if ten else "Hello 🌷",
            f"Dear {ten}, thank you 🙏" if ten else "Thank you 🙏"][k % 3]
    nhan = ["We have received your order ✅", "Your order has been received ✅", "We got your order, thank you ✅"][(k // 3) % 3]
    dong = [chao, nhan, "", f"🛍 Product: {sp}"]
    if tien:
        dong.append(f"💰 Total: {tien}" + (f" ({goi})" if goi else "") + " — free shipping")
    if dc:
        dong.append(f"📍 Address: {dc}")
    dong.append("")
    dong.append(["You pay in cash when it arrives (COD). The courier will call you before delivery 📞",
                 "Payment is cash on delivery. Our courier will call you before delivering 📞",
                 "Please prepare cash to pay when you receive it. The courier will call you first 📞"][(k // 9) % 3])
    dong.append(["If anything needs to change, just reply here.", "Need to change something? Just send us a message here.",
                 "If any detail is wrong, please tell us here."][(k // 27) % 3])
    dong.append(["Please save our number so you can reach us easily ❤️", "Please save this number to contact us anytime ❤️",
                 "Save our number so you don't miss the courier's updates ❤️"][(k // 81) % 3])
    return "\n".join(dong)


def nuoc_don(chu):
    t = truong(chu, "Total Amount", "Total", "المجموع", "الإجمالي", "المبلغ الإجمالي")
    for mau, n in TIEN_NUOC:
        if re.search(rf"\d[\d.,]*\s*(?:{mau})(?![A-Za-z])|(?<![A-Za-z])(?:{mau})\s*\d", t, re.I):
            return n
    c = truong(chu, "Country").upper().replace("KSA", "SAUDI")
    return next((n for n in NGAY_GIAO if n[:4] in c), "")


def chu_tin(m):
    t = re.sub(r"<[^>]+>", "", (m.get("original_message") or m.get("message") or "")).strip()
    loai = {str(a.get("type")) for a in m.get("attachments") or [] if isinstance(a, dict) and a.get("type")}
    if loai and not t:
        return "[" + "/".join(sorted(loai)) + "]"
    return t


LUAT_AI = """You answer WhatsApp messages for an online shop. Every customer here ALREADY placed an order on our website;
the order details are below. A confirmation message was already sent. You only help with questions about THIS order.
Output ONLY a JSON object:
{"action": "reply" | "handoff" | "none", "reply": "<message to send, empty unless action=reply>", "why": "<Vietnamese, 1 short line>"}

Choose:
- "none": the customer only says thanks / ok / emoji / "noted" and needs no answer.
- "handoff" (a staff member will answer): customer wants to CANCEL, change product/quantity/package/price, change the
  ADDRESS or phone, complains about a received item, asks for refund/return, sends only a photo/voice/file, asks about a
  different product or a new purchase, asks something you cannot answer from the facts below, or you are unsure.
- "reply": everything else you can answer truthfully from these facts:
  * Genuine / legit / real? Yes - 100% original product, and they can open and check the item before paying the courier.
  * Payment: CASH ONLY to the courier on delivery. No card, no bank transfer, no online payment. Nothing to pay now.
  * Delivery time: DELIVERY_TIME. NEVER promise today/tomorrow or a specific date.
  * The courier calls the customer before delivering. If the customer gives preferred times ("my duty is 2pm-11pm"),
    say the courier will call before coming so they can arrange the time together. Do not promise a fixed time.
  * Can I return it to the courier if I don't like it? Only say they can open and check the item before paying the
    courier. Do NOT promise returns or refunds, and do NOT say returns are impossible - do not mention returns at all.
  * "Can you deliver tomorrow / today?" -> say delivery takes DELIVERY_TIME and the courier calls before coming;
    never say tomorrow/today will happen.
  * Free shipping. The total is exactly the order total below - never change it, never offer discounts or extra items.
  * Where is it made: cosmetics / skin / hair products -> Korea; gold jewellery -> Saudi Arabia; anything else -> handoff.
  * Greeting only ("hi", "hello") -> greet back and ask how you can help with their order.
  * General product use: only very general, safe advice for the product type; no numbers, sizes, ingredients,
    medical or health claims - if they need specifics -> handoff.
Style: reply in the SAME language the customer writes in (English, Arabic, Tagalog, Hindi/Urdu in Latin letters...).
Short: 1-3 short lines, warm, at most 1 emoji, "dear" at most once. Never say you are AI or a bot. Never ask again for
name/phone/address. Never promise "we will check and get back to you". Never write links or phone numbers."""

R_CAM_REP = re.compile(r"https?://|www\.|\+?\d[\d\s-]{7,}|\brefunds?\b|\bmoney back\b"
                       r"|\bget back to you\b|\b(?:i am|i'm) (?:an? )?(?:ai|bot)\b|\bpay (?:by|with) card\b", re.I)
# hứa giao hôm nay/mai — trừ khi có chữ phủ định ngay trước ("we can't promise tomorrow")
R_HUA_SOM = re.compile(r"(?<!n't promise )(?<!not promise )(?<!cannot promise )\b(?:tomorrow|today)\b|غد[اًا]|\bbukas\b", re.I)


def hoi_ai(env, chu_don, lich_su, nuoc):
    """→ (action, reply, why); action None = gọi model hỏng (why = lỗi)."""
    import urllib.request
    key = env.get("DEEPSEEK_API_KEY") or ""
    if not key:
        return None, None, "thiếu DEEPSEEK_API_KEY"
    he = LUAT_AI.replace("DELIVERY_TIME", NGAY_GIAO.get(nuoc) or "2-7 days")
    nd = (f"ORDER (customer's own website message):\n{chu_don}\n\nCountry: {nuoc or 'unknown'}\n\n"
          f"CONVERSATION (oldest first; the last CUSTOMER lines are the new messages to answer):\n{lich_su}")
    body = {"model": env.get("AI_MODEL") or "deepseek-flash", "max_tokens": 500, "system": he,
            "messages": [{"role": "user", "content": nd}]}
    rq = urllib.request.Request("https://api.deepseek.com/anthropic/v1/messages", data=json.dumps(body).encode(),
                                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                         "content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(rq, timeout=90) as r:
            d = json.loads(r.read().decode("utf-8"))
        txt = "".join(b.get("text", "") for b in d.get("content") or [] if b.get("type") == "text")
        m = re.search(r"\{.*\}", txt, re.S)
        j = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001
        return None, None, str(e)[:150]
    a = str(j.get("action") or "").lower()
    rep = str(j.get("reply") or "").strip()
    if a not in ("reply", "handoff", "none") or (a == "reply" and not rep):
        return None, None, f"model trả lạ: {txt[:150]}"
    if a == "reply" and (R_CAM_REP.search(rep) or R_HUA_SOM.search(rep)):
        return "handoff", "", f"cổng chặn câu model: {rep[:120]}"
    return a, rep, str(j.get("why") or "")


def tra_loi_tiep(env, tok, pid, c, ds, vt, so, chua_doc, bay_gio):
    """PHẦN 2: khách đã đặt (có tin landing), vừa nhắn thêm mà page chưa đáp → AI trả lời / để nhân viên / thôi."""
    cid = c["id"]

    def tra_chua_doc():
        if chua_doc and not XEM:
            post(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/mark_unread", {"access_token": tok}, {})

    if env.get("XN_WA_AI_TAT") == "1" or vt is None or not ds or la_page(ds[-1], pid):
        if not XEM:
            so["bo"][cid] = c.get("updated_at")
        return tra_chua_doc()
    st = so["ai"].get(cid) or {}
    cuoi = str(ds[-1].get("id"))
    if st.get("moc") == cuoi:
        if not XEM:
            so["bo"][cid] = c.get("updated_at")
        return tra_chua_doc()
    if time.time() - (_gio(ds[-1].get("inserted_at")) or 0) < CHO_GIAY:
        return tra_chua_doc()                             # khách còn đang nhắn — lượt sau
    if THE_AI_CHAT_ID in (c.get("tags") or []):
        ghi(f"⏸ {cid}: thẻ AI CHAT — nhân viên đang lo, AI im")
        if not XEM:
            so["ai"][cid] = dict(st, moc=cuoi, luc=int(bay_gio))
        return tra_chua_doc()
    hom_nay = time.strftime("%Y-%m-%d")
    dem = st.get("dem", 0) if st.get("ngay") == hom_nay else 0
    if dem >= AI_TOI_DA:
        ghi(f"⏸ {cid}: đã {dem} tin AI hôm nay — để nhân viên")
        if not XEM:
            so["ai"][cid] = dict(st, moc=cuoi, luc=int(bay_gio))
        return tra_chua_doc()
    chu_don = ds[vt].get("original_message") or ds[vt].get("message") or ""
    lich_su = "\n".join(("SHOP: " if la_page(m, pid) else "CUSTOMER: ") + chu_tin(m)[:600]
                        for m in ds[max(vt + 1, len(ds) - 14):] if chu_tin(m))
    a, rep, why = hoi_ai(env, chu_don, lich_su, nuoc_don(chu_don))
    ten = (c.get("from") or {}).get("name") or cid[-12:]
    moi = " | ".join(chu_tin(m)[:80] for m in ds[-3:] if not la_page(m, pid))
    if a is None:
        ghi(f"✖ {ten}: gọi model hỏng {why} — lượt sau thử lại")
        return tra_chua_doc()
    if XEM:
        ghi(f"[XEM] {ten}: «{moi}» → {a} {('«' + rep + '»') if rep else ''} ({why})")
        return None
    so["ai"][cid] = dict(st, moc=cuoi, luc=int(bay_gio), ngay=hom_nay, dem=dem)
    if a != "reply":
        ghi(f"{'🙋' if a == 'handoff' else '💤'} {ten}: «{moi}» → {a} ({why})")
        return tra_chua_doc()
    _, e = post(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/messages", {"access_token": tok},
                {"action": "reply_inbox", "message": rep})
    if e:
        ghi(f"✖ {ten}: gửi hỏng {e}")
        return tra_chua_doc()
    so["ai"][cid]["dem"] = dem + 1
    ghi(f"🤖 {ten}: «{moi}» → «{rep}» ({why})")
    return None


def la_page(m, pid):
    return str((m.get("from") or {}).get("id")) == pid


def main():
    env = C._env()
    if env.get("XN_WA_TAT") == "1":
        return 0
    tok = env.get("PANCAKE_USER_TOKEN") or ""
    try:
        so = json.load(open(SO, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        so = {}
    so.setdefault("da_gui", {})
    so.setdefault("bo", {})
    so.setdefault("ai", {})          # cid -> {"moc": id tin khách đã xử, "luc", "ngay", "dem"}
    bay_gio = time.time()
    for pid in KENH:
        res, err = C.http_json(f"{C.WEB_API}/pages/{pid}/conversations", {"access_token": tok})
        if err:
            ghi(f"⚠️ {pid}: đọc hội thoại hỏng {err}")
            continue
        for c in (res or {}).get("conversations") or []:
            cid = c.get("id")
            lci = _gio(c.get("last_customer_interactive_at"))
            if not cid or not lci or bay_gio - lci > TOI_DA_GIO * 3600:
                continue
            if so["bo"].get(cid) == c.get("updated_at"):
                continue
            cu = ((c.get("customers") or [{}])[0] or {}).get("id")
            if not cu:
                continue
            chua_doc = not c.get("seen")
            r, e = C.http_json(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/messages",
                               {"access_token": tok, "customer_id": cu, "user_view": "true", "is_new_api": "true"})
            if e:
                ghi(f"⚠️ {cid}: đọc tin hỏng {e}")
                continue
            ds = (r or {}).get("messages") or []
            vt = max((i for i, m in enumerate(ds) if not la_page(m, pid)
                      and R_XN_LADI.search(m.get("original_message") or m.get("message") or "")), default=None)
            ly_do = None
            if cid in so["da_gui"] or (vt is not None and any(la_page(m, pid) for m in ds[vt + 1:])):
                tra_loi_tiep(env, tok, pid, c, ds, vt, so, chua_doc, bay_gio)
                continue
            if vt is None:
                ly_do = "không có tin landing"
            elif any(la_page(m, pid) for m in ds[vt + 1:]):
                ly_do = "page đã trả lời sau tin landing"
            else:
                t = _gio(ds[vt].get("inserted_at")) or 0
                if bay_gio - t > TOI_DA_GIO * 3600:
                    ly_do = "quá 23 giờ"
                elif bay_gio - (_gio(ds[-1].get("inserted_at")) or 0) < CHO_GIAY:
                    if chua_doc and not XEM:                  # khách còn đang nhắn — lượt sau
                        post(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/mark_unread", {"access_token": tok}, {})
                    continue
            chu = (ds[vt].get("original_message") or ds[vt].get("message") or "") if vt is not None else ""
            tin = soan(chu, cid) if not ly_do else None
            if not ly_do and not tin:
                ly_do = "tin landing thiếu sản phẩm"
            if ly_do:
                if not XEM:
                    so["bo"][cid] = c.get("updated_at")
                if ly_do not in ("không có tin landing", "page đã trả lời sau tin landing"):
                    ghi(f"⏭ {cid}: {ly_do}")
                if chua_doc and not XEM:
                    post(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/mark_unread", {"access_token": tok}, {})
                continue
            if XEM:
                ghi(f"[XEM] {cid} sẽ gửi:\n{tin}\n")
                continue
            d, e = post(f"{C.WEB_API}/pages/{pid}/conversations/{cid}/messages", {"access_token": tok},
                        {"action": "reply_inbox", "message": tin})
            if e:
                ghi(f"✖ {cid}: gửi hỏng {e}")
                so["bo"][cid] = c.get("updated_at")          # không thử lại vòng vòng; khách nhắn thêm thì thử lại
                continue
            so["da_gui"][cid] = int(bay_gio)
            so["bo"].pop(cid, None)
            ghi(f"✅ {cid}: đã gửi xác nhận ({truong(chu, 'Name')} · {truong(chu, 'Product')[:40]})")
            time.sleep(3)
    if not XEM:
        for k in [k for k, v in so["ai"].items() if bay_gio - (v.get("luc") or 0) > 3 * 86400]:
            so["ai"].pop(k)
        for k in sorted(so["da_gui"], key=so["da_gui"].get)[:-3000]:
            so["da_gui"].pop(k)
        if len(so["bo"]) > 3000:
            so["bo"] = dict(list(so["bo"].items())[-3000:])
        json.dump(so, open(SO, "w", encoding="utf-8"), ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GỠ SỐ WHATSAPP ĐÃ NGƯNG KHỎI KỊCH BẢN PANCAKE (chủ shop 20/09).

Chủ shop: không có số mới — cứ XIN SỐ CỦA KHÁCH rồi nhân viên chủ động nhắn. Nên mọi mẫu
"Trả lời nhanh" đang đưa số của shop phải đổi thành câu xin số của khách, đúng tiếng của mẫu.

Cách ghi (dò được 20/09): POST https://pancake.vn/api/v1/pages/{pid}/settings
    changes = {"quick_replies": [...toàn bộ danh sách mẫu...]}, current_settings_key = <của page>
Ghi y hệt bản cũ thì phiên bản +1 và nội dung giữ nguyên — đã thử trước khi sửa thật.

  python3 kb_go_wa.py --thu                 # chỉ đếm, không ghi
  python3 kb_go_wa.py --page <id>           # làm đúng 1 page
  python3 kb_go_wa.py                       # làm hết
  python3 kb_go_wa.py --hoan-tac <id>       # trả lại bản gốc đã lưu của 1 page

Bản gốc từng page lưu ở state/_saoluu-kichban-20260920/raw/<pid>.json TRƯỚC khi ghi.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = "/opt/pancake-tool"
SAO = os.path.join(HERE, "state", "_saoluu-kichban-20260920", "raw")
LOG = os.path.join(HERE, "state", "kb_go_wa.log")
os.makedirs(SAO, exist_ok=True)

SO = ("12027736276", "971543610815", "18702097265")


def _pat(s):
    return r"\+?\s*" + r"[\s.‑–()-]{0,2}".join(s)


WA = re.compile(r"(?:https?://)?(?:www\.)?(?:wa\.me|wa\.link|api\.whatsapp\.com/send|chat\.whatsapp\.com)/?\S*"
                + "".join("|" + _pat(x) for x in SO), re.I | re.U)

CAU = {
    "en": ("Please send us your WhatsApp number — our team will message you there about your delivery.",
           "Please send us your WhatsApp number — our team will message you there so you can share your location."),
    "tl": ("Pakisend po ang WhatsApp number ninyo — kokontakin po kayo ng team namin doon para sa delivery.",
           "Pakisend po ang WhatsApp number ninyo — ime-message po kayo ng team namin doon para maipadala ninyo ang location."),
    "ar": ("أرسل لنا رقم الواتساب الخاص بك وسيتواصل معك فريقنا عليه بخصوص التوصيل.",
           "أرسل لنا رقم الواتساب الخاص بك وسيراسلك فريقنا عليه لترسل لنا موقعك."),
    "zh": ("請把您的 WhatsApp 號碼發給我們，我們的團隊會在 WhatsApp 上與您聯繫配送事宜。",
           "請把您的 WhatsApp 號碼發給我們，我們的團隊會在 WhatsApp 上聯繫您，您可以在那裡發送位置。"),
}
VI_TRI = re.compile(r"location|lokasyon|maps|موقع|位置|地址", re.I | re.U)
DAU_DONG = re.compile(r"^(\s*(?:[-•*·]|\d+[.)]|[\U0001F300-\U0001FAFF☀-➿][️⃣]?)+\s*)")


def tieng(t):
    if re.search(r"[؀-ۿ]", t):
        return "ar"
    if re.search(r"[一-鿿]", t):
        return "zh"
    if re.search(r"\b(?:po|niyo|ninyo|pwede|opo|salamat|ipadala|kayo)\b", t, re.I):
        return "tl"
    return "en"


def thay(tin):
    """Thay theo DÒNG rồi theo CÂU — giữ nguyên bố cục mẫu (👉, xuống dòng, emoji)."""
    if not WA.search(tin or ""):
        return tin, 0
    lg = tieng(tin)
    ra, n = [], 0
    for dong in (tin or "").split("\n"):
        if not WA.search(dong):
            ra.append(dong)
            continue
        n += 1
        m = DAU_DONG.match(dong)
        dau = m.group(1) if m else ""
        cau_ra, da = [], False
        for c in re.split(r"(?<=[.!?。！？])\s+", dong[len(dau):]):
            if WA.search(c):
                if not da:
                    cau_ra.append(CAU[lg][1 if VI_TRI.search(dong) else 0])
                    da = True
                continue
            if c.strip():
                cau_ra.append(c.strip())
        ra.append(dau + " ".join(cau_ra))
    return "\n".join(ra), n


def _tok():
    for l in open(os.path.join(HERE, ".env"), encoding="utf-8"):
        if l.startswith("PANCAKE_USER_TOKEN="):
            return l.split("=", 1)[1].strip()
    sys.exit("thiếu PANCAKE_USER_TOKEN trong .env")


TOK = _tok()


def _get(url, p):
    u = url + "?" + urllib.parse.urlencode(p)
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40)
    return json.loads(r.read().decode() or "{}")


def _post(url, p, body):
    u = url + "?" + urllib.parse.urlencode(p)
    d = urllib.parse.urlencode(body).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            u, data=d, headers={"User-Agent": "Mozilla/5.0",
                                "Content-Type": "application/x-www-form-urlencoded"}), timeout=60)
        return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"loi": e.read().decode()[:200]}
    except Exception as e:
        return 0, {"loi": str(e)[:200]}


def doc_mau(pid):
    d = _get(f"https://pancake.vn/api/v1/pages/{pid}/settings",
             {"access_token": TOK, "load_quick_replies_only": "true", "client_version": "0"})
    if not d.get("success"):
        return None, str(d.get("message") or d)[:90]
    qr = d.get("quick_replies") or {}
    data = qr.get("data")
    if not isinstance(data, dict):
        return None, f"không có nội dung (data={str(data)[:30]})"
    return data.get("quick_replies") or [], None


def khoa(pid):
    try:
        st = _get(f"https://pages.fm/api/v1/pages/{pid}/settings", {"access_token": TOK})
        return (st.get("settings") or {}).get("current_settings_key")
    except Exception:
        return None


def sua_mau(mau):
    """Trả (mẫu đã sửa, số câu đã đổi)."""
    m2 = json.loads(json.dumps(mau))
    n = 0
    for q in m2:
        for tn in (q.get("messages") or []):
            t = tn.get("message") or ""
            if WA.search(t):
                moi, k = thay(t)
                tn["message"] = moi
                n += k
    return m2, n


def lam_1_page(pid, ten="", thu=False):
    mau, e = doc_mau(pid)
    if e:
        return "loi", e
    m2, n = sua_mau(mau)
    if not n:
        return "sach", 0
    if thu:
        return "se_sua", n
    with open(os.path.join(SAO, f"{pid}.json"), "w", encoding="utf-8") as f:
        json.dump(mau, f, ensure_ascii=False)
    code, res = _post(f"https://pancake.vn/api/v1/pages/{pid}/settings", {"access_token": TOK},
                      {"changes": json.dumps({"quick_replies": m2}), "current_settings_key": khoa(pid)})
    if code != 200:
        return "ghi_hong", f"{code} {str(res)[:120]}"
    lai, e2 = doc_mau(pid)
    if e2:
        return "ghi_xong_khong_doc_lai", n
    con = sum(1 for q in (lai or []) for tn in (q.get("messages") or []) if WA.search(tn.get("message") or ""))
    return ("xong", n) if not con else ("van_con", con)


def main():
    thu = "--thu" in sys.argv
    mot = None
    if "--page" in sys.argv:
        mot = sys.argv[sys.argv.index("--page") + 1]
    if "--hoan-tac" in sys.argv:
        pid = sys.argv[sys.argv.index("--hoan-tac") + 1]
        mau = json.load(open(os.path.join(SAO, f"{pid}.json"), encoding="utf-8"))
        code, res = _post(f"https://pancake.vn/api/v1/pages/{pid}/settings", {"access_token": TOK},
                          {"changes": json.dumps({"quick_replies": mau}), "current_settings_key": khoa(pid)})
        print("hoàn tác", pid, code, str(res)[:120])
        return

    # page nào có số: lấy từ state (đã tải) rồi kiểm lại bằng API khi chạy
    can = {}
    for tt in ("bahrain", "kuwait", "oman", "qatar", "saudi", "taiwan", "uae", "usa"):
        f = os.path.join(HERE, "state", tt, "kich_ban.json")
        if not os.path.exists(f):
            continue
        for pid, kb in json.load(open(f, encoding="utf-8")).items():
            if WA.search(json.dumps(kb, ensure_ascii=False)):
                can[pid] = (tt, kb.get("ten") or kb.get("ten_page") or "")
    if mot:
        can = {mot: can.get(mot, ("?", ""))}
    print(f"{len(can)} page cần sửa" + (" (CHẠY THỬ)" if thu else ""), flush=True)
    dem = {}
    log = open(LOG, "a", encoding="utf-8")
    for i, (pid, (tt, ten)) in enumerate(sorted(can.items()), 1):
        kq, n = lam_1_page(pid, ten, thu)
        dem[kq] = dem.get(kq, 0) + 1
        dong = f"{time.strftime('%F %T')} [{tt}] {pid} {ten[:40]:40} {kq} {n}"
        log.write(dong + "\n")
        log.flush()
        if kq not in ("sach",):
            print(f"  {i:3}/{len(can)} {dong}", flush=True)
        if not thu:
            time.sleep(0.4)
    print("\nKẾT QUẢ:", dem)


if __name__ == "__main__":
    main()

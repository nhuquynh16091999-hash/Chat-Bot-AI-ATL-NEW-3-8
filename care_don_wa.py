#!/usr/bin/env python3
"""CARE ĐƠN WHATSAPP NỬA TỰ ĐỘNG — máy đọc POS, gửi danh sách đơn landing cần care vào nhóm "vận đơn off" (chủ shop 25/09/2026).

Chủ shop 25/09 chọn care đơn bằng APP WhatsApp (không qua API): máy KHÔNG nhắn khách. Máy chỉ gom đơn cần care, mỗi đơn một
link wa.me đã điền sẵn tin đúng tiếng khách → nhân viên bấm link trên WhatsApp của ĐÚNG số landing rồi bấm Gửi.

⚠️ CHỈ KHÁCH ĐÃ NHẮN TRƯỚC (chủ shop 25/09: "chỉ nhắn với những khách đã nhắn cho tôi trước qua whatsapp, chứ k là bị khoá"):
máy chỉ đưa đơn khi THẤY được khách đã nhắn vào đúng số landing — tức số đó phải nối Pancake (whatsapp_official, co-existence)
và hội thoại `<kênh>_<sđt khách>` có `last_customer_interactive_at` (giờ khách nhắn; kiểm 25/09 trên Xophia: tin khách nhắn từ
app đồng bộ về Pancake đúng `from = wa_<sđt>`). Số landing chưa nối Pancake → KHÔNG đưa đơn nào (không biết khách nhắn chưa).
SĐT khách nhắn WhatsApp khác SĐT trên đơn → cũng không đưa.

3 loại tin (mẫu /en1-3 /ar1-3 /es1-3 /it1-3 /bg1-3 trong mau-care-don-whatsapp.txt, thêm /ro1-3):
  📦 Tin 1 ĐÃ GỬI HÀNG   — đơn POS sang "Đã gửi hàng"(2) trong 48 giờ, chưa có mốc đi giao / giao hỏng.
  🚚 Tin 2 HÔM NAY GIAO  — mốc hãng mới nhất là "Đang đi giao" trong ngày (giờ nước khách), trước 17:00 giờ nước khách.
  ❗ Tin 3 GIAO KHÔNG ĐƯỢC — mốc hãng mới nhất là giao hỏng vì không liên lạc được khách (không nghe máy, vắng nhà, máy tắt…), ≤30 giờ.
Mỗi đơn mỗi loại tối đa 1 lần. Đơn đã giao / đang hoàn / hủy thì thôi.

Nguồn:
  · Đơn landing = không gắn hội thoại + nguồn rỗng/-7 (như landing_vao_chat). Đơn có Ghi chú in "CARE ĐƠN QUA MESS" → bỏ (care qua Mess).
  · Số WhatsApp khách được đưa tới = `WA_PHONE` trong mã landing (order.link) — 25/09 đang có 3 số: +1 202 960 7988,
    +84 325 891 917, +84 377 659 376. Landing chỉ có m.me / không có nút WhatsApp → bỏ. Số ghi lại lúc máy thấy đơn lần đầu.
  · Mốc hãng = partner.extend_update do máy vận đơn ghi (chữ Việt, giờ VN trong note). Trễ so với hãng ~3 giờ (trung vị, đo 25/09).

  python3 care_don_wa.py            # 1 lượt (timer 30 phút gọi): quét → gửi nhóm → ghi sổ
  python3 care_don_wa.py --xem      # in tin sẽ gửi, KHÔNG gửi, KHÔNG ghi sổ

.env: CARE_WA_NHOM (mặc định nhóm "vận đơn off") · CARE_WA_TAT=1 tắt nhanh.
Sổ: state/care_wa/so.json (đơn đã đưa nhóm) · state/care_wa/landing.json (landing → số WA, tiếng, tên SP; nạp lại 6 giờ).
"""
import fcntl
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DIR = "/opt/pancake-tool"
STATE = os.path.join(DIR, "state", "care_wa")
F_SO = os.path.join(STATE, "so.json")
F_LANDING = os.path.join(STATE, "landing.json")
F_KHOA = os.path.join(STATE, ".khoa")
POS_API = "https://pos.pages.fm/api/v1"
WEB_API = "https://pancake.vn/api/v1"
NODE_GUI = "/opt/aicloser/src/gui-canh-bao.js"
NHOM_MAC_DINH = "120363408694597880@g.us"          # nhóm WhatsApp "vận đơn off" (chủ shop 25/09)
VN = ZoneInfo("Asia/Ho_Chi_Minh")

LUI_DAU = 48 * 3600          # lượt đầu (chưa có mốc): xét đơn cập nhật trong 48 giờ
CHONG_LUI = 40 * 60          # các lượt sau: quét từ mốc lượt trước lùi 40 phút
TIN1_TOI_DA = 48 * 3600      # Tin 1: đơn sang "Đã gửi hàng" trong 48 giờ
TIN3_TOI_DA = 30 * 3600      # Tin 3: mốc giao hỏng trong 30 giờ
TIN2_TOI_DA = 14 * 3600      # Tin 2: mốc đi giao trong 14 giờ, cùng ngày giờ nước khách
TIN2_HET_GIO = 17            # quá 17:00 giờ nước khách thì thôi báo "hôm nay giao"
LANDING_LAM_MOI = 6 * 3600
MOI_TIN_TOI_DA = 20          # số đơn mỗi tin nhóm
GIU_SO_NGAY = 20

# thị trường → (tiếng mặc định, múi giờ). Vùng Vịnh: tin landing tiếng Ả Rập thì trả Ả Rập, còn lại tiếng Anh.
TT = {
    "saudi": ("en", "Asia/Riyadh"), "kuwait": ("en", "Asia/Kuwait"), "qatar": ("en", "Asia/Qatar"),
    "bahrain": ("en", "Asia/Bahrain"), "uae": ("en", "Asia/Dubai"), "oman": ("en", "Asia/Muscat"),
    "spain": ("es", "Europe/Madrid"), "bulgaria": ("bg", "Europe/Sofia"), "romania": ("ro", "Europe/Bucharest"),
    "italy": ("it", "Europe/Rome"),
}
# tên shop trong tin — theo tên miền landing (chủ shop đổi ở đây)
TEN_SHOP = {"xophia.store": "Xophia", "kstack.io.vn": "Kstack", "zetasolutions.io.vn": "Zeta Solutions"}

# Mẫu nguyên văn từ mau-care-don-whatsapp.txt (25/09). /ro1-3 máy dịch thêm 25/09 cho Romania.
MAU = {
    "en": {
        1: "Hi [TÊN], your [SẢN PHẨM] order from [SHOP] is on its way 📦\nThe courier will contact you before delivery 📞\n"
           "Please have [TỔNG TIỀN] ready in cash 💵",
        2: "Hi [TÊN], your [SẢN PHẨM] order from [SHOP] will be delivered today 🚚\nPlease keep your phone on so the courier can "
           "reach you 📞\nPlease have [TỔNG TIỀN] ready in cash 💵",
        3: "Hi [TÊN], the courier could not reach you today to deliver your [SẢN PHẨM] order from [SHOP] 📦\nWhat day and time "
           "is best for you to receive it? 🙏\nReply here and we will arrange a new delivery ✅",
    },
    "ar": {
        1: "مرحباً [TÊN]، طلبك لـ [SẢN PHẨM] من [SHOP] في الطريق إليك 📦\nسيتواصل معك المندوب قبل التوصيل 📞\n"
           "يرجى تجهيز مبلغ [TỔNG TIỀN] نقداً 💵",
        2: "مرحباً [TÊN]، سيتم توصيل طلبك لـ [SẢN PHẨM] من [SHOP] اليوم 🚚\nيرجى إبقاء هاتفك مفتوحاً ليتمكن المندوب من "
           "الاتصال بك 📞\nيرجى تجهيز مبلغ [TỔNG TIỀN] نقداً 💵",
        3: "مرحباً [TÊN]، لم يتمكن المندوب من الوصول إليك اليوم لتوصيل طلبك لـ [SẢN PHẨM] من [SHOP] 📦\nأي يوم ووقت "
           "يناسبك لاستلام الطلب؟ 🙏\nيرجى الرد علينا هنا وسنرتب لك موعد توصيل جديد ✅",
    },
    "es": {
        1: "Hola [TÊN], tu pedido de [SẢN PHẨM] en [SHOP] ya está en camino 📦\nEl repartidor se pondrá en contacto contigo "
           "antes de la entrega 📞\nPor favor, ten preparado el importe de [TỔNG TIỀN] en efectivo 💵",
        2: "Hola [TÊN], tu pedido de [SẢN PHẨM] en [SHOP] llega hoy 🚚\nMantén el teléfono encendido para que el repartidor "
           "pueda contactarte 📞\nPor favor, ten preparado el importe de [TỔNG TIỀN] en efectivo 💵",
        3: "Hola [TÊN], hoy el repartidor no ha podido contactarte para entregar tu pedido de [SẢN PHẨM] en [SHOP] 📦\n"
           "¿Qué día y a qué hora te viene mejor recibirlo? 🙏\nRespóndenos aquí y programaremos una nueva entrega ✅",
    },
    "it": {
        1: "Ciao [TÊN], il tuo ordine di [SẢN PHẨM] su [SHOP] è stato spedito 📦\nIl corriere ti contatterà prima della "
           "consegna 📞\nPer favore, tieni pronto l'importo di [TỔNG TIỀN] in contanti 💵",
        2: "Ciao [TÊN], il tuo ordine di [SẢN PHẨM] su [SHOP] arriva oggi 🚚\nTieni il telefono acceso così il corriere può "
           "contattarti 📞\nPer favore, tieni pronto l'importo di [TỔNG TIỀN] in contanti 💵",
        3: "Ciao [TÊN], oggi il corriere non è riuscito a contattarti per consegnare il tuo ordine di [SẢN PHẨM] su [SHOP] 📦\n"
           "In quale giorno e a che ora preferisci riceverlo? 🙏\nRispondi qui e organizzeremo una nuova consegna ✅",
    },
    "bg": {
        1: "Здравейте, [TÊN]! Вашата поръчка за [SẢN PHẨM] от [SHOP] е изпратена 📦\nКуриерът ще се свърже с Вас преди "
           "доставката 📞\nМоля, пригответе сумата от [TỔNG TIỀN] в брой 💵",
        2: "Здравейте, [TÊN]! Вашата поръчка за [SẢN PHẨM] от [SHOP] ще бъде доставена днес 🚚\nМоля, дръжте телефона си "
           "включен, за да може куриерът да се свърже с Вас 📞\nМоля, пригответе сумата от [TỔNG TIỀN] в брой 💵",
        3: "Здравейте, [TÊN]! Днес куриерът не успя да се свърже с Вас, за да достави поръчката Ви за [SẢN PHẨM] от [SHOP] 📦\n"
           "Кой ден и в колко часа Ви е удобно да я получите? 🙏\nОтговорете ни тук и ще организираме нова доставка ✅",
    },
    "ro": {
        1: "Bună ziua, [TÊN]! Comanda dumneavoastră de [SẢN PHẨM] de la [SHOP] a fost expediată 📦\nCurierul vă va contacta "
           "înainte de livrare 📞\nVă rugăm să pregătiți suma de [TỔNG TIỀN] în numerar 💵",
        2: "Bună ziua, [TÊN]! Comanda dumneavoastră de [SẢN PHẨM] de la [SHOP] va fi livrată astăzi 🚚\nVă rugăm să țineți "
           "telefonul pornit ca să vă poată contacta curierul 📞\nVă rugăm să pregătiți suma de [TỔNG TIỀN] în numerar 💵",
        3: "Bună ziua, [TÊN]! Astăzi curierul nu a reușit să vă contacteze pentru a livra comanda dumneavoastră de [SẢN PHẨM] "
           "de la [SHOP] 📦\nÎn ce zi și la ce oră vă este cel mai convenabil să o primiți? 🙏\nRăspundeți-ne aici și vom "
           "programa o nouă livrare ✅",
    },
}
NHAN = {1: "📦 *ĐÃ GỬI HÀNG*", 2: "🚚 *HÔM NAY GIAO*", 3: "❗ *GIAO KHÔNG ĐƯỢC*"}

# mốc hãng (status + note do máy vận đơn ghi, đo 25/09 trên 9 nước)
R_DA_GIAO = re.compile(r"Đã giao\b|ĐÃ GIAO THÀNH CÔNG")
R_THOI = re.compile(r"hoàn|hu[ỷỷ] đơn|hủy đơn|Hãng đã hu|TIÊU HU|yêu cầu hu", re.I)   # mốc nào dính là thôi (#75255: khách huỷ 23/9 mà 24/9 hãng vẫn đi giao)
R_ARAP = re.compile(r"[\u0600-\u06FF]")
VINH = {"saudi", "kuwait", "qatar", "bahrain", "uae", "oman"}
R_DI_GIAO = re.compile(r"Đang đi giao|Đang trên đường đi giao|Đã giao cho nhân viên đi giao|EN REPARTO", re.I)
# giao hỏng vì KHÔNG LIÊN LẠC ĐƯỢC khách — đúng nghĩa Tin 3. Khách hẹn lại / từ chối / đổi địa chỉ / lỗi hãng thì KHÔNG.
R_KHONG_LIEN_LAC = re.compile(
    r"không nghe máy|không trả lời|từ chối cuộc gọi|tắt nguồn|máy tắt|không có mặt|đi vắng|chặn cuộc gọi|sai số điện thoại|"
    r"không liên lạc được|không có người nhận|NotReachable|Gọi khách không được|AUSENTE|đóng cửa|cần team liên hệ khách|"
    r"Unsuitable delivery time", re.I)
R_GIO_NOTE = re.compile(r"(\d{1,2}):(\d{2}) (sáng|trưa|chiều|tối|đêm), (\d{1,2})/(\d{1,2})/(\d{4}) theo giờ Việt Nam")
R_LY_DO = re.compile(r"Lý do hãng báo:\s*([^|\n]+)")


def _env():
    env = {}
    try:
        for line in open(os.path.join(DIR, ".env"), encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def log(msg):
    print(f"[{datetime.now(VN):%Y-%m-%d %H:%M:%S} VN] {msg}", flush=True)


def doc_json(f, mac_dinh):
    try:
        return json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError):
        return mac_dinh


def ghi_json(f, d):
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    os.replace(tmp, f)


def http_json(url, params=None, timeout=90):
    u = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for lan in range(3):
        try:
            with urllib.request.urlopen(u, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8") or "{}"), None
        except urllib.error.HTTPError as e:
            loi = f"HTTP {e.code}"
        except Exception as e:                           # noqa: BLE001 — mạng chập chờn: thử lại
            loi = str(e)[:120]
        time.sleep(2 + 3 * lan)
    return None, loi


def thi_truong():
    mk = doc_json(os.path.join(DIR, "markets.json"), {})
    return {k: v for k, v in mk.items()
            if isinstance(v, dict) and v.get("bat", True) and v.get("api_key") and k in TT}


# ---------------------------------------------------------------- landing → số WhatsApp
def _duong(link):
    link = re.sub(r"[?#].*", "", str(link or "")).rstrip("/")
    return link if link.startswith("http") else ""


def soi_landing(url):
    """{wa, tieng, sp, tieu_de} từ mã landing. wa rỗng = landing không có nút WhatsApp."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception as e:                               # noqa: BLE001
        return {"loi": str(e)[:80]}
    wa = re.findall(r"WA_PHONE\s*=\s*[\"'](\+?\d{8,15})", h) or \
        re.findall(r"(?:api\.whatsapp\.com/send\?phone=|wa\.me/)(\+?\d{8,15})", h)
    i = h.find("buildMessage")
    khoi = h[i:i + 3000] if i >= 0 else ""
    sp = re.search(r"\"(?:Product|Producto|Prodotto|Produs|Продукт)\s*:\s*([^\"+]+?)\s*\"\s*[,\]\n]", khoi)
    td = re.search(r"<title[^>]*>(.*?)</title>", h, re.S)
    return {"wa": re.sub(r"\D", "", wa[0]) if wa else "",
            "tieng": "ar" if re.search(r"[\u0600-\u06FF]", khoi) else "",
            "sp": sp.group(1).strip() if sp else "",
            "tieu_de": re.sub(r"\s+", " ", td.group(1)).strip() if td else ""}


class Landing:
    def __init__(self):
        self.bang = doc_json(F_LANDING, {})
        self.doi = False

    def lay(self, url):
        v = self.bang.get(url)
        if not v or time.time() - v.get("luc", 0) > LANDING_LAM_MOI or v.get("loi"):
            moi = soi_landing(url)
            if moi.get("loi") and v and not v.get("loi"):
                return v                                 # tải hỏng thì dùng bản cũ
            moi["luc"] = int(time.time())
            self.bang[url] = v = moi
            self.doi = True
        return v

    def luu(self):
        if self.doi:
            ghi_json(F_LANDING, self.bang)


# ---------------------------------------------------------------- đọc đơn
def gio_note(note):
    m = R_GIO_NOTE.search(note or "")
    if not m:
        return None
    h, mi, buoi, d, mo, y = m.groups()
    h = int(h)
    if buoi == "sáng":
        h = 0 if h == 12 else h
    elif buoi == "trưa":
        h = h if h >= 11 else h + 12
    elif buoi in ("chiều", "tối"):
        h = h if h >= 12 else h + 12
    else:                                                # đêm: 11:30 đêm = 23:30, 3:38 đêm = 03:38
        h = 0 if h == 12 else (h + 12 if h >= 9 else h)
    try:
        return datetime(int(y), int(mo), int(d), h, int(mi), tzinfo=VN).timestamp()
    except ValueError:
        return None


def moc_hang(o):
    """Mốc hãng, mới nhất trước: [(giờ, chữ status+note)]. extend_update.updated_at là giờ VN (đo 25/09: = partner.updated_at UTC + 7)."""
    ra = []
    for i, e in enumerate((o.get("partner") or {}).get("extend_update") or []):
        chu = f"{e.get('status') or ''} | {e.get('note') or ''}"
        t = gio_note(e.get("note"))
        if t is None:
            try:
                t = datetime.fromisoformat(str(e.get("updated_at"))[:19]).replace(tzinfo=VN).timestamp()
            except ValueError:
                t = 0
        ra.append((t, -i, chu))
    ra.sort(reverse=True)
    return [(t, chu) for t, _, chu in ra]


def gio_gui_hang(o):
    """Lần cuối đơn vào "Đã gửi hàng"(2) — status_history giờ UTC."""
    t = None
    for h in o.get("status_history") or []:
        if h.get("status") == 2 and h.get("updated_at"):
            try:
                t = datetime.fromisoformat(str(h["updated_at"])[:19]).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
    return t


def sdt_quoc_te(sdt, cc):
    s = str(sdt or "").strip()
    so = re.sub(r"\D", "", s)
    if not so:
        return ""
    if s.startswith("+"):
        return so
    if so.startswith("00"):
        return so[2:]
    cc = str(cc)
    if so.startswith(cc) and len(so) > len(cc) + 7:
        return so
    return cc + so.lstrip("0")


def ten_goi(ten):
    t = re.sub(r"\s+", " ", str(ten or "")).strip()
    if not t:
        return ""
    if re.fullmatch(r"[A-Za-z .'-]+", t) and (t.isupper() or t.islower()):
        t = t.title()
    tu = t.split(" ")
    goi = tu[0]
    if len(goi.strip(".")) <= 2 and len(tu) > 1:         # "Md. Rahim", "Mr John"
        goi = f"{tu[0]} {tu[1]}"
    return goi


def ten_sp(o, ld):
    if ld.get("sp"):
        return _hoa_thuong(ld["sp"])
    for it in o.get("items") or []:
        n = (it.get("variation_info") or {}).get("name") or ""
        n = re.sub(r"^\s*\d{2,5}\s*[-–]\s*", "", n)
        n = re.sub(r"\s*[-–]\s*\d{2,5}\s*$", "", n).strip()
        if n and not re.search(r"\btest\b", n, re.I):
            return _hoa_thuong(n)
    return _hoa_thuong(ld.get("tieu_de") or "")


def _hoa_thuong(s):
    """'ESSENTIAL OIL PERFUME SOAP' → 'Essential Oil Perfume Soap' (chữ in hoa cả tên đọc như la hét)."""
    return s.title() if s.isupper() and len(s) > 4 else s


def tong_tien(o, m):
    tien = o.get("money_to_collect") or o.get("cod")
    if not isinstance(tien, (int, float)) or tien <= 0:
        return ""
    so = tien / (m.get("scale") or 100)
    so = f"{so:.2f}".rstrip("0").rstrip(".")
    tt = (m.get("ma_tien_te") or m.get("tien_te") or "").upper()
    if tt == "EUR":
        return f"{so} €"
    if tt == "RON":
        return f"{so} lei"
    return f"{so} {tt}".strip()


def ten_shop(url):
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    return TEN_SHOP.get(host) or host.split(".")[0].title()


def ly_do_hong(chu):
    """Chữ ngắn cho nhân viên: dòng đầu note ('Giao thất bại — khách không nghe máy'); dòng chung chung thì lấy lý do hãng."""
    note = chu.split(" | ", 1)[1] if " | " in chu else chu
    dau = re.sub(r"^(?:⚠️\s*)?(?:Giao không thành:\s*)?", "", note.strip().split("\n")[0].strip()).strip()
    ly = R_LY_DO.search(note)
    if "cần team liên hệ khách" in dau or not dau:
        return f"giao không thành{', hãng ghi: ' + ly.group(1).strip() if ly else ''}"[:90]
    return dau[:90]


def xet_don(o, mkey, m, ld, so_don, now):
    """→ (loại tin, chữ lý do) hoặc None."""
    moc = moc_hang(o)
    if any(R_DA_GIAO.search(c.split(" | ")[0]) or "ĐÃ GIAO THÀNH CÔNG" in c for _, c in moc):
        return None
    if any(R_THOI.search(c) for _, c in moc):
        return None
    moi = moc[0] if moc else None
    da = so_don or {}
    if moi and R_KHONG_LIEN_LAC.search(moi[1]) and now - moi[0] <= TIN3_TOI_DA and not da.get("e3"):
        return 3, ly_do_hong(moi[1])
    if moi and R_DI_GIAO.search(moi[1]) and not da.get("e2") and not da.get("e3"):
        tz = ZoneInfo(TT[mkey][1])
        luc = datetime.fromtimestamp(moi[0], tz)
        bay_gio = datetime.fromtimestamp(now, tz)
        if now - moi[0] <= TIN2_TOI_DA and luc.date() == bay_gio.date() and bay_gio.hour < TIN2_HET_GIO:
            return 2, ""
        return None
    co_giao = any(R_DI_GIAO.search(c) or R_KHONG_LIEN_LAC.search(c) for _, c in moc)
    t2 = gio_gui_hang(o)
    if not co_giao and t2 and now - t2 <= TIN1_TOI_DA and not (da.get("e1") or da.get("e2") or da.get("e3")):
        return 1, ""
    return None


# ---------------------------------------------------------------- khách đã nhắn trước chưa (Pancake)
def kenh_wa(tok):
    """{số WhatsApp (chỉ chữ số): page_id} của các kênh WhatsApp đã nối Pancake."""
    res, err = http_json("https://pages.fm/api/v1/pages", {"access_token": tok})
    ra = {}

    def di(x):
        if isinstance(x, dict):
            if x.get("platform") == "whatsapp_official" and x.get("id"):
                so = re.sub(r"\D", "", str((x.get("platform_extra_info") or {}).get("display_phone_number") or ""))
                if so:
                    ra[so] = str(x["id"])
            for v in x.values():
                di(v)
        elif isinstance(x, list):
            for v in x:
                di(v)
    di(res or {})
    return ra, err


def khach_da_nhan(pid, tok):
    """{sđt khách: giờ khách nhắn gần nhất} — CHỈ LIỆT KÊ hội thoại, không mở tin, không lật dấu đã xem."""
    ra, thay, cuoi, loi = {}, set(), None, None
    for _ in range(100):
        tham = {"access_token": tok}
        if cuoi:
            tham["last_conversation_id"] = cuoi
        res, loi = http_json(f"{WEB_API}/pages/{pid}/conversations", tham)
        cs = (res or {}).get("conversations") or []
        moi = [c for c in cs if c.get("id") and c["id"] not in thay]
        for c in moi:
            thay.add(c["id"])
            if c.get("last_customer_interactive_at"):
                sdt = re.sub(r"\D", "", str((c.get("from") or {}).get("id") or c["id"].rsplit("_", 1)[-1]))
                ra[sdt] = c["last_customer_interactive_at"]
        if loi or not moi:
            break
        cuoi = moi[-1]["id"]
        time.sleep(0.3)
    return ra, loi


def quet(so, lan_dau, now):
    """→ (danh sách việc, số đơn đã xét, lỗi)."""
    ld_bang = Landing()
    viec, dem, loi = [], 0, []
    bo = {"chua_noi": {}, "chua_nhan": 0}
    tok = _env().get("PANCAKE_USER_TOKEN") or ""
    kenh, e_kenh = kenh_wa(tok)
    if e_kenh:
        loi.append(f"danh sách kênh Pancake: {e_kenh}")
        return viec, dem, loi, bo                        # không biết khách nhắn chưa → không đưa gì
    da_nhan = {}
    tu = now - LUI_DAU if lan_dau else max(so.get("moc", now) - CHONG_LUI, now - LUI_DAU)
    for mkey, m in thi_truong().items():
        for trang in range(1, 80):
            res, err = http_json(f"{POS_API}/shops/{m['shop_id']}/orders",
                                 {"api_key": m["api_key"], "startDateTime": int(tu), "endDateTime": int(now),
                                  "updateStatus": "updated_at", "page_size": 100, "page_number": trang})
            ds = (res or {}).get("data")
            if err or not isinstance(ds, list):
                loi.append(f"{mkey} trang {trang}: {err or 'không có data'}")
                break
            for o in ds:
                if o.get("status") != 2 or o.get("conversation_id") or \
                        str(o.get("order_sources")) not in ("None", "-7", ""):
                    continue
                if "CARE ĐƠN QUA MESS" in str(o.get("note_print") or "").upper():
                    continue
                url = _duong(o.get("link"))
                if not url:
                    continue
                dem += 1
                khoa = f"{m['shop_id']}:{o.get('id')}"
                so_don = so["don"].get(khoa) or {}
                wa = so_don.get("wa")
                ld = ld_bang.lay(url)
                if not wa:
                    wa = ld.get("wa") or ""
                if not wa:
                    continue
                so["don"].setdefault(khoa, {}).setdefault("wa", wa)      # số landing lúc máy thấy đơn lần đầu — giữ luôn
                so["don"][khoa].setdefault("thay", int(now))
                kq = xet_don(o, mkey, m, ld, so_don, now)
                if not kq:
                    continue
                loai, ly_do = kq
                sdt = sdt_quoc_te(o.get("bill_phone_number"), m.get("country_code"))
                pid = kenh.get(wa)
                if not pid:                              # số landing chưa nối Pancake → không biết khách nhắn chưa → bỏ
                    bo["chua_noi"][wa] = bo["chua_noi"].get(wa, 0) + 1
                    continue
                if pid not in da_nhan:
                    da_nhan[pid], e_dn = khach_da_nhan(pid, tok)
                    if e_dn and not da_nhan[pid]:
                        loi.append(f"hội thoại kênh {pid}: {e_dn}")
                if sdt not in da_nhan[pid]:              # khách chưa từng nhắn số này → KHÔNG đưa (luật giữ số)
                    bo["chua_nhan"] += 1
                    continue
                tien = tong_tien(o, m)
                sp = ten_sp(o, ld)
                if len(sdt) < 9 or not tien or not sp:
                    log(f"bỏ #{o.get('id')} {mkey}: thiếu {'SĐT' if len(sdt) < 9 else 'tiền' if not tien else 'tên SP'}")
                    continue
                tieng = ld.get("tieng") or TT[mkey][0]
                if mkey in VINH and R_ARAP.search(f"{o.get('bill_full_name') or ''} {(o.get('shipping_address') or {}).get('address') or ''}"):
                    tieng = "ar"                         # khách gõ tên/địa chỉ chữ Ả Rập → trả tiếng Ả Rập
                chu = MAU[tieng][loai]
                for o_, g in (("[TÊN]", ten_goi(o.get("bill_full_name")) or "there"), ("[SẢN PHẨM]", sp),
                              ("[SHOP]", ten_shop(url)), ("[TỔNG TIỀN]", tien)):
                    chu = chu.replace(o_, g)
                viec.append({"khoa": khoa, "loai": loai, "wa": wa, "mkey": mkey, "id": o.get("id"),
                             "ten": re.sub(r"\s+", " ", o.get("bill_full_name") or "").strip(), "sp": sp, "tien": tien,
                             "ly_do": ly_do, "link": f"https://wa.me/{sdt}?text={urllib.parse.quote(chu, safe='')}"})
            if len(ds) < 100:
                break
            time.sleep(0.2)
    ld_bang.luu()
    return viec, dem, loi, bo


# ---------------------------------------------------------------- soạn + gửi
def dep_so(wa):
    if wa.startswith("84") and len(wa) == 11:
        return f"+84 {wa[2:5]} {wa[5:8]} {wa[8:]}"
    if wa.startswith("1") and len(wa) == 11:
        return f"+1 {wa[1:4]} {wa[4:7]} {wa[7:]}"
    return "+" + wa


def soan(viec, now):
    """→ [(chữ tin, [khoá việc trong tin])]"""
    nhom = {}
    for v in viec:
        nhom.setdefault((v["loai"], v["wa"]), []).append(v)
    dau = (f"📲 *CARE ĐƠN WHATSAPP* — {datetime.fromtimestamp(now, VN):%H:%M %d/%m}\n"
           "Chỉ có khách ĐÃ nhắn trước vào số đó.\n"
           "Bấm link bằng WhatsApp của ĐÚNG số ghi ở từng mục rồi bấm Gửi.")
    tin = []
    for (loai, wa), ds in sorted(nhom.items(), key=lambda x: (-x[0][0], x[0][1])):   # giao hỏng trước
        ds.sort(key=lambda v: (v["mkey"], v["id"] or 0))
        for i in range(0, len(ds), MOI_TIN_TOI_DA):
            lo = ds[i:i + MOI_TIN_TOI_DA]
            dong = [f"{NHAN[loai]} · máy {dep_so(wa)} · {len(ds)} đơn" + (f" (phần {i // MOI_TIN_TOI_DA + 1})" if len(ds) > MOI_TIN_TOI_DA else "")]
            for j, v in enumerate(lo, i + 1):
                dong.append("")
                dong.append(f"{j}. #{v['id']} {v['mkey'].upper()} · {v['ten']} · {v['sp']} · {v['tien']}"
                            + (f" · hãng báo: {v['ly_do']}" if v["ly_do"] else ""))
                dong.append(v["link"])
            tin.append(("\n".join(dong), [(v["khoa"], v["loai"], v["wa"]) for v in lo]))
    if tin:
        tin[0] = (dau + "\n\n" + tin[0][0], tin[0][1])
    return tin


def gui_wa(text, jid):
    try:
        r = subprocess.run(["node", NODE_GUI, text], cwd="/opt/aicloser", env=dict(os.environ, WA_JID=jid),
                           capture_output=True, text=True, timeout=120)
    except Exception as ex:                              # noqa: BLE001
        return False, str(ex)
    if r.returncode == 0:
        return True, ""
    ra = (r.stdout or "").strip().splitlines()
    return False, (ra[-1] if ra else (r.stderr or "").strip()[-200:] or f"node thoát mã {r.returncode}")


def main():
    xem = "--xem" in sys.argv
    e = _env()
    if e.get("CARE_WA_TAT") == "1" and not xem:
        log("CARE_WA_TAT=1 — tắt")
        return
    jid = e.get("CARE_WA_NHOM") or NHOM_MAC_DINH
    os.makedirs(STATE, exist_ok=True)
    khoa_file = open(F_KHOA, "w")
    try:
        fcntl.flock(khoa_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("lượt trước còn chạy — bỏ lượt này")
        return
    so = doc_json(F_SO, {})
    so.setdefault("don", {})
    now = time.time()
    viec, dem, loi, bo = quet(so, "moc" not in so, now)
    tin = soan(viec, now)
    dem_loai = {k: sum(1 for v in viec if v["loai"] == k) for k in (1, 2, 3)}
    chua_noi = ", ".join(f"{dep_so(k)}: {v}" for k, v in sorted(bo["chua_noi"].items()))
    log(f"xét {dem} đơn landing Đã gửi hàng · đưa nhóm: Tin1 {dem_loai[1]}, Tin2 {dem_loai[2]}, Tin3 {dem_loai[3]}"
        f" · bỏ vì khách chưa nhắn: {bo['chua_nhan']}"
        + (f" · bỏ vì số landing chưa nối Pancake ({chua_noi})" if chua_noi else "")
        + (f" · LỖI {'; '.join(loi)}" if loi else ""))
    if xem:
        for chu, _ in tin:
            print("\n" + "=" * 70 + "\n" + chu)
        print(f"\n({len(tin)} tin, KHÔNG gửi, KHÔNG ghi sổ)")
        return
    gui = 0
    for chu, cac in tin:
        ok, ly = gui_wa(chu, jid)
        if not ok:
            log(f"GỬI HỎNG ({ly}) — để lượt sau")
            break
        gui += 1
        for khoa, loai, wa in cac:
            d = so["don"].setdefault(khoa, {})
            d[f"e{loai}"] = int(now)
            d.setdefault("wa", wa)
        time.sleep(2)
    if not loi:
        so["moc"] = int(now)
    elif "moc" not in so and gui:
        so["moc"] = int(now)
    han = now - GIU_SO_NGAY * 86400
    so["don"] = {k: v for k, v in so["don"].items() if max([x for x in v.values() if isinstance(x, int)] or [now]) >= han}
    ghi_json(F_SO, so)
    if tin:
        log(f"đã gửi {gui}/{len(tin)} tin vào nhóm")


if __name__ == "__main__":
    main()

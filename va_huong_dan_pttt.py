"""Vá ai_sale.py (sau va_coc_my.py): khách chọn PTTT nào → GỬI mẫu hướng dẫn của PTTT đó rồi mới chốt đơn.

Chủ shop 14/09 tối: *"khi khách chọn PTTT nào, thì bạn sẽ phải gửi phương thức đó cho khách, rồi mới chốt đơn"*.
Chạy: python3 va_huong_dan_pttt.py ai_sale.py — mỗi chỗ khớp đúng 1 lần mới ghi.
"""
import sys

f = sys.argv[1]
s = open(f, encoding="utf-8").read()
if "def mau_huong_dan_pttt" in s:
    sys.exit("đã vá rồi — không làm gì")
if "def buoc_thu_tien_sau" not in s:
    sys.exit("❌ chưa có va_coc_my.py — chạy nó trước")

VA = []

# ── 1. tìm mẫu hướng dẫn + đã gửi chưa; ghi vào kết quả buoc_thu_tien_sau ──
VA.append(('''def chua_du_9b(b):''', '''# Phương thức khách nói → tên mẫu hướng dẫn chuyển tiền trong kịch bản Mỹ (đo 37 page 14/09: /ZELLE, /VENMO,
# /CASH_APP, /Paypal, /DebitCard_CreditCard, /CHECK_, /MONEY_ORDER, /MoneyOrder, /MoneyGram+WesternUnion, /CASH_deposit).
_PTTT_MAU = [(r"zelle", r"zelle"), (r"venmo", r"venmo"), (r"cash\\s?app", r"cash_?app"),
             (r"pay\\s?pal", r"paypal"), (r"debit|credit", r"debit|credit"), (r"check|cheque|tseke", r"^check"),
             (r"money\\s?order", r"money_?order"), (r"money\\s?gram|western", r"moneygram|western"),
             (r"cash\\s?deposit", r"cash_?deposit")]


def mau_huong_dan_pttt(kb_page, pttt):
    """Mẫu hướng dẫn chuyển tiền của phương thức khách nói. Khách nói nhiều cách ("money gram / palawan",
    "I don't use cash app or Venmo, I can use my debit card") → lấy cách nói SAU CÙNG có mẫu. Không có → None."""
    mau = [m for m in (kb_page or {}).get("mau") or []
           if m.get("tin") and not re.search(r"care|levelup", m.get("tu_khoa") or "", re.I)]
    for ten in reversed([x.strip() for x in (pttt or "").split("/") if x.strip()]):
        for rx_k, rx_m in _PTTT_MAU:
            if re.search(rx_k, ten, re.I):
                ung = [m for m in mau if re.search(rx_m, (m.get("tu_khoa") or "").strip(), re.I)]
                if ung:
                    return ung[0]
    return None


def da_gui_huong_dan(msgs, mau):
    """Page (sale/AI/bot) đã gửi mẫu hướng dẫn này trong hội thoại chưa."""
    return bool(mau) and any(m["boi"] in ("nguoi", "ai", "botcake") and _khop_mau(m.get("text") or "", mau) >= 0.5
                             for m in msgs)


def chen_huong_dan_pttt(qd, msgs, kb_page):
    """Khách đã chọn PTTT (hoặc nói tới MoneyGram/WU/Money Order) mà page CHƯA gửi mẫu hướng dẫn → chèn NGUYÊN VĂN
    mẫu đó (kèm ảnh) lên đầu tin AI lượt này. Luật cứng, không tin model tự chép. Trả tên mẫu đã chèn hoặc None."""
    if not qd or qd.get("hanh_dong") not in ("tra_loi", "len_don", "tra_loi_treo"):
        return None
    tin = (qd.get("tin_nhan") or "").strip()
    b = buoc_thu_tien_sau(msgs, kb_page)
    if not tin or not b["nha_ok"]:
        return None
    ten = b["pttt"] or (b["nhac"] if b["can_coc"] else None)
    mau = mau_huong_dan_pttt(kb_page, ten)
    if not mau or da_gui_huong_dan(msgs, mau) or _khop_mau(tin, mau) >= 0.5 \\
            or any(CG._giong_nhau(tin[:len(x) + 40], x) >= 0.5 for x in mau["tin"]):
        return None
    them = "\\n\\n".join(x.strip() for x in mau["tin"] if x.strip())
    if b["can_coc"] and not b["doi_coc"] and not DOI_COC.search(tin):
        # Đòi cọc bắt buộc đi cùng hướng dẫn — model quên câu cọc thì thêm câu cố định (tiếng Anh như mẫu /Care_cọc).
        tin += (f"\\n\\nTo secure your order, please send a small deposit of ${TIEN_COC_USD} first — the remaining "
                f"balance is paid when you receive your item. After sending, please send us the MTCN / receipt photo 🙏")
    qd["tin_nhan"] = them + "\\n\\n" + tin
    if mau.get("anh"):
        qd["anh_mau"] = (mau.get("tu_khoa") or "").strip()
    return (mau.get("tu_khoa") or "").strip()


def chua_du_9b(b):'''))

# ── 2. PTTT không có mẫu hướng dẫn thì chưa đủ để chốt ──
VA.append(('''    if b["can_coc"] and not b["da_coc"]:
        return (f"đã đòi cọc''', '''    if b.get("co_mau") is False:
        return (f"phương thức khách chọn ({b['pttt']}) KHÔNG có mẫu hướng dẫn chuyển tiền trong kịch bản",
                "không nhận phương thức này — đưa lại danh sách phương thức theo mẫu /thanhtoan hoặc /PTTT_L2")
    if b["can_coc"] and not b["da_coc"]:
        return (f"đã đòi cọc'''))

VA.append(('''            "pttt": pttt, "cau_pttt": cau, "nhac": nhac, "can_coc": can_coc, "doi_coc": i_coc is not None, "da_coc": da_coc}''',
'''            "pttt": pttt, "cau_pttt": cau, "nhac": nhac, "can_coc": can_coc, "doi_coc": i_coc is not None, "da_coc": da_coc,
            "co_mau": (mau_huong_dan_pttt(kb_page, pttt) is not None) if pttt else None}'''))

# ── 3. nhắc model: hệ thống tự gửi mẫu hướng dẫn ──
VA.append(('''            + "ĐỦ chốt 1 + 2: chọn 'len_don'. tin_nhan = mẫu hướng dẫn phương thức đó (anh_mau) nếu page CHƯA gửi, "
            "rồi câu xác nhận đơn theo /XÁC_NHẬN_ĐƠN với đúng tổng tiền"''',
'''            + "ĐỦ chốt 1 + 2: chọn 'len_don'. HỆ THỐNG TỰ GỬI nguyên mẫu hướng dẫn của phương thức khách chọn (kèm "
            "ảnh) ngay trước câu của bạn nếu page chưa gửi — ĐỪNG chép lại mẫu đó. tin_nhan = câu xác nhận đơn theo "
            "/XÁC_NHẬN_ĐƠN với đúng tổng tiền"'''))

# ── 4. chèn ở cuối bước soạn (sau mọi lần bắt soạn lại) ──
VA.append(('''        except Exception as _e:                # noqa: BLE001 — một luồng hỏng không giết vòng''',
'''                # GỬI HƯỚNG DẪN PTTT RỒI MỚI CHỐT (chủ shop 14/09 tối) — Mỹ/Úc: khách chọn cách trả nào thì tin AI
                # lượt này mang NGUYÊN VĂN mẫu hướng dẫn của cách đó (+ ảnh QR), page đã gửi rồi thì thôi.
                if not err_m and qd and mkey in HS.THU_TIEN_SAU:
                    _hd_ = chen_huong_dan_pttt(qd, msgs, kb_page)
                    if _hd_:
                        print(f"{nhan} 💳 chèn mẫu hướng dẫn /{_hd_} trước tin AI (khách đã chọn phương thức)")
                        dem["chen_huong_dan"] = dem.get("chen_huong_dan", 0) + 1
        except Exception as _e:                # noqa: BLE001 — một luồng hỏng không giết vòng'''))

for cu, moi in VA:
    n = s.count(cu)
    if n != 1:
        sys.exit(f"❌ chỗ vá khớp {n} lần (phải đúng 1): {cu[:70]!r} — KHÔNG ghi gì")
    s = s.replace(cu, moi)
open(f, "w", encoding="utf-8").write(s)
print(f"✅ đã vá {len(VA)} chỗ vào {f}")

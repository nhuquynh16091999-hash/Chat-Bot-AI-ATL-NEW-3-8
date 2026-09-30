import sys
F = "ai_sale.py"
s = open(F, encoding="utf-8").read()

def thay(cu, moi):
    global s
    n = s.count(cu)
    assert n == 1, f"khớp {n} lần: {cu[:80]!r}"
    s = s.replace(cu, moi)

assert "_tin_khach_con_hieu_luc" not in s, "đã vá rồi"

thay('''def hen_giao_theo_luong(msgs):
    """Khách có nói đợi lương / chưa có tiền không?

    Trả (câu khách nói về lương, câu hẹn ngày — "" nếu khách chưa nói ngày) hoặc None.
    Quét tin khách từ MỚI về CŨ, lấy lần gần nhất; ngày hẹn tìm trong chính câu đó rồi các tin
    khách SAU đó (khách hay nói "wait my salary" rồi lượt sau mới nói "on the 25th").
    """
    khach = [lam_sach(m.get("text") or "") for m in (msgs or []) if m.get("boi") == "khach"]
''', '''# LỜI ĐỢI LƯƠNG CŨ KHÔNG KÉO SANG PHIÊN MỚI — chủ shop 14/09 tối, ca Landa Militar (Kuwait Amoura
# Gold): khách nói "I'm waiting my salary" từ 23/07, tới 14/09 bấm lại quảng cáo hỏi "How much", AI
# đáp nguyên bài "giao đúng ngày lương, bạn nhận lương ngày nào?" mà không báo giá. *"khách hỏi 1
# đường, rep 1 nẻo vậy"*. Gốc: bộ dò quét toàn bộ lịch sử không giới hạn thời gian.
# Chỉ tính tin khách: sau lần bấm quảng cáo gần nhất, trong LUONG_HIEU_LUC_GIAY tính từ tin khách
# mới nhất, và nằm trong LUONG_SO_TIN tin khách cuối.
LUONG_HIEU_LUC_GIAY = 3 * 86400
LUONG_SO_TIN = 3
_MO_PHIEN_MOI = re.compile(r"đã trả lời một quảng cáo|replied to (?:an|your) ad", re.I | re.U)


def _moc_giay(luc):
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(str(luc).replace("Z", "+00:00"))
        return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).timestamp()
    except Exception:
        return None


def _tin_khach_con_hieu_luc(msgs):
    """Tin khách (đã làm sạch) còn tính cho luật đợi lương — bỏ tin phiên cũ / quá cũ."""
    msgs = msgs or []
    dau = 0
    for i, m in enumerate(msgs):
        if m.get("boi") == "hethong" and _MO_PHIEN_MOI.search(m.get("text") or ""):
            dau = i
    kh = [m for m in msgs[dau:] if m.get("boi") == "khach"][-LUONG_SO_TIN:]
    moi = _moc_giay(kh[-1].get("luc")) if kh else None
    if moi is not None:
        kh = [m for m in kh if (_moc_giay(m.get("luc")) or moi) >= moi - LUONG_HIEU_LUC_GIAY]
    return [lam_sach(m.get("text") or "") for m in kh]


def hen_giao_theo_luong(msgs):
    """Khách có nói đợi lương / chưa có tiền không?

    Trả (câu khách nói về lương, câu hẹn ngày — "" nếu khách chưa nói ngày) hoặc None.
    Quét tin khách từ MỚI về CŨ, lấy lần gần nhất; ngày hẹn tìm trong chính câu đó rồi các tin
    khách SAU đó (khách hay nói "wait my salary" rồi lượt sau mới nói "on the 25th").
    Chỉ xét tin còn hiệu lực (_tin_khach_con_hieu_luc) — lời đợi lương 2 tháng trước không tính.
    """
    khach = _tin_khach_con_hieu_luc(msgs)
''')

thay('''                         "Xin ngày nhận lương (nếu chưa có) + các mục CÒN THIẾU ở trên trong MỘT tin, "''',
     '''                         + (" ⚠️ NHƯNG tin MỚI NHẤT của khách đang HỎI GIÁ: trả lời đúng câu đó TRƯỚC — báo giá "
                            "ngắn theo kịch bản (được nêu giá), rồi mới nói COD/giao ngày lương. " if _hoi_gia_moi else "")
                       + "Xin ngày nhận lương (nếu chưa có) + các mục CÒN THIẾU ở trên trong MỘT tin, "''')

thay('''    _hen = hen_giao_theo_luong(rec["msgs"])
    if _hen and not dang_tu_van:''', '''    _hen = hen_giao_theo_luong(rec["msgs"])
    _kh_moi = [m for m in rec["msgs"] if m.get("boi") == "khach" and lam_sach(m.get("text") or "").strip()]
    _hoi_gia_moi = bool(_kh_moi and HOI_GIA.search(lam_sach(_kh_moi[-1].get("text") or "")))
    if _hen and not dang_tu_van:''')

open(F, "w", encoding="utf-8").write(s)
print("OK vá xong")

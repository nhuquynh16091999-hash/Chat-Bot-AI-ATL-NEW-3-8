#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VÁ 2026-09-20 — AI LỘ CHỮ NỘI BỘ ("our script doesn't list…") RA KHÁCH.

Chủ shop 20/09, ca Jean Navarro Dela Cruz (Golden Soap House KSA). Khách hỏi xà phòng
có trị được vết thâm không; kịch bản không nói tới vết thâm, model được dạy KHÔNG bịa
thông số nên thú nhận thẳng bằng chữ của người trong nhà:

    "Hi Jean 😊 Our script doesn't list dark spot removal, so I'll check with the team…"

Ý ĐỊNH của câu là ĐÚNG (chưa rõ thì đi hỏi shop, không bịa) — chỉ sai ở chỗ gọi tên cái
văn bản mồi. Khách đọc ra ngay là đang nói chuyện với máy đọc kịch bản, hết tin là người thật.

Đo trên log AI Sale còn giữ (8 thị trường):
  · 3 tin ĐÃ GỬI dính `\\bscripts?\\b` — Jean Navarro (Anh), Elvie Dela Torre + Hermhey
    Guevarra (Tagalog: "nasa script lang", "sa script namin")
  · BẮT OAN 0: "prescription" / "non-prescription" / "description" (4 tin) KHÔNG khớp vì
    ranh giới từ \\b; "internal discomfort" (2 tin) cố ý không bắt
  · 0/8 bộ kịch bản của shop chứa chữ này → lưới cuối không cắt nhầm chữ shop
  · "as an AI" / "language model" / "my instructions" / "template": 0 tin — vẫn chặn sẵn

Ba tầng, rẻ dần theo mức hỏng:
  1) hằng + hàm gỡ (tầng 1)
  2) cổng mọi lượt ở tầng quyết định: sửa nhẹ → cắt câu bằng máy → treo cho sale (tầng 2)
  3) lưới cuối ngay trước khi gửi thật, cho mọi bong bóng không qua cổng trên (tầng 3)

KHÁC các cổng cùng loại: cổng này KHÔNG soạn lại cả gói. Ca hiếm (0,04% tin), sửa nhẹ +
cắt máy đã đủ, soạn lại cả gói chỉ tốn tiền.
"""
import sys

F = "/opt/pancake-tool/ai_sale.py"
BAK = F + ".bak-20260920-truoc-lo-noi-bo"
s = open(F, encoding="utf-8").read()


def thay(anchor, moi, ten):
    global s
    n = s.count(anchor)
    assert n == 1, f"{ten}: mốc xuất hiện {n} lần (phải đúng 1) — DỪNG, không sửa gì"
    s = s.replace(anchor, moi, 1)
    print(f"  ✓ {ten}")


# ───────────────────── 1. Hằng + hàm nhận/gỡ chữ nội bộ ─────────────────────
A1 = '''def cat_cau_tha_khach(t):
    """Bỏ các câu/cụm thả khách ("Take your time!") khỏi tin; còn quá ngắn thì trả nguyên."""
    cau = re.split(r"(?<=[.!?])\\s+", t or "")
    giu = [c for c in cau if not THA_KHACH.search(c)]
    kq = " ".join(giu).strip()
    return kq if len(kq) >= 40 else (t or "")
'''

M1 = A1 + '''

# CHỮ NỘI BỘ LỘ RA KHÁCH (chủ shop 20/09, ca Jean Navarro — Golden Soap House KSA:
# "Our script doesn't list dark spot removal"). Khách không được biết sau lưng có kịch bản:
# biết rồi thì mọi câu sau đó đọc như máy đọc bài, không phải sale nhắn.
# Ranh giới từ \\b là thứ giữ cho cổng này không bắt oan: "prescription", "non-prescription",
# "description" đều chứa chuỗi "script" nhưng KHÔNG khớp. "prompt" chỉ bắt khi đi với
# system/my/the — "prompt delivery", "prompt reply" là chữ bán hàng bình thường.
LO_NOI_BO = re.compile(
    r"\\bscripts?\\b"
    r"|\\bkịch\\s*bản\\b"
    r"|\\b(?:system|my|the)\\s+prompts?\\b"
    r"|\\bmy\\s+(?:instructions|training|guidelines)\\b"
    r"|\\b(?:as an|i'?m an|i am an)\\s+(?:ai|a\\.?i\\.?)\\b"
    r"|\\blanguage model\\b",
    re.I | re.U)

# Ở Úc/Anh "script" còn là ĐƠN THUỐC ("a script from your doctor") — nghĩa hợp lệ, không chặn.
_LO_DON_THUOC = re.compile(r"doctor|pharmac|chemist|prescri|refill|GP\\b", re.I)


def lo_noi_bo(t):
    """Cụm chữ nội bộ đầu tiên trong `t`, hoặc None. Bỏ qua "script" nghĩa đơn thuốc."""
    for m in LO_NOI_BO.finditer(t or ""):
        if m.group(0).lower().startswith("script") \\
                and _LO_DON_THUOC.search(t[max(0, m.start() - 45):m.end() + 45]):
            continue
        return m.group(0)
    return None


def cat_cau_lo_noi_bo(t):
    """Bỏ nguyên câu có chữ nội bộ, giữ phần còn lại. Không sạch được thì trả None để đi đường khác."""
    goc = (t or "").strip()
    kq = _don_cau(" ".join(c for c in re.split(_NGAT_CAU, goc) if not lo_noi_bo(c)))
    if len(kq) < 40 or kq == goc or lo_noi_bo(kq):
        return None
    return kq
'''

thay(A1, M1, "1. LO_NOI_BO + lo_noi_bo() + cat_cau_lo_noi_bo()")


# ───────────────────── 2. Cổng mọi lượt ở tầng quyết định ─────────────────────
A2 = '''                # SỐ KHÔNG PHẢI SỐ BẢN ĐỊA Ở NƯỚC BẮT BUỘC (chủ shop 20/09, ca Lyn Amsiugal — Kuwait Amoura'''

M2 = '''                # LỘ CHỮ NỘI BỘ — MỌI LƯỢT (chủ shop 20/09, ca Jean Navarro — Golden Soap House KSA).
                # Model thiếu thông tin thì nói thẳng "our script doesn't list…" — ý đúng (không bịa),
                # chữ sai (gọi tên kịch bản). Sửa nhẹ TRƯỚC chứ không cắt máy trước như cổng thả khách:
                # câu lộ thường CHÍNH LÀ câu trả lời khách hỏi (ca Hermhey: "script không ghi cân nặng"),
                # cắt đi là khách hỏi mà không ai đáp. Cắt máy chỉ là lưới đỡ khi sửa nhẹ hỏng; gỡ không
                # được thì treo — thà sale trả lời tay còn hơn khoe kịch bản ra cho khách.
                _tin_lo = ((qd or {}).get("tin_nhan") or "").strip()
                _cum_lo = (lo_noi_bo(_tin_lo) if not err_m and qd and _tin_lo
                           and qd.get("hanh_dong") in ("tra_loi", "tra_loi_treo", "len_don") else None)
                if _cum_lo:
                    dem["lo_noi_bo"] = dem.get("lo_noi_bo", 0) + 1
                    print(f"{nhan} 🕵️  lộ chữ nội bộ [{_cum_lo}] — bắt viết lại")
                    _nhe_lo = _thu_sua_nhe(
                        nhan, dem, "lộ chữ nội bộ", _tin_lo,
                        "The draft names our internal sales script (\\"our script\\", \\"the script doesn't list…\\", "
                        "\\"nasa script namin\\"). The customer must never learn there is a script behind this chat — "
                        "it reads like a machine reading lines. Rewrite WITHOUT any such word: if the detail really is "
                        "missing, say plainly that you are checking with the shop and will confirm shortly, the way a "
                        "salesperson would. Keep the rest of the answer and the closing question, same language as the "
                        "draft, 1-2 short sentences, keep every number unchanged.", msgs,
                        lambda t: not lo_noi_bo(t) and len(t) >= 30)
                    _cat_lo = cat_cau_lo_noi_bo(_tin_lo)
                    if _nhe_lo:
                        qd["tin_nhan"] = _nhe_lo
                    elif _cat_lo:
                        print(f"{nhan} 🕵️  bỏ câu lộ chữ nội bộ bằng CODE — không gọi thêm model")
                        dem["lo_noi_bo_cat"] = dem.get("lo_noi_bo_cat", 0) + 1
                        qd["tin_nhan"] = _cat_lo
                    else:
                        print(f"{nhan} 🕵️  không gỡ được chữ nội bộ — treo cho sale")
                        dem["lo_noi_bo_treo"] = dem.get("lo_noi_bo_treo", 0) + 1
                        qd = {"hanh_dong": "treo", "tin_nhan": "",
                              "ly_do": "tin lộ chữ nội bộ (kịch bản/script)",
                              "ghi_chu": "AI định nói với khách 'kịch bản của tôi không có thông tin này' — "
                                         "sale trả lời tay: hỏi shop thông số khách cần rồi báo lại"}
                    if qd.get("tin_phan") and any(lo_noi_bo(x) for x in qd["tin_phan"]):
                        qd.pop("tin_phan", None)

''' + A2

thay(A2, M2, "2. cổng lộ chữ nội bộ (sửa nhẹ → cắt máy → treo)")


# ───────────────────── 3. Lưới cuối ngay trước khi gửi thật ─────────────────────
A3 = '''        log(f"   📵 bỏ câu có số WhatsApp đã ngưng khỏi tin sắp gửi: {text[:100]!r}")
        text = _sach_wa
'''

M3 = A3 + '''    # LƯỚI CUỐI CHO CHỮ NỘI BỘ (20/09) — bắt những đường không qua cổng ở tầng quyết định:
    # bong bóng thứ 2-3 của bước kịch bản, tin gửi lại sau lỗi, mẫu trả lời nhanh. Đo cùng ngày:
    # 0/8 bộ kịch bản của shop chứa chữ này, nên lưới này không đụng vào chữ shop viết.
    if text and lo_noi_bo(text):
        _sach_lo = cat_cau_lo_noi_bo(text)
        if not _sach_lo:
            log(f"   🕵️  tin lộ chữ nội bộ, gỡ không được — KHÔNG gửi: {text[:100]!r}")
            return True, None
        log(f"   🕵️  bỏ câu lộ chữ nội bộ khỏi tin sắp gửi: {text[:100]!r}")
        text = _sach_lo
'''

thay(A3, M3, "3. lưới cuối trong gui_tin()")


# ───────────────────────────── ghi ─────────────────────────────
import py_compile
import tempfile

with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
    fh.write(s)
    tmp = fh.name
try:
    py_compile.compile(tmp, doraise=True)
except py_compile.PyCompileError as e:
    print("✖ bản mới KHÔNG biên dịch được — không ghi gì:", e)
    sys.exit(1)

open(BAK, "w", encoding="utf-8").write(open(F, encoding="utf-8").read())
open(F, "w", encoding="utf-8").write(s)
print(f"\n✅ đã vá {F}\n   bản cũ: {BAK}")

# -*- coding: utf-8 -*-
"""Vá 21/09: ghi chú CÙNG MỘT VIỆC chỉ ghi 1 lần cho mỗi hội thoại.

Chủ shop 21/09 (ca Melah M Enalang, page DOC Alipion-Tooth ARMOR KSA): hai ghi chú y hệt nhau
"Khách muốn nhận hàng ở PHILIPPINES… page này bán ở SAUDI" cách nhau 2 phút (14:47, 14:49) —
"các note giống nhau thì note 1 lần thôi, note gì lắm thế".

Chạy: python3 va_note_1lan.py            (vá /opt/pancake-tool/ai_sale.py + ho_so.py)
      python3 va_note_1lan.py kiem       (chỉ kiểm tra dấu vết, không ghi)
Mỗi chỗ thay đều assert count == 1 — khớp khác 1 lần thì THOÁT mà không ghi gì.
"""
import re, sys, os, shutil, time

THU_MUC = os.environ.get("PT_DIR", "/opt/pancake-tool")
AI = os.path.join(THU_MUC, "ai_sale.py")
HO = os.path.join(THU_MUC, "ho_so.py")

# ───────────────────────── ho_so.py ─────────────────────────
HO_BANG_CU = """CREATE TABLE IF NOT EXISTS ghi_chu_da_ghi (
  conv_id  TEXT,
  loai     TEXT,
  luc      INTEGER,
  PRIMARY KEY (conv_id, loai)
);
"""
HO_BANG_MOI = HO_BANG_CU + """
-- Con số (giá, SĐT) đã từng đi vào ghi chú của hội thoại. Ghi chú sau trùng VIỆC nhưng mang
-- con số mới thì vẫn ghi — đó là tin mới cho sale, không phải lời nhờ lặp lại (chủ shop 21/09).
-- Bảng riêng vì `mo()` chỉ chạy CREATE TABLE IF NOT EXISTS: thêm cột không ăn trên kho cũ.
CREATE TABLE IF NOT EXISTS ghi_chu_so (
  conv_id  TEXT,
  so       TEXT,
  luc      INTEGER,
  PRIMARY KEY (conv_id, so)
);
"""

HO_HAM_CU = '''    cn.execute("INSERT OR IGNORE INTO ghi_chu_da_ghi (conv_id, loai, luc) VALUES (?,?,?)",
               (str(conv_id), loai, int(time.time())))
    cn.commit()
'''
HO_HAM_MOI = HO_HAM_CU + '''

def so_da_ghi_chu(cn, conv_id):
    """Những con số (giá, SĐT) đã từng nằm trong ghi chú của hội thoại này."""
    if cn is None:
        return set()
    return {r[0] for r in cn.execute("SELECT so FROM ghi_chu_so WHERE conv_id=?", (str(conv_id),))}


def nho_so_ghi_chu(cn, conv_id, so):
    """Nhớ các con số vừa đi vào ghi chú — lần sau biết ghi chú mới có tin mới hay chỉ nhắc lại."""
    if cn is None or not so:
        return
    luc = int(time.time())
    cn.executemany("INSERT OR IGNORE INTO ghi_chu_so (conv_id, so, luc) VALUES (?,?,?)",
                   [(str(conv_id), str(s), luc) for s in so])
    cn.commit()
'''

# ───────────────────────── ai_sale.py ─────────────────────────
AI_BANG_CU = '''# Ghi chú KHÔNG có tên trong bảng này vẫn ghi mọi lần: mỗi ca treo khác nhau mang tin khác nhau
# ("khách ở Nepal, page chỉ giao UAE", "khách khiếu nại đơn cũ đợi 3 tuần"…) — gộp lại là mất tin.
GHI_CHU_MOT_LAN = (
    ("xin_anh", re.compile(r"xin\\s*ảnh|gửi\\s*ảnh\\s*giúp", re.I)),
    # 20/09: note nhờ sale gửi ảnh feedback (page chưa có mẫu /Feedback) — cùng kiểu "một lần/hội thoại".
    ("xin_feedback", re.compile(r"xin\\s*feedback|ảnh\\s*feedback", re.I)),
)
'''
AI_BANG_MOI = '''# Ghi chú KHÔNG có tên trong bảng này vẫn ghi lại khi CHỮ khác đi: mỗi ca treo khác nhau mang tin
# khác nhau ("khách khiếu nại đơn cũ đợi 3 tuần"…) — gộp lại là mất tin. Nhưng bản sao chép ĐÚNG
# TỪNG CHỮ thì chặn được không cần có tên: loai_ghi_chu() tự lấy vân tay chữ ("van:…").
GHI_CHU_MOT_LAN = (
    ("xin_anh", re.compile(r"xin\\s*ảnh|gửi\\s*ảnh\\s*giúp", re.I)),
    # 20/09: note nhờ sale gửi ảnh feedback (page chưa có mẫu /Feedback) — cùng kiểu "một lần/hội thoại".
    ("xin_feedback", re.compile(r"xin\\s*feedback|ảnh\\s*feedback", re.I)),
    # 21/09 — chủ shop: "các note giống nhau thì note 1 lần thôi, note gì lắm thế" (ca Melah M
    # Enalang, page DOC Alipion-Tooth ARMOR KSA: hai lần y hệt "khách ở PHILIPPINES" cách 2 phút).
    # Những việc dưới đây lặp lại vì TÌNH HUỐNG của khách không đổi — khách vẫn ở nước khác, vẫn
    # chưa có giá, đơn vẫn nằm đó chờ duyệt — nên lượt nào model cũng mô tả lại. Sale chỉ cần biết
    # MỘT lần. Đo trên 7 ngày sổ việc thật: bỏ 94/1353 ghi chú, không ca nào mất việc giao cho sale.
    ("nuoc_khac", re.compile(r"mà page này (bán|chỉ giao)|không giao được|không ship được|không nhận ship"
                             r"|giao quốc tế|khách (đang )?ở [\\wÀ-ỹ]+,? (không|page|shop)", re.I)),
    ("anh_ban", re.compile(r"nhạy cảm|quấy rối|spam tình dục", re.I)),
    ("voice", re.compile(r"voice note|tin thoại|ghi âm", re.I)),
    ("sdt_sai", re.compile(r"không phải số|sai định dạng số|số không hợp lệ", re.I)),
    ("bao_gia", re.compile(r"báo giá|chưa có giá|không có (mức|giá)|bảng giá (không|chỉ)", re.I)),
    ("chot_don", re.compile(r"chốt đơn|lên đơn|đủ (info|thông tin|tên)|đơn đủ|complete info", re.I)),
)
'''

AI_HAM_CU = '''def loai_ghi_chu(gc):
    """Ghi chú này thuộc loại 'chỉ ghi một lần' nào? None = ghi bình thường, mọi lần."""
    if not gc or GHI_CHU_LUON_GHI.search(gc):
        return None
    for ten, mau in GHI_CHU_MOT_LAN:
        if mau.search(gc):
            return ten
    return None
'''
AI_HAM_MOI = '''_GC_NGOAC = re.compile(r\'"[^"]*"|“[^”]*”\')      # câu khách nói mà model trích vào ghi chú
_GC_CHU_SO = re.compile(r"\\d+([.,]\\d+)*")
_GC_DAU = re.compile(r"[^\\wÀ-ỹ ]+")


def _van_tay_ghi_chu(gc):
    """Vân tay CHỮ của ghi chú: bỏ số, bỏ câu khách nói trong ngoặc kép, bỏ dấu câu, gộp khoảng trắng.

    Để nguyên chữ (không băm) cho đọc được thẳng trong bảng `ghi_chu_da_ghi` lúc truy lỗi.
    """
    s = _GC_NGOAC.sub(" ", gc or "")
    s = _GC_CHU_SO.sub(" ", s)
    s = _GC_DAU.sub(" ", s)
    return " ".join(s.lower().split())[:120]


def loai_ghi_chu(gc):
    """Ghi chú này thuộc VIỆC nào? Cùng việc thì mỗi hội thoại chỉ ghi một lần. None = luôn ghi."""
    if not gc or GHI_CHU_LUON_GHI.search(gc):
        return None
    for ten, mau in GHI_CHU_MOT_LAN:
        if mau.search(gc):
            return ten
    # Không thuộc việc có tên → vẫn chặn được bản chép lại y nguyên, bằng vân tay chữ.
    return "van:" + _van_tay_ghi_chu(gc)


_GC_SO_LIEN = re.compile(r"\\d[\\d.,]*\\d|\\d")          # số viết liền: giá, số lượng, SĐT không cách
_GC_SO_DAI = re.compile(r"\\+?\\d[\\d\\s.\\-]{6,}\\d")       # SĐT gõ rời: "6939 1082", "+971 50 891 1359"


def so_trong_ghi_chu(gc):
    """Con số ĐÁNG KỂ trong ghi chú — giá (≥3 chữ số) và SĐT (≥8). Đây là tin mới cho sale.

    Dấu cách KHÔNG được nối hai số rời nhau: "Buy 1 Get 1 109 SAR" phải ra {109} chứ không ra
    {1109}, nếu không thì ghi chú nào cũng "có số mới" và cổng gộp thành vô dụng.
    """
    ra = set()
    for m in _GC_SO_LIEN.finditer(gc or ""):
        chu = re.sub(r"\\D", "", m.group(0))
        if len(chu) >= 3:
            ra.add(chu)
    for m in _GC_SO_DAI.finditer(gc or ""):
        chu = re.sub(r"\\D", "", m.group(0))
        if len(chu) >= 8:
            ra.add(chu)
    return ra
'''

AI_CONG_CU = '''    loai_gc = loai_ghi_chu(gc)
    bo_gc = bool(loai_gc) and HS.da_ghi_chu(kho, conv_id, loai_gc)
'''
AI_CONG_MOI = '''    loai_gc = loai_ghi_chu(gc)
    # 21/09: trùng VIỆC thì bỏ — TRỪ khi ghi chú mới mang con số chưa từng ghi (SĐT khách vừa cho,
    # giá vừa chốt). Con số mới là tin mới cho sale, không phải lời nhờ nhắc lại.
    _so_gc = so_trong_ghi_chu(gc) if loai_gc else set()
    _so_moi = (_so_gc - HS.so_da_ghi_chu(kho, conv_id)) if _so_gc else set()
    bo_gc = bool(loai_gc) and not _so_moi and HS.da_ghi_chu(kho, conv_id, loai_gc)
'''

AI_NHO_CU = '''            HS.nho_ghi_chu(kho, conv_id, loai_gc)
'''
AI_NHO_MOI = '''            HS.nho_ghi_chu(kho, conv_id, loai_gc)
            HS.nho_so_ghi_chu(kho, conv_id, _so_gc)
'''

VA = [(HO, [(HO_BANG_CU, HO_BANG_MOI), (HO_HAM_CU, HO_HAM_MOI)]),
      (AI, [(AI_BANG_CU, AI_BANG_MOI), (AI_HAM_CU, AI_HAM_MOI),
            (AI_CONG_CU, AI_CONG_MOI), (AI_NHO_CU, AI_NHO_MOI)])]

DAU_VET = [(HO, ["def so_da_ghi_chu", "def nho_so_ghi_chu", "ghi_chu_so"]),
           (AI, ["def so_trong_ghi_chu", "def _van_tay_ghi_chu", '("nuoc_khac"', '("chot_don"',
                 "HS.so_da_ghi_chu", "HS.nho_so_ghi_chu"])]


def kiem():
    thieu = 0
    for f, cac in DAU_VET:
        s = open(f, encoding="utf-8").read()
        for d in cac:
            co = s.count(d)
            print(f"{'OK ' if co else 'MẤT'} {os.path.basename(f)}: {d}  ({co})")
            thieu += 0 if co else 1
    return thieu


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kiem":
        sys.exit(1 if kiem() else 0)
    if not kiem():
        print("→ đã vá rồi, không làm gì."); sys.exit(0)
    # 1) kiểm TOÀN BỘ chỗ thay khớp đúng 1 lần TRƯỚC khi ghi file nào
    ban = {}
    for f, cac in VA:
        s = open(f, encoding="utf-8").read()
        for cu, moi in cac:
            n = s.count(cu)
            if n != 1:
                print(f"DỪNG: {os.path.basename(f)} khớp {n} lần (cần 1):\n{cu[:90]}…"); sys.exit(2)
            s = s.replace(cu, moi, 1)
        ban[f] = s
    # 2) sao lưu rồi ghi
    moc = time.strftime("%Y%m%d-%H%M")
    for f, s in ban.items():
        shutil.copy2(f, f"{f}.bak-note1lan-{moc}")
        open(f, "w", encoding="utf-8").write(s)
        print("đã vá", f, "(bak-note1lan-" + moc + ")")
    print("--- kiểm lại dấu vết ---")
    sys.exit(1 if kiem() else 0)

"""Vá: khoá theo hội thoại trong xu_ly_mot (chống 2 tiến trình cùng tạo đơn). Khớp khác 1 lần thì KHÔNG ghi."""
import sys, io
f = sys.argv[1]
s = io.open(f, encoding="utf-8").read()

cu1 = '''def xu_ly_mot(record, products, dry):
    ex = extract(record, products)
    # ĐƯỜNG TẮT: hội thoại này đã gắn đơn nào chưa? Nhớ rồi thì đi thẳng vào đơn đó,
    # khỏi lật 300 đơn, và chắc chắn không đẻ đơn thứ hai.
    order, ly_do = don_da_nho(record["conversation_id"])
    khac = []
    if not order:
        order, ly_do, khac = find_existing(record["conversation_id"], ex["sdt"],
                                           page_id=record.get("page_id"))
    if order:
        ghi_chu = bo_sung_don_cu(order, ly_do, ex, record, dry)
        if not dry:
            nho_don(record["conversation_id"], order)    # nhớ lại cho chắc
    else:
        if khac:   # khách mua lại / mua ở page khác -> vẫn lên đơn mới, chỉ nhắc kiểm tra
            ma = ", ".join(f"#{o.get('display_id') or o.get('id')}" for o in khac[:3])
            ex["canh_bao"].append(f"khách còn đơn khác cùng SĐT ({ma}) — kiểm tra không phải đơn trùng")
        ghi_chu = tao_don_moi(ex, record, dry)
    if not dry:
        Q.cmd_mark(record["page_id"], record["conversation_id"], ghi_chu)
    # Mọi lần tool ĐỤNG vào đơn — tạo mới hay bổ sung — đều trả hội thoại về CHƯA ĐỌC.
    danh_dau_chua_doc(record["page_id"], record["conversation_id"], dry)
'''
moi1 = '''# ═════════════════════════════════════════════════════════════════════════════
# KHOÁ THEO HỘI THOẠI — hai tiến trình không được cùng lên đơn cho một hội thoại
# ═════════════════════════════════════════════════════════════════════════════
# CA THẬT (Anabelle Magbanua, Kreain Nature PH in Uae, 14/09/2026): khách gửi SĐT + địa chỉ
# lúc 04:49:15. Daemon (vòng "lên đơn không tag", 30s) và AI Sale (bước "lên đơn sớm", 8s)
# CÙNG thấy tin đó, CÙNG hỏi POS "đã có đơn chưa" (mất 10-15s) khi chưa bên nào tạo → cả hai
# đều tin là chưa có → #49886 lúc 04:50:18 rồi #49887 lúc 04:50:27, cách nhau 9 giây.
# Sổ don_theo_hoi_thoai và find_existing đều đúng — chỉ là hai bên kiểm CÙNG LÚC.
# Nên: mỗi hội thoại một khoá file (flock). Bên đến sau phải ĐỢI bên trước làm xong (kiểm +
# tạo + ghi sổ), rồi mới vào — lúc đó sổ đã có đơn, nó chỉ bổ sung vào đúng đơn đó.
# Khoá nằm trong state/<tt>/khoa/ nên daemon và AI Sale (cùng máy, cùng thị trường) dùng chung.

class _KhoaHoiThoai:
    def __init__(self, conv_id):
        self.conv_id = str(conv_id or "")
        self.fh = None

    def __enter__(self):
        if not self.conv_id:
            return self
        try:
            import fcntl
            d = os.path.join(Q.STATE_DIR, "khoa")
            os.makedirs(d, exist_ok=True)
            ten = re.sub(r"[^0-9A-Za-z_.-]", "_", self.conv_id)[:150]
            self.fh = open(os.path.join(d, ten + ".lock"), "a+")
            t0 = time.time()
            fcntl.flock(self.fh, fcntl.LOCK_EX)
            if time.time() - t0 > 1:
                log(f"  🔒 hội thoại {self.conv_id} đang được tiến trình khác lên đơn — "
                    f"đã đợi {time.time()-t0:.0f}s rồi mới vào (chỉ bổ sung, không tạo thêm)")
        except Exception as e:                           # noqa: BLE001 — không khoá được thì vẫn chạy
            log(f"  ⚠️  không khoá được hội thoại {self.conv_id}: {e}")
            self.fh = None
        return self

    def __exit__(self, *a):
        if self.fh:
            try:
                import fcntl
                fcntl.flock(self.fh, fcntl.LOCK_UN)
                self.fh.close()
            except Exception:                            # noqa: BLE001
                pass
        return False


def xu_ly_mot(record, products, dry):
    with _KhoaHoiThoai(record.get("conversation_id")):
        _xu_ly_mot_da_khoa(record, products, dry)


def _xu_ly_mot_da_khoa(record, products, dry):
    ex = extract(record, products)
    # ĐƯỜNG TẮT: hội thoại này đã gắn đơn nào chưa? Nhớ rồi thì đi thẳng vào đơn đó,
    # khỏi lật 300 đơn, và chắc chắn không đẻ đơn thứ hai.
    # (đọc sổ SAU KHI đã cầm khoá — bên kia vừa tạo xong thì sổ đã có đơn của nó)
    order, ly_do = don_da_nho(record["conversation_id"])
    khac = []
    if not order:
        order, ly_do, khac = find_existing(record["conversation_id"], ex["sdt"],
                                           page_id=record.get("page_id"))
    if order:
        ghi_chu = bo_sung_don_cu(order, ly_do, ex, record, dry)
        if not dry:
            nho_don(record["conversation_id"], order)    # nhớ lại cho chắc
    else:
        if khac:   # khách mua lại / mua ở page khác -> vẫn lên đơn mới, chỉ nhắc kiểm tra
            ma = ", ".join(f"#{o.get('display_id') or o.get('id')}" for o in khac[:3])
            ex["canh_bao"].append(f"khách còn đơn khác cùng SĐT ({ma}) — kiểm tra không phải đơn trùng")
        ghi_chu = tao_don_moi(ex, record, dry)
    if not dry:
        Q.cmd_mark(record["page_id"], record["conversation_id"], ghi_chu)
    # Mọi lần tool ĐỤNG vào đơn — tạo mới hay bổ sung — đều trả hội thoại về CHƯA ĐỌC.
    danh_dau_chua_doc(record["page_id"], record["conversation_id"], dry)
'''
n = s.count(cu1)
assert n == 1, f"khớp {n} lần, không ghi"
assert "_KhoaHoiThoai" not in s, "đã vá rồi"
io.open(f, "w", encoding="utf-8").write(s.replace(cu1, moi1))
print("✔ đã vá", f)

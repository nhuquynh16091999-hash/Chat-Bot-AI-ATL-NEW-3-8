#!/usr/bin/env python3
"""Vá KỊCH BẢN MỚI VỀ TRONG ~2 PHÚT ở page đang có khách — chủ shop duyệt 21/09/2026.

Luồng nền riêng trong mỗi tiến trình `ai_sale.py theo_doi`: vòng dò chỉ GHI page vừa có khách nhắn, luồng
nền hỏi phiên bản kịch bản các page đó (mỗi page ≤ 1 lần / 2 phút), page vừa sửa thì tải lại và ghi
kich_ban.json. Lượt trả lời khách không đợi gì → tốc độ rep giữ nguyên.

Cách dùng:  python3 va_kb_nong.py /opt/pancake-tool/ai_sale.py
Mỗi chỗ thay phải khớp ĐÚNG 1 lần, lệch là thoát KHÔNG ghi. Chạy lại trên file đã vá thì tự từ chối.
Tắt nhanh không cần sửa code: AI_KB_NONG=0 trong .env rồi restart service.
"""
import os
import shutil
import sys
import time

f = sys.argv[1] if len(sys.argv) > 1 else "/opt/pancake-tool/ai_sale.py"
src = open(f, encoding="utf-8").read()
if "def _bat_luong_kb_nong(" in src:
    sys.exit("đã vá rồi (có def _bat_luong_kb_nong) — không làm gì")

THAY = []

# 1. Khối luồng nền — đặt ngay trước cmd_chay (sau _keo_kich_ban_thieu, dùng chung khoá _KB_KEO_KHOA).
THAY.append(("\n\ndef cmd_chay(mkey, page_loc=None,", '''

# ── KỊCH BẢN MỚI VỀ TRONG ~2 PHÚT Ở PAGE ĐANG CÓ KHÁCH (chủ shop duyệt 21/09) ────────────────────────────
# Chủ shop hỏi *"khi có kịch bản mới là bạn tự kéo về để tư vấn theo kịch bản mới luôn đúng k"*: daemon lên
# đơn (auto_len_don.dong_bo_kich_ban) soát phiên bản MỌI page 15 phút/lần → sửa xong có khi 15 phút AI mới
# dùng bản mới. Hỏi phiên bản ngay trước khi soạn thì chậm thêm ~1 giây/tin (đo 21/09 trên 15 page UAE: một
# lần hỏi 0,9-3,3s, trung vị 1,0s) — chủ shop hỏi *"có làm rep chậm toàn tin nhắn mới k"* → chọn LUỒNG NỀN:
# vòng dò chỉ ghi page vừa có KHÁCH nhắn (_kb_nong_ghi), luồng này hỏi phiên bản các page đó, mỗi page tối đa
# 1 lần / KB_NONG_KIEM giây, page vừa sửa thì tải lại + ghi kich_ban.json → lượt xử kế tiếp tự nạp (_KB_DEM so
# mtime). Page vừa nóng lại thì đánh thức luồng ngay, không đợi hết nhịp. Đo 24h: 10-17 page có khách mỗi 10
# phút cả 6 nước → ~10-20 nghìn lượt hỏi nhẹ (~100 byte) mỗi ngày, ít hơn vòng 15 phút của daemon.
# Daemon vẫn soát toàn bộ 15 phút/lần cho page vắng khách. Tắt: AI_KB_NONG=0 trong .env rồi restart.
KB_NONG_KIEM = 120          # giây — một page hỏi phiên bản tối đa 1 lần / 2 phút
KB_NONG_PHUT = 15           # chỉ hỏi page có khách nhắn trong 15 phút qua
KB_NONG_NHIP = 15           # giây — nhịp thức của luồng nền
_KB_NONG = {}               # pid -> lúc vòng dò thấy khách nhắn ở page này gần nhất
_KB_NONG_HOI = {}           # pid -> lúc hỏi phiên bản gần nhất
_KB_NONG_LUONG = []         # luồng đã bật (1 luồng / tiến trình)
_KB_NONG_THUC = _threading.Event()


def _kb_nong_ghi(pids):
    """Vòng dò báo: page này vừa có khách nhắn. Page chưa hỏi phiên bản gần đây → đánh thức luồng nền ngay."""
    now = time.time()
    thuc = False
    for p in pids:
        if not p:
            continue
        p = str(p)
        _KB_NONG[p] = now
        if now - _KB_NONG_HOI.get(p, 0) >= KB_NONG_KIEM:
            thuc = True
    if thuc:
        _KB_NONG_THUC.set()


def _kb_nong_mot_vong(mkey, tok):
    """Hỏi phiên bản kịch bản các page đang có khách; page vừa sửa trên Pancake thì tải lại. Trả số page đổi."""
    import kich_ban as KB
    now = time.time()
    can = [p for p, t in list(_KB_NONG.items())
           if now - t <= KB_NONG_PHUT * 60 and now - _KB_NONG_HOI.get(p, 0) >= KB_NONG_KIEM]
    moi = {}
    for pid in can:
        _KB_NONG_HOI[pid] = time.time()
        cu = _kb_page(mkey, pid) or {}
        if not cu.get("mau"):
            continue                    # page chưa có kịch bản: _keo_kich_ban_thieu lo
        doi, _ver, err = KB.kiem_phien_ban(pid, tok, cu.get("phien_ban"))
        if err or not doi:
            continue                    # hết gói / mạng chập: bỏ lượt này, daemon 15 phút vẫn soát
        m, err = KB.tai_1_page(pid, tok)
        if err or not m or not m.get("mau"):
            continue
        moi[pid] = {"ten_page": cu.get("ten_page"), "phien_ban": m["phien_ban"],
                    "chu_de": [{"id": c.get("id"), "ten": c.get("text") or c.get("name")} for c in m["chu_de"]],
                    "mau": [KB._gon(x) for x in m["mau"]], "tai_luc": int(time.time())}
    if not moi:
        return 0
    fkb = os.path.join(SCRIPT_DIR, "state", mkey, "kich_ban.json")
    with _KB_KEO_KHOA:
        try:                            # đọc LẠI ngay trước khi ghi: daemon lên đơn cũng ghi file này
            kb = json.load(open(fkb, encoding="utf-8"))
        except Exception:               # noqa: BLE001 — đọc hỏng (daemon đang ghi dở): KHÔNG ghi đè, lượt sau thử lại
            for pid in moi:
                _KB_NONG_HOI[pid] = 0
            return 0
        kb.update(moi)
        tam = fkb + ".tam-nong"
        with open(tam, "w", encoding="utf-8") as fh:
            json.dump(kb, fh, ensure_ascii=False, indent=1)
        os.replace(tam, fkb)
    print("  📋 KỊCH BẢN MỚI (page đang có khách): "
          + " · ".join(f"{(v.get('ten_page') or p)[:28]} ({len(v['mau'])} mẫu)" for p, v in moi.items()),
          flush=True)
    return len(moi)


def _bat_luong_kb_nong(mkey):
    """Bật luồng nền kéo kịch bản mới cho page đang có khách (1 luồng / tiến trình theo_doi)."""
    if _KB_NONG_LUONG or not _so_env("AI_KB_NONG", 1):
        return

    def _chay():
        while True:
            _KB_NONG_THUC.wait(KB_NONG_NHIP)
            _KB_NONG_THUC.clear()
            try:
                tok = env().get("PANCAKE_USER_TOKEN", "")
                if tok:
                    _kb_nong_mot_vong(mkey, tok)
            except Exception as e:      # noqa: BLE001 — luồng nền hỏng không được giết vòng dò
                print(f"  ⚠ luồng kịch bản nền lỗi: {e!r}", flush=True)
                time.sleep(KB_NONG_NHIP)

    t = _threading.Thread(target=_chay, name="kb_nong", daemon=True)
    t.start()
    _KB_NONG_LUONG.append(t)
    print(f"  📋 luồng nền kịch bản: page có khách trong {KB_NONG_PHUT} phút → hỏi phiên bản mỗi "
          f"{KB_NONG_KIEM // 60} phút, đổi thì kéo về ngay", flush=True)


def cmd_chay(mkey, page_loc=None,'''))

# 2. Bật luồng khi vòng dò khởi động.
THAY.append(('''    print(f"👀 dò nhanh {mkey}: {len(pages)} page · mỗi {giay}s · đợi Botcake {cho}s "
          f"(chỉ ở page có Botcake) · {'GỬI THẬT' if that else 'CHẠY THỬ'}", flush=True)
''', '''    print(f"👀 dò nhanh {mkey}: {len(pages)} page · mỗi {giay}s · đợi Botcake {cho}s "
          f"(chỉ ở page có Botcake) · {'GỬI THẬT' if that else 'CHẠY THỬ'}", flush=True)
    _bat_luong_kb_nong(mkey)           # kịch bản mới về trong ~2 phút ở page đang có khách (21/09)
'''))

# 3. Vòng dò ghi page vừa có KHÁCH nhắn.
THAY.append(('''        for cid in moi:
            nong[cid] = time.time()
            cho_xu.add(cid)
''', '''        for cid in moi:
            nong[cid] = time.time()
            cho_xu.add(cid)
        _kb_nong_ghi(str((thong_tin.get(k) or {}).get("page_id") or k.split("_")[0])
                     for k in moi if loai.get(k) == "khach")
'''))

moi_src = src
for i, (a, b) in enumerate(THAY, 1):
    n = moi_src.count(a)
    if n != 1:
        sys.exit(f"❌ chỗ {i}: khớp {n} lần (cần đúng 1) — KHÔNG ghi gì. Đoạn: {a[:90]!r}")
    moi_src = moi_src.replace(a, b)

compile(moi_src, f, "exec")
bak = f"{f}.bak-{time.strftime('%Y%m%d-%H%M')}-truoc-kb-nong"
shutil.copy2(f, bak)
tam = f"{f}.tam-{os.getpid()}"
open(tam, "w", encoding="utf-8").write(moi_src)
os.replace(tam, f)
print(f"✅ đã vá {len(THAY)} chỗ · bak: {bak}")

"""Vá 19/09 — danh sách page hỏi hỏng thì dùng bản tốt gần nhất, KHÔNG để page chạy kênh tài khoản biến mất.

Ca Boyet Salamat Torres · ClearVision Eye Care Saudi: khách nhắn 14:49-14:58 VN (hỏi phí ship, gửi đơn + địa chỉ + SĐT,
hỏi hàng chính hãng), sale Thu Hiền rep 15:00. aisale-chat-saudi khởi động lại 14:53 đúng lúc pages.fm/api/v1/pages
hỏng → `_bang_con_goi` = None (không lọc gói, 79 page) và `_pages_khong_quyen` = [] → 12 page không token (có
ClearVision Saudi) VẮNG khỏi danh sách AI trông tới lần tra lại 10 phút sau. Log: dòng "👀 dò nhanh saudi: 79 page",
thiếu "⏸ bỏ 28 page" và "👤 12 page không có token". Mỗi lần tra lại 10 phút/lần hỏng cũng y như vậy.

Sửa: `_ds_page_tai_khoan()` dùng chung — thử 3 lần, hỏng thì bản trong bộ nhớ, rồi bản lưu đĩa ≤24 giờ
(state/chung/ds_page_tai_khoan.json). `_pages_cua_shop` (POS) hỏng thì dùng bản lưu state/<tt>/pages_cua_shop.json ≤24 giờ.
Chạy: python3 va_ds_page_ben.py ai_sale.py  (khớp khác 1 lần → thoát, KHÔNG ghi)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_ds_page_tai_khoan" in src:
    sys.exit("đã vá rồi (có _ds_page_tai_khoan) — không làm gì")
if "_page_gan_them" not in src:
    sys.exit("thiếu vá _page_gan_them (va_gan_theo_tien_te.py) — vá cái đó trước")

HAM = '''_DS_PAGE_TK = {"luc": 0.0, "ds": None}


def _ds_page_tai_khoan():
    """Danh sách page tài khoản AI thấy trên Pancake (pages.fm/api/v1/pages) — nguồn chung cho bảng còn gói
    (`_bang_con_goi`) và page chạy kênh tài khoản (`_pages_khong_quyen`).

    19/09 (ca Boyet Salamat Torres · ClearVision Eye Care Saudi): service khởi động lại 14:53 VN đúng lúc lệnh
    này hỏng → 12 page không token vắng khỏi danh sách AI trông ~10 phút; khách nhắn 14:49-14:58 không ai rep.
    Nay: thử 3 lần; hỏng hết thì dùng bản tốt gần nhất — bộ nhớ, rồi file lưu ≤24 giờ. None = chưa từng có bản nào."""
    tok_user = env().get("PANCAKE_USER_TOKEN", "")
    if not tok_user:
        return None
    if _DS_PAGE_TK["ds"] is not None and time.time() - _DS_PAGE_TK["luc"] < 60:
        return _DS_PAGE_TK["ds"]           # _bang_con_goi + _pages_khong_quyen gọi liền nhau → 1 lần hỏi
    f = os.path.join(SCRIPT_DIR, "state", "chung", "ds_page_tai_khoan.json")
    loi = None
    for lan in range(3):
        res, err = _get("https://pages.fm/api/v1/pages", {"access_token": tok_user}, thu_lai=3)
        ps = None if (err or not res) else (res.get("pages") or (res.get("categorized") or {}).get("activated"))
        if ps:
            _DS_PAGE_TK.update(luc=time.time(), ds=ps)
            try:
                tam = f"{f}.{os.getpid()}.tmp"
                with open(tam, "w", encoding="utf-8") as g:
                    json.dump({"luc": time.time(), "pages": ps}, g, ensure_ascii=False)
                os.replace(tam, f)
            except Exception:                            # noqa: BLE001 — lưu hỏng không chặn vòng
                pass
            return ps
        loi = err or "API trả rỗng"
        if lan < 2:
            time.sleep(1 + 2 * lan)
    if _DS_PAGE_TK["ds"] is not None:
        print(f"  ⚠️  hỏi danh sách page Pancake hỏng ({loi}) — dùng bản trong bộ nhớ", flush=True)
        return _DS_PAGE_TK["ds"]
    try:
        d = json.load(open(f, encoding="utf-8"))
        tuoi = time.time() - float(d.get("luc") or 0)
        if tuoi < 86400 and d.get("pages"):
            print(f"  ⚠️  hỏi danh sách page Pancake hỏng ({loi}) — dùng bản lưu {tuoi / 60:.0f} phút trước", flush=True)
            _DS_PAGE_TK["ds"] = d["pages"]          # luc giữ 0 → lần gọi sau vẫn hỏi lại mạng
            return d["pages"]
    except Exception:                                    # noqa: BLE001
        pass
    print(f"  🚨 hỏi danh sách page Pancake hỏng ({loi}) và không có bản lưu — page chạy kênh tài khoản vắng mặt", flush=True)
    return None


def _bang_con_goi():
'''

VA = [
    ("def _bang_con_goi():\n", HAM),
    ('''    res, err = _get("https://pages.fm/api/v1/pages", {"access_token": tok_user})
    ps = [] if (err or not res) else (res.get("pages") or (res.get("categorized") or {}).get("activated") or [])
    if not ps:
        return _CON_GOI["bang"]''',
     '''    ps = _ds_page_tai_khoan() or []
    if not ps:
        return _CON_GOI["bang"]'''),
    ('''    res, err = _get("https://pages.fm/api/v1/pages", {"access_token": tok_user})
    if err or not res:
        return []
    ps = res.get("pages") or (res.get("categorized") or {}).get("activated") or []''',
     '''    ps = _ds_page_tai_khoan()
    if not ps:
        return []'''),
    # POS: hỏng thì dùng bản lưu, thành công thì lưu lại
    ('''        print(f"  ⚠️  không tra được danh sách page của shop {mkey} ({e}) — BỎ QUA bước lọc,"
              f" hãy tự kiểm tên page in ra bên dưới có đúng thị trường không")
        return None''',
     '''        try:                                             # 19/09: dùng bản lưu gần nhất ≤24 giờ
            d = json.load(open(os.path.join(SCRIPT_DIR, "state", mkey, "pages_cua_shop.json"), encoding="utf-8"))
            if time.time() - float(d.get("luc") or 0) < 86400 and d.get("ids"):
                print(f"  ⚠️  không tra được danh sách page của shop {mkey} ({e}) — dùng bản lưu "
                      f"{(time.time() - float(d['luc'])) / 60:.0f} phút trước", flush=True)
                return set(d["ids"]) | _page_gan_them(mkey)
        except Exception:                                # noqa: BLE001
            pass
        print(f"  ⚠️  không tra được danh sách page của shop {mkey} ({e}) — BỎ QUA bước lọc,"
              f" hãy tự kiểm tên page in ra bên dưới có đúng thị trường không")
        return None'''),
    ('''            return {str(x.get("id")) for x in (sh.get("pages") or []) if x.get("id")} | _page_gan_them(mkey)''',
     '''            _ids = {str(x.get("id")) for x in (sh.get("pages") or []) if x.get("id")}
            if _ids:
                try:
                    _f = os.path.join(SCRIPT_DIR, "state", mkey, "pages_cua_shop.json")
                    with open(f"{_f}.{os.getpid()}.tmp", "w", encoding="utf-8") as g:
                        json.dump({"luc": time.time(), "ids": sorted(_ids)}, g)
                    os.replace(f"{_f}.{os.getpid()}.tmp", _f)
                except Exception:                        # noqa: BLE001
                    pass
            return _ids | _page_gan_them(mkey)'''),
]
for cu, moi in VA:
    n = src.count(cu)
    if n != 1:
        sys.exit(f"❌ khớp {n} lần (phải đúng 1) — KHÔNG ghi gì:\n{cu[:200]}")
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"✔ đã vá {len(VA)} chỗ")

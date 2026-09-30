"""Vá 17/09 tối: phanh hết tiền đọc THÂN lỗi 429 của Kimi + rút cửa sổ dừng 30 → 5 phút.
Chạy: python3 va_than_loi_429.py ai_sale.py   (mỗi chỗ phải khớp đúng 1 lần, không thì không ghi)"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_than_loi_429" in src:
    sys.exit("đã vá rồi — không làm gì")

CU_1 = '''    except Exception as e:
        _l = str(e)
        if ("exceeded_current_quota" in _l or "insufficient" in _l.lower()
                or ("429" in _l and "quota" in _l.lower())):
            _HET_QUOTA.update(luc=time.time(), loi=_l[:200])
        return None, _l
'''
MOI_1 = '''    except Exception as e:
        _l = str(e)
        # 17/09 tối: Kimi hết tiền trả HTTP 429 nhưng str(e) CHỈ là "HTTP Error 429: Too Many
        # Requests" — chữ "exceeded_current_quota_error" nằm trong THÂN lỗi. Không đọc thân thì
        # phanh hết tiền không bao giờ bật: 22:32→22:47 giờ VN, 322 lượt khách bị mở ra đọc rồi
        # soạn hỏng, ở page kênh tài khoản còn hiện "AI LEADER đã xem".
        _than_loi_429 = ""
        if hasattr(e, "read"):
            try:
                _than_loi_429 = e.read().decode("utf-8", "replace")[:500]
            except Exception:                            # noqa: BLE001
                _than_loi_429 = ""
        _xet = f"{_l} {_than_loi_429}"
        if ("exceeded_current_quota" in _xet or "insufficient" in _xet.lower()
                or ("429" in _l and "quota" in _xet.lower())):
            _loai = ""
            try:
                _loai = (json.loads(_than_loi_429).get("error") or {}).get("type") or ""
            except Exception:                            # noqa: BLE001
                pass
            _HET_QUOTA.update(luc=time.time(),
                              loi=(f"{_l} · {_loai}" if _loai else _xet.strip())[:200])
        return None, _l
'''
CU_2 = 'def het_tien_that(trong_phut=30):\n'
MOI_2 = 'def het_tien_that(trong_phut=5):\n'
CU_3 = '''    hoặc khi trần chi theo SỔ đã chạm.
    """
    return _HET_QUOTA["luc"]'''
MOI_3 = '''    hoặc khi trần chi theo SỔ đã chạm.

    17/09 tối: cửa sổ 30 → 5 phút (chủ shop duyệt). Trong lúc dừng không ai gọi model nên không có
    lỗi mới làm mốc; hết 5 phút vòng sau đọc lại + gọi thử — còn hết tiền thì dừng tiếp, đã nạp thì
    chạy luôn. 30 phút nghĩa là nạp xong phải chờ tới nửa tiếng AI mới trả lời lại.
    """
    return _HET_QUOTA["luc"]'''

for cu, moi in ((CU_1, MOI_1), (CU_2, MOI_2), (CU_3, MOI_3)):
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần (cần đúng 1) — file đã bị sửa vùng này, KHÔNG ghi:\n{cu[:80]}"
for cu, moi in ((CU_1, MOI_1), (CU_2, MOI_2), (CU_3, MOI_3)):
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("đã vá 3 chỗ")

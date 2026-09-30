"""VÁ 2: ghi sổ mô tả ảnh cho AN TOÀN khi 6 daemon cùng ghi (20/09).

`qht.save_json` ghi đè thẳng vào file thật — 6 tiến trình thị trường cùng ghi thì (a) tiến trình
này xoá mất mô tả tiến trình kia vừa thêm, (b) chết giữa chừng là file rách. Đổi thành: đọc lại,
GỘP, ghi ra file tạm rồi `os.replace` (đổi tên là thao tác nguyên tử trên cùng ổ đĩa).
"""
import ast
import os
import shutil
import sys
import time

F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_sale.py")

CU = '''    if xong:
        with _KHOA_MO_TA:
            try:
                d = _MO_TA_ANH
                if len(d) > ANH_NHO_TOI_DA:              # cũ nhất rơi trước (dict giữ thứ tự thêm vào)
                    d = dict(list(d.items())[-ANH_NHO_TOI_DA:])
                    _MO_TA_ANH.clear()
                    _MO_TA_ANH.update(d)
                qht.save_json(_f_mo_ta_anh(), dict(_MO_TA_ANH))
            except Exception:                            # noqa: BLE001 — sổ hỏng thì đọc lại lần sau
                pass
    return xong'''

MOI = '''    if xong:
        _ghi_so_mo_ta()
    return xong


def _ghi_so_mo_ta():
    """Ghi sổ mô tả: ĐỌC LẠI + GỘP + đổi tên file tạm.

    Sáu daemon thị trường dùng CHUNG một sổ. Ghi đè thẳng (qht.save_json) thì daemon này xoá mất
    mô tả daemon kia vừa thêm, và chết giữa chừng là file rách — lần sau đọc hỏng, đọc lại tất cả
    ảnh từ đầu. Đổi tên file là nguyên tử trên cùng ổ đĩa nên người đọc không bao giờ thấy file dở.
    """
    with _KHOA_MO_TA:
        try:
            f = _f_mo_ta_anh()
            os.makedirs(os.path.dirname(f), exist_ok=True)
            cu = qht.load_json(f, {}) or {}
            cu.update(_MO_TA_ANH)                        # mô tả mới đè mô tả cũ cùng URL
            if len(cu) > ANH_NHO_TOI_DA:                 # cũ nhất rơi trước (dict giữ thứ tự thêm vào)
                cu = dict(list(cu.items())[-ANH_NHO_TOI_DA:])
            tam = f"{f}.tam-{os.getpid()}"
            with open(tam, "w", encoding="utf-8") as fh:
                json.dump(cu, fh, ensure_ascii=False)
            os.replace(tam, f)
            _MO_TA_ANH.update(cu)                        # nhận luôn phần daemon khác vừa đọc
        except Exception:                                # noqa: BLE001 — sổ hỏng thì đọc lại lần sau
            pass'''


def main():
    that = "--that" in sys.argv
    s = open(F, encoding="utf-8").read()
    n = s.count(CU)
    assert n == 1, f"tìm thấy {n} chỗ khớp (phải đúng 1)"
    s = s.replace(CU, MOI, 1)
    ast.parse(s)
    print("  ✓ vá 1/1 · cú pháp hợp lệ")
    if not that:
        print("\n(xem trước — thêm --that để ghi thật)")
        return
    bak = f"{F}.bak-{time.strftime('%Y%m%d-%H%M')}-truoc-so-anh-nguyen-tu"
    shutil.copy2(F, bak)
    open(F, "w", encoding="utf-8").write(s)
    print(f"  ✓ đã ghi {F}\n  ✓ sao lưu {bak}")


main()

import json, os, sys
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import ai_sale as A, ho_so as HS

mkey = sys.argv[1]; so_page = int(sys.argv[2]) if len(sys.argv) > 2 else 12
pages = A._pages_cua_thi_truong(mkey)[:so_page]
tong = co_sdt = co_dc = du = rong = 0
for pid, st in pages:
    convs, err = A.hoi_thoai_gan_day(pid, st["token"], so=40, gio=24)
    if err:
        continue
    for c in convs:
        msgs, _cus, e = A.tin_cua_hoi_thoai(pid, c["id"], st["token"])
        if e or not msgs:
            continue
        tong += 1
        ten = ((c.get("customers") or [{}])[0].get("name") or "")
        co = HS.trich(msgs, mkey, ten_khach=ten)
        if co.get("sdt"): co_sdt += 1
        if co.get("dia_chi"): co_dc += 1
        if co.get("sdt") or co.get("dia_chi"): rong += 1
        if not HS.thieu(co, mkey): du += 1
print(f"\n  {mkey.upper()} — {len(pages)} page · {tong} hội thoại trong 24h\n")
print(f"    có SĐT                        {co_sdt:4d}")
print(f"    có địa chỉ                    {co_dc:4d}")
print(f"    ➡️  CÓ SĐT **HOẶC** ĐỊA CHỈ    {rong:4d}   ← số đơn 'Mới' luật mới sẽ tạo")
print(f"    ✅ đủ cả 5 trường              {du:4d}   ← số đơn được chuyển 'Đã xác nhận'")
if rong:
    print(f"\n    tỉ lệ đơn 'Mới' đi tiếp được: {du/rong:.0%}")
    print(f"    tức {rong-du} đơn nằm lại ở 'Mới' mỗi ngày, chỉ riêng {len(pages)} page này")

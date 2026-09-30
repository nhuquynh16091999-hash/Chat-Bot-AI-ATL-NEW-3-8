"""Vá 18/09 — DÒ NỀN page hỏi riêng (chủ shop: "bạn tốn thời gian lâu nhất ở khâu nào, phát hiện tin mới à").

Đo 18/09: lệnh gộp từ chối 75/80 page Saudi, 66/70 page UAE (mã 105 tài khoản AI không có quyền, 121 hết gói,
125 page bị vô hiệu hoá) → mỗi vòng dò phải hỏi riêng từng page và ĐỢI page chậm nhất: 7-20s/vòng, khách bị
phát hiện trễ 23-84s (Saudi), 58s (UAE). Tăng luồng / thu hẹp khung giờ không đỡ (đo: vẫn 7-15s).
Nay: page hỏi riêng chạy NỀN — mỗi page một yêu cầu, vòng dò lấy kết quả page nào đã về, không đợi page chậm;
page vừa về được hỏi lại sau ≥ AI_NHIP_PAGE_RIENG giây (mặc định 5). Nhịp vòng dò chỉnh được bằng AI_NHIP_DO.
Lượt mồi (lan 0) vẫn hỏi đủ, đợi đủ như cũ.
Chạy: python3 va_do_nen.py ai_sale.py   (mỗi chỗ phải khớp đúng 1 lần, không thì không ghi gì)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "hoi_nen = {}" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = []
VA.append((
    "    nhip = giay\n",
    "    # 18/09: nhịp vòng dò chỉnh được trong .env (AI_NHIP_DO) — vòng dò giờ nhẹ (không đợi lượt xử, không\n"
    "    # đợi page hỏi riêng) nên dò dày hơn được mà không nặng thêm.\n"
    "    giay = max(2, int(_so_env(\"AI_NHIP_DO\", giay)))\n"
    "    nhip = giay\n"
    "    hoi_nen, hoi_luc = {}, {}     # pid -> yêu cầu hỏi riêng đang chạy nền · lúc gửi yêu cầu gần nhất\n"
    "    bom_le = ThreadPoolExecutor(max_workers=int(_so_env(\"AI_LUONG_QUET\", 20)))\n",
))
VA.append((
    "                if _le:\n"
    '                    with ThreadPoolExecutor(max_workers=int(_so_env("AI_LUONG_QUET", 20))) as bom:\n'
    "                        ds += list(bom.map(lambda cap: _liet_ke(cap, 24 if lan == 0 else gio), _le))\n",
    "                if _le and lan == 0:\n"
    '                    with ThreadPoolExecutor(max_workers=int(_so_env("AI_LUONG_QUET", 20))) as bom:\n'
    "                        ds += list(bom.map(lambda cap: _liet_ke(cap, 24), _le))\n"
    "                elif _le:\n"
    "                    # 18/09: HỎI NỀN — không bắt vòng dò đợi page chậm nhất (Saudi 75 page: 7-20s/vòng,\n"
    "                    # khách bị phát hiện trễ 23-84s). Page nào đã về thì lấy, chưa về thì vòng sau lấy.\n"
    "                    for cap in _le:\n"
    "                        _p = str(cap[0])\n"
    "                        _fu = hoi_nen.get(_p)\n"
    "                        if _fu is not None and _fu.done():\n"
    "                            try:\n"
    "                                ds.append(_fu.result())\n"
    "                            except Exception as e:            # noqa: BLE001\n"
    "                                ds.append((cap[0], [], str(e)))\n"
    "                            hoi_nen.pop(_p, None)\n"
    "                            _fu = None\n"
    "                        if _fu is None and time.time() - hoi_luc.get(_p, 0) >= _so_env(\"AI_NHIP_PAGE_RIENG\", 5):\n"
    "                            hoi_luc[_p] = time.time()\n"
    "                            hoi_nen[_p] = bom_le.submit(_liet_ke, cap)\n",
))

for cu, moi in VA:
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần (cần đúng 1) — file đã bị sửa vùng này, KHÔNG ghi:\n{cu[:160]}"
for cu, moi in VA:
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"đã vá {len(VA)} chỗ")

"""Vá 17/09 khuya — TỐC ĐỘ TRẢ LỜI lượt 2.
  A. Chốt chặn 3 phút: chỉ đánh dấu chưa đọc, KHÔNG ghi chú (chủ shop: "khi hết tiền thì cứ đánh dấu chưa đọc
     là được, tôi tự check hết tiền").
  B. Báo trước "LƯỢT NÀY KHÔNG NÊU GIÁ" ở lượt soạn đầu — cổng nhắc giá bắt soạn lại ~50% câu Saudi (707 lượt),
     mỗi lần thêm một lượt chờ Kimi.
  C. Ghi thời gian mỗi lượt gọi model ("giay" trong state/chung/goi_model.jsonl).
  D. In thời gian mỗi lượt xử (đọc+lọc / soạn+gửi).
Chạy: python3 va_toc_do_rep_2.py ai_sale.py   (mỗi chỗ phải khớp đúng 1 lần, không thì không ghi gì)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "bao_truoc_khong_gia" in src:
    sys.exit("đã vá rồi — không làm gì")
assert "def canh_bao_cho_lau" in src, "chưa có vá tốc độ lượt 1 (va_toc_do_rep.py)"

VA = []

# ── A ────────────────────────────────────────────────────────────────────────────────
VA.append((
    '        cus = kh.get("id") or _CUST.get((pid, cid))\n'
    '        ok_cd, _ = danh_dau_chua_doc(pid, cid, st["token"], dry=False, lan=2, cho=1)   # 1 lượt từng trượt 1/31 ca\n'
    '        gc = f"[AI Sale] ⏰ Khách chờ {tre / 60:.0f} phút mà AI chưa trả lời được ({ly}) — sale rep giúp."\n'
    '        ok_gc, e = ghi_chu(pid, cus, st["token"], gc, dry=False) if cus else (False, "thiếu mã khách")\n'
    '        ten = kh.get("name") or (c.get("from") or {}).get("name") or "?"\n'
    '        return (f"  ⏰ [{ten[:20]}] khách chờ {tre / 60:.0f} phút, AI chưa trả lời ({ly}) → "\n'
    "                f\"ghi chú {'✔' if ok_gc else '✖ ' + str(e)[:60]} · chưa đọc {'✔' if ok_cd else '✖'}\")\n",
    '        ok_cd, _ = danh_dau_chua_doc(pid, cid, st["token"], dry=False, lan=2, cho=1)   # 1 lượt từng trượt 1/31 ca\n'
    '        # Chủ shop 17/09 khuya: "khi hết tiền thì cứ đánh dấu chưa đọc là được, tôi tự check hết tiền lúc nào"\n'
    '        # → KHÔNG ghi chú (bản đầu ghi "sale rep giúp" — chủ shop muốn AI rep, không giao sale).\n'
    '        ten = kh.get("name") or (c.get("from") or {}).get("name") or "?"\n'
    '        return (f"  ⏰ [{ten[:20]}] khách chờ {tre / 60:.0f} phút, AI chưa trả lời ({ly}) → "\n'
    "                f\"đánh dấu chưa đọc {'✔' if ok_cd else '✖'}\")\n",
))
VA.append((
    '    """Khách chờ quá AI_CANH_BAO_TRE giây (mặc định 180) mà AI chưa trả lời được → ghi chú +\n'
    '    đánh dấu chưa đọc NGAY cho sale, mỗi tin khách MỘT lần.\n',
    '    """Khách chờ quá AI_CANH_BAO_TRE giây (mặc định 180) mà AI chưa trả lời được → đánh dấu chưa\n'
    '    đọc NGAY, mỗi tin khách MỘT lần. KHÔNG ghi chú (chủ shop 17/09 khuya).\n',
))

# ── B ────────────────────────────────────────────────────────────────────────────────
VA.append((
    "            else:\n"
    "                qd, err_m = soan_bang_model(noi_dung, on_dinh)\n"
    "                # BẮT BUỘC ĐÚNG TIẾNG KHÁCH (chủ shop chốt 2026-09-10). Prompt vẫn có thể bị\n",
    "            else:\n"
    "                # 17/09 khuya — BÁO TRƯỚC \"LƯỢT NÀY KHÔNG NÊU GIÁ\". Cổng \"khách không hỏi giá mà model lại\n"
    "                # nhắc giá\" (bên dưới) bắt soạn lại ~50% câu ở Saudi (707 lượt trong log) — mỗi lần thêm một\n"
    "                # lượt chờ Kimi ~25-30s, khách chờ theo (chủ shop: \"chưa hết tiền bạn vẫn rep lâu\"). Cùng\n"
    "                # điều kiện đó biết được TRƯỚC khi gọi, nên nói luôn ở lượt đầu; cổng bên dưới vẫn là lưới.\n"
    "                # Không áp cho page tư vấn theo thứ tự (bước kịch bản có giá phải chép nguyên) và khách từ chối.\n"
    "                _khong_gia_ = False\n"
    "                try:\n"
    "                    _khong_gia_ = bool(\n"
    "                        \"PAGE NÀY TƯ VẤN THEO THỨ TỰ\" not in (noi_dung or \"\")\n"
    "                        and (tien_page_da_noi(msgs) or khach_hoi_san_pham(msgs) or khach_hoi_trong_tam(msgs))\n"
    "                        and not khach_hoi_gia_gan(msgs) and not khach_dang_cho_gia(msgs)\n"
    "                        and not khach_vua_chon_goi(msgs, mkey, gia) and not tinh_huong_tu_choi(msgs))\n"
    "                except Exception:                        # noqa: BLE001 — đoán hỏng thì soạn như cũ\n"
    "                    _khong_gia_ = False\n"
    "                if _khong_gia_:\n"
    "                    dem[\"bao_truoc_khong_gia\"] = dem.get(\"bao_truoc_khong_gia\", 0) + 1\n"
    "                qd, err_m = soan_bang_model(\n"
    "                    noi_dung + (\"\\n\\n⚠️ LƯỢT NÀY KHÔNG NÊU GIÁ: khách KHÔNG hỏi giá (page đã báo giá rồi, hoặc khách \"\n"
    "                                \"đang hỏi về sản phẩm). tin_nhan KHÔNG có con số tiền nào, không liệt kê combo, không \"\n"
    "                                \"tự hạ giá — trả lời đúng điều khách vừa nói rồi mời mua nhẹ nhàng. Ngoại lệ: chọn \"\n"
    "                                \"len_don thì câu xác nhận đơn vẫn ghi đúng số tiền đã chốt; chép nguyên mẫu của shop \"\n"
    "                                \"thì giữ nguyên.\" if _khong_gia_ else \"\"), on_dinh)\n"
    "                # BẮT BUỘC ĐÚNG TIẾNG KHÁCH (chủ shop chốt 2026-09-10). Prompt vẫn có thể bị\n",
))

# ── C ────────────────────────────────────────────────────────────────────────────────
VA.append((
    '    req = urllib.request.Request(url, data=body, method="POST", headers=dau)\n'
    "    try:\n"
    "        with urllib.request.urlopen(req, timeout=90) as r:\n",
    '    req = urllib.request.Request(url, data=body, method="POST", headers=dau)\n'
    "    _t_goi_ = time.time()                  # đo Kimi mất bao lâu mỗi lượt (17/09 khuya)\n"
    "    try:\n"
    "        with urllib.request.urlopen(req, timeout=90) as r:\n",
))
VA.append((
    '        "ra": u.get("output_tokens") or 0,\n'
    "    })\n"
    '    LAN_GOI_CUOI["tien"] = round(\n',
    '        "ra": u.get("output_tokens") or 0,\n'
    '        "giay": round(time.time() - _t_goi_, 1),\n'
    "    })\n"
    '    LAN_GOI_CUOI["tien"] = round(\n',
))

# ── D ────────────────────────────────────────────────────────────────────────────────
VA.append((
    "    # ── bước 2 + 3: soạn song song, hành động tuần tự ─────────────────────\n",
    "    # ── bước 2 + 3: soạn song song, hành động tuần tự ─────────────────────\n"
    "    _t_b23_ = time.time()                  # đo lượt xử (17/09 khuya)\n",
))
VA.append((
    "    if chi_hoi_thoai is not None and not goi_chua_soan:\n"
    "        return ket_qua\n",
    "    try:\n"
    "        print(f\"  ⏱  lượt xử {time.time() - t_doc:.0f}s — đọc+lọc {_t_b23_ - t_doc:.0f}s · \"\n"
    "              f\"soạn+gửi {time.time() - _t_b23_:.0f}s · {len(cac_viec)} việc soạn\"\n"
    "              + (f\" · báo trước không giá {dem['bao_truoc_khong_gia']}\" if dem.get('bao_truoc_khong_gia') else \"\"),\n"
    "              flush=True)\n"
    "    except NameError:\n"
    "        pass\n"
    "    if chi_hoi_thoai is not None and not goi_chua_soan:\n"
    "        return ket_qua\n",
))

for cu, moi in VA:
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần (cần đúng 1) — file đã bị sửa vùng này, KHÔNG ghi:\n{cu[:160]}"
for cu, moi in VA:
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"đã vá {len(VA)} chỗ")

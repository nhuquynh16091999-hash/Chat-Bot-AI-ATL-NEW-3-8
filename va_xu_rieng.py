"""Vá 18/09 — XỬ TỪNG KHÁCH RIÊNG (chủ shop: "tôi cần AI rep ngay trong vòng 1-2p").

Bản cũ: vòng dò gọi cmd_chay rồi ĐỨNG ĐỢI lượt đó xong mới dò tiếp → khách nhắn giữa lượt phải chờ hết lượt
trước + lượt của mình (Saudi 16/09: 45% khách chờ >3 phút dù Kimi còn tiền).
Nay: vòng dò KHÔNG đợi — tin mới được giao ngay cho một lượt xử chạy song song (tối đa AI_LUOT_SONG_SONG=3
lượt cùng lúc), mỗi hội thoại chỉ nằm trong MỘT lượt đang chạy. Kèm các khoá cho phần dùng chung:
  1. gui_tin: giữ CHỖ gửi dưới khoá (20s/page, 3s chung) — hai lượt không cùng lúc bắn vào một page;
     gửi hỏng thì trả chỗ để lần thử lại #2022 khỏi đợi 20s.
  2. sổ đã-trả-lời (dax) + sổ lên-đơn-sớm: ghi kiểu GỘP (đọc lại file, thêm mốc của lượt mình).
  3. sổ đã-xem (da_xem_chua_doc): sửa + ghi dưới khoá.
  4. _KHACH_NHAN_THEM: lượt nào chỉ lấy hội thoại của lượt đó.
  5. trong một lượt: hành động theo thứ tự SOẠN XONG TRƯỚC LÀM TRƯỚC (không đứng đợi câu soạn chậm đầu hàng).
Tắt nhanh: AI_LUOT_SONG_SONG=1 trong .env (một lượt một lúc; vòng dò vẫn không đứng đợi).
Chạy: python3 va_xu_rieng.py ai_sale.py   (mỗi chỗ phải khớp đúng 1 lần, không thì không ghi gì)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "_KHOA_GUI" in src:
    sys.exit("đã vá rồi — không làm gì")
assert "def canh_bao_cho_lau" in src and "bao_truoc_khong_gia" in src, "thiếu vá tốc độ lượt 1/2"

VA = []

# ── 1. giữ chỗ gửi ───────────────────────────────────────────────────────────────────
VA.append((
    "_LAN_GUI_CUOI = [0.0]\n",
    "_LAN_GUI_CUOI = [0.0]\n"
    "import threading as _thr_gui\n"
    "_KHOA_GUI = _thr_gui.Lock()     # 18/09: nhiều lượt xử gửi song song — giữ chỗ gửi dưới khoá (xem gui_tin)\n"
    "_HEN_GUI_PAGE = {}              # pid -> mốc gửi đã giữ chỗ gần nhất\n"
    "_HEN_GUI_CHUNG = [0.0]\n",
))
VA.append((
    '    _moc_page = (_GUI_THEO_PAGE.get(str(page_id)) or [0.0])[-1]\n'
    '    cho = max(0.0 if sau_anh else _so_env("AI_GIAN_CACH_GUI", 20) - (time.time() - _moc_page),\n'
    '              _so_env("AI_GIAN_CACH_CHUNG", 3) - (time.time() - _LAN_GUI_CUOI[0]))\n'
    "    if cho > 0:\n"
    "        time.sleep(cho)                      # giãn nhịp giữa hai lần gửi — luật 11/09\n"
    "    if _la_user(token) or (str(page_id) in _FB_CHAN and gui_qua_user_bat()):\n"
    "        return gui_tin_qua_user(page_id, conv_id, text)\n",
    "    # 18/09: nhiều lượt xử chạy SONG SONG → hai luồng có thể cùng thấy \"page rảnh\" rồi cùng gửi. Nên GIỮ\n"
    "    # CHỖ dưới khoá: mỗi lần gửi đặt trước một mốc giờ; lần sau cùng page phải sau mốc đó ≥ AI_GIAN_CACH_GUI,\n"
    "    # mọi page ≥ AI_GIAN_CACH_CHUNG. Đợi thì đợi NGOÀI khoá.\n"
    "    _p = str(page_id)\n"
    "    with _KHOA_GUI:\n"
    "        _bay_gio = time.time()\n"
    "        _moc_page = max((_GUI_THEO_PAGE.get(_p) or [0.0])[-1], _HEN_GUI_PAGE.get(_p, 0.0))\n"
    "        _luc_gui = max(_bay_gio,\n"
    "                       _bay_gio if sau_anh else _moc_page + _so_env(\"AI_GIAN_CACH_GUI\", 20),\n"
    "                       max(_LAN_GUI_CUOI[0], _HEN_GUI_CHUNG[0]) + _so_env(\"AI_GIAN_CACH_CHUNG\", 3))\n"
    "        _HEN_GUI_PAGE[_p] = _luc_gui\n"
    "        _HEN_GUI_CHUNG[0] = max(_HEN_GUI_CHUNG[0], _luc_gui)\n"
    "    if _luc_gui > time.time():\n"
    "        time.sleep(_luc_gui - time.time())   # giãn nhịp giữa hai lần gửi — luật 11/09\n"
    "    ok, err = _gui_tin_ngay(page_id, conv_id, token, text)\n"
    "    if not ok:\n"
    "        with _KHOA_GUI:                      # gửi hỏng không giữ chỗ — lần thử lại #2022 khỏi đợi 20s\n"
    "            if _HEN_GUI_PAGE.get(_p) == _luc_gui:\n"
    "                _HEN_GUI_PAGE[_p] = _moc_page\n"
    "    return ok, err\n"
    "\n"
    "\n"
    "def _gui_tin_ngay(page_id, conv_id, token, text):\n"
    "    \"\"\"Phần gửi thật của gui_tin (sau khi đã giữ chỗ + đợi nhịp).\"\"\"\n"
    "    if _la_user(token) or (str(page_id) in _FB_CHAN and gui_qua_user_bat()):\n"
    "        return gui_tin_qua_user(page_id, conv_id, text)\n",
))

# ── 3. sổ đã-xem dưới khoá ───────────────────────────────────────────────────────────
VA.append((
    '    so[str(conv_id)] = [cuoi["luc"], int(time.time())]\n'
    "    if len(so) > 3000:                                   # giữ sổ gọn: bỏ mốc cũ nhất\n"
    "        for k in sorted(so, key=lambda k: str(_moc_da_xem(so[k])[0]))[:len(so) - 2000]:\n"
    "            so.pop(k, None)\n"
    "    try:\n"
    '        json.dump(so, open(_f_da_xem(mkey), "w", encoding="utf-8"), ensure_ascii=False)\n'
    "    except Exception:                                    # noqa: BLE001\n"
    "        pass\n",
    "    with _KHOA_GUI:                                      # 18/09: lượt xử song song cùng sửa sổ này\n"
    '        so[str(conv_id)] = [cuoi["luc"], int(time.time())]\n'
    "        if len(so) > 3000:                               # giữ sổ gọn: bỏ mốc cũ nhất\n"
    "            for k in sorted(so, key=lambda k: str(_moc_da_xem(so[k])[0]))[:len(so) - 2000]:\n"
    "                so.pop(k, None)\n"
    "        try:\n"
    '            with open(_f_da_xem(mkey), "w", encoding="utf-8") as _fh:\n'
    "                json.dump(so, _fh, ensure_ascii=False)\n"
    "        except Exception:                                # noqa: BLE001\n"
    "            pass\n",
))

# ── 2. sổ dax / lên đơn sớm ghi kiểu gộp ─────────────────────────────────────────────
VA.append((
    "def cmd_chay(mkey, page_loc=None, gio=24, so=30, that=False, cho=CHO_BOTCAKE,\n",
    "def _ghi_moc(f, moi):\n"
    "    \"\"\"Thêm các mốc `moi` vào sổ json `f`: ĐỌC LẠI file rồi mới ghi (18/09 — nhiều lượt xử chạy song\n"
    "    song; ghi nguyên dict của lượt mình là xoá mất mốc lượt khác vừa ghi → khách nhận 2 tin).\"\"\"\n"
    "    if not moi:\n"
    "        return\n"
    "    with _KHOA_GUI:\n"
    "        try:\n"
    "            cu = json.load(open(f, encoding=\"utf-8\"))\n"
    "        except Exception:                                # noqa: BLE001\n"
    "            cu = {}\n"
    "        cu.update(moi)\n"
    "        tam = f + \".tam\"\n"
    "        with open(tam, \"w\", encoding=\"utf-8\") as fh:\n"
    "            json.dump(cu, fh, ensure_ascii=False)\n"
    "        os.replace(tam, f)\n"
    "\n"
    "\n"
    "def cmd_chay(mkey, page_loc=None, gio=24, so=30, that=False, cho=CHO_BOTCAKE,\n",
))
VA.append((
    '    som_dax = json.load(open(_f_som(mkey), encoding="utf-8")) if os.path.exists(_f_som(mkey)) else {}\n',
    '    som_dax = json.load(open(_f_som(mkey), encoding="utf-8")) if os.path.exists(_f_som(mkey)) else {}\n'
    "    _som_goc = dict(som_dax)            # 18/09: cuối lượt chỉ ghi mốc MỚI của lượt này (_ghi_moc)\n",
))
VA.append((
    '                        json.dump(dax, open(_f_dax(mkey), "w", encoding="utf-8"), ensure_ascii=False)\n',
    '                        _ghi_moc(_f_dax(mkey), {str(c["id"]): cuoi["luc"]})   # gộp, không đè (18/09)\n',
))
VA.append((
    "    if that:\n"
    '        json.dump(dax, open(_f_dax(mkey), "w", encoding="utf-8"), ensure_ascii=False)\n'
    '        json.dump(som_dax, open(_f_som(mkey), "w", encoding="utf-8"), ensure_ascii=False)\n',
    "    if that:\n"
    "        # dax đã ghi từng mốc ngay lúc gửi; sổ lên-đơn-sớm ghi gộp phần lượt này mới thêm (18/09).\n"
    "        _ghi_moc(_f_som(mkey), {k: v for k, v in som_dax.items() if _som_goc.get(k) != v})\n",
))

# ── 4. khách nhắn thêm: chỉ lấy hội thoại của lượt mình ──────────────────────────────
VA.append((
    "    for cid in list(_KHACH_NHAN_THEM):\n"
    '        ket_qua[str(cid)] = "cho"                  # hoãn vì khách nhắn thêm → lượt sau đọc lại\n'
    "        _KHACH_NHAN_THEM.discard(cid)\n",
    "    _cua_luot_ = {str(x) for x in (chi_hoi_thoai or ())}\n"
    "    for cid in list(_KHACH_NHAN_THEM):\n"
    "        if chi_hoi_thoai is not None and str(cid) not in _cua_luot_:\n"
    "            continue                              # của lượt xử khác đang chạy song song (18/09)\n"
    '        ket_qua[str(cid)] = "cho"                  # hoãn vì khách nhắn thêm → lượt sau đọc lại\n'
    "        _KHACH_NHAN_THEM.discard(cid)\n",
))

# ── 5. trong lượt: soạn xong trước làm trước ─────────────────────────────────────────
VA.append((
    "    try:\n"
    "        for _v in cac_viec:\n"
    '            if "tuong_lai" in _v:\n'
    '                _v["tuong_lai"].result()\n',
    "    def _theo_luc_xong(ds):\n"
    "        # 18/09: hành động theo thứ tự SOẠN XONG — khách soạn nhanh không phải đợi câu soạn chậm đứng trước.\n"
    "        from concurrent.futures import as_completed as _xong_truoc\n"
    '        _bd = {v["tuong_lai"]: v for v in ds if "tuong_lai" in v}\n'
    "        for _fu in _xong_truoc(_bd):\n"
    "            yield _bd[_fu]\n"
    "        for v in ds:\n"
    '            if "tuong_lai" not in v:\n'
    "                yield v\n"
    "    try:\n"
    "        for _v in _theo_luc_xong(cac_viec):\n"
    '            if "tuong_lai" in _v:\n'
    '                _v["tuong_lai"].result()\n',
))

# ── 6. vòng dò không đứng đợi ────────────────────────────────────────────────────────
VA.append((
    "    thong_tin = {}     # cid -> bản ghi hội thoại mới nhất (cho chốt chặn 3 phút)\n",
    "    thong_tin = {}     # cid -> bản ghi hội thoại mới nhất (cho chốt chặn 3 phút)\n"
    "    # 18/09 — XỬ TỪNG KHÁCH RIÊNG: vòng dò giao việc cho lượt xử chạy nền rồi dò tiếp, không đứng đợi.\n"
    "    dang_chay = {}     # future -> (tập hội thoại của lượt đó, lúc giao)\n"
    "    dang_xu = set()    # hội thoại đang nằm trong một lượt chạy — không giao lần hai\n"
    "    _toi_da_luot = max(1, int(_so_env(\"AI_LUOT_SONG_SONG\", 3)))\n"
    "    bom_xu = ThreadPoolExecutor(max_workers=_toi_da_luot)\n",
))
VA.append((
    '        gan = {k for k in nong if loai.get(k) != "nguoi" or k in cho_xu}\n',
    "        # Gom kết quả các lượt xử đã xong (chạy nền) TRƯỚC khi xếp hàng lượt mới.\n"
    "        for _fu in [x for x in dang_chay if x.done()]:\n"
    "            _ids, _luc_giao = dang_chay.pop(_fu)\n"
    "            dang_xu -= _ids\n"
    "            try:\n"
    "                kq = _fu.result() or {}\n"
    "            except SystemExit as e:\n"
    '                print(f"  ⚠️  lượt xử dừng: {e}", flush=True); kq = {}\n'
    "            except Exception as e:                    # noqa: BLE001\n"
    '                print(f"  🚨 lượt xử lỗi: {e!r}", flush=True); kq = {}\n'
    "            for cid, kc in kq.items():\n"
    "                # Khách nhắn thêm SAU lúc giao lượt (vòng dò đã đánh nóng lại) → giữ, giao lượt mới.\n"
    "                if kc != \"cho\" and nong.get(cid, 0) <= _luc_giao:\n"
    "                    nong.pop(cid, None)\n"
    '        gan = {k for k in nong if loai.get(k) != "nguoi" or k in cho_xu}\n',
))
VA.append((
    "        lam = gan | set(xa[:tran_xa])\n"
    "        if lam:\n",
    "        lam = (gan | set(xa[:tran_xa])) - dang_xu\n"
    "        if lam and len(dang_chay) >= _toi_da_luot:\n"
    "            lam = set()          # đủ lượt đang chạy — giữ nguyên hàng chờ (cho_xu), vòng dò sau giao\n"
    "        if lam:\n",
))
VA.append((
    "            cho_xu -= lam\n"
    "            try:\n"
    "                kq = cmd_chay(mkey, gio=gio, so=so, that=that, cho=cho, dong_bo=False,\n"
    "                              chi_hoi_thoai=set(lam), pages_san=pages,\n"
    "                              cho_theo_page=cho_theo_page) or {}\n"
    "            except SystemExit as e:\n"
    '                print(f"  ⚠️  lượt xử dừng: {e}", flush=True); kq = {}\n'
    "            except Exception as e:                    # noqa: BLE001\n"
    '                print(f"  🚨 lượt xử lỗi: {e!r}", flush=True); kq = {}\n'
    "            for cid, kc in kq.items():\n"
    '                if kc != "cho":\n'
    "                    nong.pop(cid, None)\n",
    "            cho_xu -= lam\n"
    "            dang_xu |= lam\n"
    "            dang_chay[bom_xu.submit(cmd_chay, mkey, gio=gio, so=so, that=that, cho=cho, dong_bo=False,\n"
    "                                    chi_hoi_thoai=set(lam), pages_san=pages,\n"
    "                                    cho_theo_page=cho_theo_page)] = (set(lam), time.time())\n",
))

for cu, moi in VA:
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần (cần đúng 1) — file đã bị sửa vùng này, KHÔNG ghi:\n{cu[:160]}"
for cu, moi in VA:
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"đã vá {len(VA)} chỗ")

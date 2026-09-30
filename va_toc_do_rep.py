"""Vá 17/09 tối — TỐC ĐỘ TRẢ LỜI (chủ shop: "bất kì tin nào khách nhắn tới, bạn rep trong bao lâu").

Chủ shop chọn: giãn 20s THEO PAGE + bỏ trần 10 tin/giờ; sale gửi trước trong lúc AI soạn thì AI vẫn bỏ câu;
tin mẫu quảng cáo vẫn để sale.
  1. gui_tin: giãn AI_GIAN_CACH_GUI giây theo từng page (chung cả nước chỉ AI_GIAN_CACH_CHUNG=3s);
     chữ đi liền sau ảnh của cùng câu trả lời không đợi.
  2. page_qua_tran_gui: AI_GUI_MOI_PAGE_GIO=0 là bỏ trần.
  3. _phan_hoi: đánh dấu chưa đọc SAU KHI GỬI chạy luồng nền, sổ việc do luồng nền ghi.
  4. ghi_so_viec: giữ "luc" nếu chỗ gọi đã đặt (lúc tin đi).
  5. _hoi_thoai_gop: page lệnh gộp từ chối (mã 121/105) → nhớ 30 phút, bỏ khỏi lô, hỏi lại lô.
  6. cmd_theo_doi: page gộp hỏng hỏi riêng; CHỐT CHẶN 3 PHÚT canh_bao_cho_lau.
Chạy: python3 va_toc_do_rep.py ai_sale.py   (mỗi chỗ phải khớp đúng 1 lần, không thì không ghi gì)
"""
import sys

f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "def canh_bao_cho_lau" in src:
    sys.exit("đã vá rồi — không làm gì")

VA = []

# ── 0. chú thích đầu file ────────────────────────────────────────────────────────────
VA.append((
    "  AI_GIAN_CACH_GUI=20     # giây tối thiểu giữa hai lần gửi (mọi page)\n"
    "  AI_GUI_MOI_PAGE_GIO=10  # tối đa tin AI gửi trên một page mỗi giờ; quá thì nhường sale\n",
    "  AI_GIAN_CACH_GUI=20     # giây tối thiểu giữa hai lần gửi CÙNG PAGE (từ 17/09; trước đó mọi page)\n"
    "  AI_GIAN_CACH_CHUNG=3    # giây tối thiểu giữa hai lần gửi bất kỳ (chung cả nước)\n"
    "  AI_GUI_MOI_PAGE_GIO=10  # tối đa tin AI gửi trên một page mỗi giờ; quá thì nhường sale; 0 = bỏ trần\n"
    "  AI_CANH_BAO_TRE=180     # khách chờ quá chừng này giây mà AI chưa rep → ghi chú + chưa đọc cho sale\n",
))
VA.append((
    "#   AI_GIAN_CACH_GUI    giây tối thiểu giữa hai lần gửi thành công, mọi page (mặc định 20)\n",
    "#   AI_GIAN_CACH_GUI    giây tối thiểu giữa hai lần gửi thành công CÙNG PAGE (mặc định 20)\n"
    "#   AI_GIAN_CACH_CHUNG  giây tối thiểu giữa hai lần gửi bất kỳ, mọi page (mặc định 3)\n",
))

# ── 2. bỏ trần giờ ───────────────────────────────────────────────────────────────────
VA.append((
    "    return len(ds) >= tran\n",
    "    return tran > 0 and len(ds) >= tran     # 0 = bỏ trần (chủ shop 17/09 tối)\n",
))

# ── 1. giãn theo page ────────────────────────────────────────────────────────────────
VA.append((
    "def gui_tin(page_id, conv_id, token, text, dry=True):\n",
    "def gui_tin(page_id, conv_id, token, text, dry=True, sau_anh=False):\n",
))
VA.append((
    '    cho = _so_env("AI_GIAN_CACH_GUI", 20) - (time.time() - _LAN_GUI_CUOI[0])\n'
    "    if cho > 0:\n"
    "        time.sleep(cho)                      # giãn nhịp giữa hai lần gửi — luật 11/09\n",
    "    # 17/09 tối — chủ shop chọn \"20s theo page, bỏ trần\": giãn AI_GIAN_CACH_GUI giây giữa hai tin\n"
    "    # CÙNG PAGE, không còn tính chung cả nước. Bản cũ bắt mọi page xếp MỘT hàng 20s/tin, cả lượt\n"
    "    # xử đứng đợi, khách nhắn sau phải chờ lượt trước gửi xong (Saudi lúc đông: 90% khách chờ tới\n"
    "    # 5p41s). Đo 14→17/09: chỉ 3% tin gửi cách tin trước CÙNG page dưới 60s, nên giãn theo page\n"
    "    # gần như không bắt ai đợi. Chung cả nước chỉ giữ AI_GIAN_CACH_CHUNG giây cho khỏi bắn dồn.\n"
    "    # `sau_anh`: chữ đi ngay sau ảnh của CÙNG câu trả lời — ảnh + lời là một lượt, không đợi 20s.\n"
    "    _moc_page = (_GUI_THEO_PAGE.get(str(page_id)) or [0.0])[-1]\n"
    '    cho = max(0.0 if sau_anh else _so_env("AI_GIAN_CACH_GUI", 20) - (time.time() - _moc_page),\n'
    '              _so_env("AI_GIAN_CACH_CHUNG", 3) - (time.time() - _LAN_GUI_CUOI[0]))\n'
    "    if cho > 0:\n"
    "        time.sleep(cho)                      # giãn nhịp giữa hai lần gửi — luật 11/09\n",
))
VA.append((
    "    anh_hong = None        # vì sao ảnh không tới khách — dùng ở khúc dưới để không gửi lời hứa suông\n",
    "    anh_hong = None        # vì sao ảnh không tới khách — dùng ở khúc dưới để không gửi lời hứa suông\n"
    "    _da_gui_anh = False    # ảnh của lượt này đã tới khách → chữ đi liền sau, không đợi 20s (17/09)\n",
))
VA.append((
    "        ok, e = gui_anh(pid, conv_id, token, anh, dry=not that)\n",
    "        ok, e = gui_anh(pid, conv_id, token, anh, dry=not that)\n"
    "        _da_gui_anh = _da_gui_anh or ok\n",
))
VA.append((
    "        ok, e = gui_anh_mau(mkey, pid, conv_id, token, anh_urls, dry=not that)\n",
    "        ok, e = gui_anh_mau(mkey, pid, conv_id, token, anh_urls, dry=not that)\n"
    "        _da_gui_anh = _da_gui_anh or ok\n",
))
VA.append((
    "            ok, e = gui_tin(pid, conv_id, token, tin, dry=not that)\n",
    "            ok, e = gui_tin(pid, conv_id, token, tin, dry=not that, sau_anh=_da_gui_anh)\n",
))

# ── 3. đánh dấu chưa đọc sau gửi chạy nền ────────────────────────────────────────────
VA.append((
    "    cd_ok, e = danh_dau_chua_doc(pid, conv_id, token, dry=not that)\n"
    "    if not cd_ok:\n"
    '        print(f"{nhan} 🚨 ĐÁNH DẤU CHƯA ĐỌC HỎNG ({e}) — tin này sẽ bị trôi, phải soát tay!")\n',
    "    # 17/09 tối: ĐÁNH DẤU CHƯA ĐỌC SAU KHI GỬI CHẠY LUỒNG NỀN. Hàm này phải đợi cái echo của tin\n"
    "    # vừa gửi (4s, tối đa 3 lượt) rồi đọc lại cờ — bản cũ bắt cả lượt xử đứng chờ 4-12s cho MỖI\n"
    "    # tin, khách nhắn sau chờ theo. Vẫn đủ các bước cũ (đánh → đợi → đọc lại → đánh lại), chỉ không\n"
    "    # chặn lượt nữa; dòng sổ việc do luồng nền ghi SAU khi biết chắc kết quả.\n"
    "    _ban_sv, _xong_ban = {}, _threading.Event()\n"
    "\n"
    "    def _cd_nen():\n"
    "        _ok, _loi = danh_dau_chua_doc(pid, conv_id, token, dry=not that)\n"
    "        if not _ok:\n"
    '            print(f"{nhan} 🚨 ĐÁNH DẤU CHƯA ĐỌC HỎNG ({_loi}) — tin này sẽ bị trôi, phải soát tay!",\n'
    "                  flush=True)\n"
    "        _xong_ban.wait(300)\n"
    "        if _ban_sv:\n"
    '            _ban_sv["chua_doc"] = 1 if _ok else 0        # để soi lại sổ, khỏi phải hỏi API từng ca\n'
    '            _ban_sv["chua_doc_loi"] = "" if _ok else str(_loi or "")[:200]\n'
    "            ghi_so_viec(mkey, _ban_sv)\n"
    '    _threading.Thread(target=_cd_nen, name=f"chua_doc_{conv_id}", daemon=False).start()\n',
))
VA.append((
    "    ghi_so_viec(mkey, {\n"
    '        "pid": str(pid), "page": ten_page, "conv": str(conv_id), "khach": ten_khach,\n',
    "    _ban_sv.update({\n"
    '        "pid": str(pid), "page": ten_page, "conv": str(conv_id), "khach": ten_khach,\n',
))
VA.append((
    '        "chua_doc": 1 if cd_ok else 0,          # để soi lại sổ, khỏi phải hỏi API từng ca\n'
    '        "chua_doc_loi": "" if cd_ok else str(e or "")[:200],\n'
    "    })\n"
    "    return gui_hong is None\n",
    '        "luc": int(time.time()),                # lúc tin đi — dòng sổ do luồng nền ghi sau vài giây\n'
    "    })\n"
    "    _xong_ban.set()\n"
    "    return gui_hong is None\n",
))

# ── 4. sổ việc giữ mốc lúc tin đi ────────────────────────────────────────────────────
VA.append((
    '        ban["luc"] = int(time.time())\n',
    '        ban.setdefault("luc", int(time.time()))   # _phan_hoi đặt sẵn lúc tin đi (ghi sổ ở luồng nền)\n',
))

# ── 5. lệnh gộp bỏ page hỏng ─────────────────────────────────────────────────────────
VA.append((
    "LO_GOP = 120          # page mỗi lô; 344 page trong 1 URL thì Pancake trả 414 Request-URI Too Long\n",
    "LO_GOP = 120          # page mỗi lô; 344 page trong 1 URL thì Pancake trả 414 Request-URI Too Long\n"
    "_GOP_HONG = {}        # page mà lệnh gộp từ chối (mã 121 hết gói / 105 không quyền) -> lúc phát hiện\n"
    "\n"
    "\n"
    "def gop_hong(pid):\n"
    '    """Page này lệnh gộp đã từ chối trong 30 phút qua → phải hỏi riêng bằng đường cũ."""\n'
    "    t = _GOP_HONG.get(str(pid))\n"
    "    return bool(t) and time.time() - t < 1800\n",
))
VA.append((
    "    ra = {}\n"
    "    ids = [str(p) for p in page_ids]\n"
    "    for i in range(0, len(ids), LO_GOP):\n"
    "        lo = ids[i:i + LO_GOP]\n"
    '        p = {("pages[%s]" % x): 0 for x in lo}\n'
    '        p.update({"unread_first": "true", "mode": "NONE", "tags": \'"ALL"\',\n'
    '                  "except_tags": "[]", "access_token": _tok_user(),\n'
    '                  "cursor_mode": "true", "from_platform": "web"})\n'
    '        res, err = _get(f"{WEB_API}/conversations", p)\n'
    '        if err or not isinstance((res or {}).get("conversations"), list):\n'
    '            return {}, err or "API gộp không trả hội thoại"\n',
    "    ra = {}\n"
    "    # Page lệnh gộp đã từ chối trong 30 phút qua (gop_hong) không đưa vào lô — chỗ gọi hỏi riêng.\n"
    "    ids = [str(p) for p in page_ids if not gop_hong(p)]\n"
    "\n"
    "    def _tham_so(lo):\n"
    '        p = {("pages[%s]" % x): 0 for x in lo}\n'
    '        p.update({"unread_first": "true", "mode": "NONE", "tags": \'"ALL"\',\n'
    '                  "except_tags": "[]", "access_token": _tok_user(),\n'
    '                  "cursor_mode": "true", "from_platform": "web"})\n'
    "        return p\n"
    "    for i in range(0, len(ids), LO_GOP):\n"
    "        lo = ids[i:i + LO_GOP]\n"
    '        res, err = _get(f"{WEB_API}/conversations", _tham_so(lo))\n'
    '        if not err and not isinstance((res or {}).get("conversations"), list):\n'
    "            # 17/09 tối: CHỈ MỘT page mà tài khoản AI không dùng được là cả lô hỏng — đo UAE: 50/76\n"
    '            # page báo "Không tìm thấy gói cước" (mã 121) hoặc "Không có quyền hạn" (105) → mỗi lượt\n'
    "            # dò quay về hỏi từng page, 8s thay vì 2s. Pancake kể đúng page hỏng trong `errors`:\n"
    "            # nhớ 30 phút, bỏ ra, hỏi lại lô MỘT lần.\n"
    '            _hong = {str(x.get("page_id")) for x in ((res or {}).get("errors") or [])\n'
    '                     if isinstance(x, dict) and x.get("page_id")}\n'
    "            if _hong:\n"
    "                for x in _hong:\n"
    "                    _GOP_HONG[x] = time.time()\n"
    "                lo = [x for x in lo if x not in _hong]\n"
    "                if not lo:\n"
    "                    continue\n"
    '                res, err = _get(f"{WEB_API}/conversations", _tham_so(lo))\n'
    '        if err or not isinstance((res or {}).get("conversations"), list):\n'
    '            return {}, err or "API gộp không trả hội thoại"\n',
))

# ── 6a. vòng dò: page gộp hỏng hỏi riêng ─────────────────────────────────────────────
VA.append((
    "            else:\n"
    "                ds = [(pid, _g.get(str(pid), []), None) for pid, _ in pages]\n",
    "            else:\n"
    "                # Page lệnh gộp từ chối (gop_hong) → hỏi riêng bằng đường cũ, song song (17/09 tối).\n"
    "                ds = [(pid, _g.get(str(pid), []), None) for pid, _ in pages if not gop_hong(pid)]\n"
    "                _le = [cap for cap in pages if gop_hong(cap[0])]\n"
    "                if _le:\n"
    '                    with ThreadPoolExecutor(max_workers=int(_so_env("AI_LUONG_QUET", 20))) as bom:\n'
    "                        ds += list(bom.map(lambda cap: _liet_ke(cap, 24 if lan == 0 else gio), _le))\n",
))
VA.append((
    "    botcake_page = {}\n    nhip = giay\n",
    "    botcake_page = {}\n"
    "    thong_tin = {}     # cid -> bản ghi hội thoại mới nhất (cho chốt chặn 3 phút)\n"
    "    nhip = giay\n",
))
VA.append((
    "                loai[cid] = ai_g\n",
    "                loai[cid] = ai_g\n"
    "                thong_tin[cid] = c\n",
))
VA.append((
    "            for cid, kc in kq.items():\n"
    '                if kc != "cho":\n'
    "                    nong.pop(cid, None)\n"
    "        if bi_chan:\n",
    "            for cid, kc in kq.items():\n"
    '                if kc != "cho":\n'
    "                    nong.pop(cid, None)\n"
    "        # ── CHỐT CHẶN 3 PHÚT (17/09 tối) — khách chờ quá lâu mà AI chưa rep → báo sale ngay ──\n"
    "        try:\n"
    "            canh_bao_cho_lau(mkey, nong, loai, thong_tin, pages, that)\n"
    "        except Exception as e:                        # noqa: BLE001 — chốt chặn hỏng không giết vòng dò\n"
    '            print(f"  ⚠ chốt chặn 3 phút lỗi: {e!r}", flush=True)\n'
    "        for _k in [k for k in thong_tin if k not in nong]:\n"
    "            thong_tin.pop(_k, None)\n"
    "        if bi_chan:\n",
))

# ── 6b. hàm chốt chặn ────────────────────────────────────────────────────────────────
VA.append((
    "def cmd_theo_doi(mkey, giay=15, cho=CHO_BOTCAKE, so=12, gio=1, that=False):\n",
    '''# ── CHỐT CHẶN 3 PHÚT — chủ shop 17/09 tối: "bất kì tin nào khách nhắn tới, bạn rep trong bao lâu" ──
_CANH_BAO_TRE = {}      # mkey -> {cid: khoá tin khách đã cảnh báo}
_KB_DEM = {}            # mkey -> (mtime, kich_ban.json) — khỏi đọc lại file 800KB mỗi 8 giây


def _co_kich_ban(mkey, pid):
    f = os.path.join(SCRIPT_DIR, "state", mkey, "kich_ban.json")
    try:
        mt = os.path.getmtime(f)
        if (_KB_DEM.get(mkey) or (None,))[0] != mt:
            _KB_DEM[mkey] = (mt, json.load(open(f, encoding="utf-8")))
        return bool((_KB_DEM[mkey][1].get(str(pid)) or {}).get("mau"))
    except Exception:                                    # noqa: BLE001
        return False


def canh_bao_cho_lau(mkey, nong, loai, thong_tin, pages, that, cho_giay=None):
    """Khách chờ quá AI_CANH_BAO_TRE giây (mặc định 180) mà AI chưa trả lời được → ghi chú +
    đánh dấu chưa đọc NGAY cho sale, mỗi tin khách MỘT lần.

    Xét: hội thoại còn nằm trong `nong` của vòng dò (lượt xử trả "cho" — Kimi hết tiền, đọc hỏng…)
    mà người gửi cuối KHÔNG phải sale thật hay chính AI. KHÔNG đụng: page chưa có kịch bản và hội
    thoại có thẻ "Đã gửi" (chủ shop dặn để nguyên cho sale; đọc thẻ hỏng thì cũng bỏ qua), bình luận
    (danh sách đã lọc INBOX). Khoá chống lặp = message_count: ghi chú làm updated_at đổi nên hội
    thoại "nóng" lại, nhưng số tin không đổi → không cảnh báo lần hai.
    """
    cho_giay = _so_env("AI_CANH_BAO_TRE", 180) if cho_giay is None else cho_giay
    if not that or not nong or cho_giay <= 0:
        return 0
    so = _CANH_BAO_TRE.get(mkey)
    f = os.path.join(SCRIPT_DIR, "state", mkey, "canh_bao_tre.json")
    if so is None:
        try:
            so = json.load(open(f, encoding="utf-8"))
        except Exception:                                # noqa: BLE001
            so = {}
        _CANH_BAO_TRE[mkey] = so
    try:
        import auto_len_don as _D
    except Exception:                                    # noqa: BLE001
        _D = None
    st_theo = {str(p): s for p, s in pages}
    viec = []
    for cid in list(nong):
        c = thong_tin.get(cid)
        if not c or loai.get(cid) in ("nguoi", "ai"):
            continue
        tre = _giay_tu(c.get("updated_at"))
        if tre < cho_giay or tre > 6 * 3600:
            continue
        khoa = str(c.get("message_count") if c.get("message_count") is not None else c.get("updated_at"))
        if so.get(cid) == khoa:
            continue
        pid = str(c.get("page_id") or str(cid).split("_")[0])
        st = st_theo.get(pid)
        if not st or not _co_kich_ban(mkey, pid) or _D is None:
            continue
        try:
            if _D.the_noi_da_xong(c):
                continue
        except Exception:                                # noqa: BLE001 — đọc thẻ hỏng thì BỎ QUA, không đụng liều
            continue
        so[cid] = khoa
        viec.append((cid, pid, st, c, tre))
    if not viec:
        return 0
    ly = "Kimi hết tiền" if het_tien_that() else "AI chưa xử lý kịp"

    def _lam(v):
        cid, pid, st, c, tre = v
        kh = ((c.get("customers") or [{}])[0] or {})
        cus = kh.get("id") or _CUST.get((pid, cid))
        ok_cd, _ = danh_dau_chua_doc(pid, cid, st["token"], dry=False, lan=2, cho=1)   # 1 lượt từng trượt 1/31 ca
        gc = f"[AI Sale] ⏰ Khách chờ {tre / 60:.0f} phút mà AI chưa trả lời được ({ly}) — sale rep giúp."
        ok_gc, e = ghi_chu(pid, cus, st["token"], gc, dry=False) if cus else (False, "thiếu mã khách")
        ten = kh.get("name") or (c.get("from") or {}).get("name") or "?"
        return (f"  ⏰ [{ten[:20]}] khách chờ {tre / 60:.0f} phút, AI chưa trả lời ({ly}) → "
                f"ghi chú {'✔' if ok_gc else '✖ ' + str(e)[:60]} · chưa đọc {'✔' if ok_cd else '✖'}")
    from concurrent.futures import ThreadPoolExecutor as _TPE_CB
    with _TPE_CB(max_workers=min(5, len(viec))) as bom:
        for dong in bom.map(_lam, viec):
            print(dong, flush=True)
    if len(so) > 3000:
        for k in list(so)[:len(so) - 2000]:
            so.pop(k, None)
    try:
        json.dump(so, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:                                    # noqa: BLE001
        pass
    return len(viec)


def cmd_theo_doi(mkey, giay=15, cho=CHO_BOTCAKE, so=12, gio=1, that=False):
''',
))

for cu, moi in VA:
    n = src.count(cu)
    assert n == 1, f"khớp {n} lần (cần đúng 1) — file đã bị sửa vùng này, KHÔNG ghi:\n{cu[:120]}"
for cu, moi in VA:
    src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print(f"đã vá {len(VA)} chỗ")

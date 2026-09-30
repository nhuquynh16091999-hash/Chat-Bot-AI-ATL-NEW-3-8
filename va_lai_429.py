import sys
F = sys.argv[1]
s = open(F, encoding="utf-8").read()
VA = []

VA.append(("1 · _get thử lại khi 429", '''def _get(url, params):
    u = url + "?" + urllib.parse.urlencode(params, doseq=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(u), timeout=30) as r:
            return json.loads(r.read().decode()), None
    except Exception as e:
        return None, str(e)
''', '''def _get(url, params, thu_lai=2):
    """GET, THỬ LẠI khi Pancake chặn nhịp (429) — chỉ lệnh ĐỌC mới được thử lại.

    Đo 2026-09-11, ca Magdolene Alsoufi (Flat Jewelry KSA in Dubai): đọc tin nhắn 8 luồng
    song song thì 6/12 lần trả "HTTP Error 429: Too Many Requests". Chỗ gọi trong cmd_chay
    chỉ đếm dem["loi"] rồi bỏ hội thoại, mà cuối hàm lại đánh dấu "xong" → khách nhắn
    "I want sets" lúc 11:19 không ai trả lời, sale phải tự vào rep lúc 11:30.

    Nghỉ 1s rồi 2s là đủ: Pancake nhả nhịp trong vòng 1-2 giây. KHÔNG đưa cách này sang
    `_post`: gửi tin mà thử lại là khách có nguy cơ nhận hai lần cùng một câu.
    """
    u = url + "?" + urllib.parse.urlencode(params, doseq=True)
    for lan in range(thu_lai + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(u), timeout=30) as r:
                return json.loads(r.read().decode()), None
        except Exception as e:                           # noqa: BLE001
            loi = str(e)
            if lan < thu_lai and ("429" in loi or "Too Many Requests" in loi):
                time.sleep(1 + lan)
                continue
            return None, loi
'''))

VA.append(("2 · đọc tin hỏng thì giữ nóng", '''            msgs, cus_id, e = tin_san.get(c["id"]) or tin_cua_hoi_thoai(pid, c["id"], st["token"])
            if e or not msgs:
                dem["loi"] += 1
                continue
''', '''            msgs, cus_id, e = tin_san.get(c["id"]) or tin_cua_hoi_thoai(pid, c["id"], st["token"])
            if e or not msgs:
                # ĐỌC HỎNG KHÔNG PHẢI LÀ "XONG". Bản cũ chỉ đếm rồi continue, mà cuối hàm
                # ket_qua.setdefault(cid, "xong") khiến vòng dò nhanh bỏ hội thoại khỏi `nong`;
                # da_thay đã giữ updated_at nên nó KHÔNG BAO GIỜ quay lại. Ca Magdolene Alsoufi
                # 11/09: một nhịp 429 → khách im 10 phút tới khi sale tự rep.
                # Giữ "cho" để lượt sau (15s) đọc lại; quá 5 phút thì cmd_theo_doi tự buông.
                dem["loi"] += 1
                ket_qua[str(c["id"])] = "cho"
                ten_k = ((c.get("customers") or [{}])[0].get("name")
                         or (c.get("from") or {}).get("name") or "?")
                print(f"     [{ten_k[:20]:22s}] ✖ không đọc được tin "
                      f"({e or 'API trả rỗng'}) — giữ lại, lượt sau đọc lại")
                continue
'''))

VA.append(("3 · số luồng đọc chỉnh được", '''    with ThreadPoolExecutor(max_workers=8) as bom:
        da_doc = dict(bom.map(_doc_page, pages))
''', '''    # 8 luồng là chỗ đẻ ra 429 (đo 11/09: 6/12 lần đọc tin bị chặn nhịp). Hạ còn 5 và có
    # _get thử lại ở trên; muốn đổi thì đặt AI_LUONG_DOC trong .env, khỏi sửa code.
    with ThreadPoolExecutor(max_workers=max(1, int(_so_env("AI_LUONG_DOC", 5)))) as bom:
        da_doc = dict(bom.map(_doc_page, pages))
'''))

VA.append(("4 · cửa gác thôi nuốt lỗi", '''        if chi_hoi_thoai is not None and not (da_doc.get(pid) or ([],))[0]:
            continue                       # vòng dò nhanh: page không có gì mới thì im, khỏi in 69 dòng
''', '''        # Cửa này NUỐT LUÔN LỖI, không chỉ nuốt page rỗng: `_doc_page` gặp 429 ở lệnh lấy
        # danh sách thì trả về convs=[] KÈM err, mà ở đây chỉ nhìn convs → `continue` ngay,
        # nên nhánh `if err:` bên dưới (in lý do + đếm, và TỰ CẤP LẠI TOKEN CHẾT) KHÔNG BAO
        # GIỜ chạy trong chế độ dò nhanh. Cả page bị bỏ mà log không một chữ, số "lỗi N"
        # cuối lượt cũng không nhích. Ca Magdolene Alsoufi 11/09: khách nhắn "Show me sets"
        # 11:34, page Flat Jewelry biến mất khỏi mọi lượt tới 11:44 — 11 phút không dấu vết.
        convs_pg, err_pg = (da_doc.get(pid) or ([], None, {}))[:2]
        if chi_hoi_thoai is not None and not convs_pg and not err_pg:
            continue                       # vòng dò nhanh: page không có gì mới thì im, khỏi in 69 dòng
'''))

VA.append(("5 · danh sách hỏng thì giữ nóng cả page", '''            dem["loi"] += 1
            print(f"  ✖ {st.get('name','?')[:44]} — KHÔNG lấy được hội thoại: {err}")
            continue
''', '''            dem["loi"] += 1
            print(f"  ✖ {st.get('name','?')[:44]} — KHÔNG lấy được hội thoại: {err}")
            # Giữ nóng mọi hội thoại của page này, nếu không `ket_qua.setdefault(cid,"xong")`
            # cuối hàm sẽ đóng sổ chúng và vòng dò nhanh không bao giờ quay lại (da_thay đã
            # giữ updated_at). Quá 5 phút thì cmd_theo_doi tự buông.
            for cid_ in (chi_hoi_thoai or ()):
                if str(cid_).startswith(str(pid) + "_"):
                    ket_qua[str(cid_)] = "cho"
            continue
'''))

loi = 0
for ten, cu, moi in VA:
    n = s.count(cu)
    if n != 1:
        print(f"  ❌ {ten}: khớp {n} lần — KHÔNG vá, phải xem lại"); loi += 1; continue
    s = s.replace(cu, moi)
    print(f"  ✅ {ten}")
if loi:
    sys.exit(f"\n{loi} vá KHÔNG áp được — dừng, không ghi file")
open(F, "w", encoding="utf-8").write(s)
print("\n  đã ghi:", F)

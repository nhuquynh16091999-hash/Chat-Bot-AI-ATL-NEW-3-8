"""Vá cmd_chay: SOẠN CÂU SONG SONG, GỬI VẪN TUẦN TỰ (14/09/2026, sau ca EsOr Adz — Saudi).

Chạy: python3 va_song_song.py ai_sale.py [--kiem]
  --kiem : chỉ in phân tích biến, không ghi file.

Cách vá: KHÔNG chép cứng code — lấy nguyên khối "soạn" (B) và khối "hành động" (C) đang có trên
đĩa, dời chỗ giữ nguyên chữ. Mỗi mốc phải khớp đúng 1 lần, không thì thoát không ghi.
"""
import ast
import builtins
import re
import sys
import textwrap

f = sys.argv[1]
chi_kiem = "--kiem" in sys.argv
s = open(f, encoding="utf-8").read()
if "AI_SOAN_SONG_SONG" in s:
    sys.exit("đã vá rồi — không làm gì")


def mot(chu, ten):
    n = s.count(chu)
    assert n == 1, f"mốc {ten!r} khớp {n} lần (phải 1)"
    return s.index(chu)


# ── các mốc ─────────────────────────────────────────────────────────────
M_HAM = "def cmd_chay(mkey, page_loc=None,"
M_LOOP = "    for pid, st in pages:\n        if dung_ns:\n            break\n"
M_B = '            if str(c["id"]) in soan:\n'
M_C = '            da_hom_nay += LAN_GOI_CUOI.get("tien", 0)\n'
M_C_HET = ('            if that and cuoi and xong:\n'
           '                dax[str(c["id"])] = cuoi["luc"]\n'
           '            time.sleep(0.15)\n'
           '        time.sleep(0.15)\n')
M_SAU_LOOP = "\n    try:\n        kho.close()\n"
M_NGAN_SACH = "                if ns_ngay and da_hom_nay >= ns_ngay:\n"
M_NGAN_SACH2 = "                elif ns_tong and da_tong >= ns_tong:\n"
M_DOC = "    t_doc = time.time()\n"
M_KHOI_TAO = "LAN_GOI_CUOI = {}\n"
M_DEM_TOKEN = '    DEM_TOKEN["luot"] += 1\n'
M_DEM_TOKEN_HET = '    DEM_TOKEN["ra"] += u.get("output_tokens") or 0\n'

i_ham = mot(M_HAM, "cmd_chay")
i_loop = mot(M_LOOP, "vòng page")
i_b = mot(M_B, "khối soạn")
i_c = mot(M_C, "khối hành động")
i_c_het = mot(M_C_HET, "hết khối hành động")
assert i_ham < i_loop < i_b < i_c < i_c_het, "thứ tự mốc sai"
i_sau = s.index(M_SAU_LOOP, i_c_het)
assert s[i_c_het + len(M_C_HET):i_sau].strip() == "", "giữa hết vòng page và kho.close có code lạ"

khoi_a = s[i_loop:i_b]
khoi_b = s[i_b:i_c]
khoi_c = s[i_c:i_c_het + len(M_C_HET) - len("        time.sleep(0.15)\n")]


# ── phân tích biến ─────────────────────────────────────────────────────
def gan_va_dung(code, boc_vong=False):
    t = textwrap.dedent(code)
    if boc_vong:
        t = "for _ in (0,):\n" + textwrap.indent(t, "    ")
    cay = ast.parse(t)
    gan, dung = set(), set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Name):
            (gan if isinstance(n.ctx, (ast.Store, ast.Del)) else dung).add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.Lambda)):
            if isinstance(n, ast.FunctionDef):
                gan.add(n.name)
            for a in n.args.args + n.args.kwonlyargs:
                gan.add(a.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            gan.add(n.name)
        elif isinstance(n, ast.comprehension):
            pass
    return gan, dung


def dong(i):
    return s.count("\n", 0, i) + 1


cay_file = ast.parse(s)
ham = next(n for n in ast.walk(cay_file) if isinstance(n, ast.FunctionDef) and n.name == "cmd_chay")
vong = next(n for n in ham.body if isinstance(n, ast.For) and dong(i_loop) <= n.lineno <= dong(i_loop) + 1)
d_b, d_c_het = dong(i_b), dong(i_c_het) + 3


def ten_gan_trong(nut, bo_tu=None, bo_den=None):
    """Tên gán ở ĐÚNG phạm vi cmd_chay — không lặn vào hàm lồng / lambda / comprehension."""
    out = set()

    def di(n):
        ln = getattr(n, "lineno", None)
        if bo_tu and ln and bo_tu <= ln <= bo_den:
            return
        if isinstance(n, ast.FunctionDef):
            out.add(n.name)
            return
        if isinstance(n, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            return
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        for con in ast.iter_child_nodes(n):
            di(con)
    di(nut)
    return out


# tên gán trong vòng page, NGOÀI khối soạn/hành động = bước lọc (A)
ten_a = ten_gan_trong(vong, d_b, d_c_het)
# tên cấp cmd_chay gán NGOÀI vòng page (ổn định suốt hàm) — closure/cùng phạm vi dùng thẳng được
ten_ham = set()
for n in ham.body:
    if n is vong:
        continue
    ten_ham |= ten_gan_trong(n)
ten_ham |= {a.arg for a in ham.args.args + ham.args.kwonlyargs}
chung = ten_a & ten_ham
assert chung <= {"e", "gd", "dung_ns"}, f"tên vừa gán trong vòng vừa gán ngoài vòng: {chung} — phải xem tay"
ten_ham -= ten_a
# dung_ns là cờ của bước lọc; gd bị báo cáo token cuối hàm gán lại SAU bước 3 — đều vô hại

gan_b, dung_b = gan_va_dung(khoi_b)
gan_c, dung_c = gan_va_dung(khoi_c, boc_vong=True)

tu_a = sorted((dung_b | dung_c) & ten_a - ten_ham - {"print"})
# tên C cần mà chỉ B gán (phải trả về từ B)
b_cho_c = sorted((dung_c & gan_b) - gan_c - ten_a - ten_ham)
print("biến truyền từ bước lọc sang soạn/hành động:", tu_a)
print("biến B gán mà C dùng:", b_cho_c)
assert set(b_cho_c) <= {"qd", "err_m"}, f"C cần thêm biến do B tạo: {b_cho_c} — phải xem tay"
# tên C gán lại mà cũng có trong A (sẽ bị C ghi đè — không sao vì C chạy sau cùng)
lo = sorted(gan_b & (ten_ham - {"dem", "_"}))
# B gán lại biến của bước lọc mà C đọc → C sẽ thấy giá trị CŨ (trước khi B đổi)
b_doi_a = sorted(gan_b & ten_a & dung_c)
print("biến bước lọc mà khối soạn gán lại và khối hành động đọc:", b_doi_a)
assert not b_doi_a, f"{b_doi_a} — phải trả về từ khối soạn, xem tay"
assert not lo, f"khối soạn GÁN vào biến cấp cmd_chay {lo} — trong luồng sẽ không về được, phải xem tay"
assert "continue" not in re.sub(r"#.*", "", khoi_b) and "break" not in re.sub(r"#.*", "", khoi_b), \
    "khối soạn có continue/break — phải xem tay"
assert not re.search(r"\bbreak\b", re.sub(r"#.*", "", khoi_c)), "khối hành động có break — phải xem tay"
# khối soạn không được đụng tới Pancake / POS / file
cam = re.findall(r"\b(_phan_hoi|gui_tin|ghi_chu|danh_dau_chua_doc|len_don|len_don_som|HS\.ghi|ghi_so|"
                 r"kho|dax|som_dax|json\.dump|open)\s*\(", khoi_b)
assert not cam, f"khối soạn gọi hàm có ghi: {cam}"
assert not re.search(r"\b(da_hom_nay|da_tong|ket_qua|goi_chua_soan)\b", khoi_b), \
    "khối soạn đụng biến sổ cấp cmd_chay"
if chi_kiem:
    sys.exit(0)

# e / e2 / gc: bước lọc chỉ gán ở nhánh có điều kiện (token chết, treo) → có thể CHƯA gán lúc xếp việc;
# khối soạn/hành động luôn tự gán trước khi đọc (except as e, qd2, e2 = …, gc = …) → không truyền.
TU_GAN = {"e", "e2", "gc"}
assert TU_GAN <= (gan_b | gan_c)
tu_a = [x for x in tu_a if x not in TU_GAN]
BIEN = ", ".join(tu_a)

# ── 1. LAN_GOI_CUOI theo luồng + khoá DEM_TOKEN ──────────────────────────
mot(M_KHOI_TAO, "LAN_GOI_CUOI = {}")
s = s.replace(M_KHOI_TAO, '''class _DictTheoLuong:
    """Dict riêng cho TỪNG LUỒNG — soạn song song (14/09) mà mọi luồng ghi chung một dict thì sổ
    chi phí chép nhầm tiền của hội thoại này sang hội thoại kia. Dùng như dict thường."""

    def __init__(self):
        import threading
        self._l = threading.local()

    def _d(self):
        d = getattr(self._l, "d", None)
        if d is None:
            d = self._l.d = {}
        return d

    def clear(self): self._d().clear()
    def update(self, *a, **k): self._d().update(*a, **k)
    def get(self, *a): return self._d().get(*a)
    def keys(self): return self._d().keys()
    def items(self): return self._d().items()
    def __getitem__(self, k): return self._d()[k]
    def __setitem__(self, k, v): self._d()[k] = v
    def __contains__(self, k): return k in self._d()
    def __iter__(self): return iter(self._d())
    def __len__(self): return len(self._d())
    def __bool__(self): return bool(self._d())


LAN_GOI_CUOI = _DictTheoLuong()
''')
i1 = mot(M_DEM_TOKEN, "DEM_TOKEN luot")
i2 = s.index(M_DEM_TOKEN_HET, i1)
cu = s[i1:i2 + len(M_DEM_TOKEN_HET)]
assert cu.count("\n") == 5, "khối cộng DEM_TOKEN không đúng 5 dòng"
s = s.replace(cu, "    with _KHOA_DEM_TOKEN:          # soạn song song: cộng dồn từ nhiều luồng\n"
              + textwrap.indent(cu, "    "))
mot("DEM_TOKEN = {", "DEM_TOKEN =")
s = s.replace("DEM_TOKEN = {", "import threading as _threading\n_KHOA_DEM_TOKEN = _threading.Lock()\nDEM_TOKEN = {", 1)

# ── 2. cmd_chay ─────────────────────────────────────────────────────────
i_loop = mot(M_LOOP, "vòng page")
i_b = mot(M_B, "khối soạn")
i_c_het = mot(M_C_HET, "hết khối hành động")
i_sau = s.index(M_SAU_LOOP, i_c_het)

ham_soan = f'''    # ── SOẠN SONG SONG, GỬI TUẦN TỰ (chủ shop 14/09, ca EsOr Adz — Saudi) ──────────────────
    # Đo 14/09: mỗi khách tốn ~10-15s soạn (model) + ~12s gửi; xử lần lượt thì lượt 4-6 khách mất
    # 1-2 phút, khách tới giữa lượt đợi hết lượt → EsOr đợi 5-7 phút. Nên chia vòng làm 3 bước:
    #   1. LỌC — mọi cửa (thẻ, đợi Botcake, treo, lên đơn sớm, trần chi…) chạy TUẦN TỰ như cũ,
    #      hội thoại cần model thì xếp vào `cac_viec`.
    #   2. SOẠN — gọi model + các lần bắt soạn lại, tối đa AI_SOAN_SONG_SONG luồng (mặc định 3).
    #      Bước này CHỈ ĐỌC: không gửi, không ghi Pancake/POS/sổ/file (va_song_song.py kiểm chữ).
    #   3. HÀNH ĐỘNG — gửi tin, ghi chú, lên đơn, ghi sổ, dời mốc: TUẦN TỰ đúng thứ tự như cũ, việc
    #      đầu gửi ngay khi soạn xong. Giãn cách 20s giữa hai lần gửi (luật 11/09) giữ nguyên, và
    #      `ai_da_bi_vuot` đọc lại hội thoại ngay trước khi gửi nên câu soạn sớm không đè sale/khách.
    # AI_SOAN_SONG_SONG=1 → soạn ngay trước khi gửi từng việc (gần giống bản cũ).
    cac_viec = []

    def _soan_viec(v):
        ({BIEN},) = v["bien"]
        dem = v["dem"]                       # đếm riêng của việc này — bước 3 cộng vào sổ chung
        _nk = v["nhat_ky"]

        def print(*a, **k):                  # noqa: A001 — gom log của luồng, bước 3 in theo thứ tự
            _nk.append(" ".join(str(x) for x in a))
        qd, err_m = None, "chưa soạn"
        try:
{khoi_b}        except Exception as _e:                # noqa: BLE001 — một luồng hỏng không giết vòng
            qd, err_m = None, f"lỗi lúc soạn: {{_e!r}}"
        v["qd"], v["err_m"], v["lan_goi"] = qd, err_m, dict(LAN_GOI_CUOI)
        return v

'''

# bước 1: khối soạn + khối hành động trong vòng → xếp việc
xep = f'''            # (soạn + hành động dời xuống bước 2-3 sau vòng page — xem khối SOẠN SONG SONG)
            cac_viec.append({{"bien": ({BIEN},), "nhat_ky": [], "dem": {{}}}})
'''
buoc_23 = f'''
    # ── bước 2 + 3: soạn song song, hành động tuần tự ─────────────────────
    _bom = None
    _luong = max(1, int(_so_env("AI_SOAN_SONG_SONG", 3)))
    if cac_viec and _luong > 1 and len(cac_viec) > 1:
        from concurrent.futures import ThreadPoolExecutor as _TPE
        _bom = _TPE(max_workers=min(_luong, len(cac_viec)))
        for _v in cac_viec:
            _v["tuong_lai"] = _bom.submit(_soan_viec, _v)
        print(f"  ⚡ soạn song song {{len(cac_viec)}} hội thoại · {{min(_luong, len(cac_viec))}} luồng", flush=True)
    try:
        for _v in cac_viec:
            if "tuong_lai" in _v:
                _v["tuong_lai"].result()
            else:
                _soan_viec(_v)
            for _mot_lan in (0,):             # để `continue` của khối cũ vẫn là "sang việc sau"
                ({BIEN},) = _v["bien"]
                for _dong in _v["nhat_ky"]:
                    print(_dong)
                for _k, _n in _v["dem"].items():
                    dem[_k] = dem.get(_k, 0) + _n
                qd, err_m = _v["qd"], _v["err_m"]
                LAN_GOI_CUOI.clear()
                LAN_GOI_CUOI.update(_v["lan_goi"])
                # Trần gửi theo page (luật 11/09) đã xét ở bước lọc, nhưng bước lọc chạy TRƯỚC mọi lần gửi
                # của lượt → hai việc cùng page có thể cùng lọt. Xét lại ngay trước khi hành động.
                if that and page_qua_tran_gui(pid) and (qd or {{}}).get("hanh_dong") not in (None, "im", "treo"):
                    print(f"{{nhan}} 🐢 page đã gửi {{_so_env('AI_GUI_MOI_PAGE_GIO', 10):.0f}} tin trong 1 giờ"
                          f" — nhường lượt này cho sale (luật 11/09, xét lại lúc gửi)")
                    continue
{textwrap.indent(khoi_c, "    ")}    finally:
        if _bom is not None:
            _bom.shutdown(wait=True)
'''
# khối soạn đổi print trong dòng chữ? không — hàm print cục bộ lo.
s = (s[:i_loop] + ham_soan + s[i_loop:i_b] + xep
     + "        time.sleep(0.15)\n" + buoc_23 + s[i_sau:])

# ── 3. trần chi tính cả việc đã xếp mà chưa soạn ─────────────────────────
mot(M_NGAN_SACH, "trần ngày")
mot(M_NGAN_SACH2, "trần tổng")
s = s.replace(M_NGAN_SACH,
              "                # việc đã xếp (bước 2 chưa soạn) chưa cộng vào da_hom_nay → ước trước để khỏi vượt trần\n"
              "                _uoc = len(cac_viec) * _so_env(\"AI_UOC_TIEN_MOI_LUOT\", 0.02)\n"
              "                if ns_ngay and da_hom_nay + _uoc >= ns_ngay:\n")
s = s.replace(M_NGAN_SACH2, "                elif ns_tong and da_tong + _uoc >= ns_tong:\n")

compile(s, f, "exec")
open(f, "w", encoding="utf-8").write(s)
print("✔ vá xong — biến:", BIEN)

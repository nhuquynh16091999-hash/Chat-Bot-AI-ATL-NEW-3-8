import json, collections, re, sys, os, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
kq = json.load(open("/opt/pancake-tool/state/luu_luong_toan_bo.json"))
m = json.load(open("markets.json"))
shop2tt = {str(v["shop_id"]): k for k, v in m.items() if isinstance(v, dict) and v.get("shop_id")}
TU_KHOA = [("uae", r"\bUAE\b|Dubai|\bUae\b"), ("saudi", r"Saudi|\bKSA\b|Ksa"), ("kuwait", r"Kuwait|\bKW\b"), ("qatar", r"Qatar"), ("bahrain", r"Bahrain"),
           ("oman", r"Oman"), ("taiwan", r"\bTW\b|Taiwan"), ("usa", r"\bU\.?S\.?\b|\bUS\b|USA"), ("japan", r"Japan|\bJP\b"), ("philippines", r"\bPH\b(?! in)|Philippines"), ("australia", r"Australia|\bAU\b")]
def tt_cua(p):
    if str(p.get("shop_id")) in shop2tt: return shop2tt[str(p["shop_id"])]
    for tt, rx in TU_KHOA:
        if re.search(rx, p.get("ten") or ""): return tt
    return "khác/không rõ"
for p in kq: p["tt"] = tt_cua(p)
# ── hệ số từ UAE: tiền thật / inbox trên các page AI đã gọi model, đúng 3 ngày 10-12/09 ──
rows = [json.loads(l) for l in open("state/uae/so_chi_phi.jsonl") if l.strip()]
NGAY_SO = {"2026-09-10", "2026-09-11", "2026-09-12"}   # đúng 3 ngày đo, khớp mốc Kimi trừ $1,49
g = [r for r in rows if r.get("goi") and r.get("that") and (r.get("luc") or "")[:10] in NGAY_SO]
pids_ai = {str(r["pid"]) for r in g}
ngay_ai = {"10/09/2026", "11/09/2026", "12/09/2026"}
inbox_ai = sum(v for p in kq if p["id"] in pids_ai for d, v in (p.get("theo_ngay") or {}).items() if d in ngay_ai)
goi_ai = len(g); tool_ai = sum(r.get("tien") or 0 for r in g)
KIMI_THAT = 1.49          # Kimi thực trừ tới 13/09 (API số dư)
he_so_that = KIMI_THAT / max(inbox_ai, 1); he_so_tool = tool_ai / max(inbox_ai, 1); goi_moi_inbox = goi_ai / max(inbox_ai, 1)
print(f"HỆ SỐ UAE: {len(pids_ai)} page AI, 10-12/09 có {inbox_ai} khách nhắn inbox (thống kê Pancake), {goi_ai} lượt gọi model, tool tính ${tool_ai:.2f}, Kimi trừ ${KIMI_THAT:.2f}")
print(f"  → mỗi khách nhắn: {goi_moi_inbox:.2f} lượt gọi · Kimi thật ${he_so_that:.4f} · tool ${he_so_tool:.4f}\n")

# ── Nhà ĐANG CHẠY (20/09: DeepSeek): giá thật mỗi lượt đo từ sổ mọi nước + số dư API, thay vì
#    xài lại hệ số Kimi của 10–12/09. Không đo được thì để None, bảng bỏ cột đó đi. ──
import quet_hoi_thoai as _q, bao_cao_tien as _BC, chi_phi as _CP
_env = _q.load_env()
nha_nay = (_env.get("AI_PROVIDER") or "kimi").strip().lower()
_tk = _BC.chi_moi_nuoc(nha_nay, moi_giay=0)
_nap = sum(float(x.get("so_tien") or 0) for x in _CP.doc_nap() if (x.get("nha") or nha_nay) == nha_nay)
_sd = _BC.so_du_kimi(_env)
gia_luot_nay = ((_nap - _sd["con"]) / _tk["luot"]) if (_sd.get("co") and _nap and _tk["luot"]) else None
nay_moi_khach = (gia_luot_nay * goi_moi_inbox) if gia_luot_nay else None
if nay_moi_khach:
    print(f"HỆ SỐ {nha_nay.upper()} (đo hôm nay, {_tk['luot']:,} lượt): ${gia_luot_nay:.6f}/lượt "
          f"→ ${nay_moi_khach:.6f}/khách nhắn, rẻ hơn Kimi {he_so_that/nay_moi_khach:.1f} lần\n")
else:
    print(f"Chưa đo được giá thật của {nha_nay} (thiếu số dư API hoặc chưa khai tiền nạp)\n")
TG = 26300
def dong(ten, ps):
    ib = sum(p["inbox"] for p in ps); n = len(ps); con_goi = sum(1 for p in ps if p.get("goi_con")); co_khach = sum(1 for p in ps if p["inbox"])
    ngay = 7; ib_ngay = ib / ngay
    return (ten, n, con_goi, co_khach, ib, ib_ngay, ib_ngay * goi_moi_inbox, ib_ngay * he_so_that * 30,
            ib_ngay * he_so_tool * 30, (ib_ngay * nay_moi_khach * 30) if nay_moi_khach else None)
theo_tt = collections.defaultdict(list)
for p in kq: theo_tt[p["tt"]].append(p)
print(f"{'thị trường':<16}{'page':>5}{'còn gói':>8}{'có khách':>9}{'khách/7ng':>10}{'khách/ngày':>11}{'gọi/ngày':>9}{'Kimi $/th':>10}{'tool $/th':>10}")
tong = [0]*8
for tt, ps in sorted(theo_tt.items(), key=lambda x: -sum(p["inbox"] for p in x[1])):
    r = dong(tt, ps); print(f"{r[0]:<16}{r[1]:>5}{r[2]:>8}{r[3]:>9}{r[4]:>10}{r[5]:>11.0f}{r[6]:>9.0f}{r[7]:>10.1f}{r[8]:>10.1f}")
    for i in range(1, 9): tong[i-1] += r[i]
print(f"{'TỔNG':<16}{tong[0]:>5}{tong[1]:>8}{tong[2]:>9}{tong[3]:>10}{tong[4]:>11.0f}{tong[5]:>9.0f}{tong[6]:>10.1f}{tong[7]:>10.1f}")
con = [p for p in kq if p.get("goi_con")]
r = dong("CHỈ PAGE CÒN GÓI", con); print(f"\n{r[0]}: {r[1]} page, {r[3]} có khách, {r[4]} khách/7 ngày → {r[5]:.0f} khách/ngày → ~{r[6]:.0f} lượt gọi/ngày → Kimi thật ${r[7]:.0f}/tháng (~{r[7]*TG/1e6:.1f} triệu) · tool tính ${r[8]:.0f}/tháng")
print("\nTOP 25 page đông khách nhất (7 ngày):")
for p in sorted(kq, key=lambda p: -p["inbox"])[:25]:
    print(f"  {p['inbox']:>5}  {p['tt']:<10} {'còn gói' if p.get('goi_con') else 'HẾT GÓI':<8} {p['ten'][:45]}")
print("\nlỗi thống kê:", sum(1 for p in kq if p.get("loi")), "| page không có gói:", sum(1 for p in kq if not p.get("goi_con")), "| role:", collections.Counter(p.get("role") for p in kq).most_common(5))
json.dump({"he_so": {"kimi_moi_khach": he_so_that, "tool_moi_khach": he_so_tool, "goi_moi_khach": goi_moi_inbox, "inbox_ai": inbox_ai, "goi_ai": goi_ai, "nha_nay": nha_nay, "gia_luot_nay": gia_luot_nay, "nay_moi_khach": nay_moi_khach, "luot_do_nay": _tk["luot"]}, "theo_tt": {tt: dong(tt, ps) for tt, ps in theo_tt.items()}, "page": kq}, open("/opt/pancake-tool/state/chi_phi_toan_bo.json", "w"), ensure_ascii=False)

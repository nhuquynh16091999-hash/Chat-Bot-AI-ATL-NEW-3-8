# Đối soát tiền Kimi (viết lại 19/09). Số phanh dùng là "CÒN CHẮC" — xem chi_phi.con_an_toan.
# Bỏ 3 dòng cũ "Đã nạp / Sổ TƯỞNG còn / SỔ ĐẾM THIẾU": chúng lấy nap_tien.json gõ tay (không ai
# cập nhật khi nạp) và sổ theo lượt khách (thiếu lượt soạn lại) nên luôn ra số sai, dễ đọc nhầm.
import sys, time
sys.path.insert(0, "/opt/pancake-tool")
import chi_phi

e = chi_phi._env_file()
san = float(e.get("AI_SO_DU_TOI_THIEU") or 0.30)
tre = float(e.get("AI_SO_DU_TRE_PHUT") or 20)
nha = (e.get("AI_PROVIDER") or "kimi").strip().lower()
k = chi_phi.con_an_toan(nha, e=e)
m = k.get("moc") or {}
goi = [(t, x) for t, x, n in chi_phi._doc_goi() if n == nha]
gio = lambda t: time.strftime("%H:%M:%S", time.localtime(t))

if k.get("con_api") is not None:
    print("%s — số trên bảng (trừ trễ 3-4 phút): $%.4f   (hỏi lúc %s)" % (nha, k["con_api"], gio(k["luc"])))
else:
    print("%s — số trên bảng: KHÔNG hỏi được (%s) — phanh vẫn chạy theo mốc" % (nha, k.get("loi_api")))
print("PHANH — CÒN CHẮC                     : $%.4f   → AI dừng khi ≤ $%.2f" % (k["con"], san))
if m:
    sau = [x for t, x in goi if t > m["t"]]
    print("   cách 1 (mốc):  $%.4f đọc lúc %s − %d lượt gọi sau đó $%.4f = $%.4f"
          % (m["con"], m["luc"][11:], len(sau), sum(sau), k["uoc_moc"]))
if k.get("uoc_api") is not None:
    gan = [x for t, x in goi if t > k["luc"] - tre * 60]
    print("   cách 2 (bảng): $%.4f − %d lượt gọi %.0f phút gần nhất $%.4f = $%.4f"
          % (k["con_api"], len(gan), tre, sum(gan), k["uoc_api"]))
    print("   → phanh lấy số NHỎ hơn. Cách 2 trừ cả phần Kimi đã trừ rồi nên thấp hơn vài xu — cố ý, cho chắc.")
ns_ngay = e.get("AI_NGAN_SACH_NGAY")
print("Hôm nay đã tiêu: $%.4f%s" % (chi_phi.da_chi_hom_nay(nha),
                                    (" · trần ngày $%s" % ns_ngay) if ns_ngay else " · không đặt trần ngày"))

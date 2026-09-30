"""Vá 18/09 — ĐO KHÂU PHÁT HIỆN TIN MỚI (chủ shop: "bạn tốn thời gian lâu nhất ở khâu nào, phát hiện tin mới à").
In mỗi vòng dò có tin khách mới: bao nhiêu giây từ lúc khách gửi tới lúc vòng dò nhìn thấy.
Chạy: python3 va_do_phat_hien.py ai_sale.py"""
import sys
f = sys.argv[1]
src = open(f, encoding="utf-8").read()
if "🔎 phát hiện" in src:
    sys.exit("đã vá rồi — không làm gì")
cu = ("        for cid in moi:\n"
      "            nong[cid] = time.time()\n"
      "            cho_xu.add(cid)\n")
moi = ("        for cid in moi:\n"
       "            nong[cid] = time.time()\n"
       "            cho_xu.add(cid)\n"
       "        # 18/09: ĐO KHÂU PHÁT HIỆN — khách gửi lúc nào (updated_at) → vòng dò thấy lúc nào. Lượt mồi bỏ qua.\n"
       "        _tre_ = sorted(_giay_tu((thong_tin.get(k) or {}).get(\"updated_at\")) for k in moi\n"
       "                       if loai.get(k) == \"khach\") if lan > 1 else []\n"
       "        _tre_ = [x for x in _tre_ if 0 <= x < 600]\n"
       "        if _tre_:\n"
       "            print(f\"  🔎 phát hiện {len(_tre_)} tin khách mới · trễ {_tre_[len(_tre_) // 2]:.0f}s\"\n"
       "                  f\" (lâu nhất {_tre_[-1]:.0f}s) từ lúc khách gửi\", flush=True)\n")
assert src.count(cu) == 1, src.count(cu)
src = src.replace(cu, moi)
compile(src, f, "exec")
open(f, "w", encoding="utf-8").write(src)
print("đã vá 1 chỗ")

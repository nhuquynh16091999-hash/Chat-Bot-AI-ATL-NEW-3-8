#!/bin/bash
# Lọc ảnh SẢN PHẨM trong BỘ SƯU TẬP (thư mục ảnh) của từng page → state/<tt>/mau_khac.json.
# AI Sale đọc file này khi khách xin ảnh / xin mẫu khác (ai_sale.anh_bo_suu_tap_cho_khach, chủ shop duyệt 21/09).
# Chạy SAU quet_thu_muc_anh.py (cron 03:20). Chỉ hỏi model ảnh MỚI (~$0,0001/ảnh) — ảnh cũ nhớ trong
# state/chung/anh_loai_bst.json. Ghi ra file .moi rồi mới đổi tên: AI không bao giờ đọc phải file dở.
cd /opt/pancake-tool || exit 1
TT="uae saudi kuwait qatar oman bahrain"
echo "=== $(date '+%F %T') bắt đầu"
python3 phan_loai_bo_suu_tap.py state/chung/anh_loai_bst.json $TT --luong=4 2>&1 | grep -v "^  [🚨⏸🔁👤]\|^     "
for t in $TT; do
  if python3 chon_mau.py state/chung/anh_loai_bst.json "$t" --ra="state/$t/mau_khac.json.moi" > "/tmp/chon_mau_$t.log" 2>&1; then
    mv "state/$t/mau_khac.json.moi" "state/$t/mau_khac.json"
    echo "  $t: $(grep -c 'BẬT' /tmp/chon_mau_$t.log) page bật"
  else
    echo "  $t: chon_mau HỎNG — giữ file cũ"; tail -3 "/tmp/chon_mau_$t.log"
  fi
done
echo "=== $(date '+%F %T') xong"

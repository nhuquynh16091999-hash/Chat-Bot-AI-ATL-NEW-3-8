# Triển khai bản clone AI Sale (server riêng, shop VIỆT NAM)

Thư mục này chứa các file cài **ngoài** `/opt/pancake-tool` trên server. Trong đó không có key hay mật khẩu nào.

| File | Cài vào | Việc |
|---|---|---|
| `cai-key-shop` | `/usr/local/bin/cai-key-shop` (chmod 700) | Chủ shop dán key POS, user token Pancake và key DeepSeek. Lệnh kiểm key thật rồi mới ghi `.env` / `markets.json` |
| `mo-web` | `/usr/local/bin/mo-web` (chmod 700) | Mở trang quản lý cho IP của máy đang SSH vào |
| `nginx/aisale-web.conf` | `/etc/nginx/conf.d/` | Trang quản lý qua HTTPS cổng 8449, chỉ cho IP trong `/etc/nginx/aisale-web/ip-cho-phep.conf` |
| `systemd/aisale-chat@.service` | `/etc/systemd/system/` | Mẫu service bot cho 1 nước |
| `systemd/aisale-chat-vietnam.service` | `/etc/systemd/system/` | Bot nước Việt Nam (trang quản lý tìm đúng tên `aisale-chat-<nước>`) |
| `systemd/aisale-giao-dien.service` | `/etc/systemd/system/` | Trang quản lý (127.0.0.1:8765) |

## Lệnh hay dùng

```bash
ssh -t root@139.180.131.21 cai-key-shop vietnam   # dán / đổi key (dán nguyên đoạn, lệnh tự nhận)
ssh root@139.180.131.21 mo-web                    # đổi mạng mà web báo 403 → mở cho IP mới
ssh root@139.180.131.21 ai-sale-gui-that tat      # TẮT KHẨN CẤP gửi thật (về chạy thử)
ssh root@139.180.131.21 ai-sale-gui-that xem      # đang gửi thật hay chạy thử
ssh root@139.180.131.21 'tail -f /var/log/aisale-chat-vietnam.log'
```

## Ghi chú vận hành (09/11/2026)

- Bot đang **CHẠY THỬ**: service không có cờ `--that`, nên không gửi gì cho khách. Muốn gửi thật thì thêm `--that` vào `ExecStart`, nhưng chỉ khi chủ shop đã duyệt.
- Đã **tắt tự gắn page theo tiền tệ**: `state/chung/tu_gan_luc.txt` = `9999999999`. Chữ `k` của VND khớp nhầm "18k vàng", gắn sai 6 page trang sức vào Việt Nam.
- Đổi DNS sang `1.1.1.1` / `8.8.8.8`. DNS Vultr `108.61.10.10` thỉnh thoảng trả sai IP pancake.vn, làm tải kịch bản lỗi SSL. Bản cũ ở `/root/resolv.conf.truoc-doi-dns`.
- 12/11: chuẩn bị gửi thật. Biến môi trường của bot Việt Nam:
  - `AI_TEN_TAI_KHOAN=Sỹ Anh Antalo`: tài khoản AI gửi tin. Người chat tay bằng tài khoản này sẽ bị coi là AI, nên tách tài khoản riêng cho AI.
  - `AI_NHUONG_SALE_PHUT=30`: sale nhắn khách trong 30 phút gần nhất thì AI tránh hội thoại đó.
  - `AI_LEN_DON=0`: AI chốt với khách nhưng không tự tạo đơn POS. Câu chốt vẫn gửi, ghi chú dặn sale lên đơn.
- `aisale-bat-gui-that.timer`: hẹn giờ bật gửi thật (thêm `--that`).
- 12/11: trang quản lý đổi giao diện theo app ANTALO (màu logo, Plus Jakarta Sans, thanh bên có nhóm + biểu tượng,
  thanh trên báo bot GỬI THẬT / CHẠY THỬ, nền sáng/tối, ngăn kéo trên điện thoại). Logo: chép tay
  `/opt/talpha/dashboard-ui/public/antalo-mark.png` → `/opt/pancake-tool/static/antalo-mark.png` (thư mục static/ không lên git).

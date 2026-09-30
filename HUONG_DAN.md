# Hướng dẫn tạo đơn Pancake POS tự động

Công cụ này dùng **Open API chính thức của Pancake POS** (`https://pos.pages.fm/api/v1`) để:
- Tạo đơn hàng: nhập tên, SĐT, địa chỉ, sản phẩm, COD, ghi chú
- Tự động chuyển trạng thái đơn (Mới → Đã xác nhận → Đã gửi hàng…)
- Tìm sản phẩm, xem đơn hàng

## Bước 1 — Lấy API key (làm 1 lần duy nhất)

1. Đăng nhập [Pancake POS](https://pos.pancake.vn/)
2. Vào **Cài đặt → Nâng cao → Kết nối bên thứ 3 → Webhook/API**
3. Ở khung **API KEY**, bấm **Tạo** và sao chép key

> ⚠️ API key có quyền như tài khoản admin. Không gửi cho ai, không dán lên mạng.

## Bước 2 — Cấu hình

1. Trong thư mục `pancake-tool`, sao chép file `.env.example` thành file tên `.env`
2. Dán API key vào dòng `PANCAKE_API_KEY=...`
3. Chạy lệnh sau để lấy mã cửa hàng:

```bash
python3 pancake_order.py cuahang
```

4. Điền mã vào dòng `PANCAKE_SHOP_ID=...` trong file `.env`

## Bước 3 — Sử dụng hằng ngày

### Tạo đơn (hỏi từng bước — dễ nhất)

```bash
python3 pancake_order.py tao
```

Script sẽ hỏi lần lượt: tên khách → SĐT → địa chỉ → tìm & chọn sản phẩm → COD → phí ship → ghi chú → trạng thái. Xem lại toàn bộ đơn rồi mới bấm `y` để tạo.

**Mẹo:**
- **Địa chỉ**: gõ nguyên câu kèm tiểu vương quốc, ví dụ `Al Barsha 1, villa 12, Dubai` — script tự nhận diện Dubai/Abu Dhabi/Sharjah... và gắn vùng cho đơn.
- **Giá**: nhập số AED (được phép lẻ: `49.5`). Khi script hỏi giá là hỏi TỔNG tiền của dòng đó. Giá sản phẩm trong kho đang để 0 nên luôn phải nhập.
- **1 sản phẩm = 1 dòng**: khách lấy 2 cái (kể cả mua 1 tặng 1) thì số lượng 2, không thêm sản phẩm 2 lần.
- **Trạng thái**: để trống là "Mới"; gõ `xacnhan` để đơn tạo xong tự chuyển "Đã xác nhận".

### Tạo đơn nhanh 1 dòng

```bash
python3 pancake_order.py tao --ten "Maria Santos" --sdt 0501234567 --diachi "Al Barsha 1, villa 12, Dubai" --sp "gold necklace:2=99" --trangthai xacnhan
```

`--sp "từ khóa:SL=TỔNG_AED"` (2 cái tổng 99 AED) hoặc `--sp "từ khóa:SL@đơn_giá"` — lặp lại `--sp` nếu nhiều sản phẩm khác nhau; `--qua "từ khóa:SL"` cho quà là sản phẩm khác. Thêm `--yes` để bỏ qua bước xác nhận.

### Tìm sản phẩm

```bash
python3 pancake_order.py sp "áo thun"
```

### Chuyển trạng thái đơn

```bash
python3 pancake_order.py trangthai 12345 xacnhan
```

Xem toàn bộ bảng mã trạng thái: `python3 pancake_order.py trangthai`

| Mã | Trạng thái | Gõ tắt |
|----|------------|--------|
| 0 | Mới | `moi` |
| 17 | Chờ xác nhận | `choxacnhan` |
| 1 | Đã xác nhận | `xacnhan` |
| 8 | Đang đóng hàng | `donghang` |
| 9 | Chờ chuyển hàng | `chochuyen` |
| 2 | Đã gửi hàng | `dagui` |
| 3 | Đã nhận | `danhan` |
| 16 | Đã thu tiền | `thutien` |
| 6 | Đã hủy | `huy` |

### Xem đơn hàng

```bash
python3 pancake_order.py don 12345
```

## Tự động lên đơn từ hội thoại (quét theo tag "Lên đơn")

Quy trình: khi khách đã chốt đơn trong hội thoại Pancake, bạn **gắn tag "Lên đơn"** vào hội thoại đó (thao tác quen thuộc trên Pancake). Hệ thống quét liên tục sẽ:

1. Thấy tag là **lên đơn ngay** — đọc tin nhắn, trích: tên, SĐT, địa chỉ, sản phẩm, số lượng, giá COD đã chốt
2. **Kiểm tra chống trùng 2 lớp**: hội thoại đã xử lý rồi thì bỏ qua; và nếu **sale đã tạo đơn tay** cho hội thoại/SĐT này rồi → **không tạo mới**, mà **sửa bổ sung vào đơn có sẵn** + nối thêm ghi chú nội bộ
3. **Đủ thông tin** → tạo đơn + tự bấm **"Đã xác nhận"** luôn. Nhân viên chỉ cần check đơn rồi chuyển "Chờ in"
4. **Thiếu thông tin** (chưa có SĐT, chưa chốt giá...) → **vẫn tạo đơn** với những gì có, để trạng thái "Mới" (không xác nhận), ghi chú rõ thiếu gì, và báo lại bạn
5. Đơn nào cũng gắn thẳng vào hội thoại (mở đơn trên POS thấy luôn chat) + ghi chú "đơn tự động"

Cấu hình thêm trong `.env`:

```
PANCAKE_USER_TOKEN=   # pages.fm → Tài khoản → Cài đặt cá nhân → API Access Token
TAG_NAME=Lên đơn      # tên tag đánh dấu đã chốt đơn
PAGES=                # để trống = quét tất cả page; hoặc liệt kê id cách nhau dấu phẩy
```

Lệnh thủ công:

```bash
python3 quet_hoi_thoai.py pages     # xem page nào đã sẵn sàng
python3 quet_hoi_thoai.py setup     # tạo token + dò tag cho từng page (chạy 1 lần)
python3 quet_hoi_thoai.py quet      # quét ngay bây giờ
python3 quet_hoi_thoai.py pending   # xem hội thoại đang chờ lên đơn
```

Quy trình chi tiết cho phiên chạy tự động: xem `QUET_PROMPT.md`.

## Lưu ý an toàn

- Lần đầu dùng, hãy **tạo 1 đơn thử** rồi vào Pancake POS kiểm tra, sau đó **hủy đơn thử** (`trangthai <mã đơn> huy`).
- Script luôn hiện bản xem lại đơn và hỏi xác nhận trước khi tạo (trừ khi bạn thêm `--yes`).
- File `.env` chứa API key — đừng chia sẻ thư mục này cho người khác.

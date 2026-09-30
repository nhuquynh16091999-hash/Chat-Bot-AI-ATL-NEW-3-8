# Cẩm nang cài hệ thống tự động lên đơn lên SERVER — từng bước cho người mới

Sau khi cài xong: hệ thống chạy 24/7 trên server, **không cần bật máy tính của bạn**. Nhân viên gắn tag "Lên đơn" vào hội thoại → 30–60 giây sau đơn tự xuất hiện trên POS.

> 🌍 **Hệ thống chạy ĐA THỊ TRƯỜNG** — 11 thị trường trong file `markets.json`: UAE, Saudi, Kuwait, Qatar, Oman, Bahrain, Đài Loan, Nhật, Mỹ, Tây Ban Nha, Romania. Mỗi thị trường tự dùng đúng tiền tệ (Nhật/Đài tính nguyên, còn lại ×100), định dạng SĐT, tỉnh/bang riêng. Xem danh sách: `python3 auto_len_don.py thi-truong`

---

## Chuẩn bị (cần đủ 3 thứ trước khi bắt đầu)

1. **Địa chỉ IP của server** — dạng 4 cụm số, ví dụ `103.57.220.15`. Nhà cung cấp VPS gửi khi bạn thuê (tìm trong email hoặc trang quản lý VPS).
2. **Tài khoản đăng nhập server** — thường là user `root` + mật khẩu (cũng do nhà cung cấp gửi).
3. **Máy Mac của bạn có sẵn Terminal** — không cần cài gì thêm.

> 📌 Trong toàn bộ hướng dẫn, chỗ nào viết `IP_SERVER` thì bạn **thay bằng IP thật** của bạn. Ví dụ thấy `root@IP_SERVER` mà IP của bạn là `103.57.220.15` thì gõ `root@103.57.220.15`.

**Mở Terminal trên Mac:** bấm `Cmd + phím cách` (Spotlight) → gõ `Terminal` → Enter. Hiện ra cửa sổ đen/trắng để gõ lệnh — tất cả các bước dưới đây đều gõ vào đó.

---

## Bước 1 — Chép thư mục lên server (làm trên máy Mac)

Dán lệnh sau vào Terminal (sửa IP_SERVER) rồi Enter:

```bash
scp -r "/Users/phanhiuuu/LEVEL UP/Levelup - Sale/pancake-tool" root@IP_SERVER:/opt/pancake-tool
```

**Những gì sẽ hiện ra lần lượt:**

1. Lần đầu kết nối sẽ hỏi:
   `Are you sure you want to continue connecting (yes/no/[fingerprint])?`
   → Gõ `yes` rồi Enter.
2. Hỏi mật khẩu: `root@IP_SERVER's password:`
   → Gõ mật khẩu server rồi Enter.
   > ⚠️ **Gõ mật khẩu sẽ KHÔNG hiện gì trên màn hình** (không có dấu `*` luôn) — đó là bình thường, cứ gõ đủ rồi Enter.
3. Chạy đúng thì thấy hàng loạt tên file lướt qua (`pancake_order.py 100%...`). Xong không báo lỗi gì là thành công.

**Nếu gặp lỗi:**
- `Permission denied` → sai mật khẩu, gõ lại lệnh và nhập lại cẩn thận.
- `Connection refused` hoặc đứng im lâu rồi `timeout` → sai IP, hoặc server chưa bật — kiểm tra lại trang quản lý VPS.
- `No such file or directory` → đường dẫn thư mục trên máy sai. Mở Finder, tìm đúng thư mục `pancake-tool`, kéo thả nó vào Terminal để lấy đường dẫn chính xác.

---

## Bước 2 — Đăng nhập vào server

Vẫn trong Terminal:

```bash
ssh root@IP_SERVER
```

Nhập mật khẩu như trên. Đăng nhập thành công thì đầu dòng lệnh đổi thành kiểu `root@ten-server:~#` — từ giờ **mọi lệnh gõ ra là chạy TRÊN SERVER** (muốn thoát về máy mình thì gõ `exit`).

Kiểm tra server có Python chưa (hầu hết có sẵn):

```bash
python3 --version
```

- Hiện `Python 3.x.x` → OK, sang bước 3.
- Hiện `command not found` → cài bằng: `apt update && apt install -y python3` (đợi chạy xong).

---

## Bước 3 — Chạy THỬ (chưa tạo đơn thật, để kiểm tra mọi thứ thông suốt)

```bash
cd /opt/pancake-tool && python3 auto_len_don.py chay --thu
```

**Đọc kết quả:**
- Nếu không có hội thoại nào mới gắn tag: chỉ hiện `Hội thoại chờ lên đơn: 0` — nghĩa là kết nối Pancake OK, không có gì để xử lý. Vậy là ĐẠT.
- Muốn thử "tận răng": nhờ nhân viên gắn tag **"Lên đơn"** vào 1 hội thoại đã chốt, rồi chạy lại lệnh trên. Sẽ thấy dòng `[THỬ] Sẽ tạo đơn...` in ra đủ tên/SĐT/địa chỉ/sản phẩm/giá — nó nói **sẽ** làm gì chứ chưa tạo thật.
- Báo lỗi đỏ gì đó → chụp/copy nguyên văn gửi vào chat cho Claude xem giúp.

---

## Bước 4 — Bật chạy tự động 24/7

Gõ lần lượt 3 lệnh (vẫn đang ở trong server):

```bash
cp /opt/pancake-tool/pancake-len-don.service /etc/systemd/system/
```

*(đăng ký chương trình với hệ thống — lệnh này chạy xong im lặng là đúng)*

```bash
systemctl daemon-reload
```

*(bảo hệ thống đọc lại danh sách — cũng im lặng)*

```bash
systemctl enable --now pancake-len-don
```

*(BẬT chạy ngay + tự khởi động lại mỗi khi server reboot. Có thể hiện dòng `Created symlink...` — là đúng)*

**Kiểm tra nó đang sống:**

```bash
systemctl status pancake-len-don
```

Nhìn dòng `Active:` — thấy **`active (running)`** màu xanh là đang chạy. Bấm phím `q` để thoát màn hình này.

**Xem nó đang làm gì (nhật ký thời gian thực):**

```bash
tail -f /opt/pancake-tool/state/nhat_ky.log
```

Mỗi khi có đơn được tạo/bổ sung sẽ hiện dòng mới ở đây. Bấm `Ctrl + C` để thoát xem (chương trình vẫn chạy tiếp, chỉ là mình không nhìn nữa).

---

## Bước 5 — Hẹn giờ tự học sản phẩm mỗi tuần

Bảng "page nào bán sản phẩm gì, giá nào ứng với mấy cái" học từ đơn cũ — cần cập nhật hàng tuần để bắt kịp page mới/deal mới. Dán nguyên lệnh sau (1 lần duy nhất):

```bash
(crontab -l 2>/dev/null; echo "0 6 * * 1 cd /opt/pancake-tool && python3 auto_len_don.py hoc-san-pham >> state/nhat_ky.log 2>&1") | crontab -
```

*(nghĩa là: 6h sáng thứ Hai hàng tuần tự học lại. Kiểm tra đã cài chưa: gõ `crontab -l` — thấy dòng vừa thêm là OK)*

---

## Bước 6 — Kích hoạt từng thị trường (làm khi muốn mở thị trường nào)

Thị trường nào muốn chạy tự động thì cần 2 điều kiện:

1. Các page của thị trường đó **có tag "Lên đơn"** (tạo trong Pancake, dùng đồng bộ thiết lập giữa các page cho nhanh)
2. Chạy setup cho thị trường đó trên server (tạo token + dò tag), ví dụ Saudi:

```bash
cd /opt/pancake-tool && python3 auto_len_don.py setup saudi
```

Tên thị trường: `uae`, `saudi`, `kuwait`, `qatar`, `oman`, `bahrain`, `taiwan`, `japan`, `usa`, `spain`, `romania`. Xem thị trường nào đã sẵn sàng bao nhiêu page:

```bash
python3 auto_len_don.py thi-truong
```

Daemon tự quét mọi thị trường đã setup — không cần cài gì thêm khi mở thêm thị trường.

## Bước 7 — Kiểm tra thực chiến lần cuối

1. Trên Pancake, gắn tag **"Lên đơn"** vào 1 hội thoại khách đã chốt thật
2. Đợi 30–60 giây
3. Mở POS → thấy đơn mới xuất hiện, gắn đúng hội thoại, có ghi chú "[Tự động]"
4. Xem thêm trong log server (`tail /opt/pancake-tool/state/nhat_ky.log`) có dòng `✔ Tạo đơn #...`

Xong! Gõ `exit` để rời server — hệ thống vẫn chạy mãi trên đó.

---

## Vận hành hằng ngày (cheat sheet)

| Muốn làm gì | Gõ gì (sau khi `ssh root@IP_SERVER`) |
|---|---|
| Xem hệ thống sống không | `systemctl status pancake-len-don` (thoát: phím `q`) |
| Xem nhật ký đơn mới nhất | `tail -50 /opt/pancake-tool/state/nhat_ky.log` |
| Theo dõi trực tiếp | `tail -f /opt/pancake-tool/state/nhat_ky.log` (thoát: `Ctrl+C`) |
| Tạm DỪNG toàn bộ | `systemctl stop pancake-len-don` |
| Chạy lại | `systemctl restart pancake-len-don` |
| Học lại sản phẩm ngay (mọi thị trường) | `cd /opt/pancake-tool && python3 auto_len_don.py hoc-san-pham` |
| Xem trạng thái các thị trường | `cd /opt/pancake-tool && python3 auto_len_don.py thi-truong` |
| Thêm page mới có tag / page vừa gia hạn gói cước | `cd /opt/pancake-tool && python3 auto_len_don.py setup <thị trường>` |
| Chạy thử 1 thị trường không tạo đơn thật | `cd /opt/pancake-tool && python3 auto_len_don.py chay saudi --thu` |
| **Soi vì sao khách X chưa lên đơn** | `cd /opt/pancake-tool && python3 auto_len_don.py soi kuwait "Amani"` |
| **Bắt hệ thống lên đơn lại cho khách X** | `cd /opt/pancake-tool && python3 auto_len_don.py lam-lai kuwait "Amani"` |
| Tạm tắt 1 thị trường | sửa `markets.json`: đổi `"bat": true` thành `false` rồi restart |
| **Báo cáo page mới: thiếu tag / chưa chốt SKU** | `cd /opt/pancake-tool && python3 auto_len_don.py bao-cao` |
| Kết nạp page mới NGAY (không đợi nhịp 1 tiếng) | `cd /opt/pancake-tool && python3 auto_len_don.py ket-nap uae` |
| Xem page nào đã chốt SKU bằng suy luận | `cd /opt/pancake-tool && python3 ket_nap_page.py ho-so uae` |

## Page mới đẻ hằng ngày — hệ thống tự kết nạp (ket_nap_page.py)

Mỗi thị trường, **1 tiếng 1 lần**, daemon tự làm 3 việc cho page vừa lập:

1. **Tạo page token** cho page mới (chỉ page CHƯA có token — tạo lại sẽ giết token cũ).
   Page báo lỗi gói cước bị đánh dấu `bo_qua` và không bao giờ nhắc lại.
2. **Chốt page bán SKU nào**: mã sản phẩm trong bài post → khớp tên sản phẩm trong
   catalog → hỏi AI 1 lần rồi nhớ vĩnh viễn. Không chốt được thì đơn vẫn được tạo,
   treo cờ "thiếu sản phẩm" và hiện trong `bao-cao`.
3. **Đọc bảng giá → số lượng** từ chính lời chào hàng của bot
   ("Buy 1 Get 1 FREE – 99 AED" → 99 AED = 2 cái), nên page chưa có đơn nào vẫn lên
   đơn đủ. Riêng đơn vị gộp kiểu "1 Set" thì CỐ Ý bỏ qua vì POS nhập khác số lượng.

Bảng học từ **đơn thật** (`hoc-san-pham`) luôn thắng phần suy luận này.

### Hai thứ phải bật trên server (chỉ làm 1 lần)

```bash
pip3 install anthropic
```

Rồi thêm 2 dòng vào `/opt/pancake-tool/.env`:

```
PANCAKE_SERVER=1
ANTHROPIC_API_KEY=sk-ant-...
```

- `PANCAKE_SERVER=1` là **khóa an toàn**: thiếu nó thì hệ thống KHÔNG tạo page token.
  Tuyệt đối không đặt biến này trên máy Mac — chạy kết nạp từ Mac sẽ vô hiệu toàn bộ
  token của server.
- Thiếu `ANTHROPIC_API_KEY` thì mọi thứ vẫn chạy, chỉ mất tầng chốt SKU bằng AI:
  page nào luật không đoán được sẽ nằm chờ trong `bao-cao`.

Script chỉ đọc `.env` lúc khởi động, nên sửa xong nhớ `systemctl restart pancake-len-don`.

## Khi khách đã gắn tag mà vẫn chưa lên đơn — soi ngay

```bash
cd /opt/pancake-tool && python3 auto_len_don.py soi <thị trường> "<tên khách>"
```

Lệnh này CHỈ ĐỌC (không tạo/sửa đơn), in ra: page nào, **tag "Lên đơn" đã gắn chưa**, toàn bộ tin nhắn, và **hệ thống trích được gì / thiếu gì**. Nhìn phát biết ngay nguyên nhân:
- `✖ CHƯA GẮN` tag → nhân viên quên gắn tag
- `Không thấy hội thoại nào` → page đó **token hỏng** (xem mục dưới), chưa setup được (thường do hết gói cước Pancake), hoặc thuộc thị trường khác
- Trích ra `✖ KHÔNG BẮT ĐƯỢC` ở mục nào → gửi kết quả này cho Claude để bổ sung luật

> ⚠️ **Tag tạo SAU khi setup thì máy không biết.** Danh sách tag được ghi nhớ lúc chạy `setup`.
> Hễ vừa tạo tag "Lên đơn" cho page nào (hoặc vừa mở page mới) thì **phải chạy lại**
> `python3 auto_len_don.py setup <thị trường>` rồi `systemctl restart pancake-len-don`,
> nếu không nhân viên gắn tag mà máy vẫn không thấy.
>
> Page lỡ có **2 tag cùng tên "Lên đơn"** thì máy nhận cả hai — gắn cái nào cũng chạy.
> Dù vậy nên xoá bớt cho gọn: nhân viên mỗi người gắn 1 cái khác nhau rất khó lần ra.

## Page báo TOKEN HỎNG — cả page im lặng, gắn tag cũng không lên đơn

Token của page có thể chết bất cứ lúc nào (Pancake cấp token mới thì token cũ hết hiệu lực).
Khi đó API vẫn trả "thành công" nhưng **không có hội thoại nào** — trước 03/09/2026 hệ thống
hiểu nhầm thành "page này không có ai gắn tag" và im lặng bỏ qua, sale gắn tag "Lên đơn"
mà **không đơn nào được tạo, không ai được báo**. Nay hệ thống báo thẳng ra:

- trong `state/nhat_ky.log` mỗi khi danh sách page hỏng thay đổi (và nhắc lại 1 giờ/lần)
- trong `python3 auto_len_don.py bao-cao` — page hỏng KHÔNG còn được đếm là "page chạy được"
- trong `python3 auto_len_don.py pages <thị trường>` — cột token ghi `✖ TOKEN HỎNG`

Kiểm tra và chữa (chạy TRÊN SERVER — token của máy Mac và của server là 2 bộ khác nhau,
đo trên Mac không nói lên điều gì về server):

```bash
cd /opt/pancake-tool && python3 ai_sale.py token <thị trường>          # đếm sống/hỏng, ghi dấu
cd /opt/pancake-tool && python3 auto_len_don.py setup <thị trường> --force-token --hong   # cấp lại token
```

`setup <thị trường>` KHÔNG cấp lại được: nó chỉ tạo token cho page **chưa có** token.
Phải kèm `--force-token --hong` mới cấp lại cho đúng những page đang bị đánh dấu hỏng.

Cấp token xong nhớ **quét bù**: vòng quét thường chỉ nhìn lại 72 giờ, nên hội thoại gắn tag
trong lúc token chết sẽ bị bỏ sót vĩnh viễn nếu không quét bù.

```bash
cd /opt/pancake-tool && python3 auto_len_don.py chay <thị trường> --gio 720 --thu   # xem trước 30 ngày
cd /opt/pancake-tool && python3 auto_len_don.py chay <thị trường> --gio 720         # chạy thật
```

## Kiểm soát chi phí AI Sale (thêm 2026-09-04)

Trước 04/09/2026, `ai_sale.py` chỉ đếm token trong bộ nhớ rồi in ra cuối vòng chạy — chạy xong
là mất. Không ai biết tổng đã chi bao nhiêu, ngày nào tốn, page nào tốn, và **không có gì chặn
khi tiền chạy quá tay**. Nay mỗi lượt quét ghi 1 dòng vào sổ:

- `state/<thị trường>/so_chi_phi.jsonl` — token + tiền + kết quả từng hội thoại
- `state/nap_tien.json` — tiền đã nạp cho nhà cung cấp (phải **tự khai bằng tay**, không có
  API nào của Kimi/Anthropic trả về số dư)

```bash
cd /opt/pancake-tool && python3 ai_sale.py cau_hinh              # model, độ sáng tạo, trần chi, prompt
cd /opt/pancake-tool && python3 ai_sale.py cau_hinh --xem        # in luôn toàn văn luật gửi cho model
cd /opt/pancake-tool && python3 ai_sale.py nap 20 --nha kimi --ghi "lần 1"   # khai tiền vừa nạp
cd /opt/pancake-tool && python3 ai_sale.py bao_cao               # gộp mọi thị trường, 30 ngày
cd /opt/pancake-tool && python3 ai_sale.py bao_cao usa --ngay 7
```

Báo cáo có: đã nạp / đã chi / còn lại / còn chạy được bao nhiêu ngày · chi theo ngày · chi theo
page · tỷ lệ phản hồi · top câu hỏi của khách.

### Một màn quản lý — giao diện web

```bash
cd /opt/pancake-tool && python3 ai_sale.py dashboard usa --phuc-vu
```

Mở `http://127.0.0.1:8765` — ứng dụng 5 tab, lưu bằng API nên không nạp lại trang:

| Tab | Làm gì |
|---|---|
| Tổng quan | nạp bao nhiêu thì đủ · sàn/trần · lưu lượng · khách hỏi gì |
| Cấu hình | nhà cung cấp, model, độ sáng tạo, trần chi, API key — **tiền dự báo đổi ngay khi chọn model khác**, chưa cần lưu. Nút **Thử key** gọi model đúng 1 lượt cực ngắn để biết key có dùng được không và ra **số token thật** |
| Hướng dẫn trả lời | sửa thẳng `luat_model.md` — thứ duy nhất gửi cho model |
| Tiền nong | đã nạp / đã chi / còn lại, khai tiền vừa nạp, chi theo page |
| Đo lại | chạy `du_bao` nền, nhật ký chảy trực tiếp lên trang |

- Máy chủ **chỉ nghe ở 127.0.0.1** và còn kiểm header `Host` — không ai ngoài mạng gọi vào được.
  Trên VPS thì mở đường hầm từ máy Mac:
  `ssh -L 8765:127.0.0.1:8765 root@<IP server>` rồi vào `http://127.0.0.1:8765`.
- Mỗi lần lưu, bản cũ chép sang `.env.bak` / `luat_model.md.bak`. Chú thích trong `.env` giữ nguyên.
- Ô API key để **trống nghĩa là giữ nguyên key cũ**, không phải xoá. Trang không bao giờ in key ra.
- Lưu hướng dẫn ngắn dưới 200 ký tự bị **từ chối** — chống xoá nhầm cả bộ luật.
- **KHÔNG có nút gửi tin cho khách** — cố ý. Gửi thật vẫn chỉ chạy bằng
  `ai_sale.py chay <thị trường> --that`.
- **Không sửa được `PANCAKE_*`** từ giao diện: token Pancake hỏng là cả hệ thống lên đơn chết,
  việc đó phải làm có ý thức bằng tay.

Bản tĩnh chỉ đọc (gửi cho người khác xem, publish được):

```bash
cd /opt/pancake-tool && python3 ai_sale.py dashboard usa      # ra bang_dieu_khien.html
```

### Hướng dẫn gửi cho model nằm ở đâu (đổi 2026-09-04)

Trước đây luật nằm cứng trong `ai_sale.py`, nên ai cũng tưởng sửa `LUAT_AI_SALE.md` là AI đổi
cách trả lời — **không phải**. Nay tách ra `luat_model.md`:

| File | Ai đọc | Sửa thì sao |
|---|---|---|
| `luat_model.md` | **model** | vòng chạy sau dùng bản mới ngay, không cần khởi động lại |
| `LUAT_AI_SALE.md` | người | AI **không** đổi hành vi |
| "Trả lời nhanh" trên Pancake | model (kèm mỗi lượt) | tải lại bằng `kich_ban.py tai <tt>` |

`ai_sale.py` vẫn giữ một bản dự phòng nhúng trong code: mất `luat_model.md` thì hệ thống chạy
tiếp chứ không chết, và nút "Khôi phục bản gốc" trên giao diện lấy đúng bản đó.

### Kịch bản "Trả lời nhanh" tự đồng bộ (thêm 2026-09-05)

Kịch bản nằm trên Pancake (`pancake.vn/<page_id>/setting/reply`), nhưng tool dùng **bản chụp**
ở `state/<tt>/kich_ban.json`. Trước 05/09/2026, sửa kịch bản trên Pancake mà quên chạy
`kich_ban.py tai` thì AI vẫn tư vấn theo bản cũ — **đo thật hôm đó: 20/27 page Mỹ đã đổi kịch
bản so với bản chụp 03/09 (thêm mẫu `/MoneyOrder`, `/MoneyGram+WesternUnion`) mà không ai hay.**

Nay `ai_sale.py chay` và `du_bao` **tự đồng bộ ở đầu mỗi vòng**, dùng mẹo `client_version` của
API Pancake — gửi đúng số phiên bản đang giữ thì API trả vỏn vẹn `{"data":"data_up_to_date"}`:

```
hỏi toàn bộ                → 20.000 byte
hỏi "bản 13 còn mới không" →    100 byte     (nhẹ hơn 200 lần)
```

Kiểm cả 27 page Mỹ mất ~10 giây, và **chỉ tải lại page nào thật sự vừa sửa**. Chạy tay:

```bash
cd /opt/pancake-tool && python3 kich_ban.py dongbo usa
```

Tắt khi cần chạy nhanh: thêm `--khong-dong-bo` vào lệnh `chay` / `du_bao`.

**Page hết gói cước Pancake thì không lấy được kịch bản.** API trả `success=false`, mã 121
("Không tìm thấy gói cước nào cho người dùng này") hoặc 122 ("Gói cước đã hết hạn"). Tool gộp
các lỗi này lại in một dòng cho đỡ nhiễu. Tình trạng 05/09/2026:

| Thị trường | Lấy được kịch bản | Hết gói cước |
|---|---|---|
| usa | 20/27 page | **7 page** (03/09 còn lấy được đủ 27) |
| uae | 42/138 page | **96 page** |

Page hết gói cước vẫn giữ bản chụp cũ nên AI vẫn chạy được, nhưng **không cập nhật được nữa**.
Gia hạn xong nhớ chạy `python3 kich_ban.py tai <thị trường>` — `dongbo` chỉ soi những page
đã có trong bản chụp, không tự phát hiện page mới hồi sinh.

### Ảnh trong mẫu kịch bản (thêm 2026-09-05)

Trước đó tool chỉ lấy phần CHỮ của mẫu và vứt ảnh đi, nên AI trả lời thiếu ảnh đúng những mẫu
quan trọng nhất — `/Paypal`, `/VENMO`, `/CASH_APP`, `/MONEY_ORDER`, `/MoneyGram+WesternUnion`:
gửi chữ mà thiếu ảnh hướng dẫn thì khách Mỹ không biết chuyển tiền kiểu gì.

Nay `kich_ban.json` giữ cả đường dẫn ảnh (host `content.pancake.vn`):

| Thị trường | Mẫu | Mẫu có ảnh | Ảnh |
|---|---|---|---|
| usa | 1.555 | 283 | 570 |
| uae | 721 | 129 | 339 |

Cách chạy: trong gói prompt, mẫu có ảnh được đánh dấu `[KÈM n ẢNH]` ngay sau tên mẫu. Model
muốn gửi thì đặt `"anh_mau": "<tên mẫu>"` trong JSON trả về; tool tra đúng mẫu đó, tải ảnh từ
Pancake, tải lên page rồi gửi **trước** lời nhắn (ảnh và chữ bắt buộc là hai tin riêng — API
từ chối gửi chung). Tên mẫu không khớp thì bỏ qua, không đoán bừa.

`content_id` của mỗi ảnh được nhớ lại ở `state/<tt>/anh_mau_da_tai.json`: cùng một ảnh
`/Paypal` gửi cho hàng trăm khách chỉ tải lên một lần. Tối đa 4 ảnh mỗi lần gửi.

Trường `anh_mau` được mô tả trong `luat_model.md` — sửa hướng dẫn thì đừng xoá phần đó,
không thì model không biết đường xin gửi ảnh nữa.

⚠️ `kich_ban.py dongbo` chỉ tải lại page **vừa sửa**, nên page chưa đổi vẫn giữ bản chụp cũ
không có đường dẫn ảnh. Muốn có ảnh cho mọi page thì chạy một lần đầy đủ:
`python3 kich_ban.py tai <thị trường>` (lệnh này nay GỘP vào bản cũ, page lỗi không bị mất).

### Đo TRƯỚC khi nạp tiền

```bash
cd /opt/pancake-tool && python3 ai_sale.py du_bao usa --gio 24
```

Quét hội thoại thật, chạy đủ bộ luật, dựng đúng gói prompt sẽ gửi rồi **dừng ngay trước lượt
gọi model** — không tốn xu nào. Ra hai kịch bản, cố ý không gộp thành một số:

- **SÀN** — chỉ những lượt AI buộc phải vào cuộc lúc đo (Botcake im, hoặc Botcake rep mà
  AI phải xét lại).
- **TRẦN** — cộng thêm những lượt hôm nay sale thật đã vào trước. Chạy thật thì AI chỉ đợi
  Botcake ~90 giây rồi nhắn, tức nó vào **trước** sale — **lấy cột trần mà quyết ngân sách**.

Đo thật 04/09/2026 trên 27 page Mỹ, cửa sổ 24 giờ: 288 lượt khách/ngày, sàn 17 lượt/ngày,
trần 286 lượt/ngày. Quy ra tiền: kimi-k3 $200–273/tháng · kimi-k2 $62–85/tháng.

**Trần chi** (`.env`) — vượt là vòng `chay` tự dừng giữa chừng, hội thoại chưa xử để vòng sau
quét lại nên không mất đơn. Để trống là **không có gì chặn**:

```
AI_NGAN_SACH_NGAY=1.5      # USD mỗi ngày
AI_NGAN_SACH_TONG=         # USD cộng dồn
AI_TEMPERATURE=0.3         # độ sáng tạo 0–1; trống = mặc định nhà cung cấp (1.0, bay nhất)
```

Trần tính trên **API key**, tức cộng dồn mọi thị trường — không phải trần riêng từng nước.

⚠️ **Hướng dẫn trả lời mà model thật sự đọc là biến `LUAT` trong `ai_sale.py`**, KHÔNG phải
`LUAT_AI_SALE.md`. File .md là sổ luật cho người đọc; sửa mình nó thì AI không đổi hành vi.

## Khi cần CẬP NHẬT code sau này

Claude sửa file trên máy Mac → bạn chép **CHỈ các file `.py`** lên server (chạy trên máy Mac):

```bash
scp "/Users/phanhiuuu/LEVEL UP/Levelup - Sale/pancake-tool/"*.py "/Users/phanhiuuu/LEVEL UP/Levelup - Sale/pancake-tool/markets.json" root@IP_SERVER:/opt/pancake-tool/
```

rồi vào server chạy `systemctl restart pancake-len-don`.

> ⚠️ **TUYỆT ĐỐI không chép đè thư mục `state/` từ máy lên server sau lần cài đầu** — `state/` trên server ghi nhớ hội thoại nào đã lên đơn; đè bản cũ lên là server "quên" và tạo đơn TRÙNG hàng loạt.

## Cách hệ thống quyết định (để nhân viên nắm)

| Tình huống | Hành động |
|---|---|
| Đủ 5 mục (tên, SĐT khách, địa chỉ có tỉnh/bang, sản phẩm + số lượng, giá shop chốt) | Tạo đơn + tự **"Đã xác nhận"** — nhân viên check rồi chuyển "Chờ in" |
| Thiếu mục nào đó | Vẫn tạo đơn với phần đã có, để **"Mới"**, ghi chú rõ thiếu gì |
| **Khách nhắn bổ sung sau đó** (5 phút/lần, theo dõi 3 ngày) | Tự quay lại **điền nốt chỗ trống** vào đúng đơn đó; đủ rồi thì **tự chuyển "Đã xác nhận"**. Chỉ điền chỗ trống — không ghi đè dữ liệu sale đã nhập, không đụng đơn nhân viên đã chuyển trạng thái |
| **Bảng SP của page dính hàng TEST** (tên có "test", "demo", "huỷ ngay"…) | **KHÔNG đẩy sản phẩm** sang vận chuyển — đơn TREO ở "Mới", ghi chú rõ tên SP nghi test để nhân viên chọn tay. Xoá đơn test trong POS rồi chạy lại `hoc-san-pham` là hết |
| **Địa chỉ chỉ có mỗi tên thành phố** (vd khách chỉ nhắn "مكة المكرمة") | TREO ở "Mới" — shipper không giao được nếu thiếu đường/số nhà |
| Sale đã tạo đơn **từ chính hội thoại này** (hoặc vừa tạo tay trong POS < 24h, cùng SĐT) | KHÔNG tạo trùng — chỉ điền chỗ trống + nối ghi chú |
| Khách **mua lại** / mua ở **page khác** (cùng SĐT nhưng hội thoại khác) | VẪN tạo đơn mới, ghi chú nhắc kiểm tra đơn cũ |
| 1 hội thoại lỗi 5 lần liên tiếp | Ghi "cần xử lý tay" vào nhật ký, bỏ qua để không kẹt các đơn khác |

### Quy ước lên đơn (đã khớp cách team làm tay)

- **Tiền thu khách nhập vào PHÍ VẬN CHUYỂN**, giá sản phẩm để 0 (giống đơn nhân viên tạo tay)
- **Đơn vị vận chuyển tự điền theo thị trường**: UAE→J&T, Saudi→VPN, Kuwait→POSTAL, Oman→asyad, Qatar→IMILE, Bahrain→UBEX, Đài Loan→NAZA, Nhật→NAZA JP. Riêng **Mỹ**: Golden Buddha (131) / Birth stone set (010) / Ginseng Serum (071) → **AMI**, còn lại → **CJ**
- **Trang sức luôn kèm hộp 008** (nhận theo tên sản phẩm + theo đơn cũ của page). Thị trường không dùng hộp: Oman, Mỹ, Qatar, Bahrain, Nhật (đặt bằng `dung_hop` trong markets.json)
- **Sản phẩm nhiều mẫu mã** (vd Birth stone set 12 tháng, Jade Bracelet 4 màu): chọn đúng mẫu khách nhắn; khách chưa nói rõ mẫu → đơn để "Mới" chờ nhân viên (không đoán bừa)

Luật trích xuất: SĐT chỉ lấy từ tin của KHÁCH (không dính số WhatsApp shop); địa chỉ phải chứa tiểu vương quốc (Dubai, Abu Dhabi...); giá lấy từ tin shop chốt kiểu "Your order is 99 AED"; sản phẩm + số lượng tra theo bảng đã học của từng page (99 AED → 2 cái, 149 → 4 cái...).

Địa chỉ còn xử lý thêm 3 kiểu khách hay gõ:
- **Khách copy nguyên cái form của shop** rồi điền vào giữa → tự cắt bỏ phần nhãn ("Your full name", "Contact number:") và phần hướng dẫn ở đuôi, chỉ giữ đoạn địa chỉ thật.
- **Gõ tách làm nhiều tin** ("مكة المكرمة" một tin, tên đường một tin) → tự gộp lại (chỉ gộp khi tin đầu quá ngắn, để không nuốt nhầm tin tán gẫu).
- **Gõ bằng tiếng Ả Rập** → nhận được tên tỉnh/thành Ả Rập cho Saudi, UAE, Kuwait, Qatar, Oman, Bahrain (viết أ hay ا, ة hay ه đều khớp). Thiếu thành phố nào thì bổ sung vào `ALIAS_AR` trong `auto_len_don.py`.

## Đơn LANDING PAGE (Webcake) — chạy chung trong cùng daemon

Đơn từ landing page đổ thẳng vào POS ở trạng thái **"Mới"**, đã có sẵn tên khách, SĐT, sản phẩm, số lượng, tiền COD — **chỉ thiếu ô ĐỊA CHỈ**: Webcake nhét cả form (địa chỉ + dòng ưu đãi) vào phần **Ghi chú**, ô địa chỉ giao hàng để trống nên đơn không đẩy được sang vận chuyển. Nhân viên đang phải chép tay từng đơn.

Máy làm đúng việc đó (file `don_landing.py`, daemon gọi sẵn sau mỗi vòng quét hội thoại của từng thị trường):

| Tình huống | Hành động |
|---|---|
| Đơn bán **HÀNG TEST** ("SP TEST", "Test", "N/A"...) | Chỉ chuyển **"Chờ hàng"** + ghi chú — KHÔNG xác nhận, KHÔNG cho vào "Chờ in", không điền địa chỉ/ĐVVC, không đem so trùng |
| Đọc được địa chỉ + tỉnh/thành, SĐT đúng định dạng, giá và số lượng khớp giữa ghi chú và đơn | Điền địa chỉ + chuẩn hóa SĐT (+ điền COD nếu đơn đang để 0) rồi tự **"Đã xác nhận"** — nhân viên chuyển "Chờ in" |
| Không dò ra tỉnh/thành, đơn không có sản phẩm, lệch giá hoặc lệch số lượng | Vẫn điền được gì thì điền, nhưng **để "Mới"** + ghi chú rõ cần kiểm tra gì |
| **SĐT thiếu/thừa chữ số, sai định dạng, hoặc đơn không có SĐT** (luật user 2026-08-24) | **HỦY LUÔN** + ghi chú rõ lý do — đơn landing không có hội thoại nên gọi không được là hết đường hỏi lại khách. Đơn **Facebook** thì ngược lại: để nguyên "Mới" cho nhân viên nhắn hỏi khách |
| SĐT trùng với đơn khác trong 14 ngày (khách bấm gửi form 2–3 lần) | **Không xác nhận** — ghi chú chỉ rõ trùng với đơn nào, ai, bao nhiêu tiền, lúc nào, để nhân viên quyết hủy hay giao |
| Đơn đã bị máy sàng lọc ghi "TREO" | Không xác nhận, để nhân viên xử lý |

Cách dò tỉnh/thành: khớp tên chuẩn → viết tắt (`DU`, `DXB`, `AUH`, `RAK`...) → gần đúng khi khách gõ sai chính tả (Buraidah ≈ Buraydah). Mặc định chỉ xử lý đơn về trong **3 ngày** gần nhất — đơn tồn lâu hơn để nhân viên tự quyết.

### SĐT nước ngoài (luật user 2026-08-23)

| Trường hợp | Máy làm gì |
|---|---|
| **Kuwait** (user chốt 23/08) và **Bahrain** (24/08): số không phải số bản địa | **Để "Mới"** + ghi chú "bắt buộc số bản địa mới giao được đơn: gọi khách xin số &lt;nước&gt;". Khai bằng khóa `sdt_bat_buoc_ban_dia` trong `markets.json`; muốn thêm nước nữa thì chỉ cần thêm khóa này, không phải sửa code |
| Thị trường khác, số nước ngoài đọc ra được (`+63…` Philippines, `+91…`, `+20…`) | **Vẫn chạy bình thường** tới "Chờ in"; ghi số vào đơn KÈM MÃ NƯỚC (`+639171234567`) vào cả ô SĐT khách lẫn ô người nhận, để ĐVVC liên hệ được qua **WhatsApp**; ghi chú nhắc rõ đây là số nước ngoài |
| **Saudi**, số không phải số Saudi | Vẫn chạy, nhưng ghi chú đầu tiên là "⚠ KHÔNG đẩy iMile của VPN — cho đi hãng khác của VPN" (iMile bắt buộc số Saudi). Câu này khai ở `ghi_chu_sdt_ngoai` trong `markets.json` |
| Số gõ nhầm mã nước (`996…` thay vì `966…`), hoặc số nước khác gõ thiếu mã nước | **Để "Mới"** — máy đọc ra được một số cụ thể để nhân viên thử gọi/WhatsApp nên KHÔNG hủy; ghi chú chỉ rõ sửa thành số nào |
| Số thiếu/thừa chữ số, số rác, không có số | Đơn **landing: HỦY LUÔN** (user chốt 2026-08-24 — không còn cách liên lạc khách). Đơn **Facebook: để "Mới"** cho nhân viên hỏi lại khách. Máy vẫn KHÔNG bao giờ tự bù chữ số |
| **Số nước ngoài gõ HỤT/THỪA thân số** (`+6391712` — nhận ra `+63` Philippines nhưng thân chỉ 5 chữ số) | Đơn **landing: HỦY**, **Facebook: treo "Mới"** (user chốt 2026-08-24: "phải đúng số"). Ghi chú nói rõ là số nước nào và thân số thiếu bao nhiêu, KHÔNG đem so với độ dài số bản địa |
| Số mở đầu bằng **một số 0 rồi tới mã nước** (`03365031008`) | **KHÔNG đọc thành số nước ngoài.** Một số 0 dẫn đầu là tiền tố gọi nội hạt, không phải cách viết quốc tế (`+` hoặc `00`) — đọc kiểu đó là gán bừa quốc tịch: số Pakistan này từng bị đọc thành `+33` số Pháp ở thị trường Kuwait. Coi như số hỏng → landing hủy / Facebook treo. Riêng số Philippines gõ kiểu bản địa `09XXXXXXXXX` vẫn nhận như cũ |

Điều kiện "số phải có WhatsApp" là do người chốt đơn bảo đảm — máy không kiểm tra được số có WhatsApp hay không.

| Muốn làm gì | Gõ gì |
|---|---|
| Chạy thử đơn landing page, không sửa gì | `cd /opt/pancake-tool && python3 don_landing.py chay --thu` |
| Xem máy đọc được gì từ 1 đơn | `cd /opt/pancake-tool && python3 don_landing.py xem 46153 uae` |
| Xử lý cả đơn tồn 30 ngày (chạy tay 1 lần) | `cd /opt/pancake-tool && python3 don_landing.py chay --ngay 30` |
| Chỉ điền địa chỉ, KHÔNG tự xác nhận | thêm `--khong-xac-nhan` vào lệnh trên |

## Lưu ý bảo mật & bảo trì

- File `.env` trong thư mục chứa API key quyền admin của shop — **không gửi thư mục này cho ai**.
- `PANCAKE_USER_TOKEN` hết hạn ~31/10/2026 — chỉ ảnh hưởng lệnh `setup` (thêm page mới); hệ thống đang chạy KHÔNG bị ảnh hưởng. Khi cần: lấy token mới ở pages.fm → Tài khoản → Cài đặt cá nhân → API Access Token, sửa vào `/opt/pancake-tool/.env`.
- Gặp bất kỳ lỗi gì: copy nguyên văn dòng lỗi (hoặc `tail -50 state/nhat_ky.log`) dán vào chat cho Claude.

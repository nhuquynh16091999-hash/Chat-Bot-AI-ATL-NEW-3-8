# Chạy AI Sale — tập ở máy mình trước, rồi mới bật trên VPS

> Viết 2026-09-08. Đọc `HUONG_DAN_SERVER.md` cho phần hạ tầng; file này chỉ nói **thứ tự thao tác**.

Nguyên tắc xuyên suốt: **mọi lệnh đều CHẠY THỬ theo mặc định.** Muốn ghi thật phải thêm cờ
(`--that`). Nên tập ở máy Mac gần như không rủi ro gì — trừ đúng một việc nói ở mục ⛔.

---

## ⛔ Ba việc TUYỆT ĐỐI không làm ở máy Mac

| Việc | Vì sao |
|---|---|
| **Sinh page token** | Pancake chỉ giữ MỘT token còn hiệu lực cho mỗi page. Mac sinh token là token VPS chết ngay, daemon lên đơn mù cả page đó. Đã khoá bằng `PANCAKE_SERVER=1` — Mac gọi sẽ bị chặn. |
| **`ai_sale.py chay ... --that`** | Gửi tin thật cho khách thật, và tạo đơn thật trên POS. |
| **`auto_len_don.py chay/daemon`** không kèm `--thu` | Tạo đơn thật. Hai máy cùng chạy = khách nhận hai câu trả lời, đơn tạo hai lần. |

Nhớ một câu: **thấy `--that` là dừng lại nghĩ.**

---

## A · Tập ở máy Mac — an toàn tuyệt đối

Chạy từ `/Users/phanhiuuu/LEVEL UP/Levelup - Sale/pancake-tool`.

### A1. Nhìn toàn cảnh bằng giao diện web

```bash
python3 ai_sale.py dashboard usa --phuc-vu
```

Tám màn ở `127.0.0.1:8765`. Đây là chỗ dễ hiểu luồng nhất — xem trước, đọc sau.
Bốn màn đáng xem trước: **Page & kịch bản** · **Sổ cổng chặn** · **Hàng chờ sale** · **Cấu hình**.

### A2. Page nào sẵn sàng, còn thiếu gì

```bash
python3 quan_ly.py page usa
```

Thang bậc: `1` chưa có kịch bản · `2` chưa có SKU · `3` không rút được giá · `4` đủ.
Page token chết bị loại khỏi bảng, không tính.

### A3. Kịch bản và giá của một page

```bash
python3 chan_gui.py thu usa "SkinPop Glow US"
```

In bộ giá neo / giá bán / **sàn theo từng combo**, và **tập số AI được phép nói**.
Con số nào AI nói ra ngoài danh sách này sẽ bị cổng chặn giữ lại.

### A4. Luật trích xuất hồ sơ khách

```bash
python3 ho_so.py thu kuwait
```

Xem máy dò rút ra tên / SĐT / địa chỉ / số lượng / thanh toán thế nào ở từng thị trường.
Đổi `kuwait` sang `usa`, `uae`, `bahrain` để so.

### A5. Cổng chặn tin ra

```bash
python3 chan_gui.py tu_kiem
```

32 ca kiểm dựng sẵn, phải xanh hết. Đây là hàng rào cuối trước khi tin tới khách.

### A6. Xem AI sẽ vào cuộc ở đâu — CHỈ ĐỌC

```bash
python3 ai_sale.py loc usa --so 30
```

Không gọi model, không tốn tiền. Cho biết trong 30 hội thoại gần nhất, AI sẽ
trả lời / im / treo ở bao nhiêu ca, và vì sao.

### A7. Đo tiền trước khi nạp

```bash
python3 ai_sale.py du_bao usa --gio 24
```

Quét hội thoại thật, dựng đúng gói prompt sẽ gửi, **rồi dừng ngay trước lượt gọi model**.
Ra con số "một ngày cần bao nhiêu lượt gọi" để biết nạp bao nhiêu là đủ.

### A8. Chạy thử trọn vòng — có gọi model, KHÔNG gửi cho khách

```bash
python3 ai_sale.py chay usa --page 1023138250882033 --gio 24 --so 20
```

Đây là bước sát thật nhất: quét hội thoại thật → soạn câu thật → đi qua cổng chặn thật →
**in ra màn hình thay vì gửi**. Có tốn tiền API. Không có `--that` nên khách không nhận gì.

Xong thì xem lại hai màn trên giao diện: **Sổ cổng chặn** và **Hàng chờ sale** — vòng thử
cũng ghi sổ.

---

## B · Chạy thật trên VPS

```bash
ssh root@169.58.33.8
cd /opt/pancake-tool
```

### B0. Chữa hậu quả đợt 2026-09-08 — làm một lần

Ngày 08/09 có 29 page bị sinh token từ máy Mac, nên token trên VPS của chúng đã chết.
Cấp lại cho từng thị trường:

```bash
for m in uae saudi taiwan qatar oman bahrain usa; do python3 auto_len_don.py setup $m --force-token --hong; done
```

### B1. Kiểm token

```bash
python3 ai_sale.py token usa
```

Còn page hỏng thì chạy lại B0 cho đúng thị trường đó.

### B2. Kết nạp page mới + chốt SKU

```bash
python3 phan_thi_truong.py soi
```

Xem trước page mới thuộc thị trường nào (theo tiền tệ trong kịch bản). Ưng thì:

```bash
python3 phan_thi_truong.py ket-nap --that
```

Rồi chốt SKU cho từng thị trường vừa có page mới:

```bash
python3 ket_nap_page.py ket-nap uae
```

Cần `ANTHROPIC_API_KEY` trong `.env` cho tầng chốt SKU bằng AI. Thiếu key thì vẫn chạy,
chỉ mất tầng đó — page không chốt được sẽ nằm chờ trong `bao-cao`.

### B3. Học bảng sản phẩm từ đơn thật

```bash
python3 auto_len_don.py hoc-san-pham usa
```

Nên chạy **định kỳ**, nhất là sau khi bật thêm page mới. Bảng cũ thì đơn tạo ra dạng
"THIẾU, để Mới" và sale phải sửa tay từng đơn.

### B4. Tải kịch bản

```bash
python3 kich_ban.py tai usa
```

Chỉ cần chạy cho thị trường mới. Về sau `ai_sale.py chay` tự đồng bộ đầu mỗi vòng —
marketer sửa "Trả lời nhanh" trên Pancake là vòng sau dùng ngay.

### B5. Dán key + đặt trần chi

Sửa `.env`, hoặc mở giao diện web qua đường hầm:

```bash
ssh -L 8765:127.0.0.1:8765 root@169.58.33.8
```

Rồi vào `127.0.0.1:8765` → tab **Cấu hình**. Đặt tối thiểu:

```
AI_TEMPERATURE=0.3
AI_NGAN_SACH_NGAY=<usd>
AI_NGAN_SACH_TONG=<usd>
```

Bấm **Thử key** để xác nhận key dùng được, và xem token thật một lượt tốn bao nhiêu.

### B6. Chạy thử trên VPS trước khi gửi thật

```bash
python3 ai_sale.py chay usa --gio 24 --so 20
```

Đọc kỹ những câu AI định gửi. Đọc luôn dòng `💵` — nếu **`đọc đệm 0`** thì bộ nhớ đệm
không chạy và Kimi đang đắt hơn Claude-có-đệm.

### B7. Gửi thật — một page trước

```bash
python3 ai_sale.py chay usa --page <ID> --gio 6 --so 10 --that
```

Bắt đầu bằng **một page**, cửa sổ hẹp. Xem trên Pancake: khách nhận đúng câu chưa,
hội thoại có quay về **chưa đọc** không, ghi chú có hiện không.

Ổn rồi mới mở rộng cả thị trường.

### B8. Chạy thật LIÊN TỤC — chế độ DÒ NHANH (từ 2026-09-10, UAE)

Yêu cầu chủ shop: *"xử lý tin nhắn nhanh nhất có thể, 1-2 phút"* — sale chờ 1-2 phút không
thấy AI là vào rep, và từ đó AI im luôn theo luật "sale đã vào".

Ba đời trong một ngày, để hiểu vì sao ra cách này:

| Đời | Cách | Khách nhắn → AI rep |
|---|---|---|
| 1 | timer 5 phút, mỗi lượt quét hết 43 page tuần tự (7-8 phút) | 7-13 phút |
| 2 | `chay --lap 20`: chạy mãi, đọc trước 8 luồng | 2-3 phút |
| **3** | **`theo_doi`**: 15s hỏi DANH SÁCH hội thoại (1 call/page), có tin khách mới thì xử **đúng hội thoại đó** | **~55s** (≤15s phát hiện + 30s đợi Botcake + ~10s soạn/gửi) |

```
aisale-chat.service   Type=simple · Restart=always
  python3 ai_sale.py theo_doi uae --giay 15 --cho 30 --that
log                   /var/log/aisale-chat.log
```

| Cờ | Nghĩa |
|---|---|
| `--giay 15` | nhịp dò. Bị Pancake chặn (429) thì tự giãn gấp đôi tới 60s rồi co lại — aicloser dò 6s cứng nhắc nên dính 50.881 lần 429 |
| `--cho 30` | đợi Botcake 30s — **chỉ ở page có Botcake**. Vòng dò tự học page nào có Botcake từ `last_sent_by.admin_name` trong danh sách hội thoại (miễn phí), lượt mồi nhìn 24h; page 24h không thấy Botcake → AI rep ngay, không đợi. Đo 10/09: 25/69 page UAE có Botcake. Đổi lại 45 nếu thấy khách hay nhận hai câu trả lời (bot + AI) |
| (không `--that`) | chạy thử: dò thật, soạn thật, KHÔNG gửi |

Lượt dò đầu chỉ ghi nhớ hiện trạng (không cày lại lịch sử) — trừ hội thoại vừa đổi trong 10 phút,
xử luôn, để khởi động lại service không làm rơi khách vừa nhắn (ca Faraisah 10/09: mất 15 phút).
Hội thoại đổi là "nóng" **trừ khi
người thật vừa gửi** (sale đã vào → AI im, khỏi tốn call đọc); bot/hệ thống vừa gửi vẫn nóng vì
câu khách có thể còn chưa được trả lời. Hội thoại nóng được giữ theo tới khi có kết cục; đang
"đợi Botcake" thì lượt sau xử tiếp; quá 5 phút thì bỏ. Page không có gì mới: **0 call thêm**.

Vì sao sale vẫn rep dù AI chạy (đo 2 giờ ngày 10/09, 52 ca): 28 ca trên page bị Facebook chặn
API; 16 ca sale rep trong ≤60s (trung vị 56s, nhanh nhất 9s); 22 page không có kịch bản vì hết
gói Pancake (lỗi 121/122). AI không thắng được người rep ở giây thứ 9 — muốn AI gánh thì sale
phải **nhường ~1 phút**.

| Muốn | Lệnh (trên VPS) |
|---|---|
| **DỪNG AI chat ngay** | `systemctl disable --now aisale-chat.service` |
| Bật lại | `systemctl enable --now aisale-chat.service` |
| Đang làm gì | `tail -f /var/log/aisale-chat.log` (dòng `🔥` = có tin mới, `💬` = đã gửi) |
| Xem AI sẽ làm gì mà không gửi | `python3 ai_sale.py theo_doi uae --giay 10` rồi Ctrl+C |

Page bị Facebook cấm gửi (`#2022`) ghi ở `state/uae/page_bi_fb_chan.json`. Facebook chỉ chặn
**kênh API** — sale vẫn gửi được qua giao diện Pancake. Nên ở page đó AI **vẫn soạn câu, không
gửi, mà ghi trọn câu vào ghi chú + đánh dấu chưa đọc** để sale chép gửi tay (ca Kilimanoor Aji,
10/09). Hết 1 giờ tool thử gửi thật lại một lần; còn bị chặn thì ghi lại mốc, lại chép vào ghi chú.
Từ 11/09: ở page bị chặn mỗi hội thoại chỉ soạn **1 câu / 15 phút** và dừng khi sale đã tự viết;
gửi ảnh qua API **tắt** (`AI_GUI_ANH=1` mới bật); giãn ≥20s giữa hai lần gửi, tối đa 10 tin/page/giờ
(`AI_GIAN_CACH_GUI`, `AI_GUI_MOI_PAGE_GIO`); cửa "đọc lại Botcake" tắt (`AI_XET_BOTCAKE=1` bật lại);
bản ghi đưa model đã cắt gọn, JSON trả về ngắn. Vì sao: mục cuối `LUAT_AI_SALE.md` — Facebook chặn theo
danh tính gửi qua API, 17/19 page bị chặn vài giờ sau lần đầu AI gửi.
`chay --lap N` vẫn còn, dùng khi cần quét bù cả cửa sổ rộng (`--gio 6`).

Mở thị trường mới: chép service thành `aisale-chat-<tt>.service`, đổi `uae`. Đừng nhét hai
thị trường vào một lệnh.

**Từ 14/09/2026 chạy 8 nước:** `aisale-chat.service` (UAE) + `aisale-chat-{saudi,kuwait,qatar,oman,bahrain,taiwan,usa}.service`,
log `/var/log/aisale-chat-<tt>.log`. Dừng hết: `systemctl disable --now aisale-chat.service 'aisale-chat-*.service'`.
Nhật / Tây Ban Nha / Romania / Bulgaria chưa có page nào có token → chưa chạy được. Trần chi `AI_NGAN_SACH_*` dùng chung cả 8 nước.

### B9. Giao diện theo dõi — có link thật

```
https://169.58.33.8:8448      tên đăng nhập: levelup   (mật khẩu RIÊNG, không dính trang 8444)
```

Quên mật khẩu thì **đặt lại** (không đọc ngược được, chỉ lưu dạng băm) — chạy trên VPS:

```bash
printf 'levelup:%s\n' "$(openssl passwd -6 'MẬT-KHẨU-MỚI')" > /etc/nginx/.htpasswd-aisale && systemctl reload nginx
```

Dùng `openssl passwd -6` (SHA-512). Đừng dùng `-apr1` qua ssh: dấu `$` trong hash bị shell
ăn mất, nginx báo "password mismatch" dù gõ đúng — đã dính 2026-09-10.

Trình duyệt sẽ cảnh báo chứng chỉ tự ký một lần — bấm "tiếp tục" là được, nội dung vẫn
mã hoá. nginx (`/etc/nginx/sites-enabled/aisale-dash`) đứng trước `giao_dien.py` vốn chỉ
nghe `127.0.0.1:8765`. Tab **Cấu hình** hiện `API_KEY` — vì vậy tuyệt đối không bỏ mật khẩu.

---

## C · Nhìn hằng ngày

```bash
python3 quan_ly.py chan usa
```

Cổng chặn tuần này chặn gì, vì lý do gì, page nào hay hỏng.

```bash
python3 quan_ly.py cho usa
```

Ca đang chờ người: treo, chờ xác minh nhà, bị cổng chặn giữ tin. Cột **quá 24h** là
cột phải xử ngay — quá cửa sổ nhắn của Facebook thì mất khách.

```bash
python3 phan_thi_truong.py soat
```

Page nào đang nằm sai thị trường so với tiền tệ trong kịch bản.

```bash
python3 ai_sale.py bao_cao usa --ngay 30
```

Nạp / chi / còn lại.

```bash
python3 hieu_suat.py do uae --gio 24            # hoặc: python3 ai_sale.py hieu_suat uae
python3 hieu_suat.py do uae --gio 24 --chay-that # chỉ tính từ lúc AI gửi thật lần đầu
python3 hieu_suat.py xem uae                    # in lại lần đo gần nhất
```

```bash
python3 so_model.py lay uae --so 40      # chụp mẻ 40 lượt thật (không gọi model, không tốn tiền)
python3 so_model.py chay uae --nha kimi  # gọi model trên mẻ — tốn ~40 lượt gọi
python3 so_model.py chay uae --nha deepseek
python3 so_model.py so uae               # bảng so sánh + các ca hai model lệch nhau
```

So hai model trên **cùng một mẻ hội thoại** trước khi đổi nhà cung cấp (11/09, chủ shop cần
~65đ/tin): chấm JSON đúng khuôn, cổng chặn, đúng ngôn ngữ, tiền, tốc độ, và trùng với quyết định
thật hôm đó. Key lấy từ `.env` — dán key nhà mới ở tab **Cấu hình**, KHÔNG đổi "Nhà cung cấp"
cho tới khi so xong. Mẻ lấy từ hội thoại đang chờ + các lượt máy đã gọi model thật trong 24h.

Ba câu chủ shop hỏi 10/09, một lệnh trả cả ba: **một tin AI tốn bao nhiêu** (tiền vòng thật ÷
tin gửi được, tách riêng tin soạn vào ghi chú khi page bị FB chặn), **AI xử lý bao nhiêu trên
tổng lượt khách nhắn** (đọc lại hội thoại thật trên API, xếp từng lượt theo ai trả lời: Botcake ≤5
phút / AI / sale / không ai), và **bảng theo page** — page có Botcake mà im quá nửa lượt là
Botcake set chưa hiệu quả, kèm 3 câu khách hỏi mà bot im để biết thêm từ khoá gì. Quét ~8 phút
với 69 page UAE (chỉ đọc, không tốn tiền model). Tab **Hiệu suất** trên giao diện web hiển thị
đúng số này. Định nghĩa từng cột nằm ở đầu `hieu_suat.py`.

---

## D · Hỏng thì soi ở đâu

| Triệu chứng | Lệnh |
|---|---|
| Page không lên đơn dù khách đã gắn tag | `python3 auto_len_don.py soi <tt> "<tên khách>"` |
| Không rõ vì sao AI im ở một hội thoại | `python3 ai_sale.py soi <tt> "<tên khách>"` |
| AI báo giá lạ | `python3 chan_gui.py thu <tt> "<tên page>"` |
| Nghi token chết | `python3 ai_sale.py token <tt>` |
| Kịch bản trên máy cũ | `python3 kich_ban.py dongbo <tt>` |
| Hồ sơ khách đang nhớ gì | `python3 ho_so.py xem <tt>` |

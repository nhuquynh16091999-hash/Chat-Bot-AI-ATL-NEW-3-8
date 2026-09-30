#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bảng điều khiển AI Sale — trang HTML gộp mọi số liệu về tiền, mở bằng trình duyệt.

Trang này trả lời đúng MỘT câu: "nạp bao nhiêu thì đủ, và mỗi tháng tốn bao nhiêu".
Nó đọc hai sổ và không tự gọi API nào:
  state/<tt>/du_bao.jsonl      — số đo của `ai_sale.py du_bao` (chưa tốn tiền)
  state/<tt>/so_chi_phi.jsonl  — chi phí thật của `ai_sale.py chay`

  python3 ai_sale.py dashboard [thị trường]
  python3 bang_dieu_khien.py [thị trường] [--than <file>]   # --than: bản không có khung <html>
"""

import html
import json
import os
import sys
import time
import webbrowser
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import chi_phi


# ───────────────────────── Gom số liệu ─────────────────────────

def thu_thap(mkey=None):
    d = {"mkey": mkey, "luc": time.strftime("%d/%m/%Y %H:%M")}

    # Cấu hình đang chạy
    import ai_sale as A
    nha, key, _url, model, _dem = A.nha_cung_cap()
    (gv, gd, gg, gr), khop_gia = A.gia_theo_model(nha, model)
    ns_ngay, ns_tong = chi_phi.ngan_sach(A.env())
    d["cf"] = {"nha": nha, "model": model, "co_key": bool(key), "khop_gia": khop_gia,
               "gia": (gv, gd, gg, gr), "nhiet_do": A.nhiet_do(),
               "ns_ngay": ns_ngay, "ns_tong": ns_tong, "luat_ky_tu": len(A.tai_luat())}

    # Dự báo
    d["db"] = chi_phi.bang_du_bao(mkey, in_ra=False)
    rows_db = [r for r in chi_phi.doc_du_bao(mkey) if not r.get("meta")]
    d["so_page"] = len({r.get("page") for r in rows_db if r.get("page")})
    d["so_page_bat"] = 0
    for tt in ([mkey] if mkey else os.listdir(os.path.join(SCRIPT_DIR, "state"))):
        f = os.path.join(SCRIPT_DIR, "state", tt, "page_tokens.json")
        if os.path.exists(f):
            try:
                d["so_page_bat"] += sum(1 for v in json.load(open(f, encoding="utf-8")).values()
                                        if v.get("token"))
            except Exception:
                pass
    cua = Counter(r.get("cua") for r in rows_db)
    d["cua"] = {"xet": cua["xet"], "tra_loi": cua["tra_loi"],
                "im": cua["im"], "treo": cua["treo"]}

    # Câu hỏi: toàn bộ, và riêng phần AI phải trả lời
    def nhom(rs):
        h = [r.get("hoi") for r in rs if (r.get("hoi") or "").strip()]
        return Counter(chi_phi.phan_nhom(x) for x in h), len(h)
    d["hoi_tat"], d["n_hoi_tat"] = nhom(rows_db)
    d["hoi_ai"], d["n_hoi_ai"] = nhom([r for r in rows_db
                                       if r.get("cua") in ("xet", "tra_loi")])

    # Chi phí thật
    recs = list(chi_phi.doc(mkey))
    d["nap"] = chi_phi.tong_nap(nha)
    d["da_chi"] = chi_phi.da_chi_tong(nha)
    d["hom_nay"] = chi_phi.da_chi_hom_nay(nha)
    d["so_du"] = chi_phi.so_du_that(nha, e=A.env(), moi_giay=120)
    theo_ngay = defaultdict(float)
    theo_page = defaultdict(float)
    for r in recs:
        theo_ngay[r.get("luc", "")[:10]] += r.get("tien") or 0
        theo_page[r.get("page") or "?"] += r.get("tien") or 0
    d["theo_ngay"] = sorted(theo_ngay.items())[-14:]
    d["theo_page"] = sorted(theo_page.items(), key=lambda x: -x[1])[:8]
    d["co_chi_that"] = any(v > 0 for _k, v in theo_ngay.items())
    return d


# ───────────────────────── Dựng trang ─────────────────────────

def _kh(x):
    return html.escape(str(x))


def _kr(lo, hi, dv="$"):
    """Khoảng tiền — luôn in ra dạng khoảng, không bao giờ giả vờ một con số chính xác."""
    if hi < 10:
        return f"{dv}{lo:,.2f}–{hi:,.2f}"
    return f"{dv}{lo:,.0f}–{hi:,.0f}"


CSS = """
:root{
  --nen:#F6F7F4; --mat:#FFFFFF; --muc:#161A15; --nhat:#6C7268; --vien:#E2E5DD;
  --nhan:#1E6F4C; --nhan-mo:#E7F1EA; --canh:#A9701A; --canh-mo:#FAF0DE;
  --nang:#A33528; --nang-mo:#FBEBE8; --bong:0 1px 2px rgba(22,26,21,.05);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --nen:#101310; --mat:#191C18; --muc:#E8ECE4; --nhat:#98A092; --vien:#282C26;
    --nhan:#5CBF8C; --nhan-mo:#16281F; --canh:#D6A24A; --canh-mo:#2A2213;
    --nang:#E0736A; --nang-mo:#2C1917; --bong:none;
  }
}
:root[data-theme="dark"]{
  --nen:#101310; --mat:#191C18; --muc:#E8ECE4; --nhat:#98A092; --vien:#282C26;
  --nhan:#5CBF8C; --nhan-mo:#16281F; --canh:#D6A24A; --canh-mo:#2A2213;
  --nang:#E0736A; --nang-mo:#2C1917; --bong:none;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--nen); color:var(--muc);
  font-family:"Be Vietnam Pro",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
.bao{max-width:1060px; margin:0 auto; padding:34px 22px 72px; display:flex;
     flex-direction:column; gap:34px}
h1{font-size:31px; font-weight:800; letter-spacing:-.022em; margin:0; text-wrap:balance}
h2{font-size:13px; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
   color:var(--nhat); margin:0 0 14px}
p{margin:0}
.phu{color:var(--nhat); font-size:14px}
.so{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
    font-variant-numeric:tabular-nums}

header{display:flex; flex-direction:column; gap:8px;
       border-bottom:1px solid var(--vien); padding-bottom:22px}
.mao{font-size:12px; letter-spacing:.12em; text-transform:uppercase;
     color:var(--nhan); font-weight:700}

/* Kết luận: phần duy nhất được to tiếng */
.ketluan{background:var(--mat); border:1px solid var(--vien); border-radius:4px;
         padding:26px 26px 24px; box-shadow:var(--bong);
         border-left:3px solid var(--nhan); display:flex; flex-direction:column; gap:18px}
.ketluan .hoi{font-size:19px; font-weight:700; letter-spacing:-.01em}
.doi{display:flex; flex-wrap:wrap; gap:26px}
.o{flex:1 1 200px; display:flex; flex-direction:column; gap:2px}
.o .nhan-o{font-size:12px; letter-spacing:.07em; text-transform:uppercase; color:var(--nhat);
           font-weight:700}
.o .to{font-size:29px; font-weight:800; letter-spacing:-.02em; line-height:1.15}
.o .to.xanh{color:var(--nhan)}
.o .ghi{font-size:13px; color:var(--nhat)}

/* Ô số liệu */
.luoi{display:grid; grid-template-columns:repeat(auto-fit,minmax(178px,1fr)); gap:1px;
      background:var(--vien); border:1px solid var(--vien); border-radius:4px;
      overflow:hidden}
.the{background:var(--mat); padding:17px 18px; display:flex; flex-direction:column; gap:3px}
.the .nhan-o{font-size:11.5px; letter-spacing:.07em; text-transform:uppercase;
             color:var(--nhat); font-weight:700}
.the .so-to{font-size:25px; font-weight:700; letter-spacing:-.02em}
.the .ghi{font-size:12.5px; color:var(--nhat)}

/* Bảng */
.cuon{overflow-x:auto; border:1px solid var(--vien); border-radius:4px; background:var(--mat)}
table{width:100%; border-collapse:collapse; font-size:14px}
th,td{text-align:right; padding:11px 15px; border-bottom:1px solid var(--vien);
      white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-size:11.5px; letter-spacing:.07em; text-transform:uppercase; color:var(--nhat);
         font-weight:700; background:var(--nen)}
tbody tr:last-child td{border-bottom:none}
tr.chon td{background:var(--nhan-mo); font-weight:600}
tr.re td{color:var(--nhan)}
.chip{display:inline-block; font-size:11px; font-weight:700; letter-spacing:.05em;
      text-transform:uppercase; padding:2px 7px; border-radius:3px; margin-left:8px}
.chip.dang{background:var(--nhan-mo); color:var(--nhan)}
.chip.re{background:var(--nhan-mo); color:var(--nhan)}

/* Thanh ngang cho top câu hỏi */
.thanhds{display:flex; flex-direction:column; gap:9px}
.dong{display:grid; grid-template-columns:1fr 52px; gap:12px; align-items:center}
.ten{font-size:14px}
.ray{height:7px; background:var(--vien); border-radius:2px; overflow:hidden; margin-top:5px}
.ray i{display:block; height:100%; background:var(--nhan); border-radius:2px}
.pt{font-size:13px; color:var(--nhat); text-align:right}

/* Danh sách kiểm */
.kiem{display:flex; flex-direction:column; gap:1px; background:var(--vien);
      border:1px solid var(--vien); border-radius:4px; overflow:hidden}
.muc{background:var(--mat); padding:15px 18px; display:flex; gap:14px; align-items:flex-start}
.dau{flex:0 0 auto; font-size:11px; font-weight:800; letter-spacing:.05em; padding:3px 8px;
     border-radius:3px; margin-top:2px}
.dau.ok{background:var(--nhan-mo); color:var(--nhan)}
.dau.canh{background:var(--canh-mo); color:var(--canh)}
.dau.nang{background:var(--nang-mo); color:var(--nang)}
.muc .noi{display:flex; flex-direction:column; gap:2px}
.muc b{font-weight:700}
code{font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12.5px;
     background:var(--nen); border:1px solid var(--vien); border-radius:3px; padding:1px 5px}
/* Form cấu hình — chỉ hiện khi mở bằng máy chủ localhost */
.form{background:var(--mat); border:1px solid var(--vien); border-radius:4px; padding:20px}
.hang{display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:16px}
label{display:flex; flex-direction:column; gap:5px; font-size:13px; font-weight:600}
label .gt{font-weight:400; color:var(--nhat); font-size:12.5px}
input,select{font-family:inherit; font-size:14px; color:var(--muc); background:var(--nen);
  border:1px solid var(--vien); border-radius:3px; padding:8px 10px; width:100%}
input:focus-visible,select:focus-visible,button:focus-visible{outline:2px solid var(--nhan);
  outline-offset:1px}
input[type=number],input[type=text]{font-family:"IBM Plex Mono",ui-monospace,monospace}
button{font-family:inherit; font-size:14px; font-weight:700; color:var(--mat);
  background:var(--nhan); border:1px solid var(--nhan); border-radius:3px;
  padding:9px 18px; cursor:pointer}
button.phu2{background:transparent; color:var(--nhan)}
button[disabled]{opacity:.5; cursor:default}
.thanhcong{background:var(--nhan-mo); color:var(--nhan); border:1px solid var(--nhan);
  border-radius:4px; padding:12px 16px; font-size:14px; font-weight:600}
.dangchay{background:var(--canh-mo); color:var(--canh); border:1px solid var(--canh);
  border-radius:4px; padding:12px 16px; font-size:14px; font-weight:600}
.trong{background:var(--mat); border:1px dashed var(--vien); border-radius:4px;
       padding:24px; color:var(--nhat); font-size:14px; text-align:center}
footer{border-top:1px solid var(--vien); padding-top:18px; color:var(--nhat); font-size:13px;
       display:flex; flex-direction:column; gap:5px}
@media (max-width:560px){ h1{font-size:25px} .o .to{font-size:24px} .bao{padding:24px 15px 56px} }
"""


def than(d, sua_duoc=False, bao=""):
    """Phần thân trang (không có khung <html>) — dùng chung cho file rời và cho Artifact.

    sua_duoc=True chỉ khi trang được phục vụ bởi máy chủ localhost (`phuc_vu`): lúc đó mới
    có form ghi thẳng vào .env. Bản tĩnh và bản Artifact luôn CHỈ ĐỌC — trang đã publish
    thì không thể với tới .env trên máy bạn.
    """
    cf, db = d["cf"], d["db"]
    pv = d["mkey"] or "mọi thị trường"
    r = []
    A = r.append

    A('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
      'family=Be+Vietnam+Pro:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;600'
      '&display=swap">')
    A(f"<style>{CSS}</style>")
    A('<div class="bao">')

    A('<header>')
    A(f'<div class="mao">Bảng điều khiển chi phí · {_kh(pv)}</div>')
    A('<h1>Nạp bao nhiêu thì đủ cho AI Sale?</h1>')
    if db:
        A(f'<p class="phu">Đo trên hội thoại thật trong {db["gio"]} giờ gần nhất: '
          f'{d["so_page"]} page có khách nhắn, trên tổng {d["so_page_bat"]} page đang bật. '
          f'Chạy đúng bộ luật và dựng đúng gói prompt sẽ gửi — nhưng '
          f'<b>không gọi model, nên chưa tốn xu nào</b>. Cập nhật {_kh(d["luc"])}.</p>')
    else:
        A('<p class="phu">Chưa có số đo. Chạy <code>python3 ai_sale.py du_bao usa</code> '
          'trước — lệnh đó chỉ đọc, không tốn tiền.</p>')
    A('</header>')

    re_nhat = None
    if db:
        m = db["model"]
        dang = cf["model"]
        khoa_dang = next((k for k in m if dang.startswith(k)), "kimi-k3")
        re_nhat = min(m, key=lambda k: m[k]["tran_thang"][1])
        td, tr = m[khoa_dang]["tran_thang"], m[re_nhat]["tran_thang"]
        sd = m[khoa_dang]["san_thang"]
        # Đủ ~10 ngày chạy đầy tải với model RẺ nhất, làm tròn 5$ — đủ để có số thật rồi quyết tiếp
        de_nghi = max(10, round(m[re_nhat]["tran_ngay"][1] * 10 / 5) * 5)
        tran_ngay_re = m[re_nhat]["tran_ngay"][1]

        A('<section class="ketluan">')
        A(f'<p class="hoi">Chạy đầy tải: khoảng '
          f'<b>{db["tran_ngay"]:,.0f} lượt gọi model mỗi ngày</b>. '
          f'Tiền tuỳ model, chênh nhau {m["claude-opus-5"]["tran_thang"][1]/max(tr[1],0.01):.1f} '
          f'lần giữa đắt nhất và rẻ nhất.</p>')
        A('<div class="doi">')
        A(f'<div class="o"><span class="nhan-o">Giữ nguyên {_kh(dang)}</span>'
          f'<span class="to so">{_kr(td[0], td[1])}</span>'
          f'<span class="ghi">mỗi tháng</span></div>')
        A(f'<div class="o"><span class="nhan-o">Đổi sang {_kh(re_nhat)}</span>'
          f'<span class="to xanh so">{_kr(tr[0], tr[1])}</span>'
          f'<span class="ghi">mỗi tháng — rẻ hơn {td[1]/max(tr[1],0.01):.1f} lần</span></div>')
        A(f'<div class="o"><span class="nhan-o">Nên nạp lần đầu</span>'
          f'<span class="to so">${de_nghi:,.0f}</span>'
          f'<span class="ghi">đủ ~10 ngày đầy tải với {_kh(re_nhat)}, '
          f'đặt trần ngày ${tran_ngay_re:,.0f}</span></div>')
        A('</div>')
        A('<p class="phu">Đây là <b>khoảng</b>, không phải con số chốt: máy không có bộ tách '
          'token của Kimi/Claude nên chỉ ước được từ số ký tự. Con số chính xác hiện ra ngay '
          'sau vòng chạy có tiền đầu tiên, ở <code>ai_sale.py bao_cao</code>.</p>')
        A('</section>')

    # ── Sàn / trần ────────────────────────────────────────────────────────
    if db:
        A('<section><h2>Vì sao có hai con số</h2><div class="kiem">')
        A(f'<div class="muc"><span class="dau ok">SÀN</span><span class="noi">'
          f'<b>{db["san_ngay"]:,.0f} lượt/ngày — {_kr(*m[khoa_dang]["san_thang"])} /tháng '
          f'với {_kh(dang)}</b>'
          f'<span class="phu">Chỉ những lượt AI buộc phải vào cuộc ngay lúc đo: Botcake im, '
          f'hoặc Botcake đã trả lời mà AI phải đọc lại xem có trúng câu khách hỏi không.</span>'
          f'</span></div>')
        A(f'<div class="muc"><span class="dau canh">TRẦN</span><span class="noi">'
          f'<b>{db["tran_ngay"]:,.0f} lượt/ngày — {_kr(*m[khoa_dang]["tran_thang"])} /tháng '
          f'với {_kh(dang)}</b>'
          f'<span class="phu">Cộng thêm {db["n_im"]:,} lượt mà hôm nay <b>sale thật đã trả lời '
          f'trước nên AI tránh ra</b>. Chạy thật thì AI chỉ đợi Botcake ~90 giây rồi nhắn, tức '
          f'nó vào <b>trước</b> sale — nên phần lớn số này sẽ thành lượt AI phải gọi model. '
          f'<b>Lấy cột trần mà quyết ngân sách.</b></span></span></div>')
        A('</div></section>')

    # ── Lưu lượng ─────────────────────────────────────────────────────────
    if db:
        A('<section><h2>Lưu lượng đo được</h2><div class="luoi">')
        for nhan_o, so, ghi in [
            ("Lượt khách / ngày", f'{db["quet_ngay"]:,.0f}',
             f'{db["quet"]:,} lượt trong {db["gio"]} giờ'),
            ("Page có khách nhắn", f'{d["so_page"]:,}',
             f'trên tổng {d["so_page_bat"]} page đang bật'),
            ("Sàn — gọi model / ngày", f'{db["san_ngay"]:,.0f}',
             f'{db["san"]/max(db["quet"],1)*100:.0f}% số lượt quét'),
            ("Trần — gọi model / ngày", f'{db["tran_ngay"]:,.0f}',
             f'{db["tran"]/max(db["quet"],1)*100:.0f}% số lượt quét'),
            ("Gói prompt / lượt", f'{db["ky_tu_goi"]:,.0f}',
             f'ký tự → ước {db["tok_vao"][0]:,.0f}–{db["tok_vao"][1]:,.0f} token'),
        ]:
            A(f'<div class="the"><span class="nhan-o">{_kh(nhan_o)}</span>'
              f'<span class="so-to so">{_kh(so)}</span>'
              f'<span class="ghi">{_kh(ghi)}</span></div>')
        A('</div>')
        A(f'<p class="phu" style="margin-top:10px">Trong {db["quet"]:,} lượt quét: '
          f'{d["cua"]["xet"]:,} lượt Botcake đã trả lời mà AI phải đọc lại · '
          f'{d["cua"]["tra_loi"]:,} lượt Botcake im · '
          f'{d["cua"]["im"]:,} lượt sale thật đã vào trước · '
          f'{d["cua"]["treo"]:,} lượt luật bắt treo cho sale.</p>')
        A('</section>')

    # ── So sánh model ─────────────────────────────────────────────────────
    if db:
        A('<section><h2>Chọn model — chênh nhau bao nhiêu tiền</h2><div class="cuon"><table>')
        A('<thead><tr><th>Model</th><th>Mỗi lượt</th><th>Sàn /tháng</th>'
          '<th>Trần /tháng</th><th>Trần nếu đệm chạy</th></tr></thead><tbody>')
        for ten, v in db["model"].items():
            lop = []
            chip = ""
            if cf["model"].startswith(ten):
                lop.append("chon")
                chip = '<span class="chip dang">đang dùng</span>'
            elif ten == re_nhat:
                lop.append("re")
                chip = '<span class="chip re">rẻ nhất</span>'
            A(f'<tr class="{" ".join(lop)}"><td>{_kh(ten)}{chip}</td>'
              f'<td class="so">${v["luot"][0]:.4f}–{v["luot"][1]:.4f}</td>'
              f'<td class="so">{_kr(*v["san_thang"])}</td>'
              f'<td class="so">{_kr(*v["tran_thang"])}</td>'
              f'<td class="so">{_kr(*v["tran_thang_dem"])}</td></tr>')
        A('</tbody></table></div>')
        A('<p class="phu" style="margin-top:10px">Cột cuối chỉ đúng khi bộ nhớ đệm thật sự '
          'chạy — Claude thì chắc chắn, Kimi <b>chưa đo được</b> vì tài liệu của họ không mở '
          'trường bật đệm ở endpoint này. Vòng chạy thật đầu tiên sẽ nói ngay: cột “đọc đệm” '
          'bằng 0 nghĩa là đệm không chạy và phải tính theo cột trần.</p>')
        A('</section>')

    # ── Top câu hỏi ───────────────────────────────────────────────────────
    if d["n_hoi_tat"]:
        A('<section><h2>Khách hỏi gì</h2>')
        A('<div class="thanhds">')
        top = d["hoi_tat"].most_common(8)
        lon = top[0][1] if top else 1
        for ten, n in top:
            A(f'<div class="dong"><div><div class="ten">{_kh(ten)}</div>'
              f'<div class="ray"><i style="width:{n/lon*100:.0f}%"></i></div></div>'
              f'<div class="pt so">{n/d["n_hoi_tat"]*100:.0f}%</div></div>')
        A('</div>')
        A(f'<p class="phu" style="margin-top:12px">Trên {d["n_hoi_tat"]:,} tin cuối của khách. '
          'Nhóm “nói tiếp giữa hội thoại” chiếm phần lớn — nghĩa là phần việc chính của AI '
          '<b>không</b> phải chào khách mới, mà là <b>nói tiếp một cuộc đã đang chạy</b>: '
          'nhớ khách đã cho gì, không hỏi lại, và chốt. Nhóm nào cao mà kịch bản '
          '“Trả lời nhanh” của page chưa có mẫu thì AI phải tự xoay — đó là chỗ đáng bổ sung '
          'trước khi cho chạy thật. Xếp nhóm bằng từ khoá đa ngữ nên là ước lượng.</p>')
        A('</section>')

    # ── Chi phí thật ──────────────────────────────────────────────────────
    A('<section><h2>Tiền thật đã tiêu</h2>')
    if d["co_chi_that"] or d["nap"]:
        A('<div class="luoi">')
        for nhan_o, so, ghi in [
            ("Đã nạp", f'${d["nap"]:,.2f}', f'nhà cung cấp {cf["nha"]}'),
            ("Đã chi (sổ)", f'${d["da_chi"]:,.4f}', 'sổ tự cộng — chỉ phần bản này ghi ra'),
            ("Còn lại THẬT",
             (f'${d["so_du"]["con"]:,.4f}' if d["so_du"].get("co")
              else f'${d["nap"]-d["da_chi"]:,.2f}'),
             ('hỏi thẳng API Kimi — số trên bảng của họ'
              + (f' · sổ đang đếm THIẾU ${d["nap"]-d["da_chi"]-d["so_du"]["con"]:,.4f}'
                 if d["so_du"].get("co") and d["nap"]
                 and d["nap"]-d["da_chi"]-d["so_du"]["con"] > 0.01 else '')
              if d["so_du"].get("co") else 'CHƯA hỏi được số dư thật — đây là số ước theo sổ nạp')),
            ("Hôm nay", f'${d["hom_nay"]:,.4f}',
             f'trần ngày {chi_phi.usd(cf["ns_ngay"])}' if cf["ns_ngay"] else 'chưa đặt trần'),
        ]:
            A(f'<div class="the"><span class="nhan-o">{_kh(nhan_o)}</span>'
              f'<span class="so-to so">{_kh(so)}</span>'
              f'<span class="ghi">{_kh(ghi)}</span></div>')
        A('</div>')
        if d["theo_page"]:
            A('<div class="cuon" style="margin-top:16px"><table>')
            A('<thead><tr><th>Page</th><th>Đã chi</th></tr></thead><tbody>')
            for ten, v in d["theo_page"]:
                A(f'<tr><td>{_kh(ten)}</td><td class="so">${v:,.4f}</td></tr>')
            A('</tbody></table></div>')
    else:
        A('<div class="trong">Chưa tiêu đồng nào — chưa có vòng <code>ai_sale.py chay</code> '
          'nào gọi model.<br>Sau vòng chạy thật đầu tiên, chỗ này hiện tiền theo ngày và '
          'theo từng page.</div>')
    A('</section>')

    # ── Form cấu hình (chỉ khi chạy máy chủ localhost) ────────────────────
    if sua_duoc:
        A(khoi_form(d, bao))
    else:
        A('<section><h2>Sửa cấu hình ngay trên màn hình</h2><div class="trong">'
          'Trang này chỉ đọc — trang đã publish không với tới được <code>.env</code> trên máy '
          'bạn.<br>Muốn sửa model, độ sáng tạo, trần chi, dán key, khai tiền nạp và đo lại '
          '<b>trong một màn</b>, mở bản chạy tại máy:<br><br>'
          '<code>python3 ai_sale.py dashboard usa --phuc-vu</code><br><br>'
          'Máy chủ chỉ nghe ở 127.0.0.1. Trên VPS thì mở đường hầm: '
          '<code>ssh -L 8765:127.0.0.1:8765 root@&lt;IP&gt;</code>'
          '</div></section>')

    # ── Việc phải làm ─────────────────────────────────────────────────────
    A('<section><h2>Trước khi nạp tiền — kiểm lại 4 việc</h2><div class="kiem">')
    viec = []
    viec.append(("ok" if cf["co_key"] else "nang",
                 "CÓ KEY" if cf["co_key"] else "THIẾU",
                 f'API key của {cf["nha"]}',
                 "Đã dán trong .env." if cf["co_key"] else
                 "Chưa dán <code>KIMI_API_KEY</code> trong <code>.env</code> — "
                 "hiện AI không soạn được câu nào."))
    nd = cf["nhiet_do"]
    viec.append(("ok" if nd is not None and nd <= 0.5 else "canh",
                 f"{nd}" if nd is not None else "MẶC ĐỊNH",
                 "Độ sáng tạo (temperature)",
                 f"Đang để {nd} — bám kịch bản, câu chữ ổn định." if nd is not None and nd <= 0.5
                 else "Đang chạy mặc định 1.0, bay nhất. Việc của AI Sale là bám kịch bản và "
                      "không bịa số — nên đặt <code>AI_TEMPERATURE=0.3</code> trong "
                      "<code>.env</code>."))
    viec.append(("ok" if cf["ns_ngay"] or cf["ns_tong"] else "nang",
                 chi_phi.usd(cf["ns_ngay"]) if cf["ns_ngay"] else "KHÔNG CÓ",
                 "Trần chi mỗi ngày",
                 "Vượt trần là vòng chạy tự dừng, hội thoại chưa xử để vòng sau quét lại."
                 if cf["ns_ngay"] or cf["ns_tong"] else
                 "Chưa có gì chặn nếu tiền chạy quá tay. Với số đo ở trên, đặt "
                 "<code>AI_NGAN_SACH_NGAY</code> bằng mức trần/ngày của model bạn chọn."))
    viec.append(("canh", "NHỚ KỸ", "Sửa cách AI trả lời ở đâu",
                 f'Model chỉ đọc biến <code>LUAT</code> trong <code>ai_sale.py</code> '
                 f'({cf["luat_ky_tu"]:,} ký tự) cộng với kịch bản “Trả lời nhanh” của từng page '
                 f'trên Pancake. File <code>LUAT_AI_SALE.md</code> là sổ luật cho người đọc — '
                 f'sửa mình nó thì AI <b>không</b> đổi hành vi.'))
    for mau, nhan_o, tieu, mo in viec:
        A(f'<div class="muc"><span class="dau {mau}">{_kh(nhan_o)}</span>'
          f'<span class="noi"><b>{_kh(tieu)}</b><span class="phu">{mo}</span></span></div>')
    A('</div></section>')

    A('<footer>')
    A('<div>Số liệu đọc từ <code>state/&lt;thị trường&gt;/du_bao.jsonl</code> và '
      '<code>state/&lt;thị trường&gt;/so_chi_phi.jsonl</code>. Dựng lại trang: '
      '<code>python3 ai_sale.py dashboard</code>.</div>')
    A(f'<div>Cập nhật {_kh(d["luc"])}.</div>')
    A('</footer>')
    A('</div>')
    return "\n".join(r)


TIEU_DE = "Bảng Chi Phí AI Sale"


def dung(mkey=None, ra=None, than_file=None, mo=True):
    d = thu_thap(mkey)
    noi = than(d, sua_duoc=False)
    if than_file:
        with open(than_file, "w", encoding="utf-8") as f:
            f.write(f"<title>{TIEU_DE}</title>\n{noi}\n")
        print(f"  ✅ Bản cho Artifact: {than_file}")
    ra = ra or os.path.join(SCRIPT_DIR, "bang_dieu_khien.html")
    with open(ra, "w", encoding="utf-8") as f:
        f.write('<!doctype html>\n<html lang="vi"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{TIEU_DE}</title></head><body>\n{noi}\n</body></html>\n')
    print(f"  ✅ Đã dựng: {ra}")
    if mo:
        try:
            webbrowser.open("file://" + ra)
        except Exception:
            pass
    return ra


# Bản SỬA ĐƯỢC nằm ở giao_dien.py (API JSON + trang ứng dụng). File này chỉ lo bản TĨNH:
# báo cáo chỉ đọc, gửi cho người khác xem hoặc publish được.

def phuc_vu(mkey=None, cong=8765, mo=True):
    import giao_dien
    giao_dien.chay(mkey, cong, mo)


if __name__ == "__main__":
    a = sys.argv[1:]
    mk = a[0] if a and not a[0].startswith("--") else None
    if "--phuc-vu" in a or "--sua" in a:
        phuc_vu(mk, cong=int(a[a.index("--cong") + 1]) if "--cong" in a else 8765,
                mo=("--khong-mo" not in a))
    else:
        dung(mk, than_file=(a[a.index("--than") + 1] if "--than" in a else None),
             mo=("--khong-mo" not in a))

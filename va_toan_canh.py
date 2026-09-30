#!/usr/bin/env python3
"""Vá tab "Toàn cảnh" vào giao_dien.py. Mỗi chỗ phải khớp đúng 1 lần, không thì thoát không ghi."""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "veToan" in s:
    sys.exit("đã có tab Toàn cảnh — không vá lại")


def thay(cu, moi):
    global s
    n = s.count(cu)
    if n != 1:
        sys.exit(f"KHÔNG VÁ: chuỗi khớp {n} lần:\n{cu[:120]}")
    s = s.replace(cu, moi)


# 1. Tab mới đứng đầu, mở trang là vào thẳng
thay("let S = null, TAB = 'tong', BAN = false, TIMER = null;",
     "let S = null, TAB = 'toan', BAN = false, TIMER = null, TC_GIO = 24, TC_HEN = null;")
thay("const TABS = [['tong','Tổng quan'],",
     "const TABS = [['toan','Toàn cảnh các nước'],['tong','Tổng quan'],")
thay("  $('#main').classList.toggle('rong', TAB === 'tong');",
     "  $('#main').classList.toggle('rong', TAB === 'tong' || TAB === 'toan');\n  $('#main').classList.toggle('toan', TAB === 'toan');")
thay("  $('#main').innerHTML = ({tong:veTong,",
     "  $('#main').innerHTML = ({toan:veToan, tong:veTong,")
thay("  ({cauhinh:sauCauHinh,",
     "  ({toan:sauToan, cauhinh:sauCauHinh,")

# 2. CSS
thay("/* Thanh câu hỏi */",
     r"""/* Toàn cảnh các nước — main.toan co lại được, bảng rộng cuộn trong khung chứ không đẩy cả trang */
main.toan{min-width:0}
main.toan .luoi{grid-template-columns:repeat(auto-fit,minmax(138px,1fr))}
main.toan td .ghi{white-space:nowrap}
main.toan th,main.toan td{padding-left:8px;padding-right:8px}
.hai-dong{display:block;font-size:11.5px;color:var(--nhat);font-weight:400}
.tc-dong{cursor:pointer}
.tc-dong:hover td{background:var(--nhan-mo)}
.den{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;vertical-align:1px}
.den.chay{background:var(--nhan)}.den.tat{background:var(--nang)}.den.cham{background:var(--canh)}
.kc{display:flex;gap:2px;height:10px;width:120px;min-width:120px}
.kc i{display:block;height:100%;border-radius:2px;min-width:2px}
.kc .g{background:var(--nhan)}.kc .n{background:var(--canh)}.kc .t{background:var(--nhat)}.kc .c{background:var(--nang)}
.chu-giai{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--nhat);margin-top:9px}
.chu-giai span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;
  margin-right:6px;vertical-align:-1px;background:var(--mau)}
.sparks{display:block;width:120px;height:18px;margin-top:5px}
.sparks rect{fill:var(--nhan)}
tr.tong td{font-weight:700;background:var(--nen)}
.hai-cot{display:grid;grid-template-columns:repeat(auto-fit,minmax(580px,1fr));gap:22px}
.feed{display:flex;flex-direction:column;gap:0;border:1px solid var(--vien);border-radius:4px;
  background:var(--mat);max-height:620px;overflow:auto}
.feed div.m{display:grid;grid-template-columns:48px 112px 1fr;gap:10px;padding:9px 13px;
  border-bottom:1px solid var(--vien);font-size:13px}
.feed div.m:last-child{border-bottom:none}
.feed .ai{color:var(--nhat);font-size:12px}
.feed .cau{color:var(--muc);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nhan-kc{font-size:10.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
  padding:1px 6px;border-radius:3px;white-space:nowrap}
.nhan-kc.gui{background:var(--nhan-mo);color:var(--nhan)}
.nhan-kc.ghi_chu,.nhan-kc.gui_hong{background:var(--canh-mo);color:var(--canh)}
.nhan-kc.treo{background:var(--nen);color:var(--nhat);box-shadow:inset 0 0 0 1px var(--vien)}
.nhan-kc.chan{background:var(--nang-mo);color:var(--nang)}
.canh-ds{display:flex;flex-direction:column;gap:6px}

/* Thanh câu hỏi */""")

# 3. JS màn Toàn cảnh
thay("/* ═══════════════════════════════════════════════════════════════════════\n   MÀN: PAGE & KỊCH BẢN",
     r"""/* ═══════════════════════════════════════════════════════════════════════
   MÀN: TOÀN CẢNH CÁC NƯỚC  (chủ shop 14/09: "đừng bắt tôi ấn từng nước")
   Một bảng mọi thị trường + việc cần người + việc AI vừa làm. Số đọc từ sổ trên
   đĩa (toan_canh.py), không gọi model. Bấm một nước để vào báo cáo riêng nước đó.
   ═══════════════════════════════════════════════════════════════════════ */
const KC_TEN = {gui:'tới khách', ghi_chu:'vào ghi chú', gui_hong:'gửi hỏng', treo:'treo cho sale', chan:'cổng chặn giữ', khac:'khác'};
function veToan(){
  return `<div id="tc"><p class="phu"><span class="quay"></span>Đang gộp sổ của mọi nước…</p></div>`;
}
function gioChu(g){ return g < 48 ? g + ' giờ' : Math.round(g/24) + ' ngày'; }
function tuoi(giay){
  if(giay == null) return '';
  return giay < 90 ? giay + ' giây trước' : giay < 5400 ? Math.round(giay/60) + ' phút trước' : Math.round(giay/3600) + ' giờ trước';
}
function thanhKc(x){
  const t = x.gui + x.ghi_chu + x.treo + x.chan;
  if(!t) return '<span class="ghi">—</span>';
  const o = (k, c, v) => v ? `<i class="${c}" style="flex:${v}" title="${v} ${KC_TEN[k]} (${pct(v,t)})"></i>` : '';
  return `<div class="kc">${o('gui','g',x.gui)}${o('ghi_chu','n',x.ghi_chu)}${o('treo','t',x.treo)}${o('chan','c',x.chan)}</div>`;
}
function sparks(ds){
  const n = ds.length, mx = Math.max(1, ...ds);
  const dinh = ds.indexOf(Math.max(...ds));
  return `<svg class="sparks" viewBox="0 0 ${n} 24" preserveAspectRatio="none" role="img">
    <title>Tin tới khách theo giờ — cao nhất ${mx} tin (${n - dinh} giờ trước)</title>
    ${ds.map((v,i) => v ? `<rect x="${i+0.12}" width="0.76" y="${24 - Math.max(2, v/mx*24)}" height="${Math.max(2, v/mx*24)}"/>` : '').join('')}</svg>`;
}
async function sauToan(){
  clearTimeout(TC_HEN);
  let k;
  try{ k = await api('toan-canh?gio=' + TC_GIO); }
  catch(e){ if($('#tc')) $('#tc').innerHTML = `<div class="xau">Không gộp được số: ${H(e.message)}</div>`; return; }
  if(TAB !== 'toan' || !$('#tc')) return;
  const t = k.tong, sd = k.kimi.so_du || {};
  const chay = k.nuoc.filter(x => x.co_chay), nghi = k.nuoc.filter(x => !x.co_chay);
  const the = (a,b,c,mau) => `<div class="the"><span class="nhan-o">${a}</span>
    <span class="so-to so"${mau ? ` style="color:var(--${mau})"` : ''}>${b}</span><span class="ghi">${c}</span></div>`;
  const nang = k.canh.filter(c => c[0] === 'nang'), nhe = k.canh.filter(c => c[0] !== 'nang');
  const dongNuoc = x => {
    const s = x.service || {}, pg = x.page || {};
    const den = s.chay === false ? 'tat' : (s.log_giay > 600 || s.loi_gan) ? 'cham' : 'chay';
    const ttSvc = s.chay === false ? 'service TẮT'
      : s.chay == null ? 'không rõ service' : `${s.luot_do != null ? s.luot_do + 's/lượt dò · ' : ''}log ${tuoi(s.log_giay)}`;
    return `<tr class="tc-dong" data-tt="${H(x.tt)}">
      <td class="trai"><span class="den ${den}"></span><b>${H(x.ten)}</b>
        <div class="ghi" style="font-size:11.5px;padding-left:15px">${H(ttSvc)}${s.loi_gan ? ` · <b style="color:var(--nang)">${s.loi_gan} lượt lỗi</b>` : ''}</div></td>
      <td class="so">${x.page_co_khach}<span class="ghi"> / ${pg.shop != null ? pg.shop : (pg.token || '?')}</span></td>
      <td class="so"><b>${n0(x.hoi_thoai)}</b></td>
      <td class="so" style="color:var(--nhan);font-weight:700">${x.gui}</td>
      <td class="so">${x.ghi_chu || '–'}</td>
      <td class="so">${x.treo || '–'}</td>
      <td class="so"${x.chan ? ' style="color:var(--nang)"' : ''}>${x.chan || '–'}</td>
      <td class="so"><b>${x.don || '–'}</b></td>
      <td class="so">${usd2(x.tien)}<span class="hai-dong">${x.tien_moi_tin != null ? vnd(x.tien_moi_tin * 26300) + '/tin' : ''}</span></td>
      <td class="so">${x.fb_chan ? `<span style="color:var(--canh);font-weight:700">${x.fb_chan} FB chặn</span>` : '–'}
        ${x.token_hong ? `<span class="hai-dong">${x.token_hong} token hỏng</span>` : ''}</td>
      <td title="tới khách theo giờ">${thanhKc(x)}${sparks(x.theo_gio)}</td></tr>`;
  };
  const bangPage = (ds, cot) => `<div class="cuon"><table><thead><tr><th class="trai">Page</th><th class="trai">Nước</th>
      ${cot.map(c => `<th>${c[0]}</th>`).join('')}</tr></thead><tbody>
      ${ds.map(p => `<tr><td class="trai" style="white-space:normal">${H(p.ten)}${p.fb_chan ? ' <span class="chip" style="background:var(--canh-mo);color:var(--canh)">FB chặn</span>' : ''}</td>
        <td class="trai">${H((k.nuoc.find(x => x.tt === p.tt) || {}).ten || p.tt)}</td>
        ${cot.map(c => `<td class="so">${c[1](p)}</td>`).join('')}</tr>`).join('')
        || `<tr><td colspan="${cot.length + 2}" class="trai phu">Không có.</td></tr>`}</tbody></table></div>`;

  $('#tc').innerHTML = `
  <div class="dau-trang"><h1>Toàn cảnh ${chay.length} nước đang chạy AI</h1>
    <p class="phu">${gioChu(k.gio)} gần nhất, tới ${H(k.luc)} (giờ máy chủ) · tự làm mới mỗi 60 giây ·
      bấm tên một nước để xem báo cáo riêng nước đó.</p>
    <div class="loc" style="margin:8px 0 0">${[6,24,72,168].map(g =>
      `<button data-g="${g}"${TC_GIO===g?' aria-pressed="true"':''}>${gioChu(g)}</button>`).join('')}
      <button id="tc_lai" style="margin-left:auto">Làm mới</button></div></div>

  <section><div class="luoi">
    ${the('Hội thoại AI xét', n0(t.hoi_thoai), `${n0(t.page_co_khach)} page có khách · gọi model ${n0(t.goi)} lần`)}
    ${the('Tin tới tay khách', n0(t.gui), `${pct(t.gui, t.gui + t.ghi_chu + t.treo + t.chan)} việc AI làm`, 'nhan')}
    ${the('Vào ghi chú', n0(t.ghi_chu), `page bị FB chặn — sale gửi tay`, t.ghi_chu ? 'canh' : '')}
    ${the('Treo cho sale', n0(t.treo), 'AI không tự lo được, đã đánh chưa đọc')}
    ${the('Cổng chặn giữ', n0(t.chan), 'câu sai luật, khách chưa được trả lời', t.chan ? 'nang' : '')}
    ${the('Đơn tool lên từ chat', n0(t.don), `${t.chot} lượt AI chốt đơn`)}
    ${the('Tiền model (tool tính)', usd2(t.tien), t.tien_moi_tin ? vnd(t.tien_moi_tin*26300) + '/tin tới khách' : '')}
    ${sd.co ? the('Kimi còn', usd2(sd.con), `nạp ${usd2(k.kimi.nap)} · đã trừ thật ${usd2(k.kimi.nap - sd.con)}`, sd.con < 3 ? 'nang' : 'nhan')
            : the('Kimi còn', '?', H(sd.loi || 'không hỏi được số dư'))}
  </div></section>

  ${k.canh.length ? `<section><h2>Cần để ý</h2><div class="canh-ds">
    ${nang.map(c => `<div class="xau">${H(c[1])}</div>`).join('')}
    ${nhe.length ? `<div class="canh-bao" style="font-weight:500"><ul style="margin:0;padding-left:18px">
      ${nhe.map(c => `<li>${H(c[1])}</li>`).join('')}</ul></div>` : ''}
  </div></section>` : `<section><div class="tot">Mọi service đang chạy, không lỗi trong 20 lượt dò gần nhất.</div></section>`}

  <section><h2>Từng nước</h2>
    <div class="cuon"><table>
      <thead><tr><th class="trai">Nước</th><th title="page có khách / page có token thuộc shop">Page</th><th>Hội thoại</th><th>Tới khách</th>
        <th>Ghi chú</th><th>Treo</th><th>Chặn</th><th>Đơn</th><th>Tiền</th>
        <th>Page lỗi</th><th class="trai">Kết cục · tới khách theo giờ</th></tr></thead>
      <tbody>${chay.map(dongNuoc).join('')}
        <tr class="tong"><td class="trai">TỔNG ${chay.length} nước</td><td class="so">${t.page_co_khach}</td>
          <td class="so">${n0(t.hoi_thoai)}</td><td class="so">${t.gui}</td><td class="so">${t.ghi_chu}</td>
          <td class="so">${t.treo}</td><td class="so">${t.chan}</td><td class="so">${t.don}</td>
          <td class="so">${usd2(t.tien)}<span class="hai-dong">${t.tien_moi_tin != null ? vnd(t.tien_moi_tin*26300) + '/tin' : ''}</span></td>
          <td class="so">${t.fb_chan} FB chặn<span class="hai-dong">${chay.reduce((a,x) => a + x.token_hong, 0)} token hỏng</span></td>
          <td>${thanhKc(t)}</td></tr>
      </tbody></table></div>
    <div class="chu-giai"><span style="--mau:var(--nhan)">tới khách</span><span style="--mau:var(--canh)">vào ghi chú (FB chặn)</span>
      <span style="--mau:var(--nhat)">treo cho sale</span><span style="--mau:var(--nang)">cổng chặn giữ</span></div>
    <p class="phu" style="margin-top:8px">“Hội thoại” = số hội thoại có khách nhắn mà AI đã xét (gồm cả lượt AI cố ý im vì Botcake/sale đã rep).
      “Đơn” = đơn tool tự lên từ chat (cả chat AI lẫn chat sale). “Tiền” = tool đếm token × giá niêm yết, cao hơn Kimi trừ thật khoảng 4 lần —
      dùng để so các nước với nhau. Số đ/tin dưới cột tiền = tiền chia số tin tới khách, tỉ giá 26.300đ. “Page” = page có khách / page có token thuộc shop.
      ${nghi.length ? `<br>Chưa chạy AI: ${nghi.map(x => H(x.ten)).join(', ')} — không có page dùng được.` : ''}</p>
  </section>

  <section class="hai-cot">
    <div><h2>Page cần người vào</h2>
      ${bangPage(k.can_nguoi, [['Ghi chú', p => p.ghi_chu || '–'], ['Treo', p => p.treo || '–'], ['Chặn', p => p.chan || '–'], ['Hội thoại', p => p.hoi_thoai]])}
      <p class="phu" style="margin-top:8px">Page dồn nhiều ca AI không tự xong: câu nằm trong ghi chú chờ sale gửi tay, ca treo, câu bị cổng chặn giữ.</p></div>
    <div><h2>Page đông khách nhất</h2>
      ${bangPage(k.dong_khach, [['Hội thoại', p => p.hoi_thoai], ['Tới khách', p => p.gui || '–'], ['Gọi model', p => p.goi], ['Tiền', p => usd2(p.tien)]])}</div>
  </section>

  <section><h2>AI vừa làm gì — mọi nước</h2>
    <div class="feed">${k.gan_day.map(r => `<div class="m">
      <span class="ai so">${new Date(r.luc*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'})}</span>
      <span><span class="nhan-kc ${r.kc}">${H(KC_TEN[r.kc] || r.kc)}</span></span>
      <div style="min-width:0"><div><b>${H((k.nuoc.find(x => x.tt === r.tt) || {}).ten || r.tt)}</b> · ${H(r.page)} · ${H(r.khach || 'khách')}
        ${(r.ma||[]).length ? (r.ma).map(m => `<code>${H(m)}</code>`).join(' ') : ''}</div>
        <div class="cau" title="${H(r.tin)}">${H(r.tin) || '<span class="ghi">—</span>'}</div></div></div>`).join('')
      || '<div class="trong">Chưa có việc nào trong khoảng này.</div>'}</div>
    <p class="phu" style="margin-top:8px">Giờ theo múi giờ máy đang mở trang.</p></section>`;

  $('#tc').querySelectorAll('.loc button[data-g]').forEach(b =>
    b.onclick = () => { TC_GIO = +b.dataset.g; $('#tc').insertAdjacentHTML('afterbegin', '<p class="phu"><span class="quay"></span>Đang gộp…</p>'); sauToan(); });
  $('#tc_lai').onclick = () => sauToan();
  $('#tc').querySelectorAll('tr.tc-dong').forEach(r => r.onclick = async () => {
    TT = r.dataset.tt; PAGE = null; PCHON = null; LOC = -1; CHAN = null; CHO = null;
    TAB = 'tong'; bao('Đang mở ' + r.querySelector('b').textContent + '…'); await tai();
  });
  TC_HEN = setTimeout(() => { if(TAB === 'toan' && !document.hidden) sauToan(); }, 60000);
}

/* ═══════════════════════════════════════════════════════════════════════
   MÀN: PAGE & KỊCH BẢN""")

# 4. API
thay('''            if self.path == "/api/do":
                return self._js(DO)''',
     '''            if self.path.split("?")[0] == "/api/toan-canh":
                import toan_canh
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    return self._js(toan_canh.toan_canh(int((q.get("gio") or ["24"])[0] or 24)))
                except Exception as ex:                # noqa: BLE001
                    return self._js({"loi": str(ex)}, 500)
            if self.path == "/api/do":
                return self._js(DO)''')

open(p, "w", encoding="utf-8").write(s)
print("đã vá", p)

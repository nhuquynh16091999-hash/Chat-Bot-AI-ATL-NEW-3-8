// NGHE NHÓM WHATSAPP + CỔNG GỬI TIN — một kết nối WhatsApp thường trực cho máy báo giờ làm (chủ shop 24/09/2026).
//
//   node /opt/pancake-tool/wa_nghe.mjs          (chạy bằng systemd: gio-lam-wa.service)
//
// Vì sao:
//   · Chủ shop 24/09: vận đơn làm nhiều việc ngoài POS (nhắn nhóm hãng ship Imile, VẬN ĐƠN - SALE…) → tin họ nhắn trong
//     NHÓM WhatsApp cũng tính là hoạt động. Ghi mỗi tin nhóm 1 dòng {giờ, nhóm, người gửi} vào
//     /opt/pancake-tool/state/gio_lam/wa-<ngày VN>.jsonl — KHÔNG lưu nội dung, KHÔNG đọc chat riêng, KHÔNG gửi "đã xem".
//   · WhatsApp chỉ cho MỘT kết nối mỗi thiết bị liên kết: kết nối thứ hai (gui-canh-bao.js tự mở mỗi lần gửi) đá văng
//     kết nối đang nghe (mã 440). Nên tiến trình này giữ luôn việc GỬI: POST http://127.0.0.1:8797/gui {jid, text};
//     gui-canh-bao.js gọi cổng này trước, cổng chết mới tự mở kết nối như cũ.
import makeWASocket, { useMultiFileAuthState, Browsers, generateMessageIDV2 } from '/opt/aicloser/node_modules/@whiskeysockets/baileys/lib/index.js';
import pino from '/opt/aicloser/node_modules/pino/pino.js';
import fs from 'node:fs';
import http from 'node:http';

const AUTH = '/opt/aicloser/wa-auth';
const STATE = '/opt/pancake-tool/state/gio_lam';
const PORT = 8797;   // 8765 là của giao_dien.py (bảng điều khiển UAE) — đừng đổi về
const logger = pino({ level: 'silent' });
let sock = null;
let sanSang = false;
let lanMo = 0;
// 24/09 22:00: tin báo cáo/nhắc do MÁY gửi đi bằng số phụ (của Linh vận đơn) bị ghi là "Linh đang hoạt động" (minh=true) → Linh
// bị nhận nhầm là làm ca tối. Tự đặt mã tin trước khi gửi, nhớ lại, gặp lại trong messages.upsert thì bỏ qua.
const mayGui = new Map();

const gioVN = () => new Date(Date.now() + 7 * 3600e3).toISOString().replace('T', ' ').slice(0, 19);
const log = (...a) => console.log(`[${gioVN()} VN]`, ...a);
const ngayVN = (t) => new Date(t * 1000 + 7 * 3600e3).toISOString().slice(0, 10);
const soGiay = (ts) => {
  if (ts == null) return Math.floor(Date.now() / 1000);
  if (typeof ts === 'object') return typeof ts.toNumber === 'function' ? ts.toNumber() : Number(ts.low);
  return Number(ts);
};

fs.mkdirSync(STATE, { recursive: true });

function ghi(rec) {
  try { fs.appendFileSync(`${STATE}/wa-${ngayVN(rec.t)}.jsonl`, JSON.stringify(rec) + '\n'); } catch (e) { log('ghi sổ lỗi', e.message); }
}

async function mo() {
  lanMo += 1;
  const { state, saveCreds } = await useMultiFileAuthState(AUTH);
  sock = makeWASocket({
    auth: state,
    logger,
    browser: Browsers.ubuntu('Chrome'),        // phải trùng ghep.mjs / wa.js, không thì bị coi là thiết bị khác
    syncFullHistory: false,
    markOnlineOnConnect: false,                // không chiếm trạng thái "online" của chủ số
    shouldSyncHistoryMessage: () => false,
  });
  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('connection.update', async (u) => {
    if (u.connection === 'open') {
      sanSang = true;
      log(`đã kết nối (lần ${lanMo})`);
      try {
        const g = await sock.groupFetchAllParticipating();
        fs.writeFileSync(`${STATE}/wa_nhom.json`, JSON.stringify(Object.fromEntries(Object.values(g).map((x) => [x.id, x.subject])), null, 1));
      } catch (e) { log('lấy tên nhóm lỗi', e.message); }
    }
    if (u.connection === 'close') {
      sanSang = false;
      const code = u.lastDisconnect?.error?.output?.statusCode;
      log(`mất kết nối, mã ${code ?? '?'} ${u.lastDisconnect?.error?.message || ''}`);
      if (code === 401 || code === 403) {                // bị đăng xuất khỏi điện thoại → phải ghép lại, đừng thử vô ích
        log('⛔ phiên WhatsApp bị đăng xuất — ghép lại: ssh -t root@169.58.33.8 \'bash /root/wa_ghep/ghep.sh --qr\'');
        process.exit(3);
      }
      setTimeout(() => mo().catch((e) => { log('mở lại lỗi', e.message); process.exit(1); }), code === 440 ? 30000 : 5000);
    }
  });
  sock.ev.on('messages.upsert', ({ messages, type }) => {
    for (const m of messages || []) {
      const k = m.key || {};
      if (!k.remoteJid || !k.remoteJid.endsWith('@g.us')) continue;     // chỉ tin NHÓM
      if (m.messageStubType) continue;                                  // bỏ tin hệ thống (vào/rời nhóm…)
      if (k.fromMe && mayGui.has(k.id)) continue;                       // tin MÁY gửi, không phải chủ số
      // 25/09: LỆNH trong nhóm ("#doica Trúc đêm", "#off Thu Hiền") — CHỈ tin bắt đầu bằng "#" mới lưu chữ, tin khác vẫn không
      const chu = String(m.message?.conversation || m.message?.extendedTextMessage?.text || '').trim();
      if (chu.startsWith('#')) {
        try {
          fs.appendFileSync(`${STATE}/lenh.jsonl`, JSON.stringify({ t: soGiay(m.messageTimestamp), id: k.id, nhom: k.remoteJid,
            ai: k.participant || null, ai2: k.participantAlt || k.participantPn || null, minh: !!k.fromMe, chu: chu.slice(0, 300) }) + '\n');
        } catch (e) { log('ghi lệnh lỗi', e.message); }
      }
      ghi({
        t: soGiay(m.messageTimestamp),
        id: k.id,
        nhom: k.remoteJid,
        ai: k.participant || null,
        ai2: k.participantAlt || k.participantPn || null,
        ten: m.pushName || null,
        minh: !!k.fromMe,
        kieu: type,
      });
    }
  });
}

http.createServer((req, res) => {
  const tra = (ma, obj) => { res.writeHead(ma, { 'content-type': 'application/json' }); res.end(JSON.stringify(obj)); };
  if (req.method === 'GET' && req.url === '/tinh-trang') return tra(200, { san_sang: sanSang, lan_mo: lanMo });
  if (req.method !== 'POST' || req.url !== '/gui') return tra(404, { ok: false, error: 'không có' });
  let body = '';
  req.on('data', (c) => { body += c; if (body.length > 1e6) req.destroy(); });
  req.on('end', async () => {
    let d;
    try { d = JSON.parse(body || '{}'); } catch { return tra(400, { ok: false, error: 'JSON hỏng' }); }
    if (!d.jid || !String(d.text || '').trim()) return tra(400, { ok: false, error: 'thiếu jid/text' });
    for (let i = 0; i < 40 && !sanSang; i += 1) await new Promise((r) => setTimeout(r, 500));   // đợi tối đa 20s nếu đang nối lại
    if (!sanSang) return tra(503, { ok: false, error: 'WhatsApp chưa kết nối', cong_song: true });
    try {
      const id = generateMessageIDV2(sock.user?.id);
      mayGui.set(id, Date.now());
      for (const [x, t] of mayGui) if (Date.now() - t > 6 * 3600e3) mayGui.delete(x);
      await sock.sendMessage(d.jid, { text: String(d.text) }, { messageId: id });
      log('đã gửi →', d.jid);
      return tra(200, { ok: true });
    } catch (e) {
      log('gửi lỗi', e.message);
      return tra(500, { ok: false, error: e.message, cong_song: true });
    }
  });
}).listen(PORT, '127.0.0.1', () => log(`cổng gửi 127.0.0.1:${PORT}`));

mo().catch((e) => { log('mở lỗi', e.message); process.exit(1); });

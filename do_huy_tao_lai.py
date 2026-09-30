"""ĐO (chỉ đọc): tool tạo đơn nháp SAU KHI sale đã hủy đơn của cùng thương vụ bao nhiêu lần?

Cùng thương vụ = cùng conversation_id, hoặc cùng SĐT trên cùng page.
In từng ca: đơn mới giờ ra sao (sale hủy tiếp = tạo oan; đi tiếp = mua lại thật),
và khách có gõ SĐT/địa chỉ nào SAU lúc hủy không (đọc tin nhắn nếu page có token).
"""
import sys, os, time, json, datetime, re
from collections import defaultdict
sys.path.insert(0, "/opt/pancake-tool")
os.chdir("/opt/pancake-tool")
import auto_len_don as D
import quet_hoi_thoai as Q

NGAY = int(sys.argv[1]) if len(sys.argv) > 1 else 7
THI_TRUONG = sys.argv[2].split(",") if len(sys.argv) > 2 else [
    "uae", "saudi", "kuwait", "qatar", "oman", "bahrain", "taiwan", "usa"]
DOC_TIN = "--tin" in sys.argv


def ts(s):
    s = (s or "").split(".")[0].replace("Z", "")
    try:
        return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp())
    except ValueError:
        return 0


def luc_huy(o):
    """(epoch, người hủy) của lần chuyển 6/7 gần nhất."""
    best = (0, None)
    for h in o.get("status_history") or []:
        if h.get("status") in (6, 7):
            t = ts(h.get("updated_at"))
            if t > best[0]:
                best = (t, h.get("name") or "tool/?")
    return best


def so9(x):
    d = re.sub(r"\D", "", str(x or ""))
    return d[-9:] if len(d) >= 8 else ""


def gio(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=7))).strftime("%d/%m %H:%M")


tong = defaultdict(lambda: defaultdict(int))
for mk in THI_TRUONG:
    D.set_market(mk)
    now = int(time.time())
    orders, pg = [], 1
    while True:
        d = D.P.fetch_orders({"startDateTime": now - (NGAY + 3) * 86400, "endDateTime": now,
                              "page_size": 100, "page_number": pg})
        orders += d
        if len(d) < 100 or pg > 80:
            break
        pg += 1
    theo_conv, theo_sdt = defaultdict(list), defaultdict(list)
    for o in orders:
        pid = str(o.get("page_id") or "") or D._page_tu_ma_khach(o)
        if o.get("conversation_id"):
            theo_conv[str(o["conversation_id"])].append(o)
        if so9(o.get("bill_phone_number")) and pid:
            theo_sdt[(pid, so9(o.get("bill_phone_number")))].append(o)
    tokens = Q.load_json(Q.TOKENS_FILE, {}) if DOC_TIN else {}
    for o in orders:
        if not D.la_don_nhap_cua_tool(o):
            continue
        # sale bấm "sao chép đơn" thì note [Tự động] đi theo — người tạo thật nằm ở status_history[0]
        h0 = (o.get("status_history") or [{}])[0]
        if h0.get("name"):
            tong[mk]["ban_sao_cua_sale"] += 1
            continue
        t_moi = ts(o.get("inserted_at"))
        if t_moi < now - NGAY * 86400:
            continue
        tong[mk]["nhap_tool"] += 1
        pid = str(o.get("page_id") or "") or D._page_tu_ma_khach(o)
        conv = str(o.get("conversation_id") or "")
        cand = {c["id"]: c for c in theo_conv.get(conv, []) + theo_sdt.get((pid, so9(o.get("bill_phone_number"))), [])
                if c["id"] != o["id"]}
        huy = []
        for c in cand.values():
            if c.get("status") in (6, 7) and ts(c.get("inserted_at")) < t_moi:
                t_h, ai = luc_huy(c)
                if t_h and t_h < t_moi:
                    huy.append((t_h, ai, c))
        if not huy:
            continue
        t_h, ai, c = max(huy, key=lambda x: x[0])
        tong[mk]["sau_huy"] += 1
        st = o.get("status")
        tong[mk][f"st_{st}"] += 1
        dong = (f"{mk:7} #{o['id']} st={st:<2} tạo {gio(t_moi)} · #{c['id']} hủy {gio(t_h)} bởi {ai}"
                f" (cách {(t_moi - t_h) // 60} phút) · {(o.get('bill_full_name') or '')[:20]}")
        print(dong)
        if DOC_TIN and conv and tokens.get(pid, {}).get("token"):
            rec = Q.extract_conversation(pid, "", tokens[pid]["token"], {"id": conv})
            sau = [m for m in rec.get("tin_nhan") or []
                   if m["ai"] == "khach" and t_h < ts(m.get("luc")) <= t_moi + 60]
            print(f"        (tin khách: {len(rec.get('tin_nhan') or [])} tin, cuối lúc {(rec.get('tin_nhan') or [{}])[-1].get('luc')})")
            for m in sau[-6:]:
                print(f"        khách {gio(ts(m['luc']))}: {m['noi_dung'][:90]!r}")
            if not sau:
                print("        (khách không nhắn gì sau lúc hủy)")

print()
for mk, v in tong.items():
    print(mk, dict(v))

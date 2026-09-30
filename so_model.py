#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SO SÁNH HAI MODEL trên CÙNG MỘT MẺ hội thoại thật — bước 1 trước khi đổi nhà cung cấp.

Vì sao có file này (chủ shop 2026-09-11): *"một tin tốn từng đó tiền tôi thấy vẫn đắt… tôi cần
tầm 65đ/tin"*. Kimi K2.6 cắt hết lãng phí cũng chỉ về ~90đ, nên phải thử bậc model rẻ hơn
(DeepSeek Flash rẻ hơn 4-7 lần). Nhưng model rẻ mà bịa giá, sai ngôn ngữ, ra JSON hỏng thì tốn
gấp nhiều lần tiền API. Cách thử rẻ và công bằng nhất: CHỤP một mẻ gói prompt y hệt vòng thật,
đưa cùng gói qua từng model, rồi chấm bằng đúng cổng chặn (`chan_gui.kiem`) của hệ thống.

Ba lệnh, không lệnh nào gửi gì cho khách, không ghi vào sổ thật:

  python3 so_model.py lay uae [--so 40] [--gio 24] [--luong 6]
        chụp mẻ: đọc hội thoại thật, chạy đủ luật `ai_co_vao_cuoc`, dựng đúng gói prompt
        (`goi_soan`) cho những lượt AI sẽ phải gọi model → state/<tt>/so_model_me.json.
        KHÔNG gọi model, không tốn tiền.
  python3 so_model.py chay uae --nha kimi [--model kimi-k2.6]
  python3 so_model.py chay uae --nha deepseek [--model deepseek-flash]
        gọi model trên mẻ đã chụp → state/<tt>/so_model_kq_<nhà>.json (tốn tiền: ~40 lượt gọi).
        Key lấy từ .env đúng như vòng thật (KIMI_API_KEY / DEEPSEEK_API_KEY / ANTHROPIC_API_KEY).
  python3 so_model.py so uae [--a kimi --b deepseek] [--xem 12] [--vnd 26170]
        bảng so sánh: JSON đúng khuôn · hành động · cổng chặn · đúng ngôn ngữ · tiền · tốc độ,
        rồi in các ca hai model LỆCH nhau để người đọc tự phán — máy chấm được lỗi, không chấm
        được câu nào bán hàng khéo hơn.

Chấm "đúng ngôn ngữ" là ước lượng bằng từ khoá (Ả Rập / Tagalog / Anh / Việt), đủ để xếp hạng.
Câu có tiếng Việt là SAI (tiếng Việt chỉ là hướng dẫn nội bộ) — cổng chặn cũng bắt ca này.
"""

import json
import os
import re
import statistics as st
import sys
import time
import urllib.request
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import ai_sale as A        # noqa: E402
import chan_gui as CG      # noqa: E402
import ho_so as HS         # noqa: E402

VND = 26170.0              # tỷ giá Vietcombank bán ra 09/09/2026 — đổi bằng --vnd


def _f(mkey, ten):
    return os.path.join(SCRIPT_DIR, "state", mkey, ten)


# ───────────────────────── Ngôn ngữ (ước lượng) ─────────────────────────

_TL = re.compile(r"\b(po|opo|ako|ikaw|kayo|natin|namin|ang|ng|mga|magkano|magkanu|pwede|"
                 r"paano|kailan|saan|hindi|oo|sige|salamat|maganda|kasi|lang|naman|ba|"
                 r"gusto|bibili|order po|sana|talaga|meron|wala|dito|diyan|ito|yan)\b", re.I)
_VI = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]|\b(dạ|ạ|chị|em ơi|anh ơi|ạ\b)")


def ngon_ngu(t):
    """'ar' | 'vi' | 'tl' | 'en' | '' — chỉ để so khách với câu trả lời, không phải máy dịch."""
    t = (t or "").strip()
    if not t:
        return ""
    if len(re.findall(r"[؀-ۿ]", t)) >= 3:
        return "ar"
    if _VI.search(t):
        return "vi"
    if len(_TL.findall(t)) >= 2:
        return "tl"
    return "en"


def cham_ngon_ngu(nn_khach, nn_tin):
    """'đúng' | 'tạm' | 'SAI' | ''.

    Anh ↔ Tagalog cả hai chiều đều là 'tạm': khách Philippines ở UAE viết Taglish, ba tin cuối
    có thể chỉ là "Villa 106" (máy đoán Anh) trong khi cả hội thoại là Tagalog — lượt đầu chấm
    "SAI" oan ca này. SAI thật chỉ còn: câu có tiếng Việt, hoặc khách Ả Rập mà trả lời không
    phải Ả Rập (và ngược lại).
    """
    if not nn_tin:
        return ""
    if nn_tin == "vi":
        return "SAI"
    if not nn_khach or nn_khach == nn_tin:
        return "đúng"
    if {nn_khach, nn_tin} == {"tl", "en"}:
        return "tạm"
    return "SAI"


# ───────────────────────── 1. Chụp mẻ ─────────────────────────

def cmd_lay(mkey, so=40, gio=24, moi_page=3, luong=6):
    """Chụp mẻ. Đọc API song song theo page (phần tốn thời gian), dựng prompt tuần tự ở luồng
    chính (hồ sơ SQLite không dùng chéo luồng được). Mỗi page dừng đọc khi đủ `moi_page` lượt
    hợp lệ — bản đầu đọc tuần tự hết 20 hội thoại/page × 69 page nên quá 10 phút."""
    import random
    from concurrent.futures import ThreadPoolExecutor
    try:
        import auto_len_don as _D
    except Exception:                                    # noqa: BLE001
        _D = None
    pages = A._pages_cua_thi_truong(mkey)
    if not pages:
        sys.exit(f"❌ {mkey}: không có page nào token sống")
    random.seed(20260911)
    random.shuffle(pages)                  # trải đều nhiều page, không dồn vào page bận nhất
    bo = Counter()
    print(f"\n📸 Chụp mẻ so sánh — {mkey}: {len(pages)} page · {gio} giờ · cần {so} lượt"
          f" · tối đa {moi_page} lượt/page · {luong} luồng", flush=True)

    def _doc_page(cap):
        pid, stt = cap
        kb_page = A.nap_kich_ban(mkey, pid)
        if not kb_page or not kb_page.get("mau"):
            return pid, stt, None, "chưa có kịch bản", []
        convs, err = A.hoi_thoai_gan_day(pid, stt["token"], so=12, gio=gio)
        if err:
            return pid, stt, None, "lỗi/token hỏng", []
        ung = []
        for c in convs:
            if len(ung) >= moi_page:
                break
            msgs, cus_id, e = A.tin_cua_hoi_thoai(pid, c["id"], stt["token"])
            if e or not msgs:
                continue
            quyet, ly_do = A.ai_co_vao_cuoc(msgs)
            if quyet not in ("tra_loi", "xet"):
                ung.append({"bo": f"luật: {quyet}"})
                continue
            if _D is not None:
                try:
                    if _D.the_noi_da_xong(c):
                        ung.append({"bo": "thẻ Đã gửi"})
                        continue
                except Exception:                        # noqa: BLE001
                    pass
            ung.append({"c": c, "msgs": msgs, "quyet": quyet, "ly_do": ly_do})
            time.sleep(0.05)
        return pid, stt, kb_page, None, ung

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=luong) as bom:
        ket = list(bom.map(_doc_page, pages))
    print(f"  đọc xong {len(pages)} page trong {time.time() - t0:.0f}s", flush=True)

    kho = HS.mo(mkey)
    phan_xa = A.nap_botcake(mkey)
    items, dem_page = [], Counter()
    for pid, stt, kb_page, loi, ung in ket:
        if loi:
            bo[loi] += 1
            continue
        gia = A.bo_gia(kb_page, mkey)
        for u in ung:
            if len(items) >= so:
                break
            if u.get("bo"):
                bo[u["bo"]] += 1
                continue
            c, msgs, quyet, ly_do = u["c"], u["msgs"], u["quyet"], u["ly_do"]
            khach = [m for m in msgs if m["boi"] == "khach"]
            cuoi = khach[-1] if khach else None
            ten_khach = ((c.get("customers") or [{}])[0].get("name")
                         or (c.get("from") or {}).get("name"))
            ta = [m["text"] for m in msgs if m["boi"] != "khach" and (m.get("text") or "").strip()]
            # Hồ sơ bền: đọc, gộp — KHÔNG ghi (HS.ghi) để mẻ thử không đụng trạng thái thật
            hs_cu = HS.doc(kho, c["id"]) or {}
            m_moi = HS.tin_moi(msgs, hs_cu.get("tin_da_doc"))
            co_moi = HS.trich(m_moi or msgs, mkey, gia, ten_khach)
            ho_so, _ = HS.gop(HS.chi_truong(hs_cu), co_moi)
            n_cu = len(msgs) - len(m_moi)
            msgs_prompt = (msgs[max(0, n_cu - A.TIN_CU_GIU):]
                           if (hs_cu.get("tin_da_doc") and len(msgs) > A.TIN_KHONG_CAT)
                           else msgs[-40:])
            rec = {"msgs": msgs, "ten_khach": ten_khach, "thi_truong": mkey, "ho_so": ho_so,
                   "msgs_prompt": msgs_prompt, "cat_bot": max(0, len(msgs) - len(msgs_prompt))}
            on_dinh, noi_dung = A.goi_soan(rec, kb_page, gia, phan_xa, quyet)
            items.append({
                "pid": str(pid), "page": stt.get("name") or str(pid), "conv": str(c["id"]),
                "khach": (ten_khach or "?")[:40], "quyet": quyet, "ly_do": ly_do,
                "hoi": (cuoi["text"] if cuoi else "")[:300], "hoi_luc": cuoi["luc"] if cuoi else "",
                "khach_noi": " | ".join(m["text"][:120] for m in khach[-3:]),
                "tin_truoc": ta[-1] if ta else None, "n_tin": len(msgs),
                "on_dinh": on_dinh, "noi_dung": noi_dung,
            })
            dem_page[stt.get("name") or str(pid)] += 1
        if len(items) >= so:
            break
    if len(items) < so:
        # Giờ vắng khách thì "đang chờ trả lời" chỉ được vài lượt (05:27 11/09: 2 lượt / 69 page).
        # Bổ sung bằng chính những lượt máy ĐÃ gọi model thật trong cửa sổ (sổ chi phí): cắt hội
        # thoại đúng tại tin khách lúc đó rồi dựng lại gói — cùng một đầu vào cho cả hai model,
        # và còn so được với quyết định thật của Kimi hôm đó.
        them = _tu_so(mkey, {(p, st.get("name")): st for p, st in pages}, kho, phan_xa, gio,
                      so - len(items), moi_page, da_co={x["conv"] for x in items}, bo=bo)
        items += them
        for x in them:
            dem_page[x["page"]] += 1
    try:
        kho.close()
    except Exception:                                    # noqa: BLE001
        pass
    out = {"mkey": mkey, "luc": time.time(), "gio": gio, "items": items}
    f = _f(mkey, "so_model_me.json")
    json.dump(out, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    q = Counter(x["quyet"] for x in items)
    print(f"\n  ✅ {len(items)} lượt từ {len(dem_page)} page — Botcake im (tra_loi) {q['tra_loi']} ·"
          f" Botcake đã rep (xet) {q['xet']}")
    print(f"     bỏ qua: {dict(bo)}")
    ky = [len(x["on_dinh"]) + len(x["noi_dung"]) for x in items]
    if ky:
        print(f"     gói prompt: trung vị {st.median(ky):,.0f} ký tự · lớn nhất {max(ky):,}")
    print(f"  💾 {f}\n  → tiếp: python3 so_model.py chay {mkey} --nha kimi   |   --nha deepseek\n")


def _tu_so(mkey, pages, kho, phan_xa, gio, can, moi_page, da_co, bo):
    """Ứng viên từ sổ chi phí: dòng that=1 có gọi model (cửa tra_loi/xet) trong `gio` giờ."""
    import random
    f = _f(mkey, "so_chi_phi.jsonl")
    if not os.path.exists(f):
        return []
    tu = time.time() - gio * 3600
    rows = {}
    for d in open(f, encoding="utf-8"):
        try:
            r = json.loads(d)
        except Exception:                                # noqa: BLE001
            continue
        try:
            luc = time.mktime(time.strptime(str(r.get("luc"))[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:                                # noqa: BLE001
            continue
        if luc < tu or r.get("that") != 1 or not r.get("goi") or r.get("cua") not in ("tra_loi", "xet"):
            continue
        rows[(r["conv"], r["khach_luc"])] = r          # dòng cuối của mỗi lượt khách
    ung = list(rows.values())
    random.seed(20260911)
    random.shuffle(ung)
    tok = {str(p): st for (p, _), st in pages.items()}
    ten_page = {str(p): n for (p, n) in pages}
    items, theo_page = [], Counter()
    print(f"  bổ sung từ sổ chi phí: {len(ung)} lượt máy đã gọi model thật trong {gio:.0f} giờ", flush=True)
    for r in ung:
        if len(items) >= can:
            break
        pid, conv = str(r["pid"]), str(r["conv"])
        if conv in da_co or theo_page[pid] >= moi_page or pid not in tok:
            continue
        kb_page = A.nap_kich_ban(mkey, pid)
        if not kb_page or not kb_page.get("mau"):
            continue
        msgs, _cus, e = A.tin_cua_hoi_thoai(pid, conv, tok[pid]["token"])
        if e or not msgs:
            bo["sổ: không đọc được tin"] += 1
            continue
        cat = [m for m in msgs if (m.get("luc") or "") <= r["khach_luc"]]
        if not cat or cat[-1]["boi"] != "khach" or cat[-1]["luc"] != r["khach_luc"]:
            bo["sổ: không dựng lại được mốc"] += 1     # tin cũ hơn 60 tin đã rơi khỏi API
            continue
        quyet, ly_do = A.ai_co_vao_cuoc(cat)
        if quyet not in ("tra_loi", "xet"):
            bo[f"sổ: luật nay bảo {quyet}"] += 1
            continue
        gia = A.bo_gia(kb_page, mkey)
        khach = [m for m in cat if m["boi"] == "khach"]
        cuoi = khach[-1]
        ten_khach = next((m.get("ten") for m in khach if m.get("ten")), None)
        ta = [m["text"] for m in cat if m["boi"] != "khach" and (m.get("text") or "").strip()]
        # Không dùng hồ sơ bền (đã bị dời sau mốc này) — coi như lượt đầu: gói nhỉnh hơn thật
        # một chút nhưng GIỐNG HỆT cho cả hai model, là điều cần cho phép so sánh.
        ho_so = HS.trich(cat, mkey, gia, ten_khach)
        rec = {"msgs": cat, "ten_khach": ten_khach, "thi_truong": mkey, "ho_so": ho_so,
               "msgs_prompt": cat[-40:], "cat_bot": max(0, len(cat) - 40)}
        on_dinh, noi_dung = A.goi_soan(rec, kb_page, gia, phan_xa, quyet)
        items.append({
            "pid": pid, "page": ten_page.get(pid) or pid, "conv": conv,
            "khach": (ten_khach or "?")[:40], "quyet": quyet, "ly_do": ly_do,
            "hoi": (cuoi["text"] or "")[:300], "hoi_luc": cuoi["luc"],
            "khach_noi": " | ".join(m["text"][:120] for m in khach[-6:]),
            "tin_truoc": ta[-1] if ta else None, "n_tin": len(cat),
            "on_dinh": on_dinh, "noi_dung": noi_dung,
            "nguon": "so", "hd_that": r.get("hd"), "tien_that": r.get("tien"), "model_that": r.get("model"),
        })
        theo_page[pid] += 1
        time.sleep(0.05)
    return items


# ───────────────────────── 2. Gọi model trên mẻ ─────────────────────────

def goi_model(nha, key, url, model, noi_dung, on_dinh, dem_duoc, nhiet_do):
    """Một lượt gọi, dựng thân yêu cầu Y HỆT ai_sale.soan_bang_model. Trả dict kết quả thô."""
    def khoi(t):
        b = {"type": "text", "text": t}
        if dem_duoc:
            b["cache_control"] = {"type": "ephemeral"}
        return b
    goi = {"model": model, "max_tokens": 1500,
           "system": [khoi(A.tai_luat())] + ([khoi(on_dinh)] if on_dinh else []),
           "messages": [{"role": "user", "content": noi_dung}]}
    if nhiet_do is not None:
        goi["temperature"] = nhiet_do
    if nha in ("kimi", "deepseek"):
        goi["thinking"] = {"type": "disabled"}      # bật là model tiêu hết trần chữ vào suy nghĩ
    dau = {"content-type": "application/json"}
    if nha == "kimi":
        dau["Authorization"] = f"Bearer {key}"
    else:
        dau["x-api-key"] = key
        dau["anthropic-version"] = "2023-06-01"
    t0 = time.time()
    res, err, ma_http = None, None, None
    for lan in (1, 2):
        req = urllib.request.Request(url, data=json.dumps(goi).encode(), method="POST", headers=dau)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read().decode())
            err = None
            break
        except urllib.error.HTTPError as e:              # đọc thân lỗi để biết vì sao
            than = e.read().decode(errors="replace")[:300]
            ma_http = e.code
            err = f"HTTP {e.code}: {than}"
            if lan == 1 and "thinking" in than.lower() and "thinking" in goi:
                goi.pop("thinking")                      # nhà không nhận tham số này → gửi lại không có
                continue
            break
        except Exception as e:                           # noqa: BLE001
            err = str(e)
            break
    giay = time.time() - t0
    if err:
        return {"err": err, "giay": round(giay, 2), "http": ma_http}
    u = res.get("usage") or {}
    txt = "".join(b.get("text", "") for b in (res.get("content") or []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    qd, loi_json = None, None
    if not m:
        loi_json = "model không trả JSON"
    else:
        try:
            qd = json.loads(m.group(0))
        except Exception as e:                           # noqa: BLE001
            loi_json = f"JSON hỏng: {e}"
    return {"qd": qd, "loi_json": loi_json, "raw": txt[:600], "giay": round(giay, 2),
            "usage": {"vao": u.get("input_tokens") or 0,
                      "doc_dem": u.get("cache_read_input_tokens") or 0,
                      "ghi_dem": u.get("cache_creation_input_tokens") or 0,
                      "ra": u.get("output_tokens") or 0},
            "usage_tho": {k: v for k, v in u.items() if isinstance(v, (int, float))},
            "stop": res.get("stop_reason"), "model_tra": res.get("model")}


def cmd_chay(mkey, nha, model=None, gioi_han=None):
    f = _f(mkey, "so_model_me.json")
    if not os.path.exists(f):
        sys.exit(f"Chưa chụp mẻ — chạy: python3 so_model.py lay {mkey}")
    me = json.load(open(f, encoding="utf-8"))
    items = me["items"][:gioi_han] if gioi_han else me["items"]
    if nha not in A.NHA:
        sys.exit(f"❌ nhà {nha!r} không có trong ai_sale.NHA ({', '.join(A.NHA)})")
    url, model_md, ten_key, dem_duoc = A.NHA[nha]
    key = A.env().get(ten_key) or os.environ.get(ten_key) or ""
    nha_env, _k, _u, model_env, _d = A.nha_cung_cap()
    # Cùng nhà với .env thì lấy đúng AI_MODEL đang chạy thật (kimi-k2.6), không lấy mặc định của
    # bảng NHA (kimi-k3, đắt gấp 7) — lượt đầu 11/09 đã chạy nhầm K3 vì thế.
    model = model or (model_env if nha == nha_env else model_md)
    if not key:
        sys.exit(f"❌ Thiếu {ten_key} trong .env — dán key vào tab Cấu hình (giao diện web) hoặc .env rồi chạy lại")
    nd = A.nhiet_do()
    (gv, gd, gg, gr), khop = A.gia_theo_model(nha, model)
    print(f"\n🧪 Gọi {nha} / {model} trên {len(items)} lượt (mẻ chụp lúc "
          f"{time.strftime('%d/%m %H:%M', time.localtime(me['luc']))}) · temperature {nd}"
          + ("" if khop else " · ⚠️ chưa có giá cho model này, tính bậc đắt nhất"), flush=True)
    kq, tong = [], 0.0
    for i, it in enumerate(items, 1):
        r = goi_model(nha, key, url, model, it["noi_dung"], it["on_dinh"], dem_duoc, nd)
        r.update({"conv": it["conv"], "pid": it["pid"], "page": it["page"], "khach": it["khach"],
                  "quyet": it["quyet"]})
        if r.get("usage"):
            u = r["usage"]
            r["tien"] = round((u["vao"] * gv + u["doc_dem"] * gd + u["ghi_dem"] * gg + u["ra"] * gr) / 1e6, 8)
            tong += r["tien"]
        # Cổng chặn — đúng hàm vòng thật dùng, đúng kịch bản + giá của page
        qd = r.get("qd")
        if qd:
            kb_page = A.nap_kich_ban(mkey, it["pid"]) or {}
            gia = A.bo_gia(kb_page, mkey)
            hd = qd.get("hanh_dong")
            tin = (qd.get("tin_nhan") or "").strip()
            r["hd"], r["tin"] = hd, tin
            if tin or hd in ("im", "treo", "xac_minh_nha"):
                try:
                    pq = CG.kiem(tin, mkey=mkey, kb_page=kb_page, gia=gia, tin_truoc=it["tin_truoc"],
                                 co_anh=bool(qd.get("anh_mau")), hanh_dong=hd)
                    ma = pq.ma_loi() if callable(pq.ma_loi) else pq.ma_loi
                    r["chan"] = {"ket": pq.ket, "ma": list(ma) if ma else []}
                except Exception as e:                   # noqa: BLE001
                    r["chan"] = {"ket": "?", "ma": [f"cổng chặn lỗi: {e}"[:80]]}
            r["nn_khach"] = ngon_ngu(it["khach_noi"])
            r["nn_tin"] = ngon_ngu(tin) if tin else ""
            r["ngon_ngu"] = cham_ngon_ngu(r["nn_khach"], r["nn_tin"])
        kq.append(r)
        tt = (f"{r['hd']:8s} {r.get('chan', {}).get('ket', '-'):8s} {r.get('ngon_ngu', ''):4s} "
              f"${r.get('tien', 0):.5f} {r['giay']:5.1f}s" if qd else f"✖ {(r.get('err') or r.get('loi_json') or '?')[:70]}")
        print(f"  {i:3d}/{len(items)} [{it['page'][:22]:22s}] {it['khach'][:16]:16s} {tt}", flush=True)
        time.sleep(0.2)
    out = {"mkey": mkey, "nha": nha, "model": model, "luc": time.time(), "temperature": nd,
           "gia": [gv, gd, gg, gr], "items": kq}
    fo = _f(mkey, f"so_model_kq_{nha}.json")
    json.dump(out, open(fo, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for r in kq if r.get("qd"))
    dem = sum(r.get("usage", {}).get("doc_dem", 0) for r in kq)
    print(f"\n  ✅ {ok}/{len(kq)} lượt ra JSON · tổng ${tong:.4f} (~{tong * VND:,.0f}đ) ·"
          f" TB ${tong / max(len(kq), 1):.5f}/lượt (~{tong / max(len(kq), 1) * VND:.0f}đ) ·"
          f" đọc đệm {dem:,} token{' — ⚠️ nhà này KHÔNG báo đệm, tiền in ra là TRẦN' if dem == 0 else ''}")
    tho = [r.get("usage_tho") for r in kq if r.get("usage_tho")]
    if tho:
        print(f"     trường usage nhà trả về: {sorted(tho[0])}")
    print(f"  💾 {fo}\n  → so sánh: python3 so_model.py so {mkey}\n")


# ───────────────────────── 3. So sánh ─────────────────────────

def _tom(kq):
    it = kq["items"]
    for r in it:                       # chấm lại ngôn ngữ theo luật hiện hành, không cần gọi lại model
        if r.get("tin"):
            r["ngon_ngu"] = cham_ngon_ngu(r.get("nn_khach"), r.get("nn_tin"))
    n = len(it)
    co = [r for r in it if r.get("qd")]
    soan = [r for r in co if r.get("tin")]
    chan = Counter(r.get("chan", {}).get("ket", "-") for r in soan)
    nn = Counter(r.get("ngon_ngu") for r in soan)
    tien = [r.get("tien", 0) for r in it if r.get("tien") is not None]
    return {
        "n": n, "json_ok": len(co), "loi": [r.get("err") or r.get("loi_json") for r in it if not r.get("qd")],
        "hd": Counter(r.get("hd") for r in co),
        "soan": len(soan), "chan": chan, "nn": nn,
        "tien_tb": sum(tien) / max(len(tien), 1), "tien_tong": sum(tien),
        "giay_tb": st.median([r["giay"] for r in it]) if it else 0,
        "giay_p95": sorted(r["giay"] for r in it)[int(len(it) * 0.95)] if it else 0,
        "dai_tb": st.median([len(r["tin"]) for r in soan]) if soan else 0,
        "ra_tb": sum(r.get("usage", {}).get("ra", 0) for r in co) / max(len(co), 1),
        "dem": sum(r.get("usage", {}).get("doc_dem", 0) for r in co),
        "vao_tb": sum(r.get("usage", {}).get("vao", 0) + r.get("usage", {}).get("doc_dem", 0) for r in co) / max(len(co), 1),
    }


def cmd_so(mkey, a="kimi", b="deepseek", xem=12, vnd=VND):
    me = json.load(open(_f(mkey, "so_model_me.json"), encoding="utf-8"))
    idx = {x["conv"]: x for x in me["items"]}
    ka = json.load(open(_f(mkey, f"so_model_kq_{a}.json"), encoding="utf-8"))
    fb = _f(mkey, f"so_model_kq_{b}.json")
    kb = json.load(open(fb, encoding="utf-8")) if os.path.exists(fb) else None
    cot = [(a, ka)] + ([(b, kb)] if kb else [])
    tom = {n: _tom(k) for n, k in cot}
    W = 22
    print(f"\n{'═' * 76}\n  SO SÁNH MODEL — {mkey} — mẻ {len(me['items'])} lượt chụp lúc "
          f"{time.strftime('%d/%m %H:%M', time.localtime(me['luc']))}\n{'═' * 76}")
    print(f"  {'':34s}" + "".join(f"{n + ' / ' + k['model']:>{W + 6}s}"[:W + 6].rjust(W + 6) for n, k in cot))
    def dong(nhan, f):
        print(f"  {nhan:34s}" + "".join(f"{f(tom[n]):>{W + 6}s}" for n, _ in cot))
    dong("JSON đúng khuôn", lambda t: f"{t['json_ok']}/{t['n']}")
    dong("hành động: trả lời / im / treo / đơn",
         lambda t: f"{t['hd'].get('tra_loi', 0)} / {t['hd'].get('im', 0)} / {t['hd'].get('treo', 0)} / {t['hd'].get('len_don', 0)}")
    dong("câu soạn ra qua cổng chặn: qua/viết lại/chặn",
         lambda t: f"{t['chan'].get('qua', 0)} / {t['chan'].get('viet_lai', 0)} / {t['chan'].get('chan', 0)}"
         + (f" (nhắc {t['chan'].get('nhac', 0)})" if t['chan'].get('nhac') else ""))
    dong("đúng ngôn ngữ: đúng / tạm / SAI",
         lambda t: f"{t['nn'].get('đúng', 0)} / {t['nn'].get('tạm', 0)} / {t['nn'].get('SAI', 0)}")
    dong("độ dài câu (ký tự, trung vị)", lambda t: f"{t['dai_tb']:.0f}")
    dong("token vào (kể cả đệm) / ra TB", lambda t: f"{t['vao_tb']:,.0f} / {t['ra_tb']:.0f}")
    dong("đọc đệm (tổng token)", lambda t: f"{t['dem']:,}" if t["dem"] else "0 — nhà không báo")
    dong("tiền TB / lượt", lambda t: f"${t['tien_tb']:.5f} ≈ {t['tien_tb'] * vnd:.0f}đ")
    dong("tiền cả mẻ", lambda t: f"${t['tien_tong']:.4f} ≈ {t['tien_tong'] * vnd:,.0f}đ")
    dong("thời gian / lượt (trung vị · p95)", lambda t: f"{t['giay_tb']:.1f}s · {t['giay_p95']:.1f}s")
    for n, k in cot:
        cap = [(idx[r["conv"]].get("hd_that"), r.get("hd")) for r in k["items"]
               if r.get("qd") and idx.get(r["conv"], {}).get("hd_that")]
        if cap:
            trung = sum(1 for a_, b_ in cap if a_ == b_)
            print(f"  {n}: cùng hành động với quyết định THẬT của hệ thống hôm đó ở {trung}/{len(cap)} lượt")
    for n, t in tom.items():
        if t["loi"]:
            print(f"\n  ✖ {n}: {len(t['loi'])} lượt hỏng — " + " | ".join(str(x)[:90] for x in t["loi"][:3]))
    if kb:
        da = {r["conv"]: r for r in ka["items"]}
        db = {r["conv"]: r for r in kb["items"]}
        chung = [c for c in da if c in db and da[c].get("qd") and db[c].get("qd")]
        cung_hd = sum(1 for c in chung if da[c].get("hd") == db[c].get("hd"))
        print(f"\n  Hai model cùng hành động ở {cung_hd}/{len(chung)} lượt"
              f" ({cung_hd / max(len(chung), 1) * 100:.0f}%).")
        if tom[a]["tien_tb"] and tom[b]["tien_tb"]:
            print(f"  Tiền: {b} = 1/{tom[a]['tien_tb'] / tom[b]['tien_tb']:.1f} của {a} trên cùng gói.")
        lech = [c for c in chung if da[c].get("hd") != db[c].get("hd")
                or (da[c].get("chan", {}).get("ket") != db[c].get("chan", {}).get("ket"))]
        xau_b = [c for c in chung if db[c].get("chan", {}).get("ket") == "chan" or db[c].get("ngon_ngu") == "SAI"]
        print(f"\n  ── {len(lech)} ca hai model LỆCH nhau (in {min(xem, len(lech))}) — người đọc tự phán ──")
        for c in lech[:xem]:
            _in_ca(idx[c], a, da[c], b, db[c])
        if xau_b:
            print(f"\n  ── {len(xau_b)} ca {b} bị cổng chặn hoặc sai ngôn ngữ ──")
            for c in xau_b[:xem]:
                _in_ca(idx[c], a, da[c], b, db[c])
    else:
        print(f"\n  (chưa có kết quả {b} — dán {A.NHA.get(b, ('', '', b.upper() + '_API_KEY'))[2]}"
              f" rồi chạy: python3 so_model.py chay {mkey} --nha {b})")
        print(f"\n  ── {min(xem, len(ka['items']))} câu {a} soạn, để đọc thử ──")
        for r in ka["items"][:xem]:
            if r.get("qd"):
                _in_ca(idx[r["conv"]], a, r)
    print("")


def _in_ca(it, a, ra, b=None, rb=None):
    print(f"\n  ▸ [{it['page'][:28]}] {it['khach'][:20]} · luật: {it['quyet']} · khách: {it['hoi'][:110]!r}")
    for ten, r in ((a, ra), (b, rb)):
        if not ten:
            continue
        if not r or not r.get("qd"):
            print(f"      {ten:9s}: ✖ {(r or {}).get('err') or (r or {}).get('loi_json') or '?'}"[:140])
            continue
        ch = r.get("chan", {})
        print(f"      {ten:9s}: {r.get('hd')} · cổng {ch.get('ket', '-')}{(' ' + ','.join(ch.get('ma') or [])) if ch.get('ma') else ''}"
              f" · ngôn ngữ {r.get('ngon_ngu') or '-'} · {r.get('giay')}s")
        if r.get("tin"):
            print(f"                 “{r['tin'][:260]}”")
        elif r["qd"].get("ly_do"):
            print(f"                 (lý do: {str(r['qd'].get('ly_do'))[:120]})")


def main():
    a = sys.argv[1:]
    g = lambda c, m: a[a.index(c) + 1] if c in a else m
    if len(a) >= 2 and a[0] == "lay":
        cmd_lay(a[1], so=int(g("--so", 40)), gio=float(g("--gio", 24)), moi_page=int(g("--moi-page", 3)),
                luong=int(g("--luong", 6)))
    elif len(a) >= 2 and a[0] == "chay":
        cmd_chay(a[1], nha=g("--nha", "kimi"), model=g("--model", None),
                 gioi_han=int(g("--gioi-han", 0)) or None)
    elif len(a) >= 2 and a[0] == "so":
        cmd_so(a[1], a=g("--a", "kimi"), b=g("--b", "deepseek"), xem=int(g("--xem", 12)),
               vnd=float(g("--vnd", VND)))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

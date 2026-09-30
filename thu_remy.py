import sys; sys.path.insert(0, "/tmp/thu_cm")
import ai_sale as A
print("nextmonth:", A.khach_vua_chon_goi([{"boi":"botcake","text":"$199"},{"boi":"khach","text":"Nextmonth I order po"}], "usa", {"gia_ban":[199]}))
mkey = "usa"
for pid, st in A._pages_cua_thi_truong(mkey):
    if "Gold Charm Bracelet" in (st.get("name") or ""):
        msgs, cus, e = A.tin_cua_hoi_thoai(pid, "1185534851313592_28200111226347333", st["token"]); break
kb = A.nap_kich_ban(mkey, pid); gia = A.bo_gia(kb, mkey); px = A.nap_botcake(mkey)
cut = [m for m in msgs if m["boi"] not in ("ai", "nguoi")][:]
i = max(k for k, m in enumerate(cut) if m["boi"] == "khach" and "Gusto yang" in (m.get("text") or ""))
cut = cut[:i + 1]
print("quyet:", A.ai_co_vao_cuoc(cut), "| chon:", A.khach_vua_chon_goi(cut, mkey, gia))
rec = {"msgs": cut, "ten_khach": "Remy Campos Baylor", "thi_truong": mkey, "ho_so": {}, "msgs_prompt": cut, "cat_bot": 0,
       "giai_doan": None, "ly_do": "", "theo_buoc": False}
od, nd = A.goi_soan(rec, kb, gia, px, "tra_loi")
for n in range(2):
    qd, e = A.soan_bang_model(nd, od); print("\nLẦN", n + 1, (qd or {}).get("hanh_dong"), "|", (qd or {}).get("tin_nhan"))

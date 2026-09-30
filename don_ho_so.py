import sys, os, glob, sqlite3, io, contextlib, time, json
os.chdir("/opt/pancake-tool"); sys.path.insert(0, "/opt/pancake-tool")
import ho_so as HS
THAT = "--that" in sys.argv
moc = time.strftime("%Y%m%d-%H%M")
tong = 0; nhat_ky = []
for db in sorted(glob.glob("state/*/ho_so.db")):
    tt = db.split("/")[1]
    cn = sqlite3.connect(db, timeout=10)
    rows = cn.execute("SELECT conv_id, dia_chi FROM ho_so WHERE dia_chi IS NOT NULL AND dia_chi!=''").fetchall()
    bo = []
    for conv, dc in rows:
        with contextlib.redirect_stdout(io.StringIO()):
            ma = HS.khong_phai_dia_chi(dc, tt)
        if ma:
            bo.append((conv, dc, ma))
    for conv, dc, ma in bo:
        print(tt, ma, conv, repr(dc[:90]))
    if bo and THAT:
        dst = sqlite3.connect(f"{db}.bak-{moc}-truoc-don-dia-chi-khong-phai")
        cn.backup(dst); dst.close()
        for conv, dc, ma in bo:
            cn.execute("UPDATE ho_so SET dia_chi=NULL WHERE conv_id=? AND dia_chi=?", (conv, dc))
            nhat_ky.append({"tt": tt, "conv": conv, "dia_chi_cu": dc, "ma": ma})
        cn.commit()
    tong += len(bo); cn.close()
print("tổng", tong, "· ghi" if THAT else "· CHẠY THỬ")
if THAT:
    json.dump(nhat_ky, open(f"state/don_dia_chi_khong_phai-{moc}.json", "w"), ensure_ascii=False, indent=1)

#!/usr/bin/env python3
"""Đổi TÀI KHOẢN Pancake (pages.fm) mà tool dùng để chat/lên đơn — trọn gói một lệnh.

Vì sao có script này: tài khoản chủ shop bị Facebook chặn gửi qua API (#2022) trên hàng chục page
UAE (xem fb-chan-2022-do-cach-gui). Danh tính gửi "Public API" sinh từ PANCAKE_USER_TOKEN, nên
cách thoát là dùng tài khoản Pancake SẠCH: thay token tài khoản, cấp lại token page bằng tài khoản
mới (token page mang danh tính tài khoản sinh ra nó), xoá danh sách page bị chặn để AI thử lại ngay.

Dùng:
  python3 doi_tai_khoan.py kiem  <token mới>     # chỉ soi: tài khoản mới thấy bao nhiêu page,
                                                 # quyền gì trên các page đang có token — KHÔNG sửa gì
  python3 doi_tai_khoan.py doi   <token mới>     # làm thật: sao lưu .env, thay token, cấp lại token
                                                 # page mọi thị trường có token, xoá page_bi_fb_chan,
                                                 # restart pancake-len-don + aisale-chat
  python3 doi_tai_khoan.py doi   <token mới> --tt uae,saudi   # chỉ cấp lại ở vài thị trường

Chạy TRÊN VPS (cần PANCAKE_SERVER=1 mới sinh được token page). Trên Mac chỉ nên dùng `kiem`.
Token page cũ HẾT HIỆU LỰC sau khi cấp lại — hệ /opt/aicloser giữ cache token cũ sẽ mất đọc
(chat của nó đang tắt nên không sao).
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")
BASE = "https://pages.fm/api/v1"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pancake-tool"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def pages_cua_token(tok):
    res = http_get(f"{BASE}/pages?" + urllib.parse.urlencode({"access_token": tok}))
    if not res.get("success", True):
        sys.exit(f"❌ Token bị từ chối: {json.dumps(res, ensure_ascii=False)[:200]}")
    pages = res.get("pages") or []
    if not pages:
        pages = (res.get("categorized") or {}).get("activated") or []
    return {str(p.get("id")): p for p in pages}


def cac_thi_truong_co_token():
    out = {}
    st_dir = os.path.join(SCRIPT_DIR, "state")
    for tt in sorted(os.listdir(st_dir)):
        f = os.path.join(st_dir, tt, "page_tokens.json")
        if not os.path.isfile(f):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        co = {pid: st for pid, st in d.items() if isinstance(st, dict) and st.get("token")}
        if co:
            out[tt] = co
    return out


def kiem(tok):
    pages = pages_cua_token(tok)
    print(f"🔎 Tài khoản mới nhìn thấy {len(pages)} page trên pages.fm")
    tong_thay = tong_admin = tong_mu = 0
    for tt, co in cac_thi_truong_co_token().items():
        thay = [p for p in co if p in pages]
        admin = [p for p in thay if (pages[p].get("role_in_page") or "").upper() not in ("EDIT_PROFILE", "EDITOR")]
        mu = [p for p in co if p not in pages]
        tong_thay += len(thay); tong_admin += len(admin); tong_mu += len(mu)
        print(f"  • {tt:<9} {len(co):>3} page đang có token → tài khoản mới thấy {len(thay):>3}, "
              f"đủ quyền cấp token {len(admin):>3}, KHÔNG thấy {len(mu):>3}")
        for p in mu[:8]:
            print(f"      ✖ không thấy: {co[p].get('name', p)[:50]} ({p})")
        if len(mu) > 8:
            print(f"      … và {len(mu) - 8} page nữa")
        for p in thay:
            if p not in admin:
                print(f"      ⚠ chỉ Editor: {pages[p].get('name', p)[:50]} ({p}) — cấp token sẽ báo 'Thiếu quyền Admin'")
    print(f"\nTổng: thấy {tong_thay} · đủ quyền {tong_admin} · không thấy {tong_mu}")
    print("Page 'không thấy' hoặc 'chỉ Editor' vẫn giữ token của tài khoản CŨ → vẫn gửi bằng danh tính cũ (vẫn bị chặn).")
    return pages


def thay_env(tok):
    bak = ENV_PATH + time.strftime(".bak-%Y%m%d-%H%M-truoc-doi-tai-khoan")
    shutil.copy2(ENV_PATH, bak)
    lines = open(ENV_PATH, encoding="utf-8").read().splitlines()
    da = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("PANCAKE_USER_TOKEN="):
            lines[i] = f"PANCAKE_USER_TOKEN={tok}"
            da = True
    if not da:
        lines.append(f"PANCAKE_USER_TOKEN={tok}")
    open(ENV_PATH, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"💾 Đã sao lưu .env → {os.path.basename(bak)} và thay PANCAKE_USER_TOKEN")


def doi(tok, chi_tt=None):
    env = {}
    for ln in open(ENV_PATH, encoding="utf-8"):
        if "=" in ln and not ln.strip().startswith("#"):
            k, v = ln.split("=", 1); env[k.strip()] = v.strip()
    if env.get("PANCAKE_SERVER") != "1":
        sys.exit("❌ Máy này không có PANCAKE_SERVER=1 → không sinh được token page. Chạy trên VPS.")
    if env.get("PANCAKE_USER_TOKEN", "") == tok:
        print("ℹ .env đã dùng đúng token này rồi — chỉ cấp lại token page + restart.")
    pages = kiem(tok)
    print()
    thay_env(tok)

    tts = cac_thi_truong_co_token()
    if chi_tt:
        tts = {k: v for k, v in tts.items() if k in chi_tt}
    ket = {}
    for tt, co in tts.items():
        only = [p for p in co if p in pages
                and (pages[p].get("role_in_page") or "").upper() not in ("EDIT_PROFILE", "EDITOR")]
        if not only:
            print(f"⏭ {tt}: tài khoản mới không thấy page nào đang có token — bỏ qua"); continue
        print(f"\n🔑 {tt}: cấp lại token cho {len(only)} page bằng tài khoản mới…")
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "auto_len_don.py"), "setup", tt,
               "--force-token", "--only", ",".join(only)]
        r = subprocess.run(cmd, cwd=SCRIPT_DIR, text=True, capture_output=True)
        tail = (r.stdout or "").strip().splitlines()
        for ln in tail:
            if ln.startswith(("  ✖", "✅")):
                print("   " + ln)
        if r.returncode != 0:
            print("   ⚠ setup thoát mã", r.returncode, (r.stderr or "")[-300:])
        ket[tt] = [ln for ln in tail if ln.startswith("✅")]

    # Xoá danh sách page bị FB chặn: danh tính mới thì phải cho AI thử gửi lại ngay.
    for tt in tts:
        f = os.path.join(SCRIPT_DIR, "state", tt, "page_bi_fb_chan.json")
        if os.path.isfile(f):
            bak = f + time.strftime(".bak-%Y%m%d-%H%M")
            shutil.move(f, bak)
            print(f"🧹 {tt}: đã dọn page_bi_fb_chan.json (giữ bản cũ {os.path.basename(bak)})")

    for svc in ("pancake-len-don", "aisale-chat"):
        r = subprocess.run(["systemctl", "restart", svc], text=True, capture_output=True)
        print(f"🔄 restart {svc}: {'ok' if r.returncode == 0 else r.stderr.strip()}")
    print("\n✅ Xong. Theo dõi: tail -f /var/log/aisale-chat.log | grep -E '2022|gửi|Gửi'")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("kiem", "doi"):
        sys.exit(__doc__)
    chi = None
    if "--tt" in a:
        chi = set(a[a.index("--tt") + 1].split(","))
    if a[0] == "kiem":
        kiem(a[1])
    else:
        doi(a[1], chi)

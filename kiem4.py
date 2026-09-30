import json, os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D
D.set_market("uae")
tok = json.load(open("state/uae/page_tokens.json", encoding="utf-8"))
def pid_cua(ten):
    for p, s in tok.items():
        if (s.get("name") or "").startswith(ten[:22]):
            return p
    return None
CA = [("BodyFirm Essentials UAE","Jori Khan","0564605687"),
      ("Veloura Collection","Arlene Cantero","0565979121"),
      ("Ginger Belly Care UAE","MD Ahasan","0545615707"),
      ("Ginger Belly Care UAE","Muhammad Ramzan","0567748303"),
      ("Leg Glow Lab UAE","Elle Chim","0521723813"),
      ("Madam Jane Feng Shui Expert UA","Vange Carias Carias","0529396654")]
print("Kiểm với PAGE THẬT của từng hội thoại:\n")
for page, ten, sdt in CA:
    pid = pid_cua(page)
    roi, mo = D.da_mua_o_page(pid, None, sdt, ten)
    print(f"  {'🛑 CHẶN   ' if roi else '✅ cho qua'} {ten:22s} @ {page[:26]:28s} {mo or ''}")
    time.sleep(0.5)

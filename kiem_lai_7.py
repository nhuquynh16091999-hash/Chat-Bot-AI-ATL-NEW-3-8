import os, sys, time
sys.path.insert(0, "/opt/pancake-tool"); os.chdir("/opt/pancake-tool")
import auto_len_don as D
D.set_market("uae")
CA = [("Jori Khan","0564605687"), ("Arlene Cantero","0565979121"),
      ("MD Ahasan","0545615707"), ("Muhammad Ramzan","0567748303"),
      ("Elle Chim","0521723813"), ("Felsa Babor","0509674764"),
      ("Vange Carias","0529396654")]
print("Kiểm lại 7 ca bằng cửa ĐÃ SỬA:\n")
for ten, sdt in CA:
    roi, mo = D.da_mua_o_page(None, None, sdt)
    print(f"  {'🛑 CHẶN' if roi else '✅ cho qua'}  {ten:18s} {sdt}  {mo or ''}")
    time.sleep(0.4)

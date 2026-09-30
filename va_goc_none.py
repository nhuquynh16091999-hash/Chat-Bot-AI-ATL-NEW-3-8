import sys, shutil, time, py_compile
f = sys.argv[1]
s = open(f, encoding="utf-8").read()
cu = '''        goc = dia_chi_luu.get("dia_chi_goc") or saved
        _manh = [x for x in goc.split(",")]'''
moi = '''        # Khách chưa có địa chỉ lưu nào → saved/dia_chi_goc đều None. Thiếu `or ""` thì goc.split văng
        # AttributeError: từ 14/09 17:53 tới 15/09 làm hỏng "lên đơn sớm" của AI Sale (ca Cucu Ella,
        # Golden Youth Beauty KSA) và giết cả vòng "lên đơn không tag" của daemon.
        goc = dia_chi_luu.get("dia_chi_goc") or saved or ""
        _manh = [x for x in goc.split(",")]'''
n = s.count(cu)
assert n == 1, f"khớp {n} lần, không ghi"
bak = f + time.strftime(".bak-%Y%m%d-%H%M-truoc-goc-none")
shutil.copy2(f, bak)
open(f, "w", encoding="utf-8").write(s.replace(cu, moi))
py_compile.compile(f, doraise=True)
print("đã vá", f, "· bak", bak)

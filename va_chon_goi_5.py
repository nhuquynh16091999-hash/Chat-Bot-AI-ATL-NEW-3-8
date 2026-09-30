import sys
f="ho_so.py"; s=open(f,encoding="utf-8").read()
a=r'|\b[1-4]\s*(?:get|take)\s*[1-4]\b", re.I)'; b=r'|^\s*[1-4]\s*(?:get|take)\s*[1-4]\b", re.I)'
if s.count(a)!=1: sys.exit(f"✖ khớp {s.count(a)}")
open(f,"w",encoding="utf-8").write(s.replace(a,b)); print("✔ siết N get N")
import importlib, ho_so as HS
importlib.reload(HS)
for t in ["2 get 2 po","buy 2 take 2","I work 1 get 2 days off","1 only","just one po","Only 1 items to try"]:
    print(" ", repr(t), bool(HS.trich([{"boi":"khach","text":t}],"saudi").get("so_luong")))

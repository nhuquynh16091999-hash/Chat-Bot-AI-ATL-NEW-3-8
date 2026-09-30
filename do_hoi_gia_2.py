"""Đo hai chiều HOI_GIA cũ (argv1, file .py) vs mới (ai_sale) trên sổ so_chi_phi, in từng câu đổi theo từ khớp."""
import collections, glob, importlib.util, json, sys
import ai_sale as A

spec = importlib.util.spec_from_file_location("cu", sys.argv[1])
cu = importlib.util.module_from_spec(spec); spec.loader.exec_module(cu)
doi = collections.defaultdict(set)
for f in glob.glob("state/*/so_chi_phi.jsonl"):
    for l in open(f, encoding="utf-8"):
        try:
            h = A.lam_sach(json.loads(l).get("hoi") or "")
        except Exception:
            continue
        a, b = cu.HOI_GIA.search(h.lower()), A.HOI_GIA.search(h.lower())
        if bool(a) != bool(b):
            doi[(bool(b), (b or a).group(0))].add(h[:100])
for (moi, tu), v in sorted(doi.items(), key=lambda x: -len(x[1])):
    print("THÊM" if moi else "BỚT", repr(tu), len(v))
    for x in sorted(v)[:12]:
        print("    ", x)

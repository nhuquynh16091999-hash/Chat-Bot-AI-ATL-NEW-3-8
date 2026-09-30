"""Thử vá + đo hai chiều trên sổ so_chi_phi (trường hoi)."""
import glob, json, re, sys
import ai_sale as A

for t in ["prce sir", "Prise", "Pirc", "how much", "price sir", "No this prize ladt sept 1",
          "pics po", "May pic po nong actual bracelet?", "nice", "piece", "Is it good for dry skin?"]:
    m = [{"boi": "page", "text": "x"}, {"boi": "khach", "text": t}]
    print(repr(t), "hoi_gia=", bool(A.khach_hoi_gia_gan(m)), "tin_mau_qc=", bool(A.TIN_MAU_QC.match(t)),
          "trong_tam=", A.khach_hoi_trong_tam(m))

if len(sys.argv) > 1:
    import importlib.util
    spec = importlib.util.spec_from_file_location("cu", sys.argv[1])
    cu = importlib.util.module_from_spec(spec); spec.loader.exec_module(cu)
    doi = {}
    for f in glob.glob("state/*/so_chi_phi.jsonl"):
        for l in open(f, encoding="utf-8"):
            try:
                h = A.lam_sach(json.loads(l).get("hoi") or "")
            except Exception:
                continue
            for ten, a, b in (("HOI_GIA", cu.HOI_GIA.search(h.lower()), A.HOI_GIA.search(h.lower())),
                              ("TIN_MAU_QC", cu.TIN_MAU_QC.match(h.strip()), A.TIN_MAU_QC.match(h.strip()))):
                if bool(a) != bool(b):
                    doi.setdefault((ten, bool(b)), set()).add(h[:90])
    for k, v in doi.items():
        print(k, len(v))
        for x in sorted(v)[:15]:
            print("   ", x)

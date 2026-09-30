"""Vá giá gõ sai ("prce sir", "Prise", "Pirc", "prize") — ca Malik Alyan 14/09. Khớp khác 1 lần thì không ghi."""
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "ai_sale.py"
s = open(p, encoding="utf-8").read()
GO = "prce|prces|pric|prics|prise|prize|pirc|pirce|prcie"
if GO in s:
    sys.exit("đã vá rồi — thôi")
va = [
    (r'''    r"\b(how\s*much|howmuch|price|prices|pricing|cost|magkano''',
     r'''    r"\b(how\s*much|howmuch|price|prices|pricing|''' + GO + r'''|cost|magkano'''),
    (r'''    r"|price|prices|the\s*price|what(?:'?s|\s*is)\s*the\s*price''',
     r'''    r"|price|prices|''' + GO + r'''|the\s*price|what(?:'?s|\s*is)\s*the\s*price'''),
    ("\nHOI_GIA = re.compile(",
     "\n# Giá gõ sai (\"prce sir\", \"Prise\", \"Pirc\", \"this prize\") — ca Malik Alyan 14/09 (Golden Noor KSA): HOI_GIA không\n"
     "# nhận \"prce\" → cổng nhac_gia tưởng khách KHÔNG hỏi giá, bắt soạn lại không giá → AI bịa đoạn công dụng.\n"
     "HOI_GIA = re.compile("),
]
for cu, moi in va:
    n = s.count(cu)
    assert n == 1, f"khớp {n} lần: {cu[:60]!r} — KHÔNG ghi"
    s = s.replace(cu, moi)
open(p, "w", encoding="utf-8").write(s)
print("vá xong")

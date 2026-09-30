"""Vá 2: giá gõ sai / tiếng khác chỉ nằm ở _GIA_GO_SAI → đưa vào HOI_GIA (cổng nhac_gia chỉ tin HOI_GIA).
Khớp khác 1 lần thì không ghi. Tham số 2 (tuỳ chọn): danh sách từ thay cho mặc định, để đo thử."""
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "ai_sale.py"
GO2 = sys.argv[2] if len(sys.argv) > 2 else (
    r"m[ae]?g\s*k[ae]?no|mgkno|magkno|harga|hrga|berapa|brp|kitna|kitne|hwo\s*much"
    r"|how\s*m[auie](?:ch|tch|ck)|rate")
s = open(p, encoding="utf-8").read()
CU = "prce|prces|pric|prics|prise|prize|pirc|pirce|prcie|cost|magkano"
if "|kitna|kitne|hwo" in s.split("\nHOI_GIA = re.compile(", 1)[-1][:600]:
    sys.exit("đã vá rồi — thôi")
n = s.count(CU)
assert n == 1, f"khớp {n} lần — KHÔNG ghi"
s = s.replace(CU, CU + "|" + GO2)
open(p, "w", encoding="utf-8").write(s)
print("vá xong")

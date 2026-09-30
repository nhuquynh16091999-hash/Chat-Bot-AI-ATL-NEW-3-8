F="/opt/pancake-tool/luat_model.md"; s=open(F,encoding="utf-8").read()
if "KHÁCH NÓI MUỐN MUA" not in s:
    cu="KHÔNG BAO GIỜ CẢN KHÁCH MUA"
    assert s.count(cu)==1
    s=s.replace(cu,"""KHÁCH NÓI MUỐN MUA = ĐÃ CHỐT → XIN THÔNG TIN (chủ shop 2026-09-14 tối, ca Remy Campos Baylor — Gold Charm Bracelet US):
Botcake báo "BUY 1 GET 1 FREE — $199", khách "Gusto yang na sa picture" (tôi muốn cái trong hình) → SAI: khen sản phẩm, giảng
thanh toán, rồi hỏi "Gusto ninyo bang subukan muna ngayon?". Chủ shop: *"khách đã bảo lấy 1 cái thì xin thông tin khách chứ ai
lại hỏi có mua k"*.
- "I want this / I'll take it / gusto yang na sa picture / kukunin ko / bibili po ako / order now / أبغى" = đã chốt.
- ⛔ CẤM hỏi lại có muốn mua/thử không, khen sản phẩm, chào lại khuyến mãi, giảng thanh toán.
- ✅ Tối đa 2 câu: xác nhận gói (+ giá page đã báo; nhiều mức mà khách chưa chọn thì hỏi gói trong cùng câu) + xin tên, SĐT,
  địa chỉ còn thiếu.

"""+cu)
    open(F,"w",encoding="utf-8").write(s); print("ok luat")

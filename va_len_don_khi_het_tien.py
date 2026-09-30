# Vá 18/09: Kimi hết tiền KHÔNG được dừng khâu lên đơn (khâu đó không gọi model, không tốn tiền).
import re, shutil, time, sys
F = "/opt/pancake-tool/ai_sale.py"
s = open(F, encoding="utf-8").read()

def thay(cu, moi):
    global s
    n = s.count(cu)
    assert n == 1, f"mốc xuất hiện {n} lần: {cu[:80]!r}"
    s = s.replace(cu, moi)

# 1) sổ nhớ trong bộ nhớ: hội thoại đã xét lên đơn ở trạng thái updated_at nào (chế độ hết tiền)
thay('_HET_QUOTA = {"luc": 0.0, "loi": ""}     # lần gần nhất CHÍNH API Kimi báo hết tiền\n',
     '_HET_QUOTA = {"luc": 0.0, "loi": ""}     # lần gần nhất CHÍNH API Kimi báo hết tiền\n'
     '_CHI_LEN_DON_MOC = {}   # 18/09: hết tiền → cid -> updated_at đã xét lên đơn (chỉ đọc lại khi có tin mới)\n')

# 2) cửa hết tiền đầu lượt: KHÔNG return nữa, chuyển sang chế độ "chỉ lên đơn"
thay('''    if not du_bao:
        _het = ""
        if het_tien_that():''',
     '''    chi_len_don = False
    if not du_bao:
        _het = ""
        if het_tien_that():''')
thay('''            print("     Nạp tại platform.kimi.ai/console/account — nạp xong service tự chạy tiếp,"
                  " KHÔNG phải sửa .env.")
            return {str(cid): "cho" for cid in (chi_hoi_thoai or ())}
''',
     '''            print("     Nạp tại platform.kimi.ai/console/account — nạp xong service tự chạy tiếp,"
                  " KHÔNG phải sửa .env.")
            # ── HẾT TIỀN VẪN LÊN ĐƠN (chủ shop 18/09: *"tạo đơn này liên quan gì đến kimi, không mất
            # tiền mà"*). Bản cũ return ngay tại đây → cả bước lên đơn sớm (không gọi model) cũng dừng,
            # 5 phút mới thử lại 1 lượt: Saudi hết tiền đơn về giữa 142s (còn tiền 69s), ca #75201 456s.
            # Nay: vẫn đọc hội thoại có tin mới, chạy lên đơn sớm + đánh dấu chưa đọc, rồi DỪNG trước
            # mọi bước gọi model. Mỗi hội thoại chỉ đọc lại khi updated_at đổi (_CHI_LEN_DON_MOC).
            if chi_hoi_thoai is None:
                return {}
            chi_len_don = True
            print("     ➜ vẫn chạy LÊN ĐƠN (không tốn tiền) + đánh dấu chưa đọc; không soạn tin.")
''')

thay('''            print("     KHÔNG đọc hội thoại nào lượt này: đọc mà không trả lời được là làm tin"
                  " của khách trôi mất dấu chưa đọc.")''',
     '''            print("     KHÔNG soạn/gửi tin nào lượt này (hội thoại đọc vào đều được đánh dấu chưa đọc cho sale).")''')

# 3) _doc_page: chế độ hết tiền chỉ đọc tin hội thoại có thay đổi
thay('''                try:
                    import auto_len_don as _D
                    if _D.the_noi_da_xong(c):
                        continue
                except Exception:                        # noqa: BLE001
                    pass
                tin[c["id"]] = tin_cua_hoi_thoai(pid, c["id"], st["token"])''',
     '''                try:
                    import auto_len_don as _D
                    if _D.the_noi_da_xong(c):
                        continue
                except Exception:                        # noqa: BLE001
                    pass
                if chi_len_don:
                    _moc_ = str(c.get("updated_at") or "")
                    if _CHI_LEN_DON_MOC.get(str(c["id"])) == _moc_:
                        continue                         # hết tiền + không có gì mới → khỏi đọc lại
                tin[c["id"]] = tin_cua_hoi_thoai(pid, c["id"], st["token"])
                if chi_len_don and not tin[c["id"]][2] and tin[c["id"]][0]:
                    _CHI_LEN_DON_MOC[str(c["id"])] = _moc_   # chỉ nhớ khi đọc được — hỏng thì lượt sau đọc lại''')

# 4) vòng chính: hội thoại đã xét ở chế độ hết tiền thì giữ "cho", không đọc lại
thay('''            msgs, cus_id, e = tin_san.get(c["id"]) or tin_cua_hoi_thoai(pid, c["id"], st["token"])
            if e or not msgs:''',
     '''            if chi_len_don and c["id"] not in tin_san:
                ket_qua[str(c["id"])] = "cho"            # hết tiền, đã xét rồi — đợi nạp tiền để AI rep
                continue
            msgs, cus_id, e = tin_san.get(c["id"]) or tin_cua_hoi_thoai(pid, c["id"], st["token"])
            if e or not msgs:''')

# 5) ngay sau lên đơn sớm: chế độ hết tiền dừng tại đây (chưa gọi model gì)
thay('''                    except Exception as e:               # noqa: BLE001 — 1 đơn hỏng không giết vòng
                        dem["loi"] += 1
                        print(f"{nhan} ✖ lên đơn sớm hỏng: {e}")

            if quyet == "im":''',
     '''                    except Exception as e:               # noqa: BLE001 — 1 đơn hỏng không giết vòng
                        dem["loi"] += 1
                        print(f"{nhan} ✖ lên đơn sớm hỏng: {e}")

            if chi_len_don:
                # Hết tiền: đơn đã xét + chưa đọc đã đánh ở trên. Giữ "cho" để nạp tiền xong AI còn rep.
                ket_qua[str(c["id"])] = "cho"
                continue

            if quyet == "im":''')

if "--that" in sys.argv:
    bak = F + ".bak-" + time.strftime("%Y%m%d-%H%M") + "-truoc-len-don-khi-het-tien"
    shutil.copy2(F, bak)
    open(F, "w", encoding="utf-8").write(s)
    print("ĐÃ GHI · bak:", bak)
else:
    open("/tmp/ai_sale_thu.py", "w", encoding="utf-8").write(s)
    print("thử: /tmp/ai_sale_thu.py")

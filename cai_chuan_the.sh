#!/bin/bash
# Cai timer chuan hoa the Pancake (chu shop chot 26/09/2026). Chay lai nhieu lan van an toan.
set -e
cd /opt/pancake-tool
python3 -m py_compile chuan_the.py
cp chuan-the.service chuan-the.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now chuan-the.timer
echo "Dang chay lan dau: quet het page con goi, xoa the thua + sap thu tu (khoang 5 phut)..."
systemctl start chuan-the.service
echo "----- ket qua -----"
grep -v "  ✔" state/chuan_the.log | tail -n 15
echo "So page da sua lan nay: $(awk '/^=== .*THẬT/{n=0} /  ✔/{n++} END{print n+0}' state/chuan_the.log)"
systemctl list-timers chuan-the.timer --no-pager | head -3

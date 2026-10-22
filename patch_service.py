import re
with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_insert = False
for i, line in enumerate(lines):
    if 'pam_no     = (data.get("pam_no") or "").strip()' in line:
        new_lines.append(line)
        new_lines.append(line.replace('pam_no', 'klasifikasi').replace('(data.get("klasifikasi") or "").strip()', 'data.get("klasifikasi", "Normal")'))
    elif 'INSERT INTO pam_records' in line:
        # We know next line usually is (company_id, pam_no, ...
        new_lines.append(line)
    elif '(company_id, pam_no,' in line and 'VALUES' not in line:
        new_lines.append(line.replace('(company_id', '(klasifikasi, company_id'))
    elif 'VALUES (?,' in line:
        new_lines.append(line.replace('VALUES (?', 'VALUES (?, ?'))
    elif line.strip().startswith('(company_id, pam_no,'):
        new_lines.append(line.replace('(company_id', '(klasifikasi, company_id'))
    else:
        new_lines.append(line)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(INSERT INTO payment_beasiswa\s*\(\s*company_id,\s*siswa_code,\s*cat1,\s*cat2,\s*tanggal,\s*amount,\s*pillar,\s*perusahaan,\s*status)',
    r'\1, klasifikasi_pa',
    text
)
text = re.sub(
    r'(VALUES\s*\(\?,\s*\?,\?,\?,\?,\?,\?,\?,\'open\'\))',
    r"VALUES (?, ?,?,?,?,?,?,?,'open',?)",
    text
)
text = re.sub(
    r'(\(company_id,\s*siswa_code,\s*cat1,\s*cat2,\s*tanggal,\s*amount,\s*pillar,\s*perusahaan)\)',
    r'\1, r.get("klasifikasi_pa", "Normal"))',
    text
)

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)

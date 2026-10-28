import re
with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

# For payment_beasiswa in save_klaim_payment
text = re.sub(
    r'(INSERT INTO payment_beasiswa\s*\(\s*company_id,\s*siswa_code,\s*cat1,\s*cat2,\s*tanggal,\s*amount,\s*pillar,\s*perusahaan,\s*pam,\s*status)',
    r'\1, klasifikasi_pam',
    text
)
text = re.sub(
    r'(VALUES\s*\(\?,\s*\?,\?,\?,\?,\?,\?,\?,\?,\?,\'open\'\))',
    r"VALUES (?, ?,?,?,?,?,?,?,?,?,'open',?)",
    text
)
text = re.sub(
    r'(\(company_id,\s*siswa_code,\s*"By Medical",\s*cat2,\s*row_tanggal,\s*amount,\s*pillar,\s*perusahaan,\s*pam_no)\)',
    r'\1, klasifikasi)',
    text
)

# For klaim_medical in save_klaim_payment
text = re.sub(
    r'(INSERT INTO klaim_medical\s*\(\s*company_id,\s*siswa_code,\s*pam,\s*tanggal,\s*amount,\s*perawatan,\s*kelas,\s*rumah_sakit,\s*diagnosa,\s*spesialisasi,\s*pillar,\s*perusahaan,\s*payment_id,\s*created_at)',
    r'\1, klasifikasi_pam',
    text
)
text = re.sub(
    r'(VALUES\s*\(\?,\s*\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?\))',
    r'VALUES (?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    text
)
text = re.sub(
    r'(pillar,\s*perusahaan,\s*pb_id,\s*_ts\(\))\)',
    r'\1, klasifikasi)',
    text
)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)

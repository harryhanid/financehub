with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(INSERT INTO payment_beasiswa\n\s*\([^)]+cat4,status\))',
    r'INSERT INTO payment_beasiswa\n               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,cat3,cat4,status,klasifikasi_pa)',
    text
)
text = re.sub(
    r'(VALUES \(\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\'open\'\))',
    r"VALUES (?,?,?,?,?,?,?,?,?,?,'open',?)",
    text
)
text = re.sub(
    r'(item\.get\("cat3",""\), item\.get\("cat4",""\)\))',
    r'item.get("cat3",""), item.get("cat4",""), item.get("klasifikasi_pa","Normal"))',
    text
)

# Also check for insert_payment_rows (the actual one used by save_pa_payment which takes `rows`)
# Wait, let's search where `insert_payment_rows` is defined.

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)

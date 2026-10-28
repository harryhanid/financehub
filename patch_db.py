with open("app/database.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(except sqlite3\.OperationalError:\n\s*pass\n\n\s*try:\n\s*conn\.execute\("ALTER TABLE klaim_medical ADD COLUMN klasifikasi_pam TEXT DEFAULT \'Normal\'"\))',
    r'\1\n    except sqlite3.OperationalError:\n        pass\n\n    try:\n        conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN klasifikasi_pa TEXT DEFAULT \'Normal\'")\n    except sqlite3.OperationalError:\n        pass\n\n    try:\n        conn.execute("ALTER TABLE klaim_medical ADD COLUMN klasifikasi_pa TEXT DEFAULT \'Normal\'")',
    text
)

# Wait, `klaim_medical` won't have `klasifikasi_pa`. 
# It's better to just append it to the end of init_db().

with open("app/database.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    'conn.execute("ALTER TABLE pam_transaction_lines ADD COLUMN klasifikasi_pam TEXT DEFAULT \'Normal\'")\n    except sqlite3.OperationalError:\n        pass',
    'conn.execute("ALTER TABLE pam_transaction_lines ADD COLUMN klasifikasi_pam TEXT DEFAULT \'Normal\'")\n    except sqlite3.OperationalError:\n        pass\n\n    try:\n        conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN klasifikasi_pa TEXT DEFAULT \'Normal\'")\n    except sqlite3.OperationalError:\n        pass'
)

with open("app/database.py", "w", encoding="utf-8") as f:
    f.write(text)

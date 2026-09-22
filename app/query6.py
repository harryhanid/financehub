from database import get_conn
import json
conn = get_conn()
rows = conn.execute("SELECT id, siswa_code, pam, amount, cat2 FROM payment_beasiswa WHERE pam LIKE '%PAM-114%'").fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))

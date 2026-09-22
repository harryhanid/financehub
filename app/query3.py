from database import get_conn
import json
conn = get_conn()
cols = [r['name'] for r in conn.execute("PRAGMA table_info(payment_beasiswa)").fetchall()]
print(json.dumps(cols))

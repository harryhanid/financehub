import sqlite3
import os

db_paths = [
    'C:/Financehub/financehub.db',
    'C:/Financehub/instance/financehub.db',
    'C:/Financehub/app/financehub.db',
    'C:/Financehub/db.sqlite3'
]

db_path = None
for p in db_paths:
    if os.path.exists(p):
        db_path = p
        break

print('DB:', db_path)
if db_path:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(budget_beasiswa)")
    cols = [r[1] for r in cur.fetchall()]
    print('Cols in budget_beasiswa:', cols)

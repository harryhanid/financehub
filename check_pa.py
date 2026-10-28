import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r["name"] for r in cur.fetchall()]
if "payment_application" in tables:
    cur.execute("PRAGMA table_info(payment_application)")
    print([r["name"] for r in cur.fetchall()])
    cur.execute("SELECT * FROM payment_application WHERE pa_number='PA/SETF/027/2026'")
    for r in cur.fetchall():
        print(dict(r))

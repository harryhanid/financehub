import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, memo_id, application_number, status, actual_payment_date FROM payment_application WHERE application_number='PA/SETF/027/2026'")
for r in cur.fetchall():
    print("payment_application:", dict(r))

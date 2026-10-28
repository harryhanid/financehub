import sqlite3
import uuid

conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
c = conn.cursor()

try:
    c.execute('ALTER TABLE budget_beasiswa_requests ADD COLUMN batch_id TEXT')
except sqlite3.OperationalError:
    pass # column might already exist

# update existing rows to have unique batch_ids if null
c.execute('SELECT id FROM budget_beasiswa_requests WHERE batch_id IS NULL')
rows = c.fetchall()
for row in rows:
    batch_id = str(uuid.uuid4())[:8]
    c.execute('UPDATE budget_beasiswa_requests SET batch_id = ? WHERE id = ?', (batch_id, row[0]))

conn.commit()
conn.close()
print('Added batch_id')

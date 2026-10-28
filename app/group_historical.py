import sqlite3
import collections

conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
c = conn.cursor()

c.execute('SELECT id, siswa_code, created_at, batch_id FROM budget_beasiswa_requests')
rows = c.fetchall()

groups = collections.defaultdict(list)
for r in rows:
    # Key: (siswa_code, created_at)
    # created_at is like '2026-10-02 06:38:15'
    groups[(r[1], r[2])].append(r)

for key, items in groups.items():
    if len(items) > 1:
        # Use the batch_id of the first item for all items in this group
        master_batch_id = items[0][3]
        for item in items[1:]:
            c.execute('UPDATE budget_beasiswa_requests SET batch_id = ? WHERE id = ?', (master_batch_id, item[0]))

conn.commit()
conn.close()
print('Historical data grouped!')

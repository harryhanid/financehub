import sqlite3
conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS budget_beasiswa_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    siswa_code      TEXT NOT NULL,
    action_type     TEXT NOT NULL, -- 'ADD', 'EDIT', 'DELETE'
    budget_id       INTEGER,       -- NULL if ADD, refers to budget_beasiswa(id) if EDIT/DELETE
    cat1            TEXT,
    cat2            TEXT,
    tanggal         TEXT,
    amount          REAL DEFAULT 0,
    pillar          TEXT,
    tgl_expired     TEXT,
    status          TEXT DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    reject_reason   TEXT,
    created_by      TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    processed_by    TEXT,
    processed_at    TEXT
);
''')
conn.commit()
conn.close()
print('Table created successfully.')

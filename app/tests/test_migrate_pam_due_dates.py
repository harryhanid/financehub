import os
import sys
import sqlite3

import config

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(os.path.dirname(base_dir), "scripts")
sys.path.insert(0, scripts_dir)

from migrate_pam_due_dates import migrate


def test_migration_updates_stale_due_dates(tmp_path):
    db_path = str(tmp_path / "migrate_test.db")
    from database import init_db
    old_db_path = config.DB_PATH
    config.DB_PATH = db_path
    try:
        init_db()
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, pillar, source, status, created_at)
               VALUES (2, 'PAM-TEST-01', '2026-05-31', 'Jany Turkanda', 'test',
                       1000000, '2026-06-30', 'AGRI', 'beasiswa', 'open', '2026-05-31T00:00:00')"""
        )
        conn.commit()
        conn.close()

        migrate(db_path, skip_backup=True)

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT due_date FROM pam_records WHERE pam_no='PAM-TEST-01'").fetchone()
        conn.close()
        assert row[0] == "2026-06-11"
    finally:
        config.DB_PATH = old_db_path

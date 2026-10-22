import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(os.path.dirname(base_dir), "scripts")
sys.path.insert(0, scripts_dir)

from database import get_conn
from migrate_pam_due_dates import migrate


# Postgres: DB test di-reset oleh fixture autouse conftest.clean_db; skrip memakai database.get_conn().
def test_migration_updates_stale_due_dates():
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, requestors_name, keterangan,
            total_amount, due_date, pillar, source, status, created_at)
           VALUES (2, 'PAM-TEST-01', '2026-05-31', 'Jany Turkanda', 'test',
                   1000000, '2026-06-30', 'AGRI', 'beasiswa', 'open', '2026-05-31T00:00:00')"""
    )
    conn.close()

    migrate(skip_backup=True)

    conn = get_conn()
    row = conn.execute("SELECT due_date FROM pam_records WHERE pam_no='PAM-TEST-01'").fetchone()
    conn.close()
    assert row[0] == "2026-06-11"

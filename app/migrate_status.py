#!/usr/bin/env python3
"""
migrate_status.py — Standardize all status values to open/on_process/complete.
Run from the project root: python app/migrate_status.py
"""
import os
import shutil
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "finance_hub.db")


def main():
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{DB_PATH}.bak_status_{ts}"
    shutil.copy2(DB_PATH, backup)
    print(f"Backup: {backup}")

    migrations = [
        # payment_beasiswa
        "UPDATE payment_beasiswa SET status='open'       WHERE status='draft'",
        "UPDATE payment_beasiswa SET status='on_process' WHERE status='in_memo'",
        "UPDATE payment_beasiswa SET status='on_process' WHERE status='approved'",
        "UPDATE payment_beasiswa SET status='complete'   WHERE status='paid'",
        # payment_memo
        "UPDATE payment_memo SET status='open'       WHERE status='draft'",
        "UPDATE payment_memo SET status='on_process' WHERE status='approved'",
        "UPDATE payment_memo SET status='complete'   WHERE status='paid'",
        # pam_records
        "UPDATE pam_records SET status='open'       WHERE status='draft'",
        "UPDATE pam_records SET status='on_process' WHERE status='approved'",
        "UPDATE pam_records SET status='complete'   WHERE status='paid'",
        # payment_application
        "UPDATE payment_application SET status='open'     WHERE status='pending'",
        "UPDATE payment_application SET status='complete' WHERE status='completed'",
    ]

    conn = sqlite3.connect(DB_PATH)
    try:
        for sql in migrations:
            cur = conn.execute(sql)
            print(f"  {cur.rowcount:4d} rows — {sql}")
        conn.commit()
        print("\nDone.")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}\nRolled back. Restore from {backup} if needed.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

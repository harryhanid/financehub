import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(base_dir, "app")
sys.path.insert(0, app_dir)

from modules.payment_memo.service import _workday


def migrate(db_path: str, skip_backup: bool) -> None:
    if not skip_backup:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.bak_before_due_date_migration_{ts}"
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, pam_date, due_date FROM pam_records").fetchall()

    updated = 0
    unchanged = 0
    for pam_id, pam_date, old_due_date in rows:
        try:
            new_due_date = _workday(pam_date, 8).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Skipping pam_records.id={pam_id}: could not compute due_date from pam_date={pam_date!r} ({e})")
            continue
        if new_due_date != old_due_date:
            conn.execute("UPDATE pam_records SET due_date = ? WHERE id = ?", (new_due_date, pam_id))
            updated += 1
        else:
            unchanged += 1
    conn.commit()
    conn.close()

    print(f"Migration complete: {updated} row(s) updated, {unchanged} row(s) already correct.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=None, help="Override the database path (defaults to config.DB_PATH)")
    parser.add_argument("--skip-backup", action="store_true", help="Skip creating a .bak copy first (used by tests)")
    args = parser.parse_args()

    if args.db_path:
        db_path = args.db_path
    else:
        import config
        db_path = config.DB_PATH

    migrate(db_path, args.skip_backup)

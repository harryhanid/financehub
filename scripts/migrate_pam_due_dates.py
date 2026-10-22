import argparse
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(base_dir, "app")
sys.path.insert(0, app_dir)

from modules.payment_memo.service import _workday


def migrate(skip_backup: bool = False) -> None:
    """Hitung ulang pam_records.due_date = WORKDAY(pam_date, 8) di DB aplikasi (database.get_conn).

    Postgres (migrasi Supabase): DB bukan lagi file SQLite, jadi salinan `.bak` file tidak berlaku;
    backup dilakukan lewat backup Supabase/flow_backup sebelum menjalankan skrip ini. Semua UPDATE
    dikirim sebagai satu panggilan atomik (executemany): semua baris berubah atau tidak sama sekali.
    """
    from database import get_conn

    if not skip_backup:
        print("Catatan: DB Postgres -- pastikan backup DB sudah dibuat sebelum migrasi ini.")

    conn = get_conn()
    rows = conn.execute("SELECT id, pam_date, due_date FROM pam_records ORDER BY id").fetchall()

    updates = []
    unchanged = 0
    for pam_id, pam_date, old_due_date in rows:
        try:
            new_due_date = _workday(pam_date, 8).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Skipping pam_records.id={pam_id}: could not compute due_date from pam_date={pam_date!r} ({e})")
            continue
        if new_due_date != old_due_date:
            updates.append((new_due_date, pam_id))
        else:
            unchanged += 1
    if updates:
        conn.executemany("UPDATE pam_records SET due_date = ? WHERE id = ?", updates)
    conn.close()

    print(f"Migration complete: {len(updates)} row(s) updated, {unchanged} row(s) already correct.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-backup", action="store_true", help="Skip the backup reminder (used by tests)")
    args = parser.parse_args()

    migrate(args.skip_backup)

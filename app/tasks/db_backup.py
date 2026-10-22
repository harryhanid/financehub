"""Backup harian isi database FinanceHub (Supabase) ke drive Y: (job APScheduler "db_backup", 18:00).

Isi `<dest_root>/YYYY-MM-DD/`:
- `<tabel>.jsonl.gz`: satu baris JSON (list nilai sesuai `columns` di manifest) per baris tabel, urut
  primary key (lihat fhdb.paging; dibaca per 5.000 baris, lebih kecil untuk tabel lebar);
- `manifest.json`: `{tabel: {"columns": [...], "rows": n}}`;
- `0002_schema.sql`: salinan skema (template `{{schema}}`) untuk membangun ulang schema kosong.
Pulihkan dengan `scripts/pg_migrate/restore_backup.py`.

Dibaca lewat fhdb (backend dari config; produksi HTTPS). `refresh_tokens` tidak di-backup (token sesi;
restore ikut mengosongkannya lewat CASCADE). Isinya data bisnis (termasuk users.password_hash bcrypt),
tidak ada rahasia konfigurasi. Folder ditulis dulu sebagai `.YYYY-MM-DD.partial` lalu di-rename, jadi
folder bertanggal selalu lengkap. Retensi (folder bertanggal > keep_days hari) hanya dijalankan setelah
backup berhasil. Halaman-halaman tidak satu transaksi: snapshot tidak konsisten antar tabel kalau ada
tulisan selama backup (jadwal 18:00 dipilih karena sepi).
"""
import datetime
import gzip
import json
import logging
import os
import re
import shutil

import config
import fhdb
from fhdb import paging

PAGE_ROWS = paging.PAGE_ROWS
SKIP_TABLES = ("refresh_tokens",)
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "db_migrations", "0002_schema.sql")
_DATE_DIR = re.compile(r"\d{4}-\d{2}-\d{2}")

logger = logging.getLogger(__name__)


def _today() -> datetime.date:
    return datetime.date.today()


def _cleanup_old_folders(root: str, keep_days: int, today: datetime.date) -> list[str]:
    """Hapus sub-folder langsung `root` bernama YYYY-MM-DD yang lebih tua dari keep_days hari.
    File, symlink, dan folder dengan nama lain tidak pernah disentuh."""
    removed = []
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not _DATE_DIR.fullmatch(name) or os.path.islink(full) or not os.path.isdir(full):
            continue
        try:
            d = datetime.datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (today - d).days > keep_days:
            shutil.rmtree(full)
            removed.append(name)
    return removed


def _dump(conn, out_dir: str) -> dict:
    """Tulis semua tabel schema aktif ke out_dir; kembalikan manifest."""
    schema = config.DB_SCHEMA

    def run(sql, params):
        return [list(r) for r in conn.execute(sql, params).fetchall()]

    tables = paging.table_columns(run, schema)
    pks = paging.primary_keys(run, schema)
    manifest = {}
    for table in sorted(tables):
        if table in SKIP_TABLES:
            continue
        cols = [c for c, _ in tables[table]]
        n = 0
        with gzip.open(os.path.join(out_dir, f"{table}.jsonl.gz"), "wt", encoding="utf-8", newline="\n") as f:
            for row in paging.iter_rows(run, table, cols, pks.get(table, []), cols, PAGE_ROWS):
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
                f.write("\n")
                n += 1
        manifest[table] = {"columns": cols, "rows": n}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    shutil.copyfile(SCHEMA_FILE, os.path.join(out_dir, "0002_schema.sql"))
    return manifest


def run_db_backup(dest_root: str | None = None, keep_days: int = 30) -> str:
    """Backup semua tabel ke `<dest_root>/YYYY-MM-DD/` (default config.DB_BACKUP_ROOT); path folder.
    Backup ulang di hari yang sama menggantikan folder hari itu."""
    root = dest_root if dest_root is not None else config.DB_BACKUP_ROOT
    os.makedirs(root, exist_ok=True)
    today = _today()
    name = today.isoformat()
    final = os.path.join(root, name)
    partial = os.path.join(root, f".{name}.partial")
    old = os.path.join(root, f".{name}.old")
    for leftover in (partial, old):
        shutil.rmtree(leftover, ignore_errors=True)
    os.makedirs(partial)
    try:
        conn = fhdb.get_conn()
        try:
            manifest = _dump(conn, partial)
        finally:
            conn.close()
        if os.path.exists(final):
            os.rename(final, old)  # Windows: rename tidak bisa menimpa folder
        os.rename(partial, final)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        if os.path.exists(old) and not os.path.exists(final):
            os.rename(old, final)
        raise
    shutil.rmtree(old, ignore_errors=True)
    removed = _cleanup_old_folders(root, keep_days, today)
    logger.info("db_backup: %d tabel, %d baris -> %s (dihapus: %s)", len(manifest),
                sum(m["rows"] for m in manifest.values()), final, ", ".join(removed) or "-")
    return final


def scheduled_db_backup():
    """Pembungkus job APScheduler: tidak pernah melempar exception (scheduler tetap hidup)."""
    try:
        return run_db_backup()
    except fhdb.OperationalError as e:
        logger.warning("db_backup dilewati, database tidak terjangkau: %s", e)
    except Exception:
        logger.exception("db_backup gagal")
    return None

"""Backup harian isi database FinanceHub (Supabase) ke drive Y: (job APScheduler "db_backup", 18:00).

Isi `<dest_root>/YYYY-MM-DD/`:
- `<tabel>.jsonl.gz`: satu baris JSON (list nilai sesuai `columns` di manifest) per baris tabel, urut
  primary key (lihat fhdb.paging; dibaca per 5.000 baris, lebih kecil untuk tabel lebar);
- `manifest.json`: `{tabel: {"columns": [...], "rows": n}}`;
- `0002_schema.sql`: salinan skema (template `{{schema}}`) untuk membangun ulang schema kosong.
Pulihkan dengan `scripts/pg_migrate/restore_backup.py`.

Dibaca lewat fhdb (backend dari config; produksi HTTPS). `refresh_tokens` dan tabel staging `fh_stage_*`
(sementara, UNLOGGED) tidak di-backup (token sesi;
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
from modules.general_ledger import staging

PAGE_ROWS = paging.PAGE_ROWS
SKIP_TABLES = ("refresh_tokens",)
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "db_migrations", "0002_schema.sql")
_DATE_DIR = re.compile(r"\d{4}-\d{2}-\d{2}")

logger = logging.getLogger(__name__)


def _today() -> datetime.date:
    return datetime.date.today()


_STALE_DIR = re.compile(r"\.(\d{4}-\d{2}-\d{2})\.(partial|old)")


def _parse_date(text: str):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _recover_today(root: str, today: datetime.date) -> bool:
    """Kalau folder hari ini hilang tapi `.<today>.old` ada (proses mati di antara dua rename),
    kembalikan `.old` menjadi folder hari ini."""
    name = today.isoformat()
    final, old = os.path.join(root, name), os.path.join(root, f".{name}.old")
    if not os.path.lexists(final) and os.path.isdir(old) and not os.path.islink(old):
        os.rename(old, final)
        return True
    return False


def _cleanup_stale(root: str, today: datetime.date) -> None:
    """Hapus `.<tanggal>.partial` / `.<tanggal>.old` untuk tanggal SEBELUM hari ini. `.old` yang folder
    bertanggalnya hilang dikembalikan (bukan dihapus). Nama lain tidak pernah disentuh."""
    for name in sorted(os.listdir(root)):
        m = _STALE_DIR.fullmatch(name)
        full = os.path.join(root, name)
        if not m or os.path.islink(full) or not os.path.isdir(full):
            continue
        d = _parse_date(m.group(1))
        if d is None or d >= today:
            continue
        if m.group(2) == "old" and not os.path.lexists(os.path.join(root, m.group(1))):
            os.rename(full, os.path.join(root, m.group(1)))
        else:
            shutil.rmtree(full, ignore_errors=True)


def _cleanup_old_folders(root: str, keep_days: int, today: datetime.date) -> list[str]:
    """Bersihkan sisa `.partial`/`.old` basi, lalu hapus sub-folder langsung `root` bernama YYYY-MM-DD
    yang lebih tua dari keep_days hari. File, symlink, dan folder dengan nama lain tidak pernah disentuh."""
    _cleanup_stale(root, today)
    removed = []
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not _DATE_DIR.fullmatch(name) or os.path.islink(full) or not os.path.isdir(full):
            continue
        d = _parse_date(name)
        if d is None:
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
        # fh_stage_*: tabel UNLOGGED sementara milik run GL/SPT yang sedang jalan (bisa di-drop kapan saja)
        if table in SKIP_TABLES or table.startswith(staging.PREFIX):
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
    _recover_today(root, today)
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
    logger.debug("db_backup: %d tabel, %d baris -> %s (dihapus: %s)", len(manifest),
                sum(m["rows"] for m in manifest.values()), final, ", ".join(removed) or "-")
    return final


def job_logger() -> logging.Logger:
    """Logger job backup yang pasti punya handler (logger modul tidak: app tidak mengonfigurasi root)."""
    lg = logging.getLogger("financehub.db_backup")
    lg.setLevel(logging.INFO)
    if not lg.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        lg.addHandler(h)
    return lg


def scheduled_db_backup(log: logging.Logger | None = None):
    """Pembungkus job APScheduler: tidak pernah melempar exception (scheduler tetap hidup).
    Baris sukses ("N tabel, N baris -> path") dikirim lewat `log` (default job_logger())."""
    log = log or job_logger()
    try:
        path = run_db_backup()
        with open(os.path.join(path, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        log.info("db_backup: %d tabel, %d baris -> %s", len(manifest),
                 sum(m["rows"] for m in manifest.values()), path)
        return path
    except fhdb.OperationalError as e:
        log.warning("db_backup dilewati, database tidak terjangkau: %s", e)
    except Exception:
        log.exception("db_backup gagal")
    return None


def register_db_backup_job(scheduler) -> None:
    """Daftarkan job harian 18:00. misfire_grace_time 1 jam + coalesce: PC tidur/sibuk jam 18:00 tetap
    menjalankan backup sekali dalam satu jam."""
    scheduler.add_job(func=scheduled_db_backup, trigger="cron", id="db_backup",
                      day_of_week="mon-sun", hour=18, minute=0,
                      misfire_grace_time=3600, coalesce=True, replace_existing=True)

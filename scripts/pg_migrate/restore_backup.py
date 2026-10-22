"""Pulihkan backup harian (app/tasks/db_backup.py) ke schema Postgres FinanceHub, lalu verifikasi.

Usage:
  python scripts/pg_migrate/restore_backup.py --folder "Y:/Seagate/Flow/db-backup/2026-10-22" \\
      --backend pg --dsn postgresql://postgres@127.0.0.1:54340/postgres --schema financehub_test
  python scripts/pg_migrate/restore_backup.py --folder ... --backend http --schema financehub --confirm-production

Schema target harus sudah punya skema (app/db_migrations, lewat apply_migrations.py; folder backup
membawa salinan 0002_schema.sql). Jalur tulis sama dengan load_data.py: semua INSERT dibangun dan
divalidasi dulu (tabel/kolom ada di target, nilai bisa dikonversi tanpa rugi, jumlah baris = manifest),
baru TRUNCATE <tabel backup> RESTART IDENTITY CASCADE -> INSERT per chunk (induk dulu) -> setval.
Tidak satu transaksi: kalau gagal di tengah, jalankan ulang. CASCADE ikut mengosongkan refresh_tokens.

Schema produksi `financehub` ditolak kecuali --confirm-production. Setelah restore, CLI menjalankan
verify_against_manifest (jumlah baris + jumlah tiap kolom numerik, sama seperti verify.py); exit 1 kalau
ada mismatch.
"""
import argparse
import gzip
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import load_data  # noqa: E402
import verify as verify_mod  # noqa: E402
from load_data import (ALLOWED_SCHEMAS, check_schema, check_write_schema, insert_order,  # noqa: E402
                       refuse_production_cli, rows_to_inserts, target_columns, target_fks, write_tables)


def read_manifest(folder) -> dict:
    with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def iter_backup_rows(folder, table):
    with gzip.open(os.path.join(folder, f"{table}.jsonl.gz"), "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def restore(folder: str, backend, schema: str, chunk: int = 500, log=None,
            confirm_production: bool = False) -> dict[str, int]:
    """Timpa isi tabel-tabel di manifest dengan isi backup; {tabel: jumlah baris}."""
    check_write_schema(schema, confirm_production)
    log = log or (lambda msg: None)
    manifest = read_manifest(folder)
    tables = sorted(manifest)
    tcols = target_columns(backend, schema)
    missing = [t for t in tables if t not in tcols]
    if missing:
        raise ValueError(f"tabel backup tidak ada di schema {schema}: {missing}")
    not_in_backup = sorted(set(tcols) - set(tables) - set(load_data.SKIP_TABLES))
    if not_in_backup:
        log(f"PERINGATAN: tabel target tanpa data backup (tidak disentuh kecuali lewat CASCADE): {not_in_backup}")
    fks = target_fks(backend, schema)
    plan, counts = [], {}
    for t in insert_order(tables, fks):
        cols = manifest[t]["columns"]
        extra = [c for c in cols if c not in tcols[t]]
        if extra:
            raise ValueError(f"kolom backup {t}.{extra} tidak ada di target")
        stmts, n = rows_to_inserts(t, cols, [tcols[t][c][0] for c in cols], iter_backup_rows(folder, t), chunk)
        if n != manifest[t]["rows"]:
            raise ValueError(f"{t}: file berisi {n} baris, manifest {manifest[t]['rows']} -- backup rusak")
        plan.append((t, stmts))
        counts[t] = n
    write_tables(backend, schema, tables, plan, counts, tcols, log)
    return counts


def verify_against_manifest(folder: str, backend, schema: str) -> list:
    """Bandingkan schema dengan backup: jumlah baris per tabel + jumlah tiap kolom numerik (kolom yang
    sama dengan verify.py; fsum/int eksak, 2 desimal, zero tolerance). Kosong = lulus."""
    check_schema(schema)
    manifest = read_manifest(folder)
    tables = sorted(manifest)
    tcols = target_columns(backend, schema)
    num = verify_mod._numeric_cols([t for t in tables if t in tcols], tcols)
    by_table = {t: [c for tt, c in num if tt == t and c in manifest[t]["columns"]] for t in tables}
    expected, corrupt = {}, []
    for t in tables:
        cols = manifest[t]["columns"]
        idx = [cols.index(c) for c in by_table[t]]
        vals = [[] for _ in idx]
        n = 0
        for row in iter_backup_rows(folder, t):
            n += 1
            for k, i in enumerate(idx):
                vals[k].append(row[i])
        if n != manifest[t]["rows"]:  # file backup sendiri tidak cocok dengan manifest
            corrupt.append(verify_mod.Mismatch(t, "<file vs manifest>", n, manifest[t]["rows"]))
        sums = [verify_mod.sum_values(v, tcols[t][c][0]) for c, v in zip(by_table[t], vals)]
        expected[t] = (manifest[t]["rows"], sums)
    present = {t: by_table[t] for t in tables if t in tcols}
    return corrupt + verify_mod.compare(expected, verify_mod.pg_stats(backend, schema, present, tcols), by_table)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", required=True, help="folder backup YYYY-MM-DD (berisi manifest.json)")
    ap.add_argument("--schema", required=True, choices=ALLOWED_SCHEMAS)
    ap.add_argument("--backend", required=True, choices=("pg", "http"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""))
    ap.add_argument("--chunk", type=int, default=500)
    ap.add_argument("--confirm-production", action="store_true",
                    help="wajib untuk --schema financehub (menimpa database produksi)")
    args = ap.parse_args(argv)
    refuse_production_cli(args.schema, args.confirm_production)
    backend = load_data.make_backend(args.backend, args.dsn)
    t0 = time.perf_counter()
    try:
        counts = restore(args.folder, backend, args.schema, chunk=args.chunk, log=print,
                         confirm_production=args.confirm_production)
        print(f"Restore: {len(counts)} tabel, {sum(counts.values())} baris, {time.perf_counter() - t0:.1f} detik")
        mm = verify_against_manifest(args.folder, backend, args.schema)
    finally:
        backend.close()
    for m in mm:
        print(f"MISMATCH {m.table}.{m.column or '<rows>'}: backup={m.sqlite} db={m.pg}")
    print(f"{len(mm)} mismatch")
    sys.exit(1 if mm else 0)


if __name__ == "__main__":
    main()

"""Ukur alur tulis berat terhadap batas Supabase (statement_timeout 8 s per panggilan fh_exec), Task 21.

HANYA untuk schema `financehub_test` (salinan scratch; tulisan diizinkan). Mencatat tiap panggilan
fh_exec (jumlah statement, detik) dan melaporkan panggilan terlama per alur:
- GL replace_year: baris GL SMT tahun terbaru (salinan produksi, ~9k baris) ditulis ulang;
- MR save_upload: workbook .xlsb (sheet Append1) diparse lalu disimpan sebagai snapshot baru;
- SPT take_snapshot: periode SMT tahun GL terbaru (dibuat kalau belum ada) di-snapshot.

    timeout 900 python scripts/pg_migrate/measure_heavy_flows.py --only gl
    timeout 900 python scripts/pg_migrate/measure_heavy_flows.py --only mr --xlsb "C:/Users/.../Management Report - MASTER.xlsb"
    timeout 900 python scripts/pg_migrate/measure_heavy_flows.py --only spt
(jalankan per alur dengan `timeout` luar supaya satu alur yang macet tidak menahan yang lain).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.join(ROOT, "app")
SCHEMA = "financehub_test"

CALLS: list[tuple[int, float, str]] = []   # (jumlah statement, detik, awal statement pertama)


def setup():
    os.environ["DB_BACKEND"] = "http"
    os.environ["DB_SCHEMA"] = SCHEMA
    sys.path.insert(0, APP_DIR)
    os.chdir(APP_DIR)
    import config

    assert config.DB_SCHEMA == SCHEMA, config.DB_SCHEMA
    from fhdb import connection as fc

    orig = fc.Connection._send

    def timed(self, plans):
        assert self._schema == SCHEMA
        stmts = [p.stmt for p in plans if p.kind != "noop"]
        t0 = time.perf_counter()
        try:
            return orig(self, plans)
        finally:
            if stmts:
                CALLS.append((len(stmts), time.perf_counter() - t0, " ".join(stmts[-1].split())[:70]))

    fc.Connection._send = timed


def flow(name, fn):
    print(time.strftime("%H:%M:%S ") + f"mulai {name} ...", flush=True)
    CALLS.clear()
    t0 = time.perf_counter()
    info = fn()
    total = time.perf_counter() - t0
    longest = max(CALLS, key=lambda c: c[1]) if CALLS else (0, 0.0, "")
    print(f"\n== {name}: {info}")
    print(f"   total {total:.2f}s, {len(CALLS)} panggilan, terlama {longest[1]:.2f}s "
          f"({longest[0]} statement; ...{longest[2]})")
    for n, dt, head in sorted(CALLS, key=lambda c: -c[1])[:5]:
        print(f"     {dt:6.2f}s  n={n:3d}  {head}", flush=True)
    return {"flow": name, "info": info, "total": total, "calls": len(CALLS), "longest": longest[1],
            "longest_stmts": longest[0]}


def gl_replace_year():
    from modules.general_ledger import service

    year = service.latest_year("smt")
    rows = service.load_rows("smt", year)
    log = {"synced_by": "perf-task21", "filename": "perf.xlsx", "content_hash": "perf", "rows_before": len(rows),
           "rows_after": len(rows), "total_debit": 0.0, "total_credit": 0.0, "dropped": 0, "summary": {}}
    service.replace_year("smt", year, rows, log)
    return f"smt {year}, {len(rows)} baris"


def mr_save_upload(xlsb):
    def run():
        import io

        from modules.management_report import service
        from modules.management_report.parser import read_append1, read_meta

        with open(xlsb, "rb") as f:
            data = f.read()
        res = read_append1(io.BytesIO(data))
        meta = read_meta(io.BytesIO(data))
        uid = service.save_upload(1, os.path.basename(xlsb), "perf-task21", res.rows, meta=meta)
        return f"upload_id {uid}, {len(res.rows)} baris (total termasuk parse workbook)"
    return run


def spt_take_snapshot():
    from fhdb import get_conn
    from modules.general_ledger import service as gl
    from modules.spt_badan import service

    year = gl.latest_year("smt")
    row = get_conn().execute("SELECT id FROM spt_period WHERE entity='smt' AND tax_year=?", (year,)).fetchone()
    pid = row["id"] if row else service.create_period("smt", year, "perf-task21")
    sid = service.take_snapshot(pid, "perf-task21")
    return f"period {pid} (smt {year}), snapshot {sid}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsb", default=None)
    ap.add_argument("--only", choices=["gl", "mr", "spt"], action="append", default=[])
    args = ap.parse_args(argv)
    setup()
    todo = args.only or ["gl", "mr", "spt"]
    out = []
    if "gl" in todo:
        out.append(flow("GL replace_year", gl_replace_year))
    if "mr" in todo and args.xlsb:
        out.append(flow("MR save_upload", mr_save_upload(args.xlsb)))
    if "spt" in todo:
        out.append(flow("SPT take_snapshot", spt_take_snapshot))
    return out


if __name__ == "__main__":
    main()

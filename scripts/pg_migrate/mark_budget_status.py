"""Penandaan awal status budget beasiswa (budget_beasiswa.status) dari payment & baris PA yang sudah ada.

Usage (laporan saja, tanpa menulis):
  python scripts/pg_migrate/mark_budget_status.py --schema financehub_staging --backend http --report staging.xlsx
Tulis (produksi wajib --confirm-production):
  python scripts/pg_migrate/mark_budget_status.py --schema financehub --backend http --report prod.xlsx \\
      --write --confirm-production

Algoritme per kunci (siswa_code, cat1, cat2), budget urut id (company ETF):
  1. pasangkan dengan payment_beasiswa urut id: status 'complete' -> complete, lainnya -> on_progress
     (payment 'rejected' tidak dihitung, konsisten dengan service.py yang mengabaikannya);
  2. sisa budget dipasangkan dengan baris *_pa_lines dari PA berstatus open/on_process yang belum punya
     payment dan belum ber-budget_id (siswa via siswa.id, cat1 = jenis_pembayaran, cat2 = semester)
     -> on_progress + isi budget_id baris itu;
  3. sisanya tetap open.
Tautan payment ke baris PA: payment_beasiswa.etf_pa_line_id adalah id baris di tabel yang ditunjuk
payment_beasiswa.pillar (AGRI/APP/LAND/ENERGY/SETF -> etf/app/sml/energy/setf_pa_lines; id per tabel
bisa kembar, lihat payment_memo/service.py _PILLAR_PA_TBL). Payment tanpa pillar dikenali dianggap
menutup baris berid itu di SEMUA tabel (konservatif: baris tidak ditandai dobel).
Idempoten: budget yang sudah bukan open tidak diubah (tetapi tetap "memakai" jatah payment urutannya,
kecuali sudah ditunjuk baris PA lewat budget_id), baris PA yang sudah ber-budget_id tidak dipakai lagi.
Penulisan = SATU execute_batch (satu transaksi); setiap UPDATE dijaga status='open' / budget_id is null.
Laporan .xlsx selalu dibuat. Tidak mencetak kredensial; backend http memakai app/.env seperti prportal_key.py.
"""
import argparse
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fhdb.sqlbind import bind  # noqa: E402

ALLOWED_SCHEMAS = ("financehub", "financehub_staging", "financehub_test")
PRODUCTION_SCHEMA = "financehub"

# Urutan tabel dipakai untuk urutan pemasangan baris PA yang deterministik.
PA_TABLES = (("etf_pa", "etf_pa_lines"), ("app_pa", "app_pa_lines"), ("sml_pa", "sml_pa_lines"),
             ("energy_pa", "energy_pa_lines"), ("setf_pa", "setf_pa_lines"))
_LINES_ORDER = {lines: i for i, (_, lines) in enumerate(PA_TABLES)}
_PILLAR_LINES = {"AGRI": "etf_pa_lines", "APP": "app_pa_lines", "LAND": "sml_pa_lines",
                 "ENERGY": "energy_pa_lines", "SETF": "setf_pa_lines"}
_LINES_SET = set(_LINES_ORDER)
OPEN_PA_STATUS = ("open", "on_process")
REPORT_HEADER = ["Kode", "Nama", "Kategori 1", "Kategori 2", "Amount", "Status Hasil", "Dasar", "Referensi"]


def _key(row):
    return (str(row.get("siswa_code") or "").strip(), str(row.get("cat1") or "").strip(),
            str(row.get("cat2") or "").strip())


def plan_marking(budgets, payments, pa_lines, siswa_status):
    """Murni: kembalikan satu hasil per budget yang MASIH 'open' (urut id)."""
    pays = {}
    for p in sorted(payments, key=lambda x: x["id"]):
        if str(p.get("status") or "").lower() == "rejected":
            continue
        pays.setdefault(_key(p), []).append(p)

    # baris PA yang sudah punya payment (per tabel dari pillar; pillar tak dikenal = semua tabel)
    paid = set()
    for p in payments:
        lid = p.get("etf_pa_line_id")
        if not lid or str(p.get("status") or "").lower() == "rejected":
            continue
        tbl = _PILLAR_LINES.get(str(p.get("pillar") or "").upper())
        for t in ([tbl] if tbl else _LINES_SET):
            paid.add((t, int(lid)))

    referenced = {int(l["budget_id"]) for l in pa_lines if l.get("budget_id")}
    free_lines = {}
    for l in sorted(pa_lines, key=lambda x: (_LINES_ORDER.get(x["table"], 99), x["line_id"])):
        if str(l.get("pa_status") or "").lower() not in OPEN_PA_STATUS:
            continue
        if l.get("budget_id") or (l["table"], int(l["line_id"])) in paid:
            continue
        free_lines.setdefault(_key(l), []).append(l)

    by_key = {}
    for b in sorted(budgets, key=lambda x: x["id"]):
        by_key.setdefault(_key(b), []).append(b)

    out = []
    for key, blist in by_key.items():
        plist = pays.get(key, [])
        flist = list(free_lines.get(key, []))
        ptr = 0
        for b in blist:
            if str(b.get("status") or "open") != "open":
                if b["id"] not in referenced and ptr < len(plist):
                    ptr += 1  # budget yang sudah ditandai memakai jatah payment urutannya
                continue
            res = {"budget_id": b["id"], "siswa_code": key[0], "cat1": key[1], "cat2": key[2],
                   "amount": b.get("amount"), "status": "open", "match_type": "none", "match_ref": ""}
            if ptr < len(plist):
                p = plist[ptr]
                ptr += 1
                done = str(p.get("status") or "").lower() == "complete"
                res.update(status="complete" if done else "on_progress",
                           match_type="payment_complete" if done else "payment_open",
                           match_ref=f"payment:{p['id']}")
            elif flist:
                l = flist.pop(0)
                res.update(status="on_progress", match_type="pa_line",
                           match_ref=f"{l['table']}:{l['line_id']}")
            elif siswa_status.get(key[0], "Aktif") != "Aktif":
                res["match_type"] = "siswa_non_aktif"
            out.append(res)
    out.sort(key=lambda r: r["budget_id"])
    return out


def changes(results):
    return [r for r in results if r["status"] != "open"]


def write_changes(backend, schema, results):
    """Satu execute_batch; kembalikan jumlah budget yang ditandai."""
    stmts, n = [], 0
    for r in changes(results):
        n += 1
        stmts.append(bind("update budget_beasiswa set status = ? where id = ? and status = 'open'",
                          (r["status"], r["budget_id"])))
        if r["match_type"] == "pa_line":
            tbl, lid = r["match_ref"].split(":")
            if tbl not in _LINES_SET:
                raise ValueError(f"tabel baris PA tidak dikenal: {tbl!r}")
            stmts.append(bind(f"update {tbl} set budget_id = ? where id = ? and budget_id is null",
                              (r["budget_id"], int(lid))))
    if stmts:
        backend.execute_batch(stmts, schema)
    return n


def write_report(path, results, names):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Penandaan Budget"
    ws.append(REPORT_HEADER)
    for r in results:
        ws.append([r["siswa_code"], names.get(r["siswa_code"], ""), r["cat1"], r["cat2"], r["amount"],
                   r["status"], r["match_type"], r["match_ref"]])
    wb.save(path)


def _rows(res):
    return [dict(zip(res["columns"], row)) for row in res.get("rows", [])]


def load_inputs(backend, schema):
    """Baca budgets, payments, pa_lines, siswa (status, nama) company ETF."""
    etf = "(select id from companies where code = 'ETF')"
    sqls = [
        f"select id, siswa_code, cat1, cat2, amount, status from budget_beasiswa where company_id = {etf} order by id",
        f"select id, siswa_code, cat1, cat2, status, etf_pa_line_id, pillar from payment_beasiswa"
        f" where company_id = {etf} order by id",
        f"select code, nama, status from siswa where company_id = {etf}",
    ]
    for pa, lines in PA_TABLES:
        sqls.append(
            f"select '{lines}' as \"table\", l.id as line_id, s.code as siswa_code, l.jenis_pembayaran as cat1,"
            f" l.semester as cat2, l.budget_id, p.status as pa_status, p.pa_number"
            f" from {lines} l join {pa} p on p.id = l.pa_id join siswa s on s.id = l.student_id"
            f" where p.company_id = {etf} and lower(p.status) in ('open', 'on_process')")
    results = backend.execute_batch(sqls, schema)
    budgets, payments, siswa = _rows(results[0]), _rows(results[1]), _rows(results[2])
    pa_lines = [r for res in results[3:] for r in _rows(res)]
    status = {s["code"]: s["status"] for s in siswa}
    names = {s["code"]: s["nama"] for s in siswa}
    return budgets, payments, pa_lines, status, names


def _make_backend(args, ap):
    from fhdb.backends import HttpBackend, PgBackend

    if args.backend == "pg":
        if not args.dsn:
            ap.error("--dsn (atau env FH_PG_DSN) wajib untuk backend pg")
        return PgBackend(args.dsn)
    from dotenv import load_dotenv

    load_dotenv(APP_DIR / ".env")
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY belum di-set (app/.env)")
    return HttpBackend(url, key, timeout=120.0)


def main(argv=None, backend=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", required=True, choices=ALLOWED_SCHEMAS)
    ap.add_argument("--backend", default="http", choices=("http", "pg"))
    ap.add_argument("--dsn", default=os.environ.get("FH_PG_DSN", ""), help="backend pg (default: env FH_PG_DSN)")
    ap.add_argument("--report", required=True, metavar="PATH.xlsx", help="laporan hasil (selalu dibuat)")
    ap.add_argument("--write", action="store_true", help="tulis status + budget_id (tanpa ini hanya laporan)")
    ap.add_argument("--confirm-production", action="store_true",
                    help=f"wajib untuk --write ke schema {PRODUCTION_SCHEMA}")
    args = ap.parse_args(argv)

    if args.write and args.schema == PRODUCTION_SCHEMA and not args.confirm_production:
        print(f"DITOLAK: --write ke schema {PRODUCTION_SCHEMA!r} (PRODUKSI) butuh --confirm-production.",
              file=sys.stderr)
        sys.exit(2)

    if backend is None:
        backend = _make_backend(args, ap)
    try:
        budgets, payments, pa_lines, status, names = load_inputs(backend, args.schema)
        results = plan_marking(budgets, payments, pa_lines, status)
        write_report(args.report, results, names)
        counts = {}
        for r in results:
            counts[r["match_type"]] = counts.get(r["match_type"], 0) + 1
        print(f"Budget open dinilai: {len(results)}; akan ditandai: {len(changes(results))}; rincian: {counts}")
        print(f"Laporan: {args.report}")
        if args.write:
            n = write_changes(backend, args.schema, results)
            print(f"Ditulis: {n} budget (satu transaksi) ke schema {args.schema}.")
        else:
            print("Mode laporan saja: tidak ada yang ditulis (pakai --write untuk menulis).")
    finally:
        backend.close()


if __name__ == "__main__":
    main()

"""Ukur waktu server per route GET FinanceHub terhadap Supabase (Task 21).

Cara kerja (keputusan Task 21):
- App dijalankan in-process (Flask test client) dengan DB_BACKEND=http dan DB_SCHEMA=<schema>,
  jadi lalu lintas DB tetap lewat HTTPS ke Supabase; waktu rendering browser TIDAK termasuk.
- Tidak login dengan password: access token dibuat di app context untuk identitas user `admin`
  dengan klaim yang sama seperti auth.routes.login (username, role).
- Company dipilih lewat session_transaction (tanpa POST).
- READ-ONLY: selain schema financehub_test, setiap statement tulis (INSERT/UPDATE/DELETE/DDL,
  fungsi fn_*, nextval/setval) ditolak sebelum dikirim; route yang mencoba menulis dicatat "skip(write)".
- Tiap route dijalankan 2x; hasil ke-2 (warm) yang dilaporkan.

Pemakaian (dari root repo):
    python scripts/pg_migrate/measure_pages.py --schema financehub_staging --out docs/pg-migration/performance.md
    python scripts/pg_migrate/measure_pages.py --only /dashboard --only /general-ledger/smt

`measure(base_url, routes, session_cookie)` juga bisa memakai server yang sedang berjalan
(base_url = "http://127.0.0.1:8082", session_cookie = header Cookie berisi fh_access dan session);
jumlah panggilan diambil dari header X-FH-DB-Calls (perlu DB_STATS_HEADER=1 di server).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.join(ROOT, "app")

TARGET_NORMAL = 2.0
TARGET_HEAVY = 5.0

# Route dengan parameter URL: id/kode nyata dari staging (diambil 2026-10-23).
CURATED = [
    ("/beasiswa/siswa/4240012", "ETF"),
    ("/beasiswa/siswa/4240012/sisa-budget", "ETF"),
    ("/beasiswa/budget/siswa/4240012", "ETF"),
    ("/beasiswa/budget/siswa/4240012/export/xlsx", "ETF"),
    ("/beasiswa/laporan/siswa/4240012", "ETF"),
    ("/beasiswa/laporan/siswa/4240012/export/xlsx", "ETF"),
    ("/beasiswa/sahabat/api/detail/4240012", "ETF"),
    ("/api/v1/siswa/4240012", "ETF"),
    ("/budget/master/B26-9-9-9", "SMT"),
    ("/budget/export/transactions", "SMT"),
    ("/budget/export/realization", "SMT"),
    ("/budget/export/department", "SMT"),
    ("/budget/export/expired", "SMT"),
    ("/budget/export/compliance", "SMT"),
    ("/etf-payment-application/2476/header", "ETF"),
    ("/etf-payment-application/2476/lines", "ETF"),
    ("/payment-memo/940", "ETF"),
    ("/payment-memo/940/export/pdf", "ETF"),
    ("/payment-memo/pam/940/detail", "ETF"),
    ("/payment-memo/pam/940/beasiswa-lines", "ETF"),
    ("/payment-memo/pam/940/transaction-lines", "ETF"),
    ("/payment-memo/pam/940/export/excel", "ETF"),
    ("/payment-memo/pam/940/export/pdf", "ETF"),
    ("/payment-memo/by-pillar/Pendidikan", "ETF"),
    ("/payment-memo/fiori/103/detail", "SMT"),
    ("/sop/65", "SMT"),
    ("/sponsorship/data/3267", "SMT"),
    ("/general-ledger/smt", "SMT"),
    ("/general-ledger/etf", "SMT"),
    ("/general-ledger/setf", "SMT"),
    ("/management-report/table?yy=2026", "SMT"),
    ("/management-report/export-all", "ETF"),
]

# Route tanpa parameter yang tidak diukur, dengan alasan (ikut ditulis ke performance.md).
# Modul backup = file browser atas drive lokal/jaringan (modules/backup/service.py BACKUP_ROOT "D:\\");
# di laptop luar kantor drive itu tidak ada / tidak terjangkau dan akses ke drive jaringan bisa memblok.
EXCLUDE = {
    "/": "redirect ke /auth/login (bukan halaman)",
    "/backup/": "not measured: drive-dependent (file browser drive D:)",
    "/backup/download": "not measured: drive-dependent (unduh file dari drive D:)",
}

ROUTE_TIMEOUT = 60.0   # detik per route (2 run) sebelum worker dimatikan dan route dicatat TIMEOUT

HEAVY_PREFIX = ("/dashboard", "/management-report", "/general-ledger")


def is_heavy(route: str) -> bool:
    path = route.split("?")[0]
    return path.startswith(HEAVY_PREFIX) or bool(re.search(r"export|\.xlsx|/download", path))


# ------------------------------------------------------------------- read-only guard

_FORBIDDEN = re.compile(r"\b(fn_[a-z_]+|nextval|setval|pg_advisory\w*|set_config)\s*\(", re.IGNORECASE)


class WriteBlocked(RuntimeError):
    pass


BLOCKED: list[str] = []   # statement tulis yang ditolak guard selama request terakhir


def install_read_only_guard():
    """Tolak semua tulisan sebelum dikirim ke backend (dipakai untuk schema selain financehub_test)."""
    from fhdb import connection as fc

    orig = fc.Connection._send

    def guarded(self, plans):
        for p in plans:
            if p.kind == "noop":
                continue
            if p.is_write or _FORBIDDEN.search(fc._code_text(p.stmt)):
                BLOCKED.append((p.stmt or "")[:120])
                raise WriteBlocked(BLOCKED[-1])
        return orig(self, plans)

    fc.Connection._send = guarded


# ------------------------------------------------------------------- app setup

def make_app(schema: str):
    os.environ["DB_BACKEND"] = "http"
    os.environ["DB_SCHEMA"] = schema
    os.environ["DB_STATS_HEADER"] = "1"
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
    os.chdir(APP_DIR)
    import config  # noqa: F401  (memuat .env; env di atas menang karena load_dotenv tidak override)
    from app import create_app

    app = create_app(testing=True)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    if schema != "financehub_test":
        install_read_only_guard()
    return app


def admin_token(app) -> str:
    """Access token untuk user admin, klaim sama dengan auth.routes.login."""
    from flask_jwt_extended import create_access_token
    from fhdb import get_conn

    with app.app_context():
        row = get_conn().execute("SELECT id, username, role FROM users WHERE username = 'admin'").fetchone()
        return create_access_token(identity=str(row["id"]),
                                   additional_claims={"username": row["username"], "role": row["role"]})


def discover_routes(app) -> list[str]:
    out = []
    for r in app.url_map.iter_rules():
        if "GET" not in r.methods or r.arguments or r.rule.startswith("/static") or r.rule in EXCLUDE:
            continue
        out.append(r.rule)
    return sorted(set(out))


# ------------------------------------------------------------------- measuring

class InProcess:
    def __init__(self, app, token: str):
        self.app = app
        self.client = app.test_client()
        self.headers = {"Authorization": f"Bearer {token}"}
        self.company = None

    def set_company(self, code: str):
        import config

        c = next(c for c in config.COMPANIES if c["code"] == code)
        with self.client.session_transaction() as s:
            s["company_id"], s["company_code"], s["company_name"] = c["id"], c["code"], c["name"]
        self.company = code

    def get(self, route: str):
        import fhdb

        fhdb.reset_stats()
        BLOCKED.clear()
        t0 = time.perf_counter()
        resp = self.client.get(route, headers=self.headers)
        body = resp.get_data()
        dt = time.perf_counter() - t0
        if BLOCKED:
            raise WriteBlocked(BLOCKED[0])
        return {"status": resp.status_code, "seconds": dt, "calls": fhdb.stats.calls,
                "db_seconds": fhdb.stats.seconds, "max_call": fhdb.stats.max_seconds, "bytes": len(body)}


def measure(base_url, routes: list[str], session_cookie) -> list[tuple[str, float, int]]:
    """Ukur `routes` (2x, laporkan yang ke-2). base_url = InProcess (test client) atau URL server
    yang berjalan dengan DB_STATS_HEADER=1; session_cookie = header Cookie untuk mode URL."""
    out = []
    for route in routes:
        res = None
        for _ in range(2):
            if isinstance(base_url, InProcess):
                res = base_url.get(route)
            else:
                req = urllib.request.Request(base_url.rstrip("/") + route, headers={"Cookie": session_cookie})
                t0 = time.perf_counter()
                with urllib.request.urlopen(req) as r:
                    r.read()
                    calls = int(r.headers.get("X-FH-DB-Calls", "-1"))
                res = {"seconds": time.perf_counter() - t0, "calls": calls}
        out.append((route, res["seconds"], res["calls"]))
    return out


def run(app, routes_with_company, runs=2, log=print):
    """Ukur langsung di proses ini (tanpa perlindungan hang); dipakai oleh worker."""
    import fhdb  # noqa: F401

    token = admin_token(app)
    client = InProcess(app, token)
    return [measure_one(client, route, company, runs) for route, company in routes_with_company]


def measure_one(client, route, company, runs=2):
    client.set_company(company)
    res = None
    err = ""
    cold = None
    for i in range(runs):
        try:
            res = client.get(route)
        except WriteBlocked as e:
            err = f"skip(write): {e}"
            res = None
            break
        except Exception as e:  # noqa: BLE001  (PROPAGATE_EXCEPTIONS=False; jaga-jaga)
            err = f"error: {type(e).__name__}: {str(e)[:100]}"
            res = None
            break
        if i == 0:
            cold = res["seconds"]
    if res is None and not err:
        err = "no result"
    heavy = is_heavy(route)
    target = TARGET_HEAVY if heavy else TARGET_NORMAL
    row = {"route": route, "company": company, "heavy": heavy, "target": target, "error": err}
    if res:
        row.update(res)
        row["cold"] = cold
        row["pass"] = res["seconds"] <= target and res["max_call"] <= 4.0 and res["status"] < 500
    return row


# ------------------------------------------------------------------- hang-proof runner

RES_PREFIX = "@@RES "


def worker_main(schema: str):
    """Mode --worker: baca 'company<TAB>route' per baris dari stdin, tulis satu baris JSON hasil."""
    import json

    app = make_app(schema)
    client = InProcess(app, admin_token(app))
    sys.stdout.write(RES_PREFIX + json.dumps({"ready": True}) + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        company, route = line.split("\t", 1)
        row = measure_one(client, route, company)
        sys.stdout.write(RES_PREFIX + json.dumps(row) + "\n")
        sys.stdout.flush()


class Worker:
    """Proses anak yang menjalankan worker_main; hasil dibaca lewat thread + queue supaya bisa di-timeout."""

    def __init__(self, schema: str, startup_timeout: float = 120.0):
        import json
        import queue
        import subprocess
        import threading

        self._json = json
        self.q = queue.Queue()
        self.p = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--worker", "--schema", schema],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1, cwd=ROOT)
        threading.Thread(target=self._read, daemon=True).start()
        first = self._next(startup_timeout)
        if not (first and first.get("ready")):
            self.kill()
            raise RuntimeError("worker tidak siap (gagal start atau DB tidak terjangkau)")

    def _read(self):
        for line in self.p.stdout:
            if line.startswith(RES_PREFIX):
                self.q.put(self._json.loads(line[len(RES_PREFIX):]))
        self.q.put(None)

    def _next(self, timeout):
        import queue

        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return "TIMEOUT"

    def measure(self, route, company, timeout):
        self.p.stdin.write(f"{company}\t{route}\n")
        self.p.stdin.flush()
        return self._next(timeout)

    def kill(self):
        try:
            self.p.kill()
        except Exception:  # noqa: BLE001
            pass


def run_isolated(schema, routes_with_company, timeout=ROUTE_TIMEOUT, log=print):
    """Seperti run(), tetapi tiap route di proses worker dengan batas waktu; route yang macet
    dicatat TIMEOUT, worker dimatikan dan diganti, lalu pengukuran lanjut."""
    results = []
    worker = None
    down = 0
    for i, (route, company) in enumerate(routes_with_company, 1):
        log(f"[{i}/{len(routes_with_company)}] {company} {route} ...")
        if worker is None:
            worker = Worker(schema)
        t0 = time.perf_counter()
        try:
            row = worker.measure(route, company, timeout)
        except (BrokenPipeError, OSError) as e:
            row = None
            err = f"worker mati: {e}"
        else:
            err = "worker mati" if row is None else ""
        if row == "TIMEOUT" or row is None:
            worker.kill()
            worker = None
            heavy = is_heavy(route)
            reason = (f"TIMEOUT (likely drive I/O) > {timeout:.0f}s" if row == "TIMEOUT" else err)
            row = {"route": route, "company": company, "heavy": heavy,
                   "target": TARGET_HEAVY if heavy else TARGET_NORMAL, "error": reason}
        results.append(row)
        if "seconds" in row:
            log(f"    {row['seconds']:6.2f}s (cold {row['cold']:.2f}s) calls={row['calls']:3d} "
                f"max={row['max_call']:.2f}s status={row['status']} {'ok' if row['pass'] else 'OVER'}")
        else:
            log(f"    {row['error']}  ({time.perf_counter() - t0:.1f}s)")
        if row.get("status") == 503:
            down += 1
            if down >= 5:
                if worker:
                    worker.kill()
                raise SystemExit("Berhenti: 5 route berturut-turut 503 (database tidak terjangkau).")
        else:
            down = 0
    if worker:
        worker.kill()
    return results


def write_markdown(results, path: str, schema: str, excluded=None, note=""):
    ok = [r for r in results if "seconds" in r]
    n_pass = sum(1 for r in ok if r["pass"])
    n_timeout = sum(1 for r in results if r.get("error", "").startswith("TIMEOUT"))
    excluded = excluded or {}
    lines = [
        "# Performa halaman FinanceHub di Supabase",
        "",
        f"Diukur {date.today().isoformat()}, schema `{schema}`, `scripts/pg_migrate/measure_pages.py` "
        "(Flask test client in-process di proses worker, DB lewat HTTPS ke Supabase; rendering browser "
        f"tidak termasuk). Tiap route 2x, yang dilaporkan run ke-2 (warm); batas {ROUTE_TIMEOUT:.0f} s per route.",
        "",
        f"Target: halaman biasa ≤ {TARGET_NORMAL:.0f} s, berat (dashboard, management-report, general-ledger, "
        f"export) ≤ {TARGET_HEAVY:.0f} s; panggilan fh_exec terlama ≤ 4 s (batas Supabase 8 s).",
        "",
        f"Lulus {n_pass} / {len(ok)} route terukur; tidak lulus {len(ok) - n_pass}; timeout {n_timeout}; "
        f"tidak terukur lainnya {len(results) - len(ok) - n_timeout}; dikecualikan {len(excluded)}.",
    ]
    if note:
        lines += ["", note]
    lines += [
        "",
        "| Route | Co | Detik | Panggilan DB | Detik DB | Panggilan terlama | Status | Target | Hasil |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in sorted(ok, key=lambda r: -r["seconds"]):
        lines.append(f"| `{r['route']}` | {r['company']} | {r['seconds']:.2f} | {r['calls']} | "
                     f"{r['db_seconds']:.2f} | {r['max_call']:.2f} | {r['status']} | {r['target']:.0f} | "
                     f"{'pass' if r['pass'] else '**FAIL**'} |")
    skipped = [r for r in results if "seconds" not in r]
    if skipped or excluded:
        lines += ["", "## Tidak terukur", "", "| Route | Co | Alasan |", "|---|---|---|"]
        for r in skipped:
            lines.append(f"| `{r['route']}` | {r['company']} | {r['error']} |")
        for route, why in excluded.items():
            lines.append(f"| `{route}` | – | {why} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default="financehub_staging")
    ap.add_argument("--out", default=None, help="tulis tabel markdown ke path ini")
    ap.add_argument("--json", default=None, help="simpan hasil mentah (JSON) ke path ini")
    ap.add_argument("--log", default=None, help="tulis progres (route sebelum tiap request) ke file ini")
    ap.add_argument("--only", action="append", default=[], help="hanya route ini (boleh berulang)")
    ap.add_argument("--company", action="append", default=[], help="SMT/ETF (default keduanya)")
    ap.add_argument("--timeout", type=float, default=ROUTE_TIMEOUT, help="detik per route")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.worker:
        return worker_main(args.schema)
    out = os.path.abspath(args.out) if args.out else None
    js = os.path.abspath(args.json) if args.json else None
    logf = open(os.path.abspath(args.log), "a", encoding="utf-8") if args.log else None

    def log(msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        if logf:
            logf.write(line + "\n")
            logf.flush()

    app = make_app(args.schema)   # hanya untuk daftar route; pengukuran di proses worker
    companies = args.company or ["SMT", "ETF"]
    if args.only:
        items = [(r, c) for r in args.only for c in companies]
    else:
        items = [(r, c) for r in discover_routes(app) for c in companies] + CURATED
    log(f"mulai: {len(items)} pengukuran, schema {args.schema}, timeout {args.timeout:.0f}s/route")
    results = run_isolated(args.schema, items, timeout=args.timeout, log=log)
    if js:
        with open(js, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1)
    if out:
        write_markdown(results, out, args.schema, excluded={} if args.only else EXCLUDE)
        log(f"ditulis: {out}")
    log("selesai")
    return results


if __name__ == "__main__":
    main()

"""Read-only profiling of a SQLite database ahead of the Postgres migration.

Usage: python scripts/pg_migrate/profile_sqlite.py <path-to-db> > docs/pg-migration/profile.md

Privacy: the Markdown report is committed to git. ``samples_odd`` only holds
values of date-like columns (name filter), max 5 distinct values, 30 chars each.
"""
import re
import sqlite3
import sys
from collections import Counter

DATE_NAME_RE = re.compile(r"tgl|tanggal|date|_at|SLA_", re.IGNORECASE)
_FORMATS = [
    ("YYYY-MM-DD", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("YYYY-MM-DD HH:MM:SS", re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?$")),
    ("DD/MM/YYYY", re.compile(r"^\d{2}/\d{2}/\d{4}$")),
]
MAX_SAMPLES = 5
SAMPLE_LEN = 30


def _qi(name):
    return '"' + name.replace('"', '""') + '"'


def _classify(value):
    s = str(value).strip()
    if s == "":
        return "empty"
    for label, rx in _FORMATS:
        if rx.match(s):
            return label
    return "other"


def profile(db_path):
    uri = "file:" + db_path.replace("\\", "/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "select name from sqlite_master where type='table' "
            "and name not like 'sqlite_%' order by name")]
        result = {}
        for t in tables:
            cols = {}
            for _cid, name, ctype, *_rest in conn.execute(f"pragma table_info({_qi(t)})"):
                q = _qi(name)
                kinds = Counter()
                for kind, n in conn.execute(f"select typeof({q}), count(*) from {_qi(t)} group by 1"):
                    kinds[kind] += n
                name_is_date = bool(DATE_NAME_RE.search(name))
                date_formats = {}
                samples = []
                if name_is_date or "text" in kinds:
                    # Name-matched columns are always classified; other text
                    # columns only when at least one value is a strict date.
                    cnt = Counter()
                    odd = []
                    for v, n in conn.execute(
                            f"select {q}, count(*) from {_qi(t)} where {q} is not null group by 1"):
                        label = _classify(v)
                        cnt[label] += n
                        if label == "other":
                            odd.append(str(v))
                    if name_is_date or any(k not in ("empty", "other") for k in cnt):
                        date_formats = dict(cnt)
                        if name_is_date:
                            samples = [" ".join(o.split())[:SAMPLE_LEN] for o in odd[:MAX_SAMPLES]]
                cols[name] = {
                    "declared": ctype or "",
                    "kinds": dict(kinds),
                    "null": kinds.get("null", 0),
                    "date_formats": date_formats,
                    "samples_odd": samples,
                }
            result[t] = cols
        return result
    finally:
        conn.close()


def _attention(prof):
    multi, odd_dates = [], []
    for t, cols in prof.items():
        for c, p in cols.items():
            nn = {k: v for k, v in p["kinds"].items() if k != "null"}
            if len(nn) > 1:
                multi.append((t, c, p["declared"], nn))
            if p["date_formats"].get("other"):
                odd_dates.append((t, c, p))
    return multi, odd_dates


def render(prof):
    multi, odd_dates = _attention(prof)
    out = ["# Profil SQLite", "", f"Jumlah tabel: {len(prof)}", "",
           "## Perlu perhatian", "",
           "### Kolom dengan >1 jenis nilai non-null", "",
           "| Tabel | Kolom | Tipe deklarasi | Jenis nilai |", "|---|---|---|---|"]
    for t, c, d, nn in multi:
        out.append(f"| {t} | {c} | {d or '-'} | {nn} |")
    out += ["", "### Kolom tanggal dengan format `other`", "",
            "| Tabel | Kolom | Format | Contoh (maks 5, 30 karakter) |", "|---|---|---|---|"]
    for t, c, p in odd_dates:
        s = "; ".join(p["samples_odd"]).replace("|", "/")
        out.append(f"| {t} | {c} | {p['date_formats']} | {s or '-'} |")
    out += ["", "## Detail per tabel", ""]
    for t, cols in prof.items():
        out += [f"### {t}", "", "| Kolom | Deklarasi | Jenis | Null | Format tanggal |",
                "|---|---|---|---|---|"]
        for c, p in cols.items():
            out.append(f"| {c} | {p['declared'] or '-'} | {p['kinds']} | {p['null']} | "
                       f"{p['date_formats'] or '-'} |")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(render(profile(sys.argv[1])))

# modules/general_ledger/sync.py
"""General Ledger: sync parsed sheet rows into Flow, with change detection."""
import hashlib
import json

from modules.general_ledger import service
from modules.general_ledger.parser import COLUMNS

_KEY = ("id_no", "acc_statutory", "acc_management", "job_name", "memo", "tgl")
_EPS = 1e-6
_BALANCE_TOLERANCE = 1.0


def _norm(v):
    return round(v, 6) if isinstance(v, float) else v


def compute_hash(rows: list) -> str:
    """Order-sensitive content hash of parsed rows (floats rounded to 6 decimals).

    Row order matters: MR New Code numbering follows sheet order, so a pure reorder is a change."""
    lines = [json.dumps([_norm(r[c]) for c in COLUMNS], ensure_ascii=False) for r in rows]
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _aggregate(rows):
    out = {}
    for r in rows:
        acc = out.setdefault(tuple(r[k] for k in _KEY), [0.0, 0.0])
        acc[0] += r["debit"]
        acc[1] += r["credit"]
    return out


def summarize_changes(old_rows: list, new_rows: list) -> dict:
    """Entries added / removed / changed (debit or credit differs), keyed on _KEY."""
    old, new = _aggregate(old_rows), _aggregate(new_rows)
    return {
        "added": sum(1 for k in new if k not in old),
        "removed": sum(1 for k in old if k not in new),
        "changed": sum(1 for k in new if k in old
                       and any(abs(a - b) > _EPS for a, b in zip(new[k], old[k]))),
    }


class NoRowsForYear(ValueError):
    """The file holds no row dated in the chosen year."""


def sync_rows(entity, year, filename, user, rows, dropped=0) -> dict:
    """Replace the entity's rows of `year` with the file's rows of that year, leaving other years alone.

    Rows dated outside `year` (or without a date) are skipped and counted in `skipped_year`.
    Nothing is written when the year's content is identical to its last sync."""
    year = int(year)
    prefix = f"{year}-"
    in_year = [r for r in rows if (r["tgl"] or "").startswith(prefix)]
    skipped_year = len(rows) - len(in_year)
    if not in_year:
        raise NoRowsForYear(f"Tidak ada baris bertanggal {year} di file ini.")

    content_hash = compute_hash(in_year)
    total_debit = sum(r["debit"] for r in in_year)
    total_credit = sum(r["credit"] for r in in_year)
    base = {"year": year, "rows": len(in_year), "skipped_year": skipped_year,
            "total_debit": total_debit, "total_credit": total_credit,
            "balanced": abs(total_debit - total_credit) <= _BALANCE_TOLERANCE}

    last = service.last_sync(entity, year)
    if (last and last["content_hash"] == content_hash
            and service.row_count(entity, year) == last["rows_after"]):   # table must still hold that sync
        return {"changed": False, "summary": last["summary"], **base}

    old = service.load_rows(entity, year)
    summary = summarize_changes(old, in_year)
    service.replace_year(entity, year, in_year, {
        "synced_by": user, "filename": filename, "content_hash": content_hash,
        "rows_before": len(old), "rows_after": len(in_year),
        "total_debit": total_debit, "total_credit": total_credit,
        "dropped": dropped, "summary": summary})
    return {"changed": True, "summary": summary, **base}

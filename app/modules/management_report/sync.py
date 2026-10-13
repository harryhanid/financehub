"""Management Report: sync a parsed Append1 into Flow, with change detection.

A sync compares the incoming rows with the active snapshot. If nothing changed
no snapshot is created; otherwise a new snapshot is stored together with a
summary of what changed since the previous one.
"""
import hashlib
import json

from modules.management_report import service

_HASH_FIELDS = ("coa", "mm", "yy", "cc", "category", "activity", "description",
                "pta", "custom", "mm1", "act", "bgt")
# A "report line" is what the Report sheet shows as one row.
_LINE_KEY = ("cc", "category", "custom", "mm1", "description", "activity")
_EPS = 1e-6


def _norm(v):
    return round(v, 6) if isinstance(v, float) else v


def _norm_meta(meta):
    """Canonical form of the sync metadata; None when it carries no information."""
    if not meta or not (meta.get("cc_names") or meta.get("period")):
        return None
    return {"cc_names": dict(sorted((meta.get("cc_names") or {}).items())),
            "period": meta.get("period")}


def compute_hash(rows: list, meta: dict = None) -> str:
    """Order-independent content hash of parsed rows (floats rounded to 6 decimals) and metadata."""
    lines = sorted(json.dumps([_norm(r[f]) for f in _HASH_FIELDS], ensure_ascii=False)
                   for r in rows)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    m = _norm_meta(meta)
    if m is not None:
        h.update(b"META\n")
        h.update(json.dumps(m, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def _aggregate(rows: list) -> dict:
    out = {}
    for r in rows:
        acc = out.setdefault(tuple(r[f] for f in _LINE_KEY), [0.0, 0.0, 0.0])
        acc[0] += r["bgt"]
        acc[1] += r["pta"]
        acc[2] += r["act"]
    return out


def summarize_changes(old_rows: list, new_rows: list) -> dict:
    """What changed between two row sets, measured on report lines (see _LINE_KEY)."""
    old, new = _aggregate(old_rows), _aggregate(new_rows)
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = [k for k in new if k in old
               and any(abs(a - b) > _EPS for a, b in zip(new[k], old[k]))]

    per_cc, total = {}, [0.0, 0.0, 0.0]

    def entry(cc):
        return per_cc.setdefault(cc, {"cc": cc, "bgt": 0.0, "pta": 0.0, "act": 0.0,
                                      "added": 0, "removed": 0, "changed": 0})

    def apply(keys, kind, sign_new, sign_old):
        for k in keys:
            e = entry(k[0])
            e[kind] += 1
            n = new.get(k, [0.0, 0.0, 0.0])
            o = old.get(k, [0.0, 0.0, 0.0])
            for i, field in enumerate(("bgt", "pta", "act")):
                d = sign_new * n[i] + sign_old * o[i]
                e[field] += d
                total[i] += d

    apply(added, "added", 1, 0)
    apply(removed, "removed", 0, -1)
    apply(changed, "changed", 1, -1)

    ccs = []
    for cc in sorted(per_cc):
        e = per_cc[cc]
        ccs.append({**e, "bgt": round(e["bgt"], 6), "pta": round(e["pta"], 6),
                    "act": round(e["act"], 6)})
    return {
        "first": not old_rows,
        "rows_before": len(old_rows),
        "rows_after": len(new_rows),
        "delta": {"bgt": round(total[0], 6), "pta": round(total[1], 6), "act": round(total[2], 6)},
        "lines": {"added": len(added), "removed": len(removed), "changed": len(changed)},
        "ccs": ccs,
    }


def sync_rows(company_id: int, filename: str, uploaded_by: str, rows: list, meta: dict = None) -> dict:
    """Store `rows` (+ metadata) as the new active snapshot unless they equal the active one.

    Returns {"changed": False, "rows": n} when nothing changed, otherwise
    {"changed": True, "upload_id": id, "rows": n, "summary": {...}}.
    """
    old_rows = service.load_active_rows(company_id)
    old_meta = _norm_meta(service.get_active_meta(company_id))
    # A file without CC descriptions/period (or one whose metadata could not be read) must not
    # wipe what an earlier sync stored: keep the previous metadata in that case.
    new_meta = _norm_meta(meta) or old_meta
    new_hash = compute_hash(rows, new_meta)
    if old_rows:
        old_hash = service.get_active_hash(company_id) or compute_hash(old_rows, old_meta)
        if old_hash == new_hash:
            return {"changed": False, "rows": len(rows)}
    summary = summarize_changes(old_rows, rows)
    summary["meta_changed"] = bool(old_rows) and old_meta != new_meta
    upload_id = service.save_upload(company_id, filename, uploaded_by, rows,
                                    content_hash=new_hash, change_summary=summary, meta=new_meta)
    return {"changed": True, "upload_id": upload_id, "rows": len(rows), "summary": summary}

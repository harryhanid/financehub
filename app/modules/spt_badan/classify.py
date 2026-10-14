# modules/spt_badan/classify.py
"""SPT Badan: classify one GL line against the Pemetaan (pure functions, no database)."""
from modules.management_report.category_map import alias_key, is_unmapped

BLOCKER = "blocker"
WARNING = "warning"
PPH_KINDS = ("pph_kosong", "pph_bukan_jenis")


def _exc(kind, severity, detail):
    return {"kind": kind, "severity": severity, "detail": detail}


def _norm(value) -> str:
    return str(value or "").strip().lower()


def classify_pph(raw, is_expense, aliases):
    """Return (pph_type, exception_kind); exception_kind is '' when the value is fine."""
    key = alias_key(raw)
    if key:
        pph_type = aliases.get(key, "")
        return (pph_type, "") if pph_type else ("", "pph_bukan_jenis")
    return ("", "pph_kosong" if is_expense else "")


def classify_line(line, source, cmap, lk_list, aliases):
    """Classify a GL line. Returns (classified_line, exceptions).

    Category LK / SPT come from the Pemetaan; the values carried by the GL row are only compared."""
    account = str(line["acc_statutory"] or "")
    entry = cmap.get((source, account))
    lk = spt = ""
    meta = None
    exceptions = []
    if entry is None:
        exceptions.append(_exc("akun_belum_dipetakan", BLOCKER,
                               f"Akun {account} tidak ada di pemetaan kategori"))
    elif is_unmapped(entry["category_lk"]):
        exceptions.append(_exc("akun_belum_dipetakan", BLOCKER,
                               f"Category LK akun {account} kosong / TBA"))
    else:
        lk = entry["category_lk"]
        spt = "" if is_unmapped(entry["category_spt"]) else entry["category_spt"]
        meta = lk_list.get(lk)
        if meta is None or not meta["statement"]:
            exceptions.append(_exc("category_lk_tidak_dikenal", BLOCKER,
                                   f"Category LK '{lk}' belum diatur jenis laporannya"))
            meta = None
        elif meta["statement"] == "laba_rugi" and not meta["kind"]:
            exceptions.append(_exc("category_lk_tidak_dikenal", BLOCKER,
                                   f"Category LK '{lk}' belum diatur sifatnya (pendapatan/beban/lainnya)"))
            meta = None
        elif meta["needs_spt"] and not spt:
            exceptions.append(_exc("category_spt_kosong", BLOCKER,
                                   f"Category SPT akun {account} kosong / TBA"))
        if (_norm(line.get("category_lk")) != _norm(entry["category_lk"])
                or _norm(line.get("category_spt")) != _norm(entry["category_spt"])):
            exceptions.append(_exc(
                "kategori_gl_beda", WARNING,
                f"GL: {line.get('category_lk') or '-'} / {line.get('category_spt') or '-'}; "
                f"pemetaan: {entry['category_lk'] or '-'} / {entry['category_spt'] or '-'}"))

    raw = str(line.get("pph_non_pph") or "").strip()
    pph_type, pph_kind = classify_pph(raw, bool(meta and meta["needs_spt"]), aliases)
    if pph_kind:
        detail = "Jenis PPh kosong pada baris biaya" if pph_kind == "pph_kosong" \
            else f"'{raw}' bukan jenis PPh"
        exceptions.append(_exc(pph_kind, WARNING, detail))

    classified = {
        "gl_id": line["id"], "tgl": line["tgl"], "id_no": line["id_no"],
        "acc_statutory": account, "acc_management": line["acc_management"],
        "job_name": line["job_name"], "memo": line["memo"], "debit_credit": line["debit_credit"],
        "accrual_actual": line["accrual_actual"], "category_lk": lk, "category_spt": spt,
        "pph_type_raw": raw, "pph_type": pph_type,
    }
    return classified, exceptions

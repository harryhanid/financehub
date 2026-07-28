# modules/sponsorship/service.py
from datetime import datetime
import config
from database import get_conn

PILLAR_COLUMNS = {
    "AGRI": "agri_amount",
    "APP": "app_amount",
    "ENERGY & FINANCE": "energy_finance_amount",
    "PROPERTY": "property_amount",
}


def _pillar_case_sql() -> str:
    cases = []
    for pillar, col in PILLAR_COLUMNS.items():
        cases.append(f"CASE WHEN cat3 = '{pillar}' THEN amount_request ELSE 0 END AS {col}")
    return ", ".join(cases)


def list_perusahaan() -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT cat1, cat2, cat3 FROM sponsorship_perusahaan ORDER BY cat1"
    ).fetchall()]
    conn.close()
    return rows


def get_perusahaan(cat1: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT cat1, cat2, cat3 FROM sponsorship_perusahaan WHERE cat1 = ?", (cat1,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def seed_perusahaan(rows) -> int:
    conn = get_conn()
    inserted = 0
    for cat1, cat2, cat3 in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?)",
            (cat1, cat2, cat3),
        )
        inserted += cur.rowcount
    conn.commit()
    conn.close()
    return inserted


def get_lembaga_suggestions(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT lembaga_perorangan FROM sponsorship_transaksi "
        "WHERE company_id = ? ORDER BY lembaga_perorangan",
        (company_id,),
    ).fetchall()
    conn.close()
    return [r["lembaga_perorangan"] for r in rows]


def _validate_payload(payload: dict):
    if payload.get("cat") not in config.SPONSORSHIP_CAT:
        return f"Cat harus salah satu dari: {', '.join(config.SPONSORSHIP_CAT)}."
    if payload.get("description") not in config.SPONSORSHIP_DESCRIPTION:
        return f"Description harus salah satu dari: {', '.join(config.SPONSORSHIP_DESCRIPTION)}."
    cat4 = payload.get("cat4")
    if cat4 not in (None, "", *config.SPONSORSHIP_CAT4):
        return f"Cat4 harus salah satu dari: {', '.join(config.SPONSORSHIP_CAT4)} atau kosong."
    if not payload.get("tanggal_form_sponsor"):
        return "Tanggal Form Sponsor wajib diisi."
    if not payload.get("lembaga_perorangan"):
        return "Lembaga/Perorangan wajib diisi."
    perusahaan = get_perusahaan(payload.get("cat1", ""))
    if not perusahaan:
        return "Cat1 tidak ditemukan di daftar perusahaan. Pilih dari daftar yang tersedia."
    try:
        float(payload.get("amount_request", 0) or 0)
    except (TypeError, ValueError):
        return "Amount Request harus berupa angka."
    return None


def create_transaksi(company_id: int, payload: dict) -> dict:
    error = _validate_payload(payload)
    if error:
        return {"ok": False, "pesan": error, "id": None}
    perusahaan = get_perusahaan(payload["cat1"])
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO sponsorship_transaksi
            (company_id, cat, description, tanggal_form_sponsor, tanggal_payment,
             cat1, cat2, cat3, lembaga_perorangan, perihal, amount_request, reff,
             status, cat4, coa, cc_total, cc, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                COALESCE(?, '701078002'), COALESCE(?, 'SMT - Corporate Communication'),
                COALESCE(?, 'POSPON'), COALESCE(?, 'Sponsor'))
        """,
        (
            company_id, payload["cat"], payload["description"],
            payload["tanggal_form_sponsor"], payload.get("tanggal_payment") or None,
            perusahaan["cat1"], perusahaan["cat2"], perusahaan["cat3"],
            payload["lembaga_perorangan"], payload.get("perihal"),
            float(payload.get("amount_request", 0) or 0), payload.get("reff"),
            payload.get("status"), payload.get("cat4") or None,
            payload.get("coa"), payload.get("cc_total"), payload.get("cc"), payload.get("source"),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"ok": True, "pesan": "Transaksi Sponsorship tersimpan.", "id": new_id}


def get_transaksi(transaksi_id: int):
    conn = get_conn()
    row = conn.execute(
        f"SELECT *, {_pillar_case_sql()} FROM sponsorship_transaksi WHERE id = ?",
        (transaksi_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_transaksi(transaksi_id: int, payload: dict) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM sponsorship_transaksi WHERE id = ?", (transaksi_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}

    # Validate fields present in payload
    if "cat" in payload and payload["cat"] not in config.SPONSORSHIP_CAT:
        conn.close()
        return {"ok": False, "pesan": f"Cat harus salah satu dari: {', '.join(config.SPONSORSHIP_CAT)}."}

    if "description" in payload and payload["description"] not in config.SPONSORSHIP_DESCRIPTION:
        conn.close()
        return {"ok": False, "pesan": f"Description harus salah satu dari: {', '.join(config.SPONSORSHIP_DESCRIPTION)}."}

    if "cat4" in payload:
        cat4 = payload["cat4"]
        if cat4 not in (None, "", *config.SPONSORSHIP_CAT4):
            conn.close()
            return {"ok": False, "pesan": f"Cat4 harus salah satu dari: {', '.join(config.SPONSORSHIP_CAT4)} atau kosong."}

    if "lembaga_perorangan" in payload and not payload["lembaga_perorangan"]:
        conn.close()
        return {"ok": False, "pesan": "Lembaga/Perorangan wajib diisi."}

    if "tanggal_form_sponsor" in payload and not payload["tanggal_form_sponsor"]:
        conn.close()
        return {"ok": False, "pesan": "Tanggal Form Sponsor wajib diisi."}

    if "amount_request" in payload:
        try:
            float(payload["amount_request"])
        except (TypeError, ValueError):
            conn.close()
            return {"ok": False, "pesan": "Amount Request harus berupa angka."}

    editable_fields = [
        "cat", "description", "tanggal_form_sponsor", "tanggal_payment", "cat1",
        "lembaga_perorangan", "perihal", "amount_request", "reff", "status", "cat4",
        "coa", "cc_total", "cc", "source",
    ]
    updates = {k: payload[k] for k in editable_fields if k in payload}

    # If cat1 is being updated, look it up and override cat2/cat3
    if "cat1" in updates:
        perusahaan = get_perusahaan(updates["cat1"])
        if not perusahaan:
            conn.close()
            return {"ok": False, "pesan": "Cat1 tidak ditemukan di daftar perusahaan. Pilih dari daftar yang tersedia."}
        updates["cat2"] = perusahaan["cat2"]
        updates["cat3"] = perusahaan["cat3"]

    # Coerce amount_request to float
    if "amount_request" in updates:
        updates["amount_request"] = float(updates["amount_request"])

    if not updates:
        conn.close()
        return {"ok": True, "pesan": "Tidak ada perubahan."}
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [datetime.now().isoformat(timespec="seconds"), transaksi_id]
    conn.execute(
        f"UPDATE sponsorship_transaksi SET {set_clause}, updated_at = ? WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Transaksi diperbarui."}


def _apply_filters(query: str, params: list, company_id: int, filters: dict):
    query += " AND company_id = ?"
    params.append(company_id)
    filters = filters or {}
    if filters.get("cat"):
        query += " AND cat = ?"
        params.append(filters["cat"])
    if filters.get("cat3"):
        query += " AND cat3 = ?"
        params.append(filters["cat3"])
    if filters.get("description"):
        query += " AND description = ?"
        params.append(filters["description"])
    if filters.get("status"):
        query += " AND status = ?"
        params.append(filters["status"])
    if filters.get("tahun"):
        query += " AND strftime('%Y', tanggal_form_sponsor) = ?"
        params.append(str(filters["tahun"]))
    return query, params


def list_transaksi(company_id: int, filters: dict = None, limit: int = None, offset: int = None) -> list:
    query = f"SELECT *, {_pillar_case_sql()} FROM sponsorship_transaksi WHERE 1=1"
    query, params = _apply_filters(query, [], company_id, filters)
    query += " ORDER BY tanggal_form_sponsor DESC, id DESC"
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = params + [limit, offset or 0]
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def count_transaksi(company_id: int, filters: dict = None) -> int:
    query = "SELECT COUNT(*) FROM sponsorship_transaksi WHERE 1=1"
    query, params = _apply_filters(query, [], company_id, filters)
    conn = get_conn()
    total = conn.execute(query, params).fetchone()[0]
    conn.close()
    return total


def get_available_years(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y', tanggal_form_sponsor) AS yy FROM sponsorship_transaksi "
        "WHERE company_id = ? ORDER BY yy DESC",
        (company_id,),
    ).fetchall()
    conn.close()
    return [r["yy"] for r in rows if r["yy"]]


def get_dashboard_data(company_id: int, filters: dict = None) -> dict:
    rows = list_transaksi(company_id, filters)

    total_amount = sum(r["amount_request"] for r in rows)
    total_count = len(rows)

    monthly = {}
    for r in rows:
        month = r["tanggal_form_sponsor"][:7]  # 'YYYY-MM'
        monthly[month] = monthly.get(month, 0) + r["amount_request"]
    monthly_chart = [{"month": m, "amount": monthly[m]} for m in sorted(monthly)]

    pillar_totals = {p: 0.0 for p in config.SPONSORSHIP_PILLARS}
    for r in rows:
        if r["cat3"] in pillar_totals:
            pillar_totals[r["cat3"]] += r["amount_request"]
    pillar_chart = [{"pillar": p, "amount": pillar_totals[p]} for p in config.SPONSORSHIP_PILLARS]

    desc_totals = {d: 0.0 for d in config.SPONSORSHIP_DESCRIPTION}
    for r in rows:
        if r["description"] in desc_totals:
            desc_totals[r["description"]] += r["amount_request"]
    description_chart = [{"description": d, "amount": desc_totals[d]} for d in config.SPONSORSHIP_DESCRIPTION]

    return {
        "summary": {"total_amount": total_amount, "total_count": total_count},
        "monthlyChart": monthly_chart,
        "pillarChart": pillar_chart,
        "descriptionChart": description_chart,
    }

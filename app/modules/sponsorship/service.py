# modules/sponsorship/service.py
import re as _re
from datetime import datetime
import config
from database import get_conn
from fhdb.errors import OperationalError

PILLAR_COLUMNS = {
    "APP": "app_amount",
    "AGRI": "agri_amount",
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
    # SQLite `INSERT OR IGNORE` juga mengabaikan pelanggaran NOT NULL (baris itu dilewati, sisanya
    # tetap masuk). `ON CONFLICT DO NOTHING` hanya menutup konflik unik, jadi baris dengan cat1/cat2/
    # cat3 None (semua NOT NULL di skema) dibuang dulu agar hasil dan jumlahnya sama dengan SQLite.
    # Sisanya satu panggilan executemany = satu transaksi; rowcount sudah dijumlah fhdb.
    conn = get_conn()
    params = [
        (cat1, cat2, cat3) for cat1, cat2, cat3 in rows
        if cat1 is not None and cat2 is not None and cat3 is not None
    ]
    inserted = 0
    if params:
        cur = conn.executemany(
            "INSERT INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            params,
        )
        inserted = cur.rowcount
    conn.close()
    return inserted


def create_perusahaan(cat1: str, cat2: str, cat3: str) -> dict:
    cat1 = (cat1 or "").strip()
    cat2 = (cat2 or "").strip()
    cat3 = (cat3 or "").strip()
    if not cat1 or not cat2 or not cat3:
        return {"ok": False, "pesan": "Cat1, Cat2, dan Cat3 wajib diisi."}
    if cat3 not in config.SPONSORSHIP_PILLARS:
        return {"ok": False, "pesan": f"Cat3 harus salah satu dari: {', '.join(config.SPONSORSHIP_PILLARS)}."}
    if get_perusahaan(cat1):
        return {"ok": False, "pesan": "Cat1 sudah terdaftar."}
    conn = get_conn()
    conn.execute(
        "INSERT INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?)",
        (cat1, cat2, cat3),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Vendor tersimpan."}


def update_perusahaan(cat1: str, cat2: str, cat3: str) -> dict:
    cat2 = (cat2 or "").strip()
    cat3 = (cat3 or "").strip()
    if not cat2 or not cat3:
        return {"ok": False, "pesan": "Cat2 dan Cat3 wajib diisi."}
    if cat3 not in config.SPONSORSHIP_PILLARS:
        return {"ok": False, "pesan": f"Cat3 harus salah satu dari: {', '.join(config.SPONSORSHIP_PILLARS)}."}
    if not get_perusahaan(cat1):
        return {"ok": False, "pesan": "Cat1 tidak ditemukan."}
    conn = get_conn()
    conn.execute(
        "UPDATE sponsorship_perusahaan SET cat2 = ?, cat3 = ? WHERE cat1 = ?",
        (cat2, cat3, cat1),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Vendor diperbarui."}


def delete_perusahaan(cat1: str) -> dict:
    if not get_perusahaan(cat1):
        return {"ok": False, "pesan": "Cat1 tidak ditemukan."}
    conn = get_conn()
    conn.execute("DELETE FROM sponsorship_perusahaan WHERE cat1 = ?", (cat1,))
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Vendor dihapus."}


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
                COALESCE(?::text, '701078002'), COALESCE(?::text, 'SMT - Corporate Communication'),
                COALESCE(?::text, 'POSPON'), COALESCE(?::text, 'Sponsor'))
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


def get_transaksi(transaksi_id: int, company_id: int = None):
    conn = get_conn()
    query = f"SELECT *, {_pillar_case_sql()} FROM sponsorship_transaksi WHERE id = ?"
    params = [transaksi_id]
    if company_id is not None:
        query += " AND company_id = ?"
        params.append(company_id)
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None


def update_transaksi(transaksi_id: int, payload: dict, company_id: int = None) -> dict:
    conn = get_conn()
    select_query = "SELECT * FROM sponsorship_transaksi WHERE id = ?"
    select_params = [transaksi_id]
    if company_id is not None:
        select_query += " AND company_id = ?"
        select_params.append(company_id)
    row = conn.execute(select_query, select_params).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}

    # Validate fields present in payload
    if "cat" in payload and payload["cat"] not in config.SPONSORSHIP_CAT:
        conn.close()
        return {"ok": False, "pesan": f"Cat harus salah satu dari: {', '.join(config.SPONSORSHIP_CAT)}."}

    if "description" in payload and payload["description"] != row["description"]:
        if payload["description"] not in config.SPONSORSHIP_DESCRIPTION:
            conn.close()
            return {"ok": False, "pesan": f"Description harus salah satu dari: {', '.join(config.SPONSORSHIP_DESCRIPTION)}."}

    if "cat4" in payload:
        cat4 = payload["cat4"]
        existing_cat4 = row["cat4"] or ""
        if cat4 != existing_cat4 and cat4 not in (None, "", *config.SPONSORSHIP_CAT4):
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
        if updates["cat1"] == row["cat1"]:
            del updates["cat1"]
        else:
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
    update_query = f"UPDATE sponsorship_transaksi SET {set_clause}, updated_at = ? WHERE id = ?"
    values = list(updates.values()) + [datetime.now().isoformat(timespec="seconds"), transaksi_id]
    if company_id is not None:
        update_query += " AND company_id = ?"
        values.append(company_id)
    conn.execute(update_query, values)
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Transaksi diperbarui."}


MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTH_LONG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
              "September", "Oktober", "November", "Desember"]
MONTH_CHOICES = [(f"{i + 1:02d}", name) for i, name in enumerate(MONTH_LONG)]


def normalise_bulan(values) -> list:
    """Two-digit month strings '01'..'12', sorted and de-duplicated; invalid values are dropped."""
    if values is None:
        return []
    if isinstance(values, (str, int)):
        values = [values]
    out = set()
    for v in values:
        try:
            m = int(str(v).strip())
        except ValueError:
            continue
        if 1 <= m <= 12:
            out.add(f"{m:02d}")
    return sorted(out)


def month_label(bulan) -> str:
    """['03', '01'] -> 'Jan, Mar'; nothing selected -> ''."""
    return ", ".join(MONTH_SHORT[int(m) - 1] for m in normalise_bulan(bulan))


def _apply_filters(query: str, params: list, company_id: int, filters: dict):
    query += " AND company_id = ?"
    params.append(company_id)
    filters = filters or {}
    if filters.get("cat1"):
        query += " AND cat1 = ?"
        params.append(filters["cat1"])
    if filters.get("cat2"):
        query += " AND cat2 = ?"
        params.append(filters["cat2"])
    if filters.get("cat"):
        cats = filters["cat"]
        if isinstance(cats, list) and cats:
            placeholders = ",".join(["?"] * len(cats))
            query += f" AND cat IN ({placeholders})"
            params.extend(cats)
        else:
            query += " AND cat = ?"
            params.append(cats)
    if filters.get("cat3"):
        pillars = filters["cat3"]
        if isinstance(pillars, list) and pillars:
            placeholders = ",".join(["?"] * len(pillars))
            query += f" AND cat3 IN ({placeholders})"
            params.extend(pillars)
        else:
            query += " AND cat3 = ?"
            params.append(pillars)
    if filters.get("cat4"):
        query += " AND cat4 = ?"
        params.append(filters["cat4"])
    if filters.get("description"):
        query += " AND description = ?"
        params.append(filters["description"])
    if filters.get("keyword"):
        kw = f"%{filters['keyword']}%"
        query += """ AND (
            status ILIKE ? OR
            cat ILIKE ? OR
            description ILIKE ? OR
            cat1 ILIKE ? OR
            cat2 ILIKE ? OR
            cat3 ILIKE ? OR
            lembaga_perorangan ILIKE ? OR
            perihal ILIKE ? OR
            reff ILIKE ?
        )"""
        params.extend([kw] * 9)
    if filters.get("outstanding"):
        query += " AND (tanggal_payment IS NULL OR tanggal_payment = '')"
    if filters.get("tahun"):
        years = filters["tahun"]
        if isinstance(years, list) and years:
            # ?::text: tahun bisa dikirim sebagai int; Postgres tidak membandingkan text = int
            placeholders = ",".join(["?::text"] * len(years))
            query += f" AND fh_strftime('%Y', tanggal_form_sponsor) IN ({placeholders})"
            params.extend(years)
        else:
            query += " AND fh_strftime('%Y', tanggal_form_sponsor) = ?"
            params.extend([str(years)])
    bulan = normalise_bulan(filters.get("bulan"))
    if bulan:
        placeholders = ",".join(["?"] * len(bulan))
        query += f" AND fh_strftime('%m', tanggal_form_sponsor) IN ({placeholders})"
        params.extend(bulan)
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
        "SELECT DISTINCT fh_strftime('%Y', tanggal_form_sponsor) AS yy FROM sponsorship_transaksi "
        "WHERE company_id = ? ORDER BY yy DESC NULLS LAST",
        (company_id,),
    ).fetchall()
    conn.close()
    years = {r["yy"] for r in rows if r["yy"]}
    # Add missing years (e.g. from current date if empty)
    return sorted(list(years), reverse=True)


def get_dashboard_data(company_id: int, filters: dict = None, cat4_mode: str = "all") -> dict:
    if filters is None:
        filters = {}
        
    if cat4_mode == "include":
        filters["cat4"] = "Include"
    elif cat4_mode == "exclude":
        filters["cat4"] = "Exclude"
    elif cat4_mode == "bib_include":
        filters["cat4"] = "Include"
        
    raw_rows = list_transaksi(company_id, filters)
    
    rows = []
    for r in raw_rows:
        if cat4_mode == "bib_include" and r["cat1"] == "BORNEO INDOBARA":
            r1 = dict(r)
            r1["cat3"] = "AGRI"
            r1["amount_request"] = r["amount_request"] * 0.51
            rows.append(r1)
            
            r2 = dict(r)
            r2["cat3"] = "ENERGY & FINANCE"
            r2["amount_request"] = r["amount_request"] * 0.49
            rows.append(r2)
        else:
            rows.append(dict(r))

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
    
    # New aggregations for the complex dashboard summaries
    desc_pillar_table = []
    desc_year_table = []
    year_pillar_chart = {}
    
    years_set = set()
    for r in rows:
        y = r["tanggal_form_sponsor"][:4]
        if y: years_set.add(y)
    sorted_years = sorted(list(years_set))
    
    for d in config.SPONSORSHIP_DESCRIPTION:
        # Desc vs Pillar
        dp_row = {"description": d, "total": 0.0}
        for p in config.SPONSORSHIP_PILLARS: dp_row[p] = 0.0
        
        # Desc vs Year
        dy_row = {"description": d, "total": 0.0}
        for y in sorted_years: dy_row[y] = 0.0
        
        for r in rows:
            if r["description"] == d:
                amt = r["amount_request"]
                
                # Pillar
                p = r["cat3"]
                if p in config.SPONSORSHIP_PILLARS:
                    dp_row[p] += amt
                dp_row["total"] += amt
                
                # Year
                y = r["tanggal_form_sponsor"][:4]
                if y in sorted_years:
                    dy_row[y] += amt
                dy_row["total"] += amt
                
        desc_pillar_table.append(dp_row)
        desc_year_table.append(dy_row)
        
    for r in rows:
        y = r["tanggal_form_sponsor"][:4]
        p = r["cat3"]
        if y and p in config.SPONSORSHIP_PILLARS:
            if y not in year_pillar_chart:
                year_pillar_chart[y] = {pil: 0.0 for pil in config.SPONSORSHIP_PILLARS}
            year_pillar_chart[y][p] += r["amount_request"]

    # Pillar summary table
    pillar_summary_table = []
    for p in ["APP", "ENERGY & FINANCE", "PROPERTY", "AGRI"]:
        amt = pillar_totals[p]
        pct = (amt / total_amount * 100) if total_amount > 0 else 0
        pillar_summary_table.append({"pillar": p, "amount": amt, "pct": pct})
    pillar_summary_table.append({"pillar": "Grand Total", "amount": total_amount, "pct": 100 if total_amount > 0 else 0})

    # Top 5 Lembaga
    lembaga_totals = {}
    for r in rows:
        l = r["lembaga_perorangan"] or "Unknown"
        lembaga_totals[l] = lembaga_totals.get(l, 0) + r["amount_request"]
    top_lembaga = [{"lembaga": k, "amount": v} for k, v in sorted(lembaga_totals.items(), key=lambda item: item[1], reverse=True)[:5]]
    
    # Status Chart
    status_totals = {}
    for r in rows:
        s = r["status"] or "Unknown"
        status_totals[s] = status_totals.get(s, 0) + r["amount_request"]
    status_chart = [{"status": k, "amount": v} for k, v in status_totals.items()]

    # Cat Mix (Sponsorship vs CSR Gedung)
    cat_totals = {c: 0.0 for c in config.SPONSORSHIP_CAT}
    for r in rows:
        if r["cat"] in cat_totals:
            cat_totals[r["cat"]] += r["amount_request"]
    cat_mix = [{"cat": c, "amount": cat_totals[c]} for c in config.SPONSORSHIP_CAT]

    # Cat4 Mix (Include vs Exclude)
    cat4_totals = {c: 0.0 for c in config.SPONSORSHIP_CAT4}
    for r in rows:
        if r["cat4"] in cat4_totals:
            cat4_totals[r["cat4"]] += r["amount_request"]
    cat4_mix = [{"cat4": c, "amount": cat4_totals[c]} for c in config.SPONSORSHIP_CAT4]

    # YoY Growth
    year_totals = {}
    for r in rows:
        y = r["tanggal_form_sponsor"][:4]
        if y:
            year_totals[y] = year_totals.get(y, 0.0) + r["amount_request"]
    yoy_growth = []
    prev_amount = None
    for y in sorted(year_totals):
        amount = year_totals[y]
        if prev_amount is None or prev_amount == 0:
            growth_pct = None
        else:
            growth_pct = (amount - prev_amount) / prev_amount * 100
        yoy_growth.append({"year": y, "amount": amount, "growth_pct": growth_pct})
        prev_amount = amount

    return {
        "summary": {"total_amount": total_amount, "total_count": total_count},
        "monthlyChart": monthly_chart,
        "pillarChart": pillar_chart,
        "descriptionChart": description_chart,
        "descPillarTable": desc_pillar_table,
        "descYearTable": desc_year_table,
        "yearPillarChart": year_pillar_chart,
        "pillarSummaryTable": pillar_summary_table,
        "sortedYears": sorted_years,
        "topLembaga": top_lembaga,
        "statusChart": status_chart,
        "catMix": cat_mix,
        "cat4Mix": cat4_mix,
        "yoyGrowth": yoy_growth
    }


def get_sponsorship_report(company_id: int, tahun: list, cat4_mode: str, bulan=None) -> dict:
    """Rekap sponsorship per description-section, dipivot per pillar (cat3),
    difilter cat4_mode ('include' | 'exclude' | 'all' | 'bib_include'). Section tanpa transaksi
    untuk tahun+cat4_mode ini disembunyikan; section yang ada urut sesuai
    config.SPONSORSHIP_DESCRIPTION. Baris dalam tiap section urut TOTAL desc.
    """
    bulan = normalise_bulan(bulan)
    filters = {"tahun": tahun}
    if bulan:
        filters["bulan"] = bulan
    if cat4_mode == "include":
        filters["cat4"] = "Include"
    elif cat4_mode == "exclude":
        filters["cat4"] = "Exclude"
    elif cat4_mode == "bib_include":
        filters["cat4"] = "Include"
    # cat4_mode == "all": no cat4 filter, includes NULL/blank cat4 rows

    rows = list_transaksi(company_id, filters)
    pillar_cols = list(PILLAR_COLUMNS.values())

    by_description = {}
    for r in rows:
        by_description.setdefault(r["description"], []).append(r)

    # Fixed config order first, then any legacy/migrated description values that
    # aren't in config.SPONSORSHIP_DESCRIPTION (new inserts can't produce these —
    # _validate_payload() blocks them — but historical/migrated rows might have
    # them; they must still show up as their own section, not vanish silently).
    ordered_descriptions = list(config.SPONSORSHIP_DESCRIPTION)
    for description in by_description:
        if description not in ordered_descriptions:
            ordered_descriptions.append(description)

    sections = []
    for description in ordered_descriptions:
        group = by_description.get(description)
        if not group:
            continue

        agg = {}
        for r in group:
            if cat4_mode == "bib_include" and r["cat1"] == "BORNEO INDOBARA":
                amt = r["amount_request"]
                r["agri_amount"] = amt * 0.51
                r["energy_finance_amount"] = amt * 0.49
                r["app_amount"] = 0.0
                r["property_amount"] = 0.0

            key = (r["lembaga_perorangan"] or "", r["perihal"] or "")
            tgl_pay = str(r["tanggal_payment"]).strip() if r.get("tanggal_payment") else ""
            reff_val = str(r["reff"]).strip() if r.get("reff") else ""
            
            if key not in agg:
                agg[key] = {
                    "lembaga_perorangan": r["lembaga_perorangan"],
                    "perihal": r["perihal"],
                    "tanggal_payment_list": [tgl_pay] if tgl_pay else [],
                    "reff_list": [reff_val] if reff_val else [],
                    "total": r["amount_request"],
                }
                for col in pillar_cols:
                    agg[key][col] = r[col]
            else:
                if tgl_pay and tgl_pay not in agg[key]["tanggal_payment_list"]:
                    agg[key]["tanggal_payment_list"].append(tgl_pay)
                if reff_val and reff_val not in agg[key]["reff_list"]:
                    agg[key]["reff_list"].append(reff_val)
                    
                agg[key]["total"] += r["amount_request"]
                for col in pillar_cols:
                    agg[key][col] += r[col]

        for row_out in agg.values():
            row_out["tanggal_payment"] = ", ".join(row_out.pop("tanggal_payment_list", []))
            row_out["reff"] = ", ".join(row_out.pop("reff_list", []))
            
        aggregated_rows = list(agg.values())
        aggregated_rows.sort(key=lambda r: r["total"], reverse=True)

        section_rows = []
        subtotal = {col: 0.0 for col in pillar_cols}
        subtotal["total"] = 0.0
        for i, row_out in enumerate(aggregated_rows, start=1):
            row_out["no"] = i
            for col in pillar_cols:
                subtotal[col] += row_out[col]
            subtotal["total"] += row_out["total"]
            section_rows.append(row_out)

        sections.append({
            "description": description,
            "rows": section_rows,
            "subtotal": subtotal,
        })

    grand_total = {col: 0.0 for col in pillar_cols}
    grand_total["total"] = 0.0
    for s in sections:
        for col in pillar_cols:
            grand_total[col] += s["subtotal"][col]
        grand_total["total"] += s["subtotal"]["total"]

    pct_allocation = {}
    for col in pillar_cols:
        pct_allocation[col] = round(grand_total[col] / grand_total["total"] * 100) if grand_total["total"] else 0

    return {
        "tahun": ",".join(tahun) if isinstance(tahun, list) else str(tahun),
        "cat4_mode": cat4_mode,
        "bulan": bulan,
        "bulan_label": month_label(bulan),
        "sections": sections,
        "grand_total": grand_total,
        "pct_allocation": pct_allocation,
    }


def get_sponsorship_outstanding(company_id: int, filters: dict = None) -> tuple:
    """
    Returns (sections, grand_total).
    sections is a list of dicts: {"cat2_label": "Charging to ...", "rows": [...], "subtotal": ...}
    Rows are those where tanggal_payment is null or empty.
    """
    filters = dict(filters or {})
    filters["outstanding"] = True
    
    rows = list_transaksi(company_id, filters)
    
    by_cat2 = {}
    for r in rows:
        cat2 = r.get("cat2") or "(blank)"
        if cat2 not in by_cat2:
            by_cat2[cat2] = []
        by_cat2[cat2].append(r)
        
    sections = []
    grand_total = 0.0
    
    for cat2, group in by_cat2.items():
        section_rows = []
        subtotal = 0.0
        
        group.sort(key=lambda x: x["tanggal_form_sponsor"] or "")
        
        for i, r in enumerate(group, start=1):
            tgl_approval = ""
            if r["tanggal_form_sponsor"]:
                try:
                    dt = datetime.strptime(r["tanggal_form_sponsor"], "%Y-%m-%d")
                    months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
                    tgl_approval = f"{months[dt.month - 1]} {dt.year}"
                except ValueError:
                    tgl_approval = r["tanggal_form_sponsor"]
                    
            amt = r["amount_request"] or 0.0
            subtotal += amt
            grand_total += amt
            
            section_rows.append({
                "no": i,
                "tanggal_approval": tgl_approval,
                "reff": r["reff"] or "(blank)",
                "lembaga_perorangan": r["lembaga_perorangan"] or "",
                "perihal": r["perihal"] or "",
                "amount": amt,
                "status": r["status"] or ""
            })
            
        cat2_label = cat2 if str(cat2).lower().startswith("charging") else f"Charging to {cat2}"
        sections.append({
            "cat2_label": cat2_label,
            "subtotal": subtotal,
            "rows": section_rows
        })
        
    STANDARD_CHARGING_ORDER = {
        "charging to app": 1,
        "charging to agri": 2,
        "charging to finance": 3,
        "charging to mining": 4,
        "charging to property": 5,
    }

    def _section_sort_key(s):
        label = (s.get("cat2_label") or "").strip().lower()
        label_norm = " ".join(label.split())
        if not label_norm.startswith("charging to"):
            label_norm = f"charging to {label_norm}"
        order = STANDARD_CHARGING_ORDER.get(label_norm, 999)
        return (order, -s.get("subtotal", 0.0), label_norm)

    sections.sort(key=_section_sort_key)
    
    return sections, grand_total


def get_sponsorship_mr(company_id: int, tahun: list) -> list:
    """Rekap sponsorship jadi format MR (Management Report) — 17 kolom
    standar untuk upload ke sistem GL, satu baris per transaksi. Difilter
    HANYA oleh tahun (tidak ada filter cat/pillar/description/status —
    lihat spec §2/§9). Nomor urut 'New Code' reset ke 1 tiap ganti tahun
    (CC0) — lihat spec §3. Urutan baris: tanggal_form_sponsor ASC, lalu
    id ASC (spec §4)."""
    filters = {"tahun": tahun}
    rows = list_transaksi(company_id, filters)
    rows.sort(key=lambda r: (r["tanggal_form_sponsor"] or "", r["id"]))

    seq_by_year = {}
    mr_rows = []
    for r in rows:
        date_str = r["tanggal_form_sponsor"]
        year_full = date_str[:4]
        cc0 = date_str[2:4]
        month = int(date_str[5:7])
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_display = date_obj.strftime("%d-%b-%y")
        except (ValueError, TypeError):
            date_obj = None
            date_display = date_str or ""

        parts = [p for p in (r["description"], r["lembaga_perorangan"], r["perihal"]) if p]
        allocation_memo = " - ".join(parts)

        seq_by_year[cc0] = seq_by_year.get(cc0, 0) + 1
        seq = seq_by_year[cc0]
        new_code = f"A{cc0}-{config.SPONSORSHIP_MR_CC1}{config.SPONSORSHIP_MR_BC1}{seq}"

        mr_rows.append({
            "account_management": config.SPONSORSHIP_MR_ACCOUNT_MANAGEMENT,
            "id_no": "",
            "date": date_obj,
            "date_display": date_display,
            "allocation_memo": allocation_memo,
            "budget_activity": "",
            "cost_center": config.SPONSORSHIP_MR_COST_CENTER,
            "debit_credit": r["amount_request"],
            "source": config.SPONSORSHIP_MR_SOURCE,
            "coa_ho": config.SPONSORSHIP_MR_COA_HO,
            "cost_center2": config.SPONSORSHIP_MR_COST_CENTER2,
            "month": month,
            "cc0": cc0,
            "cc1": config.SPONSORSHIP_MR_CC1,
            "bc1": config.SPONSORSHIP_MR_BC1,
            "new_code": new_code,
            "memo": f"- Act {year_full} : {allocation_memo} Month : {month}",
            "bc": config.SPONSORSHIP_MR_BC,
        })
    return mr_rows

def create_transaksi_bulk(company_id: int, payload: dict) -> dict:
    lines = payload.get("lines", [])
    if not lines:
        return {"ok": False, "pesan": "Tidak ada baris transaksi."}
    
    # Common validation
    if not payload.get("tanggal_form_sponsor"):
        return {"ok": False, "pesan": "Tanggal Form Sponsor wajib diisi."}
    if not payload.get("lembaga_perorangan"):
        return {"ok": False, "pesan": "Lembaga/Perorangan wajib diisi."}

    # Extract header data
    cat = payload.get("cat")
    desc = payload.get("description")
    tgl_form = payload.get("tanggal_form_sponsor")
    tgl_pay = payload.get("tanggal_payment") or None
    lembaga = payload.get("lembaga_perorangan")
    perihal = payload.get("perihal")
    reff = payload.get("reff")
    status = payload.get("status")
    coa = payload.get("coa")
    cc_total = payload.get("cc_total")
    cc = payload.get("cc")
    source = payload.get("source")

    # Validasi semua baris dulu, lalu satu batch INSERT (all-or-nothing, R22). Di SQLite dulu
    # rollback() di tengah loop membatalkan baris sebelumnya; fhdb tidak bisa rollback.
    try:
        items = []
        for idx, line in enumerate(lines):
            cat1 = line.get("cat1")
            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                return {"ok": False, "pesan": f"Baris {idx+1}: Cat1 '{cat1}' tidak ditemukan."}

            try:
                amt = float(line.get("amount_request", 0) or 0)
            except (TypeError, ValueError):
                return {"ok": False, "pesan": f"Baris {idx+1}: Amount Request harus berupa angka."}

            items.append((
                """
                INSERT INTO sponsorship_transaksi
                    (company_id, cat, description, tanggal_form_sponsor, tanggal_payment,
                     cat1, cat2, cat3, lembaga_perorangan, perihal, amount_request, reff,
                     status, cat4, coa, cc_total, cc, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE(?::text, '701078002'), COALESCE(?::text, 'SMT - Corporate Communication'),
                        COALESCE(?::text, 'POSPON'), COALESCE(?::text, 'Sponsor'))
                RETURNING id
                """,
                (
                    company_id, cat, desc, tgl_form, tgl_pay,
                    perusahaan["cat1"], perusahaan["cat2"], perusahaan["cat3"],
                    lembaga, perihal, amt, reff, status, line.get("cat4"),
                    coa, cc_total, cc, source
                ),
            ))
        conn = get_conn()
        conn.batch(items)
        return {"ok": True, "pesan": f"Berhasil menyimpan {len(lines)} transaksi Sponsorship."}
    except OperationalError:
        raise  # R25: DB tidak terjangkau -> handler 503 aplikasi
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal menyimpan transaksi: {str(e)}"}


def delete_transaksi(transaksi_id: int, company_id: int = None) -> dict:
    conn = get_conn()
    select_query = "SELECT * FROM sponsorship_transaksi WHERE id = ?"
    params = [transaksi_id]
    if company_id:
        select_query += " AND company_id = ?"
        params.append(company_id)
        
    t = conn.execute(select_query, params).fetchone()
    if not t:
        conn.close()
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}
        
    try:
        conn.execute("DELETE FROM sponsorship_transaksi WHERE id = ?", (transaksi_id,))
        conn.commit()
        return {"ok": True, "pesan": "Transaksi berhasil dihapus."}
    except OperationalError:
        raise  # R25: DB tidak terjangkau -> handler 503 aplikasi
    except Exception as e:
        conn.rollback()
        return {"ok": False, "pesan": f"Gagal menghapus transaksi: {str(e)}"}

# Teks yang dikonversi SQLite ke angka saat dibandingkan dengan kolom INTEGER (affinity numerik).
_SQLITE_NUMERIC_TEXT = _re.compile(r"^\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?\s*$")


def _sqlite_id_param(value):
    """Nilai ID Excel untuk `WHERE id = ?` dengan hasil seperti SQLite.

    SQLite: teks numerik ('12', '12.0') dibandingkan sebagai angka; teks lain ('-', 'ABC', '12a')
    atau tanggal tidak cocok dengan id mana pun. Postgres menolak teks itu sebagai bigint, jadi
    kembalikan angka, atau None = tidak ada baris yang cocok (UPDATE dilewati)."""
    if type(value) is bool:
        return int(value)  # SQLite menyimpan/membandingkan True/False sebagai 1/0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and _SQLITE_NUMERIC_TEXT.match(value):
        try:
            num = int(value.strip())  # tepat juga untuk angka > 2^53
        except ValueError:
            f = float(value)
            if not f.is_integer():
                return f  # tidak mungkin sama dengan id bigint, tapi aman dibandingkan
            num = int(f)
        if -(2 ** 63) <= num < 2 ** 63:
            return num
        return None  # di luar jangkauan bigint: SQLite tidak menemukan baris; Postgres akan error
    return None


def sync_transaksi_excel(company_id: int, file_bytes: bytes) -> dict:
    import openpyxl
    import io
    
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal membaca file Excel: {str(e)}"}
        
    conn = get_conn()
    try:
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            return {"ok": False, "pesan": "File Excel kosong atau tidak memiliki data."}
            
        header = rows[0]
        # Pastikan kolom sesuai dengan format export
        
        updated_count = 0
        inserted_count = 0
        # Seluruh sheet diparse dan divalidasi dulu, lalu semua tulisan dikirim sebagai SATU batch
        # (all-or-nothing, R22). Di SQLite dulu rollback() di tengah loop membatalkan baris sebelumnya.
        items = []
        
        for idx, row in enumerate(rows[1:], start=2):
            # Row structure: 0:ID, 1:Cat, 2:Desc, 3:Tgl Form, 4:Tgl Pay, 5:Cat1, 6:Cat2, 7:Cat3, 8:Lembaga, 9:Perihal, 10:Amount, 11:APP, 12:ENERGY, 13:PROPERTY, 14:AGRI, 15:Reff, 16:Status, 17:Cat4, 18:COA, 19:CC Total, 20:CC, 21:Source
            
            tx_id = row[0]
            cat = row[1]
            desc = row[2]
            
            # Date handling
            import datetime
            tgl_form = row[3]
            if isinstance(tgl_form, datetime.datetime):
                tgl_form = tgl_form.strftime('%Y-%m-%d')
            tgl_pay = row[4]
            if isinstance(tgl_pay, datetime.datetime):
                tgl_pay = tgl_pay.strftime('%Y-%m-%d')
            if not tgl_pay:
                tgl_pay = None
                
            cat1 = row[5]
            cat2 = row[6]
            cat3 = row[7]
            lembaga = row[8]
            perihal = row[9]
            amt = row[10]
            reff = row[15]
            status = row[16]
            cat4 = row[17]
            coa = row[18]
            cc_total = row[19]
            cc = row[20]
            source = row[21]
            
            # Validasi kolom wajib
            if not cat1:
                if not tx_id and not tgl_form and not amt:
                    continue # Baris benar-benar kosong
                return {"ok": False, "pesan": f"Baris {idx}: Cat1 (Perusahaan) wajib diisi."}
            if not tgl_form:
                return {"ok": False, "pesan": f"Baris {idx}: Tanggal Form wajib diisi."}
                
            lembaga = str(lembaga).strip() if lembaga else ""
            desc = str(desc).strip() if desc else ""
            cat = str(cat).strip() if cat else ""
                
            # Pastikan null aman
            cat1 = str(cat1).strip()
            cat2 = str(cat2).strip() if cat2 else ""
            cat3 = str(cat3).strip() if cat3 else ""
            
            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                if not cat2 or not cat3:
                    return {"ok": False, "pesan": f"Baris {idx}: Cat1 '{cat1}' baru, namun Cat2 atau Cat3 kosong di Excel."}
                # Cat1 baru yang muncul di beberapa baris: baris berikutnya menimpa cat2/cat3
                # (dedupe lewat ON CONFLICT, lihat atomic-flows.md Task 13).
                items.append((
                    "INSERT INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?) "
                    "ON CONFLICT (cat1) DO UPDATE SET cat2 = EXCLUDED.cat2, cat3 = EXCLUDED.cat3 "
                    "RETURNING cat1",
                    (cat1, cat2, cat3)
                ))
            else:
                # Update vendor info in DB if excel has different cat2/cat3
                if (cat2 and cat2 != perusahaan["cat2"]) or (cat3 and cat3 != perusahaan["cat3"]):
                    items.append((
                        "UPDATE sponsorship_perusahaan SET cat2=?, cat3=? WHERE cat1=?",
                        (cat2, cat3, cat1)
                    ))
            
            try:
                amt = float(amt) if amt else 0
            except ValueError:
                amt = 0
                
            if tx_id:
                # Update
                id_param = _sqlite_id_param(tx_id)
                if id_param is None:
                    # SQLite: UPDATE ... WHERE id='<teks bukan angka>' tidak mengubah apa pun,
                    # tapi baris tetap dihitung di-update (perilaku lama).
                    updated_count += 1
                    continue
                items.append((
                    """
                    UPDATE sponsorship_transaksi 
                    SET cat=?, description=?, tanggal_form_sponsor=?, tanggal_payment=?,
                        cat1=?, cat2=?, cat3=?, lembaga_perorangan=?, perihal=?, amount_request=?, reff=?,
                        status=?, cat4=?, coa=?, cc_total=?, cc=?, source=?
                    WHERE id=? AND company_id=?
                    """,
                    (cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source, id_param, company_id)
                ))
                updated_count += 1
            else:
                # Insert
                items.append((
                    """
                    INSERT INTO sponsorship_transaksi
                        (company_id, cat, description, tanggal_form_sponsor, tanggal_payment,
                         cat1, cat2, cat3, lembaga_perorangan, perihal, amount_request, reff,
                         status, cat4, coa, cc_total, cc, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?::text, '701078002'), COALESCE(?::text, 'SMT - Corporate Communication'), COALESCE(?::text, 'POSPON'), COALESCE(?::text, 'Sponsor'))
                    RETURNING id
                    """,
                    (company_id, cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source)
                ))
                inserted_count += 1
                
        if items:
            conn.batch(items)
        return {"ok": True, "pesan": f"Sync sukses: {updated_count} di-update, {inserted_count} ditambah."}

    except OperationalError:
        raise  # R25: DB tidak terjangkau -> handler 503 aplikasi
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal sync transaksi: {str(e)}"}


# --- Sponsorship Proposal Module Functions ---

def generate_next_proposal_number(company_id: int, year: str) -> str:
    conn = get_conn()
    prefix = f"PROP-{year}-"
    try:
        row = conn.execute(
            "SELECT nomor_proposal FROM sponsorship_proposal WHERE company_id = ? AND nomor_proposal LIKE ? ORDER BY nomor_proposal DESC LIMIT 1",
            (company_id, f"{prefix}%")
        ).fetchone()
        if row and row["nomor_proposal"]:
            try:
                last_seq = int(row["nomor_proposal"].split("-")[-1])
                new_seq = last_seq + 1
            except Exception:
                new_seq = 1
        else:
            new_seq = 1
        return f"PROP-{year}-{new_seq:04d}"
    finally:
        conn.close()


def list_proposals(company_id: int, filters: dict, limit: int = 100, offset: int = 0) -> list:
    conn = get_conn()
    try:
        clauses = ["company_id = ?"]
        params = [company_id]

        if filters.get("tahun"):
            years = filters["tahun"] if isinstance(filters["tahun"], list) else [filters["tahun"]]
            year_clauses = ["SUBSTR(tanggal, 1, 4) = ?" for _ in years]
            clauses.append(f"({' OR '.join(year_clauses)})")
            params.extend(years)

        if filters.get("status"):
            st = filters["status"]
            if st and st != "all":
                clauses.append("LOWER(status) = LOWER(?)")
                params.append(st)

        if filters.get("keyword"):
            kw = f"%{filters['keyword']}%"
            clauses.append("(nomor_proposal LIKE ? OR referensi LIKE ? OR kegiatan LIKE ?)")
            params.extend([kw, kw, kw])

        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT id, company_id, nomor_proposal, tanggal, referensi, kegiatan,
                   app_amount, agri_amount, energy_amount, land_amount, finance_amount,
                   total_amount, diajukan_oleh, versi, status, approval_date, catatan,
                   created_at, updated_at
            FROM sponsorship_proposal
            WHERE {where_sql}
            ORDER BY tanggal DESC, id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
        return rows
    finally:
        conn.close()


def count_proposals(company_id: int, filters: dict) -> int:
    conn = get_conn()
    try:
        clauses = ["company_id = ?"]
        params = [company_id]

        if filters.get("tahun"):
            years = filters["tahun"] if isinstance(filters["tahun"], list) else [filters["tahun"]]
            year_clauses = ["SUBSTR(tanggal, 1, 4) = ?" for _ in years]
            clauses.append(f"({' OR '.join(year_clauses)})")
            params.extend(years)

        if filters.get("status"):
            st = filters["status"]
            if st and st != "all":
                clauses.append("LOWER(status) = LOWER(?)")
                params.append(st)

        if filters.get("keyword"):
            kw = f"%{filters['keyword']}%"
            clauses.append("(nomor_proposal LIKE ? OR referensi LIKE ? OR kegiatan LIKE ?)")
            params.extend([kw, kw, kw])

        where_sql = " AND ".join(clauses)
        row = conn.execute(f"SELECT COUNT(*) FROM sponsorship_proposal WHERE {where_sql}", tuple(params)).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def get_proposal(company_id: int, proposal_id: int) -> dict:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM sponsorship_proposal WHERE company_id = ? AND id = ?", (company_id, proposal_id)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_available_proposal_years(company_id: int) -> list:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT SUBSTR(tanggal, 1, 4) as thn FROM sponsorship_proposal WHERE company_id = ? AND tanggal IS NOT NULL AND tanggal != '' ORDER BY thn DESC",
            (company_id,)
        ).fetchall()
        years = [str(r["thn"]) for r in rows if r["thn"]]
        if not years:
            years = [str(datetime.now().year)]
        return sorted(list(set(years)), reverse=True)
    finally:
        conn.close()


DEFAULT_ALLOCATION_VENDORS = [
    {"cat1": "In Progress Allocation (APP)", "cat2": "APP", "cat3": "APP"},
    {"cat1": "In Progress Allocation (AGRI)", "cat2": "AGRI", "cat3": "AGRI"},
    {"cat1": "In Progress Allocation (Mining)", "cat2": "Mining", "cat3": "ENERGY & FINANCE"},
    {"cat1": "In Progress Allocation (PROPERTY)", "cat2": "Property", "cat3": "PROPERTY"},
    {"cat1": "In Progress Allocation (Finance)", "cat2": "Finance", "cat3": "ENERGY & FINANCE"},
]

PROPOSAL_PILLAR_MAPPING = [
    {"field": "app_amount", "cat1": "In Progress Allocation (APP)", "cat2": "APP", "cat3": "APP"},
    {"field": "agri_amount", "cat1": "In Progress Allocation (AGRI)", "cat2": "AGRI", "cat3": "AGRI"},
    {"field": "energy_amount", "cat1": "In Progress Allocation (Mining)", "cat2": "Mining", "cat3": "ENERGY & FINANCE"},
    {"field": "land_amount", "cat1": "In Progress Allocation (PROPERTY)", "cat2": "Property", "cat3": "PROPERTY"},
    {"field": "finance_amount", "cat1": "In Progress Allocation (Finance)", "cat2": "Finance", "cat3": "ENERGY & FINANCE"},
]


def ensure_allocation_vendors(conn):
    for v in DEFAULT_ALLOCATION_VENDORS:
        row = conn.execute("SELECT cat1 FROM sponsorship_perusahaan WHERE cat1 = ?", (v["cat1"],)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?)",
                (v["cat1"], v["cat2"], v["cat3"])
            )


def sync_approved_proposal_to_transaksi(company_id: int, proposal_id: int, conn=None) -> dict:
    """Sinkronisasi data Proposal yang statusnya Approved ke Sponsor (sponsorship_transaksi).
    Jika status != 'Approved', transaksi terkait proposal ini dihapus (reversal).
    Jika status == 'Approved', baris di-breakdown per pilar yang nominalnya > 0."""
    should_close = False
    if conn is None:
        conn = get_conn()
        should_close = True
    try:
        row = conn.execute(
            "SELECT * FROM sponsorship_proposal WHERE company_id = ? AND id = ?",
            (company_id, proposal_id)
        ).fetchone()
        if not row:
            conn.execute("DELETE FROM sponsorship_transaksi WHERE company_id = ? AND proposal_id = ?", (company_id, proposal_id))
            return {"ok": True, "action": "deleted", "synced_rows": 0}

        proposal = dict(row)
        status = str(proposal.get("status") or "").strip().lower()

        if status != "approved":
            conn.execute("DELETE FROM sponsorship_transaksi WHERE company_id = ? AND proposal_id = ?", (company_id, proposal_id))
            return {"ok": True, "action": "deleted", "synced_rows": 0}

        ensure_allocation_vendors(conn)

        # Hapus transaksi lama terkait proposal ini agar tidak duplikat / update bersih
        conn.execute("DELETE FROM sponsorship_transaksi WHERE company_id = ? AND proposal_id = ?", (company_id, proposal_id))

        tgl_form = proposal.get("approval_date") or proposal.get("tanggal") or datetime.now().strftime("%Y-%m-%d")
        if len(str(tgl_form)) > 10:
            tgl_form = str(tgl_form)[:10]

        reff = proposal.get("referensi") or ""
        perihal = proposal.get("kegiatan") or ""
        lembaga = reff or perihal or "Proposal"

        # Tipe: Memo -> CAT4 'Exclude', Form -> CAT4 'Include'
        prop_tipe = str(proposal.get("tipe") or "Form").strip().lower()
        cat4_val = "Exclude" if prop_tipe == "memo" else "Include"

        synced_count = 0
        for p in PROPOSAL_PILLAR_MAPPING:
            amt = float(proposal.get(p["field"]) or 0)
            if amt > 0:
                conn.execute("""
                    INSERT INTO sponsorship_transaksi (
                        company_id, proposal_id, cat, description,
                        tanggal_form_sponsor, tanggal_payment, cat1, cat2, cat3,
                        lembaga_perorangan, perihal, amount_request, reff,
                        status, cat4, coa, cc_total, cc, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    proposal_id,
                    "Sponsorship",
                    "Lainnya",
                    tgl_form,
                    None,
                    p["cat1"],
                    p["cat2"],
                    p["cat3"],
                    lembaga,
                    perihal,
                    amt,
                    reff,
                    "On Progress Alokasi",
                    cat4_val,
                    "701078002",
                    "SMT - Corporate Communication",
                    "POSPON",
                    "Sponsor"
                ))
                synced_count += 1

        return {"ok": True, "action": "inserted", "synced_rows": synced_count}
    finally:
        if should_close:
            conn.close()


def create_proposal(company_id: int, payload: dict) -> dict:
    conn = get_conn()
    try:
        tgl = payload.get("tanggal") or datetime.now().strftime("%Y-%m-%d")
        year = str(tgl)[:4] if len(str(tgl)) >= 4 else str(datetime.now().year)
        nomor_prop = payload.get("nomor_proposal")
        if not nomor_prop:
            nomor_prop = generate_next_proposal_number(company_id, year)

        app_amt = float(payload.get("app_amount") or 0)
        agri_amt = float(payload.get("agri_amount") or 0)
        energy_amt = float(payload.get("energy_amount") or 0)
        land_amt = float(payload.get("land_amount") or 0)
        fin_amt = float(payload.get("finance_amount") or 0)
        tot_amt = float(payload.get("total_amount") or (app_amt + agri_amt + energy_amt + land_amt + fin_amt))

        status = payload.get("status") or "Open"
        approval_date = payload.get("approval_date") or ""
        if status.lower() == "approved" and not approval_date:
            approval_date = datetime.now().strftime("%Y-%m-%d")

        tipe_input = str(payload.get("tipe") or "Form").strip()
        tipe_clean = "Memo" if tipe_input.lower() == "memo" else "Form"
        attachment_file_id = payload.get("attachment_file_id") or ""
        attachment_filename = payload.get("attachment_filename") or ""

        row = conn.execute("""
            INSERT INTO sponsorship_proposal
            (company_id, nomor_proposal, tanggal, referensi, kegiatan,
             app_amount, agri_amount, energy_amount, land_amount, finance_amount,
             total_amount, diajukan_oleh, versi, status, approval_date, catatan,
             tipe, attachment_file_id, attachment_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            company_id, nomor_prop, tgl,
            payload.get("referensi") or "",
            payload.get("kegiatan") or "",
            app_amt, agri_amt, energy_amt, land_amt, fin_amt, tot_amt,
            payload.get("diajukan_oleh") or "AR/JT",
            payload.get("versi") or "",
            status, approval_date,
            payload.get("catatan") or "Nilai Sumbangan diatas netto excluded/ diluar pajak PPN/PPh",
            tipe_clean, attachment_file_id, attachment_filename
        )).fetchone()
        new_id = row[0] if row else None
        if new_id and status.lower() == "approved":
            sync_approved_proposal_to_transaksi(company_id, new_id, conn=conn)
        return {"ok": True, "pesan": "Proposal berhasil ditambahkan.", "id": new_id, "nomor_proposal": nomor_prop}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal menambahkan proposal: {str(e)}"}
    finally:
        conn.close()


def update_proposal(company_id: int, proposal_id: int, payload: dict) -> dict:
    conn = get_conn()
    try:
        app_amt = float(payload.get("app_amount") or 0)
        agri_amt = float(payload.get("agri_amount") or 0)
        energy_amt = float(payload.get("energy_amount") or 0)
        land_amt = float(payload.get("land_amount") or 0)
        fin_amt = float(payload.get("finance_amount") or 0)
        tot_amt = float(payload.get("total_amount") or (app_amt + agri_amt + energy_amt + land_amt + fin_amt))

        status = payload.get("status") or "Open"
        approval_date = payload.get("approval_date") or ""
        if status.lower() == "approved" and not approval_date:
            approval_date = datetime.now().strftime("%Y-%m-%d")

        tipe_input = str(payload.get("tipe") or "Form").strip()
        tipe_clean = "Memo" if tipe_input.lower() == "memo" else "Form"

        conn.execute("""
            UPDATE sponsorship_proposal
            SET tanggal = ?, referensi = ?, kegiatan = ?,
                app_amount = ?, agri_amount = ?, energy_amount = ?, land_amount = ?, finance_amount = ?,
                total_amount = ?, diajukan_oleh = ?, versi = ?, status = ?, approval_date = ?, catatan = ?,
                tipe = ?,
                updated_at = to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS')
            WHERE company_id = ? AND id = ?
        """, (
            payload.get("tanggal") or "",
            payload.get("referensi") or "",
            payload.get("kegiatan") or "",
            app_amt, agri_amt, energy_amt, land_amt, fin_amt, tot_amt,
            payload.get("diajukan_oleh") or "AR/JT",
            payload.get("versi") or "",
            status, approval_date,
            payload.get("catatan") or "Nilai Sumbangan diatas netto excluded/ diluar pajak PPN/PPh",
            tipe_clean,
            company_id, proposal_id
        ))
        sync_approved_proposal_to_transaksi(company_id, proposal_id, conn=conn)
        return {"ok": True, "pesan": "Proposal berhasil diperbarui."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal update proposal: {str(e)}"}
    finally:
        conn.close()


def update_proposal_status(company_id: int, proposal_id: int, status: str, approval_date: str = "") -> dict:
    conn = get_conn()
    try:
        if status.lower() == "approved" and not approval_date:
            approval_date = datetime.now().strftime("%Y-%m-%d")
        elif status.lower() != "approved":
            approval_date = ""

        conn.execute("""
            UPDATE sponsorship_proposal
            SET status = ?, approval_date = ?,
                updated_at = to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS')
            WHERE company_id = ? AND id = ?
        """, (status, approval_date, company_id, proposal_id))
        sync_approved_proposal_to_transaksi(company_id, proposal_id, conn=conn)
        return {"ok": True, "pesan": f"Status berhasil diubah menjadi {status}."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal update status: {str(e)}"}
    finally:
        conn.close()


def update_proposal_attachment(company_id: int, proposal_id: int, file_id: str, filename: str) -> dict:
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE sponsorship_proposal
            SET attachment_file_id = ?, attachment_filename = ?,
                updated_at = to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS')
            WHERE company_id = ? AND id = ?
        """, (file_id, filename, company_id, proposal_id))
        return {"ok": True, "pesan": "Attachment berhasil disimpan."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal update attachment: {str(e)}"}
    finally:
        conn.close()


def delete_proposal_attachment(company_id: int, proposal_id: int) -> dict:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT attachment_file_id FROM sponsorship_proposal WHERE company_id = ? AND id = ?",
            (company_id, proposal_id)
        ).fetchone()
        if not row:
            return {"ok": False, "pesan": "Proposal tidak ditemukan."}

        file_id = row["attachment_file_id"]
        if file_id:
            try:
                from utils.gdrive_service import delete_gdrive_file
                delete_gdrive_file(file_id)
            except Exception as e:
                print(f"Warning: gagal hapus file dari GDrive ({file_id}): {e}")

        conn.execute("""
            UPDATE sponsorship_proposal
            SET attachment_file_id = '', attachment_filename = '',
                updated_at = to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS')
            WHERE company_id = ? AND id = ?
        """, (company_id, proposal_id))
        return {"ok": True, "pesan": "Attachment berhasil dihapus."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal hapus attachment: {str(e)}"}
    finally:
        conn.close()


def delete_proposal(company_id: int, proposal_id: int) -> dict:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT attachment_file_id FROM sponsorship_proposal WHERE company_id = ? AND id = ?",
            (company_id, proposal_id)
        ).fetchone()
        if row and row["attachment_file_id"]:
            try:
                from utils.gdrive_service import delete_gdrive_file
                delete_gdrive_file(row["attachment_file_id"])
            except Exception as e:
                print(f"Warning: gagal hapus file dari GDrive: {e}")

        conn.execute("DELETE FROM sponsorship_transaksi WHERE company_id = ? AND proposal_id = ?", (company_id, proposal_id))
        conn.execute("DELETE FROM sponsorship_proposal WHERE company_id = ? AND id = ?", (company_id, proposal_id))
        return {"ok": True, "pesan": "Proposal berhasil dihapus."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal menghapus proposal: {str(e)}"}
    finally:
        conn.close()


def import_proposals_excel(company_id: int, file_stream_or_path) -> dict:
    import openpyxl
    try:
        wb = openpyxl.load_workbook(file_stream_or_path, data_only=True)
        ws = wb.active
        headers = [str(ws.cell(1, c).value or '').strip().lower() for c in range(1, ws.max_column + 1)]
        
        col_map = {}
        for idx, h in enumerate(headers, start=1):
            if "tgl" in h or "tanggal" in h: col_map["tanggal"] = idx
            elif "ref" in h: col_map["referensi"] = idx
            elif "kegiatan" in h or "acara" in h or "perihal" in h: col_map["kegiatan"] = idx
            elif h == "app": col_map["app"] = idx
            elif "agri" in h or "agro" in h: col_map["agri"] = idx
            elif "energy" in h: col_map["energy"] = idx
            elif "land" in h: col_map["land"] = idx
            elif "finance" in h or "fin" in h: col_map["finance"] = idx
            elif "total" in h or "nilai" in h: col_map["total"] = idx
            elif "diajukan" in h: col_map["diajukan_oleh"] = idx
            elif "versi" in h: col_map["versi"] = idx
            elif "status" in h: col_map["status"] = idx
            elif "approval" in h or "approved" in h: col_map["approval_date"] = idx

        count_inserted = 0
        for r in range(2, ws.max_row + 1):
            row_vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
            if not any(row_vals):
                continue
            
            raw_tgl = ws.cell(r, col_map.get("tanggal", 2)).value if "tanggal" in col_map else ws.cell(r, 2).value
            if isinstance(raw_tgl, datetime):
                tgl_str = raw_tgl.strftime('%Y-%m-%d')
            elif raw_tgl:
                tgl_str = str(raw_tgl)[:10]
            else:
                tgl_str = datetime.now().strftime('%Y-%m-%d')
            
            year = tgl_str[:4] if len(tgl_str) >= 4 else str(datetime.now().year)
            nomor_prop = generate_next_proposal_number(company_id, year)

            def get_num(key, default_col):
                c = col_map.get(key, default_col)
                val = ws.cell(r, c).value if c <= ws.max_column else 0
                try: return float(val or 0)
                except Exception: return 0.0

            app_amt = get_num("app", 5)
            agri_amt = get_num("agri", 6)
            energy_amt = get_num("energy", 7)
            land_amt = get_num("land", 8)
            fin_amt = get_num("finance", 9)
            tot_amt = get_num("total", 10)
            if tot_amt == 0:
                tot_amt = app_amt + agri_amt + energy_amt + land_amt + fin_amt

            ref_val = str(ws.cell(r, col_map.get("referensi", 3)).value or "").strip()
            keg_val = str(ws.cell(r, col_map.get("kegiatan", 4)).value or "").strip()
            diajukan = str(ws.cell(r, col_map.get("diajukan_oleh", 11)).value or "AR/JT").strip()
            versi = str(ws.cell(r, col_map.get("versi", 12)).value or "").strip()
            st_val = str(ws.cell(r, col_map.get("status", 13)).value or "Open").strip()
            st_clean = "Approved" if st_val.lower() == "approved" else ("Reject" if st_val.lower() == "reject" else "Open")
            
            raw_app_date = ws.cell(r, col_map.get("approval_date", 14)).value if "approval_date" in col_map else ""
            if isinstance(raw_app_date, datetime):
                app_date_str = raw_app_date.strftime('%Y-%m-%d')
            elif raw_app_date:
                app_date_str = str(raw_app_date)[:10]
            else:
                app_date_str = ""

            create_proposal(company_id, {
                "nomor_proposal": nomor_prop,
                "tanggal": tgl_str,
                "referensi": ref_val,
                "kegiatan": keg_val,
                "app_amount": app_amt,
                "agri_amount": agri_amt,
                "energy_amount": energy_amt,
                "land_amount": land_amt,
                "finance_amount": fin_amt,
                "total_amount": tot_amt,
                "diajukan_oleh": diajukan,
                "versi": versi,
                "status": st_clean,
                "approval_date": app_date_str
            })
            count_inserted += 1

        return {"ok": True, "pesan": f"Berhasil mengimpor {count_inserted} baris data proposal."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal mengimpor file: {str(e)}"}


def sync_proposals_excel(company_id: int, file_bytes: bytes) -> dict:
    """Sinkronisasi data proposal dari Excel: update jika nomor proposal sudah ada, insert jika baru."""
    import io
    import openpyxl
    from datetime import datetime

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal membaca file Excel: {str(e)}"}

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return {"ok": False, "pesan": "File Excel kosong atau tidak memiliki data."}

    headers = [str(c or '').strip().lower() for c in rows[0]]
    col_map = {}
    for idx, h in enumerate(headers):
        if h == "id" or "nomor" in h: col_map["nomor_proposal"] = idx
        elif "tgl" in h or "tanggal" in h: col_map["tanggal"] = idx
        elif "ref" in h: col_map["referensi"] = idx
        elif "kegiatan" in h or "acara" in h or "perihal" in h: col_map["kegiatan"] = idx
        elif h == "app": col_map["app"] = idx
        elif "agri" in h or "agro" in h: col_map["agri"] = idx
        elif "energy" in h: col_map["energy"] = idx
        elif "land" in h: col_map["land"] = idx
        elif "finance" in h or "fin" in h: col_map["finance"] = idx
        elif "total" in h or "nilai" in h: col_map["total"] = idx
        elif "diajukan" in h: col_map["diajukan_oleh"] = idx
        elif "versi" in h: col_map["versi"] = idx
        elif "status" in h: col_map["status"] = idx
        elif "approval" in h or "approved" in h: col_map["approval_date"] = idx

    conn = get_conn()
    try:
        updated_count = 0
        inserted_count = 0

        existing_rows = conn.execute(
            "SELECT id, nomor_proposal FROM sponsorship_proposal WHERE company_id = ?",
            (company_id,)
        ).fetchall()
        existing_map = {str(r["nomor_proposal"] or '').strip().upper(): r["id"] for r in existing_rows if r["nomor_proposal"]}

        items = []
        for r_idx, row in enumerate(rows[1:], start=2):
            if not any(row):
                continue

            def get_val(key, default_col):
                c = col_map.get(key, default_col)
                return row[c] if c < len(row) else None

            raw_nomor = str(get_val("nomor_proposal", 0) or '').strip()
            raw_tgl = get_val("tanggal", 1)
            raw_ref = str(get_val("referensi", 2) or '').strip()
            raw_keg = str(get_val("kegiatan", 3) or '').strip()

            if isinstance(raw_tgl, datetime):
                tgl_str = raw_tgl.strftime('%Y-%m-%d')
            elif raw_tgl:
                tgl_str = str(raw_tgl)[:10]
            else:
                tgl_str = datetime.now().strftime('%Y-%m-%d')

            def to_num(val):
                try: return float(val or 0)
                except Exception: return 0.0

            app_amt = to_num(get_val("app", 4))
            agri_amt = to_num(get_val("agri", 5))
            energy_amt = to_num(get_val("energy", 6))
            land_amt = to_num(get_val("land", 7))
            fin_amt = to_num(get_val("finance", 8))
            tot_amt = to_num(get_val("total", 9))
            if tot_amt == 0:
                tot_amt = app_amt + agri_amt + energy_amt + land_amt + fin_amt

            diajukan = str(get_val("diajukan_oleh", 10) or 'AR/JT').strip()
            versi = str(get_val("versi", 11) or '').strip()
            st_raw = str(get_val("status", 12) or 'Open').strip()
            status = "Approved" if st_raw.lower() == 'approved' else ("Reject" if st_raw.lower() == 'reject' else "Open")

            raw_app_date = get_val("approval_date", 13)
            if isinstance(raw_app_date, datetime):
                app_date_str = raw_app_date.strftime('%Y-%m-%d')
            elif raw_app_date:
                app_date_str = str(raw_app_date)[:10]
            else:
                app_date_str = ""

            prop_id = existing_map.get(raw_nomor.upper()) if raw_nomor else None

            if prop_id:
                items.append((
                    """
                    UPDATE sponsorship_proposal
                    SET tanggal = ?, referensi = ?, kegiatan = ?,
                        app_amount = ?, agri_amount = ?, energy_amount = ?, land_amount = ?, finance_amount = ?,
                        total_amount = ?, diajukan_oleh = ?, versi = ?, status = ?, approval_date = ?,
                        updated_at = to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS')
                    WHERE id = ? AND company_id = ?
                    """,
                    (tgl_str, raw_ref, raw_keg, app_amt, agri_amt, energy_amt, land_amt, fin_amt,
                     tot_amt, diajukan, versi, status, app_date_str, prop_id, company_id)
                ))
                updated_count += 1
            else:
                year = tgl_str[:4] if len(tgl_str) >= 4 else str(datetime.now().year)
                final_nomor = raw_nomor if (raw_nomor and raw_nomor.upper().startswith("PROP-")) else generate_next_proposal_number(company_id, year)
                items.append((
                    """
                    INSERT INTO sponsorship_proposal
                    (company_id, nomor_proposal, tanggal, referensi, kegiatan,
                     app_amount, agri_amount, energy_amount, land_amount, finance_amount,
                     total_amount, diajukan_oleh, versi, status, approval_date, catatan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Nilai Sumbangan diatas netto excluded/ diluar pajak PPN/PPh')
                    """,
                    (company_id, final_nomor, tgl_str, raw_ref, raw_keg,
                     app_amt, agri_amt, energy_amt, land_amt, fin_amt,
                     tot_amt, diajukan, versi, status, app_date_str)
                ))
                inserted_count += 1
                existing_map[final_nomor.upper()] = True

        if items:
            conn.batch(items)

        # Sync proposals to sponsor transactions
        if existing_map:
            for p_nomor in existing_map.keys():
                p_row = conn.execute(
                    "SELECT id, status FROM sponsorship_proposal WHERE company_id = ? AND UPPER(nomor_proposal) = ?",
                    (company_id, p_nomor.upper())
                ).fetchone()
                if p_row:
                    sync_approved_proposal_to_transaksi(company_id, p_row["id"], conn=conn)

        return {"ok": True, "pesan": f"Sync sukses: {updated_count} proposal di-update, {inserted_count} proposal baru ditambahkan."}
    except Exception as e:
        return {"ok": False, "pesan": f"Gagal sync data proposal: {str(e)}"}
    finally:
        conn.close()

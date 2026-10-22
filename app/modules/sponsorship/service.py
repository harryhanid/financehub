# modules/sponsorship/service.py
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
    # Satu panggilan executemany = satu transaksi (fhdb): sama seperti SQLite dulu, error di
    # baris mana pun (mis. cat2 NULL) membatalkan semuanya. rowcount sudah dijumlah fhdb.
    conn = get_conn()
    params = [(cat1, cat2, cat3) for cat1, cat2, cat3 in rows]
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
                items.append((
                    """
                    UPDATE sponsorship_transaksi 
                    SET cat=?, description=?, tanggal_form_sponsor=?, tanggal_payment=?,
                        cat1=?, cat2=?, cat3=?, lembaga_perorangan=?, perihal=?, amount_request=?, reff=?,
                        status=?, cat4=?, coa=?, cc_total=?, cc=?, source=?
                    WHERE id=? AND company_id=?
                    """,
                    (cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source, tx_id, company_id)
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

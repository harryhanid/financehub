import config
from database import get_conn

PROGRAM_NAME = "Sahabat ETF"


def _year_filter_sql(years, column):
    if not years:
        return "", []
    placeholders = ",".join("?" for _ in years)
    return f" AND strftime('%Y', {column}) IN ({placeholders})", [str(y) for y in years]


def _pillar_filter_sql(pillars, column):
    if not pillars:
        return "", []
    placeholders = ",".join("?" for _ in pillars)
    return f" AND {column} IN ({placeholders})", list(pillars)


def get_siswa_summary(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")

    rows = conn.execute(
        f"""
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.status,
               COALESCE(b.budget_total, 0)    AS budget_total,
               COALESCE(p.payment_total, 0)   AS payment_total,
               COALESCE(p.realisasi_total, 0) AS realisasi_total
        FROM siswa s
        LEFT JOIN (
            SELECT siswa_code, SUM(amount) AS budget_total
            FROM budget_beasiswa
            WHERE company_id = ?{budget_year_sql}
            GROUP BY siswa_code
        ) b ON b.siswa_code = s.code
        LEFT JOIN (
            SELECT siswa_code,
                   SUM(amount) AS payment_total,
                   SUM(CASE WHEN status = 'complete' THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?{payment_year_sql}{pillar_sql}
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ? AND s.program = ?
        ORDER BY s.nama
        """,
        [company_id, *budget_year_params, company_id, *payment_year_params, *pillar_params,
         company_id, PROGRAM_NAME],
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        budget = float(r["budget_total"] or 0)
        realisasi = float(r["realisasi_total"] or 0)
        result.append({
            "siswa_code":      r["code"],
            "nama":            r["nama"],
            "jenjang":         r["jenjang"],
            "angkatan":        r["angkatan"],
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   float(r["payment_total"] or 0),
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result


FAMILY_GROUPS = [
    # (family_key, [siswa_code, ...])
    ("fam1", ["5260002", "1240700", "4220003"]),  # Effendi Widjaja, Cathabell (S1 + record lama SMA)
    ("fam2", ["1240706", "1230684"]),              # Jety Widjaja, Darrell Bright Lie
    ("fam3", ["1260001", "5250001"]),              # Budi Widjaja, Birgitta Jennifer Widjaja
    ("fam4", ["5260003", "5250002"]),              # Burhanuddin Widjaja, Richard Widjaja
    ("fam5", ["5260001"]),                         # Claudia Samaoen (single)
    ("fam6", ["1210487"]),                         # Felicia Tarita Chandra (single)
    ("fam7", ["5230001"]),                         # Joshua Darren Chandra (single)
]


def _siswa_kategori_map(company_id: int, years: list = None, pillars: list = None) -> dict:
    """siswa_code -> set of cat1 dengan realisasi (payment status='complete')."""
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
    rows = conn.execute(
        f"""
        SELECT DISTINCT siswa_code, cat1
        FROM payment_beasiswa
        WHERE company_id = ? AND status = 'complete'{payment_year_sql}{pillar_sql}
        """,
        [company_id, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    result = {}
    for r in rows:
        result.setdefault(r["siswa_code"], set()).add(r["cat1"] or "(Tanpa Kategori)")
    return result


def _sort_kategori(cats: set) -> list:
    order = config.CAT1_BGT

    def key(c):
        return (order.index(c), c) if c in order else (len(order), c)
    return sorted(cats, key=key)


def get_family_summary(company_id: int, years: list = None, pillars: list = None) -> list:
    siswa_rows = get_siswa_summary(company_id, years, pillars)
    by_code = {r["siswa_code"]: r for r in siswa_rows}
    kategori_map = _siswa_kategori_map(company_id, years, pillars)

    code_to_family = {code: fk for fk, codes in FAMILY_GROUPS for code in codes}
    groups_order = list(FAMILY_GROUPS)
    for r in siswa_rows:
        code = r["siswa_code"]
        if code not in code_to_family:
            groups_order.append((code, [code]))

    families = []
    for family_key, codes in groups_order:
        existing_codes = [c for c in codes if c in by_code]
        if not existing_codes:
            continue
        members = []
        by_nama = {}
        for code in existing_codes:
            row = by_code[code]
            nama = row["nama"]
            cats = kategori_map.get(code, set())
            if nama in by_nama:
                by_nama[nama]["realisasi"] += row["realisasi_total"]
                by_nama[nama]["_kategori_set"] |= cats
            else:
                member = {"nama": nama, "realisasi": row["realisasi_total"], "_kategori_set": set(cats)}
                by_nama[nama] = member
                members.append(member)
        for m in members:
            m["kategori"] = ", ".join(_sort_kategori(m.pop("_kategori_set")))
        families.append({
            "family_key": family_key,
            "members": members,
            "total_realisasi": sum(m["realisasi"] for m in members),
        })

    family_counter = 0
    for f in families:
        if len(f["members"]) > 1:
            family_counter += 1
            f["label"] = f"Family {family_counter}"
        else:
            f["label"] = f["members"][0]["nama"]

    return [
        {
            "family_key":      f["family_key"],
            "label":           f["label"],
            "total_realisasi": f["total_realisasi"],
            "members":         f["members"],
        }
        for f in families
    ]


def get_kategori_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}
        GROUP BY b.cat1
        """,
        [company_id, PROGRAM_NAME, *budget_year_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        GROUP BY p.cat1
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    kategori = {}
    for r in budget_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["budget"] += float(r["total"] or 0)
    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["payment"] += float(r["total"] or 0)
        kategori[cat1]["realisasi"] += float(r["realisasi"] or 0)

    over_budget = [
        {
            "siswa_code":      s["siswa_code"],
            "nama":            s["nama"],
            "budget_total":    s["budget_total"],
            "realisasi_total": s["realisasi_total"],
            "selisih":         s["realisasi_total"] - s["budget_total"],
        }
        for s in get_siswa_summary(company_id, years, pillars)
        if s["realisasi_total"] > s["budget_total"]
    ]

    return {"kategori": list(kategori.values()), "over_budget": over_budget}


def get_siswa_detail(company_id: int, siswa_code: str) -> list:
    conn = get_conn()
    budget_rows = conn.execute(
        "SELECT tanggal, cat1, cat2, amount FROM budget_beasiswa "
        "WHERE company_id = ? AND siswa_code = ? ORDER BY tanggal",
        (company_id, siswa_code),
    ).fetchall()
    payment_rows = conn.execute(
        "SELECT tanggal, cat1, cat2, amount, status FROM payment_beasiswa "
        "WHERE company_id = ? AND siswa_code = ? ORDER BY tanggal",
        (company_id, siswa_code),
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "tanggal": r["tanggal"], "cat1": r["cat1"],
                     "cat2": r["cat2"], "amount": r["amount"], "status": ""})
    for r in payment_rows:
        rows.append({"sumber": "Payment", "tanggal": r["tanggal"], "cat1": r["cat1"],
                     "cat2": r["cat2"], "amount": r["amount"], "status": r["status"]})
    rows.sort(key=lambda r: r["tanggal"] or "")
    return rows


def get_all_transactions(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, b.tanggal, b.cat1, b.cat2, b.amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}
        ORDER BY s.nama, b.tanggal
        """,
        [company_id, PROGRAM_NAME, *budget_year_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, p.tanggal, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        ORDER BY s.nama, p.tanggal
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": ""})
    for r in payment_rows:
        rows.append({"sumber": "Payment", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": r["status"]})
    return rows


def get_latest_payments(company_id: int, years: list = None, pillars: list = None,
                         kategori: str = None, limit: int = 10) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    kategori_sql, kategori_params = (" AND p.cat1 = ?", [kategori]) if kategori else ("", [])

    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}{kategori_sql}
        ORDER BY p.tanggal DESC, p.id DESC
        LIMIT ?
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params, *kategori_params, limit],
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_available_years(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT strftime('%Y', b.tanggal) AS y
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''
        UNION
        SELECT DISTINCT strftime('%Y', p.tanggal) AS y
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal IS NOT NULL AND p.tanggal != ''
        """,
        (company_id, PROGRAM_NAME, company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return sorted({int(r["y"]) for r in rows if r["y"]})


def get_available_pillars(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT p.pillar
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.pillar IS NOT NULL AND p.pillar != ''
        ORDER BY p.pillar
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return [r["pillar"] for r in rows]


def get_pillar_breakdown(company_id: int, years: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")

    budget_rows = conn.execute(
        f"""
        SELECT b.pillar, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}
        GROUP BY b.pillar
        """,
        [company_id, PROGRAM_NAME, *budget_year_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.pillar,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}
        GROUP BY p.pillar
        """,
        [company_id, PROGRAM_NAME, *payment_year_params],
    ).fetchall()
    conn.close()

    pillar_map = {}
    for r in budget_rows:
        pillar = r["pillar"] or "(Tanpa Pillar)"
        pillar_map.setdefault(pillar, {"pillar": pillar, "budget": 0.0, "realisasi": 0.0})
        pillar_map[pillar]["budget"] += float(r["total"] or 0)
    for r in payment_rows:
        pillar = r["pillar"] or "(Tanpa Pillar)"
        pillar_map.setdefault(pillar, {"pillar": pillar, "budget": 0.0, "realisasi": 0.0})
        pillar_map[pillar]["realisasi"] += float(r["realisasi"] or 0)

    result = list(pillar_map.values())
    for p in result:
        p["sisa"] = p["budget"] - p["realisasi"]
    result.sort(key=lambda p: p["pillar"])
    return result


def get_yearly_breakdown(company_id: int, pillars: list = None) -> list:
    conn = get_conn()
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, SUM(p.amount) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{pillar_sql}
        GROUP BY tahun
        ORDER BY tahun
        """,
        [company_id, PROGRAM_NAME, *pillar_params],
    ).fetchall()
    conn.close()
    return [{"tahun": int(r["tahun"]), "realisasi": float(r["realisasi"] or 0)} for r in rows if r["tahun"]]


def get_monthly_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    if not years:
        return {"chart_year": None, "months": [], "comparison": []}

    chart_year = max(years)
    conn = get_conn()

    budget_rows = conn.execute(
        """
        SELECT CAST(strftime('%m', b.tanggal) AS INTEGER) AS bulan, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND strftime('%Y', b.tanggal) = ?
        GROUP BY bulan
        """,
        (company_id, PROGRAM_NAME, str(chart_year)),
    ).fetchall()

    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    year_placeholders = ",".join("?" for _ in years)
    realisasi_rows = conn.execute(
        f"""
        SELECT strftime('%Y', p.tanggal) AS tahun, CAST(strftime('%m', p.tanggal) AS INTEGER) AS bulan,
               SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'
              AND strftime('%Y', p.tanggal) IN ({year_placeholders}){pillar_sql}
        GROUP BY tahun, bulan
        """,
        [company_id, PROGRAM_NAME, *[str(y) for y in years], *pillar_params],
    ).fetchall()
    conn.close()

    budget_by_month = {r["bulan"]: float(r["total"] or 0) for r in budget_rows}
    realisasi_by_year_month = {}
    for r in realisasi_rows:
        realisasi_by_year_month.setdefault(r["tahun"], {})[r["bulan"]] = float(r["total"] or 0)

    months = [
        {
            "bulan": m,
            "budget": budget_by_month.get(m, 0.0),
            "realisasi": realisasi_by_year_month.get(str(chart_year), {}).get(m, 0.0),
        }
        for m in range(1, 13)
    ]
    comparison = [
        {
            "bulan": m,
            "per_tahun": {str(y): realisasi_by_year_month.get(str(y), {}).get(m, 0.0) for y in years},
        }
        for m in range(1, 13)
    ]
    return {"chart_year": chart_year, "months": months, "comparison": comparison}

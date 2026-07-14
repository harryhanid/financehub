from database import get_conn

PROGRAM_NAME = "Sahabat ETF"


def get_siswa_summary(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.status,
               COALESCE(b.budget_total, 0)    AS budget_total,
               COALESCE(p.payment_total, 0)   AS payment_total,
               COALESCE(p.realisasi_total, 0) AS realisasi_total
        FROM siswa s
        LEFT JOIN (
            SELECT siswa_code, SUM(amount) AS budget_total
            FROM budget_beasiswa
            WHERE company_id = ?
            GROUP BY siswa_code
        ) b ON b.siswa_code = s.code
        LEFT JOIN (
            SELECT siswa_code,
                   SUM(amount) AS payment_total,
                   SUM(CASE WHEN status = 'complete' THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ? AND s.program = ?
        ORDER BY s.nama
        """,
        (company_id, company_id, company_id, PROGRAM_NAME),
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


def get_kategori_breakdown(company_id: int) -> dict:
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?
        GROUP BY b.cat1
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?
        GROUP BY p.cat1
        """,
        (company_id, PROGRAM_NAME),
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
        for s in get_siswa_summary(company_id)
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


def get_all_transactions(company_id: int) -> list:
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT s.code AS siswa_code, s.nama, b.tanggal, b.cat1, b.cat2, b.amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?
        ORDER BY s.nama, b.tanggal
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT s.code AS siswa_code, s.nama, p.tanggal, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?
        ORDER BY s.nama, p.tanggal
        """,
        (company_id, PROGRAM_NAME),
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

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
        budget = r["budget_total"] or 0
        realisasi = r["realisasi_total"] or 0
        result.append({
            "siswa_code":      r["code"],
            "nama":            r["nama"],
            "jenjang":         r["jenjang"],
            "angkatan":        r["angkatan"],
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   r["payment_total"] or 0,
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result

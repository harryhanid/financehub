from datetime import datetime
from database import get_conn


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def get_applications(company_id: int) -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pa.*, pm.memo_number, pm.total_amount, pm.status as memo_status
           FROM payment_application pa
           JOIN payment_memo pm ON pm.id = pa.memo_id
           WHERE pa.company_id = ?
           ORDER BY pa.created_at DESC""",
        (company_id,)
    ).fetchall()]
    conn.close()
    for r in rows:
        if r.get("submitted_at") and r.get("actual_payment_date"):
            r["tat_days"] = _workday_diff(r["submitted_at"][:10], r["actual_payment_date"][:10])
        else:
            r["tat_days"] = None
    return rows


def _workday_diff(start: str, end: str) -> int:
    from datetime import date, timedelta
    d1 = date.fromisoformat(start)
    d2 = date.fromisoformat(end)
    if d2 < d1:
        return 0
    count   = 0
    current = d1
    while current <= d2:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count - 1


def create_application(company_id: int, memo_id: int, tanggal_pengajuan: str,
                        target_payment_date: str, notes: str) -> dict:
    conn = get_conn()
    memo = conn.execute(
        "SELECT id, status FROM payment_memo WHERE id=? AND company_id=?",
        (memo_id, company_id)
    ).fetchone()
    if not memo:
        conn.close()
        return {"ok": False, "pesan": "Memo tidak ditemukan."}
    if memo["status"] not in ("approved", "paid"):
        conn.close()
        return {"ok": False, "pesan": "Memo harus berstatus 'approved' sebelum diajukan."}

    year  = (tanggal_pengajuan or datetime.now().strftime("%Y"))[:4]
    count = conn.execute(
        "SELECT COUNT(*) FROM payment_application WHERE company_id=?", (company_id,)
    ).fetchone()[0]
    app_number = f"APP/{company_id}/{year}/{count+1:04d}"

    cur = conn.execute(
        """INSERT INTO payment_application
           (company_id, memo_id, application_number, submitted_at, target_payment_date, notes, status, created_at)
           VALUES (?,?,?,?,?,?,'pending',?)""",
        (company_id, memo_id, app_number, tanggal_pengajuan, target_payment_date, notes, _ts())
    )
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "application_id": app_id, "application_number": app_number,
            "pesan": f"Payment application {app_number} berhasil dibuat."}


def update_actual_payment(app_id: int, actual_date: str, company_id: int = 0) -> dict:
    conn = get_conn()
    row  = conn.execute(
        "SELECT submitted_at FROM payment_application WHERE id=? AND company_id=?",
        (app_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Application tidak ditemukan."}
    tat = None
    if row["submitted_at"]:
        tat = _workday_diff(row["submitted_at"][:10], actual_date)
    conn.execute(
        "UPDATE payment_application SET actual_payment_date=?, tat_days=?, status='completed', updated_at=? WHERE id=? AND company_id=?",
        (actual_date, tat, _ts(), app_id, company_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Tanggal pembayaran aktual disimpan. TAT: {tat} hari kerja."}

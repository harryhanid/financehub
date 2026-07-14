from database import get_conn


def get_setf_rows(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, pam_no, pam_date, keterangan, total_amount, status, tanggal_bayar "
        "FROM pam_records WHERE pillar = 'SETF' AND company_id = ?",
        (company_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def split_by_status(rows: list) -> tuple:
    open_rows = [r for r in rows if r["status"] in ("open", "on_process")]
    complete_rows = [r for r in rows if r["status"] == "complete"]

    open_rows.sort(key=lambda r: r["pam_date"] or "")

    for r in complete_rows:
        r["_date"] = r["tanggal_bayar"] or r["pam_date"]
    complete_rows.sort(key=lambda r: r["_date"] or "")

    return open_rows, complete_rows


def compute_running_balance(complete_rows: list) -> dict:
    saldo = 0.0
    total_pemasukan = 0.0
    total_pengeluaran = 0.0
    for r in complete_rows:
        amount = r["total_amount"] or 0
        pemasukan = -amount if amount < 0 else 0
        pengeluaran = amount if amount > 0 else 0
        saldo -= amount
        r["pemasukan"] = pemasukan
        r["pengeluaran"] = pengeluaran
        r["saldo_berjalan"] = saldo
        total_pemasukan += pemasukan
        total_pengeluaran += pengeluaran
    return {
        "rows": complete_rows,
        "saldo_current": saldo,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
    }

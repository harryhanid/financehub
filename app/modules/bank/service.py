from datetime import datetime
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


def compute_running_balance(rows: list) -> dict:
    saldo = 0.0
    total_pemasukan = 0.0
    total_pengeluaran = 0.0
    for r in rows:
        jumlah = r["jumlah"] or 0
        if r["jenis"] == "pemasukan":
            saldo += jumlah
            r["pemasukan"] = jumlah
            r["pengeluaran"] = 0
            total_pemasukan += jumlah
        else:
            saldo -= jumlah
            r["pemasukan"] = 0
            r["pengeluaran"] = jumlah
            total_pengeluaran += jumlah
        r["saldo_berjalan"] = saldo
    return {
        "rows": rows,
        "saldo_current": saldo,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
    }


def get_available_years(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y', tanggal) AS yr FROM bank_setf "
        "WHERE company_id = ? ORDER BY yr DESC",
        (company_id,),
    ).fetchall()
    conn.close()
    return [int(r["yr"]) for r in rows if r["yr"]]


def resolve_period(bulan_param, tahun_param, today=None):
    today = today or datetime.now()

    if bulan_param is None:
        bulan = today.month
    elif bulan_param == "all":
        bulan = None
    else:
        bulan = int(bulan_param)

    if tahun_param is None:
        tahun = today.year
    elif tahun_param == "all":
        tahun = None
    else:
        tahun = int(tahun_param)

    return bulan, tahun


def filter_period(rows: list, bulan, tahun) -> list:
    if bulan is None and tahun is None:
        return rows
    result = []
    for r in rows:
        date = r.get("tanggal")
        if not date:
            continue
        y, m = int(date[0:4]), int(date[5:7])
        if bulan is not None and m != bulan:
            continue
        if tahun is not None and y != tahun:
            continue
        result.append(r)
    return result


def sync_pam_to_bank_setf(pam_id: int) -> None:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, company_id, tanggal_bayar, pam_date, total_amount, keterangan, pillar "
        "FROM pam_records WHERE id=?",
        (pam_id,)
    ).fetchone()

    if not row or row["pillar"] != "SETF":
        conn.close()
        return

    exists = conn.execute(
        "SELECT 1 FROM bank_setf WHERE pam_record_id=?", (pam_id,)
    ).fetchone()

    if not exists:
        tanggal = row["tanggal_bayar"] or row["pam_date"]
        conn.execute(
            "INSERT INTO bank_setf (company_id, tanggal, jenis, jumlah, keterangan, source, pam_record_id) "
            "VALUES (?, ?, 'pengeluaran', ?, ?, 'pam', ?)",
            (row["company_id"], tanggal, row["total_amount"], row["keterangan"], pam_id)
        )
        conn.commit()

    conn.close()


def get_bank_setf_rows(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, tanggal, jenis, jumlah, keterangan, source, pam_record_id "
        "FROM bank_setf WHERE company_id = ? ORDER BY tanggal, id",
        (company_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

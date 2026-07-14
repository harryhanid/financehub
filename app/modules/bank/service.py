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


def get_available_years(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y', tanggal_bayar) AS yr FROM pam_records "
        "WHERE pillar = 'SETF' AND company_id = ? AND status = 'complete' AND tanggal_bayar IS NOT NULL "
        "ORDER BY yr DESC",
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
        date = r.get("_date")
        if not date:
            continue
        y, m = int(date[0:4]), int(date[5:7])
        if bulan is not None and m != bulan:
            continue
        if tahun is not None and y != tahun:
            continue
        result.append(r)
    return result

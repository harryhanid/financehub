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
    open_rows = [r for r in rows if r["status"] in ("open", "on_process", "partial")]
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
        "SELECT DISTINCT fh_strftime('%Y', tanggal) AS yr FROM bank_setf "
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
        try:
            bulan = int(bulan_param)
        except (TypeError, ValueError):
            bulan = today.month

    if tahun_param is None:
        tahun = today.year
    elif tahun_param == "all":
        tahun = None
    else:
        try:
            tahun = int(tahun_param)
        except (TypeError, ValueError):
            tahun = today.year

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
    """Keep bank_setf in sync with a SETF pam_records row, incrementally.

    Idempotent and safe to call after ANY pam_records mutation (status
    change, field edit, a partial-completion batch) — not just on full
    completion. Reconciles by DELTA rather than upserting one lump-sum row:

    - pillar=='SETF' and status in ('complete','partial'): compare the
      current sum of 'complete' payment_beasiswa lines for this PAM against
      what's already recorded in bank_setf for it. If more has been paid
      since the last sync, insert a NEW row for just that difference, dated
      to the PAM's current tanggal_bayar — so a PAM paid in several batches
      (see mark_beasiswa_lines_complete) produces one ledger row per batch,
      each showing the actual date money moved, instead of one lump sum that
      only appears once the whole PAM finally completes.
    - otherwise (reverted away from complete/partial, or pillar changed, or
      the paid total went down): collapse all of this PAM's rows back down
      to match — removing them if nothing is paid, or replacing them with a
      single row for the corrected total. Without this, reverting a
      completion or correcting an amount downward left stale ledger rows
      permanently out of sync with the actual PAM.
    """
    # Postgres: baca + hitung delta + tulis jalan atomik dalam satu fungsi plpgsql
    # (db_migrations/0004_fn_bank.sql) di bawah advisory lock per pam_id, supaya dua panggilan
    # bersamaan tidak menyisipkan delta dua kali dan cabang DELETE+INSERT tidak berhenti di tengah.
    conn = get_conn()
    try:
        conn.execute("SELECT fn_sync_pam_to_bank_setf(?)", (pam_id,))
    finally:
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


def _validate_transaksi(tanggal, jenis, jumlah):
    if not tanggal:
        return "Tanggal wajib diisi."
    if jenis not in ("pemasukan", "pengeluaran"):
        return "Jenis tidak valid."
    try:
        jumlah = float(jumlah)
    except (TypeError, ValueError):
        return "Jumlah tidak valid."
    if jumlah <= 0:
        return "Jumlah harus lebih besar dari 0."
    return None


def add_transaksi(company_id: int, tanggal: str, jenis: str, jumlah, keterangan: str) -> dict:
    error = _validate_transaksi(tanggal, jenis, jumlah)
    if error:
        return {"ok": False, "pesan": error}
    conn = get_conn()
    conn.execute(
        "INSERT INTO bank_setf (company_id, tanggal, jenis, jumlah, keterangan, source) "
        "VALUES (?, ?, ?, ?, ?, 'manual')",
        (company_id, tanggal, jenis, float(jumlah), keterangan),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Transaksi berhasil ditambahkan."}


def update_transaksi(row_id: int, company_id: int, tanggal: str, jenis: str, jumlah, keterangan: str) -> dict:
    """Single atomic UPDATE...WHERE + rowcount, not a separate SELECT then
    UPDATE — the old two-step check-then-act had a window where a
    concurrent delete_transaksi (waitress runs multi-threaded) could remove
    the row between the check and the write, leaving the UPDATE a silent
    no-op that still reported success."""
    error = _validate_transaksi(tanggal, jenis, jumlah)
    if error:
        return {"ok": False, "pesan": error}
    conn = get_conn()
    cur = conn.execute(
        "UPDATE bank_setf SET tanggal=?, jenis=?, jumlah=?, keterangan=?, updated_at=to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS') "
        "WHERE id=? AND company_id=?",
        (tanggal, jenis, float(jumlah), keterangan, row_id, company_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}
    return {"ok": True, "pesan": "Transaksi berhasil diperbarui."}


def delete_transaksi(row_id: int, company_id: int) -> dict:
    conn = get_conn()
    cur = conn.execute("DELETE FROM bank_setf WHERE id=? AND company_id=?", (row_id, company_id))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return {"ok": False, "pesan": "Transaksi tidak ditemukan."}
    return {"ok": True, "pesan": "Transaksi berhasil dihapus."}

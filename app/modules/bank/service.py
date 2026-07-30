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
    conn = get_conn()
    pam = conn.execute(
        "SELECT id, company_id, pam_no, tanggal_bayar, pam_date, keterangan, pillar, status, total_amount "
        "FROM pam_records WHERE id=?",
        (pam_id,)
    ).fetchone()
    if not pam:
        conn.close()
        return

    if pam["pillar"] != "SETF" or pam["status"] not in ("complete", "partial"):
        conn.execute("DELETE FROM bank_setf WHERE pam_record_id=? AND source='pam'", (pam_id,))
        conn.commit()
        conn.close()
        return

    # Only beasiswa-sourced PAMs break their total into payment_beasiswa lines
    # (and only those support partial completion via mark_beasiswa_lines_complete).
    # 'others'/'tagihan'/'sponsor'-sourced PAMs carry their whole amount
    # directly on pam_records.total_amount with zero payment_beasiswa rows —
    # for those, "paid" is simply the full total once status is 'complete'
    # (they can never be 'partial').
    has_beasiswa_lines = conn.execute(
        "SELECT 1 FROM payment_beasiswa WHERE pam=? AND company_id=? LIMIT 1",
        (pam["pam_no"], pam["company_id"])
    ).fetchone() is not None

    if has_beasiswa_lines:
        paid_total = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_beasiswa "
            "WHERE pam=? AND company_id=? AND status='complete'",
            (pam["pam_no"], pam["company_id"])
        ).fetchone()[0]
    else:
        paid_total = pam["total_amount"] if pam["status"] == "complete" else 0
    recorded_total = conn.execute(
        "SELECT COALESCE(SUM(jumlah),0) FROM bank_setf WHERE pam_record_id=? AND source='pam'",
        (pam_id,)
    ).fetchone()[0]

    # pam_records.tanggal_bayar is only set once the WHOLE PAM completes (see
    # mark_beasiswa_lines_complete), so it can't date a partial batch. Each
    # line's own tgl_Paid_SETF is set at completion time — the most recent one
    # is the actual date this batch (the delta) was paid.
    latest_paid = conn.execute(
        "SELECT MAX(tgl_Paid_SETF) FROM payment_beasiswa "
        "WHERE pam=? AND company_id=? AND status='complete' AND tgl_Paid_SETF IS NOT NULL",
        (pam["pam_no"], pam["company_id"])
    ).fetchone()[0]
    delta = paid_total - recorded_total
    tanggal = latest_paid or pam["tanggal_bayar"] or pam["pam_date"]

    if delta > 0.01:
        conn.execute(
            "INSERT INTO bank_setf (company_id, tanggal, jenis, jumlah, keterangan, source, pam_record_id) "
            "VALUES (?, ?, 'pengeluaran', ?, ?, 'pam', ?)",
            (pam["company_id"], tanggal, delta, pam["keterangan"], pam_id)
        )
        conn.commit()
    elif delta < -0.01:
        # Paid total dropped (amount corrected down, or a line's completion
        # reverted) — collapse existing batch rows and re-insert one row for
        # whatever remains, rather than trying to guess which batch to shrink.
        conn.execute("DELETE FROM bank_setf WHERE pam_record_id=? AND source='pam'", (pam_id,))
        if paid_total > 0.01:
            conn.execute(
                "INSERT INTO bank_setf (company_id, tanggal, jenis, jumlah, keterangan, source, pam_record_id) "
                "VALUES (?, ?, 'pengeluaran', ?, ?, 'pam', ?)",
                (pam["company_id"], tanggal, paid_total, pam["keterangan"], pam_id)
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
        "UPDATE bank_setf SET tanggal=?, jenis=?, jumlah=?, keterangan=?, updated_at=datetime('now') "
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

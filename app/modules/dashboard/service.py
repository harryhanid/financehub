# modules/dashboard/service.py
from datetime import date
from database import get_conn

# (tab, pillar_label, pa_table, lines_table) — mirrors _TAB_CFG in
# modules/etf_payment_application/service.py
PA_SOURCES = [
    ("agri", "AGRI", "etf_pa",  "etf_pa_lines"),
    ("app",  "APP",  "app_pa",  "app_pa_lines"),
    ("sml",  "SML",  "sml_pa",  "sml_pa_lines"),
    ("setf", "SETF", "setf_pa", "setf_pa_lines"),
]

# pam_records.pillar → lines table — mirrors _PILLAR_LINES_TABLE in
# modules/payment_memo/service.py
PAM_LINES_TABLE = {
    "AGRI":   "agri_pam_lines",
    "APP":    "app_pam_lines",
    "LAND":   "land_pam_lines",
    "ENERGY": "energy_pam_lines",
    "SETF":   "setf_pam_lines",
}

# Ordered approval chains; label = the stage being WAITED ON when that
# column is the first empty one (approved spec Section 3).
PA_STAGE_CHAIN = [
    ("doc_received_by_educ",  "Dokumen diterima Educ"),
    ("received_pa_from_educ", "PA diterima dari Educ"),
    ("checked_by_fincon",     "Pengecekan Fincon"),
    ("approved_by_htj_1",     "Approval HTJ 1"),
    ("send_pa_back_to_educ",  "PA dikirim balik ke Educ"),
    ("pa_received_by_po_fin", "PA diterima PO Finance"),
    ("approval_by_htj_2",     "Approval HTJ 2"),
    ("tanggal_bayar",         "Menunggu pembayaran"),
]

PAM_LINE_CHAIN = [
    ("tgl_terima_doc",     "Terima dokumen"),
    ("tgl_proses",         "Proses"),
    ("tgl_verifikasi_tax", "Verifikasi tax"),
    ("tgl_approval_1",     "Approval 1"),
    ("tgl_approval_2",     "Approval 2"),
    ("tgl_approval_3",     "Approval 3"),
    ("tgl_kirim",          "Kirim"),
]


def _parse_date(val):
    """TEXT column → date, or None. Tolerates timestamps and junk."""
    if not val:
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except ValueError:
        return None


def _walk_chain(row: dict, chain) -> tuple:
    """Return (awaited_label, last_filled_date).

    awaited_label = label of the FIRST empty column in chain order
    (None if every column is filled). last_filled_date = MAX of all
    parseable filled dates (None if none parse)."""
    awaited = None
    last_filled = None
    for col, label in chain:
        val = row.get(col)
        if val in (None, ""):
            if awaited is None:
                awaited = label
        else:
            d = _parse_date(val)
            if d and (last_filled is None or d > last_filled):
                last_filled = d
    return awaited, last_filled


def _days_since(baseline, today) -> int:
    if baseline is None or baseline > today:
        return 0
    return (today - baseline).days


def _pa_actions(conn, company_id: int, today: date) -> list:
    items = []
    for tab, pillar, pa_tbl, lines_tbl in PA_SOURCES:
        rows = conn.execute(
            f"""SELECT p.*,
                       GROUP_CONCAT(DISTINCT s.nama)         AS nama_student,
                       COALESCE(SUM(l.jumlah_pembayaran), 0) AS total_bayar
                FROM {pa_tbl} p
                LEFT JOIN {lines_tbl} l ON l.pa_id = p.id
                LEFT JOIN siswa s ON s.id = l.student_id
                WHERE p.company_id = ? AND p.status IN ('open','on_process')
                GROUP BY p.id""",
            (company_id,),
        ).fetchall()
        for r in rows:
            row = dict(r)
            awaited, last_filled = _walk_chain(row, PA_STAGE_CHAIN)
            baseline = (last_filled
                        or _parse_date(row.get("tgl_payment_application"))
                        or _parse_date(row.get("created_at")))
            items.append({
                "tab":         tab,
                "pillar":      pillar,
                "pa_id":       row["id"],
                "pa_number":   row["pa_number"],
                "nama_student": row["nama_student"] or "-",
                "stage":       awaited or "Semua tanggal terisi",
                "days":        _days_since(baseline, today),
                "total":       row["total_bayar"],
                "status":      row["status"],
            })
    return items


def _pam_actions(conn, company_id: int, today: date) -> list:
    memos = [dict(r) for r in conn.execute(
        "SELECT * FROM pam_records WHERE company_id = ? AND status = 'open'",
        (company_id,),
    ).fetchall()]

    # Fetch open memos' vendor lines, grouped per memo id
    lines_by_memo = {}
    for pillar, tbl in PAM_LINES_TABLE.items():
        ids = [m["id"] for m in memos if (m.get("pillar") or "").upper() == pillar]
        if not ids:
            continue
        marks = ",".join("?" * len(ids))
        for lr in conn.execute(
            f"SELECT * FROM {tbl} WHERE pam_id IN ({marks})", ids
        ).fetchall():
            lines_by_memo.setdefault(lr["pam_id"], []).append(dict(lr))

    items = []
    for m in memos:
        lines = lines_by_memo.get(m["id"], [])
        memo_baseline = (_parse_date(m.get("pam_date"))
                         or _parse_date(m.get("created_at")))
        done = [l for l in lines if l.get("tgl_kirim") not in (None, "")]
        open_lines = [l for l in lines if l.get("tgl_kirim") in (None, "")]

        if not lines:
            stage, vendor = "Belum ada vendor line", ""
            days = _days_since(memo_baseline, today)
        elif open_lines:
            # Longest-stuck unfinished line wins (approved Section 3)
            worst = None
            for l in open_lines:
                awaited, last_filled = _walk_chain(l, PAM_LINE_CHAIN)
                d = _days_since(last_filled or memo_baseline, today)
                if worst is None or d > worst[0]:
                    worst = (d, awaited or "Kirim", l.get("nama_vendor") or "")
            days, stage, vendor = worst
        else:
            stage, vendor = "Menunggu pembayaran", ""
            kirim_dates = [d for d in (_parse_date(l.get("tgl_kirim")) for l in lines) if d]
            days = _days_since(max(kirim_dates) if kirim_dates else memo_baseline, today)

        items.append({
            "pam_id":       m["id"],
            "pam_no":       m["pam_no"],
            "pillar":       (m.get("pillar") or "").upper(),
            "keterangan":   m.get("keterangan") or m.get("requestors_name") or "",
            "vendor_done":  len(done),
            "vendor_total": len(lines),
            "stage":        stage,
            "vendor":       vendor,
            "days":         days,
            "total_amount": m.get("total_amount") or 0,
            "due_date":     m.get("due_date") or "",
        })
    return items


def get_etf_dashboard_data(company_id: int) -> dict:
    today = date.today()
    conn = get_conn()

    pa_items  = _pa_actions(conn, company_id, today)
    pam_items = _pam_actions(conn, company_id, today)

    paid_this_month = conn.execute(
        """SELECT COALESCE(SUM(total_amount), 0) FROM pam_records
           WHERE company_id = ? AND status = 'complete'
             AND substr(COALESCE(tanggal_bayar,''), 1, 7)
                 = strftime('%Y-%m', 'now', 'localtime')""",
        (company_id,),
    ).fetchone()[0]
    conn.close()

    sort_key = lambda it: (-it["days"], -(it["total"] if "total" in it else it["total_amount"]))
    pa_items.sort(key=sort_key)
    pam_items.sort(key=sort_key)

    all_ages = [it["days"] for it in pa_items] + [it["days"] for it in pam_items]
    avg_age  = round(sum(all_ages) / len(all_ages)) if all_ages else 0

    return {
        "pa_active_total":   len(pa_items),
        "pa_open":           sum(1 for it in pa_items if it["status"] == "open"),
        "pa_on_process":     sum(1 for it in pa_items if it["status"] == "on_process"),
        "pam_open":          len(pam_items),
        "paid_this_month":   paid_this_month,
        "avg_age_days":      avg_age,
        "pa_actions":        pa_items[:10],
        "pam_actions":       pam_items[:10],
        "pa_total_actions":  len(pa_items),
        "pam_total_actions": len(pam_items),
    }

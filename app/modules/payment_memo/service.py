import re
import calendar
import config
from datetime import datetime
from database import get_conn


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def generate_memo_number(company_id: int, company_code: str, year: str) -> str:
    prefix  = f"PAM/{company_code}/{year}/"
    pattern = re.compile(rf"PAM/{re.escape(company_code)}/{re.escape(year)}/(\d+)")
    conn = get_conn()
    rows = conn.execute(
        "SELECT memo_number FROM payment_memo WHERE company_id = ? AND memo_number LIKE ?",
        (company_id, prefix + "%")
    ).fetchall()
    conn.close()
    max_seq = 0
    for row in rows:
        m = pattern.match(row["memo_number"])
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq
    return f"{prefix}{max_seq + 1:03d}"


def get_draft_payments(company_id: int) -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.*, s.nama, s.bank, s.norek, s.namarek
           FROM payment_beasiswa pb
           LEFT JOIN siswa s ON s.company_id = pb.company_id AND s.code = pb.siswa_code
           WHERE pb.company_id = ? AND pb.status = 'draft'
           ORDER BY pb.tanggal DESC""",
        (company_id,)
    ).fetchall()]
    conn.close()
    return rows


def create_memo(company_id: int, company_code: str, tanggal: str,
                notes: str, created_by: str, items: list) -> dict:
    if not items:
        return {"ok": False, "pesan": "Pilih minimal 1 payment untuk dimasukkan ke memo."}
    year        = (tanggal or datetime.now().strftime("%Y"))[:4]
    memo_number = generate_memo_number(company_id, company_code, year)
    total       = sum(float(item.get("amount", 0)) for item in items)
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO payment_memo
               (company_id, memo_number, tanggal, total_amount, status, notes, created_by, created_at)
               VALUES (?,?,?,?,'draft',?,?,?)""",
            (company_id, memo_number, tanggal, total, notes, created_by, _ts())
        )
        memo_id = cur.lastrowid
        for item in items:
            conn.execute(
                """INSERT INTO payment_memo_items
                   (memo_id, source_module, source_id, description, amount, vendor, bank_account)
                   VALUES (?,?,?,?,?,?,?)""",
                (memo_id,
                 item.get("source_module", "beasiswa"),
                 item["source_id"],
                 item.get("description", ""),
                 float(item.get("amount", 0)),
                 item.get("vendor", ""),
                 item.get("bank_account", ""))
            )
            if item.get("source_module", "beasiswa") == "beasiswa":
                conn.execute(
                    "UPDATE payment_beasiswa SET status='in_memo', memo_id=? WHERE id=?",
                    (memo_id, item["source_id"])
                )
        conn.commit()
        return {"ok": True, "memo_id": memo_id, "memo_number": memo_number,
                "pesan": f"Memo {memo_number} berhasil dibuat."}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "pesan": f"Gagal membuat memo: {e}"}
    finally:
        conn.close()


def get_memo_list(company_id: int, status: str = "") -> list:
    sql    = "SELECT * FROM payment_memo WHERE company_id = ?"
    params = [company_id]
    if status:
        sql    += " AND status = ?"
        params += [status]
    sql += " ORDER BY created_at DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_memo_detail(memo_id: int, company_id: int) -> dict | None:
    conn = get_conn()
    memo = conn.execute(
        "SELECT * FROM payment_memo WHERE id = ? AND company_id = ?",
        (memo_id, company_id)
    ).fetchone()
    if not memo:
        conn.close()
        return None
    items = [dict(r) for r in conn.execute(
        "SELECT * FROM payment_memo_items WHERE memo_id = ?", (memo_id,)
    ).fetchall()]
    conn.close()
    return {**dict(memo), "items": items}


def update_memo_status(memo_id: int, new_status: str, by_user: str, company_id: int = 0) -> dict:
    allowed = {"draft", "submitted", "approved", "paid"}
    if new_status not in allowed:
        return {"ok": False, "pesan": f"Status '{new_status}' tidak valid."}
    conn = get_conn()
    memo = conn.execute(
        "SELECT id FROM payment_memo WHERE id=? AND company_id=?",
        (memo_id, company_id)
    ).fetchone()
    if not memo:
        conn.close()
        return {"ok": False, "pesan": "Memo tidak ditemukan."}
    now  = _ts()
    if new_status == "approved":
        conn.execute(
            "UPDATE payment_memo SET status=?, approved_by=?, approved_at=?, updated_at=? WHERE id=? AND company_id=?",
            (new_status, by_user, now, now, memo_id, company_id)
        )
    elif new_status == "paid":
        conn.execute(
            "UPDATE payment_memo SET status=?, updated_at=? WHERE id=? AND company_id=?",
            (new_status, now, memo_id, company_id)
        )
        items = conn.execute(
            "SELECT source_id, source_module FROM payment_memo_items WHERE memo_id=?",
            (memo_id,)
        ).fetchall()
        for item in items:
            if item["source_module"] == "beasiswa":
                conn.execute(
                    "UPDATE payment_beasiswa SET status='paid' WHERE id=?",
                    (item["source_id"],)
                )
    else:
        conn.execute(
            "UPDATE payment_memo SET status=?, updated_at=? WHERE id=? AND company_id=?",
            (new_status, now, memo_id, company_id)
        )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Status memo diubah ke '{new_status}'."}


# ── PAM helpers ─────────────────────────────────────────────────────────────

def _add_one_month(date_str: str) -> str:
    try:
        dt    = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month % 12 + 1
        year  = dt.year + (1 if dt.month == 12 else 0)
        day   = min(dt.day, calendar.monthrange(year, month)[1])
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def generate_pam_number(company_id: int, company_code: str, year: str,
                        conn=None) -> str:
    prefix    = f"PAM/{company_code}/{year}/"
    pattern   = re.compile(rf"PAM/{re.escape(company_code)}/{re.escape(year)}/(\d+)")
    owns_conn = conn is None
    if owns_conn:
        conn = get_conn()
    rows = conn.execute(
        "SELECT pam_no FROM pam_records WHERE company_id=? AND pam_no LIKE ?",
        (company_id, prefix + "%")
    ).fetchall()
    if owns_conn:
        conn.close()
    max_seq = 0
    for row in rows:
        m = pattern.match(row["pam_no"])
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq
    return f"{prefix}{max_seq + 1:03d}"


def create_pam_record(conn, company_id: int, company_code: str,
                      data: dict) -> str:
    pam_date    = data.get("pam_date") or _ts()[:10]
    year        = pam_date[:4]
    pam_no      = generate_pam_number(company_id, company_code, year, conn)
    due_date    = _add_one_month(pam_date)
    cost_center = config.COST_CENTER_MAP.get(data.get("pt", ""), "")
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, gl_account, cost_center, pt,
            requestors_name, keterangan, total_amount, due_date, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,'draft',?)""",
        (company_id, pam_no, pam_date,
         data.get("gl_account", config.PAM_DEFAULT_GL),
         cost_center, data.get("pt", ""),
         data.get("requestors_name", config.PAM_DEFAULT_REQUESTOR),
         data.get("keterangan", ""),
         float(data.get("total_amount", 0)),
         due_date, _ts())
    )
    for pid in data.get("payment_ids", []):
        conn.execute(
            "UPDATE payment_beasiswa SET pam=? WHERE id=?", (pam_no, pid)
        )
    return pam_no


def get_pam_list(company_id: int, search: str = "", bulan: str = "",
                 tahun: str = "") -> list:
    sql    = "SELECT * FROM pam_records WHERE company_id=?"
    params = [company_id]
    if search:
        q       = f"%{search}%"
        sql    += " AND (pam_no LIKE ? OR pt LIKE ? OR keterangan LIKE ?)"
        params += [q, q, q]
    if bulan:
        sql    += " AND strftime('%m', pam_date)=?"
        params += [bulan.zfill(2)]
    if tahun:
        sql    += " AND strftime('%Y', pam_date)=?"
        params += [tahun]
    sql += " ORDER BY created_at DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_coa_list() -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT gl_code, gl_name FROM coa WHERE is_active=1 ORDER BY gl_code"
    ).fetchall()]
    conn.close()
    return rows


def update_pam_gl_account(pam_id: int, gl_account: str,
                           company_id: int) -> dict:
    conn = get_conn()
    coa  = conn.execute(
        "SELECT gl_code FROM coa WHERE gl_code=? AND is_active=1", (gl_account,)
    ).fetchone()
    if not coa:
        conn.close()
        return {"ok": False, "pesan": f"GL Account '{gl_account}' tidak ditemukan di COA."}
    row = conn.execute(
        "SELECT id FROM pam_records WHERE id=? AND company_id=?",
        (pam_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "PAM record tidak ditemukan."}
    conn.execute(
        "UPDATE pam_records SET gl_account=?, updated_at=? WHERE id=? AND company_id=?",
        (gl_account, _ts(), pam_id, company_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"GL Account diubah ke {gl_account}."}


def export_memo_pdf(memo_id: int, company_id: int, company_name: str) -> bytes:
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    memo = get_memo_detail(memo_id, company_id)
    if not memo:
        raise ValueError("Memo tidak ditemukan.")

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles   = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(company_name.upper(), styles["Title"]))
    elements.append(Paragraph("PAYMENT APPROVAL MEMO", styles["Heading2"]))
    elements.append(Spacer(1, 0.3*cm))

    info = [
        ["Nomor Memo:", memo["memo_number"]],
        ["Tanggal:",    memo["tanggal"] or ""],
        ["Status:",     memo["status"].upper()],
        ["Dibuat oleh:", memo["created_by"] or ""],
    ]
    if memo.get("approved_by"):
        info.append(["Disetujui oleh:", memo["approved_by"]])
    info_tbl = Table(info, colWidths=[4*cm, 12*cm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(info_tbl)
    elements.append(Spacer(1, 0.5*cm))

    if memo.get("notes"):
        elements.append(Paragraph(f"Keterangan: {memo['notes']}", styles["Normal"]))
        elements.append(Spacer(1, 0.3*cm))

    header = [["No", "Penerima / Keterangan", "Vendor", "Rekening", "Amount (Rp)"]]
    rows   = header
    total  = 0
    for i, item in enumerate(memo["items"], 1):
        rows.append([
            i,
            item.get("description", ""),
            item.get("vendor", ""),
            item.get("bank_account", ""),
            f"{item['amount']:,.0f}",
        ])
        total += item["amount"]
    rows.append(["", "", "", "TOTAL", f"{total:,.0f}"])

    col_widths = [1*cm, 6*cm, 4*cm, 4*cm, 3*cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ALIGN",       (4,0), (4,-1), "RIGHT"),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
        ("BACKGROUND",  (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
        ("FONTNAME",    (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 1.5*cm))

    ttd = [["Dibuat oleh", "", "Disetujui oleh", "", "Diketahui oleh"],
           ["", "", "", "", ""],
           ["", "", "", "", ""],
           ["", "", "", "", ""],
           ["(________________)", "", "(________________)", "", "(_______________)"],
           ["Finance Staff", "", "Finance Manager", "", "Direktur"]]
    ttd_tbl = Table(ttd, colWidths=[3.5*cm, 0.5*cm, 3.5*cm, 0.5*cm, 3.5*cm])
    ttd_tbl.setStyle(TableStyle([
        ("FONTSIZE",  (0,0), (-1,-1), 8),
        ("ALIGN",     (0,0), (-1,-1), "CENTER"),
        ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",  (0,-1), (-1,-1), "Helvetica"),
    ]))
    elements.append(ttd_tbl)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

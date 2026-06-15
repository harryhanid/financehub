"""
One-time migration: import pam_records + pam_lines dari Excel.

Usage:
    cd C:\\Financehub\\app
    python ..\\scripts\\migrate_pam_excel.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__) + "/../app")
import config

import openpyxl
from database import get_conn, migrate_db

EXCEL_PATH = r"C:\Users\25010160\Downloads\query_1-2026-06-15_85459.xlsx"

_PILLAR_LINES_TABLE = {
    "AGRI": "agri_pam_lines",
    "APP":  "app_pam_lines",
    "LAND": "land_pam_lines",
    "SETF": "setf_pam_lines",
}

def _val(v):
    """Return None for empty/None values."""
    if v is None or v == "":
        return None
    return v


def migrate():
    # Pastikan schema sudah up-to-date
    migrate_db()

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    conn = get_conn()
    inserted = 0
    updated  = 0
    lines_created = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        # Columns A-T (index 0-19)
        (_, company_id, pam_no, pam_date, gl_account, cost_center, pt,
         requestors_name, keterangan, mata_uang, dpp, ppn, total_amount,
         due_date, status, created_at, updated_at, tanggal_bayar, source,
         pillar) = row[:20]

        # Skip rows with no pam_no
        if not pam_no:
            continue

        pillar = (pillar or "").strip().upper()
        if pillar not in _PILLAR_LINES_TABLE:
            print(f"  SKIP {pam_no}: pillar '{pillar}' tidak dikenal")
            continue

        # Columns U-AC (index 20-28)
        line_cols = row[20:29]  # U(20)..AC(28)
        (no_vendor, nama_vendor, tgl_terima_doc, tgl_proses,
         tgl_verifikasi_tax, tgl_approval_1, tgl_approval_2,
         tgl_approval_3, tgl_kirim) = line_cols

        # INSERT OR REPLACE pam_records
        existing = conn.execute(
            "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE pam_records SET
                   company_id=?, pam_date=?, gl_account=?, cost_center=?, pt=?,
                   requestors_name=?, keterangan=?, mata_uang=?, dpp=?, ppn=?,
                   total_amount=?, due_date=?, status=?, created_at=?,
                   updated_at=?, tanggal_bayar=?, source=?, pillar=?
                   WHERE pam_no=?""",
                (_val(company_id), _val(pam_date), _val(gl_account),
                 _val(cost_center), _val(pt), _val(requestors_name),
                 _val(keterangan), _val(mata_uang) or "IDR",
                 _val(dpp) or 0, _val(ppn) or 0,
                 _val(total_amount) or 0, _val(due_date),
                 _val(status) or "open", _val(created_at), _val(updated_at),
                 _val(tanggal_bayar), _val(source) or "beasiswa", pillar,
                 pam_no)
            )
            pam_id = existing["id"]
            updated += 1
        else:
            cur = conn.execute(
                """INSERT INTO pam_records
                   (company_id, pam_no, pam_date, gl_account, cost_center, pt,
                    requestors_name, keterangan, mata_uang, dpp, ppn,
                    total_amount, due_date, status, created_at, updated_at,
                    tanggal_bayar, source, pillar)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (_val(company_id), pam_no, _val(pam_date), _val(gl_account) or "70110230",
                 _val(cost_center), _val(pt), _val(requestors_name) or "Jany Turkanda",
                 _val(keterangan), _val(mata_uang) or "IDR",
                 _val(dpp) or 0, _val(ppn) or 0,
                 _val(total_amount) or 0, _val(due_date),
                 _val(status) or "open", _val(created_at), _val(updated_at),
                 _val(tanggal_bayar), _val(source) or "beasiswa", pillar)
            )
            pam_id = cur.lastrowid
            inserted += 1

        # Upsert lines row
        tbl = _PILLAR_LINES_TABLE[pillar]
        existing_line = conn.execute(
            f"SELECT id FROM {tbl} WHERE pam_id=?", (pam_id,)
        ).fetchone()

        if existing_line:
            conn.execute(
                f"""UPDATE {tbl} SET
                    no_vendor=?, nama_vendor=?, tgl_terima_doc=?, tgl_proses=?,
                    tgl_verifikasi_tax=?, tgl_approval_1=?, tgl_approval_2=?,
                    tgl_approval_3=?, tgl_kirim=?
                    WHERE pam_id=?""",
                (_val(no_vendor), _val(nama_vendor), _val(tgl_terima_doc),
                 _val(tgl_proses), _val(tgl_verifikasi_tax), _val(tgl_approval_1),
                 _val(tgl_approval_2), _val(tgl_approval_3), _val(tgl_kirim),
                 pam_id)
            )
        else:
            conn.execute(
                f"""INSERT INTO {tbl}
                    (pam_id, no_vendor, nama_vendor, tgl_terima_doc, tgl_proses,
                     tgl_verifikasi_tax, tgl_approval_1, tgl_approval_2,
                     tgl_approval_3, tgl_kirim)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (pam_id, _val(no_vendor), _val(nama_vendor), _val(tgl_terima_doc),
                 _val(tgl_proses), _val(tgl_verifikasi_tax), _val(tgl_approval_1),
                 _val(tgl_approval_2), _val(tgl_approval_3), _val(tgl_kirim))
            )
            lines_created += 1

    conn.commit()
    conn.close()
    print(f"Migration selesai:")
    print(f"  pam_records inserted: {inserted}")
    print(f"  pam_records updated:  {updated}")
    print(f"  pam_lines created:    {lines_created}")


if __name__ == "__main__":
    migrate()

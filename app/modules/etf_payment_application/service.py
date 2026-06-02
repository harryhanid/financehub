# modules/etf_payment_application/service.py
from datetime import datetime
from database import get_conn


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def _latest_ipk(siswa_row: dict) -> float:
    """Return IPK sem terakhir yang tidak nol dari data siswa."""
    for i in range(10, 0, -1):
        val = siswa_row.get(f"ipk_sem{i}") or 0
        if val:
            return float(val)
    return 0.0


def get_siswa_autocomplete(company_id: int, q: str) -> list:
    """Return list siswa untuk autocomplete input (nama + id)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, code, nama, jenjang, angkatan, program, fakultas,
                  universitas, status,
                  ipk_sem1, ipk_sem2, ipk_sem3, ipk_sem4, ipk_sem5,
                  ipk_sem6, ipk_sem7, ipk_sem8, ipk_sem9, ipk_sem10
           FROM siswa
           WHERE company_id=? AND (nama LIKE ? OR code LIKE ?)
           ORDER BY nama LIMIT 20""",
        (company_id, f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["ipk_terakhir"] = _latest_ipk(d)
        result.append(d)
    return result


def _gen_pa_number(company_id: int, conn) -> str:
    year = datetime.now().strftime("%Y")
    count = conn.execute(
        "SELECT COUNT(*) FROM etf_pa WHERE company_id=?", (company_id,)
    ).fetchone()[0]
    return f"PA/ETF/{count + 1:03d}/{year}"


def _gen_nomor_pam(company_id: int, conn) -> str:
    now = datetime.now()
    mm   = now.strftime("%m")
    yyyy = now.strftime("%Y")
    count = conn.execute(
        """SELECT COUNT(*) FROM etf_pa
           WHERE company_id=? AND nomor_pam IS NOT NULL
           AND strftime('%Y-%m', created_at)=?""",
        (company_id, f"{yyyy}-{mm}")
    ).fetchone()[0]
    return f"{count + 1:03d}-ETF-{mm}-{yyyy}"


def get_pa_list(company_id: int) -> list:
    """Return satu row per PA header, dengan aggregate count siswa dan total bayar."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.*,
                  COUNT(l.id)          AS jml_siswa,
                  COALESCE(SUM(l.jumlah_pembayaran), 0) AS total_bayar
           FROM etf_pa p
           LEFT JOIN etf_pa_lines l ON l.pa_id = p.id
           WHERE p.company_id=?
           GROUP BY p.id
           ORDER BY p.created_at DESC""",
        (company_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pa_flat(company_id: int) -> list:
    """Return flat rows: satu baris per line, header fields diulang per baris."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT
                  s.code             AS student_code,
                  p.id               AS pa_id,
                  s.nama,
                  s.status           AS status_pb,
                  s.universitas      AS instansi_pendidikan,
                  s.angkatan         AS angkatan_etf,
                  s.angkatan_kuliah,
                  s.jenjang          AS jenjang_pendidikan,
                  s.program          AS program_beasiswa,
                  s.fakultas,
                  s.prodi            AS program_studi,
                  p.tgl_payment_application,
                  p.tgl_surat_pengajuan,
                  l.jenis_pembayaran,
                  l.semester,
                  l.tahun_ajaran,
                  l.ipk_sem_sebelumnya,
                  l.jumlah_pembayaran,
                  p.doc_received_by_educ,
                  p.received_pa_from_educ,
                  p.checked_by_fincon,
                  p.approved_by_htj_1,
                  p.send_pa_back_to_educ,
                  p.pa_received_by_po_fin,
                  p.approval_by_htj_2,
                  p.nomor_pam,
                  p.tanggal_bayar,
                  p.keterangan,
                  p.status,
                  p.pa_number,
                  l.id               AS line_id
           FROM etf_pa p
           JOIN etf_pa_lines l ON l.pa_id = p.id
           JOIN siswa s ON s.id = l.student_id
           WHERE p.company_id=?
           ORDER BY p.created_at DESC, l.id ASC""",
        (company_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pa_header(pa_id: int, company_id: int) -> dict | None:
    """Return single PA header record for edit modal."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM etf_pa WHERE id=? AND company_id=?", (pa_id, company_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_pa_lines(pa_id: int, company_id: int) -> list:
    """Return semua lines untuk satu PA, dengan data siswa di-JOIN."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.*,
                  s.nama, s.code AS siswa_code, s.status AS status_pb,
                  s.universitas AS instansi_pendidikan,
                  s.angkatan AS angkatan_etf,
                  s.jenjang AS jenjang_pendidikan,
                  s.program AS program_beasiswa,
                  s.fakultas
           FROM etf_pa_lines l
           JOIN siswa s ON s.id = l.student_id
           JOIN etf_pa p ON p.id = l.pa_id
           WHERE l.pa_id=? AND p.company_id=?
           ORDER BY l.id""",
        (pa_id, company_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_pa(company_id: int, header: dict, lines: list) -> dict:
    """
    header keys: tgl_payment_application, tgl_surat_pengajuan, keterangan
    lines items: {student_id, jenis_pembayaran, semester, tahun_ajaran,
                  ipk_sem_sebelumnya, jumlah_pembayaran}
    """
    if not lines:
        return {"ok": False, "pesan": "Minimal 1 siswa harus diisi."}

    conn = get_conn()
    # validate all student_id belong to company
    for line in lines:
        sid = line.get("student_id")
        row = conn.execute(
            "SELECT id FROM siswa WHERE id=? AND company_id=?", (sid, company_id)
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "pesan": f"Siswa ID {sid} tidak ditemukan."}

    pa_number = _gen_pa_number(company_id, conn)
    ts = _ts()
    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, tgl_surat_pengajuan,
            keterangan, status, created_at)
           VALUES (?,?,?,?,?,'draft',?)""",
        (company_id, pa_number,
         header.get("tgl_payment_application", ""),
         header.get("tgl_surat_pengajuan", ""),
         header.get("keterangan", ""),
         ts)
    )
    pa_id = cur.lastrowid

    for line in lines:
        conn.execute(
            """INSERT INTO etf_pa_lines
               (pa_id, student_id, jenis_pembayaran, semester,
                tahun_ajaran, ipk_sem_sebelumnya, jumlah_pembayaran)
               VALUES (?,?,?,?,?,?,?)""",
            (pa_id,
             line.get("student_id"),
             line.get("jenis_pembayaran", ""),
             line.get("semester", ""),
             line.get("tahun_ajaran", ""),
             line.get("ipk_sem_sebelumnya") or 0,
             line.get("jumlah_pembayaran") or 0)
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pa_id": pa_id, "pa_number": pa_number,
            "pesan": f"Payment Application {pa_number} berhasil dibuat."}


def update_pa(pa_id: int, company_id: int, data: dict) -> dict:
    """
    Update SLA dates, keterangan, tanggal_bayar, nomor_pam, status.
    Jika status → on_process dan nomor_pam belum ada, auto-generate.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id, status, nomor_pam FROM etf_pa WHERE id=? AND company_id=?",
        (pa_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "PA tidak ditemukan."}

    new_status  = data.get("status", row["status"])
    nomor_pam   = data.get("nomor_pam") or row["nomor_pam"]

    # auto-generate PAM number when transitioning to on_process
    if new_status == "on_process" and not nomor_pam:
        nomor_pam = _gen_nomor_pam(company_id, conn)

    conn.execute(
        """UPDATE etf_pa SET
            tgl_payment_application = ?,
            tgl_surat_pengajuan     = ?,
            doc_received_by_educ    = ?,
            received_pa_from_educ   = ?,
            checked_by_fincon       = ?,
            approved_by_htj_1       = ?,
            send_pa_back_to_educ    = ?,
            pa_received_by_po_fin   = ?,
            approval_by_htj_2       = ?,
            nomor_pam               = ?,
            tanggal_bayar           = ?,
            keterangan              = ?,
            status                  = ?,
            updated_at              = ?
           WHERE id=? AND company_id=?""",
        (data.get("tgl_payment_application", ""),
         data.get("tgl_surat_pengajuan", ""),
         data.get("doc_received_by_educ", ""),
         data.get("received_pa_from_educ", ""),
         data.get("checked_by_fincon", ""),
         data.get("approved_by_htj_1", ""),
         data.get("send_pa_back_to_educ", ""),
         data.get("pa_received_by_po_fin", ""),
         data.get("approval_by_htj_2", ""),
         nomor_pam,
         data.get("tanggal_bayar", ""),
         data.get("keterangan", ""),
         new_status,
         _ts(), pa_id, company_id)
    )
    conn.commit()
    conn.close()

    msg = "PA berhasil diupdate."
    if new_status == "on_process" and nomor_pam and not row["nomor_pam"]:
        msg = f"PA pindah ke On Process. Nomor PAM: {nomor_pam}"
    return {"ok": True, "pesan": msg, "nomor_pam": nomor_pam}

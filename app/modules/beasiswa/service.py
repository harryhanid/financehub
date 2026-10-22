import uuid
# modules/beasiswa/service.py
from datetime import datetime
from database import get_conn
import config
from fhdb.errors import OperationalError
from modules.payment_memo.service import pam_record_insert_stmt


def _ts():
    return datetime.now().isoformat(timespec="seconds")


_CAT2_MEDICAL = {"Rawat Jalan", "Rawat Inap"}

# pillar -> (pa_lines table, pa header table), scoped to exactly the 3 pillars this
# module's PA-status cascade has always covered (APP/LAND cascade support was never
# added for SETF/ENERGY here — preserved as-is, not expanded by this fix). `id` is a
# per-table AUTOINCREMENT primary key, so the same numeric id can exist in more than
# one of these tables — always resolve via the row's own `pillar`, never by trying
# each table in turn and taking the first/any match.
_PILLAR_PA_TBL = {
    "AGRI": ("etf_pa_lines", "etf_pa"),
    "APP":  ("app_pa_lines", "app_pa"),
    "LAND": ("sml_pa_lines", "sml_pa"),
}


def get_vendors(search: str = "") -> list:
    conn = get_conn()
    if search:
        rows = conn.execute(
            "SELECT name, pillar, cost_center FROM vendors WHERE name ILIKE ? ORDER BY name",
            (f"%{search}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT name, pillar, cost_center FROM vendors ORDER BY name"
        ).fetchall()
    conn.close()
    return [{"name": r["name"], "pillar": r["pillar"], "cost_center": r["cost_center"] or ""} for r in rows]


def generate_kode_siswa(jenjang: str, angkatan: int, company_id: int) -> str:
    kode_j = config.KODE_JENJANG.get(jenjang.strip(), "0")
    tahun2 = str(angkatan)[-2:]
    prefix = kode_j + tahun2

    conn  = get_conn()
    rows  = conn.execute(
        # LIKE (case-sensitive) disengaja: prefix hanya angka (kode jenjang + 2 digit tahun).
        "SELECT code FROM siswa WHERE company_id=? AND code LIKE ?",
        (company_id, prefix + "%")
    ).fetchall()
    conn.close()

    max_urut = 0
    for row in rows:
        kode = str(row["code"])
        if len(kode) >= 7:
            try:
                urut = int(kode[3:7])
                if urut > max_urut:
                    max_urut = urut
            except ValueError:
                pass

    return prefix + str(max_urut + 1).zfill(4)


def get_distinct_angkatan(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT angkatan FROM siswa WHERE company_id=? AND angkatan IS NOT NULL ORDER BY angkatan DESC", (company_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]

def get_distinct_universitas(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT universitas FROM siswa WHERE company_id=? AND universitas != '' ORDER BY universitas",
        (company_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_siswa_list(company_id: int, search: str = "", status: str = "", program: str = "") -> list:
    sql    = "SELECT * FROM siswa WHERE company_id=?"
    params = [company_id]
    if search:
        sql    += " AND (nama ILIKE ? OR code ILIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if status:
        sql    += " AND status=?"
        params += [status]
    if program:
        sql    += " AND program=?"
        params += [program]
    sql += " ORDER BY created_at DESC NULLS LAST"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_siswa_detail(company_id: int, code: str) -> dict | None:
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM siswa WHERE company_id=? AND code=?", (company_id, code)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_siswa(company_id: int, data: dict) -> dict:
    code = (data.get("code") or "").strip()
    nama = (data.get("nama") or "").strip()
    if not code or not nama:
        return {"ok": False, "pesan": "Code dan nama wajib diisi."}

    conn     = get_conn()
    existing = conn.execute(
        "SELECT id FROM siswa WHERE company_id=? AND code=?", (company_id, code)
    ).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "pesan": f"Code '{code}' sudah ada di database."}

    ipk_sem = [float(data.get(f"ipk_sem{i}", 0) or 0) for i in range(1, 11)]
    ipk_pen = [float(data.get(f"ipk_pen{i}", 0) or 0) for i in range(1, 4)]

    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program, group_setf, fakultas, universitas,
            bank, norek, namarek, referensi, tanggal_lahir,
            ipk_sem1,ipk_sem2,ipk_sem3,ipk_sem4,ipk_sem5,
            ipk_sem6,ipk_sem7,ipk_sem8,ipk_sem9,ipk_sem10,
            ipk_pen1,ipk_pen2,ipk_pen3,
            status, catatan, catatan_budget, catatan_payment, prodi, angkatan_kuliah, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, code, nama,
         data.get("jenjang", ""), data.get("angkatan") or None,
         data.get("program", ""), data.get("group_setf", ""), data.get("fakultas", ""), data.get("universitas", ""),
         data.get("bank", ""), data.get("norek", ""), data.get("namarek", ""),
         data.get("referensi", ""), data.get("tanggal_lahir", ""),
         *ipk_sem, *ipk_pen,
         data.get("status", "Aktif"), data.get("catatan", ""),
         data.get("catatan_budget", ""), data.get("catatan_payment", ""),
         data.get("prodi", ""), data.get("angkatan_kuliah", ""), _ts())
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Siswa '{nama}' berhasil ditambahkan."}


def update_siswa(company_id: int, code: str, data: dict) -> dict:
    conn     = get_conn()
    existing = conn.execute(
        "SELECT id FROM siswa WHERE company_id=? AND code=?", (company_id, code)
    ).fetchone()
    if not existing:
        conn.close()
        return {"ok": False, "pesan": f"Siswa '{code}' tidak ditemukan."}

    ipk_sem = [float(data.get(f"ipk_sem{i}", 0) or 0) for i in range(1, 11)]
    ipk_pen = [float(data.get(f"ipk_pen{i}", 0) or 0) for i in range(1, 4)]

    conn.execute(
        """UPDATE siswa SET
           nama=?,jenjang=?,angkatan=?,program=?,group_setf=?,fakultas=?,universitas=?,
           bank=?,norek=?,namarek=?,referensi=?,tanggal_lahir=?,
           ipk_sem1=?,ipk_sem2=?,ipk_sem3=?,ipk_sem4=?,ipk_sem5=?,
           ipk_sem6=?,ipk_sem7=?,ipk_sem8=?,ipk_sem9=?,ipk_sem10=?,
           ipk_pen1=?,ipk_pen2=?,ipk_pen3=?,
           status=?,catatan=?,catatan_budget=?,catatan_payment=?,prodi=?,angkatan_kuliah=?,updated_at=?
           WHERE company_id=? AND code=?""",
        (data.get("nama",""), data.get("jenjang",""), data.get("angkatan") or None,
         data.get("program",""), data.get("group_setf",""), data.get("fakultas",""), data.get("universitas",""),
         data.get("bank",""), data.get("norek",""), data.get("namarek",""),
         data.get("referensi",""), data.get("tanggal_lahir",""),
         *ipk_sem, *ipk_pen,
         data.get("status","Aktif"), data.get("catatan",""),
         data.get("catatan_budget",""), data.get("catatan_payment",""),
         data.get("prodi",""), data.get("angkatan_kuliah",""), _ts(),
         company_id, code)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Data siswa '{code}' berhasil diupdate."}


def update_siswa_catatan(company_id: int, code: str, catatan: str) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM siswa WHERE company_id=? AND code=?", (company_id, code)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Siswa tidak ditemukan."}
    conn.execute(
        "UPDATE siswa SET catatan_budget=?,updated_at=? WHERE company_id=? AND code=?",
        (catatan, _ts(), company_id, code)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Catatan budget diupdate."}


def update_siswa_catatan_payment(company_id: int, code: str, catatan_payment: str) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM siswa WHERE company_id=? AND code=?", (company_id, code)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Siswa tidak ditemukan."}
    conn.execute(
        "UPDATE siswa SET catatan_payment=?,updated_at=? WHERE company_id=? AND code=?",
        (catatan_payment, _ts(), company_id, code)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Catatan payment diupdate."}


def delete_siswa(company_id: int, code: str) -> dict:
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM siswa WHERE company_id=? AND code=?", (company_id, code)
    ).fetchone()
    if not existing:
        conn.close()
        return {"ok": False, "pesan": f"Siswa '{code}' tidak ditemukan."}
    bgt = conn.execute(
        "SELECT COUNT(*) FROM budget_beasiswa WHERE company_id=? AND siswa_code=?", (company_id, code)
    ).fetchone()[0]
    pay = conn.execute(
        "SELECT COUNT(*) FROM payment_beasiswa WHERE company_id=? AND siswa_code=?", (company_id, code)
    ).fetchone()[0]
    # Atomik (atomic-flows.md Task 15): tiga DELETE dalam satu batch (satu transaksi).
    conn.batch([
        ("DELETE FROM budget_beasiswa WHERE company_id=? AND siswa_code=?", (company_id, code)),
        ("DELETE FROM payment_beasiswa WHERE company_id=? AND siswa_code=?", (company_id, code)),
        ("DELETE FROM siswa WHERE company_id=? AND code=?", (company_id, code)),
    ])
    conn.commit()
    conn.close()
    detail = f" (termasuk {bgt} budget, {pay} payment)" if bgt or pay else ""
    return {"ok": True, "pesan": f"Siswa '{code}' berhasil dihapus{detail}."}





def update_budget_row(company_id: int, row_id: int, data: dict) -> dict:
    conn = get_conn()
    row  = conn.execute("SELECT id FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris budget tidak ditemukan."}
    try:
        amount = float(str(data.get("amount", 0)).replace(",", ""))
    except (ValueError, TypeError):
        amount = 0
    if amount <= 0:
        conn.close()
        return {"ok": False, "pesan": "Amount harus lebih dari 0."}
    conn.execute(
        "UPDATE budget_beasiswa SET cat1=?,cat2=?,tanggal=?,pillar=?,amount=?,tgl_expired=? WHERE id=? AND company_id=?",
        (data.get("cat1",""), data.get("cat2",""), data.get("tanggal",""),
         data.get("pillar",""), amount, data.get("tgl_expired") or None, row_id, company_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Baris budget diupdate."}





def get_budget(company_id: int, siswa_code: str) -> dict:
    conn  = get_conn()
    rows  = [dict(r) for r in conn.execute(
        "SELECT * FROM budget_beasiswa WHERE company_id=? AND siswa_code=? ORDER BY tanggal NULLS FIRST",
        (company_id, siswa_code)
    ).fetchall()]
    conn.close()
    totals = {}
    grand  = 0.0
    for r in rows:
        totals[r["cat1"]] = totals.get(r["cat1"], 0) + r["amount"]
        grand += r["amount"]
    return {"rows": rows, "totals": totals, "grand": grand}


def add_payment_batch(company_id: int, siswa_code: str, tanggal: str,
                      pillar: str, perusahaan: str, items: list) -> dict:
    conn  = get_conn()
    saved = 0
    # Atomik (atomic-flows.md Task 15): semua INSERT dikumpulkan lalu dikirim dalam satu batch.
    stmts = []
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        stmts.append((
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,cat3,cat4,status,klasifikasi_pa)
               VALUES (?,?,?,?,?,?,?,?,?,?,'open',?)""",
            (company_id, siswa_code,
             item.get("cat1",""), item.get("cat2",""),
             tanggal, amount, pillar, perusahaan,
             item.get("cat3",""), item.get("cat4",""), item.get("klasifikasi_pa","Normal"))
        ))
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0.", "saved": 0}

    conn.batch(stmts)
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} payment berhasil disimpan (status: open).", "saved": saved}


def _row_amount(row) -> float:
    try:
        return float(str(row.get("amount", 0)).replace(",", ""))
    except (ValueError, TypeError):
        return 0


def _medical_rows_invalid(rows: list) -> bool:
    """Pre-flight: True kalau ada baris medis (amount > 0) yang rekam medisnya belum lengkap."""
    for row in rows:
        if _row_amount(row) <= 0:
            continue
        if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
            rm = row.get("rekam_medis") or {}
            if not rm.get("kelas") or not rm.get("rumah_sakit") or \
               not rm.get("diagnosa") or not rm.get("spesialisasi"):
                return True
    return False


_MEDICAL_INVALID = {"ok": False,
                    "pesan": "Data rekam medis wajib diisi (kelas, rumah sakit, diagnosa, spesialisasi).",
                    "payment_ids": [], "total": 0.0, "pa_line_ids": []}
_NO_ITEMS = {"ok": False, "pesan": "Tidak ada item dengan amount > 0.",
             "payment_ids": [], "total": 0.0, "pa_line_ids": []}

# id payment_beasiswa / pam_records yang baru di-INSERT lebih dulu di batch yang sama.
_PB_CURRVAL = ("currval(pg_get_serial_sequence("
               "quote_ident(current_schema()) || '.\"payment_beasiswa\"', 'id'))")
_PAM_CURRVAL = ("currval(pg_get_serial_sequence("
                "quote_ident(current_schema()) || '.\"pam_records\"', 'id'))")


def _payment_insert_stmt(company_id, row, amount, tanggal, pillar, perusahaan, route,
                         pam_sql=None):
    """(sql, params) INSERT payment_beasiswa untuk satu baris. pam_sql: ekspresi SQL untuk kolom
    pam (mis. pam_no dari pam_records yang di-INSERT sebelumnya di batch yang sama)."""
    siswa_code     = (row.get("siswa_code") or "").strip()
    etf_pa_line_id = row.get("etf_pa_line_id") or None
    pam_col = ",pam" if pam_sql else ""
    pam_val = f",{pam_sql}" if pam_sql else ""
    return (
        f"""INSERT INTO payment_beasiswa
           (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
            tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,etf_pa_line_id,
            advance_amount,status,klasifikasi_pa{pam_col})
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open',?{pam_val})""",
        (company_id, siswa_code,
         row.get("cat1", ""), row.get("cat2", ""),
         tanggal, amount, pillar, perusahaan,
         row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
         row.get("tgl_pa", ""),        row.get("tgl_final", ""),
         row.get("cat3", ""),          row.get("cat4", ""),
         etf_pa_line_id,
         amount if route == "advance" else None, row.get("klasifikasi_pa") or "Normal")
    )


def _rekam_medis_stmt(company_id, row, payment_id_sql="?", payment_id=None):
    """(sql, params) INSERT rekam_medis. payment_id_sql '?' memakai payment_id; selain itu ekspresi
    SQL (mis. currval payment_beasiswa di batch yang sama)."""
    siswa_code = (row.get("siswa_code") or "").strip()
    rm = row.get("rekam_medis", {})
    params = (company_id,) + ((payment_id,) if payment_id_sql == "?" else ()) + (
        siswa_code,
        rm.get("kelas", ""),    rm.get("rumah_sakit", ""),
        rm.get("diagnosa", ""), rm.get("spesialisasi", ""),
        rm.get("catatan", "") or None)
    return (
        f"""INSERT INTO rekam_medis
           (company_id, payment_id, siswa_code, kelas, rumah_sakit,
            diagnosa, spesialisasi, catatan)
           VALUES (?,{payment_id_sql},?,?,?,?,?,?)""",
        params
    )


def _is_medical(row) -> bool:
    return row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL


def _pa_line_ids(rows: list) -> list:
    return [
        row.get("etf_pa_line_id")
        for row in rows
        if row.get("etf_pa_line_id") and
           float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
    ]


def _pa_on_process_stmt(company_id, pillar, pa_line_ids):
    pair = _PILLAR_PA_TBL.get((pillar or "").upper())
    if not pa_line_ids or not pair:
        return None
    lines_tbl, pa_tbl = pair
    ph = ",".join("?" * len(pa_line_ids))
    return (
        f"""UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?
            WHERE id IN (
                SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
            ) AND company_id = ? AND status = 'open'""",
        [_ts()] + pa_line_ids + [company_id]
    )


def insert_payment_rows(conn, company_id: int, company_code: str,
                        tanggal: str, pillar: str, perusahaan: str,
                        rows: list, route: str = "gl") -> dict:
    """Insert payment_beasiswa rows and update linked PA status → on_process.

    Caller owns conn (no commit, no close here). Does NOT create pam_record.
    Returns {"ok": bool, "payment_ids": list, "total": float, "pa_line_ids": list}.

    Catatan Postgres: dipakai payment_memo.save_pa_payment (Task 16 menjadikannya atomik); tiap
    statement di sini masih satu panggilan. add_payment_multi tidak memakai fungsi ini lagi, tetapi
    membangun statement yang sama ke dalam satu batch.
    """
    # Pre-flight: validate all medical rows before any INSERT
    if _medical_rows_invalid(rows):
        return dict(_MEDICAL_INVALID)

    saved = 0
    payment_ids: list = []
    total = 0.0

    for row in rows:
        amount = _row_amount(row)
        if amount <= 0:
            continue
        cur = conn.execute(*_payment_insert_stmt(company_id, row, amount, tanggal, pillar,
                                                 perusahaan, route))
        payment_ids.append(cur.lastrowid)
        total += amount
        saved += 1

        if _is_medical(row):
            conn.execute(*_rekam_medis_stmt(company_id, row, payment_id=cur.lastrowid))

    if saved == 0:
        return dict(_NO_ITEMS)

    pa_line_ids = _pa_line_ids(rows)
    stmt = _pa_on_process_stmt(company_id, pillar, pa_line_ids)
    if stmt:
        conn.execute(*stmt)

    return {
        "ok":         True,
        "pesan":      f"{saved} payment berhasil disimpan.",
        "payment_ids": payment_ids,
        "total":       total,
        "pa_line_ids": pa_line_ids,
    }


def add_payment_multi(company_id: int, company_code: str, tanggal: str,
                      pillar: str, perusahaan: str, rows: list) -> dict:
    conn = get_conn()
    try:
        if _medical_rows_invalid(rows):
            return dict(_MEDICAL_INVALID)
        valid = [(row, _row_amount(row)) for row in rows]
        valid = [(row, amt) for row, amt in valid if amt > 0]
        if not valid:
            return dict(_NO_ITEMS)
        total       = 0.0
        for _, amt in valid:
            total += amt
        saved       = len(valid)
        pa_line_ids = _pa_line_ids(rows)

        # Collect student names for auto keterangan
        unique_codes = list({
            (row.get("siswa_code") or "").strip()
            for row in rows
            if float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
        })
        name_rows = []
        if unique_codes:
            ph = ",".join("?" * len(unique_codes))
            name_rows = conn.execute(
                f"SELECT nama FROM siswa WHERE company_id=? AND code IN ({ph})",
                [company_id] + unique_codes,
            ).fetchall()
        keterangan = ", ".join(r["nama"] for r in name_rows) if name_rows else ""

        # Atomik (atomic-flows.md Task 15, R24): semua tulisan dalam SATU batch. Urutan diubah:
        # pam_records di-INSERT lebih dulu dengan pam_no dari fn_next_pam_no (advisory lock
        # 'pam_no:<code>:<year>' sampai commit), lalu payment_beasiswa langsung diisi pam = pam_no
        # itu (dulu: INSERT pb lalu UPDATE pb.pam per id; hasil akhir sama, tidak ada FK pada pb.pam),
        # rekam_medis memakai currval payment_beasiswa, lalu UPDATE PA on_process + nomor_pam.
        pam_sql, pam_params = pam_record_insert_stmt(company_id, company_code, {
            "pam_date":     tanggal,
            "pt":           perusahaan,
            "pillar":       pillar,
            "keterangan":   keterangan,
            "total_amount": total,
            "dpp":          total,
            "source":       "beasiswa",
        })
        pam_no_sql = f"(SELECT pam_no FROM pam_records WHERE id = {_PAM_CURRVAL})"
        stmts = [(pam_sql, pam_params)]
        for row, amount in valid:
            stmts.append(_payment_insert_stmt(company_id, row, amount, tanggal, pillar,
                                              perusahaan, "gl", pam_sql=pam_no_sql))
            if _is_medical(row):
                stmts.append(_rekam_medis_stmt(company_id, row, payment_id_sql=_PB_CURRVAL))
        on_process = _pa_on_process_stmt(company_id, pillar, pa_line_ids)
        if on_process:
            stmts.append(on_process)
        if pa_line_ids:
            ph = ",".join("?" * len(pa_line_ids))
            ts_pam = _ts()
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines", "etf_pa"),
                ("app_pa_lines", "app_pa"),
                ("sml_pa_lines", "sml_pa"),
            ]:
                stmts.append((
                    f"""UPDATE {pa_tbl} SET nomor_pam = {pam_no_sql}, updated_at = ?
                        WHERE id IN (
                            SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                        ) AND company_id = ?""",
                    [ts_pam] + pa_line_ids + [company_id]
                ))

        pam_no = conn.batch(stmts)[0].fetchone()["pam_no"]
        return {
            "ok":    True,
            "pesan": f"{saved} payment berhasil disimpan (status: open).",
            "saved": saved,
            "pam_no": pam_no,
        }

    except OperationalError:
        # R25: outage DB harus sampai ke handler 503, bukan jadi {"ok": False} (200).
        raise
    except Exception as exc:
        return {"ok": False, "pesan": f"Gagal menyimpan payment: {exc}", "saved": 0}
    finally:
        conn.close()


def get_budget_list(company_id: int, search: str = "", cat1: str = "",
                    pillar: str = "", bulan: str = "", tahun: str = "",
                    program: str = "", limit: int = 500) -> dict:
    sql = (
        "SELECT bb.*, s.nama, s.program FROM budget_beasiswa bb "
        "LEFT JOIN siswa s ON s.company_id=bb.company_id AND s.code=bb.siswa_code "
        "WHERE bb.company_id=?"
    )
    params = [company_id]
    if search:
        q = f"%{search}%"
        sql += (" AND (bb.siswa_code ILIKE ? OR s.nama ILIKE ? OR bb.cat1 ILIKE ?"
                " OR bb.cat2 ILIKE ? OR bb.pillar ILIKE ? OR s.program ILIKE ?)")
        params += [q, q, q, q, q, q]
    if cat1:
        sql += " AND bb.cat1=?"
        params += [cat1]
    if pillar:
        sql += " AND bb.pillar=?"
        params += [pillar]
    if program:
        sql += " AND s.program=?"
        params += [program]
    if bulan:
        sql += " AND fh_strftime('%m', bb.tanggal) = ?"
        params += [bulan.zfill(2)]
    if tahun:
        sql += " AND fh_strftime('%Y', bb.tanggal) = ?"
        params += [tahun]
    conn  = get_conn()
    agg_sql = sql.replace(
        "SELECT bb.*, s.nama, s.program FROM",
        "SELECT bb.cat1, SUM(bb.amount) AS total FROM"
    ) + " GROUP BY bb.cat1"
    totals = {r[0]: r[1] for r in conn.execute(agg_sql, params).fetchall()}
    grand  = sum(totals.values())
    # Cross-tab: payment totals for same filter scope
    pay_sql = (
        "SELECT pb.cat1, SUM(pb.amount) AS total FROM payment_beasiswa pb "
        "LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code "
        "WHERE pb.company_id=?"
    )
    pay_params = [company_id]
    if search:
        pay_sql += (" AND (pb.siswa_code ILIKE ? OR s.nama ILIKE ? OR pb.cat1 ILIKE ?"
                    " OR pb.cat2 ILIKE ? OR pb.pam ILIKE ? OR pb.pillar ILIKE ?"
                    " OR pb.perusahaan ILIKE ? OR s.program ILIKE ?)")
        pay_params += [q, q, q, q, q, q, q, q]
    if cat1:
        pay_sql += " AND pb.cat1=?"
        pay_params += [cat1]
    if pillar:
        pay_sql += " AND pb.pillar=?"
        pay_params += [pillar]
    if program:
        pay_sql += " AND s.program=?"
        pay_params += [program]
    if bulan:
        pay_sql += " AND fh_strftime('%m', pb.tanggal) = ?"
        pay_params += [bulan.zfill(2)]
    if tahun:
        pay_sql += " AND fh_strftime('%Y', pb.tanggal) = ?"
        pay_params += [tahun]
    pay_sql += " GROUP BY pb.cat1"
    payment_totals = {r[0]: r[1] for r in conn.execute(pay_sql, pay_params).fetchall()}
    payment_grand  = sum(payment_totals.values())
    sql   += " ORDER BY bb.tanggal DESC NULLS LAST"
    total  = conn.execute(f"SELECT COUNT(*) FROM ({sql}) AS _q", params).fetchone()[0]
    rows   = [dict(r) for r in conn.execute(sql + " LIMIT ?", params + [limit]).fetchall()]
    conn.close()
    return {
        "rows": rows, "total": total,
        "totals": totals, "grand": grand,
        "payment_totals": payment_totals, "payment_grand": payment_grand,
    }


def get_payment_list(company_id: int, search: str = "", bulan: str = "",
                     tahun: str = "", status: str = "", cat1: str = "",
                     pillar: str = "", program: str = "", limit: int = 500) -> dict:
    sql    = (
        "SELECT pb.*, s.nama, s.program, pr.tanggal_bayar AS tgl_bayar_pam "
        "FROM payment_beasiswa pb "
        "LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code "
        "LEFT JOIN pam_records pr ON pr.pam_no=pb.pam AND pr.company_id=pb.company_id "
        "WHERE pb.company_id=?"
    )
    params = [company_id]
    if search:
        q       = f"%{search}%"
        sql    += (" AND (pb.siswa_code ILIKE ? OR s.nama ILIKE ? OR pb.cat1 ILIKE ?"
                   " OR pb.cat2 ILIKE ? OR pb.pam ILIKE ? OR pb.pillar ILIKE ?"
                   " OR pb.perusahaan ILIKE ? OR s.program ILIKE ?)")
        params += [q, q, q, q, q, q, q, q]
    if cat1:
        sql    += " AND pb.cat1=?"
        params += [cat1]
    if pillar:
        sql    += " AND pb.pillar=?"
        params += [pillar]
    if program:
        sql    += " AND s.program=?"
        params += [program]
    if bulan:
        sql    += " AND fh_strftime('%m', pb.tanggal) = ?"
        params += [bulan.zfill(2)]
    if tahun:
        sql    += " AND fh_strftime('%Y', pb.tanggal) = ?"
        params += [tahun]
    if status:
        sql    += " AND pb.status=?"
        params += [status]
    conn  = get_conn()
    agg_sql = sql.replace(
        "SELECT pb.*, s.nama, s.program, pr.tanggal_bayar AS tgl_bayar_pam FROM",
        "SELECT pb.cat1, SUM(pb.amount) AS total FROM"
    ) + " GROUP BY pb.cat1"
    totals = {r[0]: r[1] for r in conn.execute(agg_sql, params).fetchall()}
    grand  = sum(totals.values())
    # Cross-tab: budget totals for same filter scope
    bgt_sql = (
        "SELECT bb.cat1, SUM(bb.amount) AS total FROM budget_beasiswa bb "
        "LEFT JOIN siswa s ON s.company_id=bb.company_id AND s.code=bb.siswa_code "
        "WHERE bb.company_id=?"
    )
    bgt_params = [company_id]
    if search:
        q2 = f"%{search}%"
        bgt_sql += (" AND (bb.siswa_code ILIKE ? OR s.nama ILIKE ? OR bb.cat1 ILIKE ?"
                    " OR bb.cat2 ILIKE ? OR bb.pillar ILIKE ? OR s.program ILIKE ?)")
        bgt_params += [q2, q2, q2, q2, q2, q2]
    if cat1:
        bgt_sql += " AND bb.cat1=?"
        bgt_params += [cat1]
    if pillar:
        bgt_sql += " AND bb.pillar=?"
        bgt_params += [pillar]
    if program:
        bgt_sql += " AND s.program=?"
        bgt_params += [program]
    if bulan:
        bgt_sql += " AND fh_strftime('%m', bb.tanggal) = ?"
        bgt_params += [bulan.zfill(2)]
    if tahun:
        bgt_sql += " AND fh_strftime('%Y', bb.tanggal) = ?"
        bgt_params += [tahun]
    bgt_sql += " GROUP BY bb.cat1"
    budget_totals = {r[0]: r[1] for r in conn.execute(bgt_sql, bgt_params).fetchall()}
    budget_grand  = sum(budget_totals.values())
    sql   += " ORDER BY pb.tanggal DESC NULLS LAST"
    total  = conn.execute(f"SELECT COUNT(*) FROM ({sql}) AS _q", params).fetchone()[0]
    rows   = [dict(r) for r in conn.execute(sql + " LIMIT ?", params + [limit]).fetchall()]
    conn.close()
    return {
        "rows": rows, "total": total,
        "totals": totals, "grand": grand,
        "budget_totals": budget_totals, "budget_grand": budget_grand,
    }


def get_financial_summary(company_id: int) -> dict:
    conn = get_conn()
    bgt = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) AS t FROM budget_beasiswa WHERE company_id=? GROUP BY cat1",
        (company_id,)
    ).fetchall():
        bgt[r["cat1"]] = r["t"]
    pay = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) AS t FROM payment_beasiswa WHERE company_id=? GROUP BY cat1",
        (company_id,)
    ).fetchall():
        pay[r["cat1"]] = r["t"]
    conn.close()
    cats = ["By Pendidikan", "By Tunjangan", "By Penelitian", "By Medical"]
    categories = []
    for c in cats:
        b, p = bgt.get(c, 0), pay.get(c, 0)
        categories.append({"cat1": c, "budget": b, "payment": p, "selisih": b - p})
    tb, tp = sum(bgt.values()), sum(pay.values())
    return {"categories": categories, "total": {"budget": tb, "payment": tp, "selisih": tb - tp}}


def _delete_payment_cascade(conn, company_id: int, payment_id: int, pam_no, line_id) -> None:
    """Hapus satu payment_beasiswa beserta rekam_medis, pam_records yang tidak terpakai lagi, dan
    kembalikan PA ke open kalau tidak ada payment aktif lagi -- semuanya dalam SATU batch
    (atomic-flows.md Task 15). Hitungan sisa yang dulu dibaca di Python setelah DELETE sekarang
    menjadi kondisi NOT EXISTS di SQL (dievaluasi di transaksi yang sama, setelah DELETE).
    pa_id per tabel lines dibaca sebelum batch (tabel lines tidak diubah oleh alur ini).
    Batch diawali advisory lock per company supaya dua penghapusan bersamaan pada PAM/PA yang sama
    tidak sama-sama melihat baris saudaranya masih ada (lalu tidak ada yang menghapus PAM/revert PA)."""
    pa_targets = []
    if line_id:
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines", "etf_pa"),
            ("app_pa_lines", "app_pa"),
            ("sml_pa_lines", "sml_pa"),
        ]:
            pa_row = conn.execute(
                f"SELECT pa_id FROM {lines_tbl} WHERE id=?", (line_id,)
            ).fetchone()
            if pa_row:
                pa_targets.append((lines_tbl, pa_tbl, pa_row[0]))

    stmts = [
        ("SELECT pg_advisory_xact_lock(hashtext(?))", (f"beasiswa_pb_delete:{company_id}",)),
        ("DELETE FROM rekam_medis WHERE payment_id=? AND company_id=?", (payment_id, company_id)),
        ("DELETE FROM payment_beasiswa WHERE id=? AND company_id=?", (payment_id, company_id)),
    ]
    # Hapus pam_records jika tidak ada payment lain yang memakai PAM ini
    if pam_no:
        stmts.append((
            "DELETE FROM pam_records WHERE pam_no=? AND company_id=? AND NOT EXISTS ("
            "SELECT 1 FROM payment_beasiswa WHERE pam=? AND company_id=?)",
            (pam_no, company_id, pam_no, company_id)
        ))
    # Revert semua PA tables ke open jika tidak ada payment aktif lagi untuk PA ini
    if pa_targets:
        _now = _ts()
        for lines_tbl, pa_tbl, pa_id in pa_targets:
            stmts.append((
                f"""UPDATE {pa_tbl} SET status='open', nomor_pam=NULL, updated_at=?
                    WHERE id=? AND company_id=? AND NOT EXISTS (
                        SELECT 1 FROM payment_beasiswa pb
                        JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                        WHERE el.pa_id=? AND pb.company_id=? AND pb.status != 'rejected')""",
                (_now, pa_id, company_id, pa_id, company_id)
            ))
    conn.batch(stmts)


def delete_payment_row(company_id: int, row_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, status, pam, etf_pa_line_id FROM payment_beasiswa WHERE id=? AND company_id=?",
        (row_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris payment tidak ditemukan."}
    if row["status"] == "complete":
        conn.close()
        return {"ok": False, "pesan": "Payment yang sudah selesai tidak bisa dihapus."}

    _delete_payment_cascade(conn, company_id, row_id, row["pam"], row["etf_pa_line_id"])
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Baris payment dihapus."}


def delete_payment_beasiswa(payment_id: int, company_id: int) -> dict:
    """Hapus payment_beasiswa beserta rekam_medis terkait (cascade)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, status, pam, etf_pa_line_id FROM payment_beasiswa WHERE id=? AND company_id=?",
        (payment_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris payment tidak ditemukan."}
    if row["status"] in ("complete", "rejected"):
        conn.close()
        return {"ok": False, "pesan": "Payment yang sudah selesai atau di-reject tidak bisa dihapus."}

    _delete_payment_cascade(conn, company_id, payment_id, row["pam"], row["etf_pa_line_id"])
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Baris payment dihapus."}


def update_payment_row(company_id: int, row_id: int, pam: str = None, tanggal_bayar: str = None) -> dict:
    """Edit terbatas untuk baris payment_beasiswa: No PAM (payment_beasiswa.pam)
    dan Tanggal Bayar (pam_records.tanggal_bayar, di-lookup lewat pam_no).
    Field lain (kategori, amount, pillar, dll) tidak bisa diedit lewat sini."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, status, pam FROM payment_beasiswa WHERE id=? AND company_id=?",
        (row_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris payment tidak ditemukan."}

    effective_pam = row["pam"]
    ts = _ts()

    # Atomik (atomic-flows.md Task 15): semua validasi sebelum tulisan apa pun, lalu kedua UPDATE
    # dalam satu batch (dulu rollback() dimaksudkan membatalkan UPDATE payment_beasiswa.pam).
    stmts = []
    if pam is not None and pam != row["pam"]:
        target = conn.execute(
            "SELECT id FROM pam_records WHERE pam_no=? AND company_id=?",
            (pam, company_id)
        ).fetchone()
        if not target:
            conn.close()
            return {"ok": False, "pesan": "Nomor PAM tidak ditemukan."}
        # EXISTS: kalau PAM target hilang di antara validasi dan batch (race), UPDATE ini dan
        # UPDATE pam_records sama-sama mengenai 0 baris -> tidak ada yang tersimpan, sama dengan
        # maksud rollback() versi SQLite.
        stmts.append((
            "UPDATE payment_beasiswa SET pam=? WHERE id=? AND EXISTS ("
            "SELECT 1 FROM pam_records WHERE pam_no=? AND company_id=?)",
            (pam, row_id, pam, company_id)
        ))
        effective_pam = pam

    pam_update_idx = None
    if tanggal_bayar is not None:
        if not effective_pam:
            conn.close()
            return {"ok": False, "pesan": "Isi No PAM dulu sebelum mengisi tanggal bayar."}
        pam_update_idx = len(stmts)
        stmts.append((
            "UPDATE pam_records SET tanggal_bayar=?, updated_at=? WHERE pam_no=? AND company_id=?",
            (tanggal_bayar, ts, effective_pam, company_id)
        ))

    if stmts:
        curs = conn.batch(stmts)
        if pam_update_idx is not None and curs[pam_update_idx].rowcount == 0:
            conn.close()
            return {"ok": False, "pesan": "Nomor PAM tidak ditemukan."}

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Payment berhasil diupdate."}


def get_payment(company_id: int, siswa_code: str = "", status: str = "") -> list:
    # Tanggal Bayar/Paid: APP/LAND/ENERGY/SETF each have their own tgl_Paid_<PILLAR>
    # column on payment_beasiswa, but AGRI (the majority pillar) has none -- for
    # AGRI (and any other pillar without a dedicated column) fall back to the
    # linked PAM's own tanggal_bayar instead of leaving the field unset.
    sql    = ("SELECT pb.*, s.nama, "
              "COALESCE("
              "CASE pb.pillar "
              "WHEN 'APP' THEN pb.\"tgl_Paid_APP\" "
              "WHEN 'LAND' THEN pb.\"tgl_Paid_LAND\" "
              "WHEN 'ENERGY' THEN pb.\"tgl_Paid_ENERGY\" "
              "WHEN 'SETF' THEN pb.\"tgl_Paid_SETF\" "
              "END, pr.tanggal_bayar) AS tanggal_bayar "
              "FROM payment_beasiswa pb "
              "LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code "
              "LEFT JOIN pam_records pr ON pr.pam_no=pb.pam AND pr.company_id=pb.company_id "
              "WHERE pb.company_id=?")
    params = [company_id]
    if siswa_code:
        sql    += " AND pb.siswa_code=?"
        params += [siswa_code]
    if status:
        sql    += " AND pb.status=?"
        params += [status]
    sql += " ORDER BY pb.tanggal DESC NULLS LAST"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_sisa_budget(company_id: int, siswa_code: str) -> dict:
    conn = get_conn()
    bgt  = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) as total FROM budget_beasiswa "
        "WHERE company_id=? AND siswa_code=? AND (tgl_expired IS NULL OR tgl_expired >= to_char(now() at time zone interval '+07:00', 'YYYY-MM-DD')) GROUP BY cat1",
        (company_id, siswa_code)
    ).fetchall():
        bgt[r["cat1"]] = r["total"]

    pay = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) as total FROM payment_beasiswa "
        "WHERE company_id=? AND siswa_code=? GROUP BY cat1",
        (company_id, siswa_code)
    ).fetchall():
        pay[r["cat1"]] = r["total"]

    conn.close()
    all_cats      = set(list(bgt.keys()) + list(pay.keys()))
    sisa          = {c: bgt.get(c, 0) - pay.get(c, 0) for c in all_cats}
    total_budget  = sum(bgt.values())
    total_payment = sum(pay.values())
    return {
        "budget": bgt, "payment": pay, "sisa": sisa,
        "total_budget": total_budget, "total_payment": total_payment,
        "total_sisa": total_budget - total_payment,
    }


def get_laporan_siswa(company_id: int, code: str) -> dict | None:
    siswa = get_siswa_detail(company_id, code)
    if not siswa:
        return None
    bgt  = get_budget(company_id, code)
    pay_rows = get_payment(company_id, code)

    pay_totals: dict = {}
    pay_grand = 0.0
    for r in pay_rows:
        pay_totals[r["cat1"]] = pay_totals.get(r["cat1"], 0) + r["amount"]
        pay_grand += r["amount"]

    all_cats = list(dict.fromkeys(list(bgt["totals"].keys()) + list(pay_totals.keys())))
    cat_summary = [
        {"cat1": c, "budget": bgt["totals"].get(c, 0),
         "payment": pay_totals.get(c, 0),
         "sisa": bgt["totals"].get(c, 0) - pay_totals.get(c, 0)}
        for c in all_cats
    ]
    return {
        "siswa": siswa,
        "budget_rows": bgt["rows"],
        "payment_rows": pay_rows,
        "cat_summary": cat_summary,
        "total_budget": bgt["grand"],
        "total_payment": pay_grand,
        "total_sisa": bgt["grand"] - pay_grand,
    }


def add_klaim_multi(company_id: int, pam: str, pillar: str,
                    perusahaan: str, rows: list) -> dict:
    conn  = get_conn()
    saved = 0
    stmts = []
    for row in rows:
        try:
            amount = float(str(row.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        siswa_code = (row.get("siswa_code") or "").strip()
        if not siswa_code:
            continue
        perawatan    = row.get("perawatan", "")
        tanggal      = row.get("tanggal", "")
        kelas        = row.get("kelas", "")
        rumah_sakit  = row.get("rumah_sakit", "")
        diagnosa     = row.get("diagnosa", "")
        spesialisasi = row.get("spesialisasi", "")

        etf_pa_line_id = row.get("etf_pa_line_id") or None
        stmts.append((
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,pam,status,etf_pa_line_id)
               VALUES (?,?,?,?,?,?,?,?,?,'open',?)""",
            (company_id, siswa_code, "By Medical", perawatan,
             tanggal, amount, pillar, perusahaan, pam, etf_pa_line_id)
        ))
        # payment_id = id payment_beasiswa yang baru di-INSERT tepat sebelumnya (currval, batch sama).
        stmts.append((
            f"""INSERT INTO klaim_medical
               (company_id,siswa_code,pam,tanggal,amount,perawatan,kelas,
                rumah_sakit,diagnosa,spesialisasi,pillar,perusahaan,payment_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,{_PB_CURRVAL})""",
            (company_id, siswa_code, pam, tanggal, amount, perawatan, kelas,
             rumah_sakit, diagnosa, spesialisasi, pillar, perusahaan)
        ))
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada klaim valid untuk disimpan.", "saved": 0}

    # Atomik (atomic-flows.md Task 15): pasangan payment_beasiswa -> klaim_medical dalam satu batch.
    conn.batch(stmts)
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} klaim berhasil disimpan.", "saved": saved}


def get_klaim_list(company_id: int, search: str = "", bulan: str = "",
                   tahun: str = "", perawatan: str = "", limit: int = 500) -> dict:
    sql = (
        "SELECT k.*, s.nama FROM klaim_medical k "
        "LEFT JOIN siswa s ON s.company_id=k.company_id AND s.code=k.siswa_code "
        "WHERE k.company_id=?"
    )
    params = [company_id]
    if search:
        q = f"%{search}%"
        sql += (" AND (k.siswa_code ILIKE ? OR s.nama ILIKE ? OR k.pam ILIKE ?"
                " OR k.rumah_sakit ILIKE ? OR k.diagnosa ILIKE ?)")
        params += [q, q, q, q, q]
    if perawatan:
        sql += " AND k.perawatan=?"
        params += [perawatan]
    if bulan:
        sql += " AND fh_strftime('%m', k.tanggal)=?"
        params += [bulan.zfill(2)]
    if tahun:
        sql += " AND fh_strftime('%Y', k.tanggal)=?"
        params += [tahun]
    agg_sql = sql.replace(
        "SELECT k.*, s.nama FROM",
        "SELECT k.amount FROM"
    )
    conn  = get_conn()
    total = conn.execute(f"SELECT COUNT(*) FROM ({agg_sql}) AS _q", params).fetchone()[0]
    grand = conn.execute(
        f"SELECT COALESCE(SUM(amount),0) FROM ({agg_sql}) AS _q", params
    ).fetchone()[0]
    sql  += " ORDER BY k.tanggal DESC NULLS LAST"
    rows  = [dict(r) for r in conn.execute(sql + " LIMIT ?", params + [limit]).fetchall()]
    conn.close()
    return {"rows": rows, "total": total, "grand": grand}


def delete_klaim_row(company_id: int, row_id: int) -> dict:
    conn = get_conn()
    row  = conn.execute(
        "SELECT id, payment_id FROM klaim_medical WHERE id=? AND company_id=?",
        (row_id, company_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Klaim tidak ditemukan."}
    if row["payment_id"]:
        pay = conn.execute(
            "SELECT status FROM payment_beasiswa WHERE id=? AND company_id=?",
            (row["payment_id"], company_id)
        ).fetchone()
        if pay and pay["status"] in ("complete", "rejected"):
            conn.close()
            return {"ok": False, "pesan": "Klaim yang sudah selesai atau di-reject tidak bisa dihapus."}
    # Atomik (atomic-flows.md Task 15): kedua DELETE dalam satu batch.
    stmts = []
    if row["payment_id"]:
        stmts.append(("DELETE FROM payment_beasiswa WHERE id=? AND company_id=?",
                      (row["payment_id"], company_id)))
    stmts.append(("DELETE FROM klaim_medical WHERE id=? AND company_id=?",
                  (row_id, company_id)))
    conn.batch(stmts)
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Klaim berhasil dihapus."}


def get_rekap(company_id: int, program: str = "", pillar: str = "",
              status: str = "", search: str = "",
              jenjang: str = "", angkatan: str = "") -> list:
    sql    = "SELECT * FROM siswa WHERE company_id=?"
    params = [company_id]
    if search:
        q       = f"%{search}%"
        sql    += " AND (nama ILIKE ? OR code ILIKE ?)"
        params += [q, q]
    if program:
        sql    += " AND program=?"
        params += [program]
    if status:
        sql    += " AND status=?"
        params += [status]
    if jenjang:
        sql    += " AND jenjang=?"
        params += [jenjang]
    if angkatan:
        sql    += " AND angkatan=?"
        params += [int(angkatan)]
    sql += " ORDER BY nama"

    conn  = get_conn()
    siswa = conn.execute(sql, params).fetchall()

    bgt_map = {}
    for r in conn.execute(
        "SELECT siswa_code, SUM(amount) as t FROM budget_beasiswa WHERE company_id=? GROUP BY siswa_code",
        (company_id,)
    ).fetchall():
        bgt_map[r["siswa_code"]] = r["t"]

    pay_sql    = "SELECT siswa_code, SUM(amount) as t FROM payment_beasiswa WHERE company_id=?"
    pay_params = [company_id]
    if pillar:
        pay_sql    += " AND pillar=?"
        pay_params += [pillar]
    pay_sql += " GROUP BY siswa_code"
    pay_map = {}
    for r in conn.execute(pay_sql, pay_params).fetchall():
        pay_map[r["siswa_code"]] = r["t"]

    conn.close()

    result = []
    for s in siswa:
        code   = s["code"]
        total_b = bgt_map.get(code, 0)
        total_p = pay_map.get(code, 0)
        result.append({
            "code": code, "nama": s["nama"], "jenjang": s["jenjang"],
            "angkatan": s["angkatan"], "program": s["program"], "status": s["status"],
            "total_budget": total_b, "total_payment": total_p,
            "sisa": total_b - total_p,
        })
    return result


# --- Dashboard Functions ---

def _year_filter_sql(years, column):
    if not years:
        return "", []
    placeholders = ",".join("?" for _ in years)
    return f" AND fh_strftime('%Y', {column}) IN ({placeholders})", [str(y) for y in years]

def _expand_pillars(pillars):
    if not pillars:
        return None
    expanded = set()
    for p in pillars:
        if p == "PROPERTY":
            expanded.add("PROPERTY")
            expanded.add("LAND")
        elif p == "EFIN":
            expanded.add("EFIN")
            expanded.add("FINANCE")
            expanded.add("ENERGY & FINANCE")
        elif p == "LAND":
            expanded.add("LAND")
            expanded.add("PROPERTY")
        elif p in ("FINANCE", "ENERGY & FINANCE"):
            expanded.add(p)
            expanded.add("EFIN")
        else:
            expanded.add(p)
    return list(expanded)

def _pillar_filter_sql(pillars, column):
    if not pillars:
        return "", []
    expanded = _expand_pillars(pillars)
    placeholders = ",".join("?" for _ in expanded)
    return f" AND {column} IN ({placeholders})", list(expanded)

def _program_filter_sql(programs, column):
    if not programs:
        return "", []
    placeholders = ",".join("?" for _ in programs)
    return f" AND {column} IN ({placeholders})", list(programs)

def _jenjang_filter_sql(jenjangs, column):
    if not jenjangs:
        return "", []
    placeholders = ",".join("?" for _ in jenjangs)
    return f" AND {column} IN ({placeholders})", list(jenjangs)

def _angkatan_filter_sql(angkatans, column):
    if not angkatans:
        return "", []
    placeholders = ",".join("?" for _ in angkatans)
    return f" AND {column} IN ({placeholders})", list(angkatans)

def _status_filter_sql(statuses, column):
    if not statuses:
        return "", []
    placeholders = ",".join("?" for _ in statuses)
    return f" AND {column} IN ({placeholders})", list(statuses)

def _status_case_sql(statuses, column):
    if not statuses:
        return "1=1", []
    placeholders = ",".join("?" for _ in statuses)
    return f"{column} IN ({placeholders})", list(statuses)


def get_dashboard_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    status_case_frag, status_case_params = _status_case_sql(statuses, "status")

    rows = conn.execute(
        f"""
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.program, s.status,
               COALESCE(b.budget_total, 0)    AS budget_total,
               COALESCE(p.payment_total, 0)   AS payment_total,
               COALESCE(p.realisasi_total, 0) AS realisasi_total
        FROM siswa s
        LEFT JOIN (
            SELECT siswa_code, SUM(amount) AS budget_total
            FROM budget_beasiswa
            WHERE company_id = ?{budget_year_sql}
            GROUP BY siswa_code
        ) b ON b.siswa_code = s.code
        LEFT JOIN (
            SELECT siswa_code,
                   SUM(amount) AS payment_total,
                   SUM(CASE WHEN {status_case_frag} THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?{payment_year_sql}{pillar_sql}
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ?{program_sql}{jenjang_sql}{angkatan_sql}
        ORDER BY s.nama
        """,
        [company_id, *budget_year_params, *status_case_params, company_id, *payment_year_params, *pillar_params, company_id, *program_params, *jenjang_params, *angkatan_params],
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        budget = float(r["budget_total"] or 0)
        realisasi = float(r["realisasi_total"] or 0)
        result.append({
            "siswa_code":      r["code"],
            "nama":            r["nama"],
            "jenjang":         r["jenjang"],
            "angkatan":        r["angkatan"],
            "program":         r["program"],
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   float(r["payment_total"] or 0),
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result


def get_dashboard_breakdown(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    status_case_frag, status_case_params = _status_case_sql(statuses, "p.status")

    budget_rows = conn.execute(
        f"""
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}{angkatan_sql}
        GROUP BY b.cat1
        """,
        [company_id, *budget_year_params, *program_params, *jenjang_params, *angkatan_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN {status_case_frag} THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}{angkatan_sql}
        GROUP BY p.cat1
        """,
        [*status_case_params, company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, *angkatan_params],
    ).fetchall()

    budget_jenjang_rows = conn.execute(
        f"""
        SELECT s.jenjang, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ?{budget_year_sql}{program_sql}{jenjang_sql}{angkatan_sql}
        GROUP BY s.jenjang
        """,
        [company_id, *budget_year_params, *program_params, *jenjang_params, *angkatan_params],
    ).fetchall()

    payment_jenjang_rows = conn.execute(
        f"""
        SELECT s.jenjang,
               SUM(p.amount) AS total,
               SUM(CASE WHEN {status_case_frag} THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}{angkatan_sql}
        GROUP BY s.jenjang
        """,
        [*status_case_params, company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, *angkatan_params],
    ).fetchall()
    conn.close()

    kategori = {}
    for r in budget_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["budget"] += float(r["total"] or 0)
    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        kategori.setdefault(cat1, {"cat1": cat1, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        kategori[cat1]["payment"] += float(r["total"] or 0)
        kategori[cat1]["realisasi"] += float(r["realisasi"] or 0)

    jenjang = {}
    for r in budget_jenjang_rows:
        j = r["jenjang"] or "(Tanpa Jenjang)"
        jenjang.setdefault(j, {"jenjang": j, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        jenjang[j]["budget"] += float(r["total"] or 0)
    for r in payment_jenjang_rows:
        j = r["jenjang"] or "(Tanpa Jenjang)"
        jenjang.setdefault(j, {"jenjang": j, "budget": 0.0, "payment": 0.0, "realisasi": 0.0})
        jenjang[j]["payment"] += float(r["total"] or 0)
        jenjang[j]["realisasi"] += float(r["realisasi"] or 0)

    over_budget = [
        {
            "siswa_code":      s["siswa_code"],
            "nama":            s["nama"],
            "budget_total":    s["budget_total"],
            "realisasi_total": s["realisasi_total"],
            "selisih":         s["realisasi_total"] - s["budget_total"],
        }
        for s in get_dashboard_summary(company_id, years, pillars, programs, jenjangs, statuses)
        if s["realisasi_total"] > s["budget_total"]
    ]

    return {"kategori": list(kategori.values()), "jenjang": list(jenjang.values()), "over_budget": over_budget}


def get_dashboard_monthly(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None) -> dict:
    if not years:
        return {"chart_year": None, "months": [], "comparison": []}

    chart_year = max(years)
    years_to_fetch = set(years)
    years_to_fetch.add(chart_year - 1)
    conn = get_conn()

    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")

    budget_rows = conn.execute(
        f"""
        SELECT CAST(fh_strftime('%m', b.tanggal) AS bigint) AS bulan, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND fh_strftime('%Y', b.tanggal) = ?{program_sql}{jenjang_sql}{angkatan_sql}
        GROUP BY bulan
        """,
        [company_id, str(chart_year), *program_params, *jenjang_params, *angkatan_params],
    ).fetchall()

    year_placeholders = ",".join("?" for _ in years_to_fetch)
    realisasi_rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', p.tanggal) AS tahun, CAST(fh_strftime('%m', p.tanggal) AS bigint) AS bulan,
               SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?
              AND fh_strftime('%Y', p.tanggal) IN ({year_placeholders}){pillar_sql}{program_sql}{jenjang_sql}{angkatan_sql}{status_sql}
        GROUP BY tahun, bulan
        """,
        [company_id, *[str(y) for y in years_to_fetch], *pillar_params, *program_params, *jenjang_params, *angkatan_params, *status_params],
    ).fetchall()
    conn.close()

    budget_by_month = {r["bulan"]: float(r["total"] or 0) for r in budget_rows}
    realisasi_by_year_month = {}
    for r in realisasi_rows:
        realisasi_by_year_month.setdefault(r["tahun"], {})[r["bulan"]] = float(r["total"] or 0)

    months = [
        {
            "bulan": m,
            "budget": budget_by_month.get(m, 0.0),
            "realisasi": realisasi_by_year_month.get(str(chart_year), {}).get(m, 0.0),
            "realisasi_last_year": realisasi_by_year_month.get(str(chart_year - 1), {}).get(m, 0.0),
        }
        for m in range(1, 13)
    ]
    comparison = [
        {
            "bulan": m,
            "per_tahun": {str(y): realisasi_by_year_month.get(str(y), {}).get(m, 0.0) for y in years},
        }
        for m in range(1, 13)
    ]
    return {"chart_year": chart_year, "months": months, "comparison": comparison}


def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None, limit: int = 20) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")

    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}{angkatan_sql}{status_sql}
        ORDER BY p.tanggal DESC NULLS LAST, p.id DESC
        LIMIT ?
        """,
        [company_id, *payment_year_params, *pillar_params, *program_params, *jenjang_params, *angkatan_params, *status_params, limit],
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_dashboard_program_summary(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None) -> list:
    summary = get_dashboard_summary(company_id, years, pillars, programs, jenjangs, statuses, angkatans)
    by_program = {}
    for s in summary:
        prog = s["program"] or "(Tanpa Program)"
        by_program.setdefault(prog, {"program": prog, "budget": 0.0, "realisasi": 0.0, "sisa": 0.0})
        by_program[prog]["budget"] += s["budget_total"]
        by_program[prog]["realisasi"] += s["realisasi_total"]
    
    for p in by_program.values():
        p["sisa"] = p["budget"] - p["realisasi"]
        
    return sorted(list(by_program.values()), key=lambda x: x["program"])


def get_dashboard_pillar_yearly(company_id: int, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None, years: list = None) -> list:
    conn = get_conn()
    year_sql, year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")
    mapped_pillar_expr = """CASE 
        WHEN p.pillar = 'LAND' THEN 'PROPERTY'
        WHEN p.pillar IN ('FINANCE', 'EFIN', 'ENERGY & FINANCE') THEN 'EFIN'
        ELSE p.pillar 
    END"""
    rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', p.tanggal) AS tahun, ({mapped_pillar_expr}) AS pillar, SUM(p.amount) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{year_sql}{pillar_sql}{program_sql}{jenjang_sql}{angkatan_sql}{status_sql}
        GROUP BY tahun, ({mapped_pillar_expr})
        ORDER BY tahun DESC NULLS LAST, pillar ASC NULLS FIRST
        """,
        [company_id, *year_params, *pillar_params, *program_params, *jenjang_params, *angkatan_params, *status_params],
    ).fetchall()
    conn.close()
    
    by_year = {}
    for r in rows:
        tahun = int(r["tahun"])
        pillar_name = r["pillar"] or "(Tanpa Pillar)"
        by_year.setdefault(tahun, {})
        by_year[tahun][pillar_name] = float(r["realisasi"] or 0)
        
    result = []
    for y, pillar_dict in sorted(by_year.items(), key=lambda x: x[0], reverse=True):
        result.append({"tahun": y, "pillars": pillar_dict})
    return result


def get_dashboard_trend_transactions(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None, cat1: str = None, bulan: int = None) -> list:
    conn = get_conn()
    year_sql, year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    program_sql, program_params = _program_filter_sql(programs, "s.program")
    jenjang_sql, jenjang_params = _jenjang_filter_sql(jenjangs, "s.jenjang")
    angkatan_sql, angkatan_params = _angkatan_filter_sql(angkatans, "s.angkatan")
    status_sql, status_params = _status_filter_sql(statuses, "p.status")

    cat1_sql = ""
    cat1_params = []
    if cat1:
        cat1_sql = " AND p.cat1 = ?"
        cat1_params = [cat1]

    bulan_sql = ""
    bulan_params = []
    if bulan:
        bulan_sql = " AND CAST(fh_strftime('%m', p.tanggal) AS bigint) = ?"
        bulan_params = [int(bulan)]

    mapped_pillar_expr = """CASE 
        WHEN p.pillar = 'LAND' THEN 'PROPERTY'
        WHEN p.pillar IN ('FINANCE', 'EFIN', 'ENERGY & FINANCE') THEN 'EFIN'
        ELSE p.pillar 
    END"""
    rows = conn.execute(
        f"""
        SELECT p.id, p.tanggal, fh_strftime('%Y', p.tanggal) AS tahun, CAST(fh_strftime('%m', p.tanggal) AS bigint) AS bulan,
               p.siswa_code, s.nama, 
               ({mapped_pillar_expr}) AS pillar, s.program, s.jenjang, s.angkatan, s.universitas, p.cat1, p.cat2, 
               p.amount, p.pam, p.perusahaan, p.status
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ?
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{year_sql}{pillar_sql}{program_sql}{jenjang_sql}{angkatan_sql}{status_sql}{cat1_sql}{bulan_sql}
        ORDER BY p.tanggal DESC, p.id DESC
        """,
        [company_id, *year_params, *pillar_params, *program_params, *jenjang_params, *angkatan_params, *status_params, *cat1_params, *bulan_params],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_budget_sufficient(company_id: int, rows: list, default_cat1: str = None) -> dict:
    req = {}
    for r in rows:
        sc = r.get("siswa_code")
        c1 = r.get("cat1") or default_cat1
        try:
            amt = float(str(r.get("amount", 0)).replace(",", ""))
        except:
            amt = 0
        if not sc or not c1 or amt <= 0:
            continue
        req[(sc, c1)] = req.get((sc, c1), 0) + amt

    if not req:
        return {"ok": True}

    for (sc, c1), total_req in req.items():
        sisa_info = get_sisa_budget(company_id, sc)
        sisa = sisa_info["sisa"].get(c1, 0)
        if total_req > sisa:
            return {"ok": False, "pesan": f"Budget tidak cukup untuk {sc} (Kategori {c1}). Diminta: Rp {total_req:,.0f}, Sisa: Rp {sisa:,.0f}."}
    return {"ok": True}


# ================= BUDGET APPROVAL =================

def delete_budget_row(company_id: int, row_id: int, created_by: str) -> dict:
    conn = get_conn()
    row  = conn.execute("SELECT * FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris budget tidak ditemukan."}
    conn.execute(
        "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) VALUES (?, ?, 'DELETE', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (company_id, row["siswa_code"], row["id"], row["cat1"], row["cat2"], row["tanggal"], row["amount"], row["pillar"], row["tgl_expired"], created_by, str(uuid.uuid4())[:8])
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Pengajuan hapus budget telah dikirim ke BC."}

def update_budget_row(company_id: int, row_id: int, data: dict, created_by: str) -> dict:
    conn = get_conn()
    row  = conn.execute("SELECT * FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris budget tidak ditemukan."}
    try:
        amount = float(str(data.get("amount", 0)).replace(",", ""))
    except (ValueError, TypeError):
        amount = 0
    if amount <= 0:
        conn.close()
        return {"ok": False, "pesan": "Amount harus lebih dari 0."}
    conn.execute(
        "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) VALUES (?, ?, 'EDIT', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (company_id, row["siswa_code"], row["id"], data.get("cat1",""), data.get("cat2",""), data.get("tanggal",""), amount, data.get("pillar",""), data.get("tgl_expired") or None, created_by, str(uuid.uuid4())[:8])
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Pengajuan edit budget telah dikirim ke BC."}

def add_budget_batch(company_id: int, siswa_code: str, tanggal: str, pillar: str, items: list, created_by: str) -> dict:
    conn  = get_conn()
    batch_id = str(uuid.uuid4())[:8]
    saved = 0
    # Atomik (atomic-flows.md Task 15): semua baris request dalam satu batch.
    stmts = []
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        stmts.append((
            "INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) VALUES (?, ?, 'ADD', ?, ?, ?, ?, ?, ?, ?, ?)",
            (company_id, siswa_code, item.get("cat1",""), item.get("cat2",""), tanggal, amount, pillar, item.get("tgl_expired") or None, created_by, batch_id)
        ))
        saved += 1
    if stmts:
        conn.batch(stmts)
    conn.commit()
    conn.close()
    if saved == 0:
        return {"ok": False, "pesan": "Tidak ada baris budget valid yang dikirim."}
    return {"ok": True, "pesan": f"{saved} baris pengajuan budget telah dikirim ke BC."}

def get_budget_requests(company_id: int) -> list:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT req.*, s.nama as siswa_nama "
        "FROM budget_beasiswa_requests req "
        "LEFT JOIN siswa s ON s.company_id=req.company_id AND s.code=req.siswa_code "
        "WHERE req.company_id=? ORDER BY req.id DESC",
        (company_id,)
    ).fetchall()]
    conn.close()
    
    # Group by batch_id
    batches = {}
    for r in rows:
        bid = r.get("batch_id")
        if not bid:
            bid = str(r["id"]) # fallback
        if bid not in batches:
            batches[bid] = {
                "batch_id": bid,
                "created_at": r["created_at"],
                "siswa_code": r["siswa_code"],
                "siswa_nama": r["siswa_nama"],
                "action_type": r["action_type"],
                "created_by": r["created_by"],
                "total_amount": 0,
                "lines": [],
                "status": "PENDING", # compute aggregate status later
            }
        batches[bid]["lines"].append(r)
        batches[bid]["total_amount"] += r["amount"]
    
    result = []
    for bid, data in batches.items():
        statuses = set([l["status"] for l in data["lines"]])
        if "PENDING" in statuses and ("APPROVED" in statuses or "REJECTED" in statuses):
            data["status"] = "PARTIAL"
        elif len(statuses) == 1:
            data["status"] = statuses.pop()
        else:
            data["status"] = "PROCESSED"
        result.append(data)
        
    return sorted(result, key=lambda x: x["created_at"], reverse=True)

# CURRENT_TIMESTAMP SQLite: teks UTC 'YYYY-MM-DD HH:MM:SS'.
_NOW_UTC = "to_char(now() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS')"


def approve_budget_request_batch(company_id: int, request_ids: list, processed_by: str) -> dict:
    """Atomik + aman dari race (atomic-flows.md Task 15): SATU batch yang diawali
    SELECT ... FOR UPDATE pada semua request yang diminta. Approve kedua yang bersamaan menunggu
    sampai yang pertama commit, lalu statement berikutnya (snapshot baru, READ COMMITTED) melihat
    status APPROVED sehingga aksinya tidak dijalankan dua kali. Pengecekan PENDING + action_type
    yang dulu di Python sekarang menjadi kondisi WHERE tiap statement; urutan per request sama
    (aksi budget_beasiswa lalu tandai APPROVED), jadi id yang sama dua kali di daftar diproses
    sekali seperti sebelumnya."""
    conn = get_conn()
    ids = list(request_ids or [])
    if not ids:
        conn.close()
        return {"ok": True, "pesan": "0 baris pengajuan disetujui."}
    ph = ",".join("?" * len(ids))
    stmts = [(
        f"SELECT id FROM budget_beasiswa_requests WHERE id IN ({ph}) AND company_id=? "
        "ORDER BY id FOR UPDATE",
        list(ids) + [company_id]
    )]
    mark_idx = []
    pending = "r.id=? AND r.company_id=? AND r.status='PENDING'"
    for req_id in ids:
        stmts.append((
            "INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, tgl_expired) "
            "SELECT ?, r.siswa_code, r.cat1, r.cat2, r.tanggal, r.amount, r.pillar, r.tgl_expired "
            f"FROM budget_beasiswa_requests r WHERE {pending} AND r.action_type='ADD'",
            (company_id, req_id, company_id)
        ))
        stmts.append((
            "UPDATE budget_beasiswa SET cat1=r.cat1, cat2=r.cat2, tanggal=r.tanggal, amount=r.amount, "
            "pillar=r.pillar, tgl_expired=r.tgl_expired "
            f"FROM budget_beasiswa_requests r WHERE {pending} AND r.action_type='EDIT' "
            "AND budget_beasiswa.id=r.budget_id AND budget_beasiswa.company_id=?",
            (req_id, company_id, company_id)
        ))
        stmts.append((
            "DELETE FROM budget_beasiswa USING budget_beasiswa_requests r "
            f"WHERE {pending} AND r.action_type='DELETE' "
            "AND budget_beasiswa.id=r.budget_id AND budget_beasiswa.company_id=?",
            (req_id, company_id, company_id)
        ))
        mark_idx.append(len(stmts))
        stmts.append((
            f"UPDATE budget_beasiswa_requests SET status='APPROVED', processed_by=?, processed_at={_NOW_UTC} "
            "WHERE id=? AND company_id=? AND status='PENDING'",
            (processed_by, req_id, company_id)
        ))
    curs = conn.batch(stmts)
    approved = sum(1 for i in mark_idx if curs[i].rowcount > 0)
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{approved} baris pengajuan disetujui."}

def reject_budget_request_batch(company_id: int, request_ids: list, processed_by: str, reason: str) -> dict:
    """Atomik (atomic-flows.md Task 15): satu UPDATE untuk semua request PENDING milik company;
    rowcount = jumlah yang ditolak (id ganda di daftar dihitung sekali, seperti sebelumnya)."""
    conn = get_conn()
    ids = list(request_ids or [])
    rejected = 0
    if ids:
        ph = ",".join("?" * len(ids))
        cur = conn.execute(
            f"UPDATE budget_beasiswa_requests SET status='REJECTED', processed_by=?, processed_at={_NOW_UTC}, reject_reason=? "
            f"WHERE id IN ({ph}) AND company_id=? AND status='PENDING'",
            [processed_by, reason] + ids + [company_id]
        )
        rejected = cur.rowcount
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{rejected} baris pengajuan ditolak."}

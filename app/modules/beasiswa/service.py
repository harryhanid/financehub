# modules/beasiswa/service.py
from datetime import datetime
from database import get_conn
import config
from modules.payment_memo.service import create_pam_record


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
            "SELECT name, pillar, cost_center FROM vendors WHERE name LIKE ? ORDER BY name",
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
        sql    += " AND (nama LIKE ? OR code LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if status:
        sql    += " AND status=?"
        params += [status]
    if program:
        sql    += " AND program=?"
        params += [program]
    sql += " ORDER BY created_at DESC"
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
           (company_id, code, nama, jenjang, angkatan, program, fakultas, universitas,
            bank, norek, namarek, referensi,
            ipk_sem1,ipk_sem2,ipk_sem3,ipk_sem4,ipk_sem5,
            ipk_sem6,ipk_sem7,ipk_sem8,ipk_sem9,ipk_sem10,
            ipk_pen1,ipk_pen2,ipk_pen3,
            status, catatan, catatan_budget, catatan_payment, prodi, angkatan_kuliah, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, code, nama,
         data.get("jenjang", ""), data.get("angkatan") or None,
         data.get("program", ""), data.get("fakultas", ""), data.get("universitas", ""),
         data.get("bank", ""), data.get("norek", ""), data.get("namarek", ""),
         data.get("referensi", ""),
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
           nama=?,jenjang=?,angkatan=?,program=?,fakultas=?,universitas=?,
           bank=?,norek=?,namarek=?,referensi=?,
           ipk_sem1=?,ipk_sem2=?,ipk_sem3=?,ipk_sem4=?,ipk_sem5=?,
           ipk_sem6=?,ipk_sem7=?,ipk_sem8=?,ipk_sem9=?,ipk_sem10=?,
           ipk_pen1=?,ipk_pen2=?,ipk_pen3=?,
           status=?,catatan=?,catatan_budget=?,catatan_payment=?,prodi=?,angkatan_kuliah=?,updated_at=?
           WHERE company_id=? AND code=?""",
        (data.get("nama",""), data.get("jenjang",""), data.get("angkatan") or None,
         data.get("program",""), data.get("fakultas",""), data.get("universitas",""),
         data.get("bank",""), data.get("norek",""), data.get("namarek",""),
         data.get("referensi",""),
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
    conn.execute("DELETE FROM budget_beasiswa WHERE company_id=? AND siswa_code=?", (company_id, code))
    conn.execute("DELETE FROM payment_beasiswa WHERE company_id=? AND siswa_code=?", (company_id, code))
    conn.execute("DELETE FROM siswa WHERE company_id=? AND code=?", (company_id, code))
    conn.commit()
    conn.close()
    detail = f" (termasuk {bgt} budget, {pay} payment)" if bgt or pay else ""
    return {"ok": True, "pesan": f"Siswa '{code}' berhasil dihapus{detail}."}


def delete_budget_row(company_id: int, row_id: int) -> dict:
    conn = get_conn()
    row  = conn.execute("SELECT id FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Baris budget tidak ditemukan."}
    conn.execute("DELETE FROM budget_beasiswa WHERE id=? AND company_id=?", (row_id, company_id))
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Baris budget dihapus."}


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
        "UPDATE budget_beasiswa SET cat1=?,cat2=?,tanggal=?,pillar=?,amount=? WHERE id=? AND company_id=?",
        (data.get("cat1",""), data.get("cat2",""), data.get("tanggal",""),
         data.get("pillar",""), amount, row_id, company_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Baris budget diupdate."}


def add_budget_batch(company_id: int, siswa_code: str, tanggal: str,
                     pillar: str, items: list) -> dict:
    conn  = get_conn()
    saved = 0
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        conn.execute(
            "INSERT INTO budget_beasiswa (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar) "
            "VALUES (?,?,?,?,?,?,?)",
            (company_id, siswa_code, item.get("cat1",""), item.get("cat2",""),
             tanggal, amount, pillar)
        )
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0.", "saved": 0}

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} baris budget berhasil disimpan.", "saved": saved}


def get_budget(company_id: int, siswa_code: str) -> dict:
    conn  = get_conn()
    rows  = [dict(r) for r in conn.execute(
        "SELECT * FROM budget_beasiswa WHERE company_id=? AND siswa_code=? ORDER BY tanggal",
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
    for item in items:
        try:
            amount = float(str(item.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,cat3,cat4,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
            (company_id, siswa_code,
             item.get("cat1",""), item.get("cat2",""),
             tanggal, amount, pillar, perusahaan,
             item.get("cat3",""), item.get("cat4",""))
        )
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0.", "saved": 0}

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"{saved} payment berhasil disimpan (status: open).", "saved": saved}


def insert_payment_rows(conn, company_id: int, company_code: str,
                        tanggal: str, pillar: str, perusahaan: str,
                        rows: list, route: str = "gl") -> dict:
    """Insert payment_beasiswa rows and update linked PA status → on_process.

    Caller owns conn (no commit, no close here). Does NOT create pam_record.
    Returns {"ok": bool, "payment_ids": list, "total": float, "pa_line_ids": list}.
    """
    # Pre-flight: validate all medical rows before any INSERT
    for row in rows:
        try:
            amount = float(str(row.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue
        if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
            rm = row.get("rekam_medis") or {}
            if not rm.get("kelas") or not rm.get("rumah_sakit") or \
               not rm.get("diagnosa") or not rm.get("spesialisasi"):
                return {"ok": False,
                        "pesan": "Data rekam medis wajib diisi (kelas, rumah sakit, diagnosa, spesialisasi).",
                        "payment_ids": [], "total": 0.0, "pa_line_ids": []}

    saved = 0
    payment_ids: list = []
    total = 0.0

    for row in rows:
        try:
            amount = float(str(row.get("amount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            continue

        siswa_code     = (row.get("siswa_code") or "").strip()
        etf_pa_line_id = row.get("etf_pa_line_id") or None
        cur = conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,
                tgl_pengajuan,tgl_receive,tgl_pa,tgl_final,cat3,cat4,etf_pa_line_id,
                advance_amount,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open')""",
            (company_id, siswa_code,
             row.get("cat1", ""), row.get("cat2", ""),
             tanggal, amount, pillar, perusahaan,
             row.get("tgl_pengajuan", ""), row.get("tgl_receive", ""),
             row.get("tgl_pa", ""),        row.get("tgl_final", ""),
             row.get("cat3", ""),          row.get("cat4", ""),
             etf_pa_line_id,
             amount if route == "advance" else None)
        )
        payment_ids.append(cur.lastrowid)
        total += amount
        saved += 1

        if row.get("cat1") == "By Medical" and row.get("cat2") in _CAT2_MEDICAL:
            rm = row.get("rekam_medis", {})
            conn.execute(
                """INSERT INTO rekam_medis
                   (company_id, payment_id, siswa_code, kelas, rumah_sakit,
                    diagnosa, spesialisasi, catatan)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (company_id, cur.lastrowid, siswa_code,
                 rm.get("kelas", ""),    rm.get("rumah_sakit", ""),
                 rm.get("diagnosa", ""), rm.get("spesialisasi", ""),
                 rm.get("catatan", "") or None)
            )

    if saved == 0:
        return {"ok": False, "pesan": "Tidak ada item dengan amount > 0.",
                "payment_ids": [], "total": 0.0, "pa_line_ids": []}

    pa_line_ids = [
        row.get("etf_pa_line_id")
        for row in rows
        if row.get("etf_pa_line_id") and
           float(str(row.get("amount", 0)).replace(",", "") or 0) > 0
    ]
    if pa_line_ids:
        pair = _PILLAR_PA_TBL.get((pillar or "").upper())
        if pair:
            lines_tbl, pa_tbl = pair
            ph = ",".join("?" * len(pa_line_ids))
            ts_op = _ts()
            conn.execute(
                f"""UPDATE {pa_tbl} SET status = 'on_process', updated_at = ?
                    WHERE id IN (
                        SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                    ) AND company_id = ? AND status = 'open'""",
                [ts_op] + pa_line_ids + [company_id]
            )

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
        ins = insert_payment_rows(conn, company_id, company_code,
                                  tanggal, pillar, perusahaan, rows)
        if not ins["ok"]:
            return ins

        payment_ids  = ins["payment_ids"]
        total        = ins["total"]
        pa_line_ids  = ins["pa_line_ids"]
        saved        = len(payment_ids)

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

        pam_no = create_pam_record(conn, company_id, company_code, {
            "pam_date":     tanggal,
            "pt":           perusahaan,
            "pillar":       pillar,
            "keterangan":   keterangan,
            "total_amount": total,
            "dpp":          total,
            "source":       "beasiswa",
            "payment_ids":  payment_ids,
        })

        if pa_line_ids and pam_no:
            ph = ",".join("?" * len(pa_line_ids))
            ts_pam = _ts()
            for lines_tbl, pa_tbl in [
                ("etf_pa_lines", "etf_pa"),
                ("app_pa_lines", "app_pa"),
                ("sml_pa_lines", "sml_pa"),
            ]:
                conn.execute(
                    f"""UPDATE {pa_tbl} SET nomor_pam = ?, updated_at = ?
                        WHERE id IN (
                            SELECT DISTINCT pa_id FROM {lines_tbl} WHERE id IN ({ph})
                        ) AND company_id = ?""",
                    [pam_no, ts_pam] + pa_line_ids + [company_id]
                )

        conn.commit()
        return {
            "ok":    True,
            "pesan": f"{saved} payment berhasil disimpan (status: open).",
            "saved": saved,
            "pam_no": pam_no,
        }

    except Exception as exc:
        conn.rollback()
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
        sql += (" AND (bb.siswa_code LIKE ? OR s.nama LIKE ? OR bb.cat1 LIKE ?"
                " OR bb.cat2 LIKE ? OR bb.pillar LIKE ? OR s.program LIKE ?)")
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
        sql += " AND strftime('%m', bb.tanggal) = ?"
        params += [bulan.zfill(2)]
    if tahun:
        sql += " AND strftime('%Y', bb.tanggal) = ?"
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
        pay_sql += (" AND (pb.siswa_code LIKE ? OR s.nama LIKE ? OR pb.cat1 LIKE ?"
                    " OR pb.cat2 LIKE ? OR pb.pam LIKE ? OR pb.pillar LIKE ?"
                    " OR pb.perusahaan LIKE ? OR s.program LIKE ?)")
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
        pay_sql += " AND strftime('%m', pb.tanggal) = ?"
        pay_params += [bulan.zfill(2)]
    if tahun:
        pay_sql += " AND strftime('%Y', pb.tanggal) = ?"
        pay_params += [tahun]
    pay_sql += " GROUP BY pb.cat1"
    payment_totals = {r[0]: r[1] for r in conn.execute(pay_sql, pay_params).fetchall()}
    payment_grand  = sum(payment_totals.values())
    sql   += " ORDER BY bb.tanggal DESC"
    total  = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
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
        sql    += (" AND (pb.siswa_code LIKE ? OR s.nama LIKE ? OR pb.cat1 LIKE ?"
                   " OR pb.cat2 LIKE ? OR pb.pam LIKE ? OR pb.pillar LIKE ?"
                   " OR pb.perusahaan LIKE ? OR s.program LIKE ?)")
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
        sql    += " AND strftime('%m', pb.tanggal) = ?"
        params += [bulan.zfill(2)]
    if tahun:
        sql    += " AND strftime('%Y', pb.tanggal) = ?"
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
        bgt_sql += (" AND (bb.siswa_code LIKE ? OR s.nama LIKE ? OR bb.cat1 LIKE ?"
                    " OR bb.cat2 LIKE ? OR bb.pillar LIKE ? OR s.program LIKE ?)")
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
        bgt_sql += " AND strftime('%m', bb.tanggal) = ?"
        bgt_params += [bulan.zfill(2)]
    if tahun:
        bgt_sql += " AND strftime('%Y', bb.tanggal) = ?"
        bgt_params += [tahun]
    bgt_sql += " GROUP BY bb.cat1"
    budget_totals = {r[0]: r[1] for r in conn.execute(bgt_sql, bgt_params).fetchall()}
    budget_grand  = sum(budget_totals.values())
    sql   += " ORDER BY pb.tanggal DESC"
    total  = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
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

    pam_no = row["pam"]
    line_id = row["etf_pa_line_id"]

    conn.execute("DELETE FROM rekam_medis WHERE payment_id=? AND company_id=?", (row_id, company_id))
    conn.execute("DELETE FROM payment_beasiswa WHERE id=? AND company_id=?", (row_id, company_id))

    # Hapus pam_records jika tidak ada payment lain yang memakai PAM ini
    if pam_no:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM payment_beasiswa WHERE pam=? AND company_id=?",
            (pam_no, company_id)
        ).fetchone()[0]
        if remaining == 0:
            conn.execute(
                "DELETE FROM pam_records WHERE pam_no=? AND company_id=?",
                (pam_no, company_id)
            )

    # Revert semua PA tables ke open jika tidak ada payment aktif lagi untuk PA ini
    if line_id:
        from datetime import datetime as _dt
        _now = _dt.now().isoformat(timespec="seconds")
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines", "etf_pa"),
            ("app_pa_lines", "app_pa"),
            ("sml_pa_lines", "sml_pa"),
        ]:
            pa_row = conn.execute(
                f"SELECT pa_id FROM {lines_tbl} WHERE id=?", (line_id,)
            ).fetchone()
            if pa_row:
                pa_id = pa_row[0]
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=?""",
                    (pa_id, company_id)
                ).fetchone()[0]
                if remaining_pa == 0:
                    conn.execute(
                        f"UPDATE {pa_tbl} SET status='open', nomor_pam=NULL, updated_at=? "
                        f"WHERE id=? AND company_id=?",
                        (_now, pa_id, company_id)
                    )

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
    if row["status"] == "complete":
        conn.close()
        return {"ok": False, "pesan": "Payment yang sudah selesai tidak bisa dihapus."}

    pam_no = row["pam"]
    line_id = row["etf_pa_line_id"]

    # Cascade delete rekam_medis
    conn.execute(
        "DELETE FROM rekam_medis WHERE payment_id=? AND company_id=?",
        (payment_id, company_id)
    )

    conn.execute("DELETE FROM payment_beasiswa WHERE id=? AND company_id=?", (payment_id, company_id))

    # Hapus pam_records jika tidak ada payment lain yang memakai PAM ini
    if pam_no:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM payment_beasiswa WHERE pam=? AND company_id=?",
            (pam_no, company_id)
        ).fetchone()[0]
        if remaining == 0:
            conn.execute(
                "DELETE FROM pam_records WHERE pam_no=? AND company_id=?",
                (pam_no, company_id)
            )

    # Revert semua PA tables ke open jika tidak ada payment aktif lagi untuk PA ini
    if line_id:
        from datetime import datetime as _dt
        _now = _dt.now().isoformat(timespec="seconds")
        for lines_tbl, pa_tbl in [
            ("etf_pa_lines", "etf_pa"),
            ("app_pa_lines", "app_pa"),
            ("sml_pa_lines", "sml_pa"),
        ]:
            pa_row = conn.execute(
                f"SELECT pa_id FROM {lines_tbl} WHERE id=?", (line_id,)
            ).fetchone()
            if pa_row:
                pa_id = pa_row[0]
                remaining_pa = conn.execute(
                    f"""SELECT COUNT(*) FROM payment_beasiswa pb
                           JOIN {lines_tbl} el ON el.id = pb.etf_pa_line_id
                           WHERE el.pa_id=? AND pb.company_id=?""",
                    (pa_id, company_id)
                ).fetchone()[0]
                if remaining_pa == 0:
                    conn.execute(
                        f"UPDATE {pa_tbl} SET status='open', nomor_pam=NULL, updated_at=? "
                        f"WHERE id=? AND company_id=?",
                        (_now, pa_id, company_id)
                    )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": "Baris payment dihapus."}


def get_payment(company_id: int, siswa_code: str = "", status: str = "") -> list:
    sql    = ("SELECT pb.*, s.nama FROM payment_beasiswa pb "
              "LEFT JOIN siswa s ON s.company_id=pb.company_id AND s.code=pb.siswa_code "
              "WHERE pb.company_id=?")
    params = [company_id]
    if siswa_code:
        sql    += " AND pb.siswa_code=?"
        params += [siswa_code]
    if status:
        sql    += " AND pb.status=?"
        params += [status]
    sql += " ORDER BY pb.tanggal DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_sisa_budget(company_id: int, siswa_code: str) -> dict:
    conn = get_conn()
    bgt  = {}
    for r in conn.execute(
        "SELECT cat1, SUM(amount) as total FROM budget_beasiswa "
        "WHERE company_id=? AND siswa_code=? GROUP BY cat1",
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

        cur = conn.execute(
            """INSERT INTO payment_beasiswa
               (company_id,siswa_code,cat1,cat2,tanggal,amount,pillar,perusahaan,pam,status)
               VALUES (?,?,?,?,?,?,?,?,?,'open')""",
            (company_id, siswa_code, "By Medical", perawatan,
             tanggal, amount, pillar, perusahaan, pam)
        )
        payment_id = cur.lastrowid

        conn.execute(
            """INSERT INTO klaim_medical
               (company_id,siswa_code,pam,tanggal,amount,perawatan,kelas,
                rumah_sakit,diagnosa,spesialisasi,pillar,perusahaan,payment_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, siswa_code, pam, tanggal, amount, perawatan, kelas,
             rumah_sakit, diagnosa, spesialisasi, pillar, perusahaan, payment_id)
        )
        saved += 1

    if saved == 0:
        conn.close()
        return {"ok": False, "pesan": "Tidak ada klaim valid untuk disimpan.", "saved": 0}

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
        sql += (" AND (k.siswa_code LIKE ? OR s.nama LIKE ? OR k.pam LIKE ?"
                " OR k.rumah_sakit LIKE ? OR k.diagnosa LIKE ?)")
        params += [q, q, q, q, q]
    if perawatan:
        sql += " AND k.perawatan=?"
        params += [perawatan]
    if bulan:
        sql += " AND strftime('%m', k.tanggal)=?"
        params += [bulan.zfill(2)]
    if tahun:
        sql += " AND strftime('%Y', k.tanggal)=?"
        params += [tahun]
    agg_sql = sql.replace(
        "SELECT k.*, s.nama FROM",
        "SELECT k.amount FROM"
    )
    conn  = get_conn()
    total = conn.execute(f"SELECT COUNT(*) FROM ({agg_sql})", params).fetchone()[0]
    grand = conn.execute(
        f"SELECT COALESCE(SUM(amount),0) FROM ({agg_sql})", params
    ).fetchone()[0]
    sql  += " ORDER BY k.tanggal DESC"
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
        if pay and pay["status"] == "complete":
            conn.close()
            return {"ok": False, "pesan": "Klaim yang sudah selesai tidak bisa dihapus."}
        conn.execute("DELETE FROM payment_beasiswa WHERE id=? AND company_id=?",
                     (row["payment_id"], company_id))
    conn.execute("DELETE FROM klaim_medical WHERE id=? AND company_id=?",
                 (row_id, company_id))
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
        sql    += " AND (nama LIKE ? OR code LIKE ?)"
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

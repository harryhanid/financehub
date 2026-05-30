# modules/beasiswa/service.py
from datetime import datetime
from database import get_conn
import config


def _ts():
    return datetime.now().isoformat(timespec="seconds")


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
            status, catatan, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, code, nama,
         data.get("jenjang", ""), data.get("angkatan") or None,
         data.get("program", ""), data.get("fakultas", ""), data.get("universitas", ""),
         data.get("bank", ""), data.get("norek", ""), data.get("namarek", ""),
         data.get("referensi", ""),
         *ipk_sem, *ipk_pen,
         data.get("status", "Aktif"), data.get("catatan", ""), _ts())
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
           status=?,catatan=?,updated_at=?
           WHERE company_id=? AND code=?""",
        (data.get("nama",""), data.get("jenjang",""), data.get("angkatan") or None,
         data.get("program",""), data.get("fakultas",""), data.get("universitas",""),
         data.get("bank",""), data.get("norek",""), data.get("namarek",""),
         data.get("referensi",""),
         *ipk_sem, *ipk_pen,
         data.get("status","Aktif"), data.get("catatan",""), _ts(),
         company_id, code)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Data siswa '{code}' berhasil diupdate."}


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
               VALUES (?,?,?,?,?,?,?,?,?,?,'draft')""",
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
    return {"ok": True, "pesan": f"{saved} payment berhasil disimpan (status: draft).", "saved": saved}


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


def get_rekap(company_id: int, program: str = "", pillar: str = "", status: str = "") -> list:
    sql    = "SELECT * FROM siswa WHERE company_id=?"
    params = [company_id]
    if program:
        sql    += " AND program=?"
        params += [program]
    if status:
        sql    += " AND status=?"
        params += [status]
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

import config
from database import get_conn

PROGRAM_NAME = "Sahabat ETF"


def _year_filter_sql(years, column):
    if not years:
        return "", []
    placeholders = ",".join("?" for _ in years)
    return f" AND fh_strftime('%Y', {column}) IN ({placeholders})", [str(y) for y in years]


def _pillar_filter_sql(pillars, column):
    if not pillars:
        return "", []
    placeholders = ",".join("?" for _ in pillars)
    return f" AND {column} IN ({placeholders})", list(pillars)


KESEHATAN_CAT1 = "By Medical"


def _empty_metrics() -> dict:
    return {"plafon": 0.0, "pta": 0.0, "klaim": 0.0, "dibayar": 0.0, "saldo": 0.0}


def _add_metrics(target: dict, plafon: float = 0.0, pta: float = 0.0, klaim: float = 0.0, dibayar: float = 0.0):
    target["plafon"]  += plafon
    target["pta"]     += pta
    target["klaim"]   += klaim
    target["dibayar"] += dibayar
    target["saldo"]    = target["plafon"] + target["pta"] - target["dibayar"]


def _sum_metrics(*metric_dicts) -> dict:
    total = _empty_metrics()
    for m in metric_dicts:
        _add_metrics(total, plafon=m["plafon"], pta=m.get("pta", 0.0), klaim=m["klaim"], dibayar=m["dibayar"])
    return total


def _fetch_report_rows(company_id: int, pillars: list = None):
    """Raw budget + payment rows (all years) for Sahabat ETF siswa, tagged with
    section/subgroup keys. Returns (budget_rows, payment_rows) as lists of dict."""
    conn = get_conn()
    budget_rows = conn.execute(
        """
        SELECT s.nama AS nama, s.jenjang AS jenjang, s.angkatan AS angkatan, s.group_setf AS group_setf,
               b.cat1 AS cat1, b.cat2 AS cat2,
               b.pillar AS pillar, CAST(fh_strftime('%Y', b.tanggal) AS INTEGER) AS tahun,
               CAST(fh_strftime('%m', b.tanggal) AS INTEGER) AS bulan,
               b.amount AS amount
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    payment_rows = conn.execute(
        """
        SELECT s.nama AS nama, s.jenjang AS jenjang, s.angkatan AS angkatan, s.group_setf AS group_setf,
               p.cat1 AS cat1, p.cat2 AS cat2,
               p.pillar AS pillar, p.status AS status,
               COALESCE(
                 CASE p.pillar 
                 WHEN 'APP' THEN p."tgl_Paid_APP" 
                 WHEN 'LAND' THEN p."tgl_Paid_LAND" 
                 WHEN 'ENERGY' THEN p."tgl_Paid_ENERGY" 
                 WHEN 'SETF' THEN p."tgl_Paid_SETF" 
                 END, pr.tanggal_bayar) AS tanggal_bayar, p.tanggal AS tanggal,
               CAST(fh_strftime('%Y', p.tanggal) AS INTEGER) AS tahun,
               CAST(fh_strftime('%m', p.tanggal) AS INTEGER) AS bulan, p.amount AS amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        LEFT JOIN pam_records pr ON pr.pam_no = p.pam AND pr.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal IS NOT NULL AND p.tanggal != ''
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return [dict(r) for r in budget_rows], [dict(r) for r in payment_rows]


def _row_section(cat1: str) -> str:
    return "KESEHATAN" if cat1 == KESEHATAN_CAT1 else "PENDIDIKAN"


def _row_subgroup(section: str, row: dict) -> str:
    if section == "KESEHATAN":
        return row["cat2"] or "(Tanpa Kategori)"
    return row["jenjang"] or "(Tanpa Jenjang)"


_JENJANG_DURASI = {"SD": 6, "SMP": 3, "SMA": 3, "SMK": 3, "S1": 4, "S2": 2, "S3": 4}
_KESEHATAN_DURASI = 1


def _compute_periode(section_key: str, jenjang: str, angkatan) -> tuple:
    if not angkatan:
        return None, None
    if section_key == "KESEHATAN":
        return angkatan, angkatan + _KESEHATAN_DURASI
    durasi = _JENJANG_DURASI.get(jenjang)
    return (angkatan, angkatan + durasi) if durasi else (None, None)


def _build_buckets(company_id: int, report_year: int, report_month: int = 12, pillars: list = None) -> dict:
    import calendar
    from datetime import date
    last_day = calendar.monthrange(report_year, report_month)[1]
    cutoff_date = date(report_year, report_month, last_day).strftime("%Y-%m-%d")

    """bucket[(section, subgroup, nama)] -> {"cur": metrics, "cum": metrics, "pillars": set}"""
    budget_rows, payment_rows = _fetch_report_rows(company_id)
    buckets = {}

    def bucket(section, subgroup, nama, group_setf):
        key = (section, subgroup, nama)
        if key not in buckets:
            buckets[key] = {"cur": _empty_metrics(), "cum": _empty_metrics(), "pillars": set(), "angkatan": None, "group_setf": group_setf}
        return buckets[key]

    for r in budget_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        tahun    = r["tahun"]
        bulan    = r["bulan"]
        amount   = float(r["amount"] or 0)
        is_pta   = (r["cat2"] == "Tambahan Anggaran")
        plafon_amt = 0.0 if is_pta else amount
        pta_amt    = amount if is_pta else 0.0
        
        b = bucket(section, subgroup, r["nama"], r["group_setf"])
        b["pillars"].add(r["pillar"] or "")
        b["angkatan"] = r["angkatan"]
        if tahun == report_year and bulan <= report_month:
            _add_metrics(b["cur"], plafon=plafon_amt, pta=pta_amt)
        if tahun < report_year or (tahun == report_year and bulan <= report_month):
            _add_metrics(b["cum"], plafon=plafon_amt, pta=pta_amt)

    for r in payment_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        tahun    = r["tahun"]
        bulan    = r["bulan"]
        amount   = float(r["amount"] or 0)

        comp_date = r["tanggal_bayar"] if r["tanggal_bayar"] else r["tanggal"]
        is_complete = (r["status"] == "complete" and comp_date and comp_date <= cutoff_date)
        dibayar  = amount if is_complete else 0.0

        b = bucket(section, subgroup, r["nama"], r["group_setf"])
        b["pillars"].add(r["pillar"] or "")
        b["angkatan"] = r["angkatan"]
        if tahun == report_year and bulan <= report_month:
            _add_metrics(b["cur"], klaim=amount, dibayar=dibayar)
        if tahun is not None and (tahun < report_year or (tahun == report_year and bulan <= report_month)):
            _add_metrics(b["cum"], klaim=amount, dibayar=dibayar)

    return buckets


def _pillar_label(bucket_pillars: set) -> str:
    return ", ".join(sorted(p for p in bucket_pillars if p))


def _build_section(section_key: str, buckets: dict) -> dict:
    subgroup_order = (config.JENJANG if section_key == "PENDIDIKAN" else None)
    subgroup_keys = {key[1] for key in buckets if key[0] == section_key}
    if subgroup_order:
        ordered_subgroups = [g for g in subgroup_order if g in subgroup_keys]
        ordered_subgroups += sorted(subgroup_keys - set(subgroup_order))
    else:
        ordered_subgroups = sorted(subgroup_keys)

    groups = []
    for subgroup in ordered_subgroups:
        namas = sorted(nama for (sec, sg, nama) in buckets if sec == section_key and sg == subgroup)
        siswa_rows = []
        for nama in namas:
            b = buckets[(section_key, subgroup, nama)]
            periode_start, periode_end = _compute_periode(section_key, subgroup, b["angkatan"])
            siswa_rows.append({
                "nama": nama, "pillar": _pillar_label(b["pillars"]),
                "cur": b["cur"], "cum": b["cum"],
                "periode_start": periode_start, "periode_end": periode_end,
            })
        subtotal = {
            "cur": _sum_metrics(*[r["cur"] for r in siswa_rows]),
            "cum": _sum_metrics(*[r["cum"] for r in siswa_rows]),
        }
        groups.append({"key": subgroup, "label": subgroup, "subtotal": subtotal, "siswa_rows": siswa_rows})

    total = {
        "cur": _sum_metrics(*[g["subtotal"]["cur"] for g in groups]),
        "cum": _sum_metrics(*[g["subtotal"]["cum"] for g in groups]),
    }
    return {"key": section_key, "label": section_key, "groups": groups, "total": total}


def _build_recap(section_key: str, buckets: dict) -> list:
    namas = sorted({nama for (sec, sg, nama) in buckets if sec == section_key})
    recap = []
    for nama in namas:
        bucket_list = [b for (sec, sg, n), b in buckets.items() if sec == section_key and n == nama]
        pillars = set()
        for b in bucket_list:
            pillars |= b["pillars"]
        recap.append({
            "nama": nama, "pillar": _pillar_label(pillars),
            "cur": _sum_metrics(*[b["cur"] for b in bucket_list]),
            "cum": _sum_metrics(*[b["cum"] for b in bucket_list]),
        })
    return recap


def _build_diagram_buckets(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:
    budget_rows, payment_rows = _fetch_report_rows(company_id)
    buckets = {}

    def bucket(section, subgroup, nama, group_setf):
        key = (section, subgroup, nama)
        if key not in buckets:
            buckets[key] = {"val": {"plafon": 0.0, "pta": 0.0, "dibayar": 0.0}, "pillars": set(), "group_setf": group_setf}
        return buckets[key]

    for r in budget_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        if years and r["tahun"] not in years:
            continue
        if r["bulan"] and r["bulan"] > month:
            continue
            
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        amount   = float(r["amount"] or 0)
        is_pta   = (r["cat2"] == "Tambahan Anggaran")
        plafon_amt = 0.0 if is_pta else amount
        pta_amt    = amount if is_pta else 0.0
        
        b = bucket(section, subgroup, r["nama"], r["group_setf"])
        b["pillars"].add(r["pillar"] or "")
        b["val"]["plafon"] += plafon_amt
        b["val"]["pta"] += pta_amt

    for r in payment_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        if years and r["tahun"] not in years:
            continue
        if r["bulan"] and r["bulan"] > month:
            continue
            
        section  = _row_section(r["cat1"])
        subgroup = _row_subgroup(section, r)
        amount   = float(r["amount"] or 0)

        is_complete = (r["status"] == "complete")
        dibayar  = amount if is_complete else 0.0

        b = bucket(section, subgroup, r["nama"], r["group_setf"])
        b["pillars"].add(r["pillar"] or "")
        b["val"]["dibayar"] += dibayar

    return buckets

def build_pohon_data(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:
    """Membangun struktur pohon (Root -> [Kesehatan, Pendidikan] -> [Siswa]) untuk UI Pohon Sahabat.
    Hanya mengambil nilai Kumulatif (Cum) hingga report_year, dan Plafon + PTA untuk kolom Plafon."""
    buckets = _build_diagram_buckets(company_id, years, month, pillars)

    # Filter by pillars if provided
    filtered_buckets = {}
    for key, b in buckets.items():
        if pillars and not any(p in pillars for p in b["pillars"]):
            continue
        filtered_buckets[key] = b

    # Aggregate
    kesehatan_dict = {}
    pendidikan_dict = {}
    
    kesehatan_total = _empty_metrics()
    pendidikan_total = _empty_metrics()
    root_total = _empty_metrics()

    for (section, subgroup, nama), b in filtered_buckets.items():
        cum = b["val"]
        # Changed to cum["plafon"] to match the exact "Plafon" column in Laporan (5405) instead of Plafon+PTA
        plafon_total = cum["plafon"] + cum["pta"]
        realisasi = cum["dibayar"]
        
        _add_metrics(root_total, plafon=cum["plafon"], pta=cum["pta"], dibayar=cum["dibayar"])
        
        if section == "KESEHATAN":
            if nama not in kesehatan_dict:
                kesehatan_dict[nama] = {"nama": nama, "plafon": 0, "realisasi": 0}
            kesehatan_dict[nama]["plafon"] += plafon_total
            kesehatan_dict[nama]["realisasi"] += realisasi
            _add_metrics(kesehatan_total, plafon=cum["plafon"], pta=cum["pta"], dibayar=cum["dibayar"])
        else:
            if nama not in pendidikan_dict:
                pendidikan_dict[nama] = {"nama": nama, "plafon": 0, "realisasi": 0}
            pendidikan_dict[nama]["plafon"] += plafon_total
            pendidikan_dict[nama]["realisasi"] += realisasi
            _add_metrics(pendidikan_total, plafon=cum["plafon"], pta=cum["pta"], dibayar=cum["dibayar"])

    kesehatan_siswa = list(kesehatan_dict.values())
    pendidikan_siswa = list(pendidikan_dict.values())

    k_count = len(kesehatan_siswa)
    p_count = len(pendidikan_siswa)
    total_count = k_count + p_count

    # Sort siswa by nama
    kesehatan_siswa.sort(key=lambda x: x["nama"].lower())
    pendidikan_siswa.sort(key=lambda x: x["nama"].lower())

    if not pillars:
        label_root = "Semua Pillar"
    elif len(pillars) == 1:
        label_root = pillars[0]
    else:
        label_root = "Gabungan"

    label_root = f"{label_root} : {total_count} Orang ( Kesehatan : {k_count} Orang, Pendidikan : {p_count} Orang )"

    return {
        "root": {
            "label": label_root,
            "plafon": root_total["plafon"],
            "realisasi": root_total["dibayar"]
        },
        "kesehatan": {
            "label": f"Kesehatan ( {k_count} Orang )",
            "plafon": kesehatan_total["plafon"],
            "realisasi": kesehatan_total["dibayar"],
            "siswa": kesehatan_siswa
        },
        "pendidikan": {
            "label": f"Pendidikan ( {p_count} Orang )",
            "plafon": pendidikan_total["plafon"],
            "realisasi": pendidikan_total["dibayar"],
            "siswa": pendidikan_siswa
        }
    }


_PILLAR_LABELS = {"SETF": "SAHABAT ETF"}


def _pillar_display_label(pillar_code: str) -> str:
    return _PILLAR_LABELS.get(pillar_code, pillar_code)


def _safe_pct(value: float, total: float) -> float:
    return (value / total) if total else 0.0


def _build_pillar_breakdown(company_id: int, report_year: int, report_month: int, pillars: list, grand_total: dict) -> list:
    budget_rows, payment_rows = _fetch_report_rows(company_id)
    by_pillar = {}

    def bucket(pillar_code):
        if pillar_code not in by_pillar:
            by_pillar[pillar_code] = {"cur": _empty_metrics(), "cum": _empty_metrics()}
        return by_pillar[pillar_code]

    for r in budget_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        pillar_code = r["pillar"] or "(Tanpa Pillar)"
        tahun, amount = r["tahun"], float(r["amount"] or 0)
        bulan = r["bulan"]
        is_pta = (r["cat2"] == "Tambahan Anggaran")
        plafon_amt = 0.0 if is_pta else amount
        pta_amt    = amount if is_pta else 0.0
        b = bucket(pillar_code)
        if tahun == report_year and bulan <= report_month:
            _add_metrics(b["cur"], plafon=plafon_amt, pta=pta_amt)
        if tahun < report_year or (tahun == report_year and bulan <= report_month):
            _add_metrics(b["cum"], plafon=plafon_amt, pta=pta_amt)

    for r in payment_rows:
        if pillars and r["pillar"] and r["pillar"] not in pillars:
            continue
        pillar_code = r["pillar"] or "(Tanpa Pillar)"
        tahun, amount = r["tahun"], float(r["amount"] or 0)
        bulan = r["bulan"]
        dibayar = amount if r["status"] == "complete" else 0.0
        b = bucket(pillar_code)
        if tahun == report_year and bulan <= report_month:
            _add_metrics(b["cur"], klaim=amount, dibayar=dibayar)
        if tahun is not None and (tahun < report_year or (tahun == report_year and bulan <= report_month)):
            _add_metrics(b["cum"], klaim=amount, dibayar=dibayar)

    result = []
    for pillar_code, metrics in by_pillar.items():
        pct_cur = {k: _safe_pct(metrics["cur"][k], grand_total["cur"][k]) for k in metrics["cur"]}
        pct_cum = {k: _safe_pct(metrics["cum"][k], grand_total["cum"][k]) for k in metrics["cum"]}
        result.append({
            "pillar_label": _pillar_display_label(pillar_code),
            "cur": metrics["cur"], "cum": metrics["cum"],
            "pct_cur": pct_cur, "pct_cum": pct_cum,
        })
    result.sort(key=lambda p: p["cum"]["plafon"], reverse=True)
    return result


def build_report_data(company_id: int, report_year: int, report_month: int = 12, pillars: list = None) -> dict:
    buckets = _build_buckets(company_id, report_year, report_month, pillars)
    sections = []
    for section_key in ("PENDIDIKAN", "KESEHATAN"):
        section = _build_section(section_key, buckets)
        section["recap"] = _build_recap(section_key, buckets)
        sections.append(section)

    combined_total = {
        "cur": _sum_metrics(*[s["total"]["cur"] for s in sections]),
        "cum": _sum_metrics(*[s["total"]["cum"] for s in sections]),
    }

    combined_namas = sorted({nama for (sec, sg, nama) in buckets})
    combined_recap = []
    for nama in combined_namas:
        bucket_list = [b for (sec, sg, n), b in buckets.items() if n == nama]
        b_pillars = set()
        for b in bucket_list:
            b_pillars |= b["pillars"]
        combined_recap.append({
            "nama": nama, "pillar": _pillar_label(b_pillars),
            "cur": _sum_metrics(*[b["cur"] for b in bucket_list]),
            "cum": _sum_metrics(*[b["cum"] for b in bucket_list]),
        })

    return {
        "report_year": report_year,
        "report_month": report_month,
        "sections": sections,
        "combined_total": combined_total,
        "combined_recap": combined_recap,
        "grand_total": combined_total,
        "pillar_breakdown": _build_pillar_breakdown(company_id, report_year, report_month, pillars, combined_total),
    }


def get_siswa_summary(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
    budget_pillar_sql, budget_pillar_params = _pillar_filter_sql(pillars, "pillar")

    rows = conn.execute(
        f"""
        SELECT s.code, s.nama, s.jenjang, s.angkatan, s.status,
               COALESCE(b.budget_total, 0)    AS budget_total,
               COALESCE(p.payment_total, 0)   AS payment_total,
               COALESCE(p.realisasi_total, 0) AS realisasi_total
        FROM siswa s
        LEFT JOIN (
            SELECT siswa_code, SUM(amount) AS budget_total
            FROM budget_beasiswa
            WHERE company_id = ?{budget_year_sql}{budget_pillar_sql}
            GROUP BY siswa_code
        ) b ON b.siswa_code = s.code
        LEFT JOIN (
            SELECT siswa_code,
                   SUM(amount) AS payment_total,
                   SUM(CASE WHEN status = 'complete' THEN amount ELSE 0 END) AS realisasi_total
            FROM payment_beasiswa
            WHERE company_id = ?{payment_year_sql}{pillar_sql}
            GROUP BY siswa_code
        ) p ON p.siswa_code = s.code
        WHERE s.company_id = ? AND s.program = ?
        ORDER BY s.nama
        """,
        [company_id, *budget_year_params, *budget_pillar_params, company_id, *payment_year_params, *pillar_params,
         company_id, PROGRAM_NAME],
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
            "status":          r["status"],
            "budget_total":    budget,
            "payment_total":   float(r["payment_total"] or 0),
            "realisasi_total": realisasi,
            "sisa_budget":     budget - realisasi,
        })
    return result


FAMILY_GROUPS = [
    # (family_key, [siswa_code, ...])
    ("Sahabat A.3.1", ["1260001", "5250001"]),             # Budi Widjaja, Birgitta Jennifer Widjaja
    ("Sahabat A.3.2", ["5260003", "5250002"]),             # Burhanuddin Widjaja, Richard Widjaja
    ("Sahabat A.3.3", ["1240706", "2260001", "1230684"]),             # Jety Widjaja, Darrell Bright Lie
    ("Sahabat A.3.4", ["5260002", "1240700", "4220003"]),  # Effendi Widjaja, Cathabell (S1 + record lama SMA)
]


def _siswa_kategori_map(company_id: int, years: list = None, pillars: list = None) -> dict:
    """siswa_code -> set of cat1 dengan realisasi (payment status='complete')."""
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "pillar")
    rows = conn.execute(
        f"""
        SELECT DISTINCT siswa_code, cat1
        FROM payment_beasiswa
        WHERE company_id = ? AND status = 'complete'{payment_year_sql}{pillar_sql}
        """,
        [company_id, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    result = {}
    for r in rows:
        result.setdefault(r["siswa_code"], set()).add(r["cat1"] or "(Tanpa Kategori)")
    return result


def _sort_kategori(cats: set) -> list:
    order = config.CAT1_BGT

    def key(c):
        return (order.index(c), c) if c in order else (len(order), c)
    return sorted(cats, key=key)


def get_family_summary(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    budget_pillar_sql, budget_pillar_params = _pillar_filter_sql(pillars, "b.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT b.siswa_code, b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}{budget_pillar_sql}
        GROUP BY b.siswa_code, b.cat1
        """,
        [company_id, PROGRAM_NAME, *budget_year_params, *budget_pillar_params],
    ).fetchall()

    payment_rows = conn.execute(
        f"""
        SELECT p.siswa_code, p.cat1,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        GROUP BY p.siswa_code, p.cat1
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    siswa_rows = get_siswa_summary(company_id, years, pillars)
    by_code = {r["siswa_code"]: r for r in siswa_rows}
    kategori_map = _siswa_kategori_map(company_id, years, pillars)

    code_to_family = {code: fk for fk, codes in FAMILY_GROUPS for code in codes}
    groups_order = list(FAMILY_GROUPS)
    non_group_codes = []
    for r in siswa_rows:
        code = r["siswa_code"]
        if code not in code_to_family:
            non_group_codes.append(code)
    
    if non_group_codes:
        groups_order.append(("non_group", non_group_codes))

    families = []
    family_idx = {}
    idx = 0
    for family_key, codes in groups_order:
        existing_codes = [c for c in codes if c in by_code]
        if not existing_codes:
            continue
        members = []
        by_nama = {}
        for code in existing_codes:
            row = by_code[code]
            nama = row["nama"]
            cats = kategori_map.get(code, set())
            realisasi_val = float(row["realisasi_total"] or 0)
            budget_val = float(row["budget_total"] or 0)
            if nama in by_nama:
                by_nama[nama]["realisasi"] += realisasi_val
                by_nama[nama]["budget"] += budget_val
                by_nama[nama]["_kategori_set"] |= cats
            else:
                member = {"nama": nama, "realisasi": realisasi_val, "budget": budget_val, "_kategori_set": set(cats)}
                by_nama[nama] = member
                members.append(member)
        for m in members:
            m["kategori"] = ", ".join(_sort_kategori(m.pop("_kategori_set")))
        families.append({
            "family_key": family_key,
            "members": members,
            "total_realisasi": sum(m["realisasi"] for m in members),
            "total_budget": sum(m["budget"] for m in members),
        })
        family_idx[family_key] = idx
        idx += 1

    for f in families:
        if f["family_key"] == "non_group":
            f["label"] = "Sahabat B.3.5"
        elif f["family_key"].startswith("Sahabat"):
            f["label"] = f["family_key"]
        else:
            f["label"] = f["members"][0]["nama"]

    final_families = [
        {
            "family_key":      f["family_key"],
            "label":           f["label"],
            "total_realisasi": f["total_realisasi"],
            "total_budget": f.get("total_budget", 0),
            "members":         f["members"],
        }
        for f in families
    ]

    kategori_data = {}
    for r in budget_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        code = r["siswa_code"]
        fk = code_to_family.get(code, "non_group")
        if fk in family_idx:
            kategori_data.setdefault(cat1, {"budget": [0]*len(families), "realisasi": [0]*len(families)})
            kategori_data[cat1]["budget"][family_idx[fk]] += float(r["total"] or 0)

    for r in payment_rows:
        cat1 = r["cat1"] or "(Tanpa Kategori)"
        code = r["siswa_code"]
        fk = code_to_family.get(code, "non_group")
        if fk in family_idx:
            kategori_data.setdefault(cat1, {"budget": [0]*len(families), "realisasi": [0]*len(families)})
            kategori_data[cat1]["realisasi"][family_idx[fk]] += float(r["realisasi"] or 0)

    kategori_series = []
    for cat1 in _sort_kategori(kategori_data.keys()):
        kategori_series.append({
            "name": cat1,
            "budget": kategori_data[cat1]["budget"],
            "realisasi": kategori_data[cat1]["realisasi"]
        })

    return {
        "families": final_families,
        "kategori_series": kategori_series
    }

def get_kategori_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    budget_pillar_sql, budget_pillar_params = _pillar_filter_sql(pillars, "b.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}{budget_pillar_sql}
        GROUP BY b.cat1
        """,
        [company_id, PROGRAM_NAME, *budget_year_params, *budget_pillar_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.cat1,
               SUM(p.amount) AS total,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        GROUP BY p.cat1
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
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

    over_budget = [
        {
            "siswa_code":      s["siswa_code"],
            "nama":            s["nama"],
            "budget_total":    s["budget_total"],
            "realisasi_total": s["realisasi_total"],
            "selisih":         s["realisasi_total"] - s["budget_total"],
        }
        for s in get_siswa_summary(company_id, years, pillars)
        if s["realisasi_total"] > s["budget_total"]
    ]

    return {"kategori": list(kategori.values()), "over_budget": over_budget}


def get_siswa_detail(company_id: int, siswa_code: str) -> list:
    conn = get_conn()
    budget_rows = conn.execute(
        "SELECT tanggal, cat1, cat2, amount FROM budget_beasiswa "
        "WHERE company_id = ? AND siswa_code = ? ORDER BY tanggal NULLS FIRST",
        (company_id, siswa_code),
    ).fetchall()
    payment_rows = conn.execute(
        "SELECT tanggal, cat1, cat2, amount, status FROM payment_beasiswa "
        "WHERE company_id = ? AND siswa_code = ? ORDER BY tanggal NULLS FIRST",
        (company_id, siswa_code),
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "tanggal": r["tanggal"], "cat1": r["cat1"],
                     "cat2": r["cat2"], "amount": r["amount"], "status": ""})
    for r in payment_rows:
        rows.append({"sumber": "Payment", "tanggal": r["tanggal"], "cat1": r["cat1"],
                     "cat2": r["cat2"], "amount": r["amount"], "status": r["status"]})
    rows.sort(key=lambda r: r["tanggal"] or "")
    return rows


def get_report_detail_transactions(company_id: int, report_year: int, report_month: int = 12, pillars: list = None) -> list:
    import calendar
    from datetime import date
    last_day = calendar.monthrange(report_year, report_month)[1]
    cutoff_date = date(report_year, report_month, last_day).strftime("%Y-%m-%d")

    conn = get_conn()
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, b.tanggal, b.cat1, b.cat2, b.amount, b.pillar
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal <= ?
        ORDER BY s.nama, b.tanggal NULLS FIRST
        """,
        [company_id, PROGRAM_NAME, cutoff_date],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, p.tanggal, p.cat1, p.cat2, p.amount, p.status, p.pillar,
               COALESCE(
                 CASE p.pillar 
                 WHEN 'APP' THEN p."tgl_Paid_APP" 
                 WHEN 'LAND' THEN p."tgl_Paid_LAND" 
                 WHEN 'ENERGY' THEN p."tgl_Paid_ENERGY" 
                 WHEN 'SETF' THEN p."tgl_Paid_SETF" 
                 END, pr.tanggal_bayar) AS tanggal_bayar
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        LEFT JOIN pam_records pr ON pr.pam_no = p.pam AND pr.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal <= ?{pillar_sql}
        ORDER BY s.nama, p.tanggal NULLS FIRST
        """,
        [company_id, PROGRAM_NAME, cutoff_date, *pillar_params],
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "tgl_final": "", "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": "", "pillar": r["pillar"]})
    for r in payment_rows:
        comp_date = r["tanggal_bayar"] if r["tanggal_bayar"] else r["tanggal"]
        is_complete = (r["status"] == "complete" and comp_date and comp_date <= cutoff_date)
        point_in_time_status = "complete" if is_complete else ("open" if r["status"] == "complete" else r["status"])

        rows.append({"sumber": "Payment", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "tgl_final": r["tanggal_bayar"] or "", "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": point_in_time_status, "pillar": r["pillar"]})
    rows.sort(key=lambda r: r["tanggal"] or "")
    return rows


def get_all_transactions(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, b.tanggal, b.cat1, b.cat2, b.amount, b.pillar
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}
        ORDER BY s.nama, b.tanggal NULLS FIRST
        """,
        [company_id, PROGRAM_NAME, *budget_year_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT s.code AS siswa_code, s.nama, p.tanggal, p.cat1, p.cat2, p.amount, p.status, p.pillar,
               COALESCE(
                 CASE p.pillar 
                 WHEN 'APP' THEN p."tgl_Paid_APP" 
                 WHEN 'LAND' THEN p."tgl_Paid_LAND" 
                 WHEN 'ENERGY' THEN p."tgl_Paid_ENERGY" 
                 WHEN 'SETF' THEN p."tgl_Paid_SETF" 
                 END, pr.tanggal_bayar) AS tanggal_bayar
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        LEFT JOIN pam_records pr ON pr.pam_no = p.pam AND pr.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}
        ORDER BY s.nama, p.tanggal NULLS FIRST
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    rows = []
    for r in budget_rows:
        rows.append({"sumber": "Budget", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "tgl_final": "", "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": "", "pillar": r["pillar"]})
    for r in payment_rows:
        rows.append({"sumber": "Payment", "siswa_code": r["siswa_code"], "nama": r["nama"],
                     "tanggal": r["tanggal"], "tgl_final": r["tanggal_bayar"] or "", "cat1": r["cat1"], "cat2": r["cat2"],
                     "amount": r["amount"], "status": r["status"], "pillar": r["pillar"]})
    return rows


def get_latest_payments(company_id: int, years: list = None, pillars: list = None,
                         kategori: str = None, limit: int = 10) -> list:
    conn = get_conn()
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    kategori_sql, kategori_params = (" AND p.cat1 = ?", [kategori]) if kategori else ("", [])

    rows = conn.execute(
        f"""
        SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{pillar_sql}{kategori_sql}
        ORDER BY p.tanggal DESC NULLS LAST, p.id DESC
        LIMIT ?
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params, *kategori_params, limit],
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_available_years(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT fh_strftime('%Y', b.tanggal) AS y
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''
        UNION
        SELECT DISTINCT fh_strftime('%Y', p.tanggal) AS y
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.tanggal IS NOT NULL AND p.tanggal != ''
        """,
        (company_id, PROGRAM_NAME, company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return sorted({int(r["y"]) for r in rows if r["y"]})


def get_available_pillars(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT p.pillar
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.pillar IS NOT NULL AND p.pillar != ''
        ORDER BY p.pillar
        """,
        (company_id, PROGRAM_NAME),
    ).fetchall()
    conn.close()
    return [r["pillar"] for r in rows]


def get_pillar_breakdown(company_id: int, years: list = None, pillars: list = None) -> list:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")

    budget_pillar_sql, budget_pillar_params = _pillar_filter_sql(pillars, "b.pillar")
    payment_pillar_sql, payment_pillar_params = _pillar_filter_sql(pillars, "p.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT b.pillar, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ?{budget_year_sql}{budget_pillar_sql}
        GROUP BY b.pillar
        """,
        [company_id, PROGRAM_NAME, *budget_year_params, *budget_pillar_params],
    ).fetchall()
    payment_rows = conn.execute(
        f"""
        SELECT p.pillar,
               SUM(CASE WHEN p.status = 'complete' THEN p.amount ELSE 0 END) AS realisasi
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ?{payment_year_sql}{payment_pillar_sql}
        GROUP BY p.pillar
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *payment_pillar_params],
    ).fetchall()
    conn.close()

    pillar_map = {}
    for r in budget_rows:
        pillar = r["pillar"] or "(Tanpa Pillar)"
        pillar_map.setdefault(pillar, {"pillar": pillar, "budget": 0.0, "realisasi": 0.0})
        pillar_map[pillar]["budget"] += float(r["total"] or 0)
    for r in payment_rows:
        pillar = r["pillar"] or "(Tanpa Pillar)"
        pillar_map.setdefault(pillar, {"pillar": pillar, "budget": 0.0, "realisasi": 0.0})
        pillar_map[pillar]["realisasi"] += float(r["realisasi"] or 0)

    result = list(pillar_map.values())
    for p in result:
        p["sisa"] = p["budget"] - p["realisasi"]
    result.sort(key=lambda p: p["pillar"])
    return result


def get_yearly_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    conn = get_conn()
    budget_year_sql, budget_year_params = _year_filter_sql(years, "b.tanggal")
    payment_year_sql, payment_year_params = _year_filter_sql(years, "p.tanggal")
    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    b_pillar_sql, b_pillar_params = _pillar_filter_sql(pillars, "b.pillar")
    
    budget_cat_rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', b.tanggal) AS tahun, b.cat1, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''{budget_year_sql}{b_pillar_sql}
        GROUP BY 1, 2
        """,
        [company_id, PROGRAM_NAME, *budget_year_params, *b_pillar_params],
    ).fetchall()
    
    payment_cat_rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', p.tanggal) AS tahun, p.cat1, SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{payment_year_sql}{pillar_sql}
        GROUP BY 1, 2
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    
    budget_pil_rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', b.tanggal) AS tahun, b.pillar, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND b.tanggal IS NOT NULL AND b.tanggal != ''{budget_year_sql}{b_pillar_sql}
        GROUP BY 1, 2
        """,
        [company_id, PROGRAM_NAME, *budget_year_params, *b_pillar_params],
    ).fetchall()
    
    payment_pil_rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', p.tanggal) AS tahun, p.pillar, SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'
              AND p.tanggal IS NOT NULL AND p.tanggal != ''{payment_year_sql}{pillar_sql}
        GROUP BY 1, 2
        """,
        [company_id, PROGRAM_NAME, *payment_year_params, *pillar_params],
    ).fetchall()
    conn.close()

    years_set = set()
    for r in budget_cat_rows + payment_cat_rows:
        if r["tahun"]: years_set.add(int(r["tahun"]))
    years = sorted(list(years_set))
    
    kategori_data = {}
    pillar_data = {}
    
    for r in budget_cat_rows:
        if not r["tahun"]: continue
        y = int(r["tahun"])
        c = r["cat1"] or "(Tanpa Kategori)"
        if c not in kategori_data: kategori_data[c] = {"budget": {y2:0 for y2 in years}, "realisasi": {y2:0 for y2 in years}}
        kategori_data[c]["budget"][y] += float(r["total"] or 0)
        
    for r in payment_cat_rows:
        if not r["tahun"]: continue
        y = int(r["tahun"])
        c = r["cat1"] or "(Tanpa Kategori)"
        if c not in kategori_data: kategori_data[c] = {"budget": {y2:0 for y2 in years}, "realisasi": {y2:0 for y2 in years}}
        kategori_data[c]["realisasi"][y] += float(r["total"] or 0)
        
    for r in budget_pil_rows:
        if not r["tahun"]: continue
        y = int(r["tahun"])
        p = r["pillar"] or "(Tanpa Pillar)"
        if p not in pillar_data: pillar_data[p] = {"budget": {y2:0 for y2 in years}, "realisasi": {y2:0 for y2 in years}}
        pillar_data[p]["budget"][y] += float(r["total"] or 0)
        
    for r in payment_pil_rows:
        if not r["tahun"]: continue
        y = int(r["tahun"])
        p = r["pillar"] or "(Tanpa Pillar)"
        if p not in pillar_data: pillar_data[p] = {"budget": {y2:0 for y2 in years}, "realisasi": {y2:0 for y2 in years}}
        pillar_data[p]["realisasi"][y] += float(r["total"] or 0)

    kategori_list = []
    for c, d in kategori_data.items():
        kategori_list.append({
            "name": c,
            "budget": [d["budget"][y] for y in years],
            "realisasi": [d["realisasi"][y] for y in years]
        })
        
    pillar_list = []
    for p, d in pillar_data.items():
        pillar_list.append({
            "name": p,
            "budget": [d["budget"][y] for y in years],
            "realisasi": [d["realisasi"][y] for y in years]
        })
        

    return {
        "years": years,
        "kategori": kategori_list,
        "pillar": pillar_list
    }


def get_monthly_breakdown(company_id: int, years: list = None, pillars: list = None) -> dict:
    if not years:
        return {"chart_year": None, "months": [], "comparison": []}

    chart_year = max(years)
    conn = get_conn()

    budget_pillar_sql, budget_pillar_params = _pillar_filter_sql(pillars, "b.pillar")

    budget_rows = conn.execute(
        f"""
        SELECT CAST(fh_strftime('%m', b.tanggal) AS INTEGER) AS bulan, SUM(b.amount) AS total
        FROM budget_beasiswa b
        JOIN siswa s ON s.code = b.siswa_code AND s.company_id = b.company_id
        WHERE b.company_id = ? AND s.program = ? AND fh_strftime('%Y', b.tanggal) = ?{budget_pillar_sql}
        GROUP BY 1
        """,
        [company_id, PROGRAM_NAME, str(chart_year), *budget_pillar_params],
    ).fetchall()

    pillar_sql, pillar_params = _pillar_filter_sql(pillars, "p.pillar")
    year_placeholders = ",".join("?" for _ in years)
    realisasi_rows = conn.execute(
        f"""
        SELECT fh_strftime('%Y', p.tanggal) AS tahun, CAST(fh_strftime('%m', p.tanggal) AS INTEGER) AS bulan,
               SUM(p.amount) AS total
        FROM payment_beasiswa p
        JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
        WHERE p.company_id = ? AND s.program = ? AND p.status = 'complete'
              AND fh_strftime('%Y', p.tanggal) IN ({year_placeholders}){pillar_sql}
        GROUP BY 1, 2
        """,
        [company_id, PROGRAM_NAME, *[str(y) for y in years], *pillar_params],
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

def build_pohon_group_data(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:
    buckets = _build_diagram_buckets(company_id, years, month, pillars)

    filtered_buckets = {}
    for key, b in buckets.items():
        if pillars and not any(p in pillars for p in b["pillars"]):
            continue
        filtered_buckets[key] = b

    groups = {}
    root_total = _empty_metrics()

    # Aggregate by Group
    for (section, subgroup, nama), b in filtered_buckets.items():
        cum = b["val"]
        plafon_total = cum["plafon"] + cum["pta"]
        realisasi = cum["dibayar"]
        
        group_raw = b.get("group_setf")
        group_name = "Tidak Ada Group"
        if group_raw:
            parts = str(group_raw).split('.')
            if len(parts) >= 3:
                prefix = '.'.join(parts[0:3])
            else:
                prefix = str(group_raw)
            group_name = f"Group {prefix}"

        if group_name not in groups:
            groups[group_name] = {"label": group_name, "plafon": 0, "realisasi": 0, "siswa_dict": {}}

        g = groups[group_name]
        g["plafon"] += plafon_total
        g["realisasi"] += realisasi
        
        # Aggregate per student within the group (sum Kesehatan & Pendidikan)
        if nama not in g["siswa_dict"]:
            g["siswa_dict"][nama] = {"nama": nama, "plafon": 0, "realisasi": 0, "group": group_raw or "-"}
        
        g["siswa_dict"][nama]["plafon"] += plafon_total
        g["siswa_dict"][nama]["realisasi"] += realisasi
        
        _add_metrics(root_total, plafon=cum["plafon"], pta=cum["pta"], dibayar=cum["dibayar"])

    # Convert dicts to sorted lists
    group_list = []
    total_orang = 0
    for g_name, g_data in sorted(groups.items()):
        siswa_list = list(g_data["siswa_dict"].values())
        siswa_list.sort(key=lambda x: (x["group"], x["nama"].lower()))
        
        group_count = len(siswa_list)
        total_orang += group_count
        
        g_data["label"] = f"{g_data['label']} ( {group_count} Orang )"
        g_data["siswa"] = siswa_list
        del g_data["siswa_dict"]
        group_list.append(g_data)

    if not pillars:
        label_root = "Semua Pillar"
    elif len(pillars) == 1:
        label_root = pillars[0]
    else:
        label_root = "Gabungan"
        
    label_root = f"{label_root} ( {total_orang} Orang )"

    return {
        "root": {
            "label": label_root,
            "plafon": root_total["plafon"],
            "realisasi": root_total["dibayar"]
        },
        "groups": group_list
    }

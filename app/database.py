# C:\Financehub\app\database.py
import sqlite3
import bcrypt
import config

DDL = """
CREATE TABLE IF NOT EXISTS companies (
    id   INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'requester',
    is_active      INTEGER DEFAULT 1,
    must_change_pw INTEGER DEFAULT 1,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login     TEXT
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked    INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_memo (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    memo_number  TEXT UNIQUE,
    tanggal      TEXT,
    total_amount REAL DEFAULT 0,
    tanggal_bayar TEXT,
    status       TEXT DEFAULT 'open',
    notes        TEXT,
    created_by   TEXT,
    approved_by  TEXT,
    approved_at  TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS siswa (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    code        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    jenjang     TEXT,
    angkatan    INTEGER,
    program     TEXT,
    fakultas    TEXT,
    universitas TEXT,
    bank        TEXT,
    norek       TEXT,
    namarek     TEXT,
    referensi   TEXT,
    ipk_sem1  REAL DEFAULT 0, ipk_sem2  REAL DEFAULT 0,
    ipk_sem3  REAL DEFAULT 0, ipk_sem4  REAL DEFAULT 0,
    ipk_sem5  REAL DEFAULT 0, ipk_sem6  REAL DEFAULT 0,
    ipk_sem7  REAL DEFAULT 0, ipk_sem8  REAL DEFAULT 0,
    ipk_sem9  REAL DEFAULT 0, ipk_sem10 REAL DEFAULT 0,
    ipk_pen1  REAL DEFAULT 0, ipk_pen2  REAL DEFAULT 0,
    ipk_pen3  REAL DEFAULT 0,
    status           TEXT DEFAULT 'Aktif',
    catatan          TEXT,
    catatan_budget   TEXT DEFAULT '',
    catatan_payment  TEXT DEFAULT '',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT,
    UNIQUE(company_id, code)
);

CREATE TABLE IF NOT EXISTS budget_beasiswa (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    siswa_code TEXT NOT NULL,
    cat1       TEXT,
    cat2       TEXT,
    tanggal    TEXT,
    amount     REAL DEFAULT 0,
    pillar     TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_beasiswa (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    siswa_code      TEXT NOT NULL,
    cat1            TEXT,
    cat2            TEXT,
    tanggal         TEXT,
    amount          REAL DEFAULT 0,
    pillar          TEXT,
    pam             TEXT,
    perusahaan      TEXT,
    cat3            TEXT,
    cat4            TEXT,
    memo_id         INTEGER REFERENCES payment_memo(id),
    tgl_pengajuan   TEXT,
    tgl_receive     TEXT,
    tgl_pa          TEXT,
    tgl_final       TEXT,
    etf_pa_line_id  INTEGER,
    status          TEXT DEFAULT 'open',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_memo_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    memo_id       INTEGER NOT NULL REFERENCES payment_memo(id),
    source_module TEXT NOT NULL,
    source_id     INTEGER NOT NULL,
    description   TEXT,
    amount        REAL DEFAULT 0,
    vendor        TEXT,
    bank_account  TEXT
);

CREATE TABLE IF NOT EXISTS payment_application (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL REFERENCES companies(id),
    memo_id             INTEGER NOT NULL REFERENCES payment_memo(id),
    application_number  TEXT UNIQUE,
    submitted_at        TEXT,
    target_payment_date TEXT,
    actual_payment_date TEXT,
    status              TEXT DEFAULT 'open',
    tat_days            INTEGER,
    notes               TEXT,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS klaim_medical (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id),
    siswa_code   TEXT NOT NULL,
    pam          TEXT,
    tanggal      TEXT,
    amount       REAL DEFAULT 0,
    perawatan    TEXT,
    kelas        TEXT,
    rumah_sakit  TEXT,
    diagnosa     TEXT,
    spesialisasi TEXT,
    pillar       TEXT,
    perusahaan   TEXT,
    payment_id   INTEGER,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rekam_medis (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL,
    payment_id   INTEGER NOT NULL REFERENCES payment_beasiswa(id),
    siswa_code   TEXT NOT NULL,
    kelas        TEXT NOT NULL,
    rumah_sakit  TEXT NOT NULL,
    diagnosa     TEXT NOT NULL,
    spesialisasi TEXT NOT NULL,
    catatan      TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pam_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    pam_no          TEXT UNIQUE NOT NULL,
    pam_date        TEXT,
    gl_account      TEXT DEFAULT '70110230',
    cost_center     TEXT,
    pt              TEXT,
    requestors_name TEXT DEFAULT 'Jany Turkanda',
    keterangan      TEXT,
    total_amount    REAL DEFAULT 0,
    due_date        TEXT,
    status          TEXT DEFAULT 'open',
    source          TEXT,
    pillar          TEXT,
    mata_uang       TEXT DEFAULT 'IDR',
    dpp             REAL DEFAULT 0,
    ppn             REAL DEFAULT 0,
    tanggal_bayar   TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS coa (
    gl_code   TEXT PRIMARY KEY,
    gl_name   TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vendors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    pillar      TEXT NOT NULL,
    cost_center TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS etf_pa (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id               INTEGER NOT NULL REFERENCES companies(id),
    pa_number                TEXT NOT NULL,
    tgl_payment_application  TEXT,
    tgl_surat_pengajuan      TEXT,
    doc_received_by_educ     TEXT,
    received_pa_from_educ    TEXT,
    checked_by_fincon        TEXT,
    approved_by_htj_1        TEXT,
    send_pa_back_to_educ     TEXT,
    pa_received_by_po_fin    TEXT,
    approval_by_htj_2        TEXT,
    nomor_pam                TEXT,
    tanggal_bayar            TEXT,
    keterangan               TEXT,
    status                   TEXT NOT NULL DEFAULT 'draft',
    created_at               TEXT NOT NULL,
    updated_at               TEXT
);

CREATE TABLE IF NOT EXISTS etf_pa_lines (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    pa_id                INTEGER NOT NULL REFERENCES etf_pa(id) ON DELETE CASCADE,
    student_id           INTEGER NOT NULL REFERENCES siswa(id),
    jenis_pembayaran     TEXT,
    semester             TEXT,
    tahun_ajaran         TEXT,
    ipk_sem_sebelumnya   REAL,
    jumlah_pembayaran    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_etf_pa_company    ON etf_pa(company_id);
CREATE INDEX IF NOT EXISTS idx_etf_pa_lines_pa   ON etf_pa_lines(pa_id);
CREATE INDEX IF NOT EXISTS idx_etf_pa_lines_sid  ON etf_pa_lines(student_id);

CREATE VIEW IF NOT EXISTS pa_summary AS
SELECT
    e.company_id,
    e.pa_number,
    GROUP_CONCAT(DISTINCT e.tgl_payment_application) AS tgl_payment_application,
    GROUP_CONCAT(DISTINCT e.nomor_pam)               AS nomor_pam,
    GROUP_CONCAT(DISTINCT s.nama)                    AS nama_student,
    GROUP_CONCAT(DISTINCT l.jenis_pembayaran)        AS jenis_pembayaran,
    GROUP_CONCAT(DISTINCT l.semester)                AS semester,
    SUM(l.jumlah_pembayaran)                         AS jumlah_pembayaran,
    GROUP_CONCAT(DISTINCT e.status)                  AS status,
    GROUP_CONCAT(DISTINCT e.tanggal_bayar)           AS tanggal_bayar,
    GROUP_CONCAT(DISTINCT e.keterangan)              AS keterangan
FROM etf_pa e
LEFT JOIN etf_pa_lines l ON l.pa_id = e.id
LEFT JOIN siswa s ON s.id = l.student_id
GROUP BY e.company_id, e.pa_number;

CREATE TABLE IF NOT EXISTS agri_pam_lines (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor          TEXT,
    nama_vendor        TEXT,
    tgl_terima_doc     TEXT,
    tgl_proses         TEXT,
    tgl_verifikasi_tax TEXT,
    tgl_approval_1     TEXT,
    tgl_approval_2     TEXT,
    tgl_approval_3     TEXT,
    tgl_kirim          TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS app_pam_lines (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor          TEXT,
    nama_vendor        TEXT,
    tgl_terima_doc     TEXT,
    tgl_proses         TEXT,
    tgl_verifikasi_tax TEXT,
    tgl_approval_1     TEXT,
    tgl_approval_2     TEXT,
    tgl_approval_3     TEXT,
    tgl_kirim          TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS land_pam_lines (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor          TEXT,
    nama_vendor        TEXT,
    tgl_terima_doc     TEXT,
    tgl_proses         TEXT,
    tgl_verifikasi_tax TEXT,
    tgl_approval_1     TEXT,
    tgl_approval_2     TEXT,
    tgl_approval_3     TEXT,
    tgl_kirim          TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS setf_pam_lines (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor          TEXT,
    nama_vendor        TEXT,
    tgl_terima_doc     TEXT,
    tgl_proses         TEXT,
    tgl_verifikasi_tax TEXT,
    tgl_approval_1     TEXT,
    tgl_approval_2     TEXT,
    tgl_approval_3     TEXT,
    tgl_kirim          TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS energy_pam_lines (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
    no_vendor          TEXT,
    nama_vendor        TEXT,
    tgl_terima_doc     TEXT,
    tgl_proses         TEXT,
    tgl_verifikasi_tax TEXT,
    tgl_approval_1     TEXT,
    tgl_approval_2     TEXT,
    tgl_approval_3     TEXT,
    tgl_kirim          TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS energy_pa (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id               INTEGER NOT NULL REFERENCES companies(id),
    pa_number                TEXT UNIQUE NOT NULL,
    tgl_payment_application  TEXT,
    tgl_surat_pengajuan      TEXT,
    doc_received_by_educ     TEXT,
    received_pa_from_educ    TEXT,
    checked_by_fincon        TEXT,
    approved_by_htj_1        TEXT,
    send_pa_back_to_educ     TEXT,
    pa_received_by_po_fin    TEXT,
    approval_by_htj_2        TEXT,
    nomor_pam                TEXT,
    tanggal_bayar            TEXT,
    keterangan               TEXT,
    no_pa                    TEXT,
    category                 TEXT,
    categori_1               TEXT,
    nomor_vendor             TEXT,
    nama_vendor              TEXT,
    mata_uang                TEXT DEFAULT 'IDR',
    dpp                      INTEGER DEFAULT 0,
    ppn                      INTEGER DEFAULT 0,
    total                    INTEGER DEFAULT 0,
    terima_document          TEXT,
    input_aspiro             TEXT,
    verifikasi_tax           TEXT,
    approval_1               TEXT,
    approval_2               TEXT,
    approval_3               TEXT,
    kirim_aspiro             TEXT,
    paid                     TEXT,
    status                   TEXT NOT NULL DEFAULT 'open',
    created_at               TEXT NOT NULL,
    updated_at               TEXT
);

CREATE TABLE IF NOT EXISTS energy_pa_lines (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    pa_id                INTEGER NOT NULL REFERENCES energy_pa(id) ON DELETE CASCADE,
    student_id           INTEGER NOT NULL REFERENCES siswa(id),
    jenis_pembayaran     TEXT,
    semester             TEXT,
    tahun_ajaran         TEXT,
    ipk_sem_sebelumnya   REAL,
    jumlah_pembayaran    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_agri_pam_lines_pam   ON agri_pam_lines(pam_id);
CREATE INDEX IF NOT EXISTS idx_app_pam_lines_pam    ON app_pam_lines(pam_id);
CREATE INDEX IF NOT EXISTS idx_land_pam_lines_pam   ON land_pam_lines(pam_id);
CREATE INDEX IF NOT EXISTS idx_setf_pam_lines_pam   ON setf_pam_lines(pam_id);
CREATE INDEX IF NOT EXISTS idx_energy_pam_lines_pam ON energy_pam_lines(pam_id);
CREATE INDEX IF NOT EXISTS idx_energy_pa_company    ON energy_pa(company_id);
CREATE INDEX IF NOT EXISTS idx_energy_pa_lines_pa   ON energy_pa_lines(pa_id);
"""

VENDOR_SEED = [
    ("PT. Aditunggal Mahajaya",                        "AGRI",           "5101C1POFF"),
    ("PT. Agrokarya Primalestari",                     "AGRI",           "4401C1POFF"),
    ("PT. Agrolestari Sentosa",                        "AGRI",           "4201C1POFF"),
    ("PT. Binasawit Abadi Pratama",                    "AGRI",           "3201C1POFF"),
    ("PT. Buana Artha Sejahtera",                      "AGRI",           "4501C1POFF"),
    ("PT. Buana Wiralestari Mas",                      "AGRI",           "2001C1POFF"),
    ("PT. Bumi Permai Lestari",                        "AGRI",           "2601C1POFF"),
    ("PT. Djuandasawit Lestari",                       "AGRI",           "2801C1POFF"),
    ("PT. Forestalestari Dwikarya",                    "AGRI",           "2901C1POFF"),
    ("PT. Ivo Mas Tunggal",                            "AGRI",           "1901C1POFF"),
    ("PT. Kresna Duta Agroindo",                       "AGRI",           "1101C1POFF"),
    ("PT. Maskapai Perkebunan Leidong West Indonesia", "AGRI",           "1201C1POFF"),
    ("PT. Mitrakarya Agroindo",                        "AGRI",           "3801C1POFF"),
    ("PT. Paramitra Internusa Pratama",                "AGRI",           "4701C1POFF"),
    ("PT. Ramajaya Pramukti",                          "AGRI",           "2101C1POFF"),
    ("PT. SMART Tbk",                                  "AGRI",           "1008C1POFF"),
    ("PT. Sawitakarya Manunggul",                      "AGRI",           "3401C1POFF"),
    ("PT. Sumber Indah Perkasa",                       "AGRI",           "2501C1CMOF"),
    ("PT. Tapian Nadenggan",                           "AGRI",           "1401C1POFF"),
    ("NON PILLAR",                                     "NON PILLAR",     "NON PILLAR"),
    ("NON ALLOCATED",                                  "NON ALLOCATED",  "NON ALLOCATED"),
    ("SAHABAT ETF",                                    "SETF",           "SAHABAT ETF"),
]


def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migrate_db():
    conn = get_conn()
    try:
        conn.execute("ALTER TABLE payment_memo ADD COLUMN tanggal_bayar TEXT")
        conn.commit()
    except Exception:
        pass
    for col in ["tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final",
                "tgl_retur", "tgl_final6", "tgl_proses",
                "tgl_HT_AGRI", "tgl_Yurike_AGRI", "tgl_Aditya_AGRI",
                "tgl_Pedy_AGRI", "tgl_C2_AGRI", "tgl_MSIG_AGRI", "tgl_Paid_AGRI",
                "tgl_A-GS_APP", "tgl_A-HJK_APP", "tgl_ASPIRO_APP", "tgl_Paid_APP",
                "tgl_Paid_LAND", "tgl_Paid_ENERGY", "tgl_Paid_SETF"]:
        try:
            conn.execute(f'ALTER TABLE payment_beasiswa ADD COLUMN "{col}" TEXT')
            conn.commit()
        except Exception:
            pass
    # ── SLA column rename/add/drop (2026-06-24) ───────────────────────────
    with get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(payment_beasiswa)")}
        renames = [
            ("tgl_HT_AGRI",     "SLA_Date_2_HT"),
            ("tgl_Yurike_AGRI", "SLA_Date_3_YK"),
            ("tgl_Aditya_AGRI", "SLA_Date_4_AK"),
            ("tgl_Pedy_AGRI",   "SLA_Date_5_PD"),
            ("tgl_C2_AGRI",     "SLA_Date_6_C2"),
            ("tgl_MSIG_AGRI",   "SLA_Date_7_MSIG"),
        ]
        for old, new in renames:
            if old in cols and new not in cols:
                conn.execute(f'ALTER TABLE payment_beasiswa RENAME COLUMN "{old}" TO "{new}"')
            elif old in cols and new in cols:
                # old col was re-added by ADD COLUMN loop after previous rename — drop the stale copy
                conn.execute(f'ALTER TABLE payment_beasiswa DROP COLUMN "{old}"')
        if "SLA_Date_1_LL" not in cols:
            conn.execute('ALTER TABLE payment_beasiswa ADD COLUMN "SLA_Date_1_LL" TEXT')
        if "tgl_Paid_AGRI" in cols:
            conn.execute('ALTER TABLE payment_beasiswa DROP COLUMN "tgl_Paid_AGRI"')
        conn.commit()
    try:
        conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN etf_pa_line_id INTEGER REFERENCES etf_pa_lines(id)")
        conn.commit()
    except Exception:
        pass
    for col in ["catatan_budget", "catatan_payment", "angkatan_kuliah", "prodi"]:
        try:
            conn.execute(f"ALTER TABLE siswa ADD COLUMN {col} TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass
    # klaim_medical table (may not exist in older DBs)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS klaim_medical ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "company_id INTEGER NOT NULL,"
            "siswa_code TEXT NOT NULL,"
            "pam TEXT, tanggal TEXT, amount REAL DEFAULT 0,"
            "perawatan TEXT, kelas TEXT, rumah_sakit TEXT,"
            "diagnosa TEXT, spesialisasi TEXT,"
            "pillar TEXT, perusahaan TEXT, payment_id INTEGER,"
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()
    except Exception:
        pass

    # pam_records table (new — safe to run on existing DBs)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pam_records (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id      INTEGER NOT NULL,
                pam_no          TEXT UNIQUE NOT NULL,
                pam_date        TEXT,
                gl_account      TEXT DEFAULT '70110230',
                cost_center     TEXT,
                pt              TEXT,
                requestors_name TEXT DEFAULT 'Jany Turkanda',
                keterangan      TEXT,
                total_amount    REAL DEFAULT 0,
                due_date        TEXT,
                status          TEXT DEFAULT 'draft',
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at      TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # coa table (new)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS coa (gl_code TEXT PRIMARY KEY, gl_name TEXT NOT NULL, is_active INTEGER DEFAULT 1)"
        )
        for entry in config.COA_LIST:
            conn.execute(
                "INSERT OR IGNORE INTO coa (gl_code, gl_name) VALUES (?, ?)",
                (entry["gl_code"], entry["gl_name"])
            )
        conn.commit()
    except Exception:
        pass

    # vendors table — create + add cost_center column if missing
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS vendors "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, "
            "pillar TEXT NOT NULL, cost_center TEXT DEFAULT '')"
        )
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE vendors ADD COLUMN cost_center TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    for name, pillar, cc in VENDOR_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO vendors (name, pillar, cost_center) VALUES (?, ?, ?)",
            (name, pillar, cc)
        )
        if cc:
            conn.execute(
                "UPDATE vendors SET cost_center=? WHERE name=? AND (cost_center IS NULL OR cost_center='')",
                (cc, name)
            )
    # remove vendors with no cost_center (keep only special non-pillar rows)
    conn.execute(
        "DELETE FROM vendors WHERE (cost_center IS NULL OR cost_center='') "
        "AND name NOT IN ('NON PILLAR','NON ALLOCATED','SAHABAT ETF')"
    )
    conn.commit()

    # etf_pa — drop UNIQUE constraint on pa_number (recreate table)
    try:
        has_unique = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='etf_pa'"
        ).fetchone()
        if has_unique and "UNIQUE" in (has_unique[0] or ""):
            conn.executescript("""
                PRAGMA foreign_keys = OFF;
                ALTER TABLE etf_pa RENAME TO etf_pa_old;
                CREATE TABLE etf_pa (
                    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id               INTEGER NOT NULL REFERENCES companies(id),
                    pa_number                TEXT NOT NULL,
                    tgl_payment_application  TEXT,
                    tgl_surat_pengajuan      TEXT,
                    doc_received_by_educ     TEXT,
                    received_pa_from_educ    TEXT,
                    checked_by_fincon        TEXT,
                    approved_by_htj_1        TEXT,
                    send_pa_back_to_educ     TEXT,
                    pa_received_by_po_fin    TEXT,
                    approval_by_htj_2        TEXT,
                    nomor_pam                TEXT,
                    tanggal_bayar            TEXT,
                    keterangan               TEXT,
                    status                   TEXT NOT NULL DEFAULT 'draft',
                    created_at               TEXT NOT NULL,
                    updated_at               TEXT
                );
                INSERT INTO etf_pa SELECT * FROM etf_pa_old;
                DROP TABLE etf_pa_old;
                PRAGMA foreign_keys = ON;
            """)
            conn.commit()
        else:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS etf_pa (
                    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id               INTEGER NOT NULL REFERENCES companies(id),
                    pa_number                TEXT NOT NULL,
                    tgl_payment_application  TEXT,
                    tgl_surat_pengajuan      TEXT,
                    doc_received_by_educ     TEXT,
                    received_pa_from_educ    TEXT,
                    checked_by_fincon        TEXT,
                    approved_by_htj_1        TEXT,
                    send_pa_back_to_educ     TEXT,
                    pa_received_by_po_fin    TEXT,
                    approval_by_htj_2        TEXT,
                    nomor_pam                TEXT,
                    tanggal_bayar            TEXT,
                    keterangan               TEXT,
                    status                   TEXT NOT NULL DEFAULT 'draft',
                    created_at               TEXT NOT NULL,
                    updated_at               TEXT)"""
            )
            conn.commit()
    except Exception as e:
        print(f"[migrate] etf_pa UNIQUE drop: {e}")

    # etf_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS etf_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES etf_pa(id) ON DELETE CASCADE,
                student_id           INTEGER NOT NULL,
                jenis_pembayaran     TEXT,
                semester             TEXT,
                tahun_ajaran         TEXT,
                ipk_sem_sebelumnya   REAL,
                jumlah_pembayaran    INTEGER DEFAULT 0)"""
        )
        conn.commit()
    except Exception:
        pass

    # indexes for etf_pa queries
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_etf_pa_company   ON etf_pa(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_etf_pa_lines_pa  ON etf_pa_lines(pa_id)",
        "CREATE INDEX IF NOT EXISTS idx_etf_pa_lines_sid ON etf_pa_lines(student_id)",
    ]:
        try:
            conn.execute(idx_sql)
        except Exception:
            pass
    conn.commit()

    # pa_summary view
    try:
        conn.executescript("""
            DROP VIEW IF EXISTS pa_summary;
            CREATE VIEW pa_summary AS
            SELECT
                e.company_id,
                e.pa_number,
                GROUP_CONCAT(DISTINCT e.tgl_payment_application) AS tgl_payment_application,
                GROUP_CONCAT(DISTINCT e.nomor_pam)               AS nomor_pam,
                GROUP_CONCAT(DISTINCT s.nama)                    AS nama_student,
                GROUP_CONCAT(DISTINCT l.jenis_pembayaran)        AS jenis_pembayaran,
                GROUP_CONCAT(DISTINCT l.semester)                AS semester,
                SUM(l.jumlah_pembayaran)                         AS jumlah_pembayaran,
                GROUP_CONCAT(DISTINCT e.status)                  AS status,
                GROUP_CONCAT(DISTINCT e.tanggal_bayar)           AS tanggal_bayar,
                GROUP_CONCAT(DISTINCT e.keterangan)              AS keterangan
            FROM etf_pa e
            LEFT JOIN etf_pa_lines l ON l.pa_id = e.id
            LEFT JOIN siswa s ON s.id = l.student_id
            GROUP BY e.company_id, e.pa_number;
        """)
        conn.commit()
    except Exception as e:
        print(f"[migrate] pa_summary view: {e}")

    # sml_pa table — student-based PA (same schema as etf_pa/app_pa)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sml_pa (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id               INTEGER NOT NULL REFERENCES companies(id),
                pa_number                TEXT UNIQUE NOT NULL,
                tgl_payment_application  TEXT,
                tgl_surat_pengajuan      TEXT,
                doc_received_by_educ     TEXT,
                received_pa_from_educ    TEXT,
                checked_by_fincon        TEXT,
                approved_by_htj_1        TEXT,
                send_pa_back_to_educ     TEXT,
                pa_received_by_po_fin    TEXT,
                approval_by_htj_2        TEXT,
                nomor_pam                TEXT,
                tanggal_bayar            TEXT,
                keterangan               TEXT,
                status                   TEXT NOT NULL DEFAULT 'open',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # sml_pa — safely add student-PA columns if old tracking schema exists
    for _col in [
        "company_id INTEGER NOT NULL DEFAULT 2",
        "pa_number TEXT",
        "tgl_payment_application TEXT",
        "tgl_surat_pengajuan TEXT",
        "doc_received_by_educ TEXT",
        "received_pa_from_educ TEXT",
        "checked_by_fincon TEXT",
        "approved_by_htj_1 TEXT",
        "send_pa_back_to_educ TEXT",
        "pa_received_by_po_fin TEXT",
        "approval_by_htj_2 TEXT",
        "nomor_pam TEXT",
        "tanggal_bayar TEXT",
        "keterangan TEXT",
        "status TEXT NOT NULL DEFAULT 'open'",
        "created_at TEXT DEFAULT '2000-01-01T00:00:00'",
        "updated_at TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE sml_pa ADD COLUMN {_col}")
            conn.commit()
        except Exception:
            pass

    # sml_pa vendor payment tracking columns (for payment memo SML tab)
    for _col in [
        "no_pa TEXT",
        "category TEXT",
        "categori_1 TEXT",
        "nomor_vendor TEXT",
        "nama_vendor TEXT",
        "mata_uang TEXT DEFAULT 'IDR'",
        "dpp INTEGER DEFAULT 0",
        "ppn INTEGER DEFAULT 0",
        "total INTEGER DEFAULT 0",
        "terima_document TEXT",
        "input_aspiro TEXT",
        "verifikasi_tax TEXT",
        "approval_1 TEXT",
        "approval_2 TEXT",
        "approval_3 TEXT",
        "kirim_aspiro TEXT",
        "paid TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE sml_pa ADD COLUMN {_col}")
            conn.commit()
        except Exception:
            pass

    # sml_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sml_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES sml_pa(id) ON DELETE CASCADE,
                student_id           INTEGER NOT NULL REFERENCES siswa(id),
                jenis_pembayaran     TEXT,
                semester             TEXT,
                tahun_ajaran         TEXT,
                ipk_sem_sebelumnya   REAL,
                jumlah_pembayaran    INTEGER DEFAULT 0)"""
        )
        conn.commit()
    except Exception:
        pass

    # setf_pa table — student-based PA for SETF
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS setf_pa (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id               INTEGER NOT NULL REFERENCES companies(id),
                pa_number                TEXT UNIQUE NOT NULL,
                tgl_payment_application  TEXT,
                tgl_surat_pengajuan      TEXT,
                doc_received_by_educ     TEXT,
                received_pa_from_educ    TEXT,
                checked_by_fincon        TEXT,
                approved_by_htj_1        TEXT,
                send_pa_back_to_educ     TEXT,
                pa_received_by_po_fin    TEXT,
                approval_by_htj_2        TEXT,
                nomor_pam                TEXT,
                tanggal_bayar            TEXT,
                keterangan               TEXT,
                status                   TEXT NOT NULL DEFAULT 'open',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # setf_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS setf_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES setf_pa(id) ON DELETE CASCADE,
                student_id           INTEGER NOT NULL REFERENCES siswa(id),
                jenis_pembayaran     TEXT,
                semester             TEXT,
                tahun_ajaran         TEXT,
                ipk_sem_sebelumnya   REAL,
                jumlah_pembayaran    INTEGER DEFAULT 0)"""
        )
        conn.commit()
    except Exception:
        pass

    # app_pa table — student-based PA for APP
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS app_pa (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id               INTEGER NOT NULL REFERENCES companies(id),
                pa_number                TEXT UNIQUE NOT NULL,
                tgl_payment_application  TEXT,
                tgl_surat_pengajuan      TEXT,
                doc_received_by_educ     TEXT,
                received_pa_from_educ    TEXT,
                checked_by_fincon        TEXT,
                approved_by_htj_1        TEXT,
                send_pa_back_to_educ     TEXT,
                pa_received_by_po_fin    TEXT,
                approval_by_htj_2        TEXT,
                nomor_pam                TEXT,
                tanggal_bayar            TEXT,
                keterangan               TEXT,
                status                   TEXT NOT NULL DEFAULT 'open',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # app_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS app_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES app_pa(id) ON DELETE CASCADE,
                student_id           INTEGER NOT NULL REFERENCES siswa(id),
                jenis_pembayaran     TEXT,
                semester             TEXT,
                tahun_ajaran         TEXT,
                ipk_sem_sebelumnya   REAL,
                jumlah_pembayaran    INTEGER DEFAULT 0)"""
        )
        conn.commit()
    except Exception:
        pass

    # indexes for sml_pa, setf_pa, and app_pa queries
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_sml_pa_company    ON sml_pa(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_sml_pa_lines_pa   ON sml_pa_lines(pa_id)",
        "CREATE INDEX IF NOT EXISTS idx_sml_pa_lines_sid  ON sml_pa_lines(student_id)",
        "CREATE INDEX IF NOT EXISTS idx_setf_pa_company   ON setf_pa(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_setf_pa_lines_pa  ON setf_pa_lines(pa_id)",
        "CREATE INDEX IF NOT EXISTS idx_setf_pa_lines_sid ON setf_pa_lines(student_id)",
        "CREATE INDEX IF NOT EXISTS idx_app_pa_company    ON app_pa(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_app_pa_lines_pa   ON app_pa_lines(pa_id)",
        "CREATE INDEX IF NOT EXISTS idx_app_pa_lines_sid  ON app_pa_lines(student_id)",
    ]:
        try:
            conn.execute(idx_sql)
        except Exception:
            pass
    conn.commit()

    # rekam_medis table (new — safe to run on existing DBs)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS rekam_medis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                payment_id INTEGER NOT NULL REFERENCES payment_beasiswa(id),
                siswa_code TEXT NOT NULL,
                kelas TEXT NOT NULL,
                rumah_sakit TEXT NOT NULL,
                diagnosa TEXT NOT NULL,
                spesialisasi TEXT NOT NULL,
                catatan TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        conn.commit()
    except Exception:
        pass

    # pam_records — add tanggal_bayar and source if missing
    for col_def in [
        "tanggal_bayar TEXT",
        "source TEXT DEFAULT 'beasiswa'",
    ]:
        try:
            conn.execute(f"ALTER TABLE pam_records ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass

    # pam_records — add standardization columns (mata_uang, dpp, ppn, pillar)
    for col_def in [
        "mata_uang TEXT DEFAULT 'IDR'",
        "dpp       INTEGER DEFAULT 0",
        "ppn       INTEGER DEFAULT 0",
        "pillar    TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE pam_records ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass

    # pam lines tables per pillar (all identical schema initially)
    _PAM_LINES_DDL = """
        CREATE TABLE IF NOT EXISTS {tbl} (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            pam_id             INTEGER NOT NULL REFERENCES pam_records(id) ON DELETE CASCADE,
            no_vendor          TEXT,
            nama_vendor        TEXT,
            tgl_terima_doc     TEXT,
            tgl_proses         TEXT,
            tgl_verifikasi_tax TEXT,
            tgl_approval_1     TEXT,
            tgl_approval_2     TEXT,
            tgl_approval_3     TEXT,
            tgl_kirim          TEXT,
            created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at         TEXT
        )"""
    for tbl in ["agri_pam_lines", "app_pam_lines", "land_pam_lines", "setf_pam_lines", "energy_pam_lines"]:
        try:
            conn.execute(_PAM_LINES_DDL.format(tbl=tbl))
            conn.commit()
        except Exception:
            pass
    for tbl in ["agri_pam_lines", "app_pam_lines", "land_pam_lines", "setf_pam_lines", "energy_pam_lines"]:
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{tbl}_pam ON {tbl}(pam_id)")
            conn.commit()
        except Exception:
            pass

    # energy_pa table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS energy_pa (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id               INTEGER NOT NULL REFERENCES companies(id),
                pa_number                TEXT UNIQUE NOT NULL,
                tgl_payment_application  TEXT,
                tgl_surat_pengajuan      TEXT,
                doc_received_by_educ     TEXT,
                received_pa_from_educ    TEXT,
                checked_by_fincon        TEXT,
                approved_by_htj_1        TEXT,
                send_pa_back_to_educ     TEXT,
                pa_received_by_po_fin    TEXT,
                approval_by_htj_2        TEXT,
                nomor_pam                TEXT,
                tanggal_bayar            TEXT,
                keterangan               TEXT,
                no_pa                    TEXT,
                category                 TEXT,
                categori_1               TEXT,
                nomor_vendor             TEXT,
                nama_vendor              TEXT,
                mata_uang                TEXT DEFAULT 'IDR',
                dpp                      INTEGER DEFAULT 0,
                ppn                      INTEGER DEFAULT 0,
                total                    INTEGER DEFAULT 0,
                terima_document          TEXT,
                input_aspiro             TEXT,
                verifikasi_tax           TEXT,
                approval_1               TEXT,
                approval_2               TEXT,
                approval_3               TEXT,
                kirim_aspiro             TEXT,
                paid                     TEXT,
                status                   TEXT NOT NULL DEFAULT 'open',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
        conn.commit()
    except Exception:
        pass

    # energy_pa_lines table
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS energy_pa_lines (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                pa_id                INTEGER NOT NULL REFERENCES energy_pa(id) ON DELETE CASCADE,
                student_id           INTEGER NOT NULL REFERENCES siswa(id),
                jenis_pembayaran     TEXT,
                semester             TEXT,
                tahun_ajaran         TEXT,
                ipk_sem_sebelumnya   REAL,
                jumlah_pembayaran    INTEGER DEFAULT 0)"""
        )
        conn.commit()
    except Exception:
        pass

    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_energy_pa_company    ON energy_pa(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_energy_pa_lines_pa   ON energy_pa_lines(pa_id)",
        "CREATE INDEX IF NOT EXISTS idx_energy_pa_lines_sid  ON energy_pa_lines(student_id)",
    ]:
        try:
            conn.execute(idx_sql)
        except Exception:
            pass
    conn.commit()

    # Normalize PA status values to lowercase (fix Title Case legacy data)
    # Old data may have 'Open', 'Complete', 'On_Process' from before the lowercase refactor
    for pa_tbl in ["etf_pa", "app_pa", "sml_pa"]:
        try:
            conn.execute(
                f"UPDATE {pa_tbl} SET status = LOWER(status) "
                f"WHERE status != LOWER(status)"
            )
            conn.commit()
        except Exception:
            pass

    # fiori_pa table — APP (FIORI) PAM tracking
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS fiori_pa (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                no_pa            TEXT,
                category         TEXT,
                keterangan       TEXT,
                categori_1       TEXT,
                nama_vendor      TEXT,
                total            REAL DEFAULT 0,
                terima_document  TEXT,
                input_aspiro     TEXT,
                verifikasi_tax   TEXT,
                approval_1       TEXT,
                approval_2       TEXT,
                kirim_aspiro     TEXT,
                paid             TEXT,
                status           TEXT DEFAULT 'open',
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        conn.commit()
    except Exception:
        pass

    conn.close()


def init_db():
    conn = get_conn()
    conn.executescript(DDL)
    for c in config.COMPANIES:
        conn.execute(
            "INSERT OR IGNORE INTO companies (id, code, name) VALUES (?, ?, ?)",
            (c["id"], c["code"], c["name"])
        )
    for entry in config.COA_LIST:
        conn.execute(
            "INSERT OR IGNORE INTO coa (gl_code, gl_name) VALUES (?, ?)",
            (entry["gl_code"], entry["gl_name"])
        )
    for name, pillar, cc in VENDOR_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO vendors (name, pillar, cost_center) VALUES (?, ?, ?)",
            (name, pillar, cc)
        )
    row = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if row is None:
        pw_hash = bcrypt.hashpw(
            config.ADMIN_DEFAULT_PASSWORD.encode(), bcrypt.gensalt(12)
        ).decode()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, must_change_pw) "
            "VALUES ('admin', ?, 'releaser', 1)",
            (pw_hash,)
        )
    conn.commit()
    conn.close()
    migrate_db()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")

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
    status       TEXT DEFAULT 'draft',
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
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    siswa_code TEXT NOT NULL,
    cat1       TEXT,
    cat2       TEXT,
    tanggal    TEXT,
    amount     REAL DEFAULT 0,
    pillar     TEXT,
    pam        TEXT,
    perusahaan TEXT,
    cat3       TEXT,
    cat4       TEXT,
    memo_id    INTEGER REFERENCES payment_memo(id),
    status     TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    status              TEXT DEFAULT 'pending',
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
    status          TEXT DEFAULT 'draft',
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
    for col in ["tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final",
                "tgl_retur", "tgl_final6", "tgl_proses",
                "tgl_HT_AGRI", "tgl_Yurike_AGRI", "tgl_Aditya_AGRI",
                "tgl_Pedy_AGRI", "tgl_C2_AGRI", "tgl_MSIG_AGRI", "tgl_Paid_AGRI",
                "tgl_A-GS_APP", "tgl_A-HJK_APP", "tgl_ASPIRO_APP", "tgl_Paid_APP"]:
        try:
            conn.execute(f'ALTER TABLE payment_beasiswa ADD COLUMN "{col}" TEXT')
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

    # etf_pa + etf_pa_lines tables
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS etf_pa (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id               INTEGER NOT NULL,
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
                status                   TEXT NOT NULL DEFAULT 'draft',
                created_at               TEXT NOT NULL,
                updated_at               TEXT)"""
        )
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

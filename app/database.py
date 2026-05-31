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
    status      TEXT DEFAULT 'Aktif',
    catatan     TEXT,
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
"""


def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migrate_db():
    conn = get_conn()
    for col in ["tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final"]:
        try:
            conn.execute(f"ALTER TABLE payment_beasiswa ADD COLUMN {col} TEXT")
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

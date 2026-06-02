# Finance Hub Fase 1 — Part 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold Finance Hub Flask app dengan SQLite database, JWT auth 3 role, base templates, dan dashboard — semua berjalan di `http://localhost:8080`.

**Architecture:** Flask Blueprint-based app dengan JWT disimpan di cookie (httpOnly=False untuk LAN). Company aktif disimpan di Flask session. SQLite diinit otomatis saat app pertama kali jalan.

**Tech Stack:** Python 3.9+, Flask 3.0, flask-jwt-extended 4.6, bcrypt 4.0, flask-cors, SQLite (built-in)

**Prerequisite:** Semua file dibuat di folder `C:\Financehub\app\`

---

## File Structure

```
C:\Financehub\app\
├── app.py                        ← Flask factory + register blueprints
├── config.py                     ← Konstanta: DB_PATH, JWT_SECRET, COMPANIES, JENJANG, dll
├── database.py                   ← init_db(), get_conn(), DDL semua tabel
├── run.py                        ← Entry point: python run.py
├── requirements.txt
├── .gitignore
├── auth/
│   ├── __init__.py
│   ├── routes.py                 ← /auth/login, /auth/logout, /auth/refresh, /auth/change-password
│   └── middleware.py             ← jwt_html_required, role_required, html_role_required
├── modules/
│   └── dashboard/
│       ├── __init__.py
│       └── routes.py             ← / dan /select-company
├── templates/
│   ├── base.html                 ← Layout utama: navbar + company switcher + flash messages
│   ├── login.html
│   ├── change_password.html
│   ├── company_select.html
│   └── dashboard/
│       └── index.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── tests/
    ├── conftest.py
    ├── test_auth.py
    └── test_dashboard.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `C:\Financehub\app\requirements.txt`
- Create: `C:\Financehub\app\.gitignore`
- Create: `C:\Financehub\app\auth\__init__.py`
- Create: `C:\Financehub\app\modules\dashboard\__init__.py`
- Create: semua `__init__.py` kosong untuk packages

- [ ] **Step 1: Buat folder struktur**

```bash
cd C:\Financehub\app
mkdir auth modules modules\dashboard templates templates\dashboard static static\css static\js tests
```

- [ ] **Step 2: Buat requirements.txt**

```
C:\Financehub\app\requirements.txt
```

```
flask>=3.0
flask-jwt-extended>=4.6
bcrypt>=4.0
flask-cors>=4.0
waitress>=3.0
reportlab>=4.0
pytest>=8.0
pytest-flask>=1.3
```

- [ ] **Step 3: Install dependencies**

```bash
cd C:\Financehub\app
pip install -r requirements.txt
```

Expected: semua package terinstall tanpa error.

- [ ] **Step 4: Buat .gitignore**

```
C:\Financehub\app\.gitignore
```

```
__pycache__/
*.pyc
*.pyo
finance_hub.db
*.db-shm
*.db-wal
.env
venv/
*.egg-info/
dist/
build/
```

- [ ] **Step 5: Buat semua __init__.py kosong**

```bash
type nul > auth\__init__.py
type nul > modules\__init__.py
type nul > modules\dashboard\__init__.py
```

- [ ] **Step 6: Init git repo**

```bash
cd C:\Financehub
git init
git add app/requirements.txt app/.gitignore app/auth/__init__.py app/modules/__init__.py app/modules/dashboard/__init__.py
git commit -m "chore: project scaffold — folder structure + dependencies"
```

---

## Task 2: config.py

**Files:**
- Create: `C:\Financehub\app\config.py`

- [ ] **Step 1: Tulis config.py**

```python
# C:\Financehub\app\config.py
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "finance_hub.db")

# JWT — generate secret sekali, atau set via env var FH_JWT_SECRET
JWT_SECRET       = os.environ.get("FH_JWT_SECRET", secrets.token_hex(32))
JWT_ACCESS_HOURS = 1
JWT_REFRESH_DAYS = 7

# Flask session secret
FLASK_SECRET = os.environ.get("FH_SECRET", secrets.token_hex(32))

ADMIN_DEFAULT_PASSWORD = "Admin@123"

COMPANIES = [
    {"id": 1, "code": "SMT", "name": "Sinar Mas Tjipta"},
    {"id": 2, "code": "ETF", "name": "Eka Tjipta Foundation"},
]

# ── Beasiswa lookup values ───────────────────────────────────────────
JENJANG = ["SD/SMP/SMA", "S1", "S2", "S3", "SETF"]

PROGRAM = [
    "Kejaksaan", "Kejaksaan LN", "Polri", "Special Case",
    "Special Cases LN", "Tjipta Siswa Mandiri", "Bank Sinarmas",
    "IKPP", "SMART", "Tjipta Bangun Desa", "IKPP - Tjipta Bangun Desa",
    "Soci Mas", "SMMA", "Sahabat ETF", "Tjipta Sarjana Mandiri",
]

STATUS_SISWA = ["Aktif", "lulus", "gugur", "undur diri"]

PILLAR = ["AGRI", "APP", "Finance", "Mining", "Property", "ENERGY & FINANCE"]

CAT1_BGT = [
    "By Pendidikan", "By Tunjangan", "By Penelitian", "By Pendaftaran",
    "By Ujian", "By Matrikulasi", "By Daftar Ulang", "By Gedung",
    "By Wisuda", "By Orientasi", "By Registrasi", "Kelas Afirmasi",
    "Test TOEFL", "Test Kemampuan Akademik (TKA)", "By Uang Pangkal",
    "By Tugas Akhir", "By Seragam", "By Kegiatan", "By Akomodasi",
    "By Kemahasiswaan", "By Sumbangan Pembangunan", "Rawat Inap",
    "Rawat Jalan", "Tahap 1", "Tahap 2", "Tahap 3",
    "Test TPDA", "Uang Pengembangan Institusi (IPI)",
    "By Ujian Kualifikasi", "Test Kemampuan Bahasa Inggris",
    "By Medical", "By Claim Medical",
]

CAT2_SEM = [
    "Semester 1", "Semester 2", "Semester 3", "Semester 4", "Semester 5",
    "Semester 6", "Semester 7", "Semester 8", "Semester 9", "Semester 10",
    "Tahap 1", "Tahap 2", "Tahap 3",
]

KODE_JENJANG = {
    "S1": "1", "S2": "2", "S3": "3",
    "SD/SMP/SMA": "4", "SD/SMA/SMA": "4", "SETF": "5",
}

PERUSAHAAN = [
    "PT. Aditunggal Mahajaya", "PT. Agrokarya Primalestari", "AGROLESTARI MANDIRI",
    "PT. Agrolestari Sentosa", "BAHANA KARYA SEMESTA", "BANGUN NUSA MANDIRI",
    "Bank", "PT. Binasawit Abadi Pratama", "BORNEO INDOBARA", "BUANA ADHITAMA",
    "PT. Buana Artha Sejahtera", "PT. Buana Wiralestari Mas", "PT. Bumi Permai Lestari",
    "BUMI SAWIT PERMAI", "BUMIPALMA LESTARIPERSADA", "CAHAYANUSA GEMILANG",
    "Cipta Kridatama", "PT. Djuandasawit Lestari", "DSS", "PT. Forestalestari Dwikarya",
    "Gems", "IKPP", "In Progress Allocation (AGRI)", "PT. Ivo Mas Tunggal",
    "KARTIKA PRIMA CIPTA", "KENCANA GRAHA PERMAI", "PT. Kresna Duta Agroindo",
    "KRUING LESTARI JAYA", "LONTAR PAPYRUS", "MANTAP ANDALAN UNGGUL",
    "PT. Maskapai Perkebunan Leidong West Indonesia", "MEGANUSA INTISAWIT",
    "PT. Mitrakarya Agroindo", "PT. Paramitra Internusa Pratama", "PERSADA GRAHA MANDIRI",
    "PRIMASENTOSA PRATAMAPUTRA", "PRISMA CIPTA MANDIRI", "PT. Berau Coal",
    "PT. Ramajaya Pramukti", "SATYA KISMA USAHA", "SAWIT MAS SEJAHTERA",
    "PT. Sawitakarya Manunggul", "Sekuritas", "SINAR KENCANA INTI PERKASA",
    "SINAR MAS MULTIARTHA", "PT. SMART Tbk", "SML", "PT. Sumber Indah Perkasa",
    "PT. Tapian Nadenggan",
]

COST_CENTER_MAP = {
    "PT. Forestalestari Dwikarya":                    "2901C1POFF",
    "PT. Ivo Mas Tunggal":                            "1901C1POFF",
    "PT. Maskapai Perkebunan Leidong West Indonesia": "1201C1POFF",
    "PT. Mitrakarya Agroindo":                        "3801C1POFF",
    "PT. Agrokarya Primalestari":                     "4401C1POFF",
    "PT. Agrolestari Sentosa":                        "4201C1POFF",
    "PT. Binasawit Abadi Pratama":                    "3201C1POFF",
    "PT. Buana Artha Sejahtera":                      "4501C1POFF",
    "PT. Buana Wiralestari Mas":                      "2001C1POFF",
    "PT. Bumi Permai Lestari":                        "2601C1POFF",
    "PT. Djuandasawit Lestari":                       "2801C1POFF",
    "PT. Paramitra Internusa Pratama":                "4701C1POFF",
    "PT. Ramajaya Pramukti":                          "2101C1POFF",
    "PT. Sawitakarya Manunggul":                      "3401C1POFF",
    "PT. SMART Tbk":                                  "1008C1POFF",
    "PT. Aditunggal Mahajaya":                        "5101C1POFF",
    "PT. Kresna Duta Agroindo":                       "1101C1POFF",
    "PT. Tapian Nadenggan":                           "1401C1POFF",
    "PT. Sumber Indah Perkasa":                       "2501C1CMOF",
}
```

- [ ] **Step 2: Commit**

```bash
git add app/config.py
git commit -m "feat: config.py — DB path, JWT config, Beasiswa constants"
```

---

## Task 3: database.py

**Files:**
- Create: `C:\Financehub\app\database.py`
- Test: `C:\Financehub\app\tests\test_database.py`

- [ ] **Step 1: Tulis test dulu**

```python
# C:\Financehub\app\tests\test_database.py
import os
import sqlite3
import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override DB_PATH ke test database sebelum import
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn

@pytest.fixture(autouse=True)
def clean_db():
    """Hapus test DB sebelum setiap test."""
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def test_init_db_creates_tables():
    init_db()
    conn = get_conn()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "companies" in tables
    assert "users" in tables
    assert "siswa" in tables
    assert "budget_beasiswa" in tables
    assert "payment_beasiswa" in tables
    assert "payment_memo" in tables
    assert "payment_memo_items" in tables
    assert "payment_application" in tables
    assert "refresh_tokens" in tables

def test_init_db_seeds_companies():
    init_db()
    conn = get_conn()
    rows = conn.execute("SELECT code FROM companies ORDER BY id").fetchall()
    conn.close()
    codes = [r["code"] for r in rows]
    assert codes == ["SMT", "ETF"]

def test_init_db_creates_admin_user():
    init_db()
    conn = get_conn()
    row = conn.execute("SELECT username, role, must_change_pw FROM users WHERE username='admin'").fetchone()
    conn.close()
    assert row is not None
    assert row["role"] == "releaser"
    assert row["must_change_pw"] == 1

def test_init_db_idempotent():
    init_db()
    init_db()  # Tidak boleh error atau duplicate
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    conn.close()
    assert count == 2
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
cd C:\Financehub\app
pytest tests/test_database.py -v
```

Expected: `ERROR` — ModuleNotFoundError: No module named 'database'

- [ ] **Step 3: Tulis database.py**

```python
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
"""

def get_conn():
    """Return SQLite connection dengan row_factory dan WAL mode."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    """Create semua tabel dan seed data awal. Idempotent."""
    conn = get_conn()
    conn.executescript(DDL)

    # Seed companies
    for c in config.COMPANIES:
        conn.execute(
            "INSERT OR IGNORE INTO companies (id, code, name) VALUES (?, ?, ?)",
            (c["id"], c["code"], c["name"])
        )

    # Seed admin user (hanya jika belum ada)
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

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
```

- [ ] **Step 4: Jalankan test — pastikan PASS**

```bash
cd C:\Financehub\app
pytest tests/test_database.py -v
```

Expected:
```
PASSED tests/test_database.py::test_init_db_creates_tables
PASSED tests/test_database.py::test_init_db_seeds_companies
PASSED tests/test_database.py::test_init_db_creates_admin_user
PASSED tests/test_database.py::test_init_db_idempotent
4 passed
```

- [ ] **Step 5: Commit**

```bash
git add app/database.py app/tests/test_database.py
git commit -m "feat: database.py — SQLite DDL, init_db, seed companies + admin"
```

---

## Task 4: Auth Module

**Files:**
- Create: `C:\Financehub\app\auth\routes.py`
- Create: `C:\Financehub\app\auth\middleware.py`
- Test: `C:\Financehub\app\tests\test_auth.py`

- [ ] **Step 1: Tulis auth/middleware.py**

```python
# C:\Financehub\app\auth\middleware.py
from functools import wraps
from flask import jsonify, redirect, url_for, session
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def jwt_html_required(f):
    """Untuk HTML routes — redirect ke /auth/login jika token tidak ada/invalid."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    """Decorator untuk API routes — return 403 JSON jika role tidak diizinkan."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({"ok": False, "pesan": "Token tidak valid atau expired."}), 401
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"ok": False, "pesan": "Akses ditolak."}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def html_role_required(*roles):
    """Untuk HTML routes dengan role check — redirect ke dashboard jika role tidak sesuai."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return redirect(url_for("auth.login_page"))
            claims = get_jwt()
            if claims.get("role") not in roles:
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator
```

- [ ] **Step 2: Tulis auth/routes.py**

```python
# C:\Financehub\app\auth\routes.py
import hashlib
from datetime import datetime, timedelta

import bcrypt
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

import config
from database import get_conn

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "pesan": "Username dan password wajib diisi."})

    conn = get_conn()
    row  = conn.execute(
        "SELECT id, password_hash, role, is_active, must_change_pw "
        "FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if row is None or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        conn.close()
        return jsonify({"ok": False, "pesan": "Username atau password salah."})

    if not row["is_active"]:
        conn.close()
        return jsonify({"ok": False, "pesan": "Akun tidak aktif. Hubungi admin."})

    conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now().isoformat(), row["id"]),
    )

    additional   = {"username": username, "role": row["role"]}
    access_token = create_access_token(identity=str(row["id"]), additional_claims=additional)
    refresh_token = create_refresh_token(identity=str(row["id"]), additional_claims=additional)

    # Simpan hash refresh token ke DB untuk revocation
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at = (datetime.now() + timedelta(days=config.JWT_REFRESH_DAYS)).isoformat()
    conn.execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (row["id"], token_hash, expires_at),
    )
    conn.commit()
    conn.close()

    resp = jsonify({
        "ok":           True,
        "must_change_pw": bool(row["must_change_pw"]),
        "role":         row["role"],
    })
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    data          = request.get_json(force=True) or {}
    refresh_token = data.get("refresh_token", "")
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        conn = get_conn()
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?",
            (token_hash,),
        )
        conn.commit()
        conn.close()
    resp = jsonify({"ok": True})
    unset_jwt_cookies(resp)
    return resp


@bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    data          = request.get_json(force=True) or {}
    refresh_token = data.get("refresh_token", "")
    token_hash    = hashlib.sha256(refresh_token.encode()).hexdigest()
    conn          = get_conn()
    row           = conn.execute(
        "SELECT id, revoked FROM refresh_tokens WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    conn.close()

    if row is None or row["revoked"]:
        return jsonify({"ok": False, "pesan": "Refresh token tidak valid."}), 401

    claims       = get_jwt()
    access_token = create_access_token(
        identity=get_jwt_identity(),
        additional_claims={"username": claims["username"], "role": claims["role"]},
    )
    resp = jsonify({"ok": True})
    set_access_cookies(resp, access_token)
    return resp


@bp.route("/change-password", methods=["GET"])
def change_password_page():
    return render_template("change_password.html")


@bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    data    = request.get_json(force=True)
    old_pw  = data.get("old_password", "")
    new_pw  = data.get("new_password", "")

    if len(new_pw) < 8:
        return jsonify({"ok": False, "pesan": "Password baru minimal 8 karakter."})

    conn = get_conn()
    row  = conn.execute(
        "SELECT password_hash FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not bcrypt.checkpw(old_pw.encode(), row["password_hash"].encode()):
        conn.close()
        return jsonify({"ok": False, "pesan": "Password lama salah."})

    if bcrypt.checkpw(new_pw.encode(), row["password_hash"].encode()):
        conn.close()
        return jsonify({"ok": False, "pesan": "Password baru tidak boleh sama dengan password lama."})

    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt(12)).decode()
    conn.execute(
        "UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE id = ?",
        (new_hash, user_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "pesan": "Password berhasil diubah."})
```

- [ ] **Step 3: Tulis tests/conftest.py**

```python
# C:\Financehub\app\tests\conftest.py
import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from app import create_app

@pytest.fixture
def app():
    application = create_app(testing=True)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    from database import init_db
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
```

- [ ] **Step 4: Tulis tests/test_auth.py**

```python
# C:\Financehub\app\tests\test_auth.py
import json

def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})

def test_login_success(client):
    resp = login(client)
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["must_change_pw"] is True
    assert data["role"] == "releaser"

def test_login_wrong_password(client):
    resp = login(client, password="wrong")
    data = resp.get_json()
    assert data["ok"] is False
    assert "salah" in data["pesan"].lower()

def test_login_unknown_user(client):
    resp = login(client, username="ghost")
    data = resp.get_json()
    assert data["ok"] is False

def test_change_password_success(client):
    login(client)
    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "NewPass@456"
    })
    data = resp.get_json()
    assert data["ok"] is True

def test_change_password_too_short(client):
    login(client)
    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "short"
    })
    data = resp.get_json()
    assert data["ok"] is False
    assert "8 karakter" in data["pesan"]

def test_change_password_same_as_old(client):
    login(client)
    resp = client.post("/auth/change-password", json={
        "old_password": "Admin@123",
        "new_password": "Admin@123"
    })
    data = resp.get_json()
    assert data["ok"] is False

def test_logout(client):
    login(client)
    resp = client.post("/auth/logout", json={})
    data = resp.get_json()
    assert data["ok"] is True
```

- [ ] **Step 5: Buat app.py sementara (minimal untuk test auth berjalan)**

```python
# C:\Financehub\app\app.py
from datetime import timedelta
from flask import Flask, redirect, url_for
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import config
from database import init_db

def create_app(testing=False):
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"]            = config.JWT_SECRET
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = timedelta(hours=config.JWT_ACCESS_HOURS)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=config.JWT_REFRESH_DAYS)
    app.config["JWT_TOKEN_LOCATION"]        = ["headers", "cookies"]
    app.config["JWT_COOKIE_SECURE"]         = False
    app.config["JWT_COOKIE_CSRF_PROTECT"]   = False
    app.config["JWT_ACCESS_COOKIE_NAME"]    = "fh_access"
    app.config["JWT_REFRESH_COOKIE_NAME"]   = "fh_refresh"
    app.config["SECRET_KEY"]               = config.FLASK_SECRET
    app.config["TESTING"]                  = testing

    JWTManager(app)
    CORS(app, supports_credentials=True)

    from auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/")
    def index():
        return redirect(url_for("auth.login_page"))

    if not testing:
        init_db()
    return app

if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=8080, debug=True)
```

- [ ] **Step 6: Jalankan test auth — pastikan PASS**

```bash
cd C:\Financehub\app
pytest tests/test_auth.py -v
```

Expected:
```
PASSED tests/test_auth.py::test_login_success
PASSED tests/test_auth.py::test_login_wrong_password
PASSED tests/test_auth.py::test_login_unknown_user
PASSED tests/test_auth.py::test_change_password_success
PASSED tests/test_auth.py::test_change_password_too_short
PASSED tests/test_auth.py::test_change_password_same_as_old
PASSED tests/test_auth.py::test_logout
7 passed
```

- [ ] **Step 7: Commit**

```bash
git add app/auth/routes.py app/auth/middleware.py app/app.py app/tests/conftest.py app/tests/test_auth.py
git commit -m "feat: auth module — login, logout, refresh, change-password + JWT cookie"
```

---

## Task 5: Base Templates + Static Files

**Files:**
- Create: `C:\Financehub\app\templates\base.html`
- Create: `C:\Financehub\app\templates\login.html`
- Create: `C:\Financehub\app\templates\change_password.html`
- Create: `C:\Financehub\app\static\css\style.css`
- Create: `C:\Financehub\app\static\js\app.js`

- [ ] **Step 1: Tulis static/css/style.css**

```css
/* C:\Financehub\app\static\css\style.css */
:root {
  --primary: #1a56db;
  --primary-dark: #1e429f;
  --success: #0e9f6e;
  --danger: #e02424;
  --warning: #c27803;
  --bg: #f3f4f6;
  --card: #ffffff;
  --border: #e5e7eb;
  --text: #111827;
  --text-muted: #6b7280;
  --sidebar-w: 220px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
}

/* ── Navbar ── */
.navbar {
  position: fixed; top: 0; left: 0; right: 0; height: 56px;
  background: var(--primary); color: #fff;
  display: flex; align-items: center; padding: 0 1.5rem;
  gap: 1rem; z-index: 100; box-shadow: 0 1px 4px rgba(0,0,0,.2);
}
.navbar-brand { font-weight: 700; font-size: 1.1rem; text-decoration: none; color: #fff; }
.navbar-company { margin-left: auto; font-size: .85rem; opacity: .9; cursor: pointer; }
.navbar-company:hover { opacity: 1; text-decoration: underline; }
.navbar-user { font-size: .85rem; opacity: .9; }
.btn-logout {
  background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
  color: #fff; padding: .25rem .75rem; border-radius: 4px; cursor: pointer; font-size: .8rem;
}
.btn-logout:hover { background: rgba(255,255,255,.25); }

/* ── Sidebar ── */
.layout { display: flex; margin-top: 56px; min-height: calc(100vh - 56px); }

.sidebar {
  width: var(--sidebar-w); background: #1e293b; color: #94a3b8;
  position: fixed; top: 56px; bottom: 0; left: 0;
  overflow-y: auto; padding: 1rem 0;
}
.sidebar-section { padding: .5rem 1rem; font-size: .7rem; text-transform: uppercase;
  letter-spacing: .05em; color: #64748b; margin-top: .5rem; }
.sidebar a {
  display: flex; align-items: center; gap: .5rem;
  padding: .5rem 1.25rem; color: #94a3b8; text-decoration: none;
  font-size: .875rem; transition: background .15s;
}
.sidebar a:hover, .sidebar a.active { background: #334155; color: #f1f5f9; }
.sidebar a.coming-soon { opacity: .45; cursor: default; pointer-events: none; }

/* ── Main content ── */
.main { margin-left: var(--sidebar-w); flex: 1; padding: 1.5rem; }

/* ── Cards ── */
.card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;
}
.card-title { font-size: 1rem; font-weight: 600; margin-bottom: 1rem; }

/* ── Buttons ── */
.btn {
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .45rem .9rem; border-radius: 6px; border: none;
  cursor: pointer; font-size: .875rem; font-weight: 500; transition: filter .15s;
}
.btn:hover { filter: brightness(.92); }
.btn-primary   { background: var(--primary); color: #fff; }
.btn-success   { background: var(--success); color: #fff; }
.btn-danger    { background: var(--danger);  color: #fff; }
.btn-secondary { background: #e5e7eb; color: #374151; }
.btn-sm { padding: .25rem .6rem; font-size: .8rem; }

/* ── Tables ── */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { background: #f8fafc; font-weight: 600; font-size: .8rem;
  text-transform: uppercase; letter-spacing: .03em; }
th, td { padding: .55rem .75rem; border-bottom: 1px solid var(--border); text-align: left; }
tr:hover td { background: #f8fafc; }

/* ── Forms ── */
.form-group { margin-bottom: .875rem; }
.form-group label { display: block; font-size: .8rem; font-weight: 500; margin-bottom: .3rem; color: #374151; }
input, select, textarea {
  width: 100%; padding: .45rem .65rem; border: 1px solid var(--border);
  border-radius: 6px; font-size: .875rem; background: #fff;
}
input:focus, select:focus, textarea:focus {
  outline: none; border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(26,86,219,.12);
}

/* ── Badges ── */
.badge { display: inline-block; padding: .15rem .5rem; border-radius: 9999px; font-size: .75rem; font-weight: 500; }
.badge-green  { background: #d1fae5; color: #065f46; }
.badge-red    { background: #fee2e2; color: #991b1b; }
.badge-yellow { background: #fef3c7; color: #92400e; }
.badge-blue   { background: #dbeafe; color: #1e40af; }
.badge-gray   { background: #f3f4f6; color: #374151; }

/* ── Stats cards ── */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
.stat-label { font-size: .75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .04em; }
.stat-value { font-size: 1.5rem; font-weight: 700; margin-top: .25rem; }

/* ── Alert ── */
.alert { padding: .75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: .875rem; }
.alert-danger  { background: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; }
.alert-success { background: #d1fae5; border: 1px solid #6ee7b7; color: #065f46; }

/* ── Login page ── */
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); }
.login-card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 2.5rem; width: 360px; box-shadow: 0 4px 20px rgba(0,0,0,.08); }
.login-logo { font-size: 1.5rem; font-weight: 700; color: var(--primary); text-align: center; margin-bottom: .5rem; }
.login-sub  { color: var(--text-muted); text-align: center; font-size: .85rem; margin-bottom: 1.5rem; }

/* ── Coming soon ── */
.coming-soon-wrap { text-align: center; padding: 4rem 2rem; }
.coming-soon-icon { font-size: 3rem; margin-bottom: 1rem; }
.coming-soon-title { font-size: 1.5rem; font-weight: 700; margin-bottom: .5rem; }
.coming-soon-sub { color: var(--text-muted); }

/* ── Tabs ── */
.tabs { display: flex; gap: 0; border-bottom: 2px solid var(--border); margin-bottom: 1.25rem; }
.tab-btn {
  padding: .6rem 1.2rem; border: none; background: none; cursor: pointer;
  font-size: .875rem; color: var(--text-muted); border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* ── Number formatting ── */
.num-right { text-align: right; font-variant-numeric: tabular-nums; }

/* ── Modal ── */
.modal-overlay {
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,.45);
  z-index: 200; align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal {
  background: #fff; border-radius: 10px; padding: 1.5rem;
  width: min(540px, 95vw); max-height: 90vh; overflow-y: auto;
  box-shadow: 0 8px 30px rgba(0,0,0,.15);
}
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.modal-title { font-weight: 600; font-size: 1rem; }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--text-muted); }
```

- [ ] **Step 2: Tulis static/js/app.js**

```javascript
// C:\Financehub\app\static\js\app.js

// ── Fetch helper yang otomatis kirim cookie ──────────────────────────
async function apiFetch(url, options = {}) {
  const defaults = {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  };
  const resp = await fetch(url, { ...defaults, ...options });
  if (resp.status === 401) {
    // Token expired — coba refresh
    const refreshed = await tryRefresh();
    if (refreshed) {
      return fetch(url, { ...defaults, ...options });
    }
    window.location.href = "/auth/login";
    return null;
  }
  return resp;
}

async function tryRefresh() {
  const resp = await fetch("/auth/refresh", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return resp.ok;
}

// ── Logout ───────────────────────────────────────────────────────────
function doLogout() {
  apiFetch("/auth/logout", { method: "POST", body: JSON.stringify({}) })
    .then(() => { window.location.href = "/auth/login"; });
}

// ── Tab switching ─────────────────────────────────────────────────────
function initTabs(container) {
  const tabs = container.querySelectorAll(".tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
    });
  });
  if (tabs.length > 0) tabs[0].click();
}

// ── Number formatting ─────────────────────────────────────────────────
function fmtRupiah(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

// ── Toast notification ────────────────────────────────────────────────
function showToast(msg, type = "success") {
  let toast = document.getElementById("fh-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "fh-toast";
    toast.style.cssText = `
      position:fixed; bottom:1.5rem; right:1.5rem; z-index:9999;
      padding:.75rem 1.25rem; border-radius:8px; font-size:.875rem;
      box-shadow:0 4px 12px rgba(0,0,0,.15); transition:opacity .3s;
      max-width:360px;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.background = type === "success" ? "#065f46" : "#991b1b";
  toast.style.color = "#fff";
  toast.style.opacity = "1";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = "0"; }, 3000);
}

// ── Modal helpers ─────────────────────────────────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("open");
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("open");
}

document.addEventListener("DOMContentLoaded", () => {
  // Init semua tab containers
  document.querySelectorAll("[data-tabs]").forEach(initTabs);
  // Close modal on overlay click
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => {
      if (e.target === overlay) overlay.classList.remove("open");
    });
  });
});
```

- [ ] **Step 3: Tulis templates/base.html**

```html
<!-- C:\Financehub\app\templates\base.html -->
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Finance Hub{% endblock %} — Finance Hub</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  {% block head %}{% endblock %}
</head>
<body>

<nav class="navbar">
  <a class="navbar-brand" href="/">⚡ Finance Hub</a>
  {% if company_name %}
  <a class="navbar-company" href="/select-company" title="Ganti perusahaan">
    🏢 {{ company_name }}
  </a>
  {% endif %}
  <span class="navbar-user">👤 {{ current_user or 'user' }}</span>
  <button class="btn-logout" onclick="doLogout()">Keluar</button>
</nav>

<div class="layout">
  <aside class="sidebar">
    {% set co = company_code or '' %}
    <div class="sidebar-section">Navigasi</div>
    <a href="/dashboard" {% if active_page == 'dashboard' %}class="active"{% endif %}>🏠 Dashboard</a>

    {% if co == 'ETF' %}
    <div class="sidebar-section">ETF</div>
    <a href="/beasiswa" {% if active_page == 'beasiswa' %}class="active"{% endif %}>🎓 Beasiswa</a>
    {% endif %}

    {% if co == 'SMT' %}
    <div class="sidebar-section">SMT</div>
    {% endif %}

    <div class="sidebar-section">Pembayaran</div>
    <a href="/payment-memo" {% if active_page == 'payment_memo' %}class="active"{% endif %}>📋 Payment Memo</a>
    <a href="/payment-application" {% if active_page == 'payment_app' %}class="active"{% endif %}>📊 Payment Application</a>

    <div class="sidebar-section">Coming Soon</div>
    <a class="coming-soon">🏦 Bank</a>
    <a class="coming-soon">💳 Account Payable</a>
    <a class="coming-soon">💰 Advance</a>
    <a class="coming-soon">🏧 Petty Cash</a>
    <a class="coming-soon">🤝 Sponsorship</a>

    {% if current_role == 'releaser' %}
    <div class="sidebar-section">Admin</div>
    <a href="/users" {% if active_page == 'users' %}class="active"{% endif %}>👥 User Management</a>
    {% endif %}
  </aside>

  <main class="main">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="alert alert-{{ category }}">{{ message }}</div>
      {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
</div>

<script src="{{ url_for('static', filename='js/app.js') }}"></script>
{% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: Tulis templates/login.html**

```html
<!-- C:\Financehub\app\templates\login.html -->
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login — Finance Hub</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">⚡ Finance Hub</div>
    <div class="login-sub">Internal Financial Management</div>

    <div id="login-error" class="alert alert-danger" style="display:none"></div>

    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" placeholder="Username" autocomplete="username">
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" placeholder="Password" autocomplete="current-password">
    </div>
    <button class="btn btn-primary" style="width:100%" onclick="doLogin()">Masuk</button>
  </div>
</div>

<script>
async function doLogin() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const errEl    = document.getElementById("login-error");
  errEl.style.display = "none";

  if (!username || !password) {
    errEl.textContent = "Username dan password wajib diisi.";
    errEl.style.display = "block";
    return;
  }

  const resp = await fetch("/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await resp.json();

  if (!data.ok) {
    errEl.textContent = data.pesan;
    errEl.style.display = "block";
    return;
  }

  if (data.must_change_pw) {
    window.location.href = "/auth/change-password";
  } else {
    window.location.href = "/select-company";
  }
}

document.getElementById("password").addEventListener("keydown", e => {
  if (e.key === "Enter") doLogin();
});
</script>
</body>
</html>
```

- [ ] **Step 5: Tulis templates/change_password.html**

```html
<!-- C:\Financehub\app\templates\change_password.html -->
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Ganti Password — Finance Hub</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">🔐 Ganti Password</div>
    <div class="login-sub">Wajib ganti password sebelum melanjutkan</div>

    <div id="pw-error"   class="alert alert-danger"  style="display:none"></div>
    <div id="pw-success" class="alert alert-success" style="display:none"></div>

    <div class="form-group">
      <label>Password Lama</label>
      <input type="password" id="old_pw" placeholder="Password saat ini">
    </div>
    <div class="form-group">
      <label>Password Baru</label>
      <input type="password" id="new_pw" placeholder="Minimal 8 karakter">
    </div>
    <div class="form-group">
      <label>Konfirmasi Password Baru</label>
      <input type="password" id="confirm_pw" placeholder="Ulangi password baru">
    </div>
    <button class="btn btn-primary" style="width:100%" onclick="doChangePw()">Simpan Password Baru</button>
  </div>
</div>
<script>
async function doChangePw() {
  const old_pw    = document.getElementById("old_pw").value;
  const new_pw    = document.getElementById("new_pw").value;
  const confirm   = document.getElementById("confirm_pw").value;
  const errEl     = document.getElementById("pw-error");
  const successEl = document.getElementById("pw-success");
  errEl.style.display = successEl.style.display = "none";

  if (new_pw !== confirm) {
    errEl.textContent = "Konfirmasi password tidak sama.";
    errEl.style.display = "block"; return;
  }
  const resp = await fetch("/auth/change-password", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_password: old_pw, new_password: new_pw }),
  });
  const data = await resp.json();
  if (!data.ok) {
    errEl.textContent = data.pesan; errEl.style.display = "block";
  } else {
    successEl.textContent = "Password berhasil diubah. Mengalihkan...";
    successEl.style.display = "block";
    setTimeout(() => { window.location.href = "/select-company"; }, 1500);
  }
}
</script>
</body>
</html>
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/ app/static/
git commit -m "feat: base templates + CSS + JS utilities"
```

---

## Task 6: Dashboard Module + Company Select

**Files:**
- Create: `C:\Financehub\app\modules\dashboard\routes.py`
- Create: `C:\Financehub\app\templates\company_select.html`
- Create: `C:\Financehub\app\templates\dashboard\index.html`
- Test: `C:\Financehub\app\tests\test_dashboard.py`

- [ ] **Step 1: Tulis modules/dashboard/routes.py**

```python
# C:\Financehub\app\modules\dashboard\routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required
from database import get_conn
import config

bp = Blueprint("dashboard", __name__)


def get_ctx():
    """Helper — return dict context dari JWT claims + session untuk semua template."""
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/select-company")
@jwt_html_required
def select_company():
    return render_template(
        "company_select.html",
        companies=config.COMPANIES,
        **get_ctx()
    )


@bp.route("/select-company", methods=["POST"])
@jwt_html_required
def select_company_post():
    company_id = request.form.get("company_id")
    chosen = next((c for c in config.COMPANIES if str(c["id"]) == str(company_id)), None)
    if not chosen:
        return redirect(url_for("dashboard.select_company"))
    session["company_id"]   = chosen["id"]
    session["company_code"] = chosen["code"]
    session["company_name"] = chosen["name"]
    return redirect(url_for("dashboard.index"))


@bp.route("/dashboard")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))

    conn       = get_conn()
    company_id = session["company_id"]

    stats = {}
    if session.get("company_code") == "ETF":
        stats["total_siswa"]  = conn.execute(
            "SELECT COUNT(*) FROM siswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["siswa_aktif"]  = conn.execute(
            "SELECT COUNT(*) FROM siswa WHERE company_id = ? AND status = 'Aktif'",
            (company_id,)
        ).fetchone()[0]
        stats["total_budget"] = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM budget_beasiswa WHERE company_id = ?",
            (company_id,)
        ).fetchone()[0]
        stats["total_payment"] = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_beasiswa WHERE company_id = ?",
            (company_id,)
        ).fetchone()[0]

    stats["total_memo"] = conn.execute(
        "SELECT COUNT(*) FROM payment_memo WHERE company_id = ?", (company_id,)
    ).fetchone()[0]
    stats["memo_draft"] = conn.execute(
        "SELECT COUNT(*) FROM payment_memo WHERE company_id = ? AND status = 'draft'",
        (company_id,)
    ).fetchone()[0]
    conn.close()

    return render_template(
        "dashboard/index.html",
        stats=stats,
        active_page="dashboard",
        **get_ctx()
    )
```

- [ ] **Step 2: Tulis templates/company_select.html**

```html
<!-- C:\Financehub\app\templates\company_select.html -->
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Pilih Perusahaan — Finance Hub</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  <style>
    .select-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); }
    .company-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-top: 1.5rem; }
    .company-card {
      background: #fff; border: 2px solid var(--border); border-radius: 12px;
      padding: 2rem 1.5rem; text-align: center; cursor: pointer;
      transition: border-color .2s, box-shadow .2s; text-decoration: none; color: var(--text);
    }
    .company-card:hover { border-color: var(--primary); box-shadow: 0 4px 16px rgba(26,86,219,.15); }
    .company-icon { font-size: 2.5rem; margin-bottom: .75rem; }
    .company-name { font-size: 1rem; font-weight: 600; }
    .company-code { font-size: .8rem; color: var(--text-muted); margin-top: .25rem; }
  </style>
</head>
<body>
<div class="select-wrap">
  <div style="width:min(520px, 95vw)">
    <div class="login-logo">⚡ Finance Hub</div>
    <div class="login-sub" style="margin-bottom:1.5rem">Pilih perusahaan yang akan dikelola</div>
    <form method="POST" action="/select-company">
      <div class="company-grid">
        {% for c in companies %}
        <button type="submit" name="company_id" value="{{ c.id }}" class="company-card">
          <div class="company-icon">🏢</div>
          <div class="company-name">{{ c.name }}</div>
          <div class="company-code">{{ c.code }}</div>
        </button>
        {% endfor %}
      </div>
    </form>
  </div>
</div>
</body>
</html>
```

- [ ] **Step 3: Tulis templates/dashboard/index.html**

```html
<!-- C:\Financehub\app\templates\dashboard\index.html -->
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}

{% block content %}
<h1 style="font-size:1.25rem; font-weight:700; margin-bottom:1.25rem">
  Dashboard — {{ company_name }}
</h1>

<div class="stats-grid">
  {% if company_code == 'ETF' %}
  <div class="stat-card">
    <div class="stat-label">Total Siswa</div>
    <div class="stat-value">{{ stats.total_siswa }}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Siswa Aktif</div>
    <div class="stat-value" style="color:var(--success)">{{ stats.siswa_aktif }}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Total Budget</div>
    <div class="stat-value" style="font-size:1.1rem">Rp {{ "{:,.0f}".format(stats.total_budget) }}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Total Payment</div>
    <div class="stat-value" style="font-size:1.1rem">Rp {{ "{:,.0f}".format(stats.total_payment) }}</div>
  </div>
  {% endif %}
  <div class="stat-card">
    <div class="stat-label">Total Memo</div>
    <div class="stat-value">{{ stats.total_memo }}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Memo Draft</div>
    <div class="stat-value" style="color:var(--warning)">{{ stats.memo_draft }}</div>
  </div>
</div>

<div class="card">
  <div class="card-title">Quick Links</div>
  <div style="display:flex; gap:.75rem; flex-wrap:wrap">
    {% if company_code == 'ETF' %}
    <a href="/beasiswa" class="btn btn-primary">🎓 Beasiswa</a>
    {% endif %}
    <a href="/payment-memo" class="btn btn-secondary">📋 Payment Memo</a>
    <a href="/payment-application" class="btn btn-secondary">📊 Payment Application</a>
    {% if current_role == 'releaser' %}
    <a href="/users" class="btn btn-secondary">👥 User Management</a>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Update app.py — register dashboard blueprint**

```python
# C:\Financehub\app\app.py
from datetime import timedelta
from flask import Flask, redirect, url_for
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import config
from database import init_db

def create_app(testing=False):
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"]            = config.JWT_SECRET
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = timedelta(hours=config.JWT_ACCESS_HOURS)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=config.JWT_REFRESH_DAYS)
    app.config["JWT_TOKEN_LOCATION"]        = ["headers", "cookies"]
    app.config["JWT_COOKIE_SECURE"]         = False
    app.config["JWT_COOKIE_CSRF_PROTECT"]   = False
    app.config["JWT_ACCESS_COOKIE_NAME"]    = "fh_access"
    app.config["JWT_REFRESH_COOKIE_NAME"]   = "fh_refresh"
    app.config["SECRET_KEY"]               = config.FLASK_SECRET
    app.config["TESTING"]                  = testing

    JWTManager(app)
    CORS(app, supports_credentials=True)

    from auth.routes import bp as auth_bp
    from modules.dashboard.routes import bp as dashboard_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login_page"))

    if not testing:
        init_db()
    return app

if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=8080, debug=True)
```

- [ ] **Step 5: Tulis tests/test_dashboard.py**

```python
# C:\Financehub\app\tests\test_dashboard.py

def login(client):
    return client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})

def select_etf(client):
    client.post("/select-company", data={"company_id": "2"})

def test_dashboard_redirect_without_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

def test_select_company_page_requires_login(client):
    resp = client.get("/select-company")
    assert resp.status_code == 302

def test_select_company_after_login(client):
    login(client)
    resp = client.get("/select-company")
    assert resp.status_code == 200
    assert b"Pilih" in resp.data

def test_dashboard_after_company_selection(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data

def test_dashboard_shows_etf_stats(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    assert b"Total Siswa" in resp.data
```

- [ ] **Step 6: Jalankan semua test**

```bash
cd C:\Financehub\app
pytest tests/ -v
```

Expected: semua test PASS (12+ tests).

- [ ] **Step 7: Test manual — jalankan app**

```bash
cd C:\Financehub\app
python app.py
```

Buka browser: `http://localhost:8080`
- Harus redirect ke `/auth/login`
- Login dengan `admin` / `Admin@123`
- Harus redirect ke `/auth/change-password`
- Ganti password ke `Admin@2026`
- Harus redirect ke `/select-company`
- Pilih **Eka Tjipta Foundation**
- Harus masuk ke dashboard ETF dengan stats kosong (0)

- [ ] **Step 8: Commit**

```bash
git add app/modules/dashboard/ app/templates/ app/app.py app/tests/test_dashboard.py
git commit -m "feat: dashboard module + company selector + base layout"
```

---

## Task 7: run.py (Waitress Entry Point)

**Files:**
- Create: `C:\Financehub\app\run.py`

- [ ] **Step 1: Tulis run.py**

```python
# C:\Financehub\app\run.py
"""
Entry point untuk production (waitress WSGI server).
Jalankan: python run.py
Akses LAN: http://<IP-laptop>:8080
"""
from waitress import serve
from app import create_app
from database import init_db

if __name__ == "__main__":
    init_db()
    application = create_app()
    print("=" * 50)
    print("  Finance Hub — Production Server")
    print("  http://0.0.0.0:8080")
    print("  Tekan Ctrl+C untuk berhenti")
    print("=" * 50)
    serve(application, host="0.0.0.0", port=8080, threads=4)
```

- [ ] **Step 2: Test run.py berjalan**

```bash
cd C:\Financehub\app
python run.py
```

Expected:
```
==================================================
  Finance Hub — Production Server
  http://0.0.0.0:8080
  Tekan Ctrl+C untuk berhenti
==================================================
```

Buka `http://localhost:8080` — harus bisa login.

- [ ] **Step 3: Commit**

```bash
git add app/run.py
git commit -m "feat: run.py — waitress production server entry point"
```

---

**Part 1 selesai.** Hasil: Flask app berjalan di port 8080 dengan auth JWT, 3 role, company selector, dan dashboard. Lanjut ke Part 2: Beasiswa Module.

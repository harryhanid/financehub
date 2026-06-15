import sqlite3
import pytest


def _make_db(path):
    """DB minimal dengan payment_beasiswa + siswa untuk test sort."""
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE siswa (
        id INTEGER PRIMARY KEY,
        company_id INTEGER, code TEXT, nama TEXT,
        bank TEXT, norek TEXT, namarek TEXT,
        jenjang TEXT, angkatan TEXT, program TEXT,
        universitas TEXT, fakultas TEXT
    )""")
    conn.execute("""CREATE TABLE payment_beasiswa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, siswa_code TEXT, pam TEXT,
        cat1 TEXT, cat2 TEXT, amount REAL DEFAULT 0, tanggal TEXT
    )""")
    conn.execute("""CREATE TABLE budget_beasiswa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, siswa_code TEXT,
        cat1 TEXT, amount REAL DEFAULT 0
    )""")
    # 5 siswa: S3, S2, S1 (x2 — berbeda total), SD/SMP/SMA
    conn.executemany(
        "INSERT INTO siswa VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (1, 1, "S3A", "Siti",  "BCA",    "111", "Siti",  "S3", "2018", "Kimia",  "ITB", "FMIPA"),
            (2, 1, "S2A", "Budi",  "BNI",    "222", "Budi",  "S2", "2019", "Hukum",  "UGM", "FH"),
            (3, 1, "S1A", "Ali",   "Mandiri","333", "Ali",   "S1", "2020", "Teknik", "UI",  "FT"),
            (4, 1, "S1B", "Dani",  "BRI",    "444", "Dani",  "S1", "2021", "Fisika", "UI",  "FMIPA"),
            (5, 1, "SMA", "Eko",   "Mandiri","555", "Eko",   "SD/SMP/SMA", "2022", "-", "SMA N 1", "-"),
        ]
    )
    # Payments — semua PAM-001 company_id=1
    # S3A=4jt, S2A=3jt, S1A=5jt, S1B=8jt, SMA=2jt
    # expected order: S3A, S2A, S1B(8jt), S1A(5jt), SMA
    conn.executemany(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, pam, cat1, amount, tanggal) VALUES (?,?,?,?,?,?)",
        [
            (1, "S3A", "PAM-001", "By Pendidikan", 4_000_000, "2026-01-01"),
            (1, "S2A", "PAM-001", "By Pendidikan", 3_000_000, "2026-01-01"),
            (1, "S1A", "PAM-001", "By Pendidikan", 5_000_000, "2026-01-01"),
            (1, "S1B", "PAM-001", "By Pendidikan", 8_000_000, "2026-01-01"),
            (1, "SMA", "PAM-001", "By Pendidikan", 2_000_000, "2026-01-01"),
        ]
    )
    conn.commit()
    conn.close()
    return path


def _fake_conn_factory(db_path):
    def _conn():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c
    return _conn


# ── get_pam_payments ─────────────────────────────────────────────────────────

def test_get_pam_payments_sorted_by_jenjang(monkeypatch, tmp_path):
    """S3 dulu, lalu S2, lalu S1 (total DESC dalam S1), lalu lainnya."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    rows = svc.get_pam_payments("PAM-001", 1)

    codes = [r["siswa_code"] for r in rows]
    # S3 dulu, S2, lalu S1B (8jt) sebelum S1A (5jt), lalu SMA
    assert codes == ["S3A", "S2A", "S1B", "S1A", "SMA"]


def test_get_pam_payments_jenjang_field_present(monkeypatch, tmp_path):
    """Setiap row harus punya field jenjang."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    rows = svc.get_pam_payments("PAM-001", 1)
    assert all("jenjang" in r for r in rows)


def test_get_pam_payments_empty(monkeypatch, tmp_path):
    """PAM yang tidak ada returns list kosong."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    rows = svc.get_pam_payments("PAM-NOTEXIST", 1)
    assert rows == []


# ── get_pam_payments_detail ───────────────────────────────────────────────────

def test_get_pam_payments_detail_sorted_by_jenjang(monkeypatch, tmp_path):
    """
    result list harus diurutkan: S3 dulu, S2, lalu S1 (total DESC dalam S1), lalu lainnya.
    """
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    result = svc.get_pam_payments_detail("PAM-001", 1)

    codes = [r["siswa_code"] for r in result]
    assert codes == ["S3A", "S2A", "S1B", "S1A", "SMA"]


def test_get_pam_payments_detail_no_renumbered(monkeypatch, tmp_path):
    """Field 'no' harus 1,2,3,4,5 sesuai urutan jenjang, bukan urutan DB."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    result = svc.get_pam_payments_detail("PAM-001", 1)

    nos = [r["no"] for r in result]
    assert nos == [1, 2, 3, 4, 5]


def test_get_pam_payments_detail_empty(monkeypatch, tmp_path):
    """PAM yang tidak ada returns list kosong."""
    db = str(tmp_path / "t.db")
    _make_db(db)
    from app.modules.payment_memo import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db))

    result = svc.get_pam_payments_detail("PAM-NOTEXIST", 1)
    assert result == []

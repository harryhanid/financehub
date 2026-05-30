# C:\Financehub\app\tests\test_database.py
import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn

@pytest.fixture(autouse=True)
def clean_db():
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
    row = conn.execute(
        "SELECT username, role, must_change_pw FROM users WHERE username='admin'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["role"] == "releaser"
    assert row["must_change_pw"] == 1

def test_init_db_idempotent():
    init_db()
    init_db()
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    conn.close()
    assert count == 2

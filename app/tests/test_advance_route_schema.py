# app/tests/test_advance_route_schema.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_advance_schema.db")

from database import init_db, get_conn


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


@pytest.mark.parametrize("table", ["etf_pa_lines", "app_pa_lines", "sml_pa_lines", "setf_pa_lines"])
def test_pa_lines_have_route_column(table):
    conn = get_conn()
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    conn.close()
    assert "route" in cols, f"{table} missing 'route' column"


def test_payment_beasiswa_has_advance_realization_columns():
    conn = get_conn()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(payment_beasiswa)").fetchall()]
    conn.close()
    assert "advance_amount"  in cols
    assert "realized_amount" in cols
    assert "tgl_realisasi"   in cols


def test_migrate_db_idempotent_for_new_columns():
    """Running migrate_db() twice must not raise (columns already exist on 2nd run)."""
    from database import migrate_db
    migrate_db()
    migrate_db()
    conn = get_conn()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(payment_beasiswa)").fetchall()]
    conn.close()
    assert "advance_amount" in cols


@pytest.mark.parametrize("table", ["etf_pa", "app_pa", "sml_pa", "setf_pa"])
def test_pa_header_has_route_column(table):
    conn = get_conn()
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    conn.close()
    assert "route" in cols, f"{table} missing 'route' column"


def test_pa_header_route_defaults_to_gl():
    conn = get_conn()
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (2,'PA/TEST/999/2026','open','2026-07-08T00:00:00')"
    )
    conn.commit()
    row = conn.execute(
        "SELECT route FROM etf_pa WHERE pa_number='PA/TEST/999/2026'"
    ).fetchone()
    conn.close()
    assert row["route"] == "gl"

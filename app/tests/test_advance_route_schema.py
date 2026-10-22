# app/tests/test_advance_route_schema.py
# Skema kini berasal dari migrasi (app/db_migrations, diterapkan sekali per sesi oleh conftest
# fhdb_schema; tiap test dikosongkan oleh clean_db). migrate_db() sudah tidak ada (R18).
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database
from database import get_conn

_SCHEMA_SQL = os.path.join(os.path.dirname(__file__), "..", "db_migrations", "0002_schema.sql")


def _table_ddl(ddl: str, table: str) -> str:
    body = ddl[ddl.index('create table {{schema}}."%s" (' % table):]
    return body[:body.index(");")]


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


def test_schema_migration_defines_advance_columns():
    """Pengganti test 'migrate_db idempoten': kolom advance/route kini didefinisikan di migrasi
    skema (0002_schema.sql), bukan ditambahkan saat runtime, dan migrate_db() sudah dihapus."""
    with open(_SCHEMA_SQL, encoding="utf-8") as f:
        ddl = f.read()
    pb = _table_ddl(ddl, "payment_beasiswa")
    for col in ("advance_amount", "realized_amount", "tgl_realisasi"):
        assert f'"{col}"' in pb, f"payment_beasiswa.{col} tidak ada di 0002_schema.sql"
    for table in ("etf_pa", "app_pa", "sml_pa", "setf_pa",
                  "etf_pa_lines", "app_pa_lines", "sml_pa_lines", "setf_pa_lines"):
        assert '"route"' in _table_ddl(ddl, table), f"{table}.route tidak ada di 0002_schema.sql"
    assert not hasattr(database, "migrate_db")


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

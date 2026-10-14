# tests/test_spt_service.py
import pytest

from database import get_conn
from modules.spt_badan import service as sv


def test_create_and_read_a_period():
    pid = sv.create_period("smt", 2026, "admin", params={"npwp": "123"})
    p = sv.get_period(pid)
    assert (p["entity"], p["tax_year"], p["status"], p["label"]) == ("smt", 2026, "draft", "Simulasi YTD")
    assert p["params"] == {"npwp": "123"} and p["created_by"] == "admin" and p["created_at"]
    assert sv.get_period(999) is None


def test_period_validation_and_uniqueness():
    sv.create_period("smt", 2026, "admin")
    with pytest.raises(ValueError, match="sudah ada"):
        sv.create_period("smt", 2026, "admin")
    with pytest.raises(ValueError, match="Entitas"):
        sv.create_period("etf", 2026, "admin")
    for bad in (1999, 2101, "abc", None):
        with pytest.raises(ValueError, match="Tahun"):
            sv.create_period("smt", bad, "admin")
    assert [p["tax_year"] for p in sv.list_periods()] == [2026]


def test_list_periods_newest_year_first_and_label_is_kept():
    sv.create_period("smt", 2025, "admin", label="Final")
    sv.create_period("smt", 2026, "admin")
    assert [(p["tax_year"], p["label"]) for p in sv.list_periods()] == [(2026, "Simulasi YTD"), (2025, "Final")]


def test_schema_is_created_lazily_and_idempotent():
    conn = get_conn()
    sv.ensure_schema(conn)
    sv.ensure_schema(conn)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"spt_period", "spt_snapshot", "spt_gl_line", "spt_exception", "spt_control"} <= names

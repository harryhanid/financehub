# tests/test_prportal_schema.py -- kolom tambahan untuk integrasi PR Portal (migrasi 0005).
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn

COMPANY_ID = 2  # ETF
PA_PREFIXES = ["etf", "app", "sml", "setf", "energy"]


def _insert_budget():
    conn = get_conn()
    conn.execute(
        "INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, amount) VALUES (?,?,?,?)",
        (COMPANY_ID, "1250001", "By Pendidikan", 1000))
    conn.commit()
    row = conn.execute("SELECT * FROM budget_beasiswa WHERE siswa_code=?", ("1250001",)).fetchone()
    conn.close()
    return row


def test_budget_status_defaults_open():
    assert _insert_budget()["status"] == "open"


def test_budget_status_rejects_unknown():
    row = _insert_budget()
    conn = get_conn()
    with pytest.raises(Exception):
        conn.execute("UPDATE budget_beasiswa SET status='x' WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()
    conn = get_conn()
    for ok in ("on_progress", "complete", "open"):
        conn.execute("UPDATE budget_beasiswa SET status=? WHERE id=?", (ok, row["id"]))
    conn.commit()
    conn.close()


@pytest.mark.parametrize("prefix", PA_PREFIXES)
def test_pa_lines_have_budget_id(prefix):
    from modules.beasiswa.service import add_siswa
    add_siswa(COMPANY_ID, {"code": "1250001", "nama": "Andi", "jenjang": "S1",
        "angkatan": 2025, "program": "SMART", "fakultas": "", "universitas": "",
        "bank": "", "norek": "", "namarek": "", "referensi": "",
        "status": "Aktif", "catatan": ""})
    conn = get_conn()
    siswa_id = conn.execute("SELECT id FROM siswa WHERE code=?", ("1250001",)).fetchone()["id"]
    conn.execute(f"INSERT INTO {prefix}_pa (company_id, pa_number, created_at) VALUES (?,?,?)",
                 (COMPANY_ID, "X-1", "2026-10-27T00:00:00"))
    pa_id = conn.execute(f"SELECT id FROM {prefix}_pa").fetchone()["id"]
    conn.execute(f"INSERT INTO {prefix}_pa_lines (pa_id, student_id) VALUES (?,?)", (pa_id, siswa_id))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {prefix}_pa_lines").fetchone()
    conn.close()
    assert "budget_id" in row.keys()
    assert row["budget_id"] is None


@pytest.mark.parametrize("prefix", PA_PREFIXES)
def test_pa_headers_source_default_flow(prefix):
    conn = get_conn()
    conn.execute(f"INSERT INTO {prefix}_pa (company_id, pa_number, created_at) VALUES (?,?,?)",
                 (COMPANY_ID, "X-1", "2026-10-27T00:00:00"))
    conn.commit()
    row = conn.execute(f"SELECT * FROM {prefix}_pa").fetchone()
    conn.close()
    assert row["source"] == "flow"
    assert row["requested_by"] is None
    assert row["cost_center"] is None

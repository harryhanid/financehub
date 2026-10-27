"""Skrip penandaan awal status budget beasiswa (scripts/pg_migrate/mark_budget_status.py)."""
import importlib.util
import os

import pytest
from openpyxl import load_workbook

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "pg_migrate", "mark_budget_status.py")
_spec = importlib.util.spec_from_file_location("mark_budget_status", _PATH)
mbs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mbs)


def B(id, code="S1", cat1="By Pendidikan", cat2="Semester 1", status="open", amount=1000):
    return {"id": id, "siswa_code": code, "cat1": cat1, "cat2": cat2, "amount": amount, "status": status}


def P(id, status="complete", code="S1", cat1="By Pendidikan", cat2="Semester 1", line=None, pillar="AGRI"):
    return {"id": id, "siswa_code": code, "cat1": cat1, "cat2": cat2, "status": status,
            "etf_pa_line_id": line, "pillar": pillar}


def L(line_id, tbl="etf_pa_lines", code="S1", cat1="By Pendidikan", cat2="Semester 1",
      pa_status="open", budget_id=None):
    return {"table": tbl, "line_id": line_id, "siswa_code": code, "cat1": cat1, "cat2": cat2,
            "pa_status": pa_status, "budget_id": budget_id, "pa_number": "ETF/1"}


AKTIF = {"S1": "Aktif", "S2": "Resign"}


def by_id(res):
    return {r["budget_id"]: r for r in res}


def test_marking_complete_payment():
    r = by_id(mbs.plan_marking([B(1)], [P(10, "complete")], [], AKTIF))
    assert r[1]["status"] == "complete" and r[1]["match_type"] == "payment_complete"
    assert r[1]["match_ref"] == "payment:10"


def test_marking_open_payment_on_progress():
    r = by_id(mbs.plan_marking([B(1)], [P(10, "open")], [], AKTIF))
    assert r[1]["status"] == "on_progress" and r[1]["match_type"] == "payment_open"


def test_marking_pa_line_without_payment():
    lines = [L(5), L(6, pa_status="complete"), L(7, budget_id=99),
             L(8, tbl="app_pa_lines")]  # 8 punya payment (pillar APP, id 8)
    pays = [P(10, "open", code="S2", line=8, pillar="APP")]
    r = by_id(mbs.plan_marking([B(1)], pays, lines, AKTIF))
    assert r[1]["status"] == "on_progress" and r[1]["match_type"] == "pa_line"
    assert r[1]["match_ref"] == "etf_pa_lines:5"


def test_marking_pa_line_payment_link_is_per_table():
    # payment pillar AGRI line 5 tidak menghalangi baris 5 di app_pa_lines
    pays = [P(10, "complete", code="S2", line=5, pillar="AGRI")]
    r = by_id(mbs.plan_marking([B(1)], pays, [L(5, tbl="app_pa_lines")], AKTIF))
    assert r[1]["match_ref"] == "app_pa_lines:5"


def test_marking_more_budget_than_payment_rest_open():
    bs = [B(1), B(2), B(3)]
    r = by_id(mbs.plan_marking(bs, [P(10, "complete")], [L(5)], AKTIF))
    assert [r[i]["status"] for i in (1, 2, 3)] == ["complete", "on_progress", "open"]
    assert r[3]["match_type"] == "none"


def test_marking_non_aktif_unmatched():
    r = by_id(mbs.plan_marking([B(1, code="S2")], [], [], AKTIF))
    assert r[1]["status"] == "open" and r[1]["match_type"] == "siswa_non_aktif"


def test_marking_more_payment_than_budget_ignored():
    r = mbs.plan_marking([B(1)], [P(10), P(11), P(12)], [], AKTIF)
    assert len(r) == 1 and r[0]["match_ref"] == "payment:10"


def test_marking_idempotent():
    bs = [B(1), B(2), B(3)]
    pays, lines = [P(10, "complete")], [L(5)]
    first = mbs.plan_marking(bs, pays, lines, AKTIF)
    # terapkan hasil: status budget berubah, baris PA ber-budget_id
    st = {r["budget_id"]: r["status"] for r in first}
    bs2 = [dict(b, status=st[b["id"]]) for b in bs]
    lines2 = [dict(L(5), budget_id=2)]
    second = mbs.plan_marking(bs2, pays, lines2, AKTIF)
    assert [r["budget_id"] for r in second] == [3]
    assert second[0]["status"] == "open"
    assert mbs.changes(second) == []


def test_marking_keys_are_independent():
    bs = [B(1, cat2="Semester 1"), B(2, cat2="Semester 2")]
    r = by_id(mbs.plan_marking(bs, [P(10, cat2="Semester 2")], [], AKTIF))
    assert r[1]["status"] == "open" and r[2]["status"] == "complete"


def test_rejected_payment_ignored():
    r = by_id(mbs.plan_marking([B(1)], [P(10, "rejected")], [], AKTIF))
    assert r[1]["status"] == "open"


class FakeBackend:
    def __init__(self):
        self.calls = []

    def execute_batch(self, stmts, schema):
        self.calls.append((list(stmts), schema))
        return [{"columns": [], "rows": []} for _ in stmts]

    def close(self):
        pass


def test_cli_refuses_production_write_without_flag(tmp_path, capsys):
    fb = FakeBackend()
    with pytest.raises(SystemExit) as e:
        mbs.main(["--schema", "financehub", "--backend", "http", "--write",
                  "--report", str(tmp_path / "r.xlsx")], backend=fb)
    assert e.value.code == 2
    assert fb.calls == []
    assert "confirm-production" in capsys.readouterr().err


def test_write_is_single_batch_and_guarded():
    res = [{"budget_id": 1, "status": "complete", "match_type": "payment_complete", "match_ref": "payment:10"},
           {"budget_id": 2, "status": "on_progress", "match_type": "pa_line", "match_ref": "etf_pa_lines:5"},
           {"budget_id": 3, "status": "open", "match_type": "none", "match_ref": ""}]
    fb = FakeBackend()
    n = mbs.write_changes(fb, "financehub_test", res)
    assert n == 2 and len(fb.calls) == 1
    stmts = fb.calls[0][0]
    assert len(stmts) == 3
    assert all("status = 'open'" in s or "budget_id is null" in s for s in stmts)


def test_report_xlsx_columns(tmp_path):
    res = mbs.plan_marking([B(1), B(2, code="S2")], [P(10)], [], AKTIF)
    path = tmp_path / "r.xlsx"
    mbs.write_report(str(path), res, {"S1": "Budi", "S2": "Sari"})
    ws = load_workbook(path).active
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == ["Kode", "Nama", "Kategori 1", "Kategori 2", "Amount",
                             "Status Hasil", "Dasar", "Referensi"]
    assert rows[1][:2] == ("S1", "Budi") and rows[1][5] == "complete" and rows[1][6] == "payment_complete"
    assert rows[2][6] == "siswa_non_aktif"


def test_local_db_roundtrip(fhdb_schema, tmp_path):
    """load_inputs + write_changes terhadap financehub_test (Postgres lokal): SQL valid, satu batch, idempoten."""
    from database import get_conn
    conn = get_conn()
    cid = conn.execute("SELECT id FROM companies WHERE code='ETF'").fetchone()[0]
    conn.execute("INSERT INTO siswa (company_id, code, nama, status) VALUES (?,?,?,?)", (cid, "S1", "Budi", "Aktif"))
    sid = conn.execute("SELECT id FROM siswa WHERE code='S1' AND company_id=?", (cid,)).fetchone()[0]
    for _ in range(2):
        conn.execute("INSERT INTO budget_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, status)"
                     " VALUES (?,?,?,?,?,?,?)", (cid, "S1", "By Pendidikan", "Semester 1", "2026-01-01", 1000, "open"))
    conn.execute("INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (?,?,?,?)", (cid, "ETF/1", "open", "2026-01-01T00:00:00"))
    pa = conn.execute("SELECT id FROM etf_pa WHERE company_id=?", (cid,)).fetchone()[0]
    conn.execute("INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, semester, jumlah_pembayaran)"
                 " VALUES (?,?,?,?,?)", (pa, sid, "By Pendidikan", "Semester 1", 1000))
    conn.commit()
    conn.close()

    out = tmp_path / "r.xlsx"
    args = ["--schema", "financehub_test", "--backend", "pg", "--report", str(out), "--write"]
    mbs.main(args, backend=fhdb_schema)
    rows = [tuple(r) for r in fhdb_schema.execute_batch(
        ["select status from budget_beasiswa order by id",
         "select budget_id from etf_pa_lines"], "financehub_test")[0]["rows"]]
    assert rows == [("on_progress",), ("open",)]
    assert fhdb_schema.execute_batch(["select budget_id from etf_pa_lines"], "financehub_test")[0]["rows"][0][0]
    mbs.main(args, backend=fhdb_schema)  # idempoten: tidak ada perubahan
    assert fhdb_schema.execute_batch(["select status from budget_beasiswa order by id"],
                                     "financehub_test")[0]["rows"] == [["on_progress"], ["open"]]

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


def test_schema_comes_from_the_migration():
    # Postgres: the tables are static (db_migrations/0004_fn_spt_badan.sql); no runtime ensure_schema.
    conn = get_conn()
    names = {r[0] for r in conn.execute("SELECT tablename::text FROM pg_tables WHERE schemaname = current_schema()")}
    conn.close()
    assert {"spt_period", "spt_snapshot", "spt_gl_line", "spt_exception", "spt_control"} <= names


# ---------- snapshot ----------

from modules.general_ledger import service as gl_service
from modules.management_report import category_map as cm
from modules.spt_badan import income_statement as inc
from tests.test_gl_sync import mkrow
from tests.test_mrc_category_map import row as cat_row, sheet as cat_sheet

GL_LOG = dict(synced_by="u", filename="f", content_hash="hash-1", rows_before=0, rows_after=8,
              total_debit=0, total_credit=0, dropped=0, summary={})

MAP_ROWS = [  # account, categories_expense, lk, spt
    ("4-1000", "", "Jasa Konsultasi & Advokasi", ""),
    ("5-1000", "", "HARGA POKOK PENJUALAN", "GAJI, UPAH, BONUS, GRATIFIKASI, HONORARIUM, THR, DSB"),
    ("5-2000", "", "HARGA POKOK PENJUALAN", "BIAYA SEWA"),
    ("6-1000", "", "Beban Operasional", "BIAYA LAINNYA"),
    ("8-1000", "", "Bunga Jasa Giro", ""),
    ("8-2000", "", "Pendapatan (Beban) Lainnya", "BIAYA LAINNYA"),
    ("9-1000", "", "Income Tax Expense", ""),
    ("1-1000", "", "KAS DAN SETARA KAS", ""),
]
SPT_GAJI = "GAJI, UPAH, BONUS, GRATIFIKASI, HONORARIUM, THR, DSB"


def seed_mapping(rows=MAP_ROWS):
    cm.sync_categories("GL - MASTER.xlsb", "admin", cm.normalise_categories(
        cat_sheet(*[cat_row(a, None, e, lk, spt) for a, e, lk, spt in rows])))


def gl(acc, debit, credit, lk, spt, pph="", day="2026-01-02", **kw):
    return mkrow(acc_statutory=acc, acc_management=acc, tgl=day, debit=float(debit), credit=float(credit),
                 debit_credit=float(debit) - float(credit), category_lk=lk, category_spt=spt,
                 pph_non_pph=pph, id_no=kw.pop("id_no", f"GJ-{acc}"), **kw)


def seed_gl(rows=None, year=2026, hash_="hash-1"):
    rows = rows if rows is not None else [
        gl("4-1000", 0, 1000, "Jasa Konsultasi & Advokasi", ""),
        gl("5-1000", 300, 0, "HARGA POKOK PENJUALAN", SPT_GAJI, "PPh 21"),
        gl("5-2000", 100, 0, "HARGA POKOK PENJUALAN", "BIAYA SEWA", "pph 23"),
        gl("6-1000", 200, 0, "Beban Operasional", "BIAYA LAINNYA", ""),
        gl("8-1000", 0, 50, "Bunga Jasa Giro", ""),
        gl("8-2000", 10, 0, "Pendapatan (Beban) Lainnya", "BIAYA LAINNYA", "POSENG"),
        gl("9-1000", 80, 0, "Income Tax Expense", ""),
        gl("1-1000", 360, 0, "KAS DAN SETARA KAS", "")]
    gl_service.replace_year("smt", year, rows, dict(GL_LOG, content_hash=hash_, rows_after=len(rows)))


def new_period(year=2026):
    return sv.create_period("smt", year, "admin")


def controls_of(snap_id):
    conn = get_conn()
    try:
        return {r["code"]: dict(r) for r in conn.execute(
            "SELECT * FROM spt_control WHERE snapshot_id=?", (snap_id,))}
    finally:
        conn.close()


def test_snapshot_stores_lines_exceptions_controls_and_totals():
    seed_mapping(); seed_gl()
    pid = new_period()
    sid = sv.take_snapshot(pid, "admin")
    snap = sv.get_current_snapshot(pid)
    assert snap["id"] == sid and snap["is_current"] == 1 and snap["taken_by"] == "admin"
    assert (snap["row_count"], snap["total_debit"], snap["total_credit"]) == (8, 1050.0, 1050.0)
    assert (snap["date_min"], snap["date_max"]) == ("2026-01-02", "2026-01-02")
    assert snap["gl_hash"] == "hash-1" and snap["map_version"] == cm.get_version()
    cs = controls_of(sid)
    assert {c: cs[c]["status"] for c in cs} == {"C1": "lulus", "C2": "lulus", "C3": "lulus", "C4": "lulus",
                                                "C5": "lulus", "C6": "lulus", "C7": "peringatan",
                                                "C9": "lulus"}
    kinds = {(g["kind"], g["account"]): g["n"] for g in sv.exception_groups(sid)}
    assert kinds == {("pph_kosong", "6-1000"): 1, ("pph_bukan_jenis", "8-2000"): 1}


def test_income_statement_for_a_snapshot_matches_the_gl():
    seed_mapping(); seed_gl()
    sid = sv.take_snapshot(new_period(), "admin")
    s = sv.income_statement_for(sid)["summary"]
    assert (s["revenue"], s["hpp"], s["opex"], s["pbt"], s["tax"], s["net"]) == (1000.0, 400.0, 200.0, 440.0, 80.0, 360.0)


def test_new_snapshot_replaces_current_and_old_ones_are_pruned_to_three():
    seed_mapping(); seed_gl()
    pid = new_period()
    ids = [sv.take_snapshot(pid, "admin") for _ in range(4)]
    snaps = sv.list_snapshots(pid)
    assert [s["id"] for s in snaps] == ids[:0:-1]                       # newest first, oldest pruned
    assert [s["is_current"] for s in snaps] == [1, 0, 0]
    conn = get_conn()
    leftovers = conn.execute("SELECT COUNT(*) FROM spt_gl_line WHERE snapshot_id=?", (ids[0],)).fetchone()[0]
    conn.close()
    assert leftovers == 0


def test_failed_snapshot_keeps_the_previous_one_intact(monkeypatch):
    seed_mapping(); seed_gl()
    pid = new_period()
    first = sv.take_snapshot(pid, "admin")
    monkeypatch.setattr(sv, "_prune", lambda conn, period_id: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        sv.take_snapshot(pid, "admin")
    snaps = sv.list_snapshots(pid)
    assert [s["id"] for s in snaps] == [first] and snaps[0]["is_current"] == 1
    conn = get_conn()
    n_lines = conn.execute("SELECT COUNT(*) FROM spt_gl_line").fetchone()[0]
    conn.close()
    assert n_lines == 8


def test_snapshot_without_gl_for_the_year_raises_and_unknown_period_is_keyerror():
    seed_mapping()
    pid = new_period()
    with pytest.raises(ValueError, match="2026"):
        sv.take_snapshot(pid, "admin")
    with pytest.raises(KeyError):
        sv.take_snapshot(999, "admin")
    assert sv.list_snapshots(pid) == []


def test_unmapped_account_makes_c3_fail_without_crashing():
    seed_mapping(MAP_ROWS[:-1])                                          # cash account not mapped
    seed_gl()
    sid = sv.take_snapshot(new_period(), "admin")
    assert controls_of(sid)["C3"]["status"] == "gagal" and controls_of(sid)["C3"]["left_value"] == 1
    top = sv.exception_groups(sid)[0]
    assert (top["kind"], top["severity"], top["account"]) == ("akun_belum_dipetakan", "blocker", "1-1000")


def test_unbalanced_gl_fails_c1_and_missing_pnl_kind_fails_c6():
    seed_mapping()
    pid = new_period()
    seed_gl([gl("4-1000", 0, 1000, "Jasa Konsultasi & Advokasi", ""),
             gl("5-1000", 300, 0, "HARGA POKOK PENJUALAN", SPT_GAJI, "PPh 21")])
    assert controls_of(sv.take_snapshot(pid, "admin"))["C1"]["status"] == "gagal"
    conn = get_conn()                                                    # kind removed -> not placed
    conn.execute("UPDATE gl_category_lk SET kind='' WHERE category_lk='Beban Operasional'")
    conn.commit(); conn.close()
    seed_gl([gl("6-1000", 200, 0, "Beban Operasional", "BIAYA LAINNYA", "PPh 21"),
             gl("1-1000", 0, 200, "KAS DAN SETARA KAS", "")], hash_="hash-2")
    assert controls_of(sv.take_snapshot(pid, "admin"))["C6"]["status"] == "gagal"


def test_staleness_detects_gl_and_mapping_changes():
    seed_mapping(); seed_gl()
    pid = new_period()
    sv.take_snapshot(pid, "admin")
    period, snap = sv.get_period(pid), sv.get_current_snapshot(pid)
    assert sv.staleness(period, snap) == []
    seed_gl(hash_="hash-2")
    assert sv.staleness(period, snap) == ["GL berubah sejak snapshot"]
    cm.add_pph_alias("pph empat dua", "PPh 4(2)")
    assert sv.staleness(period, snap) == ["GL berubah sejak snapshot", "Pemetaan berubah sejak snapshot"]
    c8 = [c for c in sv.get_controls(period, snap) if c["code"] == "C8"][0]
    assert c8["status"] == "peringatan"
    assert [c["code"] for c in sv.get_controls(period, snap)] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]


def test_list_exceptions_filters_and_pages():
    seed_mapping(); seed_gl()
    sid = sv.take_snapshot(new_period(), "admin")
    allx = sv.list_exceptions(sid)
    assert allx["total"] == 2 and {r["kind"] for r in allx["rows"]} == {"pph_kosong", "pph_bukan_jenis"}
    assert sv.list_exceptions(sid, kind="pph_kosong")["total"] == 1
    assert sv.list_exceptions(sid, severity="blocker")["total"] == 0
    assert sv.list_exceptions(sid, q="POSENG")["rows"][0]["account"] == "8-2000"
    assert sv.list_exceptions(sid, page=99)["page"] == 1


def test_drill_down_totals_equal_the_statement_including_blank_spt():
    seed_mapping(); seed_gl()
    sid = sv.take_snapshot(new_period(), "admin")
    st = sv.income_statement_for(sid)
    for r in st["rows"]:
        if r["cats"] is None:
            continue
        d = sv.drill_lines(sid, r["cats"], r["spt"])
        sign = -1 if r["key"] == "revenue" or r["key"].startswith("other:") else 1
        assert sign * d["amount"] == pytest.approx(r["amount"]), r["key"]
    blank = sv.drill_lines(sid, ["Jasa Konsultasi & Advokasi"], "")
    assert blank["total"] == 1 and blank["amount"] == -1000.0
    assert sv.drill_lines(sid, ["Jasa Konsultasi & Advokasi"], "BIAYA SEWA")["total"] == 0
    assert sv.drill_lines(sid, [], None)["total"] == 0


def test_step_statuses():
    seed_mapping(); seed_gl()
    pid = new_period()
    assert [s["status"] for s in sv.step_statuses(None, [])] == ["belum", "belum", "belum", "belum"]
    sv.take_snapshot(pid, "admin")
    period, snap = sv.get_period(pid), sv.get_current_snapshot(pid)
    steps = sv.step_statuses(snap, sv.get_controls(period, snap))
    assert [(s["name"], s["status"]) for s in steps] == [
        ("Snapshot GL", "lulus"), ("Validasi klasifikasi", "peringatan"),
        ("Laba rugi komersial", "lulus"), ("Kontrol", "peringatan")]


def test_snapshot_reads_hash_and_version_before_lines_so_a_race_reads_stale(monkeypatch):
    seed_mapping(); seed_gl()
    pid = new_period()
    real = gl_service.load_lines

    def racing(entity, year):
        lines = real(entity, year)
        seed_gl(hash_="hash-2")                       # GL re-sync lands mid-snapshot
        cm.add_pph_alias("pph empat dua", "PPh 4(2)")  # and so does a Pemetaan edit
        return lines

    monkeypatch.setattr(gl_service, "load_lines", racing)
    sv.take_snapshot(pid, "admin")
    assert sv.staleness(sv.get_period(pid), sv.get_current_snapshot(pid)) == [
        "GL berubah sejak snapshot", "Pemetaan berubah sejak snapshot"]


def test_laba_rugi_category_without_kind_is_a_named_blocker():
    seed_mapping(); seed_gl()
    conn = get_conn()
    conn.execute("UPDATE gl_category_lk SET kind='' WHERE category_lk='Beban Operasional'")
    conn.commit(); conn.close()
    sid = sv.take_snapshot(new_period(), "admin")
    blockers = [g for g in sv.exception_groups(sid) if g["kind"] == "category_lk_tidak_dikenal"]
    assert [g["account"] for g in blockers] == ["6-1000"]
    got = sv.list_exceptions(sid, kind="category_lk_tidak_dikenal")["rows"][0]["detail"]
    assert "belum diatur sifatnya" in got and "Beban Operasional" in got


def _counts():
    conn = get_conn()
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("spt_snapshot", "spt_gl_line", "spt_exception", "spt_control")}
    finally:
        conn.close()


def test_take_snapshot_atomic_on_failure(monkeypatch):
    seed_mapping(); seed_gl()
    pid = new_period()
    first = sv.take_snapshot(pid, "admin")
    before = _counts()
    real = sv.controls.compute_controls

    def broken(**kw):           # the spt_control inserts come after the snapshot and its lines/exceptions
        out = real(**kw)
        out[-1] = {**out[-1], "status": None}                 # spt_control.status is NOT NULL
        return out

    monkeypatch.setattr(sv.controls, "compute_controls", broken)
    with pytest.raises(Exception):
        sv.take_snapshot(pid, "admin")
    assert _counts() == before
    assert sv.get_current_snapshot(pid)["id"] == first
    conn = get_conn()
    try:
        assert conn.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = current_schema() "
                            "AND left(tablename, 9) = 'fh_stage_'").fetchone()[0] == 0
    finally:
        conn.close()

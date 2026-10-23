import pytest

from database import get_conn
from modules.management_report import service as svc


def mkrow(cc='POCFAD', coa='70105120', mm=1, yy=26, bgt=1.0, pta=0.0, act=0.0,
          category='01 - Rental', custom='1', mm1=1, description='d', activity='Operational'):
    return dict(coa=coa, mm=mm, yy=yy, cc=cc, category=category, activity=activity,
                description=description, pta=pta, custom=custom, mm1=mm1, act=act, bgt=bgt)


def count(sql, *p):
    conn = get_conn()
    try:
        return conn.execute(sql, p).fetchone()[0]
    finally:
        conn.close()


def test_save_upload_becomes_active_and_replaces_previous():
    a = svc.save_upload(1, 'a.xlsb', 'u', [mkrow(), mkrow(cc='POCFAC')])
    assert svc.get_active_upload_id(1) == a
    b = svc.save_upload(1, 'b.xlsb', 'u', [mkrow()])
    assert svc.get_active_upload_id(1) == b
    ups = {u['id']: u for u in svc.list_uploads(1)}
    assert ups[a]['is_active'] is False and ups[b]['is_active'] is True
    assert ups[a]['row_count'] == 2 and ups[b]['row_count'] == 1
    assert [u['id'] for u in svc.list_uploads(1)] == [b, a]


def test_empty_rows_rejected():
    with pytest.raises(ValueError):
        svc.save_upload(1, 'x.xlsb', 'u', [])


def test_failed_save_rolls_back_and_keeps_previous_active():
    a = svc.save_upload(1, 'a.xlsb', 'u', [mkrow()])
    with pytest.raises(KeyError):
        svc.save_upload(1, 'bad.xlsb', 'u', [{'coa': '1'}])
    assert svc.get_active_upload_id(1) == a
    assert count("SELECT COUNT(*) FROM mr_upload") == 1


def test_retention_purges_old_snapshots_but_keeps_metadata():
    ids = [svc.save_upload(1, f'{i}.xlsb', 'u', [mkrow()], keep=3) for i in range(5)]
    ups = {u['id']: u for u in svc.list_uploads(1)}
    assert [ups[i]['purged'] for i in ids] == [True, True, False, False, False]
    assert count("SELECT COUNT(*) FROM mr_append WHERE upload_id=?", ids[0]) == 0
    assert count("SELECT COUNT(*) FROM mr_append WHERE upload_id=?", ids[4]) == 1
    assert svc.get_active_upload_id(1) == ids[4]


def test_companies_are_isolated():
    a = svc.save_upload(1, 'a.xlsb', 'u', [mkrow()])
    b = svc.save_upload(2, 'b.xlsb', 'u', [mkrow()])
    assert svc.get_active_upload_id(1) == a
    assert svc.get_active_upload_id(2) == b
    assert [u['id'] for u in svc.list_uploads(1)] == [a]
    assert svc.activate_upload(1, b) is False        # belongs to company 2


def test_activate_older_snapshot_and_refuse_purged():
    ids = [svc.save_upload(1, f'{i}.xlsb', 'u', [mkrow()], keep=2) for i in range(3)]
    assert svc.activate_upload(1, ids[0]) is False   # purged
    assert svc.activate_upload(1, ids[1]) is True
    assert svc.get_active_upload_id(1) == ids[1]
    assert svc.activate_upload(1, 9999) is False


def test_filter_options_use_active_snapshot_only():
    assert svc.get_filter_options(1) == {'ccs': [], 'yys': [], 'mms': [], 'coas': [], 'cats': []}
    svc.save_upload(1, 'old.xlsb', 'u', [mkrow(cc='OLDCC')])
    svc.save_upload(1, 'new.xlsb', 'u', [
        mkrow(cc='POCFAD', mm=2, coa='70105120'),
        mkrow(cc='POCFAC', mm=1, coa='70106200'),
        mkrow(cc='POCFAC', mm=2, coa='70106200'),
    ])
    assert svc.get_filter_options(1) == {
        'ccs': ['POCFAC', 'POCFAD'], 'yys': [26], 'mms': [1, 2],
        'coas': ['70105120', '70106200'], 'cats': ['01 - Rental'],
    }


# ---------- Postgres atomicity (one batch per flow) ----------

def fail_batch_after_writes(monkeypatch, marker):
    """Make the batch whose SQL contains `marker` fail AFTER all its statements ran: every write of
    that batch must then be rolled back together."""
    from fhdb.connection import Connection
    real = Connection.batch

    def failing(self, items):
        items = list(items)
        if any(marker in sql for sql, _ in items):
            items.append(("SELECT 1/0", ()))
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", failing)


def mr_state():
    conn = get_conn()
    try:
        ups = [tuple(r) for r in conn.execute(
            "SELECT id, is_active, purged, row_count FROM mr_upload ORDER BY id")]
        per_upload = [tuple(r) for r in conn.execute(
            "SELECT upload_id, COUNT(*) FROM mr_append GROUP BY upload_id ORDER BY upload_id")]
        stages = conn.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = current_schema() "
                              "AND tablename LIKE 'fh_stage_mr_%'").fetchone()[0]
        return ups, per_upload, stages
    finally:
        conn.close()


def test_save_upload_atomic_on_failure(monkeypatch):
    a = svc.save_upload(1, 'a.xlsb', 'u', [mkrow(), mkrow(cc='POCFAC')], keep=1)
    svc.save_upload(1, 'b.xlsb', 'u', [mkrow()], keep=1)               # a is purged
    b = svc.save_upload(1, 'c.xlsb', 'u', [mkrow(), mkrow(), mkrow()], keep=1)
    before = mr_state()
    fail_batch_after_writes(monkeypatch, "INSERT INTO mr_upload")
    with pytest.raises(Exception):
        svc.save_upload(1, 'd.xlsb', 'u', [mkrow()] * 4, keep=1)      # would purge b's rows
    assert mr_state() == before
    assert before[2] == 0                                              # no staging table left
    assert svc.get_active_upload_id(1) == b and a != b


def test_save_upload_large_snapshot_goes_in_chunks_and_keeps_sheet_order(monkeypatch):
    from fhdb.connection import Connection
    sent = []
    real = Connection.execute

    def spy(self, sql, params=()):
        if sql.startswith('INSERT INTO "fh_stage_mr_'):
            sent.append(len(params) // 13)
        return real(self, sql, params)
    monkeypatch.setattr(Connection, "execute", spy)
    rows = [mkrow(description=f'd{i}', mm=i % 12 + 1) for i in range(2500)]
    up = svc.save_upload(1, 'big.xlsb', 'u', rows)
    assert sent == [1000, 1000, 500]
    assert count("SELECT COUNT(*) FROM mr_append WHERE upload_id=?", up) == 2500
    got = svc.query_append(1)["rows"]
    assert [r['description'] for r in got] == [f'd{i}' for i in range(2500)]
    assert got[7] == {k: rows[7][k] for k in svc._APPEND_COLS}


def test_save_upload_swap_batch_starts_with_the_advisory_lock(monkeypatch):
    from fhdb.connection import Connection
    batches = []
    real = Connection.batch

    def spy(self, items):
        batches.append(list(items))
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", spy)
    svc.save_upload(1, 'a.xlsb', 'u', [mkrow()])
    swap = [b for b in batches if any("INSERT INTO mr_upload" in sql for sql, _ in b)][-1]
    assert swap[0] == ("SELECT pg_advisory_xact_lock(hashtext(?))", ("mr:upload:1",))
    batches.clear()
    svc.activate_upload(1, svc.get_active_upload_id(1))
    act = [b for b in batches if any("is_active=1" in sql for sql, _ in b)][-1]
    assert act[0] == ("SELECT pg_advisory_xact_lock(hashtext(?))", ("mr:upload:1",))


def test_concurrent_save_upload_leaves_one_active_snapshot(pg_dsn):
    from tests.test_gl_sync import run_concurrently_behind_lock
    svc.save_upload(1, 'a.xlsb', 'u', [mkrow()], keep=2)
    run_concurrently_behind_lock(pg_dsn, "mr:upload:1",
                                 lambda: svc.save_upload(1, 'b.xlsb', 'u', [mkrow(), mkrow()], keep=2))
    ups = svc.list_uploads(1)
    assert [u['is_active'] for u in ups] == [True, False, False]
    assert [u['purged'] for u in ups] == [False, False, True]            # keep=2 still holds
    assert count("SELECT COUNT(*) FROM mr_append") == 4
    assert count("SELECT COUNT(*) FROM mr_upload WHERE is_active=1") == 1


def test_activate_upload_atomic_on_failure(monkeypatch):
    a = svc.save_upload(1, 'a.xlsb', 'u', [mkrow()])
    b = svc.save_upload(1, 'b.xlsb', 'u', [mkrow()])
    before = mr_state()
    fail_batch_after_writes(monkeypatch, "is_active=1")
    with pytest.raises(Exception):
        svc.activate_upload(1, a)
    assert mr_state() == before
    assert svc.get_active_upload_id(1) == b


def test_snapshot_cache_reads_once_and_returns_independent_copies():
    """Task 21: inside snapshot_cache() the snapshot lookups hit the DB once; results are copies."""
    import fhdb
    svc.save_upload(1, 'a.xlsb', 'u', [mkrow(), mkrow(cc='POCFAC')])
    plain = svc.query_append(1, 'POCFAD')
    opts = svc.get_filter_options(1)
    with svc.snapshot_cache():
        fhdb.reset_stats()
        first = svc.query_append(1, 'POCFAD')
        first["rows"][0]["coa"] = "changed"
        again = svc.query_append(1, 'POCFAD')
        assert svc.get_filter_options(1) == opts
        svc.get_filter_options(1)
        calls = fhdb.stats.calls
    assert again == plain
    assert calls == 3            # uid, append (count+rows in one batch), filter options (one batch)
    svc.save_upload(1, 'b.xlsb', 'u', [mkrow(cc='ZZZ')])
    assert svc.get_filter_options(1)["ccs"] == ['ZZZ']   # outside the block: no cache

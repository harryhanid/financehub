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

import io
import os

import pytest

from modules.management_report import service as svc
from modules.management_report.parser import read_append1

SAMPLE = os.environ.get('MR_SAMPLE_XLSB',
                        r'C:\Users\25010160\Downloads\Management Report - MASTER.xlsb')

# From Excel sheet "Report", CC = TFKHAR.
EXCEL_TFKHAR = {
    '01 - Rental, Tax & License Expense':          (3.2, 0.0, 3.2, 0.0, -3.2, -1.0),
    '02 - Transport & Travelling Expense':         (89.3, 0.0, 89.3, 0.0, -89.3, -1.0),
    '05 - Professional Fee':                       (40.4, 0.0, 40.4, 0.0, -40.4, -1.0),
    '06 - Entertainment & Gift Expense':           (33.5, 0.0, 33.5, 7.0, -26.5, -0.791045),
    '10 - Office Supplies And Equipment Expense':  (2.5, 0.0, 2.5, 3.8, 1.3, 0.52),
    '11 - Human Resources':                        (12.5, 4.9, 17.4, 4.9, -12.5, -0.718391),
    '20 - Others':                                 (0.0, 0.0, 0.0, 8.9, 8.9, None),
}
EXCEL_GRAND = (181.4, 4.9, 186.3, 24.6, -161.7, -0.867955)
KEYS = ('bgt', 'pta', 'available', 'act', 'diff', 'pct')


@pytest.fixture
def uploaded():
    try:
        with open(SAMPLE, 'rb') as f:
            data = f.read()
    except OSError:
        pytest.skip('sample master workbook not available')
    res = read_append1(io.BytesIO(data))
    svc.save_upload(1, 'Management Report - MASTER.xlsb', 'test', res.rows)
    return res.rows


def _cmp(actual: dict, expected: tuple):
    for k, e in zip(KEYS, expected):
        if e is None:
            assert actual[k] is None, k
        else:
            assert actual[k] == pytest.approx(e, abs=1e-5), k


def test_tfkhar_matches_excel_report(uploaded):
    rep = svc.build_report(1, 'TFKHAR')
    assert rep['has_data']
    got = {g['category']: g['total'] for g in rep['groups']}
    assert set(got) == set(EXCEL_TFKHAR)
    for cat, expected in EXCEL_TFKHAR.items():
        _cmp(got[cat], expected)
    _cmp(rep['grand'], EXCEL_GRAND)


def test_every_cc_grand_total_equals_raw_sums(uploaded):
    ccs = svc.list_ccs_with_data(1)
    assert len(ccs) >= 30
    for cc in ccs:
        rows = [r for r in uploaded if r['cc'] == cc]
        rep = svc.build_report(1, cc)
        assert rep['grand']['bgt'] == pytest.approx(sum(r['bgt'] for r in rows), abs=1e-4), cc
        assert rep['grand']['pta'] == pytest.approx(sum(r['pta'] for r in rows), abs=1e-4), cc
        assert rep['grand']['act'] == pytest.approx(sum(r['act'] for r in rows), abs=1e-4), cc
        assert sum(len(g['rows']) for g in rep['groups']) <= len(rows)


def test_syncing_the_real_file_twice_reports_no_change_second_time(uploaded):
    from modules.management_report import sync as mrsync
    with open(SAMPLE, 'rb') as f:
        rows = read_append1(io.BytesIO(f.read())).rows
    first = mrsync.sync_rows(2, 'Master.xlsb', 'test', rows)
    assert first['changed'] is True and first['summary']['first'] is True
    again = mrsync.sync_rows(2, 'Master.xlsb', 'test', list(reversed(rows)))
    assert again == {'changed': False, 'rows': len(rows)}
    # one edited amount is detected as exactly one changed line for exactly one CC
    edited = [dict(r) for r in rows]
    edited[0]['act'] += 5.0
    res = mrsync.sync_rows(2, 'Master.xlsb', 'test', edited)
    assert res['changed'] is True
    assert res['summary']['lines'] == {'added': 0, 'removed': 0, 'changed': 1}
    assert res['summary']['delta']['act'] == pytest.approx(5.0, abs=1e-6)
    assert [c['cc'] for c in res['summary']['ccs']] == [rows[0]['cc']]

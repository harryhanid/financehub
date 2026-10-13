import pytest

from modules.management_report import service as svc
from tests.test_mr_service import mkrow


@pytest.fixture
def seeded():
    svc.save_upload(1, 'a.xlsb', 'u', [
        mkrow(cc='TFKHAR', category='B Cat', mm1=3, description='d1', bgt=10, pta=2, act=4, mm=3, coa='111'),
        mkrow(cc='TFKHAR', category='B Cat', mm1=3, description='d1', bgt=1, pta=0, act=1, mm=3, coa='111'),
        mkrow(cc='TFKHAR', category='A Cat', mm1=2, description='d3', bgt=0, pta=0, act=3, mm=2, coa='222'),
        mkrow(cc='TFKHAR', category='A Cat', mm1=1, description='d2', bgt=5, pta=0, act=0, mm=1, coa='222'),
        mkrow(cc='OTHER', category='A Cat', mm1=1, description='x', bgt=99, pta=0, act=99, mm=1, coa='222'),
    ])


def test_hierarchy_order_and_aggregation(seeded):
    rep = svc.build_report(1, 'TFKHAR')
    assert rep['has_data'] is True and rep['cc'] == 'TFKHAR'
    assert [g['category'] for g in rep['groups']] == ['A Cat', 'B Cat']
    a, b = rep['groups']
    assert [r['description'] for r in a['rows']] == ['d2', 'd3']       # mm1 1 then 2
    assert len(b['rows']) == 1                                         # duplicate keys summed
    r = b['rows'][0]
    assert (r['bgt'], r['pta'], r['act']) == (11, 2, 5)


def test_formulas_row_total_and_grand(seeded):
    rep = svc.build_report(1, 'TFKHAR')
    a, b = rep['groups']
    d2, d3 = a['rows']
    assert d2['available'] == 5 and d2['diff'] == -5 and d2['pct'] == -1.0
    assert d3['available'] == 0 and d3['diff'] == 3 and d3['pct'] is None
    assert a['total'] == {'bgt': 5, 'pta': 0, 'available': 5, 'act': 3, 'diff': -2, 'pct': -0.4}
    br = b['rows'][0]
    assert br['available'] == 13 and br['diff'] == -8
    assert br['pct'] == pytest.approx(-8 / 13, abs=1e-6)
    g = rep['grand']
    assert (g['bgt'], g['pta'], g['available'], g['act'], g['diff']) == (16, 2, 18, 8, -10)
    assert g['pct'] == pytest.approx(-10 / 18, abs=1e-6)


def test_filters(seeded):
    assert svc.build_report(1, 'TFKHAR', mm=1)['grand']['bgt'] == 5
    assert svc.build_report(1, 'TFKHAR', yy=25)['has_data'] is False
    assert svc.build_report(1, 'TFKHAR', coas=['111'])['grand']['bgt'] == 11
    assert svc.build_report(1, 'TFKHAR', coas=['111', '222'])['grand']['bgt'] == 16


def test_no_data_cases(seeded):
    rep = svc.build_report(1, 'NOPE')
    assert rep['has_data'] is False and rep['groups'] == []
    assert rep['grand'] == {'bgt': 0, 'pta': 0, 'available': 0, 'act': 0, 'diff': 0, 'pct': None}
    assert svc.build_report(2, 'TFKHAR')['has_data'] is False          # other company
    assert svc.build_report(1, 'TFKHAR', mm=12)['has_data'] is False


def test_list_ccs_with_data(seeded):
    assert svc.list_ccs_with_data(1) == ['OTHER', 'TFKHAR']
    assert svc.list_ccs_with_data(1, mm=3) == ['TFKHAR']
    assert svc.list_ccs_with_data(1, coas=['999']) == []

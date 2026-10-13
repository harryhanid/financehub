import io
import os
import pytest

from modules.management_report.parser import (
    REQUIRED_COLUMNS, ParseError, normalise_rows, read_append1,
)

HEADER = ['COA', 'MM', 'YY', 'CC', 'CC.1', 'Category', 'Activity', 'Description',
          'PTA', 'Custom', 'MM.1', 'ACT', 'BGT']


def raw(**kw):
    base = dict(COA=70107600.0, MM=5.0, YY=26.0, CC='POSENG', **{'CC.1': 'POSENG'},
                Category=' 18 - Office Consumption ', Activity='Operational PO',
                Description='- Pta 2026 : x Month : 5', PTA=1.4, Custom='2',
                **{'MM.1': 5.0}, ACT=0.0, BGT=0.0)
    base.update(kw)
    return [base[h] for h in HEADER]


def test_normalises_a_row():
    res = normalise_rows(HEADER, [raw()])
    assert res.dropped == 0
    assert res.rows == [{
        'coa': '70107600', 'mm': 5, 'yy': 26, 'cc': 'POSENG',
        'category': '18 - Office Consumption', 'activity': 'Operational PO',
        'description': '- Pta 2026 : x Month : 5', 'pta': 1.4, 'custom': '2',
        'mm1': 5, 'act': 0.0, 'bgt': 0.0,
    }]


def test_blank_numbers_become_zero_and_blank_category_is_labelled():
    res = normalise_rows(HEADER, [raw(PTA=None, ACT=None, BGT=None, Category=None)])
    r = res.rows[0]
    assert (r['pta'], r['act'], r['bgt']) == (0.0, 0.0, 0.0)
    assert r['category'] == '(blank)'


def test_drops_rows_without_cc_and_counts_them():
    rows = [raw(), raw(CC=None, **{'CC.1': None}), raw(CC='0'), [None] * len(HEADER)]
    res = normalise_rows(HEADER, rows)
    assert len(res.rows) == 1
    assert res.dropped == 2          # fully blank row is ignored, not counted


def test_missing_column_raises_with_name():
    header = [h for h in HEADER if h != 'BGT']
    with pytest.raises(ParseError) as e:
        normalise_rows(header, [])
    assert 'BGT' in str(e.value)


def test_required_columns_constant():
    assert 'MM.1' in REQUIRED_COLUMNS and 'CC.1' not in REQUIRED_COLUMNS


SAMPLE = os.environ.get('MR_SAMPLE_XLSB',
                        r'C:\Users\25010160\Downloads\Management Report - MASTER.xlsb')


def test_reads_real_master_file():
    try:
        with open(SAMPLE, 'rb') as f:
            data = f.read()
    except OSError:
        pytest.skip('sample master workbook not available')
    res = read_append1(io.BytesIO(data))
    assert len(res.rows) > 8000
    t = [r for r in res.rows if r['cc'] == 'TFKHAR']
    assert round(sum(r['bgt'] for r in t), 6) == 181.4
    assert round(sum(r['pta'] for r in t), 6) == 4.9
    assert round(sum(r['act'] for r in t), 6) == 24.6


def test_garbage_file_raises_parse_error():
    with pytest.raises(ParseError):
        read_append1(io.BytesIO(b'not an xlsb'))


def test_read_errors_during_iteration_become_parse_error(monkeypatch):
    from modules.management_report import parser

    class Cell:
        def __init__(self, v):
            self.v = v

    class Sheet:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def rows(self):
            yield [Cell(h) for h in HEADER]
            raise RuntimeError("corrupt record")

    class WB:
        sheets = [parser.SHEET_NAME]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_sheet(self, name):
            return Sheet()

    monkeypatch.setattr(parser, "open_workbook", lambda f: WB())
    with pytest.raises(ParseError, match="File tidak bisa dibaca: corrupt record"):
        read_append1(io.BytesIO(b"x"))


def test_int_overflow_gives_none():
    res = normalise_rows(HEADER, [raw(MM=float('inf'))])
    assert res.rows[0]['mm'] is None

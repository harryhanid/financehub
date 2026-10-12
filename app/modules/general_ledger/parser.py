# modules/general_ledger/parser.py
"""General Ledger: read the GL SMT / GL ETF / GL SETF sheets of GL - MASTER.xlsb."""
import datetime as _dt
import re
from collections import namedtuple

from pyxlsb import open_workbook

# (sheet header, stored column) in sheet order; every one of the sheet's 51 columns is imported
_SHEET_COLUMNS = (
    [("x", "entry_no"), ("x1", "source_type"),
     ("Account Statutory", "acc_statutory"), ("Description Account Statutory", "acc_statutory_desc"),
     ("Account Management", "acc_management"), ("Description Account Management", "acc_management_desc"),
     ("ID#", "id_no"), ("Date", "tgl"), ("Memo", "memo"), ("Debit", "debit"), ("Credit", "credit"),
     ("Job Name", "job_name"), ("Job Description", "job_desc"), ("PPH/Non PPH", "pph_non_pph"),
     ("Budget Activity", "budget_activity"), ("Customer/ Vendor", "customer_vendor"),
     ("Allocation Memo", "allocation_memo"), ("EVENT", "event"),
     ("Qty Awal", "qty_awal"), ("Qty Akhir", "qty_akhir"), ("UOM", "uom"),
     ("Nama Item", "nama_item"), ("Harga Satuan", "harga_satuan")]
    + [(f"Keterangan {i}", f"ket{i}") for i in range(1, 21)]
    + [("DEBIT - CREDIT", "debit_credit"), ("Period", "period"),
       ("CATEGORIES EXPENSE (6-****)", "category_expense"), ("Category LK", "category_lk"),
       ("Category SPT", "category_spt"), ("Accrual/Actual", "accrual_actual"),
       ("PPh", "pph"), ("Sub-Category", "sub_category")]
)
COLUMNS = tuple(col for _, col in _SHEET_COLUMNS)
LABELS = {col: label for label, col in _SHEET_COLUMNS}
# Normalised sheet header (lower case, whitespace collapsed) -> column
_HEADER_MAP = {" ".join(label.split()).lower(): col for label, col in _SHEET_COLUMNS}
_REQUIRED = ("account statutory", "account management", "id#", "date", "debit", "credit")
_REAL = {"debit", "credit", "qty_awal", "qty_akhir", "harga_satuan", "debit_credit"}
_ERR = re.compile(r"^0x[0-9A-Fa-f]{1,2}$")       # how pyxlsb shows an Excel error cell

ParseResult = namedtuple("ParseResult", "rows dropped")


class ParseError(ValueError):
    """Raised with a user-facing message when the workbook cannot be used."""


def _norm(h) -> str:
    return " ".join(str(h).split()).lower() if h is not None else ""


def _text(v) -> str:
    if v is None or (isinstance(v, (int, float)) and v == 0):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return "" if _ERR.match(s) else s


def _num(v) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError, OverflowError):
        return None


def _date(v):
    if isinstance(v, (int, float)):
        if v <= 0:
            return None
        try:
            return (_dt.date(1899, 12, 30) + _dt.timedelta(days=int(v))).isoformat()
        except OverflowError:
            return None
    s = _text(v)
    return s or None


def normalise_rows(header, raw_rows) -> ParseResult:
    names = [_norm(h) for h in header]
    missing = [h for h in _REQUIRED if h not in names]
    if missing:
        raise ParseError("Kolom tidak ditemukan: " + ", ".join(m.title() for m in missing))
    pos = {}
    for i, n in enumerate(names):
        col = _HEADER_MAP.get(n)
        if col and col not in pos:               # first occurrence wins; later helper columns repeat names
            pos[col] = i

    rows, dropped = [], 0
    for raw in raw_rows:
        if all(v in (None, "") for v in raw):
            continue

        def g(col):
            i = pos.get(col)
            return raw[i] if i is not None and i < len(raw) else None

        row = {}
        for col in COLUMNS:
            v = g(col)
            if col in _REAL:
                row[col] = _num(v)
            elif col == "entry_no":
                row[col] = _int(v)
            elif col == "tgl":
                row[col] = _date(v)
            else:
                row[col] = _text(v)
        if not (row["debit"] or row["credit"]):          # only rows that carry an amount are synced
            dropped += 1
            continue
        rows.append(row)
    return ParseResult(rows, dropped)


def read_gl_sheet(fileobj, sheet_name: str) -> ParseResult:
    try:
        wb = open_workbook(fileobj)
    except Exception as e:
        raise ParseError(f"File tidak bisa dibaca sebagai .xlsb: {e}") from e
    try:
        with wb:
            if sheet_name not in wb.sheets:
                raise ParseError(f"Sheet '{sheet_name}' tidak ditemukan di file.")
            with wb.get_sheet(sheet_name) as sh:
                it = ([c.v for c in r] for r in sh.rows())
                header = None
                for i, vals in enumerate(it):          # row 0 is a control row, header is row 1
                    if i > 4:
                        break
                    names = [_norm(h) for h in vals]
                    if "debit" in names and "credit" in names:
                        header = vals
                        break
                if header is None:
                    raise ParseError(f"Header (Debit/Credit) tidak ditemukan di sheet '{sheet_name}'.")
                return normalise_rows(header, it)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"File tidak bisa dibaca: {e}") from e

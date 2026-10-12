# modules/general_ledger/parser.py
"""General Ledger: read the GL SMT / GL ETF / GL SETF sheets of GL - MASTER.xlsb."""
import datetime as _dt
import re
from collections import namedtuple

from pyxlsb import open_workbook

COLUMNS = ("entry_no", "source_type", "acc_statutory", "acc_statutory_desc", "acc_management",
           "acc_management_desc", "id_no", "tgl", "memo", "debit", "credit", "job_name",
           "job_desc", "budget_activity", "customer_vendor", "allocation_memo", "event",
           "qty_awal", "qty_akhir", "uom", "nama_item", "harga_satuan", "ket1", "ket2")

# Normalised sheet header (lower case, whitespace collapsed) -> column
_HEADER_MAP = {
    "x": "entry_no", "x1": "source_type",
    "account statutory": "acc_statutory",
    "description account statutory": "acc_statutory_desc",
    "account management": "acc_management",
    "description account management": "acc_management_desc",
    "id#": "id_no", "date": "tgl", "memo": "memo", "debit": "debit", "credit": "credit",
    "job name": "job_name", "job description": "job_desc",
    "budget activity": "budget_activity", "customer/ vendor": "customer_vendor",
    "allocation memo": "allocation_memo", "event": "event",
    "qty awal": "qty_awal", "qty akhir": "qty_akhir", "uom": "uom",
    "nama item": "nama_item", "harga satuan": "harga_satuan",
    "keterangan 1": "ket1", "keterangan 2": "ket2",
}
_REQUIRED = ("account statutory", "account management", "id#", "date", "debit", "credit")
_REAL = {"debit", "credit", "qty_awal", "qty_akhir", "harga_satuan"}
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
        if not (row["id_no"] or row["acc_statutory"] or row["acc_management"]):
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

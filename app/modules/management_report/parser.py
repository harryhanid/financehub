"""Read sheet Append1 from the Management Report master workbook (.xlsb)."""
from collections import namedtuple
import datetime as _dt

from pyxlsb import open_workbook

SHEET_NAME = "Append1"
REQUIRED_COLUMNS = ["COA", "MM", "YY", "CC", "Category", "Activity",
                    "Description", "PTA", "Custom", "MM.1", "ACT", "BGT"]

ParseResult = namedtuple("ParseResult", "rows dropped")


class ParseError(ValueError):
    """Raised with a user-facing message when the workbook cannot be used."""


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


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def normalise_rows(header, raw_rows) -> ParseResult:
    names = [_text(h) for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in names]
    if missing:
        raise ParseError("Kolom tidak ditemukan di sheet Append1: " + ", ".join(missing))
    ix = {n: i for i, n in enumerate(names)}

    rows, dropped = [], 0
    for raw in raw_rows:
        if all(v is None for v in raw):
            continue

        def g(name):
            i = ix[name]
            return raw[i] if i < len(raw) else None

        cc = _text(g("CC"))
        if cc in ("", "0"):
            dropped += 1
            continue
        rows.append({
            "coa": _text(g("COA")),
            "mm": _int(g("MM")),
            "yy": _int(g("YY")),
            "cc": cc,
            "category": _text(g("Category")) or "(blank)",
            "activity": _text(g("Activity")),
            "description": _text(g("Description")),
            "pta": _num(g("PTA")),
            "custom": _text(g("Custom")),
            "mm1": _int(g("MM.1")),
            "act": _num(g("ACT")),
            "bgt": _num(g("BGT")),
        })
    return ParseResult(rows, dropped)


def read_append1(fileobj) -> ParseResult:
    try:
        wb = open_workbook(fileobj)
    except Exception as e:
        raise ParseError(f"File tidak bisa dibaca sebagai .xlsb: {e}") from e
    try:
        with wb:
            if SHEET_NAME not in wb.sheets:
                raise ParseError(f"Sheet '{SHEET_NAME}' tidak ditemukan di file.")
            with wb.get_sheet(SHEET_NAME) as sh:
                it = ([c.v for c in r] for r in sh.rows())
                try:
                    header = next(it)
                except StopIteration:
                    raise ParseError("Sheet Append1 kosong.")
                return normalise_rows(header, it)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"File tidak bisa dibaca: {e}") from e


def _excel_date(v):
    try:
        return (_dt.date(1899, 12, 30) + _dt.timedelta(days=int(float(v)))).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def build_meta(report_pairs, period_value) -> dict:
    """CC descriptions from the (code, description) cells of Report!U10:V100 and the report period."""
    names = {}
    for code, name in report_pairs:
        code, name = _text(code), _text(name)
        if code and name and not code.startswith("0x") and not name.startswith("0x"):
            names[code] = name                       # '0x..' is how pyxlsb shows an Excel error cell
    return {"cc_names": names, "period": _excel_date(period_value)}


def read_meta(fileobj) -> dict:
    """Best effort: a missing sheet or cell leaves the field empty, the sync never fails because of it."""
    pairs, period = [], None
    try:
        with open_workbook(fileobj) as wb:
            if "Report" in wb.sheets:
                with wb.get_sheet("Report") as sh:
                    for row in sh.rows():
                        r = row[0].r
                        if r < 9:
                            continue
                        if r > 99:
                            break
                        pairs.append((row[20].v if len(row) > 20 else None,
                                      row[21].v if len(row) > 21 else None))
            if "Parameter" in wb.sheets:
                with wb.get_sheet("Parameter") as sh:
                    for row in sh.rows():
                        if row[0].r == 1:
                            period = row[1].v if len(row) > 1 else None
                            break
                        if row[0].r > 1:
                            break
    except Exception:
        pass
    return build_meta(pairs, period)
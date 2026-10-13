"""General Ledger MR: column specs of the Data tables and the Report, in ONE place.

Each spec is an ordered list of (key, header label, kind). The template loops over them and the tests
import them, so the headers always match the workbook sheets `GL Combine`, `Append1` and `Report`.

Kinds: text | rp (rupiah, thousands dots) | mio (Rp Mio, 1 decimal) | date (ISO -> dd/mm/yyyy)
       | int | yy2 (four-digit year shown as two digits).
"""

COMBINE = [
    ("account", "Account Management", "text"), ("id_no", "ID#", "text"), ("tgl", "Date", "date"),
    ("allocation_memo", "Allocation Memo", "text"), ("activity", "Budget Activity", "text"),
    ("cc", "COST CENTER", "text"), ("debit_credit", "DEBIT - CREDIT", "rp"), ("source", "Source", "text"),
    ("coa", "COA HO", "text"), ("cost_center2", "COST CENTER2", "text"), ("mm", "Month", "int"),
    ("cc0", "CC0", "text"), ("cc1", "CC1", "int"), ("bc1", "BC1", "text"), ("new_code", "New Code", "text"),
    ("description", "Memo", "text"), ("category", "BC", "text"),
]

APPEND1 = [
    ("coa", "COA", "text"), ("mm", "MM", "int"), ("yy", "YY", "yy2"), ("cc", "CC", "text"),
    ("cc", "CC.1", "text"), ("category", "Category", "text"), ("activity", "Activity", "text"),
    ("description", "Description", "text"), ("pta", "PTA", "mio"), ("custom", "Custom", "text"),
    ("mm1", "MM.1", "int"), ("act", "ACT", "mio"), ("bgt", "BGT", "mio"),
]

# Report columns after the five label columns (Category, Custom, MM.1, Description, Activity).
REPORT_LABELS = ["Category", "Custom", "MM.1", "Description", "Activity"]
REPORT_METRICS = [("bgt", "Sum of BGT"), ("pta", "Sum of PTA"), ("available", "BGT_Available"),
                  ("act", "Sum of ACT"), ("diff", "Diff_ACT-BGT"), ("pct", "Diff Percentage")]

TABLES = {"combine": ("GL Combine", COMBINE), "append1": ("Append1", APPEND1)}
DEFAULT_TABLE = "combine"


def resolve_table(name) -> str:
    """Requested Data table if known, otherwise GL Combine."""
    return name if name in TABLES else DEFAULT_TABLE

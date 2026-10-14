# tests/test_mrc_category_map.py
import pytest

from modules.management_report import category_map as cm
from modules.management_report.coa_map import CoaParseError

HEADER = [None, "COA SMT", "Description", "COA ETF", "Description", "FROM :", "COA HO",
          "Sub Account", "CATEGORIES", "CATEGORIES 2", None, "BUDGET CATEGORY",
          "CATEGORIES EXPENSE (6-****)", "Category LK", "Category SPT"]


def row(smt=None, etf=None, exp=None, lk=None, spt=None):
    r = [None] * 15
    r[1], r[3], r[12], r[13], r[14] = smt, etf, exp, lk, spt
    return r


def sheet(*rows):
    return [[None] * 15, HEADER, *rows]


def as_map(rows):
    return {(r["source"], r["account"]): (r["categories_expense"], r["category_lk"], r["category_spt"])
            for r in rows}


# ---------- parse ----------

def test_maps_smt_and_etf_accounts_with_stripped_categories():
    rows = cm.normalise_categories(sheet(
        row("6-1810", None, " Office Supplies And Equipment Expense ", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1720", "6-2150", "Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA")))
    assert as_map(rows) == {
        ("SMT", "6-1810"): ("Office Supplies And Equipment Expense", "Beban Operasional", "BIAYA LAINNYA"),
        ("SMT", "6-1720"): ("Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA"),
        ("ETF", "6-2150"): ("Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA"),
    }


def test_same_account_in_smt_and_etf_keeps_separate_categories():
    rows = cm.normalise_categories(sheet(
        row("6-1000", None, "", "Beban Operasional", "BIAYA LAINNYA"),
        row(None, "6-1000", "", "HARGA POKOK PENJUALAN", "BIAYA TRANSPORTASI")))
    assert as_map(rows) == {
        ("SMT", "6-1000"): ("", "Beban Operasional", "BIAYA LAINNYA"),
        ("ETF", "6-1000"): ("", "HARGA POKOK PENJUALAN", "BIAYA TRANSPORTASI"),
    }


def test_tba_is_normalised_and_zero_or_error_cells_are_empty():
    rows = cm.normalise_categories(sheet(
        row("6-1", None, "tba", "tba", "TBA"),
        row("6-2", None, 0.0, 0.0, "0x2a"),
        row("6-3", None, None, None, None)))
    # 6-2 (all cells 0 / error) and 6-3 (all empty) carry no category at all, so they are skipped
    assert as_map(rows) == {("SMT", "6-1"): ("TBA", "TBA", "TBA")}


def test_rows_without_any_account_are_skipped_and_duplicates_keep_first():
    rows = cm.normalise_categories(sheet(
        row(None, None, "x", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1", None, "a", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1", None, "b", "HARGA POKOK PENJUALAN", "BIAYA SEWA")))
    assert as_map(rows) == {("SMT", "6-1"): ("a", "Beban Operasional", "BIAYA LAINNYA")}


def test_numeric_account_is_text():
    rows = cm.normalise_categories(sheet(row(61810.0, None, "", "Beban Operasional", "BIAYA LAINNYA")))
    assert [r["account"] for r in rows] == ["61810"]


def test_wrong_header_or_empty_sheet_raises():
    bad = list(HEADER)
    bad[13] = "Kategori"
    with pytest.raises(CoaParseError, match="Category LK"):
        cm.normalise_categories([[None] * 15, bad])
    with pytest.raises(CoaParseError, match="kosong"):
        cm.normalise_categories([[None] * 15])


def test_is_unmapped():
    assert cm.is_unmapped("") and cm.is_unmapped("TBA") and cm.is_unmapped(" tba ")
    assert not cm.is_unmapped("BIAYA LAINNYA")


# ---------- storage ----------

RO = cm.normalise_categories(sheet(row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA")))


def test_sync_stores_logs_and_second_identical_sync_is_unchanged():
    out = cm.sync_categories("GL - MASTER.xlsb", "admin", RO)
    assert out == {"changed": True, "rows_smt": 1, "rows_etf": 0}
    assert cm.get_category_map()[("SMT", "6-1810")] == {
        "categories_expense": "Office", "category_lk": "Beban Operasional", "category_spt": "BIAYA LAINNYA"}
    assert cm.last_sync()["filename"] == "GL - MASTER.xlsb"
    again = cm.sync_categories("GL - MASTER.xlsb", "admin", RO)
    assert again["changed"] is False and len(cm.list_syncs()) == 1


def test_sync_replaces_previous_rows_and_bumps_version():
    cm.sync_categories("a.xlsb", "admin", RO)
    v1 = cm.get_version()
    other = cm.normalise_categories(sheet(row("6-2000", None, "", "HARGA POKOK PENJUALAN", "BIAYA SEWA")))
    cm.sync_categories("b.xlsb", "admin", other)
    assert list(cm.get_category_map()) == [("SMT", "6-2000")]
    assert cm.get_version() == v1 + 1
    assert [s["filename"] for s in cm.list_syncs()] == ["b.xlsb", "a.xlsb"]


def test_failed_sync_keeps_previous_mapping():
    cm.sync_categories("a.xlsb", "admin", RO)
    with pytest.raises(KeyError):
        cm.sync_categories("b.xlsb", "admin", [{"source": "SMT", "account": "x"}])
    assert list(cm.get_category_map()) == [("SMT", "6-1810")]
    assert cm.last_sync()["filename"] == "a.xlsb"


# ---------- M2: Kategori LK ----------

def _rows_with(*lks):
    return cm.normalise_categories(sheet(*[row(f"6-{i}", None, "", lk, "BIAYA LAINNYA")
                                          for i, lk in enumerate(lks, 1)]))


def test_sync_seeds_lk_list_with_defaults_and_skips_tba_and_empty():
    cm.sync_categories("a", "u", _rows_with("Beban Operasional", "Kategori Baru", "tba"))
    lk = cm.get_lk_list()
    assert set(lk) == {"Beban Operasional", "Kategori Baru"}
    bo = lk["Beban Operasional"]
    assert (bo["statement"], bo["kind"], bo["needs_spt"]) == ("laba_rugi", "beban", 1)
    assert lk["Kategori Baru"]["statement"] == "" and lk["Kategori Baru"]["label"] == "Kategori Baru"


def test_known_defaults_cover_pnl_and_balance_sheet_categories():
    assert cm.DEFAULT_LK["Jasa Konsultasi & Advokasi"][:2] == ("laba_rugi", "pendapatan")
    assert cm.DEFAULT_LK["HUTANG PAJAK"][0] == "neraca"
    assert cm.DEFAULT_LK["MODAL SAHAM"][0] == "neraca"
    assert cm.DEFAULT_LK["Income Tax Expense"][:2] == ("laba_rugi", "beban")


def test_resync_keeps_manual_lk_edits():
    cm.sync_categories("a", "u", _rows_with("Kategori Baru"))
    cm.update_lk("Kategori Baru", statement="neraca", kind="lainnya", seq=50, label="Baru", needs_spt=0)
    cm.sync_categories("b", "u", _rows_with("Kategori Baru", "Beban Operasional"))
    lk = cm.get_lk_list()["Kategori Baru"]
    assert (lk["statement"], lk["kind"], lk["seq"], lk["label"]) == ("neraca", "lainnya", 50, "Baru")


def test_lk_list_is_ordered_by_seq_then_name():
    cm.sync_categories("a", "u", _rows_with("Beban Operasional", "HARGA POKOK PENJUALAN", "Zeta", "Alfa"))
    assert list(cm.get_lk_list())[:2] == ["HARGA POKOK PENJUALAN", "Beban Operasional"]
    assert list(cm.get_lk_list())[2:] == ["Alfa", "Zeta"]          # unknown ones share seq 999


def test_update_lk_validates_and_bumps_version():
    cm.sync_categories("a", "u", _rows_with("Kategori Baru"))
    v = cm.get_version()
    with pytest.raises(ValueError):
        cm.update_lk("Kategori Baru", statement="salah", kind="", seq=1, label="x", needs_spt=0)
    with pytest.raises(ValueError):
        cm.update_lk("Kategori Baru", statement="neraca", kind="salah", seq=1, label="x", needs_spt=0)
    with pytest.raises(ValueError):
        cm.update_lk("Kategori Baru", statement="neraca", kind="", seq="abc", label="x", needs_spt=0)
    with pytest.raises(KeyError):
        cm.update_lk("tidak ada", statement="neraca", kind="", seq=1, label="x", needs_spt=0)
    assert cm.get_version() == v                                     # nothing changed
    cm.update_lk("Kategori Baru", statement="neraca", kind="", seq=3, label=" Baru ", needs_spt=1)
    got = cm.get_lk_list()["Kategori Baru"]
    assert (got["statement"], got["seq"], got["label"], got["needs_spt"]) == ("neraca", 3, "Baru", 1)
    assert cm.get_version() == v + 1


# ---------- M3: alias jenis PPh ----------

def test_alias_key_ignores_case_spaces_and_dashes():
    assert cm.alias_key(" PPh 4 (2) ") == "pph4(2)"
    assert cm.alias_key("non-PPH") == "nonpph"
    assert cm.alias_key("Non  PPh") == "nonpph"


def test_default_aliases_cover_the_four_types():
    assert cm.get_pph_aliases() == {"pph21": "PPh 21", "pph23": "PPh 23",
                                    "pph4(2)": "PPh 4(2)", "nonpph": "Non PPh"}


def test_add_and_delete_alias_bump_version():
    v = cm.get_version()
    key = cm.add_pph_alias("PPh 4 ayat 2", "PPh 4(2)")
    assert key == "pph4ayat2" and cm.get_pph_aliases()[key] == "PPh 4(2)"
    assert cm.get_version() == v + 1
    cm.delete_pph_alias(key)
    assert key not in cm.get_pph_aliases() and cm.get_version() == v + 2


def test_alias_validation_and_default_alias_is_protected():
    for bad_alias, bad_type in (("", "PPh 21"), ("  ", "PPh 21"), ("x", "PPh 99")):
        with pytest.raises(ValueError):
            cm.add_pph_alias(bad_alias, bad_type)
    with pytest.raises(ValueError):
        cm.delete_pph_alias("pph21")
    assert "pph21" in cm.get_pph_aliases()
    with pytest.raises(KeyError):
        cm.delete_pph_alias("tidak-ada")


# ---------- search + unmapped ----------

from modules.general_ledger import service as gl_service
from tests.test_gl_sync import mkrow

GL_LOG = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
              total_debit=0, total_credit=0, dropped=0, summary={})


def seed_gl(entity, *accounts):
    rows = [mkrow(acc_statutory=a, tgl="2026-01-02", debit_credit=amt) for a, amt in accounts]
    gl_service.replace_year(entity, 2026, rows, GL_LOG)


def test_search_accounts_filters_by_source_and_text_and_pages():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(
        row("6-1810", "6-2150", "Office", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1720", None, "Gift", "HARGA POKOK PENJUALAN", "BIAYA SEWA"))))
    assert cm.search_accounts()["total"] == 3
    assert cm.search_accounts("ETF")["total"] == 1
    assert [r["account"] for r in cm.search_accounts(None, "gift")["rows"]] == ["6-1720"]
    assert cm.search_accounts(None, "biaya sewa")["rows"][0]["category_spt"] == "BIAYA SEWA"
    assert cm.search_accounts(None, "", page=99)["page"] == 1


def test_unmapped_accounts_reasons_and_ordering():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(
        row("6-ok", None, "", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-tba", None, "", "TBA", "TBA"),
        row("6-nospt", None, "", "HARGA POKOK PENJUALAN", "TBA"),
        row("6-noreport", None, "", "Kategori Baru", "BIAYA LAINNYA"),
        row("1-bank", None, "", "KAS DAN SETARA KAS", ""))))
    seed_gl("smt", ("6-ok", 5.0), ("6-tba", 10.0), ("6-nospt", -30.0), ("6-noreport", 2.0),
            ("1-bank", 100.0), ("9-missing", 1.0))
    got = {u["account"]: u for u in cm.unmapped_accounts(2026)}
    assert set(got) == {"6-tba", "6-nospt", "6-noreport", "9-missing"}
    assert got["6-tba"]["reason"] == "Category LK kosong / TBA"
    assert got["6-nospt"]["reason"] == "Category SPT kosong / TBA"
    assert got["6-noreport"]["reason"] == "Category LK belum diatur jenis laporannya"
    assert got["9-missing"]["reason"] == "Akun tidak ada di pemetaan kategori"
    assert got["6-nospt"]["source"] == "SMT" and got["6-nospt"]["rows"] == 1
    assert [u["account"] for u in cm.unmapped_accounts(2026)][0] == "6-nospt"      # biggest |amount| first


def test_unmapped_accounts_is_empty_for_other_years_and_when_everything_is_mapped():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(
        row("6-ok", None, "", "Beban Operasional", "BIAYA LAINNYA"))))
    seed_gl("smt", ("6-ok", 5.0))
    assert cm.unmapped_accounts(2026) == [] and cm.unmapped_accounts(2025) == []


def test_unmapped_accounts_keeps_smt_and_etf_apart():
    cm.sync_categories("a", "u", cm.normalise_categories(sheet(row("6-x", None, "", "Beban Operasional", "BIAYA LAINNYA"))))
    seed_gl("etf", ("6-x", 5.0))                                   # only SMT knows 6-x
    assert [(u["source"], u["account"]) for u in cm.unmapped_accounts(2026)] == [("ETF", "6-x")]

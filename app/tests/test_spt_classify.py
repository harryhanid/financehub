# tests/test_spt_classify.py
from modules.spt_badan import classify as cl

ALIASES = {"pph21": "PPh 21", "pph23": "PPh 23", "pph4(2)": "PPh 4(2)", "nonpph": "Non PPh"}
LK = {
    "Beban Operasional": {"statement": "laba_rugi", "kind": "beban", "seq": 3, "label": "BO", "needs_spt": 1},
    "KAS DAN SETARA KAS": {"statement": "neraca", "kind": "lainnya", "seq": 1, "label": "Kas", "needs_spt": 0},
    "Kategori Baru": {"statement": "", "kind": "", "seq": 999, "label": "Baru", "needs_spt": 0},
}
CMAP = {
    ("SMT", "6-1000"): {"categories_expense": "", "category_lk": "Beban Operasional", "category_spt": "BIAYA LAINNYA"},
    ("SMT", "1-1000"): {"categories_expense": "", "category_lk": "KAS DAN SETARA KAS", "category_spt": ""},
    ("SMT", "6-tba"): {"categories_expense": "", "category_lk": "TBA", "category_spt": "TBA"},
    ("SMT", "6-nospt"): {"categories_expense": "", "category_lk": "Beban Operasional", "category_spt": "TBA"},
    ("SMT", "6-baru"): {"categories_expense": "", "category_lk": "Kategori Baru", "category_spt": "X"},
}


def line(**kw):
    base = {"id": 1, "tgl": "2026-01-02", "id_no": "GJ-1", "acc_statutory": "6-1000",
            "acc_management": "6-1000", "job_name": "POCFAD", "memo": "m", "debit_credit": 10.0,
            "category_lk": "Beban Operasional", "category_spt": "BIAYA LAINNYA",
            "pph_non_pph": "PPh 21", "accrual_actual": "Actual"}
    base.update(kw)
    return base


def run(**kw):
    return cl.classify_line(line(**kw), "SMT", CMAP, LK, ALIASES)


def kinds(exceptions):
    return sorted((e["kind"], e["severity"]) for e in exceptions)


def test_clean_line_has_no_exceptions_and_carries_classification():
    c, ex = run()
    assert ex == []
    assert c == {"gl_id": 1, "tgl": "2026-01-02", "id_no": "GJ-1", "acc_statutory": "6-1000",
                 "acc_management": "6-1000", "job_name": "POCFAD", "memo": "m", "debit_credit": 10.0,
                 "accrual_actual": "Actual", "category_lk": "Beban Operasional",
                 "category_spt": "BIAYA LAINNYA", "pph_type_raw": "PPh 21", "pph_type": "PPh 21"}


def test_pph_aliases_ignore_case_spaces_and_dashes():
    for raw, want in [("pph 23", "PPh 23"), ("PPH23", "PPh 23"), ("Non-PPh", "Non PPh"),
                      ("non pph", "Non PPh"), (" PPh 4 (2) ", "PPh 4(2)")]:
        c, ex = run(pph_non_pph=raw)
        assert (c["pph_type"], ex) == (want, []), raw
        assert c["pph_type_raw"] == raw.strip()


def test_blank_pph_on_an_expense_line_is_a_warning():
    c, ex = run(pph_non_pph="")
    assert c["pph_type"] == "" and kinds(ex) == [("pph_kosong", "warning")]


def test_blank_pph_on_a_balance_sheet_line_is_ignored():
    c, ex = cl.classify_line(line(acc_statutory="1-1000", category_lk="KAS DAN SETARA KAS",
                                  category_spt="", pph_non_pph=""), "SMT", CMAP, LK, ALIASES)
    assert ex == [] and c["category_lk"] == "KAS DAN SETARA KAS"


def test_cost_center_code_in_the_pph_column_is_a_warning():
    for raw in ("POSENG", "$POITEC", "TFKHAR"):
        c, ex = run(pph_non_pph=raw)
        assert c["pph_type"] == "" and c["pph_type_raw"] == raw
        assert kinds(ex) == [("pph_bukan_jenis", "warning")], raw


def test_account_missing_from_the_mapping_is_a_blocker():
    c, ex = cl.classify_line(line(acc_statutory="9-none"), "SMT", CMAP, LK, ALIASES)
    assert kinds(ex)[0] == ("akun_belum_dipetakan", "blocker")
    assert c["category_lk"] == "" and c["category_spt"] == ""


def test_same_account_is_looked_up_per_source():
    c, ex = cl.classify_line(line(), "ETF", CMAP, LK, ALIASES)
    assert ("akun_belum_dipetakan", "blocker") in kinds(ex)


def test_tba_category_lk_is_a_blocker():
    c, ex = run(acc_statutory="6-tba")
    assert ("akun_belum_dipetakan", "blocker") in kinds(ex) and c["category_lk"] == ""


def test_category_lk_without_report_type_is_a_blocker_but_is_kept_on_the_line():
    c, ex = run(acc_statutory="6-baru")
    assert ("category_lk_tidak_dikenal", "blocker") in kinds(ex)
    assert c["category_lk"] == "Kategori Baru"


def test_expense_line_with_tba_category_spt_is_a_blocker_and_spt_is_stored_empty():
    c, ex = run(acc_statutory="6-nospt")
    assert ("category_spt_kosong", "blocker") in kinds(ex) and c["category_spt"] == ""


def test_gl_row_categories_that_differ_from_the_mapping_are_a_warning():
    c, ex = run(category_spt="BIAYA SEWA")
    assert kinds(ex) == [("kategori_gl_beda", "warning")]
    assert c["category_spt"] == "BIAYA LAINNYA"                       # mapping wins
    c, ex = run(category_lk="beban operasional")                       # case only: not a difference
    assert ex == []


def test_account_is_matched_as_text():
    c, ex = cl.classify_line(line(acc_statutory=None), "SMT", CMAP, LK, ALIASES)
    assert ("akun_belum_dipetakan", "blocker") in kinds(ex)


def test_laba_rugi_category_without_kind_is_a_blocker_naming_the_missing_sifat():
    lk = {"Aneh": {"statement": "laba_rugi", "kind": "", "seq": 9, "label": "Aneh", "needs_spt": 0}}
    cmap = {("SMT", "6-1"): {"category_lk": "Aneh", "category_spt": ""}}
    item, excs = cl.classify_line(
        {"id": 1, "tgl": "2026-01-02", "id_no": "x", "acc_statutory": "6-1", "acc_management": "6-1",
         "job_name": "", "memo": "", "debit_credit": 5.0, "accrual_actual": "", "category_lk": "Aneh",
         "category_spt": "", "pph_non_pph": ""}, "SMT", cmap, lk, {})
    blockers = [e for e in excs if e["kind"] == "category_lk_tidak_dikenal"]
    assert len(blockers) == 1 and blockers[0]["severity"] == "blocker"
    assert "belum diatur sifatnya" in blockers[0]["detail"] and "'Aneh'" in blockers[0]["detail"]

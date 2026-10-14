# tests/test_spt_statement.py
from modules.spt_badan import controls as ct
from modules.spt_badan import income_statement as inc

LK = {
    "Jasa Konsultasi & Advokasi": {"statement": "laba_rugi", "kind": "pendapatan", "seq": 1, "label": "Jasa", "needs_spt": 0},
    "HARGA POKOK PENJUALAN": {"statement": "laba_rugi", "kind": "beban", "seq": 2, "label": "HPP", "needs_spt": 1},
    "Beban Operasional": {"statement": "laba_rugi", "kind": "beban", "seq": 3, "label": "Beban Operasional", "needs_spt": 1},
    "Pendapatan (Beban) Lainnya": {"statement": "laba_rugi", "kind": "lainnya", "seq": 4, "label": "Pendapatan (Beban) Lainnya", "needs_spt": 1},
    "Bunga Jasa Giro": {"statement": "laba_rugi", "kind": "lainnya", "seq": 5, "label": "Bunga Jasa Giro", "needs_spt": 0},
    "Income Tax Expense": {"statement": "laba_rugi", "kind": "beban", "seq": 6, "label": "Income Tax Expense", "needs_spt": 0},
    "KAS DAN SETARA KAS": {"statement": "neraca", "kind": "lainnya", "seq": 1, "label": "Kas", "needs_spt": 0},
}


def ln(lk, spt, amount):
    return {"category_lk": lk, "category_spt": spt, "debit_credit": amount}


LINES = [ln("Jasa Konsultasi & Advokasi", "", -1000.0),
         ln("HARGA POKOK PENJUALAN", "GAJI", 300.0), ln("HARGA POKOK PENJUALAN", "BIAYA SEWA", 100.0),
         ln("Beban Operasional", "BIAYA LAINNYA", 200.0),
         ln("Bunga Jasa Giro", "", -50.0), ln("Pendapatan (Beban) Lainnya", "BIAYA LAINNYA", 10.0),
         ln("Income Tax Expense", "", 80.0), ln("KAS DAN SETARA KAS", "", 360.0),
         ln("", "", 5.0)]                                              # unclassified line is ignored


def statement(lines=LINES, lk=LK):
    totals, spt = inc.aggregate(lines)
    return inc.build_income_statement(totals, spt, lk)


def test_aggregate_sums_per_category_and_spt_and_ignores_unclassified():
    totals, spt = inc.aggregate(LINES)
    assert totals["HARGA POKOK PENJUALAN"] == 400.0 and "" not in totals
    assert spt[("HARGA POKOK PENJUALAN", "GAJI")] == 300.0
    assert spt[("Jasa Konsultasi & Advokasi", "")] == -1000.0


def test_summary_signs_and_subtotals():
    s = statement()["summary"]
    assert s == {"revenue": 1000.0, "hpp": 400.0, "gross": 600.0, "opex": 200.0, "operating": 400.0,
                 "other": 40.0, "pbt": 440.0, "tax": 80.0, "net": 360.0}


def test_rows_layout_with_sub_rows_and_drill_hints():
    rows = statement()["rows"]
    top = [(r["label"], r["amount"]) for r in rows if r["kind"] != "sub"]
    assert top == [("Pendapatan bersih", 1000.0), ("Harga pokok penjualan", 400.0), ("Laba kotor", 600.0),
                   ("Biaya operasional", 200.0), ("Laba operasional", 400.0), ("Pendapatan (Beban) Lainnya", -10.0),
                   ("Bunga Jasa Giro", 50.0), ("Laba sebelum pajak penghasilan", 440.0),
                   ("Income tax expense", 80.0), ("Laba (rugi) bersih", 360.0)]
    hpp_subs = [(r["label"], r["amount"], r["spt"]) for r in rows
                if r["kind"] == "sub" and r["cats"] == ["HARGA POKOK PENJUALAN"]]
    assert hpp_subs == [("GAJI", 300.0, "GAJI"), ("BIAYA SEWA", 100.0, "BIAYA SEWA")]
    revenue = next(r for r in rows if r["key"] == "revenue")
    assert revenue["cats"] == ["Jasa Konsultasi & Advokasi"] and revenue["spt"] is None
    assert next(r for r in rows if r["key"] == "gross")["cats"] is None


def test_blank_spt_gets_a_label_but_keeps_an_empty_drill_value():
    rows = statement([ln("HARGA POKOK PENJUALAN", "", 50.0)])["rows"]
    sub = next(r for r in rows if r["kind"] == "sub")
    assert sub["label"] == inc.NO_SPT_LABEL and sub["spt"] == "" and sub["amount"] == 50.0


def test_missing_categories_give_zero_and_other_expense_goes_to_opex():
    lk = dict(LK, **{"Beban Lain": {"statement": "laba_rugi", "kind": "beban", "seq": 9,
                                    "label": "Beban Lain", "needs_spt": 0}})
    s = statement([ln("Beban Lain", "", 7.0)], lk)["summary"]
    assert s["opex"] == 7.0 and s["revenue"] == 0.0 and s["pbt"] == -7.0
    assert statement([], {})["summary"]["net"] == 0.0


def test_categories_without_a_laba_rugi_kind_stay_out_of_the_statement():
    lk = dict(LK, **{"Aneh": {"statement": "laba_rugi", "kind": "", "seq": 9, "label": "Aneh", "needs_spt": 0}})
    assert statement([ln("Aneh", "", 9.0)], lk)["summary"]["pbt"] == 0.0


# ---------- controls ----------

def run_controls(**kw):
    base = dict(total_debit=100.0, total_credit=100.0, line_count=5, gl_row_count=5, exceptions=[],
                out_of_year=0, statement_pbt=440.0, pnl_sum_excl_tax=440.0)
    base.update(kw)
    return {c["code"]: c for c in ct.compute_controls(**base)}


def test_all_clean_controls_pass():
    cs = run_controls()
    assert list(cs) == ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C9"]
    assert all(c["status"] == "lulus" for c in cs.values())
    assert cs["C1"]["blocking"] and not cs["C7"]["blocking"] and not cs["C9"]["blocking"]


def test_money_tolerance_applies_to_c1_and_c6_only():
    assert run_controls(total_credit=100.5)["C1"]["status"] == "lulus"
    assert run_controls(total_credit=102.0)["C1"]["status"] == "gagal"
    assert run_controls(statement_pbt=441.0, pnl_sum_excl_tax=440.0)["C6"]["status"] == "lulus"
    assert run_controls(statement_pbt=445.0)["C6"]["status"] == "gagal"
    assert run_controls(gl_row_count=6)["C2"]["status"] == "gagal"


def test_exceptions_are_counted_per_control():
    ex = [{"kind": "akun_belum_dipetakan"}, {"kind": "category_lk_tidak_dikenal"},
          {"kind": "category_spt_kosong"}, {"kind": "pph_kosong"}, {"kind": "pph_bukan_jenis"},
          {"kind": "kategori_gl_beda"}]
    cs = run_controls(exceptions=ex)
    assert (cs["C3"]["left_value"], cs["C3"]["status"]) == (2, "gagal")
    assert (cs["C4"]["left_value"], cs["C4"]["status"]) == (1, "gagal")
    assert (cs["C7"]["left_value"], cs["C7"]["status"]) == (2, "peringatan")
    assert (cs["C9"]["left_value"], cs["C9"]["status"]) == (1, "peringatan")
    assert run_controls(out_of_year=3)["C5"]["status"] == "gagal"


def test_stale_control():
    assert ct.stale_control([])["status"] == "lulus"
    c = ct.stale_control(["GL berubah sejak snapshot"])
    assert (c["code"], c["status"], c["blocking"]) == ("C8", "peringatan", False)
    assert c["left_value"] == 1 and "GL berubah" in c["name"]

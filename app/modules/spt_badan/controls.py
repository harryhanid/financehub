# modules/spt_badan/controls.py
"""SPT Badan: control checks C1-C9 (pure functions)."""
from modules.spt_badan.classify import PPH_KINDS

TOL_MONEY = 1.0


def _control(code, name, left, right, blocking, tol=0.0):
    diff = left - right
    if abs(diff) <= tol:
        status = "lulus"
    else:
        status = "gagal" if blocking else "peringatan"
    return {"code": code, "name": name, "left_value": left, "right_value": right,
            "diff": diff, "status": status, "blocking": 1 if blocking else 0}


def _count(exceptions, kinds):
    return sum(1 for e in exceptions if e["kind"] in kinds)


def compute_controls(*, total_debit, total_credit, line_count, gl_row_count, exceptions, out_of_year,
                     statement_pbt, pnl_sum_excl_tax):
    """pnl_sum_excl_tax is profit-positive: -(sum of debit_credit of laba_rugi lines except
    Income Tax Expense). It must equal statement_pbt (the raw GL sum is negative for a profit)."""
    return [
        _control("C1", "Total debit = total kredit", total_debit, total_credit, True, TOL_MONEY),
        _control("C2", "Jumlah baris snapshot = jumlah baris GL", line_count, gl_row_count, True),
        _control("C3", "Semua akun terpetakan dan Category LK dikenal",
                 _count(exceptions, ("akun_belum_dipetakan", "category_lk_tidak_dikenal")), 0, True),
        _control("C4", "Semua baris HPP/biaya punya Category SPT",
                 _count(exceptions, ("category_spt_kosong",)), 0, True),
        _control("C5", "Semua tanggal berada di tahun pajak", out_of_year, 0, True),
        _control("C6", "Laba sebelum pajak = jumlah baris laba rugi di GL",
                 statement_pbt, pnl_sum_excl_tax, True, TOL_MONEY),
        _control("C7", "Jenis PPh bersih (tanpa kosong / bukan jenis)",
                 _count(exceptions, PPH_KINDS), 0, False),
        _control("C9", "Kategori pada baris GL = hasil Pemetaan",
                 _count(exceptions, ("kategori_gl_beda",)), 0, False),
    ]


def stale_control(reasons):
    name = "Snapshot masih sesuai GL dan Pemetaan"
    if reasons:
        name += " (" + "; ".join(reasons) + ")"
    return _control("C8", name, len(reasons), 0, False)

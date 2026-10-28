# tests/test_prportal_pa_to_pam.py -- Review akhir F4 (spec kriteria penerimaan 3):
# PA yang dibuat PR Portal (fn_prp_submit_pa) bisa ditarik ke PAM lewat Payment Memo -> Input PA
# (get_draft_lines_for_siswa + save_pa_payment) tanpa perubahan apa pun.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from modules.etf_payment_application.service import get_draft_lines_for_siswa
from modules.payment_memo.service import save_pa_payment
from tests.test_prportal_fn import _siswa, _budget, _payload, _submit

COMPANY_ID = 2
COMPANY_CODE = "ETF"


def test_prportal_pa_pulled_into_pam_via_input_pa():
    _siswa("P1", "Pam Satu")
    _budget("P1", "By Pendidikan", "Semester 3", amount=5_000_000)
    conn = get_conn()
    bid = conn.execute("SELECT id FROM budget_beasiswa WHERE siswa_code='P1'").fetchone()["id"]
    sid = conn.execute("SELECT id FROM siswa WHERE code='P1'").fetchone()["id"]
    conn.close()
    res = _submit(_payload("P1", [{"budget_id": bid, "tahun_ajaran": "2026/2027", "jumlah": 4_000_000}]))
    assert res.get("ok") is True, res
    pa_number = res["pa_number"]

    # Seperti UI Input PA: ambil baris draft siswa, lalu kirim baris dengan etf_pa_line_id.
    lines = get_draft_lines_for_siswa(COMPANY_ID, sid, "agri")
    assert len(lines) == 1, lines
    line = lines[0]
    pam_no = "PAM-901-ETF-10-2026"
    out = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-10-28", "pam_no": pam_no, "keterangan": "PA dari PR Portal",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "P1", "etf_pa_line_id": line["line_id"],
                  "cat1": line["jenis_pembayaran"], "cat2": line["semester"],
                  "amount": line["jumlah_pembayaran"],
                  "tgl_pengajuan": line.get("tgl_surat_pengajuan") or "",
                  "tgl_receive": line.get("doc_received_by_educ") or "",
                  "tgl_pa": line.get("tgl_payment_application") or "", "tgl_final": ""}],
    })
    assert out["ok"] is True, out

    conn = get_conn()
    try:
        pa = conn.execute("SELECT status, nomor_pam, source FROM etf_pa WHERE pa_number=?",
                          (pa_number,)).fetchone()
        pbs = conn.execute("SELECT amount, pam, etf_pa_line_id, siswa_code FROM payment_beasiswa "
                           "WHERE company_id=?", (COMPANY_ID,)).fetchall()
        pam = conn.execute("SELECT total_amount, status FROM pam_records WHERE pam_no=?", (pam_no,)).fetchone()
    finally:
        conn.close()
    assert pa["source"] == "prportal"
    assert pa["status"] == "on_process" and pa["nomor_pam"] == pam_no
    assert [(float(p["amount"]), p["pam"], p["etf_pa_line_id"], p["siswa_code"]) for p in pbs] == \
        [(4_000_000.0, pam_no, line["line_id"], "P1")]
    assert float(pam["total_amount"]) == 4_000_000 and pam["status"] == "open"

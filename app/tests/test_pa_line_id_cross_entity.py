"""payment_beasiswa.etf_pa_line_id tidak unik lintas entitas: id baris PA adalah serial per tabel
(etf/app/sml/energy/setf_pa_lines), jadi id yang sama bisa ada di beberapa tabel. Semua lookup
dari baris PA ke payment_beasiswa (dan sebaliknya) wajib memfilter pillar entitasnya.

Regresi produksi 2026-10: edit baris PA SETF menimpa amount payment_beasiswa LAND ber-id baris
sama (PAM-002-LAND-07-2026 dan PAM-004-LAND-09-2026)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from database import get_conn
from modules.etf_payment_application.service import create_pa, update_pa
from modules.payment_memo.service import remove_student_from_pam

COMPANY_ID = 2


@pytest.fixture(autouse=True)
def seed(clean_db):
    conn = get_conn()
    for code in ("1250720", "5260003"):
        conn.execute(
            """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan,
               program, fakultas, universitas, status)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (COMPANY_ID, code, f"Siswa {code}", "S1", 2025, "SMART", "Teknik", "UI", "Aktif"))
    conn.commit()
    conn.close()
    yield


def _sid(code):
    conn = get_conn()
    row = conn.execute("SELECT id FROM siswa WHERE code=?", (code,)).fetchone()
    conn.close()
    return row["id"]


def _make_pa(tab, code, amount, jenis="By Tunjangan", semester="Semester 2"):
    r = create_pa(COMPANY_ID, {"tgl_payment_application": "2026-07-01"}, [
        {"student_id": _sid(code), "jenis_pembayaran": jenis, "semester": semester,
         "tahun_ajaran": "2025/2026", "ipk_sem_sebelumnya": 3.5, "jumlah_pembayaran": amount}
    ], tab=tab)
    assert r["ok"], r
    conn = get_conn()
    line_id = conn.execute(
        f"SELECT id FROM {'etf' if tab == 'agri' else tab}_pa_lines WHERE pa_id=?",
        (r["pa_id"],)).fetchone()["id"]
    conn.close()
    return r["pa_id"], line_id


def _draw_into_pam(pam_no, pillar, code, amount, line_id, pa_tbl=None, pa_id=None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO pam_records (company_id, pam_no, pam_date, total_amount, dpp, pillar,
           source, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-07-27", amount, amount, pillar, "beasiswa", "open",
         "2026-07-27T00:00:00"))
    conn.execute(
        """INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount,
           pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, code, "By Tunjangan", "Semester 2", "2026-07-27", amount, pillar,
         "PT X", pam_no, line_id))
    if pa_tbl:
        conn.execute(f"UPDATE {pa_tbl} SET status='on_process', nomor_pam=? WHERE id=?",
                     (pam_no, pa_id))
    conn.commit()
    conn.close()


def _pb_amount(pam_no):
    conn = get_conn()
    row = conn.execute("SELECT amount FROM payment_beasiswa WHERE pam=?", (pam_no,)).fetchone()
    tot = conn.execute("SELECT total_amount FROM pam_records WHERE pam_no=?", (pam_no,)).fetchone()
    conn.close()
    return float(row["amount"]), float(tot["total_amount"])


def _edit_line(tab, pa_id, line_id, amount):
    return update_pa(pa_id, COMPANY_ID, {
        "status": "open", "tgl_payment_application": "2026-07-01", "line_id": line_id,
        "jenis_pembayaran": "By Medical", "semester": "Rawat Jalan",
        "tahun_ajaran": "2026/2027", "jumlah_pembayaran": amount}, tab=tab)


def test_edit_setf_line_does_not_touch_land_payment_with_same_line_id():
    _, land_line = _make_pa("sml", "1250720", 6_000_000)
    setf_pa, setf_line = _make_pa("setf", "5260003", 1_000_000, jenis="By Medical")
    assert land_line == setf_line  # serial per tabel -> id sama
    _draw_into_pam("PAM-002-LAND-07-2026", "LAND", "1250720", 6_000_000, land_line)

    r = _edit_line("setf", setf_pa, setf_line, 7_805_485)

    assert r["ok"], r
    assert _pb_amount("PAM-002-LAND-07-2026") == (6_000_000, 6_000_000)


def test_edit_setf_line_still_propagates_to_its_own_payment():
    _, land_line = _make_pa("sml", "1250720", 6_000_000)
    setf_pa, setf_line = _make_pa("setf", "5260003", 1_000_000, jenis="By Medical")
    _draw_into_pam("PAM-002-LAND-07-2026", "LAND", "1250720", 6_000_000, land_line)
    _draw_into_pam("PAM-001-SETF-07-2026", "SETF", "5260003", 1_000_000, setf_line)

    r = _edit_line("setf", setf_pa, setf_line, 7_805_485)

    assert r["ok"], r
    assert _pb_amount("PAM-001-SETF-07-2026") == (7_805_485, 7_805_485)
    assert _pb_amount("PAM-002-LAND-07-2026") == (6_000_000, 6_000_000)


def test_edit_blocked_only_by_own_entity_pam_status():
    _, land_line = _make_pa("sml", "1250720", 6_000_000)
    setf_pa, setf_line = _make_pa("setf", "5260003", 1_000_000, jenis="By Medical")
    _draw_into_pam("PAM-002-LAND-07-2026", "LAND", "1250720", 6_000_000, land_line)
    conn = get_conn()
    conn.execute("UPDATE pam_records SET status='complete' WHERE pam_no='PAM-002-LAND-07-2026'")
    conn.commit()
    conn.close()

    # PAM LAND yang sudah complete bukan milik baris SETF ini -> edit tidak boleh diblokir.
    r = _edit_line("setf", setf_pa, setf_line, 2_000_000)

    assert r["ok"], r


def test_remove_land_student_reverts_land_pa_not_agri_pa_with_same_line_id():
    agri_pa, agri_line = _make_pa("agri", "5260003", 5_000_000)
    land_pa, land_line = _make_pa("sml", "1250720", 6_000_000)
    assert agri_line == land_line
    conn = get_conn()
    conn.execute("UPDATE etf_pa SET status='on_process', nomor_pam='PAM-001-ETF-07-2026' WHERE id=?",
                 (agri_pa,))
    conn.commit()
    conn.close()
    _draw_into_pam("PAM-002-LAND-07-2026", "LAND", "1250720", 6_000_000, land_line,
                   pa_tbl="sml_pa", pa_id=land_pa)
    conn = get_conn()
    pb_id = conn.execute("SELECT id FROM payment_beasiswa WHERE pam='PAM-002-LAND-07-2026'"
                         ).fetchone()["id"]
    conn.close()

    r = remove_student_from_pam(pb_id, COMPANY_ID)

    assert r["ok"], r
    conn = get_conn()
    agri = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (agri_pa,)).fetchone()
    land = conn.execute("SELECT status, nomor_pam FROM sml_pa WHERE id=?", (land_pa,)).fetchone()
    conn.close()
    assert (agri["status"], agri["nomor_pam"]) == ("on_process", "PAM-001-ETF-07-2026")
    assert (land["status"], land["nomor_pam"]) == ("open", None)

# tests/test_prportal_verif.py -- verifikasi Verificator PA Beasiswa (PA Verified PO Fin) + riwayat serah terima.
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from tests.test_prportal_fn import _today
from tests.test_prportal_serah import _call, _ready, OWNER, FINANCE

VERIF = "verif@sinarmas.test"


def _with_pam(pa_id, no="PAM/ETF/021/2026"):
    conn = get_conn()
    try:
        conn.execute("UPDATE etf_pa SET nomor_pam=? WHERE id=?", (no, pa_id))
        conn.commit()
    finally:
        conn.close()


def _log(num):
    conn = get_conn()
    try:
        return json.loads(conn.execute("SELECT fn_prp_serah_log(?)::text", (num,)).fetchone()[0])
    finally:
        conn.close()


def _kej(num):
    return [r["kejadian"] for r in _log(num)["rows"]]


def _row2(pa_id):
    conn = get_conn()
    try:
        return conn.execute("SELECT serah_status, pa_received_by_po_fin, pa_verified_by_po_fin, verif_by, verif_at, verif_catatan, "
                            "serah_catatan FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    finally:
        conn.close()


def _to_verif(code, pam=True):
    """PA siap diverifikasi: diserahkan pemohon lalu diterima Finance (opsional sudah ada PAM)."""
    pa_id, num = _ready(code)
    assert _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})["ok"] is True
    assert _call("fn_prp_terima_pa", {"pa_number": num, "oleh": FINANCE})["ok"] is True
    if pam:
        _with_pam(pa_id)
    return pa_id, num


def test_terima_moves_to_menunggu_verifikasi_and_logs():
    pa_id, num = _to_verif("V1", pam=False)
    assert _row2(pa_id)["serah_status"] == "menunggu_verifikasi"
    assert _kej(num) == ["diserahkan", "diterima_finance"]


def test_verifikasi_requires_pam_and_state():
    pa_id, num = _ready("V2")
    assert _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})["ok"] is False      # belum diserahkan/diterima
    _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    assert _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})["ok"] is False      # masih menunggu Finance
    _call("fn_prp_terima_pa", {"pa_number": num, "oleh": FINANCE})
    r = _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})
    assert r["ok"] is False and "Nomor PAM" in r["pesan"]
    assert _row2(pa_id)["serah_status"] == "menunggu_verifikasi" and not _row2(pa_id)["pa_verified_by_po_fin"]
    _with_pam(pa_id)
    assert _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": ""})["ok"] is False
    assert _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})["ok"] is True


def test_verifikasi_sets_date_and_terverifikasi():
    pa_id, num = _to_verif("V3")
    out = _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF.upper()})
    assert out == {"ok": True, "tanggal": _today()}
    row = _row2(pa_id)
    assert row["serah_status"] == "terverifikasi" and row["pa_verified_by_po_fin"] == _today()
    assert row["verif_by"] == VERIF and row["verif_at"].startswith(_today())
    assert _kej(num)[-1] == "terverifikasi"


def test_tolak_verifikasi_returns_to_finance_with_reason():
    pa_id, num = _to_verif("V4")
    for bad in ("", "   ", "x" * 301):
        assert _call("fn_prp_tolak_verifikasi_pa", {"pa_number": num, "oleh": VERIF, "alasan": bad})["ok"] is False
    assert _row2(pa_id)["serah_status"] == "menunggu_verifikasi"
    ok = _call("fn_prp_tolak_verifikasi_pa", {"pa_number": num, "oleh": VERIF, "alasan": "  PAM belum lengkap <b>  "})
    assert ok["ok"] is True
    row = _row2(pa_id)
    assert row["serah_status"] == "dikembalikan" and row["verif_catatan"] == "PAM belum lengkap <b>"
    assert not row["pa_verified_by_po_fin"]
    rows = _log(num)["rows"]
    assert rows[-1]["kejadian"] == "dikembalikan_verificator" and rows[-1]["catatan"] == "PAM belum lengkap <b>" and rows[-1]["oleh"] == VERIF
    assert _call("fn_prp_tolak_verifikasi_pa", {"pa_number": num, "oleh": VERIF, "alasan": "lagi"})["ok"] is False


def test_teruskan_only_from_dikembalikan():
    pa_id, num = _to_verif("V5")
    assert _call("fn_prp_teruskan_pa", {"pa_number": num, "oleh": FINANCE})["ok"] is False   # masih menunggu_verifikasi
    _call("fn_prp_tolak_verifikasi_pa", {"pa_number": num, "oleh": VERIF, "alasan": "kurang"})
    assert _call("fn_prp_teruskan_pa", {"pa_number": num, "oleh": FINANCE})["ok"] is True
    row = _row2(pa_id)
    assert row["serah_status"] == "menunggu_verifikasi" and not row["verif_catatan"]
    assert _kej(num)[-2:] == ["dikembalikan_verificator", "diteruskan_finance"]
    assert _call("fn_prp_teruskan_pa", {"pa_number": num, "oleh": FINANCE})["ok"] is False


def test_tolak_finance_from_dikembalikan_clears_dates_but_log_keeps_them():
    pa_id, num = _to_verif("V6")
    _call("fn_prp_tolak_verifikasi_pa", {"pa_number": num, "oleh": VERIF, "alasan": "kurang"})
    assert _row2(pa_id)["pa_received_by_po_fin"] == _today()
    out = _call("fn_prp_tolak_serah_pa", {"pa_number": num, "oleh": FINANCE, "alasan": "Lengkapi dokumen"})
    assert out["ok"] is True
    row = _row2(pa_id)
    assert row["serah_status"] == "ditolak" and row["serah_catatan"] == "Lengkapi dokumen"
    assert not row["pa_received_by_po_fin"] and not row["pa_verified_by_po_fin"]
    rows = _log(num)["rows"]
    assert [r["kejadian"] for r in rows] == ["diserahkan", "diterima_finance", "dikembalikan_verificator", "ditolak_finance"]
    assert rows[1]["waktu"].startswith(_today()), "tanggal penerimaan pertama tetap terekam di riwayat"
    assert _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})["ok"] is True   # siklus baru
    assert _kej(num)[-1] == "diserahkan"


def test_tolak_finance_from_menunggu_is_logged():
    pa_id, num = _ready("V7")
    _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    assert _call("fn_prp_tolak_serah_pa", {"pa_number": num, "oleh": FINANCE, "alasan": "fisik belum ada"})["ok"] is True
    assert _kej(num) == ["diserahkan", "ditolak_finance"]


def test_repeat_calls_are_refused_and_log_has_single_entries():
    pa_id, num = _to_verif("V8")
    assert _call("fn_prp_terima_pa", {"pa_number": num, "oleh": "finance2@x.test"})["ok"] is False
    assert _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})["ok"] is True
    assert _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": "verif2@x.test"})["ok"] is False
    row = _row2(pa_id)
    assert row["verif_by"] == VERIF and row["pa_verified_by_po_fin"] == _today()
    kej = _kej(num)
    assert kej.count("diterima_finance") == 1 and kej.count("terverifikasi") == 1


def test_serah_log_chronological_with_reasons():
    pa_id, num = _to_verif("V9")
    _call("fn_prp_tolak_verifikasi_pa", {"pa_number": num, "oleh": VERIF, "alasan": "kurang PAM"})
    _call("fn_prp_teruskan_pa", {"pa_number": num, "oleh": FINANCE})
    _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})
    rows = _log(num)["rows"]
    assert [r["kejadian"] for r in rows] == ["diserahkan", "diterima_finance", "dikembalikan_verificator", "diteruskan_finance", "terverifikasi"]
    assert rows[2]["catatan"] == "kurang PAM" and all(r["oleh"] and r["waktu"] for r in rows)
    assert [r["waktu"] for r in rows] == sorted(r["waktu"] for r in rows)
    assert _log("PA/ETF/999/2026") == {"ok": True, "rows": []}


def test_list_serah_includes_dikembalikan_with_reason():
    a_id, a = _ready("V10")
    _call("fn_prp_serah_pa", {"pa_number": a, "requested_by": OWNER})
    b_id, b = _to_verif("V11")
    _call("fn_prp_tolak_verifikasi_pa", {"pa_number": b, "oleh": VERIF, "alasan": "PAM kurang tanda tangan"})
    rows = {r["pa_number"]: r for r in _call("fn_prp_list_serah")["rows"]}
    assert rows[a]["status"] == "menunggu" and rows[b]["status"] == "dikembalikan"
    assert rows[b]["catatan"] == "PAM kurang tanda tangan" and rows[b]["requested_by"] == OWNER
    _call("fn_prp_teruskan_pa", {"pa_number": b, "oleh": FINANCE})
    assert b not in [r["pa_number"] for r in _call("fn_prp_list_serah")["rows"]]


def test_list_verifikasi_only_menunggu_verifikasi():
    a_id, a = _to_verif("V12")
    b_id, b = _ready("V13")
    _call("fn_prp_serah_pa", {"pa_number": b, "requested_by": OWNER})        # masih menunggu Finance
    c_id, c = _to_verif("V14")
    _call("fn_prp_verifikasi_pa", {"pa_number": c, "oleh": VERIF})            # sudah terverifikasi
    out = _call("fn_prp_list_verifikasi")
    nums = [r["pa_number"] for r in out["rows"]]
    assert out["ok"] is True and a in nums and b not in nums and c not in nums
    row = [r for r in out["rows"] if r["pa_number"] == a][0]
    assert row["nomor_pam"] == "PAM/ETF/021/2026" and row["total"] == 4000000 and row["terima_at"].startswith(_today())


def test_pa_status_includes_verif_keys():
    pa_id, num = _to_verif("V15")
    _call("fn_prp_verifikasi_pa", {"pa_number": num, "oleh": VERIF})
    r = _call("fn_prp_pa_status", [num])[num]
    assert r["serah_status"] == "terverifikasi" and r["pa_verified_by_po_fin"] == _today()
    assert r["verif_at"].startswith(_today()) and "verif_catatan" in r

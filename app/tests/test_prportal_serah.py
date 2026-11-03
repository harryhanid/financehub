# tests/test_prportal_serah.py -- serah terima dokumen fisik PA Beasiswa (PR Portal): serahkan -> Finance terima/tolak.
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_conn
from tests.test_prportal_fc_review import _make
from tests.test_prportal_fn import _today

OWNER = "harry@sinarmas.test"     # requested_by dari _payload
FINANCE = "finance@sinarmas.test"


def _call(fn, payload=None):
    conn = get_conn()
    try:
        if payload is None:
            row = conn.execute(f"SELECT {fn}()::text").fetchone()
        else:
            row = conn.execute(f"SELECT {fn}(?::jsonb)::text", (json.dumps(payload),)).fetchone()
        return json.loads(row[0])
    finally:
        conn.close()


def _ready(code, send_back="2026-11-01", recv=""):
    """PA open, sudah Checked + Send Back Educ (siap diserahkan)."""
    pa_id, bid = _make(code)
    conn = get_conn()
    try:
        conn.execute("UPDATE etf_pa SET status='open', checked_by_fincon='2026-10-30', send_pa_back_to_educ=?, "
                     "pa_received_by_po_fin=? WHERE id=?", (send_back, recv, pa_id))
        conn.commit()
        num = conn.execute("SELECT pa_number FROM etf_pa WHERE id=?", (pa_id,)).fetchone()["pa_number"]
    finally:
        conn.close()
    return pa_id, num


def _row(pa_id):
    conn = get_conn()
    try:
        return conn.execute("SELECT serah_status, serah_at, serah_by, serah_catatan, terima_by, terima_at, "
                            "pa_received_by_po_fin FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    finally:
        conn.close()


def test_serah_requires_owner():
    pa_id, num = _ready("H1")
    r = _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": "orang.lain@x.test"})
    assert r["ok"] is False and r["pesan"] == "PA tidak ditemukan."
    assert _call("fn_prp_serah_pa", {"pa_number": "PA/ETF/999/2026", "requested_by": OWNER})["ok"] is False
    assert _row(pa_id)["serah_status"] is None
    ok = _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER.upper()})   # tanpa peka huruf besar
    assert ok["ok"] is True
    row = _row(pa_id)
    assert row["serah_status"] == "menunggu" and row["serah_by"] == OWNER and row["serah_at"].startswith(_today())


def test_serah_requires_send_back_and_empty_recv():
    pa_id, num = _ready("H2", send_back="")
    r = _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    assert r["ok"] is False and "Send Back Educ" in r["pesan"]
    pa_id2, num2 = _ready("H3", recv="2026-11-02")          # FC sudah mengisi manual
    r = _call("fn_prp_serah_pa", {"pa_number": num2, "requested_by": OWNER})
    assert r["ok"] is False and "sudah diterima" in r["pesan"]
    pa_id3, num3 = _make("H4")                               # masih on_review_fc
    conn = get_conn()
    num3 = conn.execute("SELECT pa_number FROM etf_pa WHERE id=?", (pa_id3,)).fetchone()["pa_number"]
    conn.close()
    assert _call("fn_prp_serah_pa", {"pa_number": num3, "requested_by": OWNER})["ok"] is False
    assert _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER}) ["ok"] is False
    assert _row(pa_id)["serah_status"] is None and _row(pa_id2)["serah_status"] is None


def test_serah_then_terima_sets_recv_today_and_audit():
    pa_id, num = _ready("H5")
    assert _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})["ok"] is True
    again = _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    assert again["ok"] is False and "menunggu" in again["pesan"]
    out = _call("fn_prp_terima_pa", {"pa_number": num, "oleh": FINANCE})
    assert out == {"ok": True, "tanggal": _today()}
    row = _row(pa_id)
    assert row["serah_status"] == "diterima" and row["pa_received_by_po_fin"] == _today()
    assert row["terima_by"] == FINANCE and row["terima_at"].startswith(_today())


def test_terima_twice_refused_and_requires_menunggu():
    pa_id, num = _ready("H6")
    assert _call("fn_prp_terima_pa", {"pa_number": num, "oleh": FINANCE})["ok"] is False   # belum diserahkan
    _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    assert _call("fn_prp_terima_pa", {"pa_number": num, "oleh": FINANCE})["ok"] is True
    second = _call("fn_prp_terima_pa", {"pa_number": num, "oleh": "finance2@x.test"})
    assert second["ok"] is False
    row = _row(pa_id)
    assert row["terima_by"] == FINANCE and row["pa_received_by_po_fin"] == _today(), "tidak tertimpa"
    assert _call("fn_prp_terima_pa", {"pa_number": num, "oleh": ""})["ok"] is False


def test_tolak_requires_reason_max_300_then_reserah_clears_note():
    pa_id, num = _ready("H7")
    _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    for bad in ("", "   ", "x" * 301):
        r = _call("fn_prp_tolak_serah_pa", {"pa_number": num, "oleh": FINANCE, "alasan": bad})
        assert r["ok"] is False, bad[:5]
    assert _row(pa_id)["serah_status"] == "menunggu"
    ok = _call("fn_prp_tolak_serah_pa", {"pa_number": num, "oleh": FINANCE, "alasan": "  Dokumen fisik belum diterima <b>  "})
    assert ok["ok"] is True
    row = _row(pa_id)
    assert row["serah_status"] == "ditolak" and row["serah_catatan"] == "Dokumen fisik belum diterima <b>"
    assert row["pa_received_by_po_fin"] in (None, "")
    assert _call("fn_prp_tolak_serah_pa", {"pa_number": num, "oleh": FINANCE, "alasan": "lagi"})["ok"] is False  # sudah ditolak
    again = _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    assert again["ok"] is True
    row = _row(pa_id)
    assert row["serah_status"] == "menunggu" and row["serah_catatan"] in (None, "")


def test_list_serah_only_menunggu_ordered():
    a_id, a = _ready("H8")
    b_id, b = _ready("H9")
    c_id, c = _ready("H10")
    for num in (a, b, c):
        _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    _call("fn_prp_terima_pa", {"pa_number": b, "oleh": FINANCE})
    out = _call("fn_prp_list_serah")
    assert out["ok"] is True
    nums = [r["pa_number"] for r in out["rows"]]
    assert a in nums and c in nums and b not in nums
    row = [r for r in out["rows"] if r["pa_number"] == a][0]
    assert row["requested_by"] == OWNER and row["serah_by"] == OWNER and row["total"] == 4000000
    assert [r["serah_at"] for r in out["rows"]] == sorted(r["serah_at"] for r in out["rows"])


def test_pa_status_includes_serah_keys():
    pa_id, num = _ready("H11")
    _call("fn_prp_serah_pa", {"pa_number": num, "requested_by": OWNER})
    r = _call("fn_prp_pa_status", [num])[num]
    assert r["serah_status"] == "menunggu" and r["serah_at"].startswith(_today())
    assert "serah_catatan" in r and "terima_at" in r

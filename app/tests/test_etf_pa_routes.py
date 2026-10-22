# tests/test_etf_pa_routes.py
# Route create (etf_payment_application/routes.py): lampiran Google Drive setelah create_pa.
# R25: DB tidak terjangkau saat menautkan lampiran -> 503, bukan 200 ok:True "gagal upload".
import io
import json

import database
from database import get_conn

COMPANY_ID = 2


def _login(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(COMPANY_ID)})


def _seed_siswa():
    conn = get_conn()
    sid = conn.execute(
        "INSERT INTO siswa (company_id, code, nama, status) VALUES (?,?,?,?)",
        (COMPANY_ID, "1230001", "Budi Santoso", "Aktif")).lastrowid
    conn.close()
    return sid


def _post_create(client, sid):
    data = {"tgl_payment_application": "2026-06-01",
            "lines": [{"student_id": sid, "jenis_pembayaran": "By Pendidikan", "jumlah_pembayaran": 1000}]}
    return client.post("/etf-payment-application/create?tab=agri",
                       data={"data": json.dumps(data), "files": (io.BytesIO(b"x"), "a.pdf")},
                       content_type="multipart/form-data")


def _fake_gdrive(monkeypatch):
    import utils.gdrive_service as g
    monkeypatch.setattr(g, "create_gdrive_folder", lambda name: "folder1")
    monkeypatch.setattr(g, "upload_file_to_gdrive", lambda *a, **k: "file1")


def test_create_links_attachment(client, monkeypatch):
    _login(client)
    sid = _seed_siswa()
    _fake_gdrive(monkeypatch)
    resp = _post_create(client, sid)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True and "gagal upload" not in body["pesan"]
    conn = get_conn()
    row = conn.execute("SELECT attachment_file_id FROM etf_pa WHERE id=?", (body["pa_id"],)).fetchone()
    conn.close()
    assert row["attachment_file_id"] == "file1"


def test_create_attachment_link_db_outage_returns_503(client, monkeypatch):
    from fhdb.errors import OperationalError
    _login(client)
    sid = _seed_siswa()
    _fake_gdrive(monkeypatch)
    real_get_conn = database.get_conn

    class _OutageOnLink:
        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, params=()):
            if "SET attachment_file_id=?" in sql:
                raise OperationalError("fh_exec HTTP koneksi gagal: ConnectError")
            return self._conn.execute(sql, params)

        def __getattr__(self, name):
            return getattr(self._conn, name)

    # Route mengimpor get_conn dari database saat dipanggil; service memakai referensi aslinya.
    monkeypatch.setattr(database, "get_conn", lambda: _OutageOnLink(real_get_conn()))
    resp = _post_create(client, sid)
    assert resp.status_code == 503
    conn = real_get_conn()
    row = conn.execute("SELECT attachment_file_id FROM etf_pa").fetchone()
    conn.close()
    assert row["attachment_file_id"] == ""  # PA dibuat, lampiran tidak tertaut, dan itu tidak disembunyikan


def test_create_attachment_gdrive_error_still_reports_message(client, monkeypatch):
    import utils.gdrive_service as g
    _login(client)
    sid = _seed_siswa()

    def _boom(name):
        raise RuntimeError("drive down")
    monkeypatch.setattr(g, "create_gdrive_folder", _boom)
    resp = _post_create(client, sid)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True and "gagal upload lampiran" in body["pesan"] and "drive down" in body["pesan"]

# tests/test_etf_pa_attachment_route.py
# Lampiran PA (/etf-payment-application/attachment/<id>): galat Google Drive harus terbaca (bukan "Internal Server Error" polos),
# dependensi Drive harus terdaftar di requirements.txt (server memasangnya dari sana), dan otorisasi interaktif tidak boleh
# menggantung di server.
import os
import sys

import pytest

import config

APP_DIR = os.path.join(os.path.dirname(__file__), "..")
COMPANY_ID = 2


def _login(client):
    client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    client.post("/select-company", data={"company_id": str(COMPANY_ID)})


def test_attachment_import_failure_is_reported_not_generic_500(client, monkeypatch):
    _login(client)
    monkeypatch.setitem(sys.modules, "utils.gdrive_service", None)   # paket Google tidak terpasang -> ImportError
    r = client.get("/etf-payment-application/attachment/abc")
    assert r.status_code == 502
    assert "Lampiran tidak dapat dibuka" in r.get_data(as_text=True)


def test_attachment_drive_error_is_reported(client, monkeypatch):
    _login(client)
    import utils.gdrive_service as g

    def boom(_):
        raise RuntimeError("Token Google Drive tidak valid")
    monkeypatch.setattr(g, "get_file_metadata_from_gdrive", boom)
    r = client.get("/etf-payment-application/attachment/abc")
    assert r.status_code == 502 and "Token Google Drive tidak valid" in r.get_data(as_text=True)


def test_requirements_lists_google_drive_packages():
    req = open(os.path.join(APP_DIR, "requirements.txt"), encoding="utf-8").read().lower()
    for pkg in ("google-api-python-client", "google-auth-oauthlib", "google-auth-httplib2"):
        assert pkg in req, pkg


def test_gdrive_without_valid_token_fails_fast_unless_interactive(tmp_path, monkeypatch):
    from utils import gdrive_service
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    monkeypatch.delenv("GDRIVE_INTERACTIVE_AUTH", raising=False)
    with pytest.raises(RuntimeError, match="token.json"):
        gdrive_service.get_gdrive_service()


def test_auth_helper_script_enables_interactive_flow():
    src = open(os.path.join(APP_DIR, "auth.py"), encoding="utf-8").read()
    assert "GDRIVE_INTERACTIVE_AUTH" in src, "skrip otorisasi manual harus mengaktifkan alur interaktif"


def test_poin_labels_cover_groups_and_legacy_letters():
    from modules.etf_payment_application.routes import PA_POIN_LABELS, PA_POIN_DISPLAY
    # kelompok baru: a, b&c, d-e-f, g&h, i, j, k, l; huruf lama (c, e, f, h) tetap berlabel untuk PA lama
    assert set(PA_POIN_LABELS) == set("abcdefghijkl")
    assert PA_POIN_DISPLAY == {"b": "b & c", "d": "d, e & f", "g": "g & h"}
    assert "Kwitansi" in PA_POIN_LABELS["b"] and "Bukti pembayaran" in PA_POIN_LABELS["b"]
    assert "Kartu rencana studi" in PA_POIN_LABELS["d"] and "Rekap nilai" in PA_POIN_LABELS["d"]
    assert "Rincian biaya pendidikan" in PA_POIN_LABELS["g"]

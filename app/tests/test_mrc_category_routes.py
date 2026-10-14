# tests/test_mrc_category_routes.py
import io
import re

import bcrypt

import database
from modules.general_ledger import service as gl_service
from modules.management_report import category_map as cm
from tests.test_gl_sync import mkrow
from tests.test_mrc_category_map import GL_LOG, row, sheet
from tests.test_mrc_routes import login

URL = "/management-report/pemetaan/kategori"


def rows_of(html, table_id):
    block = html.split(f'id="{table_id}"', 1)[1].split("</table>", 1)[0]
    return [[re.sub(r"<.*?>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.S) if "<td" in r]


def seed_map():
    cm.sync_categories("GL - MASTER.xlsb", "admin", cm.normalise_categories(sheet(
        row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-tba", None, "", "TBA", "TBA"))))


def post_sync(client, monkeypatch, rows, name="GL - MASTER.xlsb"):
    monkeypatch.setattr(cm, "read_category_sheet", lambda f: rows)
    return client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), name)},
                       content_type="multipart/form-data")


def make_requester(client):
    pw = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) "
                 "VALUES (?, ?, 'requester', 0)", ("req1", pw))
    conn.commit()
    conn.close()
    client.post("/auth/login", json={"username": "req1", "password": "Req@12345"})
    client.post("/select-company", data={"company_id": "2"})


def test_page_requires_login(client):
    r = client.get(URL)
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_empty_state_and_tab(client):
    login(client)
    html = client.get(URL).data.decode()
    assert "Kategori SPT" in html and "belum pernah disync" in html.lower()
    assert 'id="mr-cat-sync-btn"' in html


def test_tab_is_present_on_the_existing_pemetaan_page(client):
    login(client)
    assert "/management-report/pemetaan/kategori" in client.get("/management-report/pemetaan").data.decode()


def test_sync_success_then_unchanged(client, monkeypatch):
    login(client)
    rows = cm.normalise_categories(sheet(row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA")))
    j = post_sync(client, monkeypatch, rows).get_json()
    assert j["ok"] and j["changed"] and "SMT 1 akun" in j["pesan"]
    again = post_sync(client, monkeypatch, rows).get_json()
    assert again["ok"] and again["changed"] is False and "Sudah sinkron" in again["pesan"]
    assert rows_of(client.get(URL).data.decode(), "mr-cat-table") == [
        ["SMT", "6-1810", "Office", "Beban Operasional", "BIAYA LAINNYA"]]


def test_sync_rejects_non_xlsb_missing_file_and_parse_errors_without_touching_data(client, monkeypatch):
    login(client)
    seed_map()
    assert client.post(URL + "/sync", data={}, content_type="multipart/form-data").status_code == 400
    r = client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), "a.xlsx")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "xlsb" in r.get_json()["pesan"]

    from modules.management_report.coa_map import CoaParseError

    def boom(f):
        raise CoaParseError("Sheet 'COA' tidak ditemukan di file.")
    monkeypatch.setattr(cm, "read_category_sheet", boom)
    r = client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), "a.xlsb")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "tidak ditemukan" in r.get_json()["pesan"]
    assert ("SMT", "6-1810") in cm.get_category_map()
    monkeypatch.setattr(cm, "read_category_sheet", lambda f: [])
    r = client.post(URL + "/sync", data={"file": (io.BytesIO(b"x"), "a.xlsb")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_non_admin_can_view_but_not_change_anything(client, monkeypatch):
    seed_map()
    make_requester(client)
    html = client.get(URL).data.decode()
    assert client.get(URL).status_code == 200 and 'id="mr-cat-sync-btn"' not in html
    r = post_sync(client, monkeypatch, [])
    assert r.status_code == 403
    assert client.post(URL + "/lk", json={"name": "Beban Operasional", "statement": "neraca"}).status_code == 403
    assert client.post(URL + "/pph", json={"alias": "x", "pph_type": "PPh 21"}).status_code == 403
    assert client.delete(URL + "/pph/pph21").status_code == 403
    assert cm.get_lk_list()["Beban Operasional"]["statement"] == "laba_rugi"


def test_lk_view_lists_and_updates(client):
    login(client)
    seed_map()
    html = client.get(URL + "?view=lk").data.decode()
    assert [r[0] for r in rows_of(html, "mr-lk-table")] == ["Beban Operasional"]
    r = client.post(URL + "/lk", json={"name": "Beban Operasional", "statement": "neraca", "kind": "lainnya",
                                       "seq": 7, "label": "BO", "needs_spt": False})
    assert r.status_code == 200 and r.get_json()["ok"]
    assert cm.get_lk_list()["Beban Operasional"]["label"] == "BO"
    bad = client.post(URL + "/lk", json={"name": "Beban Operasional", "statement": "salah"})
    assert bad.status_code == 400 and not bad.get_json()["ok"]
    assert client.post(URL + "/lk", json={"name": "tidak ada", "statement": "neraca"}).status_code == 404


def test_pph_alias_add_list_and_delete(client):
    login(client)
    html = client.get(URL + "?view=pph").data.decode()
    assert {r[0] for r in rows_of(html, "mr-pph-table")} >= {"pph21", "pph23", "pph4(2)", "nonpph"}
    r = client.post(URL + "/pph", json={"alias": "PPh 4 ayat 2", "pph_type": "PPh 4(2)"})
    assert r.status_code == 200 and r.get_json()["alias"] == "pph4ayat2"
    assert client.post(URL + "/pph", json={"alias": "", "pph_type": "PPh 21"}).status_code == 400
    assert client.delete(URL + "/pph/pph4ayat2").status_code == 200
    assert client.delete(URL + "/pph/pph21").status_code == 400
    assert client.delete(URL + "/pph/tidak-ada").status_code == 404


def test_unmapped_panel_lists_gl_accounts_without_mapping(client):
    login(client)
    seed_map()
    gl_service.replace_year("smt", 2026, [
        mkrow(acc_statutory="6-1810", tgl="2026-01-02", debit_credit=1.0),
        mkrow(acc_statutory="6-tba", tgl="2026-01-02", debit_credit=2.0),
        mkrow(acc_statutory="9-none", tgl="2026-01-02", debit_credit=3.0)], GL_LOG)
    html = client.get(URL).data.decode()
    accounts = [r[1] for r in rows_of(html, "mr-cat-unmapped")]
    assert accounts == ["9-none", "6-tba"]                       # biggest amount first, mapped one absent
    assert "Akun tidak ada di pemetaan kategori" in html

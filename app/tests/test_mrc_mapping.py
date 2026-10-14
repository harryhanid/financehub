import re

import bcrypt

import database
from modules.general_ledger import service as gl_service
from modules.management_report import coa_map
from tests.test_gl_sync import mkrow
from tests.test_mrc_routes import CC_ROWS, CMAP_ROWS, login, seed
from tests.test_mrc_sources import LOG

URL = "/management-report/pemetaan"


def get(client, qs=""):
    r = client.get(URL + qs)
    assert r.status_code == 200, qs
    return r.data.decode()


def _table(html, table_id):
    return html.split(f'id="{table_id}"', 1)[1].split("</table>", 1)[0]


def rows_of(html, table_id):
    """<td> texts of every body row of the table with this id."""
    block = _table(html, table_id)
    return [[re.sub(r"<.*?>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            for row in re.findall(r"<tr>(.*?)</tr>", block, re.S) if "<td" in row]


def th_texts(html, table_id):
    return [re.sub(r"<.*?>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", _table(html, table_id), re.S)]


def seed_many(n_smt=130):
    rows = [{"source": "SMT", "account": f"6-{i:04d}", "coa_ho": f"7{i:07d}", "category": "10 - Office Supplies",
             "code": "-10-"} for i in range(n_smt)]
    rows.append({"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others", "code": "-20-"})
    coa_map.sync_coa("big.xlsb", "u", rows, CC_ROWS)


def login_requester(client):
    pw_hash = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) VALUES (?, ?, 'requester', 0)",
                 ("req1", pw_hash))
    conn.commit()
    conn.close()
    assert client.post("/auth/login", json={"username": "req1", "password": "Req@12345"}).status_code == 200
    client.post("/select-company", data={"company_id": "2"})


def test_requires_login(client):
    r = client.get(URL)
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_sync_card_history_and_coa_table(client):
    login(client)
    coa_map.sync_coa("first.xlsb", "alice", CMAP_ROWS[:1], CC_ROWS[:2])
    coa_map.sync_coa("m.xlsb", "bob", CMAP_ROWS, CC_ROWS)
    html = get(client)
    last = coa_map.last_sync()
    assert f"Terakhir sync: {last['synced_at']} · bob · m.xlsb · SMT 1 akun, ETF 1 akun, 4 cost center" in html
    assert th_texts(html, "mr-history") == ["Waktu", "User", "File", "SMT", "ETF", "Cost center"]
    assert [h[1:] for h in rows_of(html, "mr-history")] == [["bob", "m.xlsb", "1", "1", "4"],
                                                             ["alice", "first.xlsb", "1", "0", "2"]]
    assert th_texts(html, "mr-map-table") == ["Sumber", "Akun", "COA HO", "Kategori", "Code (BC1)"]
    assert rows_of(html, "mr-map-table") == [["ETF", "6-2190", "70119100", "20 - Others", "-20-"],
                                             ["SMT", "6-1810", "70108100", "10 - Office Supplies", "-10-"]]
    assert "2 baris" in html and "Halaman 1 dari 1" in html
    assert "mr-map-btn" in html                                  # admin


def test_cc_view(client):
    login(client)
    seed()
    html = get(client, "?view=cc")
    assert th_texts(html, "mr-map-table") == ["Cost Center", "COST CENTER2", "CC1", "Deskripsi"]
    assert rows_of(html, "mr-map-table") == [
        ["POCFAD", "$POCFOF", "9", "SMT - Finance"], ["POITEC", "$POITEC", "16", "SMT - IT"],
        ["POSPON", "$POCCOM", "5", "SMT - Sponshorship"], ["TFOPEX", "$TFOPEX", "6", "ETF - Opex"]]
    only = get(client, "?view=cc&q=finance")
    assert rows_of(only, "mr-map-table") == [["POCFAD", "$POCFOF", "9", "SMT - Finance"]] and "1 baris" in only
    assert 'name="source"' not in only                           # no source select in the cc view


def test_source_and_search_filters(client):
    login(client)
    seed()
    etf = get(client, "?source=ETF")
    assert rows_of(etf, "mr-map-table") == [["ETF", "6-2190", "70119100", "20 - Others", "-20-"]]
    q = get(client, "?q=70108")
    assert rows_of(q, "mr-map-table") == [["SMT", "6-1810", "70108100", "10 - Office Supplies", "-10-"]]
    none = get(client, "?q=zzzz")
    assert rows_of(none, "mr-map-table") == [["Tidak ada baris yang cocok."]] and "0 baris" in none


def test_pagination_preserves_params(client):
    login(client)
    seed_many()
    p1 = get(client, "?view=coa&source=SMT&q=6-0")
    assert "Halaman 1 dari 2" in p1 and len(rows_of(p1, "mr-map-table")) == 100
    nxt = re.search(r'<a [^>]*href="([^"]*page=2[^"]*)"', p1).group(1).replace("&amp;", "&")
    assert "view=coa" in nxt and "source=SMT" in nxt and "q=6-0" in nxt
    p2 = client.get(URL + nxt[nxt.index("?"):]).data.decode()
    assert "Halaman 2 dari 2" in p2 and len(rows_of(p2, "mr-map-table")) == 30 and "Berikutnya" not in p2
    assert "Sebelumnya" in p2
    huge = get(client, "?source=SMT&q=6-0&page=999999")
    assert "Halaman 2 dari 2" in huge and "Berikutnya" not in huge


def test_invalid_params_fall_back(client):
    login(client)
    seed()
    for qs in ("?view=zzz", "?source=NOPE", "?page=abc", "?page=-4", "?page=0", "?page=999999", "?view=cc&source=NOPE"):
        assert "Halaman 1 dari 1" in get(client, qs), qs
    assert len(rows_of(get(client, "?source=NOPE"), "mr-map-table")) == 2    # unknown source = both
    assert th_texts(get(client, "?view=zzz"), "mr-map-table")[0] == "Sumber"


def test_switch_links_keep_q_and_drop_page(client):
    login(client)
    seed_many()
    html = get(client, "?q=6-0&page=2&view=coa")
    links = re.findall(r'<a class="mc-switch[^"]*" href="([^"]*)"', html)
    assert len(links) == 2 and all("q=6-0" in l and "page" not in l for l in links)
    assert any("view=cc" in l for l in links)


def test_q_is_escaped(client):
    login(client)
    seed()
    html = get(client, "?q=%3Cscript%3Ealert(1)%3C/script%3E")
    assert "<script>alert(1)</script>" not in html
    assert 'value="&lt;script&gt;alert(1)&lt;/script&gt;"' in html


def test_unmapped_panel_lists_exact_accounts_and_cost_centers(client):
    login(client)
    seed()
    gl_service.replace_all("smt", [
        mkrow(acc_management="6-9999", tgl="2026-02-20", debit_credit=2000000.0, job_name="POXXXX", allocation_memo="a"),
        mkrow(acc_management="6-9999", tgl="2026-03-20", debit_credit=1000000.0, job_name="POXXXX", allocation_memo="b"),
        mkrow(acc_management="6-1810", tgl="2026-03-21", debit_credit=1000.0, job_name="POITEC", allocation_memo="c")],
        LOG)
    html = get(client)
    assert rows_of(html, "mr-unmapped-acc") == [["SMT", "6-9999", "2", "3,0"]]
    assert rows_of(html, "mr-unmapped-cc") == [["POXXXX", "2"]]
    assert "Semua akun" not in html


def test_all_mapped_message(client):
    login(client)
    seed()
    html = get(client)
    assert "Semua akun dan cost center sudah terpetakan." in html
    assert 'id="mr-unmapped-acc"' not in html and 'id="mr-unmapped-cc"' not in html


def test_no_mapping_message_admin(client):
    login(client)
    seed(mapping=False)
    html = get(client)
    assert "Pemetaan belum ada. Upload Management Report - MASTER.xlsb di atas." in html
    assert "belum pernah disync" in html and 'id="mr-map-table"' not in html and 'id="mr-unmapped-acc"' not in html
    assert "Belum ada riwayat." in html
    assert "Semua akun" not in html


def test_no_mapping_message_non_admin(client):
    login_requester(client)
    seed(mapping=False)
    html = get(client)
    assert "Pemetaan belum ada. Minta admin untuk sync pemetaan." in html
    assert "mr-map-btn" not in html and "mr-map-file" not in html


def test_old_style_mapping_single_banner_and_no_cc_list(client):
    login(client)
    seed(mapping=False)
    gl_service.replace_all("smt", [
        mkrow(acc_management="6-1810", tgl="2026-02-20", debit_credit=1000.0, job_name="POXXXX", allocation_memo="a")], LOG)
    coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS)
    html = get(client)
    assert html.count("Pemetaan perlu disync ulang") == 1
    assert "belum ada di sheet CC" not in html and 'id="mr-unmapped-cc"' not in html
    assert "Semua akun sudah terpetakan." in html and "cost center sudah" not in html


def test_non_admin_has_no_sync_button(client):
    login_requester(client)
    seed()
    html = get(client)
    assert "mr-map-btn" not in html and "mrSyncMapping" not in html
    assert "Terakhir sync" in html


def test_admin_sees_sync_controls(client):
    login(client)
    seed()
    html = get(client)
    for el in ('id="mr-map-file"', 'id="mr-map-btn"', 'id="mr-map-msg"', "/management-report/gl-combine/sync-mapping"):
        assert el in html, el


def test_navbar_and_active_tab(client):
    login(client)
    seed()
    idx = client.get("/management-report/").data.decode()
    company = re.search(r'class="navbar-company"[^>]*>(.*?)</a>', idx, re.S).group(1).strip()
    html = get(client)
    assert re.search(r'class="navbar-company"[^>]*>\s*' + re.escape(company), html)
    assert re.search(r'class="navbar-user">.*?</svg>\s*(\S+)', html, re.S).group(1) == "admin"
    assert re.findall(r'<a class="mr-linktab active"[^>]*>(.*?)</a>', html) == ["Pemetaan"]


def test_unmapped_list_truncates_at_50(client):
    login(client)
    seed()
    gl_service.replace_all("smt", [
        mkrow(acc_management=f"6-{7000 + i}", tgl="2026-02-20", debit_credit=1000.0, job_name="POITEC",
              allocation_memo="x") for i in range(53)], LOG)
    html = get(client)
    assert len(rows_of(html, "mr-unmapped-acc")) == 50 and "dan 3 lainnya" in html

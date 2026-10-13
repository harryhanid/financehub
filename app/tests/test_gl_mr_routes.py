# tests/test_gl_mr_routes.py
import io

from modules.management_report import coa_map
from modules.general_ledger import routes as gl_routes
from modules.general_ledger import service as svc
from tests.test_gl_sync import mkrow

LOG = dict(synced_by="u", filename="f", content_hash="h", rows_before=0, rows_after=1,
           total_debit=0, total_credit=0, dropped=0, summary={})


def login(client, user="admin", password="Admin@123"):
    client.post("/auth/login", json={"username": user, "password": password})
    client.post("/select-company", data={"company_id": "2"})


def seed_gl(extra_smt=()):
    smt = [mkrow(acc_management="6-1810", tgl="2026-01-15", debit_credit=-957910.0,
                 job_name="POITEC", budget_activity="SMT - IT", allocation_memo="Zoom"),
           mkrow(acc_management="6-1810", tgl="2026-02-10", debit_credit=5000000.0,
                 job_name="POCFAD", budget_activity="SMT - Finance", allocation_memo="ATK"),
           *extra_smt]
    etf = [mkrow(acc_management="6-2190", tgl="2026-02-05", debit_credit=30000.0,
                 job_name="TFOPEX", budget_activity="", allocation_memo="Biaya admin")]
    svc.replace_all("smt", smt, LOG)
    svc.replace_all("etf", etf, LOG)


def seed_map():
    coa_map.sync_coa("m.xlsb", "u", [
        {"source": "SMT", "account": "6-1810", "coa_ho": "70108100",
         "category": "10 - Office Supplies And Equipment Expense"},
        {"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others"}])


def page(client, qs=""):
    return client.get("/general-ledger/mr" + qs)


def test_requires_login(client):
    resp = client.get("/general-ledger/mr")
    assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_mr_tab_link_is_in_the_tab_bar(client):
    login(client)
    assert "/general-ledger/mr" in client.get("/general-ledger/smt").data.decode()


def test_empty_state_without_coa_map(client):
    login(client)
    seed_gl()
    assert "Pemetaan COA belum ada" in page(client).data.decode()


def test_empty_state_without_gl_data(client):
    login(client)
    seed_map()
    assert "Belum ada data GL" in page(client).data.decode()


def test_report_defaults_to_latest_month_and_is_cumulative(client):
    login(client)
    seed_gl()
    seed_map()
    html = page(client).data.decode()
    assert "10 - Office Supplies And Equipment Expense" in html and "20 - Others" in html
    assert "- Act 2026 : Zoom Month : 1" in html and "- Act 2026 : ATK Month : 2" in html
    import re
    # -0.958 + 5.0 (category 10) + 0.03 (category 20) = 4.07 Rp Mio
    z = r'<td class="num">0,0</td><td class="num">0,0</td><td class="num">0,0</td>'
    assert re.search(r'gl-grand"><td colspan="5">Total All Cost Center</td>' + z +
                     r'<td class="num">4,0</td><td class="num">4,0</td><td class="num"></td>', html)
    assert re.search(r'gl-cat"><td colspan="5">10 - Office Supplies And Equipment Expense</td>' + z +
                     r'<td class="num">4,0</td><td class="num">4,0</td>', html)
    assert re.search(r'gl-cat"><td colspan="5">20 - Others</td>' + z +
                     r'<td class="num">0,0</td><td class="num">0,0</td>', html)
    assert "-1,0</td>" in html and "5,0</td>" in html


def test_cutoff_month_limits_the_report(client):
    login(client)
    seed_gl()
    seed_map()
    html = page(client, "?yy=2026&mm=1").data.decode()
    assert "Zoom" in html and "ATK" not in html


def test_cost_center_filter(client):
    login(client)
    seed_gl()
    seed_map()
    html = page(client, "?cc=POCFAD").data.decode()
    assert "ATK" in html and "Zoom" not in html


def test_invalid_parameters_fall_back_without_error(client):
    login(client)
    seed_gl()
    seed_map()
    for qs in ("?yy=abc&mm=99", "?yy=1999", "?mm=0", "?page=abc&view=data", "?page=-5&view=data",
               "?view=nonsense", "?cc=NOPE"):
        resp = page(client, qs)
        assert resp.status_code == 200, qs
    assert "ATK" in page(client, "?yy=1999").data.decode()          # fell back to latest period


def test_data_view_lists_flat_rows_with_source(client):
    login(client)
    seed_gl()
    seed_map()
    html = page(client, "?view=data").data.decode()
    for text in ("70108100", "70119100", "POITEC", "TFOPEX", "SMT", "ETF"):
        assert text in html, text
    filtered = page(client, "?view=data&q=ATK").data.decode()
    assert "ATK" in filtered and "Zoom" not in filtered


def test_unmapped_accounts_are_reported_not_hidden(client):
    login(client)
    seed_gl(extra_smt=[mkrow(acc_management="6-9999", tgl="2026-02-20", debit_credit=2000000.0,
                             job_name="POCFAD", allocation_memo="Misterius")])
    seed_map()
    html = page(client).data.decode()
    assert "Belum dipetakan" in html and "6-9999" in html and "Misterius" in html


def seed_cc(rows):
    coa_map.sync_coa("m.xlsb", "u", [
        {"source": "SMT", "account": "6-1810", "coa_ho": "70108100",
         "category": "10 - Office Supplies And Equipment Expense", "code": "-10-"},
        {"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others",
         "code": "-20-"}], rows)


def test_unmapped_cost_center_banner(client):
    login(client)
    seed_gl()
    seed_cc([{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "IT"},
             {"cost_center": "POCFAD", "total_cc": "$POCFAD", "seq": 3, "description": "F"}])
    html = page(client).data.decode()
    assert "2 cost center belum ada di sheet CC (COST CENTER2 kosong, CC1 = 0): TFOPEX (1)" not in html
    assert "1 cost center belum ada di sheet CC (COST CENTER2 kosong, CC1 = 0): TFOPEX (1)" in html


def test_no_cost_center_banner_when_all_mapped(client):
    login(client)
    seed_gl()
    seed_cc([{"cost_center": c, "total_cc": "$" + c, "seq": i + 1, "description": ""}
             for i, c in enumerate(("POITEC", "POCFAD", "TFOPEX"))])
    assert "belum ada di sheet CC" not in page(client).data.decode()


def test_cost_center_banner_counts_only_cutoff_scoped_rows(client):
    login(client)
    seed_gl()
    seed_cc([{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": ""},
             {"cost_center": "POCFAD", "total_cc": "$POCFAD", "seq": 3, "description": ""}])
    # TFOPEX row is in Feb; cutoff January must not report it
    assert "belum ada di sheet CC" not in page(client, "?yy=2026&mm=1").data.decode()


def make_non_admin(client):
    import bcrypt
    import database
    pw_hash = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) "
                 "VALUES (?, ?, 'requester', 0)", ("req1", pw_hash))
    conn.commit()
    conn.close()
    assert client.post("/auth/login", json={"username": "req1", "password": "Req@12345"}).status_code == 200
    client.post("/select-company", data={"company_id": "2"})


def upload(client, name="Master.xlsb", data=b"x"):
    return client.post("/general-ledger/mr/sync-coa", data={"file": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_non_admin_can_view_but_not_sync_coa(client):
    make_non_admin(client)
    seed_gl()
    seed_map()
    html = page(client).data.decode()
    assert "gl-coa-btn" not in html
    assert upload(client).status_code == 403
    assert coa_map.get_map() != {}


def test_sync_coa_success_then_unchanged(client, monkeypatch):
    login(client)
    rows = [{"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office",
             "code": "-10-"}]
    cc = [{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "IT"},
          {"cost_center": "PULPP", "total_cc": "", "seq": 0, "description": ""}]
    monkeypatch.setattr(gl_routes.coa_map, "read_mapping_sheets", lambda f: (rows, cc))
    j = upload(client).get_json()
    assert j["ok"] and j["changed"] is True
    assert j["pesan"] == "Sync pemetaan selesai: SMT 1 akun, ETF 0 akun, 2 cost center."
    assert (j["rows_smt"], j["rows_etf"], j["rows_cc"]) == (1, 0, 2)
    again = upload(client).get_json()
    assert again["ok"] and again["changed"] is False
    assert again["pesan"] == ("Sudah sinkron: pemetaan tidak berubah "
                              "(SMT 1 akun, ETF 0 akun, 2 cost center).")
    assert coa_map.get_map() == {("SMT", "6-1810"): ("70108100", "10 - Office", "-10-")}
    assert coa_map.get_cc_map() == {"POITEC": {"total": "$POITEC", "seq": 16, "description": "IT"},
                                    "PULPP": {"total": "", "seq": 0, "description": ""}}


def test_sync_ui_labels_and_cc_count(client):
    login(client)
    seed_gl()
    coa_map.sync_coa("m.xlsb", "u", [
        {"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "c"}],
        [{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": ""}])
    html = page(client).data.decode()
    assert "Sync pemetaan COA &amp; CC dari Excel" in html
    assert "SMT 1 akun, ETF 0 akun, 1 cost center" in html


def test_sync_coa_rejects_bad_uploads_and_keeps_old_map(client, monkeypatch):
    login(client)
    seed_map()
    assert upload(client, "a.xlsx").status_code == 400
    assert client.post("/general-ledger/mr/sync-coa", data={},
                       content_type="multipart/form-data").status_code == 400

    def boom(f):
        raise coa_map.CoaParseError("Sheet 'CC' tidak ditemukan di file.")
    monkeypatch.setattr(gl_routes.coa_map, "read_mapping_sheets", boom)
    r = upload(client)
    assert r.status_code == 400
    assert r.get_json()["pesan"] == "Sheet 'CC' tidak ditemukan di file."
    monkeypatch.setattr(gl_routes.coa_map, "read_mapping_sheets", lambda f: ([], []))
    assert upload(client).status_code == 400                       # nothing to import
    assert len(coa_map.get_map()) == 2


def test_sync_coa_database_error_returns_json_500(client, monkeypatch):
    login(client)
    monkeypatch.setattr(gl_routes.coa_map, "read_mapping_sheets", lambda f: (
        [{"source": "SMT", "account": "x", "coa_ho": "1", "category": "c", "code": ""}], []))

    def boom(*a, **k):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(gl_routes.coa_map, "sync_coa", boom)
    r = upload(client)
    assert r.status_code == 500 and r.get_json()["ok"] is False
    assert "database is locked" in r.get_json()["pesan"]


def test_gl_mio_filter_formats_indonesian_style():
    assert gl_routes._gl_mio(1234.56) == "1.234,6"
    assert gl_routes._gl_mio(-0.9) == "-0,9"
    assert gl_routes._gl_mio(0.0) == "0,0"


def test_data_view_pager_paginates_and_preserves_filters(client):
    login(client)
    smt = [mkrow(acc_management="6-1810", tgl="2026-02-10", debit_credit=1000000.0,
                 job_name="POCFAD", budget_activity="SMT - Finance", allocation_memo=f"Memo{i:03d}")
           for i in range(130)]
    svc.replace_all("smt", smt, LOG)
    seed_map()
    base = "?view=data&yy=2026&mm=2&cc=POCFAD&q=Memo"
    html = page(client, base).data.decode()
    assert "Halaman 1 dari 2" in html and "Sebelumnya" not in html
    import re
    nxt = re.search(r'<a class="btn btn-sm" href="([^"]*)">Berikutnya', html)
    assert nxt, "next link missing"
    href = nxt.group(1).replace("&amp;", "&")
    for part in ("view=data", "yy=2026", "mm=2", "cc=POCFAD", "q=Memo", "page=2"):
        assert part in href, part
    assert html.count("<tr><td>6-1810</td>") == 100
    p2 = page(client, base + "&page=2").data.decode()
    assert "Halaman 2 dari 2" in p2 and "Sebelumnya" in p2 and "Berikutnya" not in p2
    assert p2.count("<tr><td>6-1810</td>") == 30


def test_user_input_is_html_escaped(client):
    login(client)
    seed_gl()
    seed_map()
    raw = "<script>alert(1)</script>"
    html = page(client, "?cc=" + raw).data.decode()
    assert raw not in html
    html = page(client, "?view=data&q=" + raw).data.decode()
    assert raw not in html and "&lt;script&gt;" in html
    html = page(client, "?view=data&cc=" + raw + "&q=" + raw).data.decode()
    assert raw not in html


def test_gl_mio_never_shows_negative_zero():
    assert gl_routes._gl_mio(-1e-17) == "0,0"
    assert gl_routes._gl_mio(-0.04) == "0,0"
    assert gl_routes._gl_mio(-0.0) == "0,0"
    assert gl_routes._gl_mio(-0.06) == "-0,1"


def test_unknown_or_out_of_scope_cost_center_falls_back_to_all(client):
    login(client)
    seed_gl()
    seed_map()
    html = page(client, "?yy=2026&mm=1&cc=POCFAD").data.decode()
    assert "Zoom" in html and "Tidak ada data" not in html
    html = page(client, "?cc=NOPE").data.decode()
    assert "Zoom" in html and "ATK" in html and "Total All Cost Center" in html


def test_data_view_cards_follow_the_search_filter(client):
    import re
    login(client)
    seed_gl()
    seed_map()
    html = page(client, "?view=data&q=ATK").data.decode()
    assert re.search(r"Baris<b>1</b>", html)
    assert re.search(r"Total ACT \(Rp Mio\)<b>5,0</b>", html)
    full = page(client, "?view=data").data.decode()
    assert re.search(r"Baris<b>3</b>", full)


# ---- Task C: Data (GL Combine | Append1) and Report layouts ---------------------------------
import re

COMBINE_HEADERS = ["Account Management", "ID#", "Date", "Allocation Memo", "Budget Activity",
                   "COST CENTER", "DEBIT - CREDIT", "Source", "COA HO", "COST CENTER2", "Month", "CC0",
                   "CC1", "BC1", "New Code", "Memo", "BC"]
APPEND1_HEADERS = ["COA", "MM", "YY", "CC", "CC.1", "Category", "Activity", "Description", "PTA",
                   "Custom", "MM.1", "ACT", "BGT"]
REPORT_HEADERS = ["Category", "Custom", "MM.1", "Description", "Activity", "Sum of BGT", "Sum of PTA",
                  "BGT_Available", "Sum of ACT", "Diff_ACT-BGT", "Diff Percentage"]
CAT10 = "10 - Office Supplies And Equipment Expense"


def headers(html):
    thead = html[html.index("<thead"):html.index("</thead>")]
    return [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", thead, re.S)]


def cells(html, marker):
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        if marker in tr:
            return [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
    raise AssertionError("row not found: " + marker)


def seed_full():
    seed_gl()
    seed_cc([{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "IT Dept"},
             {"cost_center": "POCFAD", "total_cc": "$CC2", "seq": 3, "description": "Finance"},
             {"cost_center": "TFOPEX", "total_cc": "$TFOPEX", "seq": 5, "description": ""}])


def test_default_data_view_is_gl_combine_with_real_values(client):
    login(client)
    seed_full()
    html = page(client, "?view=data").data.decode()
    assert headers(html) == COMBINE_HEADERS
    assert cells(html, "A26-16-10-1") == [
        "6-1810", "GJ-1", "15/01/2026", "Zoom", "SMT - IT", "POITEC", "-957.910", "SMT", "70108100",
        "$POITEC", "1", "26", "16", "-10-", "A26-16-10-1", "- Act 2026 : Zoom Month : 1", CAT10]
    row = cells(html, "A26-3-10-1")
    assert row[6] == "5.000.000" and row[9] == "$CC2" and row[2] == "10/02/2026" and row[10] == "2"
    assert cells(html, "A26-5-20-1")[7:9] == ["ETF", "70119100"]


def test_table_append1_shows_append1_columns(client):
    login(client)
    seed_full()
    html = page(client, "?view=data&table=append1").data.decode()
    assert headers(html) == APPEND1_HEADERS
    assert cells(html, "Zoom") == ["70108100", "1", "26", "POITEC", "POITEC", CAT10, "SMT - IT",
                                   "- Act 2026 : Zoom Month : 1", "0,0", "3", "1", "-1,0", "0,0"]


def test_invalid_table_falls_back_to_combine(client):
    login(client)
    seed_full()
    for qs in ("?view=data&table=bogus", "?view=data&table=", "?view=data&table=APPEND1"):
        resp = page(client, qs)
        assert resp.status_code == 200 and headers(resp.data.decode()) == COMBINE_HEADERS, qs


def test_table_switch_links_preserve_filters(client):
    login(client)
    seed_full()
    html = page(client, "?view=data&table=append1&yy=2026&mm=2&cc=POCFAD&q=ATK").data.decode()
    links = {m[1]: m[0].replace("&amp;", "&") for m in
             re.findall(r'<a class="btn btn-sm[^"]*" href="([^"]*)">(GL Combine|Append1)</a>', html)}
    assert set(links) == {"GL Combine", "Append1"}
    for label, tbl in (("GL Combine", "combine"), ("Append1", "append1")):
        href = links[label]
        for part in ("view=data", "yy=2026", "mm=2", "cc=POCFAD", "q=ATK", "table=" + tbl):
            assert part in href, (label, part)
    assert "page=" not in links["Append1"]
    assert headers(page(client, "?" + links["GL Combine"].split("?", 1)[1]).data.decode()) == COMBINE_HEADERS


def test_view_toggle_to_data_preserves_table_and_q(client):
    login(client)
    seed_full()
    html = page(client, "?view=report&table=append1&q=ATK&cc=POCFAD").data.decode()
    m = re.search(r'href="([^"]*)">Data</a>', html)
    href = m.group(1).replace("&amp;", "&")
    for part in ("view=data", "table=append1", "q=ATK", "cc=POCFAD"):
        assert part in href, part


def test_data_search_by_new_code_and_id(client):
    login(client)
    seed_full()
    html = page(client, "?view=data&q=A26-3-10-1").data.decode()
    assert "ATK" in html and "Zoom" not in html and "Biaya admin" not in html
    svc.replace_all("smt", [
        mkrow(acc_management="6-1810", tgl="2026-01-15", debit_credit=1000000.0, job_name="POITEC",
              id_no="GJ-777", allocation_memo="Zoom"),
        mkrow(acc_management="6-1810", tgl="2026-01-16", debit_credit=2000000.0, job_name="POITEC",
              id_no="GJ-888", allocation_memo="Other")], LOG)
    html = page(client, "?view=data&q=gj-777").data.decode()
    assert "Zoom" in html and "Other" not in html


def test_data_rows_follow_build_order(client):
    login(client)
    seed_gl(extra_smt=[mkrow(acc_management="6-1810", tgl="2026-01-20", debit_credit=1000000.0,
                             job_name="POCFAD", allocation_memo="LateJan")])
    seed_cc([{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": ""},
             {"cost_center": "POCFAD", "total_cc": "$POCFAD", "seq": 3, "description": ""},
             {"cost_center": "TFOPEX", "total_cc": "$TFOPEX", "seq": 5, "description": ""}])
    html = page(client, "?view=data").data.decode()
    codes = re.findall(r"A26-\d+-\d+-\d+", html)
    # SMT in GL order (Jan, Feb, late Jan), then ETF; not re-sorted by month
    assert codes == ["A26-16-10-1", "A26-3-10-1", "A26-3-10-2", "A26-5-20-1"]


def test_report_view_layout_and_values(client):
    login(client)
    seed_full()
    html = page(client, "?cc=POITEC").data.decode()
    assert headers(html) == REPORT_HEADERS
    assert "In Rp Mio" in html
    assert "POITEC – IT Dept" in html
    assert "CC: POITEC | YY: 2026 | MM: s/d Februari" in html
    assert cells(html, "SMT - IT") == ["", "3", "1", "- Act 2026 : Zoom Month : 1", "SMT - IT",
                                       "0,0", "0,0", "0,0", "-1,0", "-1,0", ""]
    assert cells(html, "Total POITEC") == ["Total POITEC", "0,0", "0,0", "0,0", "-1,0", "-1,0", ""]
    assert cells(html, CAT10)[-6:] == ["0,0", "0,0", "0,0", "-1,0", "-1,0", ""]
    assert "-0,0" not in html


def test_report_view_all_cost_centers_echo_and_no_heading(client):
    login(client)
    seed_full()
    html = page(client, "").data.decode()
    assert "CC: All | YY: 2026 | MM: s/d Februari" in html
    assert "POITEC – IT Dept" not in html and "In Rp Mio" in html


def test_report_heading_without_description_is_just_the_cc(client):
    login(client)
    seed_full()
    html = page(client, "?cc=TFOPEX").data.decode()
    assert '<h3 class="gl-heading">TFOPEX</h3>' in html


# ---- needs-resync banner (old-style map: COA rows only, no CC sheet / Code column) -----------
RESYNC_FIRST = ("Pemetaan perlu disync ulang: sheet CC dan kolom Code belum dimuat, jadi COST CENTER2, "
                "CC1, BC1 dan New Code belum valid.")
RESYNC_ADMIN = RESYNC_FIRST + " Upload Management Report - MASTER.xlsb lalu klik Sync pemetaan COA & CC."
RESYNC_USER = RESYNC_FIRST + " Minta admin untuk sync pemetaan."


def test_old_style_map_shows_resync_banner_for_admin_and_no_cc_banner(client):
    login(client)
    seed_gl()
    seed_map()                                           # no cc_rows: gl_cc_map empty, rows_cc 0
    from markupsafe import escape
    for view in ("", "?view=data"):
        html = page(client, view).data.decode()
        assert str(escape(RESYNC_ADMIN)) in html and RESYNC_USER not in html
        assert "belum ada di sheet CC" not in html
        assert html.count("Pemetaan perlu disync ulang") == 1


def test_old_style_map_shows_resync_banner_for_non_admin(client):
    make_non_admin(client)
    seed_gl()
    seed_map()
    html = page(client).data.decode()
    assert RESYNC_USER in html and RESYNC_ADMIN not in html
    assert "belum ada di sheet CC" not in html


def test_complete_map_has_no_resync_banner_but_keeps_cc_banner(client):
    login(client)
    seed_gl()
    seed_cc([{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": ""},
             {"cost_center": "POCFAD", "total_cc": "$POCFAD", "seq": 3, "description": ""}])
    html = page(client).data.decode()
    assert "Pemetaan perlu disync ulang" not in html
    assert "1 cost center belum ada di sheet CC (COST CENTER2 kosong, CC1 = 0): TFOPEX (1)" in html

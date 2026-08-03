path_test_service = r"C:\Financehub\app\tests\test_sponsorship_service.py"
with open(path_test_service, "r", encoding="utf-8") as f:
    ts = f.read()

new_tests = """
def test_list_transaksi_filter_by_cat3_list(app):
    _seed_one_perusahaan()
    seed_perusahaan([("PT KUNCIRANMAS SEJATI", "Property", "PROPERTY")])
    create_transaksi(SMT, _valid_payload())  # cat1=SMART -> AGRI
    create_transaksi(SMT, _valid_payload(cat1="PT KUNCIRANMAS SEJATI"))
    rows = list_transaksi(SMT, filters={"cat3": ["PROPERTY", "AGRI"]})
    assert len(rows) == 2
    rows_single = list_transaksi(SMT, filters={"cat3": ["PROPERTY"]})
    assert len(rows_single) == 1
    assert rows_single[0]["cat1"] == "PT KUNCIRANMAS SEJATI"


def test_list_transaksi_filter_by_cat_list(app):
    _seed_one_perusahaan()
    create_transaksi(SMT, _valid_payload(cat="Sponsorship"))
    create_transaksi(SMT, _valid_payload(cat="CSR Gedung"))
    rows = list_transaksi(SMT, filters={"cat": ["Sponsorship", "CSR Gedung"]})
    assert len(rows) == 2
    rows_single = list_transaksi(SMT, filters={"cat": ["CSR Gedung"]})
    assert len(rows_single) == 1
    assert rows_single[0]["cat"] == "CSR Gedung"
"""
# Insert after test_list_transaksi_filter_by_cat3
if "def test_list_transaksi_filter_by_cat3" in ts:
    import re
    # Find the end of test_list_transaksi_filter_by_cat3
    match = re.search(r'def test_list_transaksi_filter_by_cat3\(app\):.*?assert len\(rows\) == 1\n    assert rows\[0\]\["cat1"\] == "PT KUNCIRANMAS SEJATI"\n', ts, flags=re.DOTALL)
    if match:
        ts = ts[:match.end()] + new_tests + ts[match.end():]
        with open(path_test_service, "w", encoding="utf-8") as f:
            f.write(ts)

path_test_routes = r"C:\Financehub\app\tests\test_sponsorship_routes.py"
with open(path_test_routes, "r", encoding="utf-8") as f:
    tr = f.read()

new_route_test = """
def test_api_dashboard_data_accepts_multi_value_cat_and_pillar(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/api/dashboard-data", query_string=[
        ("cat", "Sponsorship"), ("cat", "CSR Gedung"),
        ("cat3", "AGRI"), ("cat3", "APP"),
    ])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"]["total_count"] == 1
"""
# Insert after test_api_dashboard_data_rejects_non_smt
import re
match = re.search(r'def test_api_dashboard_data_rejects_non_smt\(client\):.*?assert resp.status_code == 403\n', tr, flags=re.DOTALL)
if match:
    tr = tr[:match.end()] + new_route_test + tr[match.end():]
    with open(path_test_routes, "w", encoding="utf-8") as f:
        f.write(tr)
        
print("done tests")

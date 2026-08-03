import re

routes_path = r"C:\Financehub\app\modules\beasiswa\routes.py"
with open(routes_path, "r", encoding="utf-8") as f:
    routes = f.read()

# Add import
import_marker = "from modules.beasiswa.service import"
if "from format_utils import format_rupiah" not in routes:
    routes = routes.replace(import_marker, import_marker + "\nfrom format_utils import format_rupiah")

# Replace budget_siswa_export
routes = routes.replace('r.get("pillar",""), f"{r.get(\'amount\',0):,.0f}"])', 'r.get("pillar",""), format_rupiah(r.get(\'amount\',0), prefix="")])')
routes = routes.replace('data.append(["", "TOTAL", "", "", "", f"{grand:,.0f}"])', 'data.append(["", "TOTAL", "", "", "", format_rupiah(grand, prefix="")])')

# Replace budget_export_pdf
routes = routes.replace('r.get("pillar",""), f"{a:,.0f}"])', 'r.get("pillar",""), format_rupiah(a, prefix="")])')
routes = routes.replace('data.append(["","","TOTAL","","","","","",f"{total:,.0f}"])', 'data.append(["","","TOTAL","","","","","",format_rupiah(total, prefix="")])')

# Replace payment_export_pdf
routes = routes.replace('r.get("pillar",""), f"{a:,.0f}",', 'r.get("pillar",""), format_rupiah(a, prefix=""),')
routes = routes.replace('data.append(["","","TOTAL","","","","","",f"{total:,.0f}","","",""])', 'data.append(["","","TOTAL","","","","","",format_rupiah(total, prefix=""),"","",""])')

# Replace laporan_export
routes = routes.replace('sum_data.append([c["cat1"], f"{c[\'budget\']:,.0f}", f"{c[\'payment\']:,.0f}", f"{c[\'sisa\']:,.0f}"])', 'sum_data.append([c["cat1"], format_rupiah(c[\'budget\'], prefix=""), format_rupiah(c[\'payment\'], prefix=""), format_rupiah(c[\'sisa\'], prefix="")])')

routes = routes.replace('''sum_data.append(["TOTAL", f"{data['total_budget']:,.0f}",
                   f"{data['total_payment']:,.0f}", f"{data['total_sisa']:,.0f}"])''', '''sum_data.append(["TOTAL", format_rupiah(data['total_budget'], prefix=""),
                   format_rupiah(data['total_payment'], prefix=""), format_rupiah(data['total_sisa'], prefix="")])''')

routes = routes.replace('r.get("pillar",""), f"{a:,.0f}"]))', 'r.get("pillar",""), format_rupiah(a, prefix="")]))')
routes = routes.replace('bgt_data.append(wrap_row(["", "TOTAL", "", "", f"{bgt_total:,.0f}"], is_footer=True))', 'bgt_data.append(wrap_row(["", "TOTAL", "", "", format_rupiah(bgt_total, prefix="")], is_footer=True))')
routes = routes.replace('f"{a:,.0f}", r.get("status","")]))', 'format_rupiah(a, prefix=""), r.get("status","")]))')
routes = routes.replace('pay_data.append(wrap_row(["", "TOTAL", "", "", "", f"{pay_total:,.0f}", ""], is_footer=True))', 'pay_data.append(wrap_row(["", "TOTAL", "", "", "", format_rupiah(pay_total, prefix=""), ""], is_footer=True))')

# Replace rekap_export_pdf
routes = routes.replace('fmt = lambda n: f"{n:,.0f}"', 'fmt = lambda n: format_rupiah(n, prefix="")')
routes = routes.replace('header.append(["","","TOTAL","","","", f"{tb:,.0f}", f"{tp:,.0f}", f"{tb-tp:,.0f}"])', 'header.append(["","","TOTAL","","","", format_rupiah(tb, prefix=""), format_rupiah(tp, prefix=""), format_rupiah(tb-tp, prefix="")])')


with open(routes_path, "w", encoding="utf-8") as f:
    f.write(routes)


# Test additions for test_beasiswa_routes.py
test_path = r"C:\Financehub\app\tests\test_beasiswa_routes.py"
test_append = '''

def test_budget_export_pdf_returns_pdf(client):
    from tests.test_beasiswa_routes import _login, _select_etf
    _login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/budget/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_payment_export_pdf_returns_pdf(client):
    from tests.test_beasiswa_routes import _login, _select_etf
    _login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/payment/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_rekap_export_pdf_returns_pdf(client):
    from tests.test_beasiswa_routes import _login, _select_etf
    _login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/rekap/export/pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_budget_siswa_export_pdf_does_not_crash(client):
    from tests.test_beasiswa_routes import _login, _select_etf
    _login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/budget/siswa/NOTFOUND/export/pdf")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.data[:4] == b"%PDF"


def test_laporan_export_pdf_does_not_crash(client):
    from tests.test_beasiswa_routes import _login, _select_etf
    _login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/laporan/siswa/NOTFOUND/export/pdf")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.data[:4] == b"%PDF"
'''

with open(test_path, "a", encoding="utf-8") as f:
    f.write(test_append)

print("Task 3 complete")

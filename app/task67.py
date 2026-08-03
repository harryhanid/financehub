# 1. Create test file for Task 6
test_code = """from modules.sponsorship.service import seed_perusahaan, create_transaksi

COMPANY_ID = 1  # SMT


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def _seed(n):
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    for i in range(n):
        result = create_transaksi(COMPANY_ID, {
            "cat": "Sponsorship",
            "description": "Akademisi",
            "tanggal_form_sponsor": "2026-06-01",
            "cat1": "SMART",
            "lembaga_perorangan": f"Lembaga {i}",
            "amount_request": 1000000,
        })
        assert result["ok"] is True, result


def test_page_size_query_param_controls_slicing(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data?page_size=2")
    assert resp.status_code == 200
    assert b"Halaman 1 dari 2" in resp.data


def test_page_size_defaults_when_absent(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data")
    assert resp.status_code == 200
    assert b"budget-pagination" not in resp.data  # 3 rows < default 100, hidden


def test_page_size_ignores_invalid_values(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data?page_size=abc")
    assert resp.status_code == 200


def test_page_size_clamped_to_max(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data?page_size=99999")
    assert resp.status_code == 200
"""
with open(r"C:\Financehub\app\tests\test_sponsorship_dynamic_page_size.py", "w", encoding="utf-8") as f:
    f.write(test_code)

# 2. Modify sponsorship routes
routes_path = r"C:\Financehub\app\modules\sponsorship\routes.py"
with open(routes_path, "r", encoding="utf-8") as f:
    routes = f.read()

new_constants = """PER_PAGE = 100
PER_PAGE_MAX = PER_PAGE * 4


def _resolve_page_size():
    from flask import request
    try:
        requested = int(request.args.get("page_size", PER_PAGE))
    except ValueError:
        return PER_PAGE
    if 1 <= requested <= PER_PAGE_MAX:
        return requested
    return PER_PAGE"""
if "_resolve_page_size()" not in routes:
    routes = routes.replace("PER_PAGE = 100", new_constants)

old_paging = """    total = count_transaksi(_cid(), filters) if not _wrong_company() else 0
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    rows = list_transaksi(_cid(), filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE) if not _wrong_company() else []"""
new_paging = """    total = count_transaksi(_cid(), filters) if not _wrong_company() else 0
    page_size = _resolve_page_size()
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    rows = list_transaksi(_cid(), filters, limit=page_size, offset=(page - 1) * page_size) if not _wrong_company() else []"""
if "page_size = _resolve_page_size()" not in routes:
    routes = routes.replace(old_paging, new_paging)

routes = routes.replace("rows=rows, page=page, total_pages=total_pages, total_count=total, years=years,",
                        "rows=rows, page=page, page_size=page_size, total_pages=total_pages, total_count=total, years=years,")

with open(routes_path, "w", encoding="utf-8") as f:
    f.write(routes)


# 3. Modify sponsorship template (Task 7)
html_path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Replace filter_qs prev/next logic
old_prev = '<a class="budget-btn {% if page <= 1 %}disabled{% endif %}" href="?page={{ page - 1 }}{{ filter_qs }}">‹ Prev</a>'
new_prev = '<a class="budget-btn {% if page <= 1 %}disabled{% endif %}" href="?page={{ page - 1 }}&page_size={{ page_size }}{{ filter_qs }}">‹ Prev</a>'
html = html.replace(old_prev, new_prev)

old_next = '<a class="budget-btn {% if page >= total_pages %}disabled{% endif %}" href="?page={{ page + 1 }}{{ filter_qs }}">Next ›</a>'
new_next = '<a class="budget-btn {% if page >= total_pages %}disabled{% endif %}" href="?page={{ page + 1 }}&page_size={{ page_size }}{{ filter_qs }}">Next ›</a>'
html = html.replace(old_next, new_next)

# Add initServerPagedDynamicSize logic
script_injection = """<script>
if ({{ total_count }} > 0) {
  window.addEventListener('load', () => {
    initServerPagedDynamicSize({
      cacheName: 'sponsorship-data',
      paramName: 'page_size',
      scrollContainer: '.budget-table-container, .budget-page',
      rowSelector: '.budget-table tbody tr',
      defaultSize: 100,
      renderedPageSize: {{ page_size }},
    });
  });
}
</script>"""
if "initServerPagedDynamicSize" not in html:
    html = html.replace('<script src="{{ url_for(\'static\', filename=\'js/sponsorship.js\') }}"></script>',
                        '<script src="{{ url_for(\'static\', filename=\'js/sponsorship.js\') }}"></script>\n' + script_injection)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Tasks 6 & 7 complete")

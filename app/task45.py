# 1. Create test file
test_code = """from database import get_conn
from modules.etf_payment_application.service import create_pa

COMPANY_ID = 2  # ETF


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def _seed_students_and_pas(n):
    conn = get_conn()
    ids = []
    for i in range(n):
        conn.execute(
            "INSERT INTO siswa (company_id, code, nama, jenjang, angkatan, "
            "program, fakultas, universitas, status, ipk_sem1) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (COMPANY_ID, f"900000{i}", f"Siswa {i}", "S1", 2023,
             "SMART", "Teknik", "Univ. Test", "Aktif", 3.5)
        )
        conn.commit()
        row = conn.execute("SELECT id FROM siswa WHERE code=?", (f"900000{i}",)).fetchone()
        ids.append(row["id"])
    conn.close()
    for i, sid in enumerate(ids):
        result = create_pa(COMPANY_ID, {
            "tgl_payment_application": "2026-06-01",
            "tgl_surat_pengajuan": "2026-06-01",
            "keterangan": f"Test PA {i}",
        }, [
            {"student_id": sid, "jenis_pembayaran": "By Pendidikan",
             "semester": "Semester 3", "tahun_ajaran": "2025/2026",
             "ipk_sem_sebelumnya": 3.6, "jumlah_pembayaran": 5000000}
        ], tab="agri")
        assert result["ok"] is True, result


def test_page_size_query_param_controls_slicing(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri&page_size=2")
    assert resp.status_code == 200
    assert b"halaman 1/2" in resp.data


def test_page_size_defaults_when_absent(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri")
    assert resp.status_code == 200
    assert b"halaman" not in resp.data  # 3 rows < default 50, pagination hidden


def test_page_size_ignores_invalid_values(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri&page_size=abc")
    assert resp.status_code == 200
    assert b"halaman" not in resp.data


def test_page_size_clamped_to_max(client):
    login(client)
    _select_etf(client)
    _seed_students_and_pas(3)
    resp = client.get("/etf-payment-application/?tab=agri&page_size=99999")
    assert resp.status_code == 200
    assert b"halaman" not in resp.data
"""
with open(r"C:\Financehub\app\tests\test_pa_dynamic_page_size.py", "w", encoding="utf-8") as f:
    f.write(test_code)

# 2. Modify routes.py
routes_path = r"C:\Financehub\app\modules\etf_payment_application\routes.py"
with open(routes_path, "r", encoding="utf-8") as f:
    routes = f.read()

new_constants = """PA_PAGE_SIZE = 50
PA_PAGE_SIZE_MAX = PA_PAGE_SIZE * 4


def _resolve_page_size():
    from flask import request
    try:
        requested = int(request.args.get("page_size", PA_PAGE_SIZE))
    except ValueError:
        return PA_PAGE_SIZE
    if 1 <= requested <= PA_PAGE_SIZE_MAX:
        return requested
    return PA_PAGE_SIZE"""

if "_resolve_page_size()" not in routes:
    routes = routes.replace("PA_PAGE_SIZE = 50", new_constants)

old_vars = """    page = 1
    total_pages = 1
    total_rows = 0
    start_row = 0
    end_row = 0"""
new_vars = """    page = 1
    page_size = PA_PAGE_SIZE
    total_pages = 1
    total_rows = 0
    start_row = 0
    end_row = 0"""
routes = routes.replace(old_vars, new_vars)

old_paging = """        total_rows = len(filtered_rows)
        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1
        total_pages = max(1, -(-total_rows // PA_PAGE_SIZE))
        page = min(max(1, page), total_pages)
        offset = (page - 1) * PA_PAGE_SIZE
        pa_rows = filtered_rows[offset:offset + PA_PAGE_SIZE]
        start_row = offset + 1 if total_rows else 0
        end_row = min(offset + PA_PAGE_SIZE, total_rows)"""
new_paging = """        total_rows = len(filtered_rows)
        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1
        page_size = _resolve_page_size()
        total_pages = max(1, -(-total_rows // page_size))
        page = min(max(1, page), total_pages)
        offset = (page - 1) * page_size
        pa_rows = filtered_rows[offset:offset + page_size]
        start_row = offset + 1 if total_rows else 0
        end_row = min(offset + page_size, total_rows)"""
if "page_size = _resolve_page_size()" not in routes:
    routes = routes.replace(old_paging, new_paging)

routes = routes.replace("page_size=PA_PAGE_SIZE,", "page_size=page_size,")

with open(routes_path, "w", encoding="utf-8") as f:
    f.write(routes)


# 3. Modify template
html_path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

old_macro = """{% macro pa_page_url(p) -%}
?tab={{ active_tab }}{% if active_sf %}&sf={{ active_sf }}{% endif %}{% if f_nama %}&nama={{ f_nama | urlencode }}{% endif %}{% if f_jenjang %}&jenjang={{ f_jenjang | urlencode }}{% endif %}{% if f_program %}&program={{ f_program | urlencode }}{% endif %}{% if f_angkatan %}&angkatan={{ f_angkatan | urlencode }}{% endif %}{% if f_jenis %}&jenis={{ f_jenis | urlencode }}{% endif %}{% if f_pam %}&pam={{ f_pam | urlencode }}{% endif %}{% if f_bulan_pa %}&bulan_pa={{ f_bulan_pa }}{% endif %}{% if f_tahun_pa %}&tahun_pa={{ f_tahun_pa }}{% endif %}&page={{ p }}
{%- endmacro %}"""
new_macro = """{% macro pa_page_url(p) -%}
?tab={{ active_tab }}{% if active_sf %}&sf={{ active_sf }}{% endif %}{% if f_nama %}&nama={{ f_nama | urlencode }}{% endif %}{% if f_jenjang %}&jenjang={{ f_jenjang | urlencode }}{% endif %}{% if f_program %}&program={{ f_program | urlencode }}{% endif %}{% if f_angkatan %}&angkatan={{ f_angkatan | urlencode }}{% endif %}{% if f_jenis %}&jenis={{ f_jenis | urlencode }}{% endif %}{% if f_pam %}&pam={{ f_pam | urlencode }}{% endif %}{% if f_bulan_pa %}&bulan_pa={{ f_bulan_pa }}{% endif %}{% if f_tahun_pa %}&tahun_pa={{ f_tahun_pa }}{% endif %}&page_size={{ page_size }}&page={{ p }}
{%- endmacro %}"""
html = html.replace(old_macro, new_macro)

old_script = """<script>
const TODAY   = new Date().toISOString().slice(0,10);
const ACTIVE_TAB = "{{ active_tab }}";"""
new_script = """<script>
const TODAY   = new Date().toISOString().slice(0,10);
const ACTIVE_TAB = "{{ active_tab }}";
const PA_RENDERED_PAGE_SIZE = {{ page_size }};
const PA_TOTAL_ROWS = {{ total_rows }};

if (PA_TOTAL_ROWS > 0) {
  window.addEventListener('load', () => {
    initServerPagedDynamicSize({
      cacheName: 'pa',
      paramName: 'page_size',
      scrollContainer: '#pa-scroll-wrap',
      rowSelector: '#pa-table tbody tr',
      defaultSize: 50,
      renderedPageSize: PA_RENDERED_PAGE_SIZE,
    });
  });
}"""
if "initServerPagedDynamicSize" not in html:
    html = html.replace(old_script, new_script)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Tasks 4 & 5 complete")

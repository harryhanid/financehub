# Finance Hub Fase 1 — Part 4: REST API + Coming Soon + Deployment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi REST API `/api/v1/` untuk semua operasi Beasiswa dan Payment Memo, halaman Coming Soon untuk 5 modul yang belum ready, dan konfigurasi deployment via waitress untuk LAN.

**Architecture:** API endpoints ditambahkan ke `modules/beasiswa/api.py` dan `modules/payment_memo/api.py` (Blueprint terpisah dari HTML routes). Auth API via JWT Bearer header. Coming Soon adalah halaman template sederhana. Deployment menggunakan `waitress` (WSGI server Windows) via `run_production.py`.

**Tech Stack:** Flask Blueprint, flask-jwt-extended (headers mode), waitress 3.x

**Prerequisite:** Part 1 + Part 2 + Part 3 sudah selesai. Semua service layer sudah ada.

---

## File Structure (Part 4 additions)

```
C:\Financehub\app\
├── modules/
│   ├── beasiswa/
│   │   └── api.py              ← REST: GET/POST /api/v1/siswa, /api/v1/budget, /api/v1/payment, /api/v1/rekap
│   ├── payment_memo/
│   │   └── api.py              ← REST: GET/POST /api/v1/payment-memo, /api/v1/payment-draft
│   └── coming_soon/
│       ├── __init__.py
│       └── routes.py           ← /bank, /account-payable, /advance, /petty-cash, /sponsorship
├── templates/
│   └── coming_soon.html        ← Satu template reusable untuk semua coming soon pages
├── run_production.py           ← waitress launcher untuk LAN
└── README.md                   ← Setup + cara jalankan
```

---

## Task 1: Beasiswa REST API (`/api/v1/`)

**Files:**
- Create: `C:\Financehub\app\modules\beasiswa\api.py`
- Modify: `C:\Financehub\app\app.py` — register blueprint `beasiswa_api`
- Test: `C:\Financehub\app\tests\test_beasiswa_api.py`

- [ ] **Step 1: Tulis test untuk API siswa**

```python
# tests/test_beasiswa_api.py
import pytest
from app import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DB_PATH": str(tmp_path / "test.db")})
    with app.test_client() as c:
        yield c

def login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@2026!"})
    return r.get_json()["access_token"]

def test_get_siswa_requires_auth(client):
    r = client.get("/api/v1/siswa?company=ETF")
    assert r.status_code == 401

def test_get_siswa_empty(client):
    token = login(client)
    r = client.get("/api/v1/siswa?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert isinstance(body["data"], list)

def test_post_siswa(client):
    token = login(client)
    payload = {
        "nama": "Budi Santoso",
        "jenjang": "S1",
        "angkatan": 2024,
        "program": "Tjipta Siswa Mandiri",
        "company": "ETF"
    }
    r = client.post("/api/v1/siswa",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["ok"] is True
    assert "code" in body["data"]

def test_get_rekap(client):
    token = login(client)
    r = client.get("/api/v1/rekap?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
```

- [ ] **Step 2: Jalankan test — pastikan FAIL (api.py belum ada)**

```bash
cd C:\Financehub\app
pytest tests/test_beasiswa_api.py -v
```

Expected: FAIL dengan `404` atau `ImportError`.

- [ ] **Step 3: Buat `modules/beasiswa/api.py`**

```python
# modules/beasiswa/api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .service import (
    get_siswa_list, add_siswa, get_siswa_by_code, update_siswa,
    get_budget_list, add_budget,
    get_payment_list, add_payment,
    get_rekap_data
)
from auth.middleware import api_role_required

beasiswa_api = Blueprint("beasiswa_api", __name__, url_prefix="/api/v1")


def _company(req):
    """Ambil company dari query string."""
    company = req.args.get("company") or req.get_json(silent=True, force=True).get("company", "")
    if company not in ("SMT", "ETF"):
        return None
    return company


def ok(data, status=200):
    return jsonify({"ok": True, "data": data}), status


def err(pesan, status=400):
    return jsonify({"ok": False, "pesan": pesan}), status


# ─── SISWA ─────────────────────────────────────────────────────────────

@beasiswa_api.get("/siswa")
@jwt_required(locations=["headers"])
def api_list_siswa():
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    filters = {
        "search":  request.args.get("search", ""),
        "status":  request.args.get("status", ""),
        "program": request.args.get("program", ""),
    }
    return ok(get_siswa_list(company, **filters))


@beasiswa_api.get("/siswa/<code>")
@jwt_required(locations=["headers"])
def api_get_siswa(code):
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    siswa = get_siswa_by_code(company, code)
    if not siswa:
        return err("Siswa tidak ditemukan", 404)
    return ok(siswa)


@beasiswa_api.post("/siswa")
@jwt_required(locations=["headers"])
@api_role_required("requester", "verificator", "releaser")
def api_add_siswa():
    body = request.get_json(force=True) or {}
    company = body.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    required = ["nama", "jenjang", "angkatan", "program"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return err(f"Field wajib: {', '.join(missing)}")
    code = add_siswa(company, body)
    return ok({"code": code}, 201)


@beasiswa_api.put("/siswa/<code>")
@jwt_required(locations=["headers"])
@api_role_required("requester", "verificator", "releaser")
def api_update_siswa(code):
    body = request.get_json(force=True) or {}
    company = body.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    update_siswa(company, code, body)
    return ok({"code": code})


# ─── BUDGET ────────────────────────────────────────────────────────────

@beasiswa_api.get("/budget")
@jwt_required(locations=["headers"])
def api_list_budget():
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    return ok(get_budget_list(company,
                              code=request.args.get("code", ""),
                              pillar=request.args.get("pillar", "")))


@beasiswa_api.post("/budget")
@jwt_required(locations=["headers"])
@api_role_required("requester", "verificator", "releaser")
def api_add_budget():
    body = request.get_json(force=True) or {}
    company = body.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    required = ["siswa_code", "cat1", "cat2", "tanggal", "amount", "pillar"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return err(f"Field wajib: {', '.join(missing)}")
    row_id = add_budget(company, body)
    return ok({"id": row_id}, 201)


# ─── PAYMENT ───────────────────────────────────────────────────────────

@beasiswa_api.get("/payment")
@jwt_required(locations=["headers"])
def api_list_payment():
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    return ok(get_payment_list(company,
                               code=request.args.get("code", ""),
                               pillar=request.args.get("pillar", ""),
                               status=request.args.get("status", "")))


@beasiswa_api.post("/payment")
@jwt_required(locations=["headers"])
@api_role_required("requester")
def api_add_payment():
    body = request.get_json(force=True) or {}
    company = body.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    required = ["siswa_code", "cat1", "cat2", "tanggal", "amount", "pillar"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return err(f"Field wajib: {', '.join(missing)}")
    row_id = add_payment(company, body, created_by=get_jwt_identity())
    return ok({"id": row_id}, 201)


# ─── REKAP ─────────────────────────────────────────────────────────────

@beasiswa_api.get("/rekap")
@jwt_required(locations=["headers"])
def api_rekap():
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    data = get_rekap_data(company,
                          program=request.args.get("program", ""),
                          pillar=request.args.get("pillar", ""),
                          status=request.args.get("status", ""))
    return ok(data)


@beasiswa_api.get("/dashboard")
@jwt_required(locations=["headers"])
def api_dashboard():
    from database import get_conn
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM companies WHERE code=?", (company,))
    row = c.fetchone()
    if not row:
        return err("Company tidak ditemukan", 404)
    cid = row["id"]
    c.execute("SELECT COUNT(*) FROM siswa WHERE company_id=? AND status='Aktif'", (cid,))
    total_aktif = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM budget_beasiswa WHERE company_id=?", (cid,))
    total_budget = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payment_beasiswa WHERE company_id=?", (cid,))
    total_payment = c.fetchone()[0]
    conn.close()
    return ok({
        "total_siswa_aktif": total_aktif,
        "total_budget": total_budget,
        "total_payment": total_payment,
        "sisa": total_budget - total_payment,
    })
```

- [ ] **Step 4: Tambahkan `api_role_required` di `auth/middleware.py`**

Buka `C:\Financehub\app\auth\middleware.py` dan tambahkan fungsi berikut setelah fungsi `html_role_required` yang sudah ada:

```python
def api_role_required(*roles):
    """Decorator untuk REST API — cek role dari JWT claims."""
    from functools import wraps
    from flask_jwt_extended import get_jwt
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get("role", "requester")
            if user_role not in roles:
                return jsonify({"ok": False, "pesan": "Akses ditolak"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 5: Register `beasiswa_api` blueprint di `app.py`**

Buka `C:\Financehub\app\app.py` dan tambahkan di dalam fungsi `create_app()`:

```python
from modules.beasiswa.api import beasiswa_api
app.register_blueprint(beasiswa_api)
```

- [ ] **Step 6: Jalankan test**

```bash
cd C:\Financehub\app
pytest tests/test_beasiswa_api.py -v
```

Expected: semua 4 test PASS.

- [ ] **Step 7: Commit**

```bash
git add app/modules/beasiswa/api.py app/auth/middleware.py app/app.py app/tests/test_beasiswa_api.py
git commit -m "feat: beasiswa REST API — GET/POST siswa, budget, payment, rekap, dashboard"
```

---

## Task 2: Payment Memo REST API

**Files:**
- Create: `C:\Financehub\app\modules\payment_memo\api.py`
- Modify: `C:\Financehub\app\app.py` — register blueprint `payment_memo_api`
- Test: `C:\Financehub\app\tests\test_memo_api.py`

- [ ] **Step 1: Tulis test**

```python
# tests/test_memo_api.py
import pytest
from app import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DB_PATH": str(tmp_path / "test.db")})
    with app.test_client() as c:
        yield c

def login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@2026!"})
    return r.get_json()["access_token"]

def test_get_draft_payments_empty(client):
    token = login(client)
    r = client.get("/api/v1/payment-draft?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert r.get_json()["data"] == []

def test_create_memo_requires_verificator(client):
    # Admin adalah releaser, bukan verificator — harus ditolak
    token = login(client)
    r = client.post("/api/v1/payment-memo",
                    json={"company": "ETF", "tanggal": "2026-05-30",
                          "notes": "", "item_ids": []},
                    headers={"Authorization": f"Bearer {token}"})
    # releaser tidak bisa buat memo — hanya verificator
    assert r.status_code == 403

def test_list_memo_empty(client):
    token = login(client)
    r = client.get("/api/v1/payment-memo?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.get_json()["data"], list)
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
cd C:\Financehub\app
pytest tests/test_memo_api.py -v
```

Expected: FAIL (blueprint belum ada).

- [ ] **Step 3: Buat `modules/payment_memo/api.py`**

```python
# modules/payment_memo/api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .service import (
    get_draft_payments, create_memo, get_memo_list,
    get_memo_detail, update_memo_status, generate_memo_pdf_buffer
)
from auth.middleware import api_role_required

payment_memo_api = Blueprint("payment_memo_api", __name__, url_prefix="/api/v1")


def ok(data, status=200):
    return jsonify({"ok": True, "data": data}), status


def err(pesan, status=400):
    return jsonify({"ok": False, "pesan": pesan}), status


@payment_memo_api.get("/payment-draft")
@jwt_required(locations=["headers"])
def api_draft_payments():
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    return ok(get_draft_payments(company))


@payment_memo_api.get("/payment-memo")
@jwt_required(locations=["headers"])
def api_list_memo():
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    return ok(get_memo_list(company))


@payment_memo_api.post("/payment-memo")
@jwt_required(locations=["headers"])
@api_role_required("verificator")
def api_create_memo():
    body = request.get_json(force=True) or {}
    company = body.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    if not body.get("tanggal"):
        return err("tanggal wajib diisi")
    memo_id, memo_number = create_memo(
        company=company,
        tanggal=body["tanggal"],
        notes=body.get("notes", ""),
        item_ids=body.get("item_ids", []),
        created_by=get_jwt_identity(),
    )
    return ok({"id": memo_id, "memo_number": memo_number}, 201)


@payment_memo_api.get("/payment-memo/<int:memo_id>")
@jwt_required(locations=["headers"])
def api_get_memo(memo_id):
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    memo = get_memo_detail(company, memo_id)
    if not memo:
        return err("Memo tidak ditemukan", 404)
    return ok(memo)


@payment_memo_api.put("/payment-memo/<int:memo_id>/status")
@jwt_required(locations=["headers"])
def api_update_memo_status(memo_id):
    body = request.get_json(force=True) or {}
    company = body.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    new_status = body.get("status")
    VALID = ("draft", "submitted", "approved", "paid")
    if new_status not in VALID:
        return err(f"Status harus salah satu dari: {', '.join(VALID)}")
    update_memo_status(company, memo_id, new_status, approved_by=get_jwt_identity())
    return ok({"id": memo_id, "status": new_status})


@payment_memo_api.get("/payment-memo/<int:memo_id>/export/pdf")
@jwt_required(locations=["headers"])
@api_role_required("verificator", "releaser")
def api_export_memo_pdf(memo_id):
    from flask import Response
    company = request.args.get("company")
    if company not in ("SMT", "ETF"):
        return err("company harus SMT atau ETF")
    memo = get_memo_detail(company, memo_id)
    if not memo:
        return err("Memo tidak ditemukan", 404)
    pdf_bytes = generate_memo_pdf_buffer(memo)
    filename = f"PAM_{memo['memo_number'].replace('/', '_')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

- [ ] **Step 4: Register blueprint di `app.py`**

```python
from modules.payment_memo.api import payment_memo_api
app.register_blueprint(payment_memo_api)
```

- [ ] **Step 5: Jalankan test**

```bash
cd C:\Financehub\app
pytest tests/test_memo_api.py -v
```

Expected: semua 3 test PASS.

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/api.py app/app.py app/tests/test_memo_api.py
git commit -m "feat: payment memo REST API — draft list, create memo, update status, PDF export"
```

---

## Task 3: Coming Soon Pages (5 modul)

**Files:**
- Create: `C:\Financehub\app\modules\coming_soon\__init__.py`
- Create: `C:\Financehub\app\modules\coming_soon\routes.py`
- Create: `C:\Financehub\app\templates\coming_soon.html`
- Modify: `C:\Financehub\app\app.py` — register blueprint

- [ ] **Step 1: Buat `modules/coming_soon/__init__.py`** (kosong)

```python
# modules/coming_soon/__init__.py
```

- [ ] **Step 2: Buat `modules/coming_soon/routes.py`**

```python
# modules/coming_soon/routes.py
from flask import Blueprint, render_template, session
from auth.middleware import jwt_html_required

coming_soon = Blueprint("coming_soon", __name__)

MODULES = {
    "bank":            {"label": "Bank",             "icon": "🏦", "desc": "Manajemen rekening bank perusahaan."},
    "account-payable": {"label": "Account Payable",  "icon": "📋", "desc": "Hutang dan pembayaran ke vendor."},
    "advance":         {"label": "Advance",           "icon": "💳", "desc": "Uang muka karyawan dan proyek."},
    "petty-cash":      {"label": "Petty Cash",        "icon": "💰", "desc": "Kas kecil operasional."},
    "sponsorship":     {"label": "Sponsorship",       "icon": "🤝", "desc": "Pengelolaan sponsorship dan donasi."},
}


@coming_soon.route("/bank")
@coming_soon.route("/account-payable")
@coming_soon.route("/advance")
@coming_soon.route("/petty-cash")
@coming_soon.route("/sponsorship")
@jwt_html_required
def coming_soon_page():
    from flask import request
    slug = request.path.lstrip("/")
    module = MODULES.get(slug, {"label": slug.title(), "icon": "🔜", "desc": "Segera hadir."})
    return render_template("coming_soon.html",
                           module=module,
                           company=session.get("company", ""))
```

- [ ] **Step 3: Buat `templates/coming_soon.html`**

```html
{% extends "base.html" %}
{% block title %}{{ module.label }} — Segera Hadir{% endblock %}
{% block content %}
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            min-height:60vh;text-align:center;gap:1.5rem;">
  <div style="font-size:4rem;">{{ module.icon }}</div>
  <h1 style="font-size:2rem;font-weight:700;color:#1a56db;">{{ module.label }}</h1>
  <p style="color:#6b7280;font-size:1.1rem;max-width:400px;">
    {{ module.desc }}<br>
    Modul ini sedang dalam pengembangan dan akan tersedia di <strong>Fase 2</strong>.
  </p>
  <span style="display:inline-flex;align-items:center;gap:.5rem;background:#fef3c7;
               color:#92400e;padding:.5rem 1.25rem;border-radius:9999px;font-weight:600;">
    🔜 Coming Soon
  </span>
  <a href="{{ url_for('dashboard.index') }}"
     style="color:#1a56db;text-decoration:none;font-size:.95rem;">
    ← Kembali ke Dashboard
  </a>
</div>
{% endblock %}
```

- [ ] **Step 4: Register di `app.py`**

```python
from modules.coming_soon.routes import coming_soon
app.register_blueprint(coming_soon)
```

- [ ] **Step 5: Pastikan navbar di `base.html` sudah ada link ke semua modul**

Verifikasi bahwa `templates/base.html` sudah memiliki menu item untuk Bank, AP, Advance, Petty Cash, Sponsorship yang mengarah ke URL:
- `/bank`
- `/account-payable`
- `/advance`
- `/petty-cash`
- `/sponsorship`

Jika belum, tambahkan di dalam section nav Coming Soon di `base.html`:

```html
<!-- Di dalam sidebar nav, setelah menu modul aktif -->
<div class="nav-section-label">Segera Hadir</div>
<a href="/bank" class="nav-item coming-soon">
  <span class="nav-icon">🏦</span> Bank
  <span class="cs-badge">Soon</span>
</a>
<a href="/account-payable" class="nav-item coming-soon">
  <span class="nav-icon">📋</span> Account Payable
  <span class="cs-badge">Soon</span>
</a>
<a href="/advance" class="nav-item coming-soon">
  <span class="nav-icon">💳</span> Advance
  <span class="cs-badge">Soon</span>
</a>
<a href="/petty-cash" class="nav-item coming-soon">
  <span class="nav-icon">💰</span> Petty Cash
  <span class="cs-badge">Soon</span>
</a>
<a href="/sponsorship" class="nav-item coming-soon">
  <span class="nav-icon">🤝</span> Sponsorship
  <span class="cs-badge">Soon</span>
</a>
```

Tambahkan CSS di `static/css/style.css`:

```css
.nav-section-label {
  font-size: .7rem;
  font-weight: 700;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: .08em;
  padding: .75rem 1rem .25rem;
}
.nav-item.coming-soon { opacity: .6; }
.nav-item.coming-soon:hover { opacity: .85; }
.cs-badge {
  margin-left: auto;
  font-size: .65rem;
  background: #fef3c7;
  color: #92400e;
  padding: .1rem .4rem;
  border-radius: 9999px;
  font-weight: 600;
}
```

- [ ] **Step 6: Test manual — jalankan dev server dan buka di browser**

```bash
cd C:\Financehub\app
python run.py
```

Buka `http://localhost:8080`, login, lalu klik Bank → harus tampil halaman Coming Soon.
Ulangi untuk account-payable, advance, petty-cash, sponsorship.

- [ ] **Step 7: Commit**

```bash
git add app/modules/coming_soon/ app/templates/coming_soon.html app/app.py app/static/css/style.css
git commit -m "feat: coming soon pages — bank, account-payable, advance, petty-cash, sponsorship"
```

---

## Task 4: waitress Production Launcher

**Files:**
- Create: `C:\Financehub\app\run_production.py`

- [ ] **Step 1: Buat `run_production.py`**

```python
# run_production.py
"""
Launcher production menggunakan waitress WSGI server.
Jalankan: python run_production.py

User lain di LAN akses via: http://[IP-laptop]:8080
Cari IP laptop: ipconfig → cari "IPv4 Address" pada adapter WiFi/LAN aktif.
"""
import os
import socket
from waitress import serve
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))

    # Tampilkan IP LAN agar user lain tahu URL yang harus dibuka
    local_ip = socket.gethostbyname(socket.gethostname())
    print("=" * 55)
    print("  Finance Hub — Production Server")
    print("=" * 55)
    print(f"  Local :  http://localhost:{port}")
    print(f"  LAN   :  http://{local_ip}:{port}")
    print("=" * 55)
    print("  Tekan Ctrl+C untuk menghentikan server")
    print()

    serve(app, host=host, port=port, threads=8)
```

- [ ] **Step 2: Pastikan `waitress` sudah ada di `requirements.txt`**

Buka `requirements.txt` — pastikan ada baris:

```
waitress>=3.0
```

Jika belum, tambahkan.

- [ ] **Step 3: Install waitress**

```bash
cd C:\Financehub\app
pip install waitress>=3.0
```

Expected output: `Successfully installed waitress-...`

- [ ] **Step 4: Test production launcher**

```bash
cd C:\Financehub\app
python run_production.py
```

Expected output:
```
=======================================================
  Finance Hub — Production Server
=======================================================
  Local :  http://localhost:8080
  LAN   :  http://192.168.x.x:8080
=======================================================
```

Buka `http://localhost:8080` di browser — pastikan halaman login muncul.
Tekan Ctrl+C untuk stop.

- [ ] **Step 5: Commit**

```bash
git add app/run_production.py app/requirements.txt
git commit -m "feat: waitress production launcher dengan LAN IP display"
```

---

## Task 5: README Setup Guide

**Files:**
- Create: `C:\Financehub\README.md`

- [ ] **Step 1: Buat `README.md`**

```markdown
# Finance Hub

Sistem manajemen keuangan internal untuk Sinar Mas Tjipta (SMT) dan Eka Tjipta Foundation (ETF).

## Setup (Pertama Kali)

### 1. Prasyarat
- Python 3.9 atau lebih baru
- Jalankan di laptop yang terhubung ke LAN/WiFi kantor

### 2. Install dependencies

```cmd
cd C:\Financehub\app
pip install -r requirements.txt
```

### 3. Jalankan (Development)

```cmd
python run.py
```

Buka `http://localhost:8080`

### 4. Jalankan (Production / LAN)

```cmd
python run_production.py
```

User lain di LAN buka: `http://[IP-yang-tampil]:8080`

---

## Login Pertama Kali

| Field    | Value          |
|----------|----------------|
| Username | `admin`        |
| Password | `Admin@2026!`  |

**Penting:** Ganti password segera setelah login pertama.

---

## Backup Database

File database: `C:\Financehub\app\finance_hub.db`

Backup manual ke Y:/ shared folder:
```cmd
copy C:\Financehub\app\finance_hub.db "Y:\Backup\finance_hub_%date%.db"
```

Atau set Windows Task Scheduler untuk backup otomatis tiap hari jam 18:00.

---

## Tips Laptop Server

- **Jangan biarkan laptop sleep** saat jam kerja: Settings → Power → Never sleep saat colok listrik
- **IP bisa berubah** jika reconnect WiFi — run `ipconfig` untuk cek IP terbaru, atau minta IT set static IP
- **Restart server** jika lemot: Ctrl+C → `python run_production.py` lagi

---

## Modul

| Modul               | Status    | Perusahaan  |
|---------------------|-----------|-------------|
| Beasiswa            | ✅ v1.0   | ETF         |
| Payment Memo        | ✅ v1.0   | SMT + ETF   |
| Payment Application | ✅ v1.0   | SMT + ETF   |
| Bank                | 🔜 Fase 2 | SMT + ETF   |
| Account Payable     | 🔜 Fase 2 | SMT + ETF   |
| Advance             | 🔜 Fase 2 | SMT + ETF   |
| Petty Cash          | 🔜 Fase 2 | SMT + ETF   |
| Sponsorship         | 🔜 Fase 2 | SMT         |

---

## REST API

Semua endpoint `/api/v1/` memerlukan header:
```
Authorization: Bearer <access_token>
```

Dapatkan token via `POST /auth/login` dengan body `{"username": "...", "password": "..."}`.

Dokumentasi lengkap: lihat PRD di `docs/specs/2026-05-30-finance-hub-prd.md`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README setup guide — install, jalankan, backup, tips laptop server"
```

---

## Task 6: Final Integration Test

- [ ] **Step 1: Jalankan seluruh test suite**

```bash
cd C:\Financehub\app
pytest tests/ -v --tb=short
```

Expected: semua test PASS. Jumlah test: 30+ assertions.

- [ ] **Step 2: Smoke test manual — full user journey**

1. Jalankan: `python run.py`
2. Buka `http://localhost:8080` → redirect ke `/login`
3. Login dengan `admin / Admin@2026!` → redirect ke change-password
4. Ganti password → redirect ke `/select-company`
5. Pilih ETF → Dashboard ETF
6. Klik Beasiswa → tab Siswa → Tambah Siswa Baru → isi form → Submit
7. Tab Budget → Pilih siswa tadi → isi budget → Submit
8. Tab Payment → isi payment → Submit
9. Menu Payment Memo → buat Memo baru dari draft payment tadi
10. Export PDF memo → pastikan PDF ter-download
11. Menu Bank → pastikan halaman Coming Soon muncul
12. API test:

```bash
# Di terminal lain saat server jalan:
curl -s -X POST http://localhost:8080/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"[password-baru]\"}" | python -m json.tool
```

- [ ] **Step 3: Commit final**

```bash
git add .
git commit -m "chore: finance hub fase 1 complete — all modules, API, coming soon, deployment"
```

---

**Part 4 selesai. Finance Hub Fase 1 lengkap:**

- ✅ **Part 1** — Scaffold, SQLite, JWT auth 3 role, company selector, dashboard
- ✅ **Part 2** — Beasiswa module (Siswa CRUD, Budget, Payment, Rekap, CSV/PDF export)
- ✅ **Part 3** — Payment Approval Memo, Payment Application, User Management
- ✅ **Part 4** — REST API `/api/v1/`, Coming Soon pages, waitress deployment, README

Jalankan produksi: `python run_production.py` dari `C:\Financehub\app\`

# Finance Hub Fase 1 — Part 3: Payment Memo + Payment Application + User Management

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi Payment Approval Memo (list draft, buat memo, update status, PDF export), Payment Application monitoring (TAT tracking), dan User Management (Releaser: tambah/nonaktifkan user).

**Architecture:** 3 Blueprint terpisah: `payment_memo`, `payment_application`, `users`. Masing-masing punya `service.py` untuk query dan `routes.py` untuk HTML. Memo number di-generate otomatis format `PAM/{COMPANY_CODE}/{YYYY}/{SEQ:03d}`.

**Tech Stack:** Flask Blueprint, SQLite, reportlab (PDF memo)

**Prerequisite:** Part 1 + Part 2 sudah selesai. Tabel `payment_memo`, `payment_memo_items`, `payment_application`, `users` sudah dibuat oleh `database.py`.

---

## File Structure (Part 3 additions)

```
C:\Financehub\app\
├── modules/
│   ├── payment_memo/
│   │   ├── __init__.py
│   │   ├── service.py          ← generate memo number, list draft, create memo, update status
│   │   └── routes.py           ← /payment-memo, JSON endpoints
│   ├── payment_application/
│   │   ├── __init__.py
│   │   ├── service.py          ← list aplikasi, update actual payment date, hitung TAT
│   │   └── routes.py           ← /payment-application
│   └── users/
│       ├── __init__.py
│       ├── service.py          ← list users, add user, toggle aktif, change role
│       └── routes.py           ← /users (releaser only)
├── templates/
│   ├── payment_memo/
│   │   └── index.html
│   ├── payment_application/
│   │   └── index.html
│   └── users/
│       └── index.html
└── tests/
    ├── test_payment_memo_service.py
    └── test_users_service.py
```

---

## Task 1: payment_memo/service.py

**Files:**
- Create: `C:\Financehub\app\modules\payment_memo\__init__.py`
- Create: `C:\Financehub\app\modules\payment_memo\service.py`
- Test: `C:\Financehub\app\tests\test_payment_memo_service.py`

- [ ] **Step 1: Buat __init__.py**

```bash
type nul > modules\payment_memo\__init__.py
```

- [ ] **Step 2: Tulis tests/test_payment_memo_service.py dulu**

```python
# C:\Financehub\app\tests\test_payment_memo_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import (
    generate_memo_number, get_draft_payments, create_memo, update_memo_status,
    get_memo_list, get_memo_detail
)

COMPANY_ID   = 2  # ETF
COMPANY_CODE = "ETF"

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def _add_draft_payment(siswa_code="1250001", amount=5000000):
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status) "
        "VALUES (?,?,?,?,?,?,?,?,'draft')",
        (COMPANY_ID, siswa_code, "By Pendidikan", "Semester 1", "2025-06-01", amount, "AGRI", "PT. SMART Tbk")
    )
    last_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    return last_id

def test_generate_memo_number_first():
    num = generate_memo_number(COMPANY_ID, COMPANY_CODE, "2025")
    assert num == "PAM/ETF/2025/001"

def test_generate_memo_number_increments():
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
        (COMPANY_ID, "PAM/ETF/2025/001", "draft")
    )
    conn.execute(
        "INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
        (COMPANY_ID, "PAM/ETF/2025/002", "draft")
    )
    conn.commit(); conn.close()
    num = generate_memo_number(COMPANY_ID, COMPANY_CODE, "2025")
    assert num == "PAM/ETF/2025/003"

def test_get_draft_payments_empty():
    rows = get_draft_payments(COMPANY_ID)
    assert rows == []

def test_get_draft_payments_returns_draft_only():
    pay_id = _add_draft_payment()
    rows   = get_draft_payments(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["id"] == pay_id

def test_create_memo_success():
    pay_id = _add_draft_payment()
    result = create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "Memo test",
                         "admin", [{"source_id": pay_id, "source_module": "beasiswa",
                                    "description": "By Pendidikan Sem 1", "amount": 5000000,
                                    "vendor": "Budi", "bank_account": "BCA 1234"}])
    assert result["ok"] is True
    assert "PAM/ETF" in result["memo_number"]

def test_create_memo_updates_payment_status():
    pay_id = _add_draft_payment()
    create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "", "admin",
                [{"source_id": pay_id, "source_module": "beasiswa",
                  "description": "", "amount": 5000000,
                  "vendor": "", "bank_account": ""}])
    conn = get_conn()
    row  = conn.execute("SELECT status FROM payment_beasiswa WHERE id=?", (pay_id,)).fetchone()
    conn.close()
    assert row["status"] == "in_memo"

def test_get_memo_list():
    pay_id = _add_draft_payment()
    create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "", "admin",
                [{"source_id": pay_id, "source_module": "beasiswa",
                  "description": "", "amount": 5000000, "vendor": "", "bank_account": ""}])
    memos = get_memo_list(COMPANY_ID)
    assert len(memos) == 1

def test_update_memo_status_approved():
    pay_id = _add_draft_payment()
    result = create_memo(COMPANY_ID, COMPANY_CODE, "2025-06-10", "", "admin",
                         [{"source_id": pay_id, "source_module": "beasiswa",
                           "description": "", "amount": 5000000, "vendor": "", "bank_account": ""}])
    memo_id = result["memo_id"]
    upd = update_memo_status(memo_id, "approved", "manager")
    assert upd["ok"] is True
    conn = get_conn()
    row  = conn.execute("SELECT status FROM payment_memo WHERE id=?", (memo_id,)).fetchone()
    conn.close()
    assert row["status"] == "approved"
```

- [ ] **Step 3: Jalankan test — pastikan FAIL**

```bash
cd C:\Financehub\app
pytest tests/test_payment_memo_service.py -v
```

Expected: `ERROR — ModuleNotFoundError: No module named 'modules.payment_memo.service'`

- [ ] **Step 4: Tulis modules/payment_memo/service.py**

```python
# C:\Financehub\app\modules\payment_memo\service.py
import re
from datetime import datetime
from database import get_conn


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def generate_memo_number(company_id: int, company_code: str, year: str) -> str:
    """
    Generate nomor memo berikutnya.
    Format: PAM/{COMPANY_CODE}/{YYYY}/{SEQ:03d}
    Contoh: PAM/ETF/2025/001
    """
    prefix  = f"PAM/{company_code}/{year}/"
    pattern = re.compile(rf"PAM/{re.escape(company_code)}/{re.escape(year)}/(\d+)")

    conn = get_conn()
    rows = conn.execute(
        "SELECT memo_number FROM payment_memo WHERE company_id = ? AND memo_number LIKE ?",
        (company_id, prefix + "%")
    ).fetchall()
    conn.close()

    max_seq = 0
    for row in rows:
        m = pattern.match(row["memo_number"])
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq

    return f"{prefix}{max_seq + 1:03d}"


def get_draft_payments(company_id: int) -> list:
    """
    Return semua payment_beasiswa dengan status='draft' untuk company ini.
    Sertakan nama siswa dari tabel siswa.
    """
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pb.*, s.nama, s.bank, s.norek, s.namarek
           FROM payment_beasiswa pb
           LEFT JOIN siswa s ON s.company_id = pb.company_id AND s.code = pb.siswa_code
           WHERE pb.company_id = ? AND pb.status = 'draft'
           ORDER BY pb.tanggal DESC""",
        (company_id,)
    ).fetchall()]
    conn.close()
    return rows


def create_memo(company_id: int, company_code: str, tanggal: str,
                notes: str, created_by: str, items: list) -> dict:
    """
    Buat memo baru dari daftar payment items.
    items: [{"source_id", "source_module", "description", "amount", "vendor", "bank_account"}]
    Update status payment sumber ke 'in_memo'.
    Return {"ok": True, "memo_id": int, "memo_number": str}
    """
    if not items:
        return {"ok": False, "pesan": "Pilih minimal 1 payment untuk dimasukkan ke memo."}

    year       = (tanggal or datetime.now().strftime("%Y"))[:4]
    memo_number = generate_memo_number(company_id, company_code, year)
    total       = sum(float(item.get("amount", 0)) for item in items)

    conn = get_conn()
    cur  = conn.execute(
        """INSERT INTO payment_memo
           (company_id, memo_number, tanggal, total_amount, status, notes, created_by, created_at)
           VALUES (?,?,?,?,?,'draft',?,?)""",
        (company_id, memo_number, tanggal, total, notes, created_by, _ts())
    )
    memo_id = cur.lastrowid

    for item in items:
        conn.execute(
            """INSERT INTO payment_memo_items
               (memo_id, source_module, source_id, description, amount, vendor, bank_account)
               VALUES (?,?,?,?,?,?,?)""",
            (memo_id,
             item.get("source_module", "beasiswa"),
             item["source_id"],
             item.get("description", ""),
             float(item.get("amount", 0)),
             item.get("vendor", ""),
             item.get("bank_account", ""))
        )
        # Update status payment sumber ke 'in_memo'
        if item.get("source_module", "beasiswa") == "beasiswa":
            conn.execute(
                "UPDATE payment_beasiswa SET status='in_memo', memo_id=? WHERE id=?",
                (memo_id, item["source_id"])
            )

    conn.commit()
    conn.close()
    return {"ok": True, "memo_id": memo_id, "memo_number": memo_number,
            "pesan": f"Memo {memo_number} berhasil dibuat."}


def get_memo_list(company_id: int, status: str = "") -> list:
    """Return list memo per company, opsional filter status."""
    sql    = "SELECT * FROM payment_memo WHERE company_id = ?"
    params = [company_id]
    if status:
        sql    += " AND status = ?"
        params += [status]
    sql += " ORDER BY created_at DESC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def get_memo_detail(memo_id: int, company_id: int) -> dict | None:
    """Return memo header + items. None jika tidak ditemukan atau beda company."""
    conn = get_conn()
    memo = conn.execute(
        "SELECT * FROM payment_memo WHERE id = ? AND company_id = ?",
        (memo_id, company_id)
    ).fetchone()
    if not memo:
        conn.close()
        return None

    items = [dict(r) for r in conn.execute(
        "SELECT * FROM payment_memo_items WHERE memo_id = ?", (memo_id,)
    ).fetchall()]
    conn.close()
    return {**dict(memo), "items": items}


def update_memo_status(memo_id: int, new_status: str, by_user: str) -> dict:
    """
    Update status memo. Status yang diizinkan: draft → submitted → approved → paid.
    Jika paid: update semua payment_beasiswa items ke status='paid'.
    """
    allowed = {"draft", "submitted", "approved", "paid"}
    if new_status not in allowed:
        return {"ok": False, "pesan": f"Status '{new_status}' tidak valid."}

    conn = get_conn()
    now  = _ts()

    if new_status == "approved":
        conn.execute(
            "UPDATE payment_memo SET status=?, approved_by=?, approved_at=?, updated_at=? WHERE id=?",
            (new_status, by_user, now, now, memo_id)
        )
    elif new_status == "paid":
        conn.execute(
            "UPDATE payment_memo SET status=?, updated_at=? WHERE id=?",
            (new_status, now, memo_id)
        )
        # Update semua payment sources ke 'paid'
        items = conn.execute(
            "SELECT source_id, source_module FROM payment_memo_items WHERE memo_id=?",
            (memo_id,)
        ).fetchall()
        for item in items:
            if item["source_module"] == "beasiswa":
                conn.execute(
                    "UPDATE payment_beasiswa SET status='paid' WHERE id=?",
                    (item["source_id"],)
                )
    else:
        conn.execute(
            "UPDATE payment_memo SET status=?, updated_at=? WHERE id=?",
            (new_status, now, memo_id)
        )

    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Status memo diubah ke '{new_status}'."}


def export_memo_pdf(memo_id: int, company_id: int, company_name: str) -> bytes:
    """Generate PDF memo. Return bytes PDF."""
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    memo = get_memo_detail(memo_id, company_id)
    if not memo:
        raise ValueError("Memo tidak ditemukan.")

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles   = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph(company_name.upper(), styles["Title"]))
    elements.append(Paragraph("PAYMENT APPROVAL MEMO", styles["Heading2"]))
    elements.append(Spacer(1, 0.3*cm))

    # Memo info
    info = [
        ["Nomor Memo:", memo["memo_number"]],
        ["Tanggal:",    memo["tanggal"] or ""],
        ["Status:",     memo["status"].upper()],
        ["Dibuat oleh:", memo["created_by"] or ""],
    ]
    if memo.get("approved_by"):
        info.append(["Disetujui oleh:", memo["approved_by"]])
    info_tbl = Table(info, colWidths=[4*cm, 12*cm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(info_tbl)
    elements.append(Spacer(1, 0.5*cm))

    if memo.get("notes"):
        elements.append(Paragraph(f"Keterangan: {memo['notes']}", styles["Normal"]))
        elements.append(Spacer(1, 0.3*cm))

    # Items table
    header = [["No", "Penerima / Keterangan", "Vendor", "Rekening", "Amount (Rp)"]]
    rows   = header
    total  = 0
    for i, item in enumerate(memo["items"], 1):
        rows.append([
            i,
            item.get("description", ""),
            item.get("vendor", ""),
            item.get("bank_account", ""),
            f"{item['amount']:,.0f}",
        ])
        total += item["amount"]
    rows.append(["", "", "", "TOTAL", f"{total:,.0f}"])

    col_widths = [1*cm, 6*cm, 4*cm, 4*cm, 3*cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ALIGN",       (4,0), (4,-1), "RIGHT"),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
        ("BACKGROUND",  (0,-1), (-1,-1), colors.HexColor("#f3f4f6")),
        ("FONTNAME",    (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 1.5*cm))

    # Tanda tangan
    ttd = [["Dibuat oleh", "", "Disetujui oleh", "", "Diketahui oleh"],
           ["", "", "", "", ""],
           ["", "", "", "", ""],
           ["", "", "", "", ""],
           ["(________________)", "", "(________________)", "", "(_______________)"],
           ["Finance Staff", "", "Finance Manager", "", "Direktur"]]
    ttd_tbl = Table(ttd, colWidths=[3.5*cm, 0.5*cm, 3.5*cm, 0.5*cm, 3.5*cm])
    ttd_tbl.setStyle(TableStyle([
        ("FONTSIZE",  (0,0), (-1,-1), 8),
        ("ALIGN",     (0,0), (-1,-1), "CENTER"),
        ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",  (0,-1), (-1,-1), "Helvetica"),
    ]))
    elements.append(ttd_tbl)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
```

- [ ] **Step 5: Jalankan test — pastikan PASS**

```bash
cd C:\Financehub\app
pytest tests/test_payment_memo_service.py -v
```

Expected: semua test PASS (9+ tests).

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/ app/tests/test_payment_memo_service.py
git commit -m "feat: payment_memo service — generate memo, create, list, update status, PDF export"
```

---

## Task 2: payment_memo/routes.py + Template

**Files:**
- Create: `C:\Financehub\app\modules\payment_memo\routes.py`
- Create: `C:\Financehub\app\templates\payment_memo\index.html`

- [ ] **Step 1: Buat folder templates/payment_memo/**

```bash
mkdir templates\payment_memo
```

- [ ] **Step 2: Tulis modules/payment_memo/routes.py**

```python
# C:\Financehub\app\modules\payment_memo\routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.payment_memo.service import (
    get_draft_payments, create_memo, get_memo_list, get_memo_detail,
    update_memo_status, export_memo_pdf
)
import io

bp = Blueprint("payment_memo", __name__, url_prefix="/payment-memo")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    memos  = get_memo_list(session["company_id"])
    drafts = get_draft_payments(session["company_id"])
    return render_template(
        "payment_memo/index.html",
        memos=memos,
        drafts=drafts,
        active_page="payment_memo",
        **_ctx()
    )


# ── JSON API endpoints ────────────────────────────────────────────────

@bp.route("/drafts")
@role_required("requester", "verificator", "releaser")
def list_drafts():
    rows = get_draft_payments(session.get("company_id"))
    return jsonify({"ok": True, "rows": rows})


@bp.route("/create", methods=["POST"])
@role_required("verificator")
def create():
    data       = request.get_json(force=True)
    company_id = session.get("company_id")
    company_code = session.get("company_code", "")
    tanggal    = data.get("tanggal", "")
    notes      = data.get("notes", "")
    items      = data.get("items", [])
    claims     = get_jwt()
    username   = claims.get("username", "")

    if not items:
        return jsonify({"ok": False, "pesan": "Pilih minimal 1 payment."})

    result = create_memo(company_id, company_code, tanggal, notes, username, items)
    return jsonify(result)


@bp.route("/<int:memo_id>")
@role_required("requester", "verificator", "releaser")
def memo_detail_api(memo_id):
    memo = get_memo_detail(memo_id, session.get("company_id"))
    if not memo:
        return jsonify({"ok": False, "pesan": "Memo tidak ditemukan."}), 404
    return jsonify({"ok": True, "data": memo})


@bp.route("/<int:memo_id>/status", methods=["POST"])
@role_required("verificator", "releaser")
def update_status(memo_id):
    data       = request.get_json(force=True)
    new_status = data.get("status", "")
    claims     = get_jwt()
    username   = claims.get("username", "")

    # Role enforcement: hanya releaser yang bisa set 'paid'
    if new_status == "paid":
        if claims.get("role") != "releaser":
            return jsonify({"ok": False, "pesan": "Hanya Releaser yang dapat mark as Paid."}), 403

    result = update_memo_status(memo_id, new_status, username)
    return jsonify(result)


@bp.route("/<int:memo_id>/export/pdf")
@role_required("verificator", "releaser")
def export_pdf(memo_id):
    company_id   = session.get("company_id")
    company_name = session.get("company_name", "")
    try:
        pdf_bytes = export_memo_pdf(memo_id, company_id, company_name)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            download_name=f"memo_{memo_id}.pdf",
            as_attachment=True
        )
    except ValueError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 404
```

- [ ] **Step 3: Tulis templates/payment_memo/index.html**

```html
<!-- C:\Financehub\app\templates\payment_memo\index.html -->
{% extends "base.html" %}
{% block title %}Payment Approval Memo{% endblock %}

{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem">
  <h1 style="font-size:1.25rem; font-weight:700">📋 Payment Approval Memo — {{ company_name }}</h1>
  {% if current_role == 'verificator' %}
  <button class="btn btn-primary" onclick="openModal('modal-buat-memo')">+ Buat Memo Baru</button>
  {% endif %}
</div>

<div data-tabs>
  <div class="tabs">
    <button class="tab-btn" data-tab="tab-memo-list">Daftar Memo</button>
    <button class="tab-btn" data-tab="tab-draft-pay">Draft Payment ({{ drafts|length }})</button>
  </div>

  <!-- ══════════════════════════════════════════════════ TAB DAFTAR MEMO -->
  <div class="tab-panel" id="tab-memo-list">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nomor Memo</th><th>Tanggal</th><th>Total</th>
            <th>Status</th><th>Dibuat oleh</th><th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          {% for m in memos %}
          <tr>
            <td><strong>{{ m.memo_number }}</strong></td>
            <td>{{ m.tanggal }}</td>
            <td class="num-right">Rp {{ "{:,.0f}".format(m.total_amount) }}</td>
            <td>
              <span class="badge
                {% if m.status == 'draft' %}badge-gray
                {% elif m.status == 'submitted' %}badge-yellow
                {% elif m.status == 'approved' %}badge-blue
                {% elif m.status == 'paid' %}badge-green
                {% endif %}">
                {{ m.status }}
              </span>
            </td>
            <td>{{ m.created_by }}</td>
            <td style="display:flex; gap:.4rem; flex-wrap:wrap">
              <button class="btn btn-secondary btn-sm" onclick="showMemoDetail({{ m.id }})">Detail</button>
              {% if current_role in ['verificator', 'releaser'] %}
              <a href="/payment-memo/{{ m.id }}/export/pdf" class="btn btn-secondary btn-sm">PDF</a>
              {% endif %}
              {% if current_role == 'verificator' and m.status == 'draft' %}
              <button class="btn btn-primary btn-sm" onclick="changeStatus({{ m.id }}, 'submitted')">Submit</button>
              {% endif %}
              {% if current_role == 'verificator' and m.status == 'submitted' %}
              <button class="btn btn-success btn-sm" onclick="changeStatus({{ m.id }}, 'approved')">Approve</button>
              {% endif %}
              {% if current_role == 'releaser' and m.status == 'approved' %}
              <button class="btn btn-success btn-sm" onclick="changeStatus({{ m.id }}, 'paid')">Mark Paid</button>
              {% endif %}
            </td>
          </tr>
          {% else %}
          <tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:2rem">
            Belum ada memo. Buat memo baru dari tab "Draft Payment".
          </td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════════ TAB DRAFT PAYMENT -->
  <div class="tab-panel" id="tab-draft-pay">
    {% if current_role == 'verificator' %}
    <div style="margin-bottom:1rem; display:flex; align-items:center; gap:1rem">
      <span style="font-size:.875rem; color:var(--text-muted)">Pilih payment untuk dimasukkan ke memo baru.</span>
      <button class="btn btn-primary btn-sm" onclick="openBuatMemoFromSelected()">Buat Memo dari Pilihan</button>
    </div>
    {% endif %}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            {% if current_role == 'verificator' %}<th><input type="checkbox" id="select-all-drafts" onchange="toggleAllDrafts(this)"></th>{% endif %}
            <th>Code</th><th>Nama Siswa</th><th>Kategori</th><th>Tanggal</th>
            <th>Perusahaan</th><th class="num-right">Amount</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {% for d in drafts %}
          <tr>
            {% if current_role == 'verificator' %}
            <td><input type="checkbox" class="draft-check" data-id="{{ d.id }}"
                data-desc="{{ d.cat1 }} / {{ d.cat2 }} — {{ d.siswa_code }}"
                data-amount="{{ d.amount }}"
                data-vendor="{{ d.namarek or d.nama or '' }}"
                data-bank="{{ (d.bank or '') + ' ' + (d.norek or '') }}"></td>
            {% endif %}
            <td><code>{{ d.siswa_code }}</code></td>
            <td>{{ d.nama or '—' }}</td>
            <td>{{ d.cat1 }} / {{ d.cat2 }}</td>
            <td>{{ d.tanggal }}</td>
            <td>{{ d.perusahaan }}</td>
            <td class="num-right">Rp {{ "{:,.0f}".format(d.amount) }}</td>
            <td><span class="badge badge-gray">{{ d.status }}</span></td>
          </tr>
          {% else %}
          <tr {% if loop.first %} {% endif %}><td colspan="{% if current_role == 'verificator' %}8{% else %}7{% endif %}"
              style="text-align:center; color:var(--text-muted); padding:2rem">
            Tidak ada payment draft.
          </td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ MODAL: Buat Memo -->
<div class="modal-overlay" id="modal-buat-memo">
  <div class="modal" style="width:min(640px,95vw)">
    <div class="modal-header">
      <span class="modal-title">Buat Memo Baru</span>
      <button class="modal-close" onclick="closeModal('modal-buat-memo')">✕</button>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem; margin-bottom:.75rem">
      <div class="form-group">
        <label>Tanggal Memo</label>
        <input type="date" id="memo-tgl">
      </div>
      <div class="form-group">
        <label>Catatan</label>
        <input type="text" id="memo-notes" placeholder="Keterangan memo (opsional)">
      </div>
    </div>
    <div class="card" style="padding:.75rem; margin-bottom:.75rem; background:#f8fafc">
      <strong style="font-size:.8rem">Items yang dipilih:</strong>
      <div id="memo-items-preview" style="margin-top:.5rem; font-size:.8rem; color:var(--text-muted)">
        (pilih dari tab Draft Payment terlebih dahulu)
      </div>
      <div style="margin-top:.5rem; font-weight:700" id="memo-total-preview"></div>
    </div>
    <div style="display:flex; gap:.75rem; justify-content:flex-end">
      <button class="btn btn-secondary" onclick="closeModal('modal-buat-memo')">Batal</button>
      <button class="btn btn-primary" onclick="submitMemo()">💾 Buat Memo</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════ MODAL: Detail Memo -->
<div class="modal-overlay" id="modal-memo-detail">
  <div class="modal" style="width:min(700px,95vw)">
    <div class="modal-header">
      <span class="modal-title" id="memo-detail-title">Detail Memo</span>
      <button class="modal-close" onclick="closeModal('modal-memo-detail')">✕</button>
    </div>
    <div id="memo-detail-body">Loading...</div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let _selectedDrafts = [];

function toggleAllDrafts(cb) {
  document.querySelectorAll(".draft-check").forEach(c => { c.checked = cb.checked; });
}

function openBuatMemoFromSelected() {
  _selectedDrafts = [];
  document.querySelectorAll(".draft-check:checked").forEach(cb => {
    _selectedDrafts.push({
      source_id:     parseInt(cb.dataset.id),
      source_module: "beasiswa",
      description:   cb.dataset.desc,
      amount:        parseFloat(cb.dataset.amount),
      vendor:        cb.dataset.vendor,
      bank_account:  cb.dataset.bank,
    });
  });
  if (_selectedDrafts.length === 0) {
    showToast("Pilih minimal 1 payment terlebih dahulu.", "error"); return;
  }
  const total = _selectedDrafts.reduce((s,i) => s+i.amount, 0);
  document.getElementById("memo-items-preview").innerHTML =
    _selectedDrafts.map(i => `<div>• ${i.description} — Rp ${fmtRupiah(i.amount)}</div>`).join("");
  document.getElementById("memo-total-preview").textContent =
    `Total: Rp ${fmtRupiah(total)}`;
  openModal("modal-buat-memo");
}

async function submitMemo() {
  const tanggal = document.getElementById("memo-tgl").value;
  const notes   = document.getElementById("memo-notes").value;
  if (!tanggal) { showToast("Tanggal memo wajib diisi.", "error"); return; }
  if (_selectedDrafts.length === 0) { showToast("Pilih minimal 1 payment.", "error"); return; }

  const resp = await apiFetch("/payment-memo/create", {
    method: "POST",
    body: JSON.stringify({ tanggal, notes, items: _selectedDrafts })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) {
    closeModal("modal-buat-memo");
    setTimeout(() => location.reload(), 1000);
  }
}

async function changeStatus(memoId, newStatus) {
  const label = { submitted: "Submit", approved: "Approve", paid: "Mark as Paid" }[newStatus] || newStatus;
  if (!confirm(`${label} memo ini?`)) return;
  const resp = await apiFetch(`/payment-memo/${memoId}/status`, {
    method: "POST", body: JSON.stringify({ status: newStatus })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) setTimeout(() => location.reload(), 800);
}

async function showMemoDetail(memoId) {
  const resp = await apiFetch(`/payment-memo/${memoId}`);
  const data = await resp.json();
  if (!data.ok) { showToast("Gagal load detail.", "error"); return; }
  const m = data.data;
  document.getElementById("memo-detail-title").textContent = m.memo_number;
  document.getElementById("memo-detail-body").innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.5rem; margin-bottom:1rem; font-size:.875rem">
      <div><strong>Tanggal:</strong> ${m.tanggal || '—'}</div>
      <div><strong>Status:</strong> <span class="badge badge-${m.status==='paid'?'green':m.status==='approved'?'blue':m.status==='submitted'?'yellow':'gray'}">${m.status}</span></div>
      <div><strong>Dibuat oleh:</strong> ${m.created_by || '—'}</div>
      <div><strong>Disetujui oleh:</strong> ${m.approved_by || '—'}</div>
      <div><strong>Catatan:</strong> ${m.notes || '—'}</div>
      <div><strong>Total:</strong> Rp ${fmtRupiah(m.total_amount)}</div>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>No</th><th>Keterangan</th><th>Vendor</th><th>Rekening</th><th class="num-right">Amount</th></tr></thead>
        <tbody>
          ${m.items.map((item, i) => `<tr>
            <td>${i+1}</td>
            <td>${item.description || '—'}</td>
            <td>${item.vendor || '—'}</td>
            <td>${item.bank_account || '—'}</td>
            <td class="num-right">Rp ${fmtRupiah(item.amount)}</td>
          </tr>`).join("")}
        </tbody>
        <tfoot><tr><td colspan="4"><strong>Total</strong></td>
          <td class="num-right"><strong>Rp ${fmtRupiah(m.total_amount)}</strong></td></tr></tfoot>
      </table>
    </div>`;
  openModal("modal-memo-detail");
}
</script>
{% endblock %}
```

- [ ] **Step 4: Update app.py — register payment_memo blueprint**

Tambahkan di `create_app()`:

```python
    from modules.payment_memo.routes import bp as memo_bp
    app.register_blueprint(memo_bp)
```

- [ ] **Step 5: Test manual**

```bash
python app.py
```

Buka `http://localhost:8080/payment-memo`:
- Harus tampil 2 tab: Daftar Memo dan Draft Payment
- Login sebagai requester → tab Draft Payment ada, tombol "Buat Memo" tidak ada
- Login sebagai verificator → ada tombol "Buat Memo Baru" dan checkbox di Draft Payment

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_memo/routes.py app/templates/payment_memo/ app/app.py
git commit -m "feat: payment_memo routes + template — list, buat memo, update status, PDF"
```

---

## Task 3: payment_application/service.py + routes.py + Template

**Files:**
- Create: `C:\Financehub\app\modules\payment_application\__init__.py`
- Create: `C:\Financehub\app\modules\payment_application\service.py`
- Create: `C:\Financehub\app\modules\payment_application\routes.py`
- Create: `C:\Financehub\app\templates\payment_application\index.html`

- [ ] **Step 1: Buat folder + __init__.py**

```bash
mkdir modules\payment_application
type nul > modules\payment_application\__init__.py
mkdir templates\payment_application
```

- [ ] **Step 2: Tulis modules/payment_application/service.py**

```python
# C:\Financehub\app\modules\payment_application\service.py
from datetime import datetime
from database import get_conn


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def get_applications(company_id: int) -> list:
    """
    Return daftar payment application + info memo + TAT calculation.
    """
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT pa.*, pm.memo_number, pm.total_amount, pm.status as memo_status
           FROM payment_application pa
           JOIN payment_memo pm ON pm.id = pa.memo_id
           WHERE pa.company_id = ?
           ORDER BY pa.created_at DESC""",
        (company_id,)
    ).fetchall()]
    conn.close()

    # Hitung TAT hari kerja
    for r in rows:
        if r.get("submitted_at") and r.get("actual_payment_date"):
            r["tat_days"] = _workday_diff(r["submitted_at"][:10], r["actual_payment_date"][:10])
        else:
            r["tat_days"] = None
    return rows


def _workday_diff(start: str, end: str) -> int:
    """Hitung jumlah hari kerja antara dua tanggal (Senin-Jumat)."""
    from datetime import date, timedelta
    d1 = date.fromisoformat(start)
    d2 = date.fromisoformat(end)
    if d2 < d1:
        return 0
    count = 0
    current = d1
    while current <= d2:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count - 1  # Tidak hitung hari mulai


def create_application(company_id: int, memo_id: int, tanggal_pengajuan: str,
                        target_payment_date: str, notes: str) -> dict:
    """Buat payment application dari memo yang sudah approved."""
    conn = get_conn()
    # Cek memo valid + approved
    memo = conn.execute(
        "SELECT id, status FROM payment_memo WHERE id=? AND company_id=?",
        (memo_id, company_id)
    ).fetchone()
    if not memo:
        conn.close()
        return {"ok": False, "pesan": "Memo tidak ditemukan."}
    if memo["status"] not in ("approved", "paid"):
        conn.close()
        return {"ok": False, "pesan": "Memo harus berstatus 'approved' sebelum diajukan."}

    # Generate application number
    year  = (tanggal_pengajuan or datetime.now().strftime("%Y"))[:4]
    count = conn.execute(
        "SELECT COUNT(*) FROM payment_application WHERE company_id=?", (company_id,)
    ).fetchone()[0]
    app_number = f"APP/{company_id}/{year}/{count+1:04d}"

    cur = conn.execute(
        """INSERT INTO payment_application
           (company_id, memo_id, application_number, submitted_at, target_payment_date, notes, status, created_at)
           VALUES (?,?,?,?,?,?,'pending',?)""",
        (company_id, memo_id, app_number, tanggal_pengajuan, target_payment_date, notes, _ts())
    )
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "application_id": app_id, "application_number": app_number,
            "pesan": f"Payment application {app_number} berhasil dibuat."}


def update_actual_payment(app_id: int, actual_date: str) -> dict:
    """Releaser update tanggal actual payment — otomatis hitung TAT."""
    conn = get_conn()
    row  = conn.execute(
        "SELECT submitted_at FROM payment_application WHERE id=?", (app_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "pesan": "Application tidak ditemukan."}

    tat = None
    if row["submitted_at"]:
        tat = _workday_diff(row["submitted_at"][:10], actual_date)

    conn.execute(
        "UPDATE payment_application SET actual_payment_date=?, tat_days=?, status='completed', updated_at=? WHERE id=?",
        (actual_date, tat, _ts(), app_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Tanggal pembayaran aktual disimpan. TAT: {tat} hari kerja."}
```

- [ ] **Step 3: Tulis modules/payment_application/routes.py**

```python
# C:\Financehub\app\modules\payment_application\routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, role_required
from modules.payment_application.service import (
    get_applications, create_application, update_actual_payment
)
from modules.payment_memo.service import get_memo_list

bp = Blueprint("payment_application", __name__, url_prefix="/payment-application")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id   = session["company_id"]
    applications = get_applications(company_id)
    # Approved memos yang belum diajukan
    approved_memos = [m for m in get_memo_list(company_id, status="approved")
                      if not any(a["memo_id"] == m["id"] for a in applications)]
    return render_template(
        "payment_application/index.html",
        applications=applications,
        approved_memos=approved_memos,
        active_page="payment_app",
        **_ctx()
    )


@bp.route("/create", methods=["POST"])
@role_required("releaser")
def create():
    data       = request.get_json(force=True)
    company_id = session.get("company_id")
    result = create_application(
        company_id,
        int(data.get("memo_id", 0)),
        data.get("submitted_at", ""),
        data.get("target_payment_date", ""),
        data.get("notes", ""),
    )
    return jsonify(result)


@bp.route("/<int:app_id>/update-payment", methods=["POST"])
@role_required("releaser")
def update_payment(app_id):
    data        = request.get_json(force=True)
    actual_date = data.get("actual_payment_date", "")
    if not actual_date:
        return jsonify({"ok": False, "pesan": "Tanggal aktual wajib diisi."})
    result = update_actual_payment(app_id, actual_date)
    return jsonify(result)
```

- [ ] **Step 4: Tulis templates/payment_application/index.html**

```html
<!-- C:\Financehub\app\templates\payment_application\index.html -->
{% extends "base.html" %}
{% block title %}Payment Application{% endblock %}

{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem">
  <h1 style="font-size:1.25rem; font-weight:700">📊 Payment Application — {{ company_name }}</h1>
  {% if current_role == 'releaser' and approved_memos %}
  <button class="btn btn-primary" onclick="openModal('modal-buat-app')">+ Buat Application</button>
  {% endif %}
</div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>No. Application</th><th>Memo</th><th>Tgl Pengajuan</th>
        <th>Target Bayar</th><th>Aktual Bayar</th>
        <th class="num-right">Total</th><th>TAT (hari kerja)</th>
        <th>Status</th><th>Aksi</th>
      </tr>
    </thead>
    <tbody>
      {% for a in applications %}
      <tr>
        <td><code>{{ a.application_number }}</code></td>
        <td>{{ a.memo_number }}</td>
        <td>{{ a.submitted_at or '—' }}</td>
        <td>{{ a.target_payment_date or '—' }}</td>
        <td>{{ a.actual_payment_date or '—' }}</td>
        <td class="num-right">Rp {{ "{:,.0f}".format(a.total_amount) }}</td>
        <td style="text-align:center">
          {% if a.tat_days is not none %}
          <span class="badge {% if a.tat_days <= 5 %}badge-green{% elif a.tat_days <= 8 %}badge-yellow{% else %}badge-red{% endif %}">
            {{ a.tat_days }} hr
          </span>
          {% else %}—{% endif %}
        </td>
        <td>
          <span class="badge {% if a.status == 'completed' %}badge-green{% elif a.status == 'pending' %}badge-yellow{% else %}badge-gray{% endif %}">
            {{ a.status }}
          </span>
        </td>
        <td>
          {% if current_role == 'releaser' and not a.actual_payment_date %}
          <button class="btn btn-primary btn-sm" onclick="openUpdatePayment({{ a.id }}, '{{ a.application_number }}')">
            Update Tanggal
          </button>
          {% endif %}
        </td>
      </tr>
      {% else %}
      <tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding:2rem">
        Belum ada payment application.
      </td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- MODAL: Buat Application -->
<div class="modal-overlay" id="modal-buat-app">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">Buat Payment Application</span>
      <button class="modal-close" onclick="closeModal('modal-buat-app')">✕</button>
    </div>
    <div class="form-group">
      <label>Pilih Memo (status: approved)</label>
      <select id="app-memo-id">
        {% for m in approved_memos %}
        <option value="{{ m.id }}">{{ m.memo_number }} — Rp {{ "{:,.0f}".format(m.total_amount) }}</option>
        {% endfor %}
      </select>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.75rem">
      <div class="form-group">
        <label>Tanggal Pengajuan</label>
        <input type="date" id="app-submitted-at">
      </div>
      <div class="form-group">
        <label>Target Tanggal Bayar</label>
        <input type="date" id="app-target-date">
      </div>
    </div>
    <div class="form-group">
      <label>Catatan</label>
      <input type="text" id="app-notes" placeholder="Catatan (opsional)">
    </div>
    <div style="display:flex; gap:.75rem; justify-content:flex-end; margin-top:.75rem">
      <button class="btn btn-secondary" onclick="closeModal('modal-buat-app')">Batal</button>
      <button class="btn btn-primary" onclick="createApp()">💾 Buat Application</button>
    </div>
  </div>
</div>

<!-- MODAL: Update Aktual Payment -->
<div class="modal-overlay" id="modal-update-payment">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">Update Tanggal Pembayaran Aktual</span>
      <button class="modal-close" onclick="closeModal('modal-update-payment')">✕</button>
    </div>
    <p style="font-size:.875rem; margin-bottom:1rem" id="update-pay-label"></p>
    <div class="form-group">
      <label>Tanggal Aktual Pembayaran</label>
      <input type="date" id="actual-pay-date">
    </div>
    <div style="display:flex; gap:.75rem; justify-content:flex-end">
      <button class="btn btn-secondary" onclick="closeModal('modal-update-payment')">Batal</button>
      <button class="btn btn-primary" id="btn-save-actual" onclick="saveActualPayment()">💾 Simpan</button>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let _currentAppId = null;

async function createApp() {
  const memo_id             = document.getElementById("app-memo-id").value;
  const submitted_at        = document.getElementById("app-submitted-at").value;
  const target_payment_date = document.getElementById("app-target-date").value;
  const notes               = document.getElementById("app-notes").value;
  if (!memo_id || !submitted_at) {
    showToast("Pilih memo dan isi tanggal pengajuan.", "error"); return;
  }
  const resp = await apiFetch("/payment-application/create", {
    method: "POST",
    body: JSON.stringify({ memo_id: parseInt(memo_id), submitted_at, target_payment_date, notes })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-buat-app"); setTimeout(() => location.reload(), 800); }
}

function openUpdatePayment(appId, label) {
  _currentAppId = appId;
  document.getElementById("update-pay-label").textContent = `Application: ${label}`;
  document.getElementById("actual-pay-date").value = "";
  openModal("modal-update-payment");
}

async function saveActualPayment() {
  const actual = document.getElementById("actual-pay-date").value;
  if (!actual) { showToast("Tanggal aktual wajib diisi.", "error"); return; }
  const resp = await apiFetch(`/payment-application/${_currentAppId}/update-payment`, {
    method: "POST", body: JSON.stringify({ actual_payment_date: actual })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-update-payment"); setTimeout(() => location.reload(), 800); }
}
</script>
{% endblock %}
```

- [ ] **Step 5: Update app.py — register payment_application blueprint**

Tambahkan di `create_app()`:

```python
    from modules.payment_application.routes import bp as payapp_bp
    app.register_blueprint(payapp_bp)
```

- [ ] **Step 6: Commit**

```bash
git add app/modules/payment_application/ app/templates/payment_application/ app/app.py
git commit -m "feat: payment_application — monitoring, TAT tracking, update actual payment date"
```

---

## Task 4: User Management (Releaser only)

**Files:**
- Create: `C:\Financehub\app\modules\users\__init__.py`
- Create: `C:\Financehub\app\modules\users\service.py`
- Create: `C:\Financehub\app\modules\users\routes.py`
- Create: `C:\Financehub\app\templates\users\index.html`
- Test: `C:\Financehub\app\tests\test_users_service.py`

- [ ] **Step 1: Buat folder + __init__.py**

```bash
mkdir modules\users
type nul > modules\users\__init__.py
mkdir templates\users
```

- [ ] **Step 2: Tulis tests/test_users_service.py**

```python
# C:\Financehub\app\tests\test_users_service.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db
from modules.users.service import get_users, add_user, toggle_user_active, change_user_role

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

def test_get_users_returns_admin():
    users = get_users()
    assert any(u["username"] == "admin" for u in users)

def test_add_user_success():
    result = add_user("staff01", "Pass@word1", "requester")
    assert result["ok"] is True

def test_add_user_duplicate_username():
    add_user("staff01", "Pass@word1", "requester")
    result = add_user("staff01", "Pass@word2", "verificator")
    assert result["ok"] is False
    assert "sudah ada" in result["pesan"]

def test_add_user_invalid_role():
    result = add_user("staff02", "Pass@word1", "superadmin")
    assert result["ok"] is False

def test_add_user_short_password():
    result = add_user("staff03", "short", "requester")
    assert result["ok"] is False
    assert "8" in result["pesan"]

def test_toggle_user_active():
    add_user("staff01", "Pass@word1", "requester")
    result = toggle_user_active("staff01", False)
    assert result["ok"] is True
    users  = get_users()
    staff  = next(u for u in users if u["username"] == "staff01")
    assert staff["is_active"] == 0

def test_change_user_role():
    add_user("staff01", "Pass@word1", "requester")
    result = change_user_role("staff01", "verificator")
    assert result["ok"] is True
    users  = get_users()
    staff  = next(u for u in users if u["username"] == "staff01")
    assert staff["role"] == "verificator"

def test_cannot_change_admin_role():
    result = change_user_role("admin", "requester")
    assert result["ok"] is False
```

- [ ] **Step 3: Tulis modules/users/service.py**

```python
# C:\Financehub\app\modules\users\service.py
import bcrypt
from database import get_conn


VALID_ROLES = {"requester", "verificator", "releaser"}


def get_users() -> list:
    """Return semua user (tanpa password_hash)."""
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, username, role, is_active, must_change_pw, created_at, last_login FROM users ORDER BY created_at"
    ).fetchall()]
    conn.close()
    return rows


def add_user(username: str, password: str, role: str) -> dict:
    """Tambah user baru. Password di-hash dengan bcrypt."""
    username = username.strip()
    if not username:
        return {"ok": False, "pesan": "Username wajib diisi."}
    if len(password) < 8:
        return {"ok": False, "pesan": "Password minimal 8 karakter."}
    if role not in VALID_ROLES:
        return {"ok": False, "pesan": f"Role tidak valid. Pilihan: {', '.join(VALID_ROLES)}"}

    conn     = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "pesan": f"Username '{username}' sudah ada."}

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
    conn.execute(
        "INSERT INTO users (username, password_hash, role, must_change_pw) VALUES (?,?,?,1)",
        (username, pw_hash, role)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"User '{username}' berhasil ditambahkan (role: {role})."}


def toggle_user_active(username: str, is_active: bool) -> dict:
    """Aktifkan atau nonaktifkan user. Admin tidak bisa dinonaktifkan."""
    if username == "admin":
        return {"ok": False, "pesan": "User 'admin' tidak dapat dinonaktifkan."}
    conn = get_conn()
    conn.execute("UPDATE users SET is_active=? WHERE username=?", (int(is_active), username))
    conn.commit()
    conn.close()
    status = "diaktifkan" if is_active else "dinonaktifkan"
    return {"ok": True, "pesan": f"User '{username}' berhasil {status}."}


def change_user_role(username: str, new_role: str) -> dict:
    """Ganti role user. Admin tidak bisa diganti rolenya."""
    if username == "admin":
        return {"ok": False, "pesan": "Role user 'admin' tidak dapat diubah."}
    if new_role not in VALID_ROLES:
        return {"ok": False, "pesan": f"Role tidak valid."}
    conn = get_conn()
    conn.execute("UPDATE users SET role=? WHERE username=?", (new_role, username))
    conn.commit()
    conn.close()
    return {"ok": True, "pesan": f"Role '{username}' berhasil diubah ke '{new_role}'."}
```

- [ ] **Step 4: Jalankan test users**

```bash
cd C:\Financehub\app
pytest tests/test_users_service.py -v
```

Expected: semua test PASS (8 tests).

- [ ] **Step 5: Tulis modules/users/routes.py**

```python
# C:\Financehub\app\modules\users\routes.py
from flask import Blueprint, render_template, request, jsonify, session
from flask_jwt_extended import get_jwt
from auth.middleware import jwt_html_required, html_role_required, role_required
from modules.users.service import get_users, add_user, toggle_user_active, change_user_role

bp = Blueprint("users", __name__, url_prefix="/users")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


@bp.route("/")
@html_role_required("releaser")
def index():
    return render_template("users/index.html", users=get_users(),
                           active_page="users", **_ctx())


@bp.route("/add", methods=["POST"])
@role_required("releaser")
def add():
    data   = request.get_json(force=True)
    result = add_user(data.get("username", ""), data.get("password", ""), data.get("role", ""))
    return jsonify(result)


@bp.route("/<username>/toggle", methods=["POST"])
@role_required("releaser")
def toggle(username):
    data      = request.get_json(force=True)
    is_active = bool(data.get("is_active", True))
    result    = toggle_user_active(username, is_active)
    return jsonify(result)


@bp.route("/<username>/role", methods=["POST"])
@role_required("releaser")
def change_role(username):
    data   = request.get_json(force=True)
    result = change_user_role(username, data.get("role", ""))
    return jsonify(result)
```

- [ ] **Step 6: Tulis templates/users/index.html**

```html
<!-- C:\Financehub\app\templates\users\index.html -->
{% extends "base.html" %}
{% block title %}User Management{% endblock %}

{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem">
  <h1 style="font-size:1.25rem; font-weight:700">👥 User Management</h1>
  <button class="btn btn-primary" onclick="openModal('modal-add-user')">+ Tambah User</button>
</div>

<div class="table-wrap">
  <table>
    <thead>
      <tr><th>Username</th><th>Role</th><th>Status</th><th>Terakhir Login</th><th>Dibuat</th><th>Aksi</th></tr>
    </thead>
    <tbody>
      {% for u in users %}
      <tr>
        <td><strong>{{ u.username }}</strong></td>
        <td>
          {% if u.username != 'admin' %}
          <select class="role-select" data-username="{{ u.username }}"
            style="padding:.2rem .4rem; font-size:.8rem; border-radius:4px"
            onchange="changeRole('{{ u.username }}', this.value)">
            {% for r in ['requester','verificator','releaser'] %}
            <option value="{{ r }}" {% if u.role == r %}selected{% endif %}>{{ r }}</option>
            {% endfor %}
          </select>
          {% else %}
          <span class="badge badge-blue">{{ u.role }}</span>
          {% endif %}
        </td>
        <td>
          <span class="badge {% if u.is_active %}badge-green{% else %}badge-red{% endif %}">
            {{ 'Aktif' if u.is_active else 'Nonaktif' }}
          </span>
        </td>
        <td>{{ u.last_login[:16] if u.last_login else '—' }}</td>
        <td>{{ u.created_at[:10] if u.created_at else '—' }}</td>
        <td>
          {% if u.username != 'admin' %}
          {% if u.is_active %}
          <button class="btn btn-danger btn-sm" onclick="toggleUser('{{ u.username }}', false)">Nonaktifkan</button>
          {% else %}
          <button class="btn btn-success btn-sm" onclick="toggleUser('{{ u.username }}', true)">Aktifkan</button>
          {% endif %}
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- MODAL: Tambah User -->
<div class="modal-overlay" id="modal-add-user">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">Tambah User Baru</span>
      <button class="modal-close" onclick="closeModal('modal-add-user')">✕</button>
    </div>
    <div class="form-group">
      <label>Username</label>
      <input type="text" id="new-username" placeholder="Huruf kecil, tanpa spasi">
    </div>
    <div class="form-group">
      <label>Password (minimal 8 karakter)</label>
      <input type="password" id="new-password" placeholder="Password awal">
    </div>
    <div class="form-group">
      <label>Role</label>
      <select id="new-role">
        <option value="requester">Requester — input data, lihat laporan</option>
        <option value="verificator">Verificator — review, buat memo</option>
        <option value="releaser">Releaser — approve, release payment</option>
      </select>
    </div>
    <div class="alert alert-success" style="font-size:.8rem; margin-top:.5rem">
      User baru wajib ganti password saat pertama login.
    </div>
    <div style="display:flex; gap:.75rem; justify-content:flex-end; margin-top:.75rem">
      <button class="btn btn-secondary" onclick="closeModal('modal-add-user')">Batal</button>
      <button class="btn btn-primary" onclick="addUser()">💾 Tambah User</button>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
async function addUser() {
  const username = document.getElementById("new-username").value.trim();
  const password = document.getElementById("new-password").value;
  const role     = document.getElementById("new-role").value;
  if (!username || !password) { showToast("Username dan password wajib diisi.", "error"); return; }
  const resp = await apiFetch("/users/add", {
    method: "POST", body: JSON.stringify({ username, password, role })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) { closeModal("modal-add-user"); setTimeout(() => location.reload(), 800); }
}

async function toggleUser(username, isActive) {
  const label = isActive ? "aktifkan" : "nonaktifkan";
  if (!confirm(`${label} user '${username}'?`)) return;
  const resp = await apiFetch(`/users/${username}/toggle`, {
    method: "POST", body: JSON.stringify({ is_active: isActive })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
  if (data.ok) setTimeout(() => location.reload(), 600);
}

async function changeRole(username, role) {
  const resp = await apiFetch(`/users/${username}/role`, {
    method: "POST", body: JSON.stringify({ role })
  });
  const data = await resp.json();
  showToast(data.pesan, data.ok ? "success" : "error");
}
</script>
{% endblock %}
```

- [ ] **Step 7: Update app.py — register users blueprint**

Tambahkan di `create_app()`:

```python
    from modules.users.routes import bp as users_bp
    app.register_blueprint(users_bp)
```

- [ ] **Step 8: Jalankan semua test**

```bash
cd C:\Financehub\app
pytest tests/ -v
```

Expected: semua test PASS (25+ tests).

- [ ] **Step 9: Commit**

```bash
git add app/modules/users/ app/templates/users/ app/app.py app/tests/test_users_service.py
git commit -m "feat: user management — tambah user, toggle aktif, ganti role (releaser only)"
```

---

**Part 3 selesai.** Payment Approval Memo lengkap (buat memo, update status draft→submitted→approved→paid, PDF export), Payment Application monitoring dengan TAT, dan User Management Releaser. Lanjut ke Part 4: REST API + Coming Soon + Deployment.

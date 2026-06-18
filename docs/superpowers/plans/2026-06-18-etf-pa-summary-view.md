# ETF PA Summary View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `pa_summary` SQL VIEW aggregating `etf_pa` + `etf_pa_lines` + `siswa` per `pa_number`, exposed as a new Summary tab in the ETF Payment Application page.

**Architecture:** Drop the UNIQUE constraint on `etf_pa.pa_number` (allowing multiple rows per PA number), create a VIEW `pa_summary` using `GROUP_CONCAT(DISTINCT ...)` + `SUM`, add a lazy-loaded Summary tab that fetches from a new `/etf-payment-application/summary` JSON endpoint.

**Tech Stack:** SQLite (GROUP_CONCAT, VIEW), Flask/Jinja2, vanilla JS fetch

---

## File Map

| File | Change |
|---|---|
| `app/database.py` | Drop UNIQUE in DDL string + migrate_db(); add CREATE VIEW pa_summary |
| `app/modules/etf_payment_application/service.py` | Add `get_pa_summary()` |
| `app/modules/etf_payment_application/routes.py` | Allow `summary` tab in `_tab()`; add `/summary` route |
| `app/templates/etf_payment_application/index.html` | Add Summary tab nav item + summary section + JS loader |
| `app/tests/test_etf_pa_service.py` | Add tests for duplicate pa_number + pa_summary view |

---

## Task 1: Migrate DB schema — drop UNIQUE on etf_pa.pa_number + create pa_summary VIEW

**Files:**
- Modify: `app/database.py:206-240` (DDL string)
- Modify: `app/database.py:460-514` (migrate_db section)
- Test: `app/tests/test_etf_pa_service.py`

- [ ] **Step 1: Write failing tests**

Add to `app/tests/test_etf_pa_service.py` after the existing imports:

```python
from database import get_conn, init_db


def test_etf_pa_allows_duplicate_pa_number():
    """etf_pa should accept two rows with the same pa_number."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, nomor_pam, status, created_at) "
        "VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/ETF/DUP/2026", "PAM-001", "complete", "2026-06-18")
    )
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, nomor_pam, status, created_at) "
        "VALUES (?,?,?,?,?)",
        (COMPANY_ID, "PA/ETF/DUP/2026", "PAM-002", "complete", "2026-06-18")
    )
    conn.commit()
    count = conn.execute(
        "SELECT COUNT(*) FROM etf_pa WHERE pa_number='PA/ETF/DUP/2026'"
    ).fetchone()[0]
    conn.close()
    assert count == 2


def test_pa_summary_view_aggregates():
    """pa_summary view sums jumlah_pembayaran and comma-separates nomor_pam."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, nomor_pam, tanggal_bayar, status, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "PA/ETF/S/2026", "PAM-A", "2026-06-01", "complete", "2026-06-18")
    )
    pa_id1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, nomor_pam, tanggal_bayar, status, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "PA/ETF/S/2026", "PAM-B", "2026-06-02", "complete", "2026-06-18")
    )
    pa_id2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    sid = _student_id("1230001")
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, semester, jumlah_pembayaran) "
        "VALUES (?,?,?,?,?)",
        (pa_id1, sid, "By Pendidikan", "Semester 1", 5000000)
    )
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, semester, jumlah_pembayaran) "
        "VALUES (?,?,?,?,?)",
        (pa_id2, sid, "By Tunjangan", "Semester 2", 3000000)
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM pa_summary WHERE pa_number='PA/ETF/S/2026' AND company_id=?",
        (COMPANY_ID,)
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["jumlah_pembayaran"] == 8000000
    nomor_pam_vals = set(row["nomor_pam"].split(","))
    assert "PAM-A" in nomor_pam_vals
    assert "PAM-B" in nomor_pam_vals
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd C:/Financehub/app && python -m pytest tests/test_etf_pa_service.py::test_etf_pa_allows_duplicate_pa_number tests/test_etf_pa_service.py::test_pa_summary_view_aggregates -v
```

Expected: FAIL — `IntegrityError: UNIQUE constraint failed` on first test; `OperationalError: no such table: pa_summary` on second.

- [ ] **Step 3: Update DDL string in database.py**

In `app/database.py`, find the `CREATE TABLE IF NOT EXISTS etf_pa` block in the DDL string (around line 206). Change `pa_number TEXT UNIQUE NOT NULL` → `pa_number TEXT NOT NULL`:

```python
# OLD (line ~209):
#     pa_number                TEXT UNIQUE NOT NULL,
# NEW:
#     pa_number                TEXT NOT NULL,
```

Then directly after the `etf_pa_lines` DDL block and indexes (after line ~240), add the VIEW:

```sql
CREATE VIEW IF NOT EXISTS pa_summary AS
SELECT
    e.company_id,
    e.pa_number,
    GROUP_CONCAT(DISTINCT e.tgl_payment_application) AS tgl_payment_application,
    GROUP_CONCAT(DISTINCT e.nomor_pam)               AS nomor_pam,
    GROUP_CONCAT(DISTINCT s.nama)                    AS nama_student,
    GROUP_CONCAT(DISTINCT l.jenis_pembayaran)        AS jenis_pembayaran,
    GROUP_CONCAT(DISTINCT l.semester)                AS semester,
    SUM(l.jumlah_pembayaran)                         AS jumlah_pembayaran,
    GROUP_CONCAT(DISTINCT e.status)                  AS status,
    GROUP_CONCAT(DISTINCT e.tanggal_bayar)           AS tanggal_bayar,
    GROUP_CONCAT(DISTINCT e.keterangan)              AS keterangan
FROM etf_pa e
LEFT JOIN etf_pa_lines l ON l.pa_id = e.id
LEFT JOIN siswa s ON s.id = l.student_id
GROUP BY e.company_id, e.pa_number;
```

- [ ] **Step 4: Add migration step in migrate_db()**

In `app/database.py`, find the `# etf_pa table` migration section (around line 460). Replace the existing block with one that recreates the table without UNIQUE, plus creates the VIEW:

```python
    # etf_pa — drop UNIQUE constraint on pa_number (recreate table)
    try:
        has_unique = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='etf_pa'"
        ).fetchone()
        if has_unique and "UNIQUE" in (has_unique[0] or ""):
            conn.executescript("""
                PRAGMA foreign_keys = OFF;
                ALTER TABLE etf_pa RENAME TO etf_pa_old;
                CREATE TABLE etf_pa (
                    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id               INTEGER NOT NULL REFERENCES companies(id),
                    pa_number                TEXT NOT NULL,
                    tgl_payment_application  TEXT,
                    tgl_surat_pengajuan      TEXT,
                    doc_received_by_educ     TEXT,
                    received_pa_from_educ    TEXT,
                    checked_by_fincon        TEXT,
                    approved_by_htj_1        TEXT,
                    send_pa_back_to_educ     TEXT,
                    pa_received_by_po_fin    TEXT,
                    approval_by_htj_2        TEXT,
                    nomor_pam                TEXT,
                    tanggal_bayar            TEXT,
                    keterangan               TEXT,
                    status                   TEXT NOT NULL DEFAULT 'draft',
                    created_at               TEXT NOT NULL,
                    updated_at               TEXT
                );
                INSERT INTO etf_pa SELECT * FROM etf_pa_old;
                DROP TABLE etf_pa_old;
                PRAGMA foreign_keys = ON;
            """)
            conn.commit()
    except Exception as e:
        print(f"[migrate] etf_pa UNIQUE drop: {e}")

    # pa_summary view
    try:
        conn.executescript("""
            DROP VIEW IF EXISTS pa_summary;
            CREATE VIEW pa_summary AS
            SELECT
                e.company_id,
                e.pa_number,
                GROUP_CONCAT(DISTINCT e.tgl_payment_application) AS tgl_payment_application,
                GROUP_CONCAT(DISTINCT e.nomor_pam)               AS nomor_pam,
                GROUP_CONCAT(DISTINCT s.nama)                    AS nama_student,
                GROUP_CONCAT(DISTINCT l.jenis_pembayaran)        AS jenis_pembayaran,
                GROUP_CONCAT(DISTINCT l.semester)                AS semester,
                SUM(l.jumlah_pembayaran)                         AS jumlah_pembayaran,
                GROUP_CONCAT(DISTINCT e.status)                  AS status,
                GROUP_CONCAT(DISTINCT e.tanggal_bayar)           AS tanggal_bayar,
                GROUP_CONCAT(DISTINCT e.keterangan)              AS keterangan
            FROM etf_pa e
            LEFT JOIN etf_pa_lines l ON l.pa_id = e.id
            LEFT JOIN siswa s ON s.id = l.student_id
            GROUP BY e.company_id, e.pa_number;
        """)
        conn.commit()
    except Exception as e:
        print(f"[migrate] pa_summary view: {e}")
```

Also remove or replace the old `# etf_pa table` try/except block (lines ~462-485) since migrate_db now handles it above.

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd C:/Financehub/app && python -m pytest tests/test_etf_pa_service.py::test_etf_pa_allows_duplicate_pa_number tests/test_etf_pa_service.py::test_pa_summary_view_aggregates -v
```

Expected: PASS both.

- [ ] **Step 6: Run full test suite — no regressions**

```bash
cd C:/Financehub/app && python -m pytest tests/test_etf_pa_service.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 7: Run migration on live DB**

```bash
cd C:/Financehub/app && python database.py
```

Verify:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('finance_hub.db')
cur = conn.cursor()
cur.execute(\"SELECT sql FROM sqlite_master WHERE type='table' AND name='etf_pa'\")
print(cur.fetchone()[0])
cur.execute(\"SELECT COUNT(*) FROM pa_summary\")
print('pa_summary rows:', cur.fetchone()[0])
conn.close()
"
```

Expected: `pa_number TEXT NOT NULL` (no UNIQUE), pa_summary rows = some number based on current data.

- [ ] **Step 8: Commit**

```bash
cd C:/Financehub && git add app/database.py app/tests/test_etf_pa_service.py
git commit -m "feat: drop UNIQUE on etf_pa.pa_number; add pa_summary view"
```

---

## Task 2: Import etf_pa + etf_pa_lines from Excel

**Files:**
- Script (run once, not committed): import via Python

- [ ] **Step 1: Import etf_pa (2161 rows)**

```python
import sqlite3, pandas as pd

df = pd.read_excel('C:/Users/25010160/Downloads/etf_pa query upload 180626.xlsx')
for col in df.columns:
    df[col] = df[col].where(df[col].notna(), None)

conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
cur = conn.cursor()
cur.execute('PRAGMA foreign_keys = OFF')
cur.execute('DELETE FROM etf_pa')

cols = ['id','company_id','pa_number','tgl_payment_application','tgl_surat_pengajuan',
        'doc_received_by_educ','received_pa_from_educ','checked_by_fincon',
        'approved_by_htj_1','send_pa_back_to_educ','pa_received_by_po_fin',
        'approval_by_htj_2','nomor_pam','tanggal_bayar','keterangan','status',
        'created_at','updated_at']
ph = ','.join(['?']*len(cols))
cur.executemany(
    f'INSERT INTO etf_pa ({",".join(cols)}) VALUES ({ph})',
    [tuple(row[c] for c in cols) for _, row in df.iterrows()]
)
conn.commit()
cur.execute('SELECT COUNT(*) FROM etf_pa')
print('etf_pa inserted:', cur.fetchone()[0])
cur.execute('PRAGMA foreign_keys = ON')
conn.close()
```

Run and verify output: `etf_pa inserted: 2161`

- [ ] **Step 2: Import etf_pa_lines (2228 rows)**

```python
import sqlite3, pandas as pd

df = pd.read_excel('C:/Users/25010160/Downloads/etf_pa_lines query upload 180626.xlsx')
for col in df.columns:
    df[col] = df[col].where(df[col].notna(), None)

conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
cur = conn.cursor()
cur.execute('PRAGMA foreign_keys = OFF')
cur.execute('DELETE FROM etf_pa_lines')

cols = ['id','pa_id','student_id','jenis_pembayaran','semester',
        'tahun_ajaran','ipk_sem_sebelumnya','jumlah_pembayaran']
ph = ','.join(['?']*len(cols))
cur.executemany(
    f'INSERT INTO etf_pa_lines ({",".join(cols)}) VALUES ({ph})',
    [tuple(row[c] for c in cols) for _, row in df.iterrows()]
)
conn.commit()
cur.execute('SELECT COUNT(*) FROM etf_pa_lines')
print('etf_pa_lines inserted:', cur.fetchone()[0])
cur.execute('PRAGMA foreign_keys = ON')
conn.close()
```

Run and verify output: `etf_pa_lines inserted: 2228`

- [ ] **Step 3: Verify pa_summary has data**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM pa_summary')
print('pa_summary rows:', cur.fetchone()[0])
cur.execute('SELECT * FROM pa_summary WHERE pa_number=\"PA/ETF/1/2026\"')
row = cur.fetchone()
print('PA/ETF/1/2026:', dict(row) if row else None)
conn.close()
"
```

Expected: 2071 unique pa_summary rows; PA/ETF/1/2026 shows combined nomor_pam and total jumlah_pembayaran.

---

## Task 3: Backend service function + route

**Files:**
- Modify: `app/modules/etf_payment_application/service.py`
- Modify: `app/modules/etf_payment_application/routes.py`

- [ ] **Step 1: Add get_pa_summary to service.py**

Add at the end of `app/modules/etf_payment_application/service.py`:

```python
def get_pa_summary(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM pa_summary WHERE company_id=? ORDER BY pa_number",
        (company_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: Update imports in routes.py**

In `app/modules/etf_payment_application/routes.py`, add `get_pa_summary` to the import:

```python
from modules.etf_payment_application.service import (
    get_pa_list, get_pa_flat, get_pa_header, bulk_update_pa, export_pa_excel,
    create_pa, update_pa, delete_pa, get_pa_lines, get_siswa_autocomplete,
    get_draft_siswa, get_draft_lines_for_siswa, VALID_TABS, get_pa_summary,
)
```

- [ ] **Step 3: Update _tab() to allow summary tab**

In `app/modules/etf_payment_application/routes.py`, change `_tab()`:

```python
def _tab(allow_input: bool = False, allow_summary: bool = False):
    t = request.args.get("tab", "agri").lower()
    if allow_input and t == "input":
        return "input"
    if allow_summary and t == "summary":
        return "summary"
    return t if t in VALID_TABS else "agri"
```

- [ ] **Step 4: Update index() route to pass summary tab through**

In `app/modules/etf_payment_application/routes.py`, change the `index` function:

```python
@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    tab = _tab(allow_input=True, allow_summary=True)
    sf = ""
    pa_rows = []
    if tab not in ("input", "summary"):
        sf = request.args.get("sf", "active").lower()
        if sf not in ("open", "on_process", "complete", "active", ""):
            sf = "active"
        pa_rows = get_pa_flat(company_id, tab, sf)
    return render_template(
        "etf_payment_application/index.html",
        pa_rows=pa_rows,
        active_tab=tab,
        active_sf=sf,
        cat1=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        active_page="etf_payment_app",
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        **_ctx(),
    )
```

- [ ] **Step 5: Add /summary JSON route**

Add after the `index` route in `app/modules/etf_payment_application/routes.py`:

```python
@bp.route("/summary-data")
@jwt_html_required
def summary_data():
    company_id = session.get("company_id")
    return jsonify(get_pa_summary(company_id))
```

- [ ] **Step 6: Commit**

```bash
cd C:/Financehub && git add app/modules/etf_payment_application/service.py app/modules/etf_payment_application/routes.py
git commit -m "feat: add get_pa_summary service + /summary-data route"
```

---

## Task 4: Frontend — Summary tab + table

**Files:**
- Modify: `app/templates/etf_payment_application/index.html`

- [ ] **Step 1: Add Summary to tab nav**

Find the tab nav loop (line ~179):
```html
{% for t, label in [('input','Input'),('agri','AGRI'),('app','APP'),('sml','LAND'),('setf','SETF')] %}
```

Change to:
```html
{% for t, label in [('input','Input'),('agri','AGRI'),('app','APP'),('sml','LAND'),('setf','SETF'),('summary','Summary')] %}
```

- [ ] **Step 2: Exclude summary from filter bar and PA table**

Find the filter bar condition (line ~201):
```html
{% if active_tab != 'input' %}
```
Change to:
```html
{% if active_tab not in ('input', 'summary') %}
```

Find the PA table section. Search for `{% if active_tab != 'input' %}` that wraps the PA table scroll container. Change to:
```html
{% if active_tab not in ('input', 'summary') %}
```

- [ ] **Step 3: Add Summary section**

After the closing `{% endif %}` of the PA table section, add:

```html
{# ── Summary Tab ──────────────────────────────────────────────── #}
{% if active_tab == 'summary' %}
<div style="margin-top:.5rem">
  <div id="summary-loading" style="text-align:center; padding:2rem; color:var(--text-muted)">Memuat data summary...</div>
  <div id="summary-wrap" style="display:none; overflow-x:auto; max-height:calc(100vh - 180px); overflow-y:auto">
    <table id="summary-table" style="width:100%; border-collapse:collapse; font-size:.8rem">
      <thead>
        <tr style="background:var(--bg-muted); position:sticky; top:0; z-index:2">
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">#</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">PA Number</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Tgl PA</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Nomor PAM</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Nama Student</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Jenis Pembayaran</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Semester</th>
          <th style="padding:.5rem .6rem; text-align:right; white-space:nowrap; border-bottom:2px solid var(--border)">Total (IDR)</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Status</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Tgl Bayar</th>
          <th style="padding:.5rem .6rem; text-align:left; white-space:nowrap; border-bottom:2px solid var(--border)">Keterangan</th>
        </tr>
      </thead>
      <tbody id="summary-tbody"></tbody>
    </table>
  </div>
  <div id="summary-count" style="margin-top:.4rem; font-size:.75rem; color:var(--text-muted)"></div>
</div>

<script>
(function loadSummary() {
  fetch('/etf-payment-application/summary-data')
    .then(r => r.json())
    .then(rows => {
      const tbody = document.getElementById('summary-tbody');
      tbody.innerHTML = rows.map((r, i) => `
        <tr style="border-bottom:1px solid var(--border)">
          <td style="padding:.4rem .6rem; color:var(--text-muted)">${i+1}</td>
          <td style="padding:.4rem .6rem; font-weight:600; white-space:nowrap">${r.pa_number || ''}</td>
          <td style="padding:.4rem .6rem; white-space:nowrap">${r.tgl_payment_application || '-'}</td>
          <td style="padding:.4rem .6rem">${r.nomor_pam || '-'}</td>
          <td style="padding:.4rem .6rem">${r.nama_student || '-'}</td>
          <td style="padding:.4rem .6rem">${r.jenis_pembayaran || '-'}</td>
          <td style="padding:.4rem .6rem">${r.semester || '-'}</td>
          <td style="padding:.4rem .6rem; text-align:right; font-variant-numeric:tabular-nums">${(r.jumlah_pembayaran||0).toLocaleString('id-ID')}</td>
          <td style="padding:.4rem .6rem">${r.status || '-'}</td>
          <td style="padding:.4rem .6rem; white-space:nowrap">${r.tanggal_bayar || '-'}</td>
          <td style="padding:.4rem .6rem">${r.keterangan || '-'}</td>
        </tr>`).join('');
      document.getElementById('summary-loading').style.display = 'none';
      document.getElementById('summary-wrap').style.display = 'block';
      document.getElementById('summary-count').textContent = `${rows.length} PA Number`;
    })
    .catch(err => {
      document.getElementById('summary-loading').textContent = 'Gagal memuat data: ' + err.message;
    });
})();
</script>
{% endif %}
```

- [ ] **Step 4: Commit**

```bash
cd C:/Financehub && git add app/templates/etf_payment_application/index.html
git commit -m "feat: add Summary tab to ETF PA page with pa_summary view"
```

- [ ] **Step 5: Run full test suite — no regressions**

```bash
cd C:/Financehub/app && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests PASS.

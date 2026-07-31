# FLOW Dynamic Pagination Page Size Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paginated tables (Payment Memo's SMT/AGRI tabs, Payment Application, Sponsorship's Data tab) size their page to the visible screen height instead of a fixed row count, so tall screens show more rows instead of leaving empty space below a partial last page.

**Architecture:** A shared JS helper (`computeDynamicPageSize`) measures actual rendered row height against available container height to compute a page size, clamped to `[default, default×4]`. Payment Memo (client-side, all rows already in memory) re-slices instantly with no reload. Payment Application and Sponsorship's Data tab (server-side pagination) accept an optional `page_size` query param, defaulting to today's fixed size; JS measures after render and triggers at most one calibration reload, then caches the result in `localStorage` keyed by viewport height so later loads skip the reload.

**Tech Stack:** Flask/Jinja2, vanilla JS, pytest (no JS test framework exists in this repo — JS tasks are verified by manual browser check, not automated tests).

## Global Constraints

- No live recompute on window resize — only on page load/reload (spec requirement, user-confirmed).
- Payment Memo's non-paginating tabs (FIORI/APP, SML/LAND, SETF, Advance, Vendors), Sponsorship's Outstanding/Report tabs, and Payment Application's `summary` tab's own separate client-side pagination (`_summaryPageSize`) are OUT OF SCOPE — do not touch them.
- The FinanceHub working tree currently has substantial pre-existing uncommitted changes in several files this plan touches (`app/static/js/app.js`, `app/templates/payment_memo/index.html`, `app/templates/etf_payment_application/index.html`, `app/modules/sponsorship/routes.py`, `app/templates/sponsorship/data.html`) — confirmed with the user to be old, abandoned WIP that is safe to ignore. Each task below still edits only the exact lines described; commit with plain `git add <file> && git commit` (this will fold the pre-existing uncommitted content into the commit alongside this feature's changes — that's expected and accepted, not a mistake to avoid).
- Every code snippet and pytest test below was hand-verified against the current codebase before this plan was written (implemented, run, confirmed passing/failing as described, then reverted) — copy them as given rather than re-deriving.

---

### Task 1: Shared dynamic page-size JS helpers

**Files:**
- Modify: `app/static/js/app.js:610` (insert after `restoreFilterOpenState()`, before `pressTabStep()`)

**Interfaces:**
- Produces: `computeDynamicPageSize(opts)` — `opts: {scrollContainer, rowSelector, defaultSize}` (selectors or elements), returns an integer page size. `getCachedPageSize(name, viewportHeight)` / `setCachedPageSize(name, pageSize, viewportHeight)` — localStorage cache keyed by a short name, invalidated when viewport height differs by more than 20px. `initServerPagedDynamicSize(opts)` — `opts: {cacheName, paramName, scrollContainer, rowSelector, defaultSize, renderedPageSize}`, triggers at most one `window.location.href` reload with `paramName` set in the query string.

- [ ] **Step 1: Add the helpers to app.js**

Open `app/static/js/app.js`, find this existing block (currently ending at line 610):

```js
function restoreFilterOpenState() {
  const panel = getActiveFilterPanel();
  if (panel && panel.id && sessionStorage.getItem(_filterOpenKey(panel)) === '1') {
    panel.classList.add('open');
  }
}
```

Insert immediately after it (before the `pressTabStep` comment block):

```js

// Dynamic pagination page-size: computes how many rows fit the space below
// a paginated table so screen height isn't wasted on a half-empty last page.
// See docs/superpowers/specs/2026-07-31-flow-dynamic-pagination-page-size-design.md
function computeDynamicPageSize(opts) {
  const container = typeof opts.scrollContainer === 'string'
    ? document.querySelector(opts.scrollContainer) : opts.scrollContainer;
  const row = typeof opts.rowSelector === 'string'
    ? document.querySelector(opts.rowSelector) : opts.rowSelector;
  if (!container || !row) return opts.defaultSize;
  const rowHeight = row.getBoundingClientRect().height;
  if (!rowHeight) return opts.defaultSize;
  const available = container.getBoundingClientRect().height;
  const raw = Math.floor(available / rowHeight);
  return Math.max(opts.defaultSize, Math.min(raw, opts.defaultSize * 4));
}

function _pageSizeCacheKey(name) {
  return 'fh-pagesize:' + name;
}
function getCachedPageSize(name, viewportHeight) {
  try {
    const raw = localStorage.getItem(_pageSizeCacheKey(name));
    if (!raw) return null;
    const cached = JSON.parse(raw);
    if (!cached || Math.abs(cached.viewportHeight - viewportHeight) > 20) return null;
    return cached.pageSize;
  } catch (e) { return null; }
}
function setCachedPageSize(name, pageSize, viewportHeight) {
  try {
    localStorage.setItem(_pageSizeCacheKey(name), JSON.stringify({ pageSize, viewportHeight }));
  } catch (e) {}
}

// Shared "calibrate once, then cache" flow for server-paginated tables
// (Payment Application, Sponsorship Data tab). Called after the table has
// rendered `renderedPageSize` rows. Navigates (full page reload) at most
// once: either applying a cached size that doesn't match what was rendered,
// or applying a freshly-measured size that differs from what was rendered.
// No-op if the current render already matches the right size.
function initServerPagedDynamicSize(opts) {
  const viewportHeight = window.innerHeight;
  const url = new URL(window.location);
  const cached = getCachedPageSize(opts.cacheName, viewportHeight);
  if (cached && cached !== opts.renderedPageSize) {
    url.searchParams.set(opts.paramName, cached);
    window.location.href = url.toString();
    return;
  }
  requestAnimationFrame(() => {
    const computed = computeDynamicPageSize({
      scrollContainer: opts.scrollContainer,
      rowSelector: opts.rowSelector,
      defaultSize: opts.defaultSize,
    });
    setCachedPageSize(opts.cacheName, computed, viewportHeight);
    if (computed !== opts.renderedPageSize) {
      url.searchParams.set(opts.paramName, computed);
      window.location.href = url.toString();
    }
  });
}
```

- [ ] **Step 2: Manual verify (no JS test framework in this repo)**

Run the Flask dev server, open any FinanceHub page, open devtools console, and run:

```js
typeof computeDynamicPageSize === 'function' &&
typeof getCachedPageSize === 'function' &&
typeof setCachedPageSize === 'function' &&
typeof initServerPagedDynamicSize === 'function'
```

Expected: `true`, and no console errors on page load.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/app.js
git commit -m "feat: add shared dynamic pagination page-size helpers"
```

---

### Task 2: Payment Memo — SMT tab dynamic page size

**Files:**
- Modify: `app/templates/payment_memo/index.html:2413` (declaration), `:2444-2447` (loadSMT)

**Interfaces:**
- Consumes: `computeDynamicPageSize`, `getCachedPageSize`, `setCachedPageSize` (Task 1).

- [ ] **Step 1: Change `_smtPageSize` from `const` to `let`**

Find (line 2413):
```js
const _smtPageSize = 50;
```
Replace with:
```js
let _smtPageSize = 50;
```

- [ ] **Step 2: Wire dynamic sizing into `loadSMT()`**

Find (lines 2444-2447):
```js
  _smtAllRows = data.rows;
  _smtPage = 1;
  if (count) count.textContent = data.rows.length + ' baris';
  _smtRenderPage();
```
Replace with:
```js
  _smtAllRows = data.rows;
  _smtPage = 1;
  if (count) count.textContent = data.rows.length + ' baris';
  const _smtCachedSize = getCachedPageSize('smt', window.innerHeight);
  if (_smtCachedSize) _smtPageSize = _smtCachedSize;
  _smtRenderPage();
  if (_smtAllRows.length) {
    const _smtComputed = computeDynamicPageSize({
      scrollContainer: '#tab-smt .pillar-table-wrap',
      rowSelector: '#smt-tbody tr',
      defaultSize: 50,
    });
    setCachedPageSize('smt', _smtComputed, window.innerHeight);
    if (_smtComputed !== _smtPageSize) {
      _smtPageSize = _smtComputed;
      _smtRenderPage();
    }
  }
```

- [ ] **Step 3: Manual verify**

Open Payment Memo → SMT tab with enough rows to paginate (50+). In devtools console: `_smtPageSize` should be greater than 50 on a tall/maximized window, and the "Menampilkan..." text should reflect the new page size. Reload — the page should render at the cached size immediately (no visible flash-then-resize on the second load).

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: dynamic page size for Payment Memo SMT tab"
```

---

### Task 3: Payment Memo — AGRI tab dynamic page size

**Files:**
- Modify: `app/templates/payment_memo/index.html:3229` (declaration), `:3264-3266` (loadPAM)

**Interfaces:**
- Consumes: same as Task 2.

- [ ] **Step 1: Change `_agriPageSize` from `const` to `let`**

Find (line 3229):
```js
const _agriPageSize = 50;
```
Replace with:
```js
let _agriPageSize = 50;
```

- [ ] **Step 2: Wire dynamic sizing into `loadPAM()`**

Find (lines 3264-3266):
```js
  _agriAllRows = data.rows;
  _agriPage = 1;
  _agriRenderPage();
```
Replace with:
```js
  _agriAllRows = data.rows;
  _agriPage = 1;
  const _agriCachedSize = getCachedPageSize('agri', window.innerHeight);
  if (_agriCachedSize) _agriPageSize = _agriCachedSize;
  _agriRenderPage();
  if (_agriAllRows.length) {
    const _agriComputed = computeDynamicPageSize({
      scrollContainer: '#tab-pam .pillar-table-wrap',
      rowSelector: '#pam-tbody tr',
      defaultSize: 50,
    });
    setCachedPageSize('agri', _agriComputed, window.innerHeight);
    if (_agriComputed !== _agriPageSize) {
      _agriPageSize = _agriComputed;
      _agriRenderPage();
    }
  }
```

- [ ] **Step 3: Manual verify**

Same as Task 2 Step 3, but on the AGRI (PAM) tab, checking `_agriPageSize` and `#pam-tbody`.

- [ ] **Step 4: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: dynamic page size for Payment Memo AGRI tab"
```

---

### Task 4: Payment Application — backend `page_size` query param

**Files:**
- Modify: `app/modules/etf_payment_application/routes.py:40` (constant + new helper), `:53-102` (index route body), `:110` (render_template kwarg)
- Test: `app/tests/test_pa_dynamic_page_size.py` (new)

**Interfaces:**
- Produces: route `GET /etf-payment-application/?tab=<t>&page_size=<n>` — `page_size` optional, defaults to `PA_PAGE_SIZE` (50), invalid/out-of-range values fall back to the default, valid range is `[1, PA_PAGE_SIZE_MAX]` (`PA_PAGE_SIZE_MAX = 200`). Template receives `page_size` reflecting what was actually used (already the case today via the existing `page_size=` kwarg, just no longer hardcoded to the constant).

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_pa_dynamic_page_size.py`:

```python
from database import get_conn
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
            """INSERT INTO siswa (company_id, code, nama, jenjang, angkatan,
               program, fakultas, universitas, status, ipk_sem1)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_pa_dynamic_page_size.py -v`
Expected: `test_page_size_query_param_controls_slicing` FAILS (assertion on `b"halaman 1/2"`), the other 3 pass already (they don't exercise the new behavior yet).

- [ ] **Step 3: Add `PA_PAGE_SIZE_MAX` and `_resolve_page_size()`**

Find (routes.py, near line 40):
```python
PA_PAGE_SIZE = 50
```
Replace with:
```python
PA_PAGE_SIZE = 50
PA_PAGE_SIZE_MAX = PA_PAGE_SIZE * 4


def _resolve_page_size():
    try:
        requested = int(request.args.get("page_size", PA_PAGE_SIZE))
    except ValueError:
        return PA_PAGE_SIZE
    if 1 <= requested <= PA_PAGE_SIZE_MAX:
        return requested
    return PA_PAGE_SIZE
```

- [ ] **Step 4: Default `page_size` alongside the other pre-block defaults**

Find (in `index()`, near line 53):
```python
    page = 1
    total_pages = 1
    total_rows = 0
    start_row = 0
    end_row = 0
```
Replace with:
```python
    page = 1
    page_size = PA_PAGE_SIZE
    total_pages = 1
    total_rows = 0
    start_row = 0
    end_row = 0
```

- [ ] **Step 5: Use the resolved page size in the pagination block**

Find:
```python
        total_rows = len(filtered_rows)
        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1
        total_pages = max(1, -(-total_rows // PA_PAGE_SIZE))
        page = min(max(1, page), total_pages)
        offset = (page - 1) * PA_PAGE_SIZE
        pa_rows = filtered_rows[offset:offset + PA_PAGE_SIZE]
        start_row = offset + 1 if total_rows else 0
        end_row = min(offset + PA_PAGE_SIZE, total_rows)
```
Replace with:
```python
        total_rows = len(filtered_rows)
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
        end_row = min(offset + page_size, total_rows)
```

- [ ] **Step 6: Pass the resolved size to the template**

Find:
```python
        page_size=PA_PAGE_SIZE,
```
Replace with:
```python
        page_size=page_size,
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_pa_dynamic_page_size.py -v`
Expected: all 4 PASS.

- [ ] **Step 8: Commit**

```bash
git add app/modules/etf_payment_application/routes.py app/tests/test_pa_dynamic_page_size.py
git commit -m "feat: accept page_size query param on Payment Application route"
```

---

### Task 5: Payment Application — frontend calibration + cache wiring

**Files:**
- Modify: `app/templates/etf_payment_application/index.html:481-483` (`pa_page_url` macro), `:1021-1048` (near the `sizeWrap` IIFE)

**Interfaces:**
- Consumes: `initServerPagedDynamicSize` (Task 1), `page_size`/`page`/`total_rows` template variables (Task 4).

- [ ] **Step 1: Preserve `page_size` in the Prev/Next pagination macro**

Find (lines 481-483):
```
{% macro pa_page_url(p) -%}
?tab={{ active_tab }}{% if active_sf %}&sf={{ active_sf }}{% endif %}{% if f_nama %}&nama={{ f_nama | urlencode }}{% endif %}{% if f_jenjang %}&jenjang={{ f_jenjang | urlencode }}{% endif %}{% if f_program %}&program={{ f_program | urlencode }}{% endif %}{% if f_angkatan %}&angkatan={{ f_angkatan | urlencode }}{% endif %}{% if f_jenis %}&jenis={{ f_jenis | urlencode }}{% endif %}{% if f_pam %}&pam={{ f_pam | urlencode }}{% endif %}{% if f_bulan_pa %}&bulan_pa={{ f_bulan_pa }}{% endif %}{% if f_tahun_pa %}&tahun_pa={{ f_tahun_pa }}{% endif %}&page={{ p }}
{%- endmacro %}
```
Replace with:
```
{% macro pa_page_url(p) -%}
?tab={{ active_tab }}{% if active_sf %}&sf={{ active_sf }}{% endif %}{% if f_nama %}&nama={{ f_nama | urlencode }}{% endif %}{% if f_jenjang %}&jenjang={{ f_jenjang | urlencode }}{% endif %}{% if f_program %}&program={{ f_program | urlencode }}{% endif %}{% if f_angkatan %}&angkatan={{ f_angkatan | urlencode }}{% endif %}{% if f_jenis %}&jenis={{ f_jenis | urlencode }}{% endif %}{% if f_pam %}&pam={{ f_pam | urlencode }}{% endif %}{% if f_bulan_pa %}&bulan_pa={{ f_bulan_pa }}{% endif %}{% if f_tahun_pa %}&tahun_pa={{ f_tahun_pa }}{% endif %}&page_size={{ page_size }}&page={{ p }}
{%- endmacro %}
```

- [ ] **Step 2: Add the calibration call near the existing `sizeWrap` IIFE**

Find (lines 1021-1023):
```js
<script>
const TODAY   = new Date().toISOString().slice(0,10);
const ACTIVE_TAB = "{{ active_tab }}";
```
Replace with:
```js
<script>
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
}
```

- [ ] **Step 3: Manual verify**

Open Payment Application on a tab with 50+ rows (e.g. AGRI), on a tall/maximized window. First load may briefly reload once with `&page_size=N` appended to the URL; subsequent loads (same window size) should not reload. Check `localStorage.getItem('fh-pagesize:pa')` reflects `{pageSize, viewportHeight}`. Click Prev/Next and confirm the URL keeps the calibrated `page_size`.

- [ ] **Step 4: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: dynamic page-size calibration for Payment Application"
```

---

### Task 6: Sponsorship Data tab — backend `page_size` query param

**Files:**
- Modify: `app/modules/sponsorship/routes.py:18` (constant + new helper), `:172-176` (data_page route body)
- Test: `app/tests/test_sponsorship_dynamic_page_size.py` (new)

**Interfaces:**
- Produces: route `GET /sponsorship/data?page_size=<n>` — same default/clamp/invalid-fallback behavior as Task 4, `PER_PAGE_MAX = PER_PAGE * 4` (400). Template receives `page_size`.

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_sponsorship_dynamic_page_size.py`:

```python
from modules.sponsorship.service import seed_perusahaan, create_transaksi

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_sponsorship_dynamic_page_size.py -v`
Expected: `test_page_size_query_param_controls_slicing` FAILS, the other 3 pass already.

- [ ] **Step 3: Add `PER_PAGE_MAX` and `_resolve_page_size()`**

Find (routes.py, near line 18):
```python
PER_PAGE = 100
```
Replace with:
```python
PER_PAGE = 100
PER_PAGE_MAX = PER_PAGE * 4


def _resolve_page_size():
    try:
        requested = int(request.args.get("page_size", PER_PAGE))
    except ValueError:
        return PER_PAGE
    if 1 <= requested <= PER_PAGE_MAX:
        return requested
    return PER_PAGE
```

- [ ] **Step 4: Use the resolved page size in `data_page()`**

Find:
```python
    total = count_transaksi(_cid(), filters) if not _wrong_company() else 0
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    rows = list_transaksi(_cid(), filters, limit=PER_PAGE, offset=(page - 1) * PER_PAGE) if not _wrong_company() else []
```
Replace with:
```python
    total = count_transaksi(_cid(), filters) if not _wrong_company() else 0
    page_size = _resolve_page_size()
    page = request.args.get("page", 1, type=int) or 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    rows = list_transaksi(_cid(), filters, limit=page_size, offset=(page - 1) * page_size) if not _wrong_company() else []
```

- [ ] **Step 5: Pass `page_size` to the template**

Find:
```python
        rows=rows, page=page, total_pages=total_pages, total_count=total, years=years,
```
Replace with:
```python
        rows=rows, page=page, page_size=page_size, total_pages=total_pages, total_count=total, years=years,
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_sponsorship_dynamic_page_size.py -v`
Expected: all 4 PASS.

- [ ] **Step 7: Commit**

```bash
git add app/modules/sponsorship/routes.py app/tests/test_sponsorship_dynamic_page_size.py
git commit -m "feat: accept page_size query param on Sponsorship Data route"
```

---

### Task 7: Sponsorship Data tab — frontend calibration + cache wiring

**Files:**
- Modify: `app/templates/sponsorship/data.html` — the Prev/Next pagination links and the `{% block scripts %}` section.

**Interfaces:**
- Consumes: `initServerPagedDynamicSize` (Task 1), `page_size`/`total_count` template variables (Task 6).

Before starting, run `git diff app/templates/sponsorship/data.html` — this file has pre-existing uncommitted changes (see Global Constraints). The exact surrounding lines may differ from what's quoted below; locate the equivalent Prev/Next markup and `{% block scripts %}` in whatever the current version looks like, and apply the same two changes described in intent: (a) add `&page_size={{ page_size }}` to the Prev/Next links' query string, (b) add the calibration script block.

- [ ] **Step 1: Preserve `page_size` in the Prev/Next pagination links**

If the file still has the original per-filter conditional links:
```
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}"
         href="?page={{ page - 1 }}{% if filters.cat %}&cat={{ filters.cat|urlencode }}{% endif %}{% if filters.cat3 %}&cat3={{ filters.cat3|urlencode }}{% endif %}{% if filters.description %}&description={{ filters.description|urlencode }}{% endif %}{% if filters.tahun %}&tahun={{ filters.tahun|urlencode }}{% endif %}{% if filters.status %}&status={{ filters.status|urlencode }}{% endif %}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}"
         href="?page={{ page + 1 }}{% if filters.cat %}&cat={{ filters.cat|urlencode }}{% endif %}{% if filters.cat3 %}&cat3={{ filters.cat3|urlencode }}{% endif %}{% if filters.description %}&description={{ filters.description|urlencode }}{% endif %}{% if filters.tahun %}&tahun={{ filters.tahun|urlencode }}{% endif %}{% if filters.status %}&status={{ filters.status|urlencode }}{% endif %}">Next ›</a>
```
add `&page_size={{ page_size }}` right after `?page={{ page - 1 }}` and `?page={{ page + 1 }}` respectively.

If the file already has the generalized `query_str`/`filter_qs` loop (as seen in the current uncommitted working-tree version):
```
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}" href="?page={{ page - 1 }}{{ filter_qs }}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}" href="?page={{ page + 1 }}{{ filter_qs }}">Next ›</a>
```
change both to add `&page_size={{ page_size }}`:
```
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}" href="?page={{ page - 1 }}&page_size={{ page_size }}{{ filter_qs }}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}" href="?page={{ page + 1 }}&page_size={{ page_size }}{{ filter_qs }}">Next ›</a>
```

- [ ] **Step 2: Add the calibration script**

In `{% block scripts %}`, after the existing `<script src="{{ url_for('static', filename='js/sponsorship.js') }}"></script>` line, add:

```html
<script>
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
</script>
```

Use `.budget-table-container` as the scroll container if that wrapper class is present in the current file (per the pre-existing uncommitted change), otherwise fall back to `.budget-page` — the comma-separated selector list in `computeDynamicPageSize`'s `document.querySelector` call picks whichever matches first.

- [ ] **Step 3: Manual verify**

Seed or use existing Sponsorship Data with 100+ rows, load `/sponsorship/data` on a tall/maximized window, confirm one calibration reload occurs (URL gains `&page_size=N`), then reload again and confirm no further reload happens. Check `localStorage.getItem('fh-pagesize:sponsorship-data')`.

- [ ] **Step 4: Commit**

```bash
git add app/templates/sponsorship/data.html
git commit -m "feat: dynamic page-size calibration for Sponsorship Data tab"
```

---

### Task 8: Final regression and whole-branch review

**Files:** None (verification only).

- [ ] **Step 1: Run the full pytest suite**

Run: `cd app && python -m pytest -q`
Expected: no new failures beyond the pre-existing, unrelated failures already known in this repo (`test_export_report_filename_matches_cat4_and_tahun`, `test_report_page_tahun_dropdown_has_options_for_seeded_years` in `test_sponsorship_routes.py`).

- [ ] **Step 2: Manual smoke test across all three modules**

- Payment Memo SMT and AGRI tabs: page size adapts, no console errors, sort/filter/bulk-edit still work.
- Payment Application: a per-pillar tab (e.g. AGRI) calibrates once then stays stable; Prev/Next preserve `page_size`; the `input`/`summary`/`advance` tabs (unaffected by this plan) still load normally.
- Sponsorship Data tab: calibrates once then stays stable; filters and Excel export still work; Outstanding/Report tabs (out of scope) still load normally.

- [ ] **Step 3: Final whole-branch review**

Review the full diff introduced by Tasks 1-7 (`git log` since this plan's first commit) against `docs/superpowers/specs/2026-07-31-flow-dynamic-pagination-page-size-design.md` — confirm every spec requirement is covered and no out-of-scope tabs were touched.

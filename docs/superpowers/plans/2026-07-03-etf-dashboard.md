# ETF Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-07-03-etf-dashboard-design.md` (all sections approved 2026-07-03).

**Goal:** Replace the dead "Total Memo"/"Memo Draft" KPI cards on the ETF dashboard with 4 real KPI cards plus two prioritized action lists ("PA Perlu Tindakan", "PAM Perlu Tindakan") sorted by days stuck in current approval stage, with deep links that land the user on the editable record.

**Architecture:** New `app/modules/dashboard/service.py` does all aggregation in Python (per approved Section 5): ~6 light queries (4 pillar PA tables + `pam_records` + `{pillar}_pam_lines`), then a shared stage-walk computes "days in current stage" for both the KPI average and the action lists — one source of truth. Dashboard template is server-rendered Jinja (no AJAX). Deep links reuse existing URL params on the PA page (`?tab=&sf=`) and add tiny read-URL-params-on-load scripts to both module templates.

**Tech Stack:** Python stdlib only (`datetime.date`), SQLite via existing `get_conn()`, Jinja server-side rendering, vanilla JS (no new libraries).

## Global Constraints

- Python-side aggregation only — **no new SQL views**, no schema changes, no new dependencies
- Date columns are TEXT — parse defensively: take first 10 chars, `date.fromisoformat`, treat unparseable as "filled but dateless" (never crash the dashboard)
- Stage-walk rule (approved Section 3): current stage = **first empty** column in chain order; days = today − **MAX(all filled dates)**; PA fallback baseline `tgl_payment_application` → `created_at`; PAM line fallback `pam_date` → memo `created_at`
- PAM aggregation: 1 row per memo, age = longest-stuck **unfinished** vendor line (line selesai ⇔ `tgl_kirim` filled); all lines selesai but memo open → stage "Menunggu pembayaran"; zero lines → stage "Belum ada vendor line"
- Sort: days desc, tie-break `total_amount` desc; top 10 per list
- PA scope: `status IN ('open','on_process')` across `etf_pa`/`app_pa`/`sml_pa`/`setf_pa`; PAM scope: `pam_records.status='open'`
- SMT (non-ETF) dashboard branch stays **unchanged** (its Total Memo/Memo Draft cards remain — out of scope); the ETF branch stops querying `payment_memo` entirely (dead-card bugfix)
- All new CSS-in-template colors must use existing CSS variables (`--border`, `--text-muted`, `--caution`, `--positive`, `--accent-surface`, `--bg-muted`) for dark/light support
- Deep-link params: PA `?tab=<tab>&sf=active&open_pa=<pa_id>` (uses `sf=active` so both open and on_process items are present in the list); PAM `?pam_pillar=<PILLAR>&pam_no=<pam_no>`
- Pillar mappings are duplicated as module constants in the dashboard service (mirroring `_TAB_CFG` in `etf_payment_application/service.py` and `_PILLAR_LINES_TABLE` in `payment_memo/service.py`) — do not import private constants across modules

---

## File Structure

| File | Changes |
|---|---|
| `app/modules/dashboard/service.py` | **New file** — stage chains, `_parse_date`, `_walk_chain`, PA/PAM item builders, `get_etf_dashboard_data()` |
| `app/modules/dashboard/routes.py` | ETF branch: drop `payment_memo` queries, call `get_etf_dashboard_data`; non-ETF branch keeps old stats |
| `app/templates/dashboard/index.html` | ETF branch: replace 2 dead cards with 4 KPI cards; add 2 action-list tables with row deep links |
| `app/templates/etf_payment_application/index.html` | Read `open_pa` URL param on load → scroll to row + click its Edit button |
| `app/templates/payment_memo/index.html` | Read `pam_pillar`/`pam_no` URL params on load → prefill pillar search box + activate pillar tab |

---

## Task 1: Dashboard service — stage walk + aggregation

**Files:**
- Create: `app/modules/dashboard/service.py`

**Interfaces:**
- Produces: `get_etf_dashboard_data(company_id) -> dict` — consumed by Task 2 (routes) and Task 3 (template). Returned keys: `pa_active_total, pa_open, pa_on_process, pam_open, paid_this_month, avg_age_days, pa_actions, pam_actions, pa_total_actions, pam_total_actions`

- [ ] **Step 1: Create `app/modules/dashboard/service.py` with this exact content**

```python
# modules/dashboard/service.py
from datetime import date
from database import get_conn

# (tab, pillar_label, pa_table, lines_table) — mirrors _TAB_CFG in
# modules/etf_payment_application/service.py
PA_SOURCES = [
    ("agri", "AGRI", "etf_pa",  "etf_pa_lines"),
    ("app",  "APP",  "app_pa",  "app_pa_lines"),
    ("sml",  "SML",  "sml_pa",  "sml_pa_lines"),
    ("setf", "SETF", "setf_pa", "setf_pa_lines"),
]

# pam_records.pillar → lines table — mirrors _PILLAR_LINES_TABLE in
# modules/payment_memo/service.py
PAM_LINES_TABLE = {
    "AGRI":   "agri_pam_lines",
    "APP":    "app_pam_lines",
    "LAND":   "land_pam_lines",
    "ENERGY": "energy_pam_lines",
    "SETF":   "setf_pam_lines",
}

# Ordered approval chains; label = the stage being WAITED ON when that
# column is the first empty one (approved spec Section 3).
PA_STAGE_CHAIN = [
    ("doc_received_by_educ",  "Dokumen diterima Educ"),
    ("received_pa_from_educ", "PA diterima dari Educ"),
    ("checked_by_fincon",     "Pengecekan Fincon"),
    ("approved_by_htj_1",     "Approval HTJ 1"),
    ("send_pa_back_to_educ",  "PA dikirim balik ke Educ"),
    ("pa_received_by_po_fin", "PA diterima PO Finance"),
    ("approval_by_htj_2",     "Approval HTJ 2"),
    ("tanggal_bayar",         "Menunggu pembayaran"),
]

PAM_LINE_CHAIN = [
    ("tgl_terima_doc",     "Terima dokumen"),
    ("tgl_proses",         "Proses"),
    ("tgl_verifikasi_tax", "Verifikasi tax"),
    ("tgl_approval_1",     "Approval 1"),
    ("tgl_approval_2",     "Approval 2"),
    ("tgl_approval_3",     "Approval 3"),
    ("tgl_kirim",          "Kirim"),
]


def _parse_date(val):
    """TEXT column → date, or None. Tolerates timestamps and junk."""
    if not val:
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except ValueError:
        return None


def _walk_chain(row: dict, chain) -> tuple:
    """Return (awaited_label, last_filled_date).

    awaited_label = label of the FIRST empty column in chain order
    (None if every column is filled). last_filled_date = MAX of all
    parseable filled dates (None if none parse)."""
    awaited = None
    last_filled = None
    for col, label in chain:
        val = row.get(col)
        if val in (None, ""):
            if awaited is None:
                awaited = label
        else:
            d = _parse_date(val)
            if d and (last_filled is None or d > last_filled):
                last_filled = d
    return awaited, last_filled


def _days_since(baseline, today) -> int:
    if baseline is None or baseline > today:
        return 0
    return (today - baseline).days


def _pa_actions(conn, company_id: int, today: date) -> list:
    items = []
    for tab, pillar, pa_tbl, lines_tbl in PA_SOURCES:
        rows = conn.execute(
            f"""SELECT p.*,
                       COUNT(l.id)                           AS jml_siswa,
                       COALESCE(SUM(l.jumlah_pembayaran), 0) AS total_bayar
                FROM {pa_tbl} p
                LEFT JOIN {lines_tbl} l ON l.pa_id = p.id
                WHERE p.company_id = ? AND p.status IN ('open','on_process')
                GROUP BY p.id""",
            (company_id,),
        ).fetchall()
        for r in rows:
            row = dict(r)
            awaited, last_filled = _walk_chain(row, PA_STAGE_CHAIN)
            baseline = (last_filled
                        or _parse_date(row.get("tgl_payment_application"))
                        or _parse_date(row.get("created_at")))
            items.append({
                "tab":       tab,
                "pillar":    pillar,
                "pa_id":     row["id"],
                "pa_number": row["pa_number"],
                "stage":     awaited or "Semua tanggal terisi",
                "days":      _days_since(baseline, today),
                "jml_siswa": row["jml_siswa"],
                "total":     row["total_bayar"],
                "status":    row["status"],
            })
    return items


def _pam_actions(conn, company_id: int, today: date) -> list:
    memos = [dict(r) for r in conn.execute(
        "SELECT * FROM pam_records WHERE company_id = ? AND status = 'open'",
        (company_id,),
    ).fetchall()]

    # Fetch open memos' vendor lines, grouped per memo id
    lines_by_memo = {}
    for pillar, tbl in PAM_LINES_TABLE.items():
        ids = [m["id"] for m in memos if (m.get("pillar") or "").upper() == pillar]
        if not ids:
            continue
        marks = ",".join("?" * len(ids))
        for lr in conn.execute(
            f"SELECT * FROM {tbl} WHERE pam_id IN ({marks})", ids
        ).fetchall():
            lines_by_memo.setdefault(lr["pam_id"], []).append(dict(lr))

    items = []
    for m in memos:
        lines = lines_by_memo.get(m["id"], [])
        memo_baseline = (_parse_date(m.get("pam_date"))
                         or _parse_date(m.get("created_at")))
        done = [l for l in lines if l.get("tgl_kirim") not in (None, "")]
        open_lines = [l for l in lines if l.get("tgl_kirim") in (None, "")]

        if not lines:
            stage, vendor = "Belum ada vendor line", ""
            days = _days_since(memo_baseline, today)
        elif open_lines:
            # Longest-stuck unfinished line wins (approved Section 3)
            worst = None
            for l in open_lines:
                awaited, last_filled = _walk_chain(l, PAM_LINE_CHAIN)
                d = _days_since(last_filled or memo_baseline, today)
                if worst is None or d > worst[0]:
                    worst = (d, awaited or "Kirim", l.get("nama_vendor") or "")
            days, stage, vendor = worst
        else:
            stage, vendor = "Menunggu pembayaran", ""
            kirim_dates = [d for d in (_parse_date(l.get("tgl_kirim")) for l in lines) if d]
            days = _days_since(max(kirim_dates) if kirim_dates else memo_baseline, today)

        items.append({
            "pam_id":       m["id"],
            "pam_no":       m["pam_no"],
            "pillar":       (m.get("pillar") or "").upper(),
            "keterangan":   m.get("keterangan") or m.get("requestors_name") or "",
            "vendor_done":  len(done),
            "vendor_total": len(lines),
            "stage":        stage,
            "vendor":       vendor,
            "days":         days,
            "total_amount": m.get("total_amount") or 0,
            "due_date":     m.get("due_date") or "",
        })
    return items


def get_etf_dashboard_data(company_id: int) -> dict:
    today = date.today()
    conn = get_conn()

    pa_items  = _pa_actions(conn, company_id, today)
    pam_items = _pam_actions(conn, company_id, today)

    paid_this_month = conn.execute(
        """SELECT COALESCE(SUM(total_amount), 0) FROM pam_records
           WHERE company_id = ? AND status = 'complete'
             AND substr(COALESCE(tanggal_bayar,''), 1, 7)
                 = strftime('%Y-%m', 'now', 'localtime')""",
        (company_id,),
    ).fetchone()[0]
    conn.close()

    sort_key = lambda it: (-it["days"], -(it["total"] if "total" in it else it["total_amount"]))
    pa_items.sort(key=sort_key)
    pam_items.sort(key=sort_key)

    all_ages = [it["days"] for it in pa_items] + [it["days"] for it in pam_items]
    avg_age  = round(sum(all_ages) / len(all_ages)) if all_ages else 0

    return {
        "pa_active_total":   len(pa_items),
        "pa_open":           sum(1 for it in pa_items if it["status"] == "open"),
        "pa_on_process":     sum(1 for it in pa_items if it["status"] == "on_process"),
        "pam_open":          len(pam_items),
        "paid_this_month":   paid_this_month,
        "avg_age_days":      avg_age,
        "pa_actions":        pa_items[:10],
        "pam_actions":       pam_items[:10],
        "pa_total_actions":  len(pa_items),
        "pam_total_actions": len(pam_items),
    }
```

- [ ] **Step 2: Smoke-test the service in a Python shell**

From `app/` with the venv active:

```bash
python - <<'EOF'
import sys; sys.path.insert(0, '.')
from modules.dashboard.service import get_etf_dashboard_data
d = get_etf_dashboard_data(2)
print('pa_active_total:', d['pa_active_total'])
print('pam_open:', d['pam_open'])
print('avg_age_days:', d['avg_age_days'])
print('top PA:', d['pa_actions'][0] if d['pa_actions'] else None)
print('top PAM:', d['pam_actions'][0] if d['pam_actions'] else None)
EOF
```

Expected against live data: `pa_active_total` ≈ 173 (101 open + 72 on_process), `pam_open` ≈ 29, non-zero `avg_age_days`, top items have `stage` labels from the chains and plausible `days`.

- [ ] **Step 3: Commit**

```bash
git add app/modules/dashboard/service.py
git commit -m "feat: dashboard service — PA/PAM stage-walk aggregation for ETF dashboard"
```

---

## Task 2: Dashboard routes — wire service, remove dead queries from ETF path

**Files:**
- Modify: `app/modules/dashboard/routes.py`

**Interfaces:**
- Consumes: `get_etf_dashboard_data` (Task 1)
- Produces: template context `dash` (dict or `None`) — consumed by Task 3

- [ ] **Step 1: Import the service**

After line 5 (`from database import get_conn`), add:

```python
from modules.dashboard.service import get_etf_dashboard_data
```

- [ ] **Step 2: Restructure `index()` — dead `payment_memo` queries only for non-ETF**

Replace the body of `index()` (lines 46–76) so the ETF branch no longer computes `total_memo`/`memo_draft` (the dead-card bugfix) and instead builds `dash`; the non-ETF (SMT) branch keeps the old stats unchanged:

```python
@bp.route("/dashboard")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))

    conn       = get_conn()
    company_id = session["company_id"]
    stats      = {}
    dash       = None

    if session.get("company_code") == "ETF":
        stats["total_siswa"]   = conn.execute(
            "SELECT COUNT(*) FROM siswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["siswa_aktif"]   = conn.execute(
            "SELECT COUNT(*) FROM siswa WHERE company_id = ? AND status = 'Aktif'", (company_id,)
        ).fetchone()[0]
        stats["total_budget"]  = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM budget_beasiswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["total_payment"] = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_beasiswa WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        conn.close()
        dash = get_etf_dashboard_data(company_id)
    else:
        stats["total_memo"] = conn.execute(
            "SELECT COUNT(*) FROM payment_memo WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        stats["memo_draft"] = conn.execute(
            "SELECT COUNT(*) FROM payment_memo WHERE company_id = ? AND status = 'open'", (company_id,)
        ).fetchone()[0]
        conn.close()

    return render_template("dashboard/index.html", stats=stats, dash=dash,
                           active_page="dashboard", **get_ctx())
```

- [ ] **Step 3: Verify the route still renders**

Start the dev server, log in, select ETF, open `/dashboard`. The page must render without a Jinja error (template still shows the old cards until Task 3 — `stats.total_memo` is now missing in the ETF branch, so **do Task 3 before reloading as ETF**, or accept the transient error here and verify after Task 3). For SMT: select SMT company → old two cards render exactly as before.

- [ ] **Step 4: Commit** (combined with Task 3 — see Task 3 Step 5, since the ETF template depends on this context change)

---

## Task 3: Dashboard template — 4 KPI cards + 2 action tables

**Files:**
- Modify: `app/templates/dashboard/index.html`

**Interfaces:**
- Consumes: `dash` context (Task 2), existing `.stat-card`/`.kpi-grid`/`.card`/`.thead-primary` CSS

- [ ] **Step 1: Replace the two dead cards in the ETF branch**

Delete lines 36–47 (the "Total Memo" and "Memo Draft" `stat-card` divs inside the `{% if company_code == 'ETF' %}` branch) and insert:

```html
  <div class="stat-card">
    <div class="stat-label">PA Aktif</div>
    <div class="stat-value" data-count="{{ dash.pa_active_total }}">{{ dash.pa_active_total }}</div>
    <div class="stat-sub">{{ dash.pa_open }} Open · {{ dash.pa_on_process }} On Process</div>
    <div class="stat-bar"></div>
  </div>
  <div class="stat-card caution">
    <div class="stat-label">PAM Terbuka</div>
    <div class="stat-value" style="color:var(--caution)" data-count="{{ dash.pam_open }}">{{ dash.pam_open }}</div>
    <div class="stat-sub">menunggu proses</div>
    <div class="stat-bar"></div>
  </div>
  <div class="stat-card positive">
    <div class="stat-label">Total Dibayar Bulan Ini</div>
    <div class="stat-value currency" data-count="{{ dash.paid_this_month }}" data-prefix="Rp ">Rp {{ "{:,.0f}".format(dash.paid_this_month) }}</div>
    <div class="stat-sub">PAM complete bulan berjalan</div>
    <div class="stat-bar"></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Rata-rata Umur Item Terbuka</div>
    <div class="stat-value" data-count="{{ dash.avg_age_days }}">{{ dash.avg_age_days }}</div>
    <div class="stat-sub">hari sejak pergerakan terakhir</div>
    <div class="stat-bar"></div>
  </div>
```

The non-ETF `{% else %}` branch (lines 49–64) stays untouched.

- [ ] **Step 2: Add the two action-list tables after the ETF `kpi-grid`**

Still inside the `{% if company_code == 'ETF' %}` branch, immediately after the closing `</div>` of `.kpi-grid`, add:

```html
<div class="card" style="margin-top:1.25rem">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;gap:.5rem;flex-wrap:wrap">
    <h2 style="font-size:1rem;font-weight:700;margin:0">PA Perlu Tindakan</h2>
    <a href="/etf-payment-application/" style="font-size:.8rem;font-weight:600">Lihat semua ({{ dash.pa_total_actions }}) →</a>
  </div>
  <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:12.5px">
      <thead class="thead-primary">
        <tr>
          <th style="padding:8px 10px;text-align:left">Pilar</th>
          <th style="padding:8px 10px;text-align:left">No. PA</th>
          <th style="padding:8px 10px;text-align:left">Stage ditunggu</th>
          <th style="padding:8px 10px;text-align:right">Hari</th>
          <th style="padding:8px 10px;text-align:right">Jml Siswa</th>
          <th style="padding:8px 10px;text-align:right">Total (Rp)</th>
          <th style="padding:8px 10px;text-align:left">Status</th>
        </tr>
      </thead>
      <tbody>
        {% for it in dash.pa_actions %}
        <tr style="cursor:pointer;border-bottom:1px solid var(--border)"
            onclick="window.location='/etf-payment-application/?tab={{ it.tab }}&sf=active&open_pa={{ it.pa_id }}'"
            title="Buka PA ini">
          <td style="padding:7px 10px"><span style="display:inline-block;padding:1px 8px;border-radius:99px;font-size:10.5px;font-weight:700;background:var(--bg-muted);border:1px solid var(--border)">{{ it.pillar }}</span></td>
          <td style="padding:7px 10px;font-family:var(--mono);font-size:11.5px;white-space:nowrap">{{ it.pa_number }}</td>
          <td style="padding:7px 10px">{{ it.stage }}</td>
          <td style="padding:7px 10px;text-align:right;font-weight:700">{{ it.days }}</td>
          <td style="padding:7px 10px;text-align:right">{{ it.jml_siswa }}</td>
          <td style="padding:7px 10px;text-align:right">{{ "{:,.0f}".format(it.total) }}</td>
          <td style="padding:7px 10px;white-space:nowrap">{{ 'On Process' if it.status == 'on_process' else 'Open' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="7" style="padding:16px;text-align:center;color:var(--text-muted)">Tidak ada PA aktif.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<div class="card" style="margin-top:1.25rem">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;gap:.5rem;flex-wrap:wrap">
    <h2 style="font-size:1rem;font-weight:700;margin:0">PAM Perlu Tindakan</h2>
    <a href="/payment-memo/" style="font-size:.8rem;font-weight:600">Lihat semua ({{ dash.pam_total_actions }}) →</a>
  </div>
  <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:12.5px">
      <thead class="thead-primary">
        <tr>
          <th style="padding:8px 10px;text-align:left">No. PAM</th>
          <th style="padding:8px 10px;text-align:left">Pilar</th>
          <th style="padding:8px 10px;text-align:left">Keterangan</th>
          <th style="padding:8px 10px;text-align:center">Vendor</th>
          <th style="padding:8px 10px;text-align:left">Stage terlama</th>
          <th style="padding:8px 10px;text-align:right">Hari</th>
          <th style="padding:8px 10px;text-align:right">Total (Rp)</th>
          <th style="padding:8px 10px;text-align:left">Due Date</th>
        </tr>
      </thead>
      <tbody>
        {% for it in dash.pam_actions %}
        <tr style="cursor:pointer;border-bottom:1px solid var(--border)"
            onclick="window.location='/payment-memo/?pam_pillar={{ it.pillar }}&pam_no={{ it.pam_no|urlencode }}'"
            title="Buka PAM ini">
          <td style="padding:7px 10px;font-family:var(--mono);font-size:11.5px;white-space:nowrap">{{ it.pam_no }}</td>
          <td style="padding:7px 10px"><span style="display:inline-block;padding:1px 8px;border-radius:99px;font-size:10.5px;font-weight:700;background:var(--bg-muted);border:1px solid var(--border)">{{ it.pillar }}</span></td>
          <td style="padding:7px 10px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{{ it.keterangan }}">{{ it.keterangan or '-' }}</td>
          <td style="padding:7px 10px;text-align:center;white-space:nowrap">{{ it.vendor_done }}/{{ it.vendor_total }} selesai</td>
          <td style="padding:7px 10px">{{ it.stage }}{% if it.vendor %} — {{ it.vendor }}{% endif %}</td>
          <td style="padding:7px 10px;text-align:right;font-weight:700">{{ it.days }}</td>
          <td style="padding:7px 10px;text-align:right">{{ "{:,.0f}".format(it.total_amount) }}</td>
          <td style="padding:7px 10px;white-space:nowrap">{{ it.due_date or '-' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="8" style="padding:16px;text-align:center;color:var(--text-muted)">Tidak ada PAM terbuka.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
```

- [ ] **Step 3: Verify in browser (ETF)**

Open `/dashboard` as ETF:
1. 8 KPI cards render: Budget, Payment, Siswa, Aktif (unchanged) + PA Aktif (~173, "101 Open · 72 On Process"), PAM Terbuka (~29), Total Dibayar Bulan Ini (Rp), Rata-rata Umur
2. "PA Perlu Tindakan" shows ≤10 rows sorted by Hari desc; pillar badges AGRI/APP only expected with live data
3. "PAM Perlu Tindakan" shows ≤10 rows with "N/M selesai" and stage — vendor name for stuck lines
4. Dark mode: no hardcoded-color glitches in tables/badges
5. "Lihat semua" links navigate to `/etf-payment-application/` and `/payment-memo/`

- [ ] **Step 4: Verify in browser (SMT)**

Switch company to SMT → dashboard shows the old Total Memo / Memo Draft cards, no errors.

- [ ] **Step 5: Commit (Tasks 2+3 together)**

```bash
git add app/modules/dashboard/routes.py app/templates/dashboard/index.html
git commit -m "feat: ETF dashboard — real KPI cards + PA/PAM action lists (fixes dead payment_memo cards)"
```

---

## Task 4: PA deep-link — `open_pa` auto-opens the Edit modal

**Files:**
- Modify: `app/templates/etf_payment_application/index.html`

**Interfaces:**
- Consumes: dashboard links `/etf-payment-application/?tab=<tab>&sf=active&open_pa=<pa_id>` (Task 3); existing `openEditById(paId, lineId)` and `tr[data-pa-id]` rows

**Context:** The list renders one `<tr data-pa-id="{{ r.pa_id }}">` per PA *line*; each row's Edit button calls `openEditById(pa_id, line_id)`. The deep link only knows `pa_id`, so we click the **first** matching row's Edit button — this reuses the exact existing code path (correct `lineId`, `ACTIVE_TAB` already set server-side from `?tab=`).

- [ ] **Step 1: Add the param reader at the bottom of `{% block scripts %}`**

In `app/templates/etf_payment_application/index.html`, inside the scripts block (before the closing `</script>`), add:

```javascript
/* Deep link from dashboard: ?open_pa=<pa_id> auto-opens that PA's edit modal */
document.addEventListener('DOMContentLoaded', function () {
  const openPa = new URLSearchParams(window.location.search).get('open_pa');
  if (!openPa) return;
  const tr = document.querySelector(`#pa-table tbody tr[data-pa-id="${CSS.escape(openPa)}"]`);
  if (!tr) return;
  tr.scrollIntoView({ block: 'center' });
  const btn = tr.querySelector("button[onclick^='openEditById']");
  if (btn) btn.click();
});
```

(Registered after app.js's `DOMContentLoaded` listener — `app.js` is included earlier in `base.html` — so it runs after the page's own init.)

- [ ] **Step 2: Verify in browser**

1. From the ETF dashboard, click a "PA Perlu Tindakan" row → lands on `/etf-payment-application/?tab=<pilar>&sf=active&open_pa=<id>`, the list shows the Active filter, the page scrolls to the row, and the "Edit PA" modal opens pre-filled with the 7 stage-date fields
2. Edit a stage date, save → toast success; reload dashboard → that item's "Hari"/stage updated
3. Open `/etf-payment-application/?tab=agri` with no `open_pa` → no JS errors, no modal

- [ ] **Step 3: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: PA deep link — open_pa param auto-opens edit modal from dashboard"
```

---

## Task 5: PAM deep-link — `pam_pillar`/`pam_no` lands on the pillar tab, filtered

**Files:**
- Modify: `app/templates/payment_memo/index.html`

**Interfaces:**
- Consumes: dashboard links `/payment-memo/?pam_pillar=<PILLAR>&pam_no=<no>` (Task 3); existing tab buttons (`tab-pam`/`tab-fiori`/`tab-sml`/`tab-setf`), search inputs (`pam-search`/`fiori-search`/`sml-search`/`setf-search`), and `loadPAM/loadFIORI/loadSML/loadSETF` (each reads its search input; server filters `pr.pam_no LIKE`)

**Context:** Vendor-line stage dates are edited **inline** in the pillar tabs (via `_plDate` cells → `pamLineDateEdit`), not in a modal — so the "editable record" target for a PAM is its pillar tab filtered down to that memo. Clicking the tab button triggers its `onclick` loader, which reads the (pre-filled) search input.

- [ ] **Step 1: Add the param reader at the bottom of `{% block scripts %}`**

In `app/templates/payment_memo/index.html`, inside the scripts block (before the closing `</script>`), add:

```javascript
/* Deep link from dashboard: ?pam_pillar=AGRI&pam_no=... lands on the pillar
   tab with the search pre-filtered to that memo's rows (inline-editable). */
document.addEventListener('DOMContentLoaded', function () {
  const params = new URLSearchParams(window.location.search);
  const pillar = (params.get('pam_pillar') || '').toUpperCase();
  if (!pillar) return;
  const cfg = {
    AGRI: ['tab-pam',   'pam-search'],
    APP:  ['tab-fiori', 'fiori-search'],
    LAND: ['tab-sml',   'sml-search'],
    SETF: ['tab-setf',  'setf-search'],
  }[pillar];
  if (!cfg) return;
  const pamNo = params.get('pam_no') || '';
  const inp = document.getElementById(cfg[1]);
  if (inp && pamNo) inp.value = pamNo;
  document.querySelector(`[data-tab="${cfg[0]}"]`)?.click();
});
```

(Same ordering guarantee as Task 4: runs after `initTabs` has attached handlers and defaulted to the first tab.)

- [ ] **Step 2: Verify in browser**

1. From the ETF dashboard, click a "PAM Perlu Tindakan" row (AGRI) → lands on `/payment-memo/`, AGRI tab active, search box shows the pam_no, table shows only that memo's vendor-line rows
2. Click a stage-date cell → inline date editor opens; save → toast "Tersimpan"; reload dashboard → item's Hari/stage/progress updated
3. Repeat for an APP memo → tab-fiori activates and filters
4. Open `/payment-memo/` with no params → Open PAM tab active as before, no JS errors

- [ ] **Step 3: Commit and push**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: PAM deep link — pam_pillar/pam_no params land on filtered pillar tab"
git push -u origin claude/etf-dashboard-design-pmconl
```

---

## Self-Review Checklist

### Spec Coverage

| Spec item | Task |
|---|---|
| §2 KPI: PA Aktif / PAM Terbuka / Total Dibayar Bulan Ini / Rata-rata Umur | T1 (data) + T3 (cards) |
| §2 dead-card removal (`payment_memo` queries) from ETF path | T2 |
| §3 stage-walk algorithm (first-empty column, MAX filled date, fallbacks) | T1 `_walk_chain` + baselines |
| §3 PAM aggregation (longest unfinished line, N/M selesai, edge cases) | T1 `_pam_actions` |
| §3 two tables, top 10, columns, sort days↓ then total↓ | T1 sort + T3 tables |
| §4 row click → editable record (PA modal / PAM inline cells) | T4 + T5 |
| §4 "lihat semua" links | T3 (headers of both cards) |
| §5 Python aggregation, no new views, defensive TEXT-date parsing | T1 |
| §1 SMT unchanged | T2 else-branch + T3 else-branch untouched |

### Deviations from spec (agreed working names refined during planning)

- Spec §4 used working params `?view=open-pam&open_pam=<id>`; planning found PAM vendor-line dates are edited **inline in pillar tabs**, not a modal — so the deep link became `?pam_pillar=<PILLAR>&pam_no=<no>` targeting the pillar tab filtered to the memo. Behavior approved in §4 (one click → editable record) is preserved.
- PAM "lihat semua" target is `/payment-memo/` — the Open PAM tab is already the default first tab, so no extra param is needed.

### Placeholder Scan

- No TBDs/TODOs; all code shown in full
- Pillar/tab/search-input mappings are exact string literals verified against `payment_memo/index.html` (lines 94–100) and `etf_payment_application/service.py` `_TAB_CFG`

### Type Consistency

- `get_etf_dashboard_data(company_id: int) -> dict` — keys consumed by name in `dashboard/index.html`; `dash` is `None` for non-ETF (template only dereferences it inside the ETF branch)
- `_walk_chain(row: dict, chain) -> (str|None, date|None)` — shared by PA and PAM paths
- Action item dicts: PA uses `total`, PAM uses `total_amount` — the shared sort lambda handles both keys

---

## Files Changed Summary

| File | Task |
|---|---|
| `app/modules/dashboard/service.py` (new) | T1 |
| `app/modules/dashboard/routes.py` | T2 |
| `app/templates/dashboard/index.html` | T3 |
| `app/templates/etf_payment_application/index.html` | T4 |
| `app/templates/payment_memo/index.html` | T5 |

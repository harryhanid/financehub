# FLOW Backup Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace FLOW's narrow, PA-only Excel backup job with a registry-driven system that backs up every module/sub-module that already has a working `.xlsx` export, organized by company, plus a daily SQLite database backup — all on the existing weekday 17:00 schedule.

**Architecture:** A single `BACKUP_REGISTRY` list in `app/tasks/flow_backup.py` maps (company, module, sub-module) → an export function that returns `bytes`. One orchestrator function walks the registry, writes each result to `Y:\Seagate\Flow\<Company Name>\<Module>\<Sub-module>\<date>.xlsx`, and prunes files older than the retention window. A sibling function copies the live SQLite file to `Y:\Seagate\Flow\Dsqlite Backup\`. Both are wired into the APScheduler job that already exists in `app.py`.

**Tech Stack:** Python 3, Flask, APScheduler (already a dependency), pytest, `openpyxl` (already used by every export function this plan calls — no new dependency).

## Global Constraints

- Backup root: `Y:\Seagate\Flow` (was `Y:\Seagate\Harry\8. Backup\2. Financehub\2.1 Payment Application`).
- Folder layout: `<company name>\<module>\<sub-module>\<YYYY-MM-DD>.xlsx` — company names come from `config.COMPANIES` (`"Sinar Mas Tjipta"`, `"Eka Tjipta Foundation"`), exactly as already defined in `config.py:29-32`.
- Retention: Excel backups keep the last 5 days; SQLite backups keep the last 10 days. Cutoff logic: delete a dated file if `(today - file_date).days > keep_days` (matches the exact semantics of the retention logic already in production, in `app/tasks/excel_backup.py`).
- SQLite backup location: `Y:\Seagate\Flow\Dsqlite Backup\finance_hub_<YYYY-MM-DD>.db`.
- Schedule: unchanged — weekdays only, 17:00, via the existing APScheduler `BackgroundScheduler` cron job in `app.py`.
- The old job (writing to `Y:\Seagate\Harry\...\2.1 Payment Application\`) is fully replaced, not run in parallel. `app/tasks/excel_backup.py` is deleted once the new job is verified working.
- Every export call in the registry is isolated in its own `try/except` — one failing export must not prevent the others from running.
- No new modules are added to the registry beyond what's listed below — Budget and the rest of Beasiswa (Data Siswa, Data Budget, Data Payment, Report Siswa, Dashboard BI, Rekam Medis) are explicitly out of scope for this plan; they get their own plan once their own `.xlsx` builders exist.

## Confirmed Registry Contents

Verified directly against the current codebase (routes, service signatures, and the live JS that wires each tab's "Export Excel" button) — not assumptions:

| Company | Module | Sub-module | Export function |
|---|---|---|---|
| ETF | Bank | Mutasi & Saldo | `modules.bank.reports.build_laporan_mutasi_excel(company_id)` |
| ETF | Payment Approval Memo | Open PAM | `modules.payment_memo.exports.export_open_pam_excel(company_id)` |
| ETF | Payment Approval Memo | Advance | `modules.payment_memo.exports.export_pam_tab_excel(company_id, pillar="ADVANCE")` |
| ETF | Payment Approval Memo | AGRI | `export_pam_tab_excel(company_id, pillar="AGRI")` |
| ETF | Payment Approval Memo | APP | `export_pam_tab_excel(company_id, pillar="APP")` |
| ETF | Payment Approval Memo | LAND | `export_pam_tab_excel(company_id, pillar="LAND")` |
| ETF | Payment Approval Memo | SETF | `export_pam_tab_excel(company_id, pillar="SETF")` |
| ETF | Payment Application | AGRI | `modules.etf_payment_application.service.export_pa_excel(company_id, tab="agri")` |
| ETF | Payment Application | APP | `export_pa_excel(company_id, tab="app")` |
| ETF | Payment Application | LAND | `export_pa_excel(company_id, tab="sml")` — internal tab key is `"sml"`, display name is "LAND" |
| ETF | Payment Application | SETF | `export_pa_excel(company_id, tab="setf")` |
| ETF | Beasiswa | Sahabat ETF | `build_report_workbook(build_report_data(company_id, year))` — `year` = latest from `modules.sahabat_etf.service.get_available_years(company_id)`, else current year |
| SMT | Payment Approval Memo | Open PAM | `export_open_pam_excel(company_id)` |
| SMT | Payment Approval Memo | Advance | `export_pam_tab_excel(company_id, pillar="ADVANCE")` |
| SMT | Payment Approval Memo | PAM List | `export_pam_tab_excel(company_id, pillar="SMT")` |
| SMT | Sponsorship | Report | `modules.sponsorship.exports.export_report_excel(company_id, tahun, "all")` — `tahun` = latest from `modules.sponsorship.service.get_available_years(company_id)`, else current year (as string) |

Notes on what was ruled out and why:
- **Bank** and **Payment Application** (`etf_payment_application`) are ETF-only in practice: their underlying tables (`bank_setf`, `etf_pa`/`app_pa`/`sml_pa`/`setf_pa`) and report titles are ETF/SETF-pillar-specific, even though the routes have no explicit company gate. No SMT entries exist for them.
- The separate `/payment-application` blueprint (`modules/payment_application`) is dead code — not linked from any nav or `DASHBOARD_TABS` entry (confirmed both by reading `app.py`'s `inject_nav_modules()` and by the prior `2026-07-29-flow-unified-header-navigation-design.md` spec, which flagged the same thing). Not included.
- `export_fiori_excel` / `export_sml_excel` / `export_sla_excel` (in `modules/payment_memo/exports.py`) are superseded dead code — the live "Export Excel" buttons in `templates/payment_memo/index.html` all call `exportPillarExcel(pillar)` (line 5810), which always hits `/payment-memo/export/pam?pillar=...` → `export_pam_tab_excel`. The old excel-only functions are not used by this plan.
- The pre-existing production bug where `excel_backup.py` looped `["agri", "app", "land"]` against `export_pa_excel`'s actual tab keys (`agri`/`app`/`sml`/`setf`) — meaning "land" silently fell back to re-exporting AGRI data — is fixed here by using the correct key `"sml"`.

## File Structure

- **Modify** `app/config.py` — add `BACKUP_ROOT`.
- **Create** `app/tasks/flow_backup.py` — registry, orchestrator, SQLite backup, retention helper. Replaces `app/tasks/excel_backup.py`.
- **Delete** `app/tasks/excel_backup.py` — once the new job is verified (Task 4).
- **Modify** `app/app.py` — point the existing scheduler job at `run_flow_backups` instead of `run_excel_backups`.
- **Modify** `scripts/run_backup_now.py` — manual trigger, updated to call the new entry point.
- **Create** `app/tests/test_flow_backup.py` — all automated coverage for the above.

---

### Task 1: Retention helper + config

**Files:**
- Modify: `app/config.py`
- Create: `app/tasks/flow_backup.py`
- Test: `app/tests/test_flow_backup.py`

**Interfaces:**
- Produces: `config.BACKUP_ROOT: str`; `tasks.flow_backup._cleanup_old_files(folder: str, keep_days: int, prefix: str = "", suffix: str = "") -> None`

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_flow_backup.py`:

```python
import os
import datetime
from tasks.flow_backup import _cleanup_old_files


def test_cleanup_keeps_recent_and_removes_old_files(tmp_path):
    today = datetime.datetime.now()
    recent = today - datetime.timedelta(days=3)
    old = today - datetime.timedelta(days=8)

    recent_path = tmp_path / f"{recent.strftime('%Y-%m-%d')}.xlsx"
    old_path = tmp_path / f"{old.strftime('%Y-%m-%d')}.xlsx"
    recent_path.write_text("recent")
    old_path.write_text("old")

    _cleanup_old_files(str(tmp_path), keep_days=5)

    assert recent_path.exists()
    assert not old_path.exists()


def test_cleanup_ignores_files_that_dont_match_date_pattern(tmp_path):
    junk_path = tmp_path / "not-a-date.xlsx"
    junk_path.write_text("junk")

    _cleanup_old_files(str(tmp_path), keep_days=5)

    assert junk_path.exists()


def test_cleanup_handles_prefix_and_suffix_for_sqlite_naming(tmp_path):
    today = datetime.datetime.now()
    old = today - datetime.timedelta(days=15)

    recent_path = tmp_path / f"finance_hub_{today.strftime('%Y-%m-%d')}.db"
    old_path = tmp_path / f"finance_hub_{old.strftime('%Y-%m-%d')}.db"
    recent_path.write_text("recent")
    old_path.write_text("old")

    _cleanup_old_files(str(tmp_path), keep_days=10, prefix="finance_hub_", suffix=".db")

    assert recent_path.exists()
    assert not old_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tasks.flow_backup'`

- [ ] **Step 3: Write minimal implementation**

Add to `app/config.py` (after the `DB_PATH` line at `config.py:6`):

```python
BACKUP_ROOT = r"Y:\Seagate\Flow"
```

Create `app/tasks/flow_backup.py`:

```python
# tasks/flow_backup.py
import os
import datetime
import shutil
import traceback

import config


def _cleanup_old_files(folder: str, keep_days: int, prefix: str = "", suffix: str = "") -> None:
    """Delete dated files in `folder` older than `keep_days`.

    Files are expected to be named `<prefix><YYYY-MM-DD><suffix>`. Anything that
    doesn't parse as a date after stripping prefix/suffix is left alone.
    """
    if not os.path.exists(folder):
        return
    now = datetime.datetime.now()
    for fname in os.listdir(folder):
        full_path = os.path.join(folder, fname)
        if not os.path.isfile(full_path):
            continue
        stem = fname
        if suffix and stem.endswith(suffix):
            stem = stem[: -len(suffix)]
        elif suffix:
            continue
        if prefix and stem.startswith(prefix):
            stem = stem[len(prefix):]
        elif prefix:
            continue
        try:
            file_date = datetime.datetime.strptime(stem, "%Y-%m-%d")
        except ValueError:
            continue
        if (now - file_date).days > keep_days:
            os.remove(full_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/config.py app/tasks/flow_backup.py app/tests/test_flow_backup.py
git commit -m "feat: add FLOW backup retention helper and BACKUP_ROOT config"
```

---

### Task 2: Backup registry + Excel orchestrator

**Files:**
- Modify: `app/tasks/flow_backup.py`
- Test: `app/tests/test_flow_backup.py`

**Interfaces:**
- Consumes: `_cleanup_old_files(folder, keep_days, prefix="", suffix="")` from Task 1; `config.BACKUP_ROOT: str`; `config.COMPANIES: list[dict]` (each `{"id": int, "code": str, "name": str}`, from `config.py:29-32`)
- Produces: `tasks.flow_backup.BACKUP_REGISTRY: list[dict]` (each `{"company": str, "module": str, "submodule": str, "export_fn": Callable[[int], bytes]}`); `tasks.flow_backup.run_excel_backups() -> None`

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_flow_backup.py`:

```python
import tasks.flow_backup as flow_backup


def test_run_excel_backups_writes_files_for_every_registry_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    flow_backup.run_excel_backups()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    for entry in flow_backup.BACKUP_REGISTRY:
        company_name = next(c["name"] for c in config.COMPANIES if c["code"] == entry["company"])
        expected = tmp_path / company_name / entry["module"] / entry["submodule"] / f"{today_str}.xlsx"
        assert expected.exists(), f"missing backup for {entry['company']}/{entry['module']}/{entry['submodule']}"
        assert expected.stat().st_size > 0


def test_one_failing_entry_does_not_block_the_rest(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))

    def _broken(company_id):
        raise RuntimeError("simulated export failure")

    fake_registry = [
        {"company": "ETF", "module": "Broken", "submodule": "Sub", "export_fn": _broken},
        {"company": "ETF", "module": "Working", "submodule": "Sub", "export_fn": lambda cid: b"ok"},
    ]
    monkeypatch.setattr(flow_backup, "BACKUP_REGISTRY", fake_registry)
    flow_backup.run_excel_backups()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    working_file = tmp_path / "Eka Tjipta Foundation" / "Working" / "Sub" / f"{today_str}.xlsx"
    broken_dir = tmp_path / "Eka Tjipta Foundation" / "Broken" / "Sub"
    assert working_file.exists()
    assert working_file.read_bytes() == b"ok"
    assert not broken_dir.exists() or not any(broken_dir.iterdir())
```

Add `import config` at the top of `app/tests/test_flow_backup.py`, alongside the `import os`/`import datetime` lines from Task 1 (Task 1's test code never referenced `config` directly, so this import is new here).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v -k "excel_backups or failing_entry"`
Expected: FAIL with `AttributeError: module 'tasks.flow_backup' has no attribute 'BACKUP_REGISTRY'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/tasks/flow_backup.py`:

```python
def _pam_pillar_export(pillar: str):
    def _fn(company_id: int) -> bytes:
        from modules.payment_memo.exports import export_pam_tab_excel
        return export_pam_tab_excel(company_id, pillar=pillar)
    return _fn


def _pa_tab_export(tab: str):
    def _fn(company_id: int) -> bytes:
        from modules.etf_payment_application.service import export_pa_excel
        return export_pa_excel(company_id, tab=tab)
    return _fn


def _open_pam_export(company_id: int) -> bytes:
    from modules.payment_memo.exports import export_open_pam_excel
    return export_open_pam_excel(company_id)


def _bank_mutasi_export(company_id: int) -> bytes:
    from modules.bank.reports import build_laporan_mutasi_excel
    return build_laporan_mutasi_excel(company_id)


def _sahabat_etf_report_export(company_id: int) -> bytes:
    from modules.sahabat_etf.service import get_available_years, build_report_data
    from modules.sahabat_etf.report_xlsx import build_report_workbook
    years = get_available_years(company_id)
    year = int(years[0]) if years else datetime.datetime.now().year
    data = build_report_data(company_id, year)
    return build_report_workbook(data)


def _sponsorship_report_export(company_id: int) -> bytes:
    from modules.sponsorship.service import get_available_years
    from modules.sponsorship.exports import export_report_excel
    years = get_available_years(company_id)
    tahun = years[0] if years else str(datetime.datetime.now().year)
    return export_report_excel(company_id, tahun, "all")


BACKUP_REGISTRY = [
    {"company": "ETF", "module": "Bank", "submodule": "Mutasi & Saldo", "export_fn": _bank_mutasi_export},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "Open PAM", "export_fn": _open_pam_export},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "Advance", "export_fn": _pam_pillar_export("ADVANCE")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "AGRI", "export_fn": _pam_pillar_export("AGRI")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "APP", "export_fn": _pam_pillar_export("APP")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "LAND", "export_fn": _pam_pillar_export("LAND")},
    {"company": "ETF", "module": "Payment Approval Memo", "submodule": "SETF", "export_fn": _pam_pillar_export("SETF")},
    {"company": "ETF", "module": "Payment Application", "submodule": "AGRI", "export_fn": _pa_tab_export("agri")},
    {"company": "ETF", "module": "Payment Application", "submodule": "APP", "export_fn": _pa_tab_export("app")},
    {"company": "ETF", "module": "Payment Application", "submodule": "LAND", "export_fn": _pa_tab_export("sml")},
    {"company": "ETF", "module": "Payment Application", "submodule": "SETF", "export_fn": _pa_tab_export("setf")},
    {"company": "ETF", "module": "Beasiswa", "submodule": "Sahabat ETF", "export_fn": _sahabat_etf_report_export},
    {"company": "SMT", "module": "Payment Approval Memo", "submodule": "Open PAM", "export_fn": _open_pam_export},
    {"company": "SMT", "module": "Payment Approval Memo", "submodule": "Advance", "export_fn": _pam_pillar_export("ADVANCE")},
    {"company": "SMT", "module": "Payment Approval Memo", "submodule": "PAM List", "export_fn": _pam_pillar_export("SMT")},
    {"company": "SMT", "module": "Sponsorship", "submodule": "Report", "export_fn": _sponsorship_report_export},
]


def run_excel_backups() -> None:
    companies = {c["code"]: c for c in config.COMPANIES}
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    for entry in BACKUP_REGISTRY:
        label = f"{entry['company']}/{entry['module']}/{entry['submodule']}"
        try:
            company = companies[entry["company"]]
            target_dir = os.path.join(config.BACKUP_ROOT, company["name"], entry["module"], entry["submodule"])
            os.makedirs(target_dir, exist_ok=True)

            xlsx_bytes = entry["export_fn"](company["id"])

            filepath = os.path.join(target_dir, f"{today_str}.xlsx")
            with open(filepath, "wb") as f:
                f.write(xlsx_bytes)

            print(f"[FLOW Backup] OK: {label}")
            _cleanup_old_files(target_dir, keep_days=5)
        except Exception as e:
            print(f"[FLOW Backup] ERROR {label}: {e}")
            traceback.print_exc()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v`
Expected: PASS (5 tests — the 3 from Task 1 plus these 2)

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/tasks/flow_backup.py app/tests/test_flow_backup.py
git commit -m "feat: add FLOW backup registry covering all xlsx-ready modules"
```

---

### Task 3: SQLite backup + combined entry point

**Files:**
- Modify: `app/tasks/flow_backup.py`
- Test: `app/tests/test_flow_backup.py`

**Interfaces:**
- Consumes: `_cleanup_old_files` (Task 1); `config.BACKUP_ROOT`, `config.DB_PATH`
- Produces: `tasks.flow_backup.run_sqlite_backup() -> None`; `tasks.flow_backup.run_flow_backups() -> None`

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_flow_backup.py`:

```python
def test_run_sqlite_backup_copies_db_to_dsqlite_backup_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    flow_backup.run_sqlite_backup()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    expected = tmp_path / "Dsqlite Backup" / f"finance_hub_{today_str}.db"
    assert expected.exists()
    assert expected.read_bytes() == open(config.DB_PATH, "rb").read()


def test_run_sqlite_backup_prunes_files_older_than_ten_days(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    backup_dir = tmp_path / "Dsqlite Backup"
    backup_dir.mkdir(parents=True)
    old_date = datetime.datetime.now() - datetime.timedelta(days=11)
    old_file = backup_dir / f"finance_hub_{old_date.strftime('%Y-%m-%d')}.db"
    old_file.write_text("stale backup")

    flow_backup.run_sqlite_backup()

    assert not old_file.exists()


def test_run_flow_backups_runs_both_excel_and_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_ROOT", str(tmp_path))
    flow_backup.run_flow_backups()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    assert (tmp_path / "Dsqlite Backup" / f"finance_hub_{today_str}.db").exists()
    assert (tmp_path / "Eka Tjipta Foundation" / "Bank" / "Mutasi & Saldo" / f"{today_str}.xlsx").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v -k "sqlite or run_flow_backups"`
Expected: FAIL with `AttributeError: module 'tasks.flow_backup' has no attribute 'run_sqlite_backup'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/tasks/flow_backup.py`:

```python
def run_sqlite_backup() -> None:
    try:
        target_dir = os.path.join(config.BACKUP_ROOT, "Dsqlite Backup")
        os.makedirs(target_dir, exist_ok=True)

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        dest = os.path.join(target_dir, f"finance_hub_{today_str}.db")
        shutil.copy2(config.DB_PATH, dest)

        print(f"[FLOW Backup] SQLite backup OK: {dest}")
        _cleanup_old_files(target_dir, keep_days=10, prefix="finance_hub_", suffix=".db")
    except Exception as e:
        print(f"[FLOW Backup] SQLite backup ERROR: {e}")
        traceback.print_exc()


def run_flow_backups() -> None:
    run_excel_backups()
    run_sqlite_backup()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v`
Expected: PASS (8 tests total)

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/tasks/flow_backup.py app/tests/test_flow_backup.py
git commit -m "feat: add FLOW SQLite backup and combined run_flow_backups entry point"
```

---

### Task 4: Scheduler cutover + retire the old job

**Files:**
- Modify: `app/app.py:97-116`
- Modify: `scripts/run_backup_now.py`
- Delete: `app/tasks/excel_backup.py`
- Test: `app/tests/test_flow_backup.py`

**Interfaces:**
- Consumes: `tasks.flow_backup.run_flow_backups` (Task 3)

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_flow_backup.py`:

```python
def test_app_module_no_longer_imports_the_old_excel_backup_task():
    import app as app_module
    source = open(app_module.__file__).read()
    assert "tasks.excel_backup" not in source
    assert "run_flow_backups" in source


def test_old_excel_backup_module_is_removed():
    import importlib
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("tasks.excel_backup")
```

Add `import pytest` at the top of `app/tests/test_flow_backup.py`, alongside the imports added in Tasks 1-3 (`os`, `datetime`, `config`, `tasks.flow_backup as flow_backup`) — `pytest` itself was only ever used implicitly via fixtures (`tmp_path`, `monkeypatch`) until now, so this is a new explicit import.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v -k "old_excel_backup or app_module"`
Expected: FAIL — `test_app_module_no_longer_imports_the_old_excel_backup_task` fails because `app.py` still references `tasks.excel_backup`; `test_old_excel_backup_module_is_removed` fails because the module still imports successfully.

- [ ] **Step 3: Write minimal implementation**

In `app/app.py`, replace the scheduler block (currently lines 97-116):

```python
        # --- Scheduler Setup ---
        import os
        # Ensure we only run scheduler in the main werkzeug process if reloading, or if debug is off
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                from tasks.excel_backup import run_excel_backups

                scheduler = BackgroundScheduler()

                def scheduled_backup_job():
                    with app.app_context():
                        run_excel_backups()

                # Run at 17:00 on Mon-Fri
                scheduler.add_job(func=scheduled_backup_job, trigger="cron", day_of_week="mon-fri", hour=17, minute=0)
                scheduler.start()
                app.logger.info("APScheduler started successfully.")
            except ImportError:
                app.logger.warning("APScheduler is not installed. Background tasks will not run.")
```

with:

```python
        # --- Scheduler Setup ---
        import os
        # Ensure we only run scheduler in the main werkzeug process if reloading, or if debug is off
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                from tasks.flow_backup import run_flow_backups

                scheduler = BackgroundScheduler()

                def scheduled_backup_job():
                    with app.app_context():
                        run_flow_backups()

                # Run at 17:00 on Mon-Fri
                scheduler.add_job(func=scheduled_backup_job, trigger="cron", day_of_week="mon-fri", hour=17, minute=0)
                scheduler.start()
                app.logger.info("APScheduler started successfully.")
            except ImportError:
                app.logger.warning("APScheduler is not installed. Background tasks will not run.")
```

Replace the full contents of `scripts/run_backup_now.py`:

```python
import os
import sys

# Tambahkan folder 'app' ke system path agar bisa import modul Flask
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(base_dir, 'app')
sys.path.insert(0, app_dir)

from app import create_app
from tasks.flow_backup import run_flow_backups

if __name__ == "__main__":
    print("Mempersiapkan manual backup FLOW...")
    app = create_app()
    with app.app_context():
        run_flow_backups()
    print("Selesai! Silakan cek Y:\\Seagate\\Flow.")
```

Delete `app/tasks/excel_backup.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_flow_backup.py -v`
Expected: PASS (10 tests total)

Also run the full existing suite to confirm no regression:
Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan (pre-existing failures listed in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault are unrelated Windows SQLite file-lock flakiness, not caused by this change).

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/app.py scripts/run_backup_now.py app/tests/test_flow_backup.py
git rm app/tasks/excel_backup.py
git commit -m "feat: cut FLOW backup scheduler over to run_flow_backups, retire old PA-only job"
```

- [ ] **Step 6: Manual verification against the real Y: drive**

This step writes real files to `Y:\Seagate\Flow` — confirm with the user before running it unattended.

Run: `cd C:\Financehub && python scripts\run_backup_now.py`

Expected: console prints one `[FLOW Backup] OK: ...` line per registry entry (16 lines) with no `ERROR` lines, then one `[FLOW Backup] SQLite backup OK: ...` line. Then manually inspect `Y:\Seagate\Flow` and confirm:
- `Sinar Mas Tjipta\` and `Eka Tjipta Foundation\` folders exist with the module/sub-module structure from the registry table above.
- `Dsqlite Backup\finance_hub_<today>.db` exists and opens correctly.
- Each `.xlsx` file opens in Excel and shows real data for pillars/tabs that have data in the live database.

## Out of Scope (tracked for follow-up plans)

- Building `.xlsx` export functions for Budget (currently CSV-only: transactions, realization, department, expired, compliance reports).
- Building `.xlsx`/wiring backup for the rest of Beasiswa: Data Siswa, Data Budget, Data Payment, Report Siswa (currently CSV/PDF), and Dashboard BI + Rekam Medis (no export today).
- Any failure notification (Telegram/email) — this plan logs to console/app log only.
- Cleaning up files already sitting in the old `Y:\Seagate\Harry\8. Backup\2. Financehub\2.1 Payment Application\` path.

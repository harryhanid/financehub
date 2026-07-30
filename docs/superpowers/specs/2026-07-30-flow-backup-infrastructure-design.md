# FLOW Backup Infrastructure — Design

## Problem

FLOW already has one automated backup job (`app/tasks/excel_backup.py`), but its scope
is narrow and its layout doesn't generalize:

- Only exports 3 tabs of one module (ETF Payment Application: AGRI/APP/LAND).
- Writes to `Y:\Seagate\Harry\8. Backup\2. Financehub\2.1 Payment Application\YYYY-MM-DD\`
  — a personal, module-specific path that doesn't scale to the rest of FLOW.
- Folders are organized **by date**, not by module — finding "last Tuesday's Bank ledger"
  means opening a dated folder and hunting for the right file, not going straight to a
  Bank folder.
- No backup of the SQLite database itself exists anywhere.

FLOW now has 7 top-level modules (Beasiswa, Payment Approval Memo, Payment Application,
Budget, Bank, Sponsorship, Users), most with their own sub-modules/tabs, spread across
two companies (Sinar Mas Tjipta / SMT, Eka Tjipta Foundation / ETF). None of that is
covered today except the 3 PA tabs.

## Goal

Replace the existing narrow job with a general-purpose backup system that:

1. Exports every module/sub-module that already has a working Excel export function to
   `.xlsx`, organized in a folder tree by **company → module → sub-module**.
2. Also makes a full copy of the SQLite database file on the same schedule.
3. Runs automatically once a day on the existing schedule (weekdays, 17:00), fully
   replacing the old job — the old backup path stops receiving new files.
4. Is built so that modules without a working `.xlsx` export today (Budget — CSV only;
   most of Beasiswa — CSV/PDF only; Beasiswa Dashboard BI and Rekam Medis — no export at
   all) can be wired in later with a one-line registry addition, once their own `.xlsx`
   builders exist (tracked as separate follow-up projects, out of scope here).

## Scope for This Phase

**In scope** — modules/sub-modules with a working `.xlsx` export function today:

| Module | Sub-module(s) | Company |
|---|---|---|
| Bank | Mutasi & Saldo | To confirm during planning: ETF-only (SETF pillar account) or also SMT |
| Payment Approval Memo | Per-company tab set (confirmed distinct tabs for SMT vs ETF exist; only "SMT: PAM List, Advance" and "ETF: AGRI, APP" verified directly so far — full tab list and each tab's export function to confirm during planning) | SMT & ETF (different tabs per company) |
| Payment Application | AGRI/APP/LAND/SETF via `etf_payment_application.service.export_pa_excel`; the separate `/payment-application` blueprint's relevance to confirm during planning (per [FLOW Unified Header Navigation design](2026-07-29-flow-unified-header-navigation-design.md), it looked unwired) | ETF (SMT applicability to confirm) |
| Sponsorship | Report | SMT only |
| Beasiswa | Sahabat ETF only | ETF only |

**Out of scope** (deferred to separate follow-up projects, each needs its own `.xlsx`
builder built first): Budget (all 5 reports are CSV today), Beasiswa's Data Siswa / Data
Budget / Data Payment / Report Siswa (CSV/PDF today), Beasiswa Dashboard BI and Rekam
Medis (no export today), Users (no transactional data to back up).

The exact sub-module-to-export-function mapping for the "to confirm" rows above is a
planning-phase task (read each module's routes/tabs directly) — this spec fixes the
*architecture*, not the final registry contents.

## Design

### Folder layout

```
Y:\Seagate\Flow\
├── Sinar Mas Tjipta\
│   └── <Module>\<Sub-module>\YYYY-MM-DD.xlsx   (last 5 days kept)
├── Eka Tjipta Foundation\
│   └── <Module>\<Sub-module>\YYYY-MM-DD.xlsx   (last 5 days kept)
└── Dsqlite Backup\
    └── finance_hub_YYYY-MM-DD.db               (last 10 days kept)
```

- File name is just the date — the folder path already encodes company, module, and
  sub-module, so repeating that in the filename would be redundant.
- Each leaf folder keeps a rolling window of dated files; older files are deleted after
  each run (5 days for Excel, 10 days for the SQLite copy — the DB backup gets a longer
  window since it's the only full-fidelity fallback if a spreadsheet's underlying data
  needs re-deriving).
- The old path (`Y:\Seagate\Harry\8. Backup\2. Financehub\2.1 Payment Application\`) is
  not touched/deleted retroactively — existing files stay as historical record — but
  nothing new is written there after this ships.

### Registry-driven orchestrator

A single Python list, `BACKUP_REGISTRY`, replaces the hardcoded 3-tab loop in
`tasks/excel_backup.py`. Each entry declares:

```python
{
    "company": "ETF",              # or "SMT"
    "module": "Bank",
    "submodule": "Mutasi & Saldo",
    "export_fn": lambda company_id: build_laporan_mutasi_excel(company_id=company_id),
}
```

The orchestrator (`run_excel_backups()`):

1. Iterates `BACKUP_REGISTRY`.
2. Resolves `company_id` from the company code.
3. Calls `export_fn(company_id)` inside a `try/except` — one entry's failure is logged
   (message + traceback) and skipped; it does not abort the remaining entries.
4. Writes the returned bytes to
   `Y:\Seagate\Flow\<company folder>\<module>\<submodule>\<today>.xlsx`
   (creating directories as needed).
5. Runs retention cleanup on that leaf folder (delete files whose date-parsed filename
   is older than 5 days).

A sibling function, `run_sqlite_backup()`, copies the live `finance_hub.db` to
`Y:\Seagate\Flow\Dsqlite Backup\finance_hub_<today>.db`, then runs its own retention
cleanup (10 days). It is wrapped in its own `try/except`, independent of the Excel step
— either can fail without affecting the other.

A top-level `run_flow_backups()` calls both and is what the scheduler invokes; this
replaces `scheduled_backup_job`'s current call to `run_excel_backups()` alone.

### Scheduling

No change to the existing APScheduler wiring in `app.py` beyond pointing it at the new
entry function — same guard (only runs in the main Werkzeug process), same cron
(`day_of_week="mon-fri", hour=17, minute=0`). Weekends are intentionally skipped, matching
the office's operating days.

### Configurability

The backup root (`Y:\Seagate\Flow`) becomes a `config.py` value (`BACKUP_ROOT`), following
the existing precedent of `config.DB_PATH` — this lets tests point at a temp directory
instead of touching the real `Y:` drive.

### Error handling & logging

- Every registry entry's export call is isolated (per-entry `try/except`), matching the
  existing script's pattern — one broken export doesn't take down the whole run.
- Errors are logged via the existing `print(...)` + `traceback.print_exc()` convention
  used in `excel_backup.py` today (visible in the app's console/log output).
- No push notification (e.g. Telegram) is added in this phase — logging only, matching
  what exists today. A notification hook can be added later without changing this
  design's architecture.

## Technical Approach

- Rewrite `app/tasks/excel_backup.py`: replace the hardcoded PA-only loop with
  `BACKUP_REGISTRY` + the generalized `run_excel_backups()` walk described above; add
  `run_sqlite_backup()`; add `run_flow_backups()` as the new combined entry point.
- Update `app/app.py`'s scheduler wiring to call `run_flow_backups` instead of
  `run_excel_backups` directly.
- Add `BACKUP_ROOT = r"Y:\Seagate\Flow"` to `config.py`.
- Update `scripts/run_backup_now.py` to call `run_flow_backups()` so there's a manual
  on-demand trigger for verifying against the real `Y:` drive before relying on the
  17:00 schedule.
- Retention/cleanup logic is shared between the Excel and SQLite paths (same "parse date
  from filename, delete if older than N days" helper, parameterized by `keep_days`).

## Migration Order

1. Build the registry-driven orchestrator + SQLite backup + config path, with the
   registry populated only for modules confirmed to have a ready export function
   (planning phase confirms exact company/sub-module mapping per the table above).
2. Point the scheduler and `run_backup_now.py` at the new `run_flow_backups()`.
3. Manual run via `run_backup_now.py` against the real `Y:\Seagate\Flow` to confirm
   folder structure, file contents, and retention behavior end to end.
4. Remove the old hardcoded PA-only code path once the new one is verified working — no
   parallel run; the old job stops the moment the new one ships.

## Testing

- Unit tests with `tmp_path` (pytest) covering: registry iteration writes files to the
  expected `<company>\<module>\<submodule>\<date>.xlsx` path; retention cleanup deletes
  files older than the configured window and keeps newer ones; a failing `export_fn` for
  one entry doesn't stop the rest of the registry from running; SQLite backup copies the
  file and applies its own (10-day) retention independently of the Excel retention.
- No test touches the real `Y:` drive — `config.BACKUP_ROOT` is overridden to a temp
  directory in tests, same pattern as `config.DB_PATH` in `tests/conftest.py`.
- Manual verification: run `scripts/run_backup_now.py` once against the real path and
  visually confirm the folder tree and file contents for each in-scope module before
  calling this done.

## Out of Scope

- Building `.xlsx` export functions for Budget or the remaining Beasiswa sub-modules —
  separate follow-up projects; this design only wires up what already exists.
- Any change to the export functions' own content/formatting.
- Failure notifications (Telegram/email) — logging only for now.
- Retroactively cleaning up or migrating files already sitting in the old
  `Y:\Seagate\Harry\8. Backup\2. Financehub\2.1 Payment Application\` path.

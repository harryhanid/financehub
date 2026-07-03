# ETF Dashboard Redesign — Design

> **Status: all sections (1–5) discussed and approved by user, 2026-07-03.** Awaiting final user sign-off on this written file, then proceed to the writing-plans skill. Do NOT start implementation before that.

## Context / Why

Current ETF dashboard (`app/modules/dashboard/routes.py`, `app/templates/dashboard/index.html`) shows "Total Memo" and "Memo Draft" KPI cards that query the `payment_memo` table — which has **0 live records**. Those cards always show 0. Real live data for Payment Memo lives in `pam_records`, and real Payment Application data spans **four pillar-specific tables**, not the (also empty) `payment_application` scaffold table.

Goal: redesign the ETF dashboard into an **operational daily-use tool** for finance staff — surface what needs action now, not just static totals.

## Research Findings (verified against live `finance_hub.db`)

**Companies:** `companies` table = `(1, SMT, Sinar Mas Tjipta)`, `(2, ETF, Eka Tjipta Foundation)`. All `etf_pa`/pillar-PA data and all `pam_records` belong to company_id=2 (ETF only) — confirmed no SMT rows in either.

**Payment Application — 4 pillar tables, same schema, selected via `_TAB_CFG` in `app/modules/etf_payment_application/service.py`:**

| tab | table | lines table | rows (open / on_process / complete) |
|---|---|---|---|
| agri | `etf_pa` | `etf_pa_lines` | 30 / 67 / 258 (355 total) |
| app | `app_pa` | `app_pa_lines` | 71 / 5 / 230 (306 total) |
| sml | `sml_pa` | `sml_pa_lines` | 0 / 0 / 19 (19 total) |
| setf | `setf_pa` | `setf_pa_lines` | 0 / 0 / 0 (empty) |

Each PA row has a 7-stage approval chain (all nullable TEXT dates, filled in order):
`doc_received_by_educ → received_pa_from_educ → checked_by_fincon → approved_by_htj_1 → send_pa_back_to_educ → pa_received_by_po_fin → approval_by_htj_2` then `tanggal_bayar` (payment date). `nomor_pam` links a PA to its `pam_records.pam_no`. PA schema also has `status` (default `'draft'`; live data contains only open/on_process/complete).

There's an existing `pa_summary` SQL VIEW (in `app/database.py`) joining `etf_pa` + `etf_pa_lines` + `siswa` — **AGRI-only**, not generalized across the other 3 pillar tables. Reuse pattern, don't assume it covers APP/SML/SETF.

**Payment Approval Memo — `pam_records` (286 rows), pillar-tagged:**

| pillar | open | complete |
|---|---|---|
| AGRI | 13 | 165 |
| APP | 15 | 92 |
| SETF | 1 | 0 |
| (SML has no pam_records rows) |

`pam_records` columns: `id, company_id, pam_no, pam_date, gl_account, cost_center, pt, requestors_name, keterangan, total_amount, due_date, status, created_at, updated_at, tanggal_bayar, source, mata_uang, dpp, ppn, pillar`. `source` breakdown: beasiswa 241, sponsor 27, tagihan 6, etf 9, klaim_medis 1, others 2.

PAM approval-stage detail is **not on `pam_records` itself** — it's on per-vendor line items in `{pillar}_pam_lines` tables (`agri_pam_lines`, `app_pam_lines`, `setf_pam_lines`; `sml_pam_lines` exists but empty), each with columns `id, pam_id, no_vendor, nama_vendor, tgl_terima_doc, tgl_proses, tgl_verifikasi_tax, tgl_approval_1, tgl_approval_2, tgl_approval_3, tgl_kirim, created_at, updated_at`. A PAM can have multiple vendor lines, each progressing independently.

**Click-through routes available** (all JSON/AJAX endpoints used by modals, not full-page detail views):
- PA: `/etf-payment-application/<int:pa_id>/{update,delete,lines,header}` (path prefix same pattern for other pillar tabs — verify per-tab routing before implementation)
- PAM: `/payment-memo/pam/<int:pam_id>/{status,detail,edit,export/...}`, memo-level `/payment-memo/<int:memo_id>`

**URL-param support today (verified in code, 2026-07-03):**
- PA page (`/etf-payment-application/`) reads `?tab=` and `?sf=` server-side (`routes.py`) — filtered deep links work today with no changes.
- Payment Memo page (`/payment-memo/`) loads the PAM list via AJAX (`/payment-memo/pam` JSON endpoint); the page does **not** read any URL query params to preset tab/filter. Any deep-linking into the PAM view requires a small template enhancement (read params on load, switch tab, apply filter).
- No existing "URL param auto-opens a specific record's modal" mechanism in either module — that is a new (small) template enhancement in both (see Section 4).

## Design — Section 1: Overview & Scope (✅ approved)

**In scope:**
- ETF dashboard (`localhost:8081/`, dashboard module) — replace dead KPI cards with real data.
- Sources: Payment Application (4 pillar tables) + Payment Approval Memo (`pam_records` + `{pillar}_pam_lines`).
- Audience: daily operational use by finance staff — dashboard as a prioritized action list, not a static report.

**Out of scope (this iteration):**
- Other dashboard sections (Beasiswa, Budget) — unchanged.
- SMT company — dashboard for SMT context unaffected (all PA/PAM data is ETF-only anyway).
- SETF pillar — will render but is realistically near-empty (0 PA, 1 PAM).
- Trend/historical charts (monthly trends etc.) — explicitly deferred; this dashboard is operational, not analytical-trend-focused.

## Design — Section 2: KPI Summary Cards (✅ approved)

4 cards, aggregated across all 4 pillars:

| Card | Content | Source |
|---|---|---|
| PA Aktif | Open + On Process count across `etf_pa`/`app_pa`/`sml_pa`/`setf_pa` (e.g. "173 aktif — 101 Open · 72 On Process") | `COUNT(*) ... WHERE status IN ('open','on_process')` per table, summed |
| PAM Terbuka | Open count from `pam_records` (e.g. "29 terbuka") | `COUNT(*) FROM pam_records WHERE status='open'` |
| Total Dibayar Bulan Ini | Rupiah sum of completed PAM paid this calendar month | `SUM(total_amount) FROM pam_records WHERE status='complete' AND tanggal_bayar` in current month |
| Rata-rata Umur Item Terbuka | Avg "days in current stage" across all active PA (open+on_process) and open PAM, using the Section 3 algorithm (PAM item age = its longest-stuck unfinished vendor line) | Derived in Python from the same per-item ages computed for the action lists |

This directly replaces the dead "Total Memo"/"Memo Draft" cards (which query the empty `payment_memo` table).

## Design — Section 3: Action List PA & PAM (✅ approved)

**Layout:** two separate tables stacked vertically — "PA Perlu Tindakan" and "PAM Perlu Tindakan". Columns differ per type, so no forced generalization into one combined list.

**Item count:** Top 10 longest-stuck per table, plus a "lihat semua" link to the module list pre-filtered (targets in Section 4).

**"Days in current stage" algorithm — PA** (statuses `open` + `on_process`, all 4 pillar tables):

Ordered date-column chain with awaited-stage labels:

| # | Column | Awaited-stage label |
|---|---|---|
| 1 | `doc_received_by_educ` | Dokumen diterima Educ |
| 2 | `received_pa_from_educ` | PA diterima dari Educ |
| 3 | `checked_by_fincon` | Pengecekan Fincon |
| 4 | `approved_by_htj_1` | Approval HTJ 1 |
| 5 | `send_pa_back_to_educ` | PA dikirim balik ke Educ |
| 6 | `pa_received_by_po_fin` | PA diterima PO Finance |
| 7 | `approval_by_htj_2` | Approval HTJ 2 |
| 8 | `tanggal_bayar` | Menunggu pembayaran |

- **Current stage** = first *empty* column in chain order (the stage being waited on).
- **Days in stage** = today − MAX(all filled dates in the chain). MAX (not "last before the gap") so out-of-order data still yields a sane age.
- No dates filled at all → baseline `tgl_payment_application`, fallback `created_at`.

**Algorithm — PAM** (status `open`): same walk per *vendor line* over `tgl_terima_doc → tgl_proses → tgl_verifikasi_tax → tgl_approval_1 → tgl_approval_2 → tgl_approval_3 → tgl_kirim`. Line with no dates filled → baseline `pam_date`, fallback memo `created_at`.

**PAM aggregation (1 row per memo):**
- A vendor line counts as *selesai* when `tgl_kirim` is filled.
- **Memo age = its longest-stuck unfinished vendor line**; the shown stage is that line's awaited stage (plus vendor name).
- Progress indicator per memo: "N/M vendor selesai".
- All lines selesai but memo still open → stage = "Menunggu pembayaran" (memo-level `tanggal_bayar` empty), age = today − MAX(`tgl_kirim` across lines).
- Memo with zero vendor lines → stage = "Belum ada vendor line", age from `pam_date` (fallback `created_at`).

**Columns:**
- PA table: `Pilar (badge) · No. PA · Stage ditunggu · Hari (sort key, bold) · Jml siswa · Total (Rp) · Status chip`
- PAM table: `No. PAM · Pilar · Keterangan/Requestor (truncated) · Progress vendor (mis. "2/5 selesai") · Stage terlama · Hari · Total (Rp) · Due date`

**Sort:** days-in-stage descending (longest-stuck first — agreed principle, no fixed SLA thresholds); tie-break `total_amount` descending.

## Design — Section 4: Click-through / Navigation (✅ approved)

**Row click → deep link that auto-opens the record's modal**, so the user can act immediately (records stay fully editable — read-only view explicitly rejected):

- PA row: `/etf-payment-application/?tab=<pilar>&sf=open&open_pa=<id>` — page loads with correct tab+filter (already supported), then a small template enhancement reads `open_pa` and opens that record's edit modal.
- PAM row: `/payment-memo/?view=open-pam&open_pam=<id>` — new (small) template enhancement: read params on load, switch to the Open PAM view, open that memo's detail/edit modal. (Exact modal target — the one where vendor-line stage dates are editable — to be pinned down during planning.)

**"Lihat semua" links** (below each top-10 table):
- PA: `/etf-payment-application/?tab=<pilar>&sf=open` per pillar, or the summary tab — works today, no changes needed.
- PAM: `/payment-memo/?view=open-pam` (uses the same new param as above).

Param names (`open_pa`, `open_pam`, `view`) are working names — finalize during planning; behavior is what's approved.

## Design — Section 5: Technical Implementation Notes (✅ approved)

**Aggregation in Python, not new SQL views.** Dataset is small (~680 PA rows + 286 PAM rows total); the stage-walk algorithm is far more readable/testable in Python than as 8-level `CASE WHEN` SQL, and this avoids generalizing the AGRI-only `pa_summary` view across 4 pillars.

- Dashboard service issues simple queries: 4 × `SELECT ... FROM {pillar}_pa WHERE company_id=? AND status IN ('open','on_process')`, 1 × `SELECT ... FROM pam_records WHERE company_id=? AND status='open'`, plus the pillar `{pillar}_pam_lines` rows for those open memos (per-pillar query or UNION ALL). All stage/age math + top-10 selection in Python.
- KPI cards computed from the same in-memory pass (single source of truth for "days in stage" — no drift between cards and lists).
- Performance: ~6 light indexed queries per dashboard load — fine at this scale; revisit only if row counts grow ~100×.
- **Dead-card bugfix called out explicitly:** the "Total Memo"/"Memo Draft" cards and their `payment_memo`-table queries are *removed* as part of this work (they can never show non-zero data); replaced by Section 2 cards.
- Date columns are TEXT — parse defensively (ISO `YYYY-MM-DD` expected; skip/log unparseable values rather than crash the dashboard).

## Next Steps

1. User sign-off on this written spec (this file).
2. Spec self-review pass: done 2026-07-03 (cross-section consistency: KPI card 4 ↔ Section 3 algorithm; Section 3 "lihat semua" ↔ Section 4 targets; scope statuses consistent across Sections 2/3/5).
3. After sign-off: invoke the writing-plans skill to produce the implementation plan. **Do not start implementation before that.**

# ETF Dashboard Redesign — Design (DRAFT, IN PROGRESS)

> **Status: brainstorming in progress, NOT approved.** Sections 1–2 discussed with user; Sections 3–5 not yet presented. Resume by presenting Section 3 (Action List detail for PA & PAM) via the brainstorming skill.

## Context / Why

Current ETF dashboard (`modules/dashboard/routes.py`, `templates/dashboard/index.html`) shows "Total Memo" and "Memo Draft" KPI cards that query the `payment_memo` table — which has **0 live records**. Those cards always show 0. Real live data for Payment Memo lives in `pam_records`, and real Payment Application data spans **four pillar-specific tables**, not the (also empty) `payment_application` scaffold table.

Goal: redesign the ETF dashboard into an **operational daily-use tool** for finance staff — surface what needs action now, not just static totals.

## Research Findings (verified against live `finance_hub.db`)

**Companies:** `companies` table = `(1, SMT, Sinar Mas Tjipta)`, `(2, ETF, Eka Tjipta Foundation)`. All `etf_pa`/pillar-PA data and all `pam_records` belong to company_id=2 (ETF only) — confirmed no SMT rows in either.

**Payment Application — 4 pillar tables, same schema, selected via `_TAB_CFG` in `modules/etf_payment_application/service.py`:**

| tab | table | lines table | rows (open / on_process / complete) |
|---|---|---|---|
| agri | `etf_pa` | `etf_pa_lines` | 30 / 67 / 258 (355 total) |
| app | `app_pa` | `app_pa_lines` | 71 / 5 / 230 (306 total) |
| sml | `sml_pa` | `sml_pa_lines` | 0 / 0 / 19 (19 total) |
| setf | `setf_pa` | `setf_pa_lines` | 0 / 0 / 0 (empty) |

Each PA row has a 7-stage approval chain (all nullable TEXT dates, filled in order):
`doc_received_by_educ → received_pa_from_educ → checked_by_fincon → approved_by_htj_1 → send_pa_back_to_educ → pa_received_by_po_fin → approval_by_htj_2` then `tanggal_bayar` (payment date). `nomor_pam` links a PA to its `pam_records.pam_no`.

There's an existing `pa_summary` SQL VIEW (in `database.py`) joining `etf_pa` + `etf_pa_lines` + `siswa` — **AGRI-only**, not generalized across the other 3 pillar tables. Reuse pattern, don't assume it covers APP/SML/SETF.

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

No existing "deep link opens this exact record's modal from a URL param" mechanism was found — linking from dashboard will land on the correct module + tab + status filter (e.g. `/etf-payment-application/?tab=agri&sf=open`); auto-opening the specific record's modal on load is a small template enhancement to design during planning, not yet confirmed as in-scope.

## Design — Section 1: Overview & Scope (✅ approved by user)

**In scope:**
- ETF dashboard (`localhost:8081/`, dashboard module) — replace dead KPI cards with real data.
- Sources: Payment Application (4 pillar tables) + Payment Approval Memo (`pam_records` + `{pillar}_pam_lines`).
- Audience: daily operational use by finance staff — dashboard as a prioritized action list, not a static report.

**Out of scope (this iteration):**
- Other dashboard sections (Beasiswa, Budget) — unchanged.
- SMT company — dashboard for SMT context unaffected (all PA/PAM data is ETF-only anyway).
- SETF pillar — will render but is realistically near-empty (0 PA, 1 PAM).
- Trend/historical charts (monthly trends etc.) — explicitly deferred; this dashboard is operational, not analytical-trend-focused.

## Design — Section 2: KPI Summary Cards (presented, awaiting user confirmation)

4 cards, aggregated across all 4 pillars:

| Card | Content | Source |
|---|---|---|
| PA Aktif | Open + On Process count across `etf_pa`/`app_pa`/`sml_pa`/`setf_pa` (e.g. "173 aktif — 101 Open · 72 On Process") | `COUNT(*) ... WHERE status IN ('open','on_process')` per table, summed |
| PAM Terbuka | Open count from `pam_records` (e.g. "29 terbuka") | `COUNT(*) FROM pam_records WHERE status='open'` |
| Total Dibayar Bulan Ini | Rupiah sum of completed PAM paid this calendar month | `SUM(total_amount) FROM pam_records WHERE status='complete' AND tanggal_bayar` in current month |
| Rata-rata Umur Item Terbuka | Avg days open/on_process PA+PAM items have been sitting since last stage movement | Derived, same "days in stage" logic as Section 3 (not yet detailed) |

This directly replaces the dead "Total Memo"/"Memo Draft" cards (which query the empty `payment_memo` table).

## Design — Sections 3–5: NOT YET DONE

Still to design (resume brainstorming here):
- **Section 3:** Action list detail for PA & PAM — which columns shown, sort order, and the concrete "days in current stage" derivation algorithm (walk the 7 PA approval-date columns / per-vendor-line PAM approval columns to find the last-filled one, diff vs today). User already decided the *sorting principle* (longest time stuck in current stage, no fixed SLA thresholds) but not the exact column list or how PAM aggregates across multiple vendor lines per memo.
- **Section 4:** Click-through/navigation behavior — user confirmed clicking a stuck item should jump to the record (not read-only), but exact link target (list+filter vs. deep-linked modal) still needs deciding along with implementation approach.
- **Section 5:** Technical implementation notes — query/view approach (new SQL views similar to `pa_summary` generalized across pillars? or Python-side aggregation?), performance considerations, and explicit callout of the dead-card bug fix.

After Sections 3–5 are approved, write/replace this doc as the final validated spec, do the spec self-review pass, get user sign-off on the written file, then invoke the writing-plans skill — do not start implementation before that.

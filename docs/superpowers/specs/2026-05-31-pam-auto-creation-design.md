# Design: PAM Auto-Creation from Beasiswa Payment Input

**Date:** 2026-05-31  
**Module:** Finance Hub ETF — Payment Approval Memo (PAM)  
**Status:** Approved

---

## Summary

When a user submits payment input via the Beasiswa module (`add_payment_multi`), the system automatically creates a Payment Approval Memo (PAM) record in a new `pam_records` table. This replaces the previous manual memo-creation flow. PAM creation happens atomically in the same database transaction as the payment rows.

---

## Decisions

| Question | Decision |
|---|---|
| Relationship to `payment_memo` | **New table** `pam_records` — `payment_memo` untouched (kept for historical data) |
| UI location | **Payment Memo page** — extended with PAM data + GL Account dropdown |
| Trigger timing | **Atomic** — PAM created in same transaction as `payment_beasiswa` rows |
| PAM No format | Reuse existing `generate_memo_number()` → `PAM/ETF/2026/001` |

---

## Architecture

### Data Flow

```
User: Input Payment (Beasiswa)
  └─► add_payment_multi()
        ├─► INSERT payment_beasiswa rows (per siswa, status='draft')
        │     └─ pam = generated PAM No (auto-set)
        ├─► INSERT pam_records (1 record per batch)
        └─► INSERT coa (seeded once at init_db)
```

All steps inside one SQLite transaction. Rollback on any failure.

---

## Database Schema

### Table: `pam_records` (NEW)

| Column | Type | Source | Notes |
|---|---|---|---|
| `id` | INTEGER PK | auto | |
| `company_id` | INTEGER | session | FK → companies |
| `pam_no` | TEXT UNIQUE | `generate_memo_number()` | e.g. `PAM/ETF/2026/001` |
| `pam_date` | TEXT | `tanggal` from payment input | PAM Date |
| `gl_account` | TEXT | default `70110230` | Editable via COA dropdown |
| `cost_center` | TEXT | `COST_CENTER_MAP[perusahaan]` | Auto from PT, read-only |
| `pt` | TEXT | `perusahaan` from payment input | PT |
| `requestors_name` | TEXT | default `Jany Turkanda` | Requestor's Name |
| `keterangan` | TEXT | comma-join of student names | e.g. `Harry, Joni, Tika` |
| `total_amount` | REAL | sum of batch amounts | Column2 |
| `due_date` | TEXT | `pam_date + 1 month` | Due Date |
| `status` | TEXT | default `draft` | draft → submitted → approved → paid |
| `created_at` | TEXT | timestamp | |
| `updated_at` | TEXT | on edit | |

### Table: `coa` (NEW — Chart of Accounts)

| Column | Type | Notes |
|---|---|---|
| `gl_code` | TEXT PK | e.g. `70110230` |
| `gl_name` | TEXT | e.g. `Scholarship Expense` |
| `is_active` | INTEGER | default 1 |

**Seed data** (16 accounts, duplicates merged on gl_code):

| GL Code | GL Name |
|---|---|
| 70107800 | Sponsorship Expense |
| 70107500 | Social Donation Expense |
| 70110220 | CSR Expense |
| 70110230 | Scholarship Expense (DEFAULT) |
| 70109100 | Communication Expense - 3rd Party |
| 70110100 | Professional International Organization Expense |
| 70110110 | Professional National Organization Expense |
| 70111130 | Consultant Fee |
| 70108100 | Office Equipment Expense / Office Supplies |
| 70111132 | Biaya Jasa Konsultan – Affiliasi |
| 70107200 | Entertainment Expense |
| 70119310 | Gift Expense |
| 70106300 | Overseas Travel Expense |
| 70107600 | Office Consumption |

### Existing tables (unchanged)

- `payment_memo` — historical data, no migration needed
- `payment_beasiswa.pam` — auto-filled with `pam_no` after creation (currently user-entered manually)

---

## Cost Center Map (already in `config.py`)

| PT | Cost Center |
|---|---|
| PT. Forestalestari Dwikarya | 2901C1POFF |
| PT. Ivo Mas Tunggal | 1901C1POFF |
| PT. Maskapai Perkebunan Leidong West Indonesia | 1201C1POFF |
| PT. Mitrakarya Agroindo | 3801C1POFF |
| PT. Agrokarya Primalestari | 4401C1POFF |
| PT. Agrolestari Sentosa | 4201C1POFF |
| PT. Binasawit Abadi Pratama | 3201C1POFF |
| PT. Buana Artha Sejahtera | 4501C1POFF |
| PT. Buana Wiralestari Mas | 2001C1POFF |
| PT. Bumi Permai Lestari | 2601C1POFF |
| PT. Djuandasawit Lestari | 2801C1POFF |
| PT. Paramitra Internusa Pratama | 4701C1POFF |
| PT. Ramajaya Pramukti | 2101C1POFF |
| PT. Sawitakarya Manunggul | 3401C1POFF |
| PT. SMART Tbk | 1008C1POFF |
| PT. Aditunggal Mahajaya | 5101C1POFF |
| PT. Kresna Duta Agroindo | 1101C1POFF |
| PT. Tapian Nadenggan | 1401C1POFF |
| PT. Sumber Indah Perkasa | 2501C1CMOF |

---

## Component Changes

### 1. `database.py`
- Add `pam_records` table DDL
- Add `coa` table DDL with seed data
- Add `migrate_db()` step for `pam_records` and `coa`

### 2. `config.py`
- Add `COA_LIST` constant (gl_code → gl_name mapping, for seeding + dropdown)
- `COST_CENTER_MAP` already present — no change needed

### 3. `modules/beasiswa/service.py` — `add_payment_multi()`
- After inserting `payment_beasiswa` rows, call `create_pam_record()` in same transaction
- Auto-generate `pam_no` via `generate_memo_number()` from `payment_memo.service`
- Auto-set `payment_beasiswa.pam = pam_no` for all inserted rows
- Compute: `keterangan` = comma-join of siswa names, `total_amount` = sum, `due_date` = date + 1 month, `cost_center` = `COST_CENTER_MAP.get(perusahaan, '')`

### 4. `modules/payment_memo/service.py`
- Add `create_pam_record(company_id, company_code, data) → dict`
- Add `get_pam_list(company_id, ...) → list`
- Add `update_pam_gl_account(pam_id, gl_account, company_id) → dict`
- Add `get_coa_list() → list`

### 5. `modules/payment_memo/routes.py`
- Add `GET /payment-memo/pam` → list of PAM records
- Add `POST /payment-memo/pam/<id>/gl-account` → update GL Account
- Add `GET /payment-memo/coa` → COA list (for dropdown)

### 6. Payment Memo HTML template
- Add PAM section/tab showing `pam_records` data
- Add GL Account dropdown (populated from `coa` table)
- Columns: PAM No, PAM Date, PT, Cost Center, GL Account (editable), Requestor, Keterangan, Total, Due Date, Status

---

## Auto-Population Logic

```python
# Inside add_payment_multi() transaction:

# 1. Collect student names from batch
siswa_names = get_siswa_names(company_id, [r['siswa_code'] for r in rows])
keterangan  = ', '.join(siswa_names)

# 2. Total amount
total = sum(row['amount'] for row in valid_rows)

# 3. Due date = tanggal + 1 month
due_date = (datetime.strptime(tanggal, '%Y-%m-%d') + relativedelta(months=1)).strftime('%Y-%m-%d')

# 4. Cost center from PT
cost_center = config.COST_CENTER_MAP.get(perusahaan, '')

# 5. PAM No
pam_no = generate_memo_number(company_id, company_code, year)

# 6. Insert pam_records
conn.execute(INSERT INTO pam_records ...)

# 7. Update payment_beasiswa.pam
conn.execute(UPDATE payment_beasiswa SET pam=? WHERE ...)
```

---

## Error Handling

- If `perusahaan` not in `COST_CENTER_MAP` → `cost_center` = empty string (no error, just blank)
- If `add_payment_multi` batch has 0 valid rows → return early, no PAM created
- PAM creation failure → full rollback of both payment rows and PAM

---

## Testing

- Unit: `create_pam_record()` with known batch data → verify all auto-populated fields
- Unit: `generate_memo_number()` sequence increments correctly across `pam_records`
- Integration: `add_payment_multi()` → verify `pam_records` row exists + `payment_beasiswa.pam` filled
- Edge: PT not in `COST_CENTER_MAP` → cost_center blank, no crash
- Edge: Due date computation across month-end boundaries

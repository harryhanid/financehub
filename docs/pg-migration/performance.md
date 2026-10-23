# Performa halaman FinanceHub di Supabase

Diukur 2026-10-23, schema `financehub_staging`, `scripts/pg_migrate/measure_pages.py` (Flask test client in-process di proses worker, DB lewat HTTPS ke Supabase; rendering browser tidak termasuk). Tiap route 2x, yang dilaporkan run ke-2 (warm); batas 60 s per route.

Target: halaman biasa ≤ 2 s, berat (dashboard, management-report, general-ledger, export) ≤ 5 s; panggilan fh_exec terlama ≤ 4 s (batas Supabase 8 s).

Lulus 268 / 278 route terukur; tidak lulus 10; timeout 0; tidak terukur lainnya 4; dikecualikan 3.

| Route | Co | Detik | Panggilan DB | Detik DB | Panggilan terlama | Status | Target | Hasil |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `/management-report/export-all` | ETF | 13.00 | 112 | 7.77 | 0.28 | 200 | 5 | **FAIL** |
| `/management-report/export-all` | ETF | 12.44 | 112 | 6.94 | 0.47 | 200 | 5 | **FAIL** |
| `/beasiswa/payment/export/pdf` | ETF | 12.10 | 4 | 12.10 | 10.68 | 503 | 5 | **FAIL** |
| `/management-report/export-all` | SMT | 12.00 | 112 | 6.93 | 0.78 | 200 | 5 | **FAIL** |
| `/beasiswa/payment/export/excel` | ETF | 11.12 | 4 | 11.11 | 10.25 | 503 | 5 | **FAIL** |
| `/beasiswa/payment/export/xlsx` | ETF | 10.39 | 4 | 6.46 | 5.98 | 200 | 5 | **FAIL** |
| `/beasiswa/api/dashboard/export_trend_bulanan` | ETF | 8.52 | 4 | 2.30 | 1.16 | 200 | 5 | **FAIL** |
| `/beasiswa/api/dashboard/export_trend_tahunan` | ETF | 7.64 | 2 | 1.05 | 0.84 | 200 | 5 | **FAIL** |
| `/beasiswa/api/dashboard/export_kategori` | ETF | 6.23 | 6 | 1.35 | 0.92 | 200 | 5 | **FAIL** |
| `/beasiswa/payment/export/csv` | ETF | 3.97 | 4 | 3.81 | 3.17 | 200 | 5 | pass |
| `/beasiswa/budget/export/excel` | ETF | 2.33 | 4 | 0.95 | 0.64 | 200 | 5 | pass |
| `/beasiswa/budget/export/pdf` | ETF | 1.75 | 4 | 0.28 | 0.14 | 200 | 5 | pass |
| `/management-report/pemetaan` | ETF | 1.73 | 15 | 1.66 | 0.60 | 200 | 5 | pass |
| `/beasiswa/budget/export/xlsx` | ETF | 1.68 | 4 | 0.29 | 0.13 | 200 | 5 | pass |
| `/management-report/gl-combine` | SMT | 1.58 | 13 | 1.49 | 0.30 | 200 | 5 | pass |
| `/management-report/append/export` | SMT | 1.39 | 4 | 0.53 | 0.38 | 200 | 5 | pass |
| `/etf-payment-application/export-excel` | ETF | 1.18 | 1 | 0.21 | 0.21 | 200 | 5 | pass |
| `/management-report/pemetaan` | SMT | 1.17 | 15 | 1.10 | 0.22 | 200 | 5 | pass |
| `/management-report/gl-combine` | ETF | 1.16 | 13 | 1.09 | 0.26 | 200 | 5 | pass |
| `/management-report/append1` | SMT | 1.15 | 13 | 1.08 | 0.29 | 200 | 5 | pass |
| `/management-report/append1` | ETF | 1.13 | 13 | 1.03 | 0.27 | 200 | 5 | pass |
| `/management-report/append/export` | ETF | 1.12 | 4 | 0.40 | 0.26 | 200 | 5 | pass |
| `/general-ledger/setf` | SMT | 1.06 | 9 | 1.05 | 0.31 | 200 | 5 | pass |
| `/beasiswa/rekap/export/excel` | ETF | 0.86 | 3 | 0.33 | 0.21 | 200 | 5 | pass |
| `/general-ledger/smt` | SMT | 0.85 | 9 | 0.84 | 0.16 | 200 | 5 | pass |
| `/dashboard` | ETF | 0.77 | 13 | 0.76 | 0.10 | 200 | 5 | pass |
| `/bank/` | SMT | 0.75 | 3 | 0.75 | 0.50 | 200 | 2 | pass |
| `/beasiswa/` | ETF | 0.75 | 6 | 0.70 | 0.24 | 200 | 2 | pass |
| `/general-ledger/etf` | SMT | 0.72 | 9 | 0.71 | 0.12 | 200 | 5 | pass |
| `/beasiswa/rekap/export/xlsx` | ETF | 0.69 | 3 | 0.29 | 0.18 | 200 | 5 | pass |
| `/management-report/` | SMT | 0.67 | 12 | 0.66 | 0.12 | 200 | 5 | pass |
| `/management-report/` | ETF | 0.66 | 12 | 0.64 | 0.14 | 200 | 5 | pass |
| `/payment-memo/` | ETF | 0.64 | 7 | 0.60 | 0.19 | 200 | 2 | pass |
| `/payment-memo/pam/940/detail` | ETF | 0.62 | 7 | 0.62 | 0.23 | 200 | 2 | pass |
| `/beasiswa/rekap/export/pdf` | ETF | 0.60 | 3 | 0.27 | 0.16 | 200 | 5 | pass |
| `/payment-memo/pam/940/export/excel` | ETF | 0.57 | 8 | 0.55 | 0.09 | 200 | 5 | pass |
| `/management-report/ho-table` | ETF | 0.50 | 7 | 0.50 | 0.11 | 200 | 5 | pass |
| `/budget/export/transactions` | SMT | 0.50 | 4 | 0.46 | 0.21 | 200 | 5 | pass |
| `/budget/realisasi` | SMT | 0.50 | 6 | 0.49 | 0.25 | 200 | 2 | pass |
| `/sponsorship/data` | SMT | 0.50 | 4 | 0.49 | 0.30 | 200 | 2 | pass |
| `/budget/export/compliance` | SMT | 0.45 | 4 | 0.42 | 0.19 | 200 | 5 | pass |
| `/budget/api/dashboard-data` | ETF | 0.44 | 4 | 0.40 | 0.17 | 200 | 2 | pass |
| `/beasiswa/rekap/data` | ETF | 0.43 | 3 | 0.42 | 0.20 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/breakdown` | ETF | 0.42 | 9 | 0.42 | 0.06 | 200 | 2 | pass |
| `/budget/export/department` | SMT | 0.41 | 4 | 0.38 | 0.16 | 200 | 5 | pass |
| `/beasiswa/api/dashboard/breakdown` | ETF | 0.41 | 5 | 0.40 | 0.13 | 200 | 2 | pass |
| `/etf-payment-application/advance-data` | SMT | 0.41 | 5 | 0.40 | 0.10 | 200 | 2 | pass |
| `/payment-memo/` | SMT | 0.39 | 7 | 0.39 | 0.08 | 200 | 2 | pass |
| `/beasiswa/rekap/export/csv` | ETF | 0.39 | 3 | 0.38 | 0.19 | 200 | 5 | pass |
| `/etf-payment-application/summary-data` | ETF | 0.39 | 5 | 0.36 | 0.13 | 200 | 2 | pass |
| `/etf-payment-application/summary-data` | SMT | 0.37 | 5 | 0.36 | 0.09 | 200 | 2 | pass |
| `/etf-payment-application/advance-data` | ETF | 0.37 | 5 | 0.35 | 0.11 | 200 | 2 | pass |
| `/management-report/ho-table` | SMT | 0.37 | 7 | 0.36 | 0.07 | 200 | 5 | pass |
| `/management-report/table?yy=2026` | SMT | 0.37 | 5 | 0.36 | 0.14 | 200 | 5 | pass |
| `/budget/export/expired` | SMT | 0.37 | 4 | 0.34 | 0.15 | 200 | 5 | pass |
| `/budget/realisasi` | ETF | 0.36 | 6 | 0.36 | 0.07 | 200 | 2 | pass |
| `/budget/export/realization` | SMT | 0.35 | 4 | 0.32 | 0.14 | 200 | 5 | pass |
| `/bank/` | ETF | 0.34 | 3 | 0.33 | 0.13 | 200 | 2 | pass |
| `/budget/api/dashboard-data` | SMT | 0.33 | 4 | 0.29 | 0.14 | 200 | 2 | pass |
| `/sponsorship/api/report-data` | SMT | 0.32 | 2 | 0.32 | 0.24 | 200 | 2 | pass |
| `/beasiswa/payment/list` | ETF | 0.31 | 4 | 0.30 | 0.11 | 200 | 2 | pass |
| `/payment-memo/pam/940/export/pdf` | ETF | 0.31 | 5 | 0.29 | 0.08 | 200 | 5 | pass |
| `/beasiswa/budget/export/csv` | ETF | 0.30 | 4 | 0.28 | 0.16 | 200 | 5 | pass |
| `/management-report/append-table` | SMT | 0.30 | 5 | 0.30 | 0.07 | 200 | 5 | pass |
| `/budget/master` | ETF | 0.30 | 6 | 0.29 | 0.06 | 200 | 2 | pass |
| `/budget/master` | SMT | 0.27 | 6 | 0.26 | 0.06 | 200 | 2 | pass |
| `/payment-memo/coa` | ETF | 0.26 | 1 | 0.26 | 0.26 | 200 | 2 | pass |
| `/management-report/table` | SMT | 0.25 | 5 | 0.25 | 0.07 | 200 | 5 | pass |
| `/beasiswa/laporan/siswa/4240012/export/xlsx` | ETF | 0.24 | 3 | 0.24 | 0.13 | 400 | 5 | pass |
| `/management-report/table` | ETF | 0.23 | 5 | 0.23 | 0.07 | 200 | 5 | pass |
| `/management-report/append-table` | ETF | 0.23 | 5 | 0.23 | 0.06 | 200 | 5 | pass |
| `/payment-memo/pam` | SMT | 0.23 | 1 | 0.23 | 0.23 | 200 | 2 | pass |
| `/beasiswa/budget/list` | ETF | 0.22 | 4 | 0.22 | 0.07 | 200 | 2 | pass |
| `/bank/export-laporan-mutasi` | SMT | 0.22 | 1 | 0.21 | 0.21 | 200 | 5 | pass |
| `/beasiswa/sahabat/api/family_summary` | ETF | 0.21 | 4 | 0.20 | 0.06 | 200 | 2 | pass |
| `/sponsorship/mr` | SMT | 0.21 | 3 | 0.20 | 0.07 | 200 | 2 | pass |
| `/sponsorship/report/export` | SMT | 0.20 | 2 | 0.15 | 0.08 | 200 | 5 | pass |
| `/beasiswa/api/dashboard/pillar_yearly` | ETF | 0.20 | 1 | 0.20 | 0.20 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/pohon` | ETF | 0.20 | 4 | 0.20 | 0.06 | 200 | 2 | pass |
| `/budget/api/lookups` | SMT | 0.20 | 4 | 0.20 | 0.06 | 200 | 2 | pass |
| `/sponsorship/mr/export` | SMT | 0.19 | 2 | 0.15 | 0.09 | 200 | 5 | pass |
| `/budget/api/lookups` | ETF | 0.19 | 4 | 0.18 | 0.05 | 200 | 2 | pass |
| `/beasiswa/laporan/siswa/4240012` | ETF | 0.18 | 3 | 0.18 | 0.08 | 200 | 2 | pass |
| `/payment-memo/export/pam` | ETF | 0.18 | 1 | 0.08 | 0.08 | 200 | 5 | pass |
| `/beasiswa/siswa/4240012/sisa-budget` | ETF | 0.17 | 2 | 0.17 | 0.10 | 200 | 2 | pass |
| `/payment-memo/export/open-pam` | SMT | 0.17 | 2 | 0.16 | 0.10 | 200 | 5 | pass |
| `/bank/export-detail-transaksi` | SMT | 0.16 | 1 | 0.15 | 0.15 | 200 | 5 | pass |
| `/bank/export-detail-transaksi` | ETF | 0.15 | 1 | 0.14 | 0.14 | 200 | 5 | pass |
| `/payment-memo/drafts` | ETF | 0.15 | 2 | 0.14 | 0.08 | 200 | 2 | pass |
| `/dashboard` | SMT | 0.14 | 2 | 0.14 | 0.10 | 200 | 5 | pass |
| `/payment-memo/pam/940/beasiswa-lines` | ETF | 0.14 | 2 | 0.14 | 0.08 | 200 | 2 | pass |
| `/payment-memo/export/open-pam` | ETF | 0.14 | 2 | 0.09 | 0.05 | 200 | 5 | pass |
| `/beasiswa/klaim/list` | ETF | 0.13 | 3 | 0.13 | 0.05 | 200 | 2 | pass |
| `/sponsorship/outstanding` | SMT | 0.13 | 2 | 0.12 | 0.08 | 200 | 2 | pass |
| `/payment-memo/export/fiori` | SMT | 0.13 | 1 | 0.06 | 0.06 | 200 | 5 | pass |
| `/payment-application/` | SMT | 0.13 | 2 | 0.12 | 0.07 | 200 | 2 | pass |
| `/beasiswa/summary` | ETF | 0.12 | 2 | 0.12 | 0.07 | 200 | 2 | pass |
| `/budget/carryover` | ETF | 0.12 | 2 | 0.12 | 0.07 | 200 | 2 | pass |
| `/beasiswa/sahabat/export/detail` | ETF | 0.12 | 2 | 0.10 | 0.06 | 200 | 5 | pass |
| `/payment-memo/drafts` | SMT | 0.12 | 2 | 0.12 | 0.06 | 200 | 2 | pass |
| `/payment-memo/export/fiori` | ETF | 0.11 | 1 | 0.05 | 0.05 | 200 | 5 | pass |
| `/beasiswa/api/dashboard/program_summary` | ETF | 0.11 | 1 | 0.11 | 0.11 | 200 | 2 | pass |
| `/payment-memo/940` | ETF | 0.11 | 1 | 0.11 | 0.11 | 404 | 2 | pass |
| `/beasiswa/budget/siswa/4240012` | ETF | 0.11 | 2 | 0.11 | 0.06 | 200 | 2 | pass |
| `/beasiswa/sahabat/export/detail/csv` | ETF | 0.11 | 2 | 0.11 | 0.06 | 200 | 5 | pass |
| `/budget/carryover` | SMT | 0.10 | 2 | 0.10 | 0.06 | 200 | 2 | pass |
| `/payment-memo/ipay/siswa-medical` | ETF | 0.10 | 1 | 0.10 | 0.10 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/detail/4240012` | ETF | 0.10 | 2 | 0.10 | 0.05 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/all_transactions` | ETF | 0.10 | 2 | 0.10 | 0.05 | 200 | 2 | pass |
| `/spt-badan/` | ETF | 0.10 | 1 | 0.10 | 0.10 | 200 | 2 | pass |
| `/beasiswa/api/dashboard/summary` | ETF | 0.10 | 1 | 0.09 | 0.09 | 200 | 2 | pass |
| `/beasiswa/` | SMT | 0.10 | 1 | 0.09 | 0.09 | 200 | 2 | pass |
| `/payment-memo/export/sml` | SMT | 0.09 | 1 | 0.06 | 0.06 | 200 | 5 | pass |
| `/sponsorship/api/lookups` | SMT | 0.09 | 2 | 0.09 | 0.05 | 200 | 2 | pass |
| `/payment-application/export` | ETF | 0.09 | 1 | 0.08 | 0.08 | 200 | 5 | pass |
| `/sponsorship/api/dashboard-data` | SMT | 0.09 | 1 | 0.09 | 0.09 | 200 | 2 | pass |
| `/payment-memo/advance/list` | SMT | 0.09 | 1 | 0.09 | 0.09 | 200 | 2 | pass |
| `/bank/export-laporan-mutasi` | ETF | 0.09 | 1 | 0.07 | 0.07 | 200 | 5 | pass |
| `/payment-application/` | ETF | 0.09 | 2 | 0.08 | 0.04 | 200 | 2 | pass |
| `/etf-payment-application/siswa-search` | SMT | 0.08 | 1 | 0.08 | 0.08 | 200 | 2 | pass |
| `/sponsorship/data/export` | SMT | 0.08 | 1 | 0.06 | 0.06 | 200 | 5 | pass |
| `/beasiswa/budget/siswa/4240012/export/xlsx` | ETF | 0.08 | 2 | 0.08 | 0.04 | 400 | 5 | pass |
| `/sponsorship/outstanding/export` | SMT | 0.08 | 1 | 0.07 | 0.07 | 200 | 5 | pass |
| `/payment-memo/coa` | SMT | 0.08 | 1 | 0.08 | 0.08 | 200 | 2 | pass |
| `/etf-payment-application/draft-siswa` | SMT | 0.08 | 1 | 0.08 | 0.08 | 200 | 2 | pass |
| `/beasiswa/api/dashboard/latest_payments` | ETF | 0.08 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/payment-memo/pam/940/transaction-lines` | ETF | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/sponsorship/` | SMT | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/spt-badan/` | SMT | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/payment-memo/pam` | ETF | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/payment-memo/agri-pa-open` | ETF | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/payment-memo/export/pam` | SMT | 0.07 | 1 | 0.07 | 0.07 | 200 | 5 | pass |
| `/payment-memo/export/sml` | ETF | 0.07 | 1 | 0.05 | 0.05 | 200 | 5 | pass |
| `/payment-memo/agri-pa-open` | SMT | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/users/` | SMT | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/sop/65` | SMT | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/etf-payment-application/2476/header` | ETF | 0.07 | 1 | 0.07 | 0.07 | 200 | 2 | pass |
| `/payment-memo/vendors` | ETF | 0.07 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/etf-payment-application/export-excel` | SMT | 0.07 | 1 | 0.06 | 0.06 | 200 | 5 | pass |
| `/payment-memo/ipay/siswa-medical` | SMT | 0.07 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/sop/` | ETF | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/payment-memo/advance/list` | ETF | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/summary` | ETF | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/beasiswa/vendors` | SMT | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/beasiswa/sahabat/tree-data` | SMT | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/sponsorship/report` | SMT | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/payment-memo/940/export/pdf` | ETF | 0.06 | 1 | 0.06 | 0.06 | 404 | 5 | pass |
| `/payment-memo/vendors` | SMT | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/payment-memo/fiori` | ETF | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/budget/master/B26-9-9-9` | SMT | 0.06 | 1 | 0.06 | 0.06 | 200 | 2 | pass |
| `/beasiswa/vendors` | ETF | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/payment-memo/fiori/103/detail` | SMT | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/beasiswa/approval-budget` | ETF | 0.05 | 1 | 0.05 | 0.05 | 500 | 2 | **FAIL** |
| `/payment-memo/fiori` | SMT | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/payment-memo/sml` | ETF | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/beasiswa/siswa/4240012` | ETF | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/users/` | ETF | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/beasiswa/sahabat/export/summary` | ETF | 0.05 | 1 | 0.05 | 0.05 | 200 | 5 | pass |
| `/payment-application/export` | SMT | 0.05 | 1 | 0.04 | 0.04 | 200 | 5 | pass |
| `/beasiswa/sahabat/tree-data` | ETF | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/sponsorship/data/3267` | SMT | 0.05 | 1 | 0.05 | 0.05 | 200 | 2 | pass |
| `/sop/` | SMT | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/etf-payment-application/siswa-search` | ETF | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/payment-memo/sml` | SMT | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/etf-payment-application/draft-siswa` | ETF | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/etf-payment-application/2476/lines` | ETF | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/sponsorship/vendor` | SMT | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/latest_payments` | ETF | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/sponsorship/data` | ETF | 0.04 | 1 | 0.04 | 0.04 | 200 | 2 | pass |
| `/advance` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/account-payable` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/auth/change-password` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/advance` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/account-payable` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/auth/login` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/api/dashboard/pillar_yearly` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/api/v1/siswa` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/etf-payment-application/` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/sahabat/export/report/detail` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/api/v1/siswa` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/etf-payment-application/` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/sponsorship/input` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/api/v1/payment` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/api/dashboard/summary` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/api/v1/payment-memo` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/payment-memo/by-pillar/Pendidikan` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/api/v1/payment` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/api/v1/payment-memo` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/auth/change-password` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/budget/` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/approval-budget` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/api/v1/payment-draft` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/sahabat/api/report` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/sahabat/api/summary` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/sponsorship/mr` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/budget/` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/sponsorship/` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/sponsorship/mr/export` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/payment-memo/api/due-date` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/sponsorship/report` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/rekap/data` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/sponsorship/api/lookups` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/api/dashboard/export_trend_tahunan` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/` | SMT | 0.00 | 0 | 0.00 | 0.00 | 302 | 2 | pass |
| `/petty-cash` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/api/dashboard/monthly` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/sponsorship/input` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/budget/export/xlsx` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/budget/export/csv` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/sponsorship/vendor` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/api/v1/rekap` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/api/v1/payment-draft` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/api/dashboard/latest_payments` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/api/dashboard/program_summary` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/petty-cash` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/rekap/export/xlsx` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/budget/export/excel` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/sponsorship` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/api/v1/rekap` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/select-company` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/all_transactions` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/auth/login` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/api/v1/budget` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/payment/export/pdf` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/api/v1/budget` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/sponsorship` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/rekap/export/excel` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/api/dashboard/export_trend_bulanan` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/api/pohon` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/sponsorship/outstanding` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/sahabat/api/report/export_ppt` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 5 | pass |
| `/beasiswa/api/dashboard/breakdown` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/general-ledger/` | ETF | 0.00 | 0 | 0.00 | 0.00 | 302 | 5 | pass |
| `/beasiswa/rekap/export/pdf` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/select-company` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/breakdown` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/sponsorship/data/export` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/` | ETF | 0.00 | 0 | 0.00 | 0.00 | 302 | 2 | pass |
| `/beasiswa/sahabat/export/report/detail` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 5 | pass |
| `/beasiswa/sahabat/export/detail` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/management-report/export` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 5 | pass |
| `/management-report/export` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 5 | pass |
| `/beasiswa/budget/export/pdf` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/payment/export/excel` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/sponsorship/api/report-data` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/api/dashboard/export_kategori` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/export/report` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 5 | pass |
| `/etf-payment-application/draft-lines` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/sahabat/login` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/sahabat/export/report` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/rekap/export/csv` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/sponsorship/api/dashboard-data` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/budget/list` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/klaim/list` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/sahabat/export/detail/csv` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/api/latest_payments` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/sahabat/api/family_summary` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/sahabat/api/monthly` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/sahabat/api/report` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/payment/export/xlsx` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/siswa/generate-kode` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/etf-payment-application/draft-lines` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/sahabat/api/monthly` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/sahabat/export/summary` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/payment/export/csv` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/payment-memo/pam/check` | SMT | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/beasiswa/summary` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/api/v1/siswa/4240012` | ETF | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/sponsorship/outstanding/export` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/payment-memo/api/due-date` | SMT | 0.00 | 0 | 0.00 | 0.00 | 400 | 2 | pass |
| `/beasiswa/siswa/generate-kode` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/general-ledger/` | SMT | 0.00 | 0 | 0.00 | 0.00 | 302 | 5 | pass |
| `/beasiswa/payment/list` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/beasiswa/api/dashboard/monthly` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 2 | pass |
| `/payment-memo/pam/check` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |
| `/sponsorship/report/export` | ETF | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/api/report/export_ppt` | SMT | 0.00 | 0 | 0.00 | 0.00 | 403 | 5 | pass |
| `/beasiswa/sahabat/login` | ETF | 0.00 | 0 | 0.00 | 0.00 | 200 | 2 | pass |

## Tidak terukur

| Route | Co | Alasan |
|---|---|---|
| `/management-report/pemetaan/kategori` | SMT | skip(write): INSERT INTO gl_mapping_meta (key, value) VALUES ('version', '1') ON CONFLICT DO NOTHING RETURNING * |
| `/management-report/pemetaan/kategori` | ETF | skip(write): INSERT INTO gl_mapping_meta (key, value) VALUES ('version', '1') ON CONFLICT DO NOTHING RETURNING * |
| `/payment-memo/ipay/next-pam-no` | SMT | skip(write): SELECT fn_next_pam_no(1, 'ETF', '2026', '10') AS pam_no |
| `/payment-memo/ipay/next-pam-no` | ETF | skip(write): SELECT fn_next_pam_no(2, 'ETF', '2026', '10') AS pam_no |
| `/` | – | redirect ke /auth/login (bukan halaman) |
| `/backup/` | – | not measured: drive-dependent (file browser drive D:) |
| `/backup/download` | – | not measured: drive-dependent (unduh file dari drive D:) |

## Catatan

- Optimasi Task 21 yang sudah termasuk di angka di atas: `fh_strftime` plpgsql (`0002b_compat.sql`, diterapkan ulang ke `financehub_staging` dan `financehub_test`), gzip pada `HttpBackend`, cache snapshot + batch di `management-report/export-all` (615 → 112 panggilan).
- Sebelum optimasi (run pertama): `beasiswa/api/dashboard/pillar_yearly`, `export_kategori`, `export_trend_*` → 503 (statement_timeout 8 s karena `fh_strftime` lama ~0,8 ms/baris); `management-report/export-all` 78–92 s; halaman sponsorship 2–6 s. Sesudah: pillar_yearly 0,6 s, sponsorship ≤ 0,6 s, export-all 12–13 s.
- `beasiswa/payment/export/pdf` dan `/excel` (ETF) sempat 503 di run penuh (satu panggilan ~10 s, transfer ~9 MB JSON); diukur ulang langsung sesudahnya: 6,6 s dan 4,8 s, status 200, panggilan terlama 1,2 s. Query-nya sendiri 0,3–0,6 s di server; sisanya transfer + openpyxl/reportlab di Python. Variasi jaringan (laptop di luar kantor) besar.
- Export berat yang masih di atas 5 s sebagian besar waktu Python (openpyxl/reportlab, kolom "Detik" − "Detik DB"), bukan DB.
- `/beasiswa/approval-budget` 500: `TemplateNotFound: beasiswa/approval.html` — bug lama, bukan migrasi.

## Alur tulis berat (`financehub_test`, `scripts/pg_migrate/measure_heavy_flows.py`)

| Alur | Baris | Total | Panggilan | Panggilan fh_exec terlama | Batas 8 s |
|---|---:|---:|---:|---:|---|
| GL replace_year (smt 2026) | 8.898 | 10,1 s | 19 | 1,94 s (baca baris GL) | aman |
| MR save_upload (`Management Report - MASTER.xlsb`, termasuk parse) | 8.388 | 6,4 s | 12 | 1,39 s | aman |
| SPT take_snapshot (smt 2026) | – | 5,3 s | 35 | 0,55 s | aman |

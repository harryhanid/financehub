# FinanceHub — Runbook Cutover ke Supabase (project Flow)

## Setup awal (Task 20, selesai 2026-10-23)

| Langkah | Cara | Hasil |
|---|---|---|
| Hapus sisa spike `fh_spike_exec` / `fh_spike` | SQL Editor (owner), `docs/pg-migration/task20_setup_flow.sql` bagian 1 | spike = 0 |
| Pasang `public.fh_exec` (hanya `service_role`) | SQL Editor (owner) | anon_exec=false, service_exec=true |
| Buat schema `financehub_staging`, `financehub_test` + `grant usage, create` ke `service_role` | SQL Editor (owner) | OK |
| Migrasi 0002–0004 ke `financehub_test` dan `financehub_staging` | `python scripts/pg_migrate/apply_migrations.py --schema <s> --backend http` | ±3 detik per schema |
| Kontrak HTTP | `FH_CONTRACT_HTTP=1 FH_CONTRACT_SCHEMA=financehub_test python -m pytest tests/test_fhdb_backends.py tests/test_fhdb_connection.py -m contract_http` (dari `app/`) | 25/25 lulus |
| Data API | Accept-Profile `financehub*` → PGRST106 | hanya `public`, `graphql_public` yang terekspos |
| Load staging | `python scripts/pg_migrate/load_data.py --sqlite C:/FinanceHub/app/finance_hub.db --backend http --schema financehub_staging` | 61 tabel / 113.910 baris, 69 detik |
| Verifikasi staging | `python scripts/pg_migrate/verify.py --sqlite ... --backend http --schema financehub_staging` | 0 mismatch, 65 detik |
| Uji backup → restore | `run_db_backup` dari staging (30 detik, 2,6 MB) → `restore_backup.py --schema financehub_test` | 66 tabel / 113.910 baris, 68 detik, 0 mismatch |

## Batasan Supabase yang ditemukan

- `pg_safeupdate`: UPDATE/DELETE tanpa WHERE ditolak (SQLSTATE 21000), tidak bisa dimatikan (service_role maupun postgres). Kode sudah disesuaikan (commit 6b59399); test lokal meniru aturan ini.
- `statement_timeout = 8s` dan `lock_timeout = 8s` per panggilan (role `authenticator`). Proses berat diukur di Task 21; kalau perlu dinaikkan, lewat SQL Editor sebagai owner.
- Plugin Supabase (MCP) untuk perintah tulis butuh persetujuan prompt di laptop; dari HP tertolak. Perintah owner dijalankan lewat SQL Editor.

## Belum diputuskan sebelum hari-H

- Schema `financehub` di Flow masih berisi salinan sync lama (60 tabel + 1 view, ±113.782 baris, nama kolom huruf kecil). Usulan: `alter schema financehub rename to financehub_legacy_sync;` lalu `create schema financehub` + grant, terapkan migrasi; hapus `financehub_legacy_sync` setelah cutover sukses.
- Fungsi pre-existing `public.rls_auto_enable()` (SECURITY DEFINER) bisa dipanggil anon/authenticated — bukan dari migrasi ini; perlu dicek pemiliknya.

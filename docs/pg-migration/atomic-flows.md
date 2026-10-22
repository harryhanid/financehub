# Inventaris alur tulis multi-langkah (atomic flows)

> Task 8, migrasi SQLite → Supabase (`feat/supabase-primary-db`). Dokumen ini hanya membaca kode; tidak ada file sumber yang diubah.
> Nomor baris mengacu ke commit `ecb9e7d` (HEAD saat inventaris dibuat). Path relatif ke `app/`.

## Kenapa perlu

Lewat `fhdb`, satu panggilan backend = satu transaksi:

- `conn.execute(...)` tulis langsung ter-commit. `commit()` tidak melakukan apa-apa.
- `rollback()` **tidak bisa membatalkan** tulisan sebelumnya, hanya mencatat warning.
- Atomik hanya lewat `conn.batch([(sql, params), ...])`, `executemany` (satu panggilan), `executescript` (satu panggilan), atau fungsi plpgsql.

Jadi semua alur yang dulu mengandalkan transaksi implisit SQLite (beberapa tulisan lalu satu `commit()`, atau `try/except: rollback()`) sekarang bisa meninggalkan data setengah jadi. Tiap baris di tabel utama adalah satu work item untuk Task 9–17, dan masing-masing butuh test `test_<fungsi>_atomic_on_failure`: paksa langkah terakhir gagal, lalu assert jumlah baris di semua tabel yang disentuh tidak berubah.

## Pola

| Pola | Kapan | Catatan implementasi |
|---|---|---|
| **batch** | Semua tulisan bisa disusun sebelum dikirim. Termasuk tulisan bersyarat yang kondisinya bisa dipindah ke SQL (`WHERE NOT EXISTS (...)`, `SET x = (SELECT SUM ...)`, `CASE WHEN`). | Validasi dan pembacaan data yang tidak berubah (mapping line → pa_id, daftar line_ids) dilakukan **sebelum** batch. Bacaan yang sekarang muncul *di antara* tulisan (hitung sisa setelah DELETE) diganti subquery dalam statement batch. Batch berjalan dalam satu transaksi, jadi statement berikutnya melihat efek statement sebelumnya. |
| **batch+currval** | Tulisan berikutnya butuh `id` baris yang baru dibuat di batch yang sama. | `currval(pg_get_serial_sequence('"<schema>"."<tabel>"', 'id'))`. Untuk header + banyak line: INSERT header, lalu semua INSERT line memakai currval header. Untuk pasangan per baris (payment → rekam_medis/klaim): susun INSERT parent lalu INSERT child berselang-seling; currval selalu menunjuk parent terakhir. `cursor.lastrowid` dari hasil batch tetap tersedia untuk nilai return. |
| **fungsi plpgsql** | Alur membaca, menghitung di Python, lalu menulis berdasarkan hasil baca, dan hasil itu bisa diubah user lain di antaranya (nomor urut, saldo/budget, status persetujuan, delta ledger). | File migrasi `0004_fn_<modul>.sql`. Penomoran memakai `pg_advisory_xact_lock(hashtext('<nama-kunci>'))`. Persetujuan memakai `SELECT ... FOR UPDATE` pada baris request/log. |

## Ringkasan

| Task | Modul | Alur | batch | batch+currval | plpgsql |
|---|---|---:|---:|---:|---:|
| 9 | auth, users, sop, dashboard, payment_application, backup, bank, utils/gdrive_service | 4 | 2 | 0 | 2 |
| 10 | budget | 2 | 0 | 0 | 2 |
| 11 | etf_payment_application | 3 | 1 | 0 | 2 |
| 12 | sahabat_etf | 0 | 0 | 0 | 0 |
| 13 | sponsorship | 3 | 3 | 0 | 0 |
| 14 | general_ledger, spt_badan | 3 | 1 | 1 | 1 |
| 15 | management_report, beasiswa | 19 | 15 | 2 | 2 |
| 16 | payment_memo bagian 1 | 16 | 10 | 3 | 3 |
| 17 | payment_memo bagian 2 | 4 | 3 | 0 | 1 |
| | **Total** | **54** | **35** | **6** | **13** |

Ditambah: 4 alur multi-panggilan lintas fungsi (§ Rantai lintas fungsi), 5 situs `rollback()` yang hanya membungkus satu statement (§ Akuntansi rollback), 5 situs penomoran (§ Penomoran), 18 handler yang menelan error database (§ Error yang tertelan), dan skrip one-off (§ Skrip one-off/import).

---

## Tabel utama

Kolom "butuh hasil langkah sebelumnya?" = apakah sebuah tulisan butuh nilai (id, nomor, hasil hitung) dari tulisan atau bacaan sebelumnya di alur yang sama.

### Task 9: auth, users, sop, dashboard, payment_application, backup, bank, utils/gdrive_service

`users`, `dashboard`, `backup`, `utils/gdrive_service`: tidak ada alur. `users/service.py` hanya satu statement per fungsi. `dashboard` hanya membaca. `backup` dan `utils/gdrive_service.py` tidak menyentuh database (filesystem dan Google Drive API).

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| auth | `auth/routes.py:47` `login` | UPDATE users.last_login (69); INSERT refresh_tokens (80) | Tidak. Token dibuat di Python. | batch: dua tulisan independen. | `test_login_atomic_on_failure` |
| sop | `modules/sop/service.py:46` `record_upload` | UPDATE sop_documents (48); INSERT sop_upload_history (55) | Tidak (`doc_id` dari argumen). | batch: dua tulisan independen. | `test_record_upload_atomic_on_failure` |
| payment_application | `modules/payment_application/service.py:48` `create_application` | INSERT payment_application (68) dengan `application_number` dari `COUNT(*)+1` (63–66) | Ya: nomor dari COUNT. `application_number` UNIQUE global, jadi dua request bersamaan saling tabrak. COUNT juga salah setelah ada baris yang dihapus. | fungsi plpgsql: penomoran → `pg_advisory_xact_lock(hashtext('payment_application:'\|\|company_id))`. | `test_create_application_atomic_on_failure` |
| bank | `modules/bank/service.py:108` `sync_pam_to_bank_setf` | Cabang delta<0: DELETE bank_setf (193) + INSERT bank_setf (195). Cabang delta>0: INSERT delta (183) setelah membaca SUM yang sudah tercatat (167). Cabang lain: DELETE (141). | Ya: delta = SUM(payment_beasiswa) − SUM(bank_setf). Dua panggilan bersamaan untuk PAM yang sama akan menyisipkan delta dua kali. | fungsi plpgsql `fn_sync_pam_to_bank_setf(pam_id)`: baca, hitung delta, lalu tulis → advisory lock per `pam_id`. Fungsi ini juga dipanggil dari payment_memo (lihat § Rantai lintas fungsi). | `test_sync_pam_to_bank_setf_atomic_on_failure` |

### Task 10: budget

`create_budget`, `update_budget`, `delete_budget`, `create_realisasi`, `update_realisasi`, `delete_realisasi`, `request_carryover`, `request_additional_budget`, `reject_request`: satu statement, di luar inventaris. `create_realisasi` tidak memeriksa sisa budget, jadi tidak ada baca-hitung-tulis.

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| budget | `modules/budget/service.py:705` `approve_carryover` | UPDATE budget_master.deadline (723); UPDATE budget_carryover_logs → Approved (725) | Ya: deadline baru = deadline lama + N bulan (dihitung di Python dari baris yang dibaca). Dua approve bersamaan memperpanjang dua kali. | fungsi plpgsql: `FOR UPDATE` pada log Pending, lalu hitung deadline di SQL. | `test_approve_carryover_atomic_on_failure` |
| budget | `modules/budget/service.py:734` `approve_additional_budget` | UPDATE budget_master.amount + deadline (750); UPDATE budget_carryover_logs → Approved (752) | Ya: amount baru = amount + additional_amount (dibaca dulu). Approve ganda menambah dua kali. | fungsi plpgsql: membaca budget lalu menulis → `FOR UPDATE` pada log + budget_master. | `test_approve_additional_budget_atomic_on_failure` |

### Task 11: etf_payment_application

`bulk_update_pa` (178): satu UPDATE + SELECT COUNT, di luar inventaris. Rute `create` (`routes.py:188`) memanggil `create_pa` lalu UPDATE lampiran di panggilan terpisah (lihat § Rantai lintas fungsi dan § Error yang tertelan).

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| etf_payment_application | `modules/etf_payment_application/service.py:366` `create_pa` | INSERT {pa_tbl} (387) dengan `pa_number` dari `_gen_pa_number` (COUNT+1, 54–59); INSERT {lines_tbl} ×N (406) | Ya: nomor PA dari COUNT (`pa_number` UNIQUE); semua line butuh `pa_id`. | fungsi plpgsql: penomoran + header/lines → advisory lock `'pa:'\|\|tbl\|\|':'\|\|company_id`, lines memakai id hasil INSERT ... RETURNING. | `test_create_pa_atomic_on_failure` |
| etf_payment_application | `modules/etf_payment_application/service.py:427` `update_pa` | UPDATE {pa_tbl} header (498); UPDATE {lines_tbl} (504); UPDATE payment_beasiswa.amount (527); UPDATE pam_records total = SUM (535) | Ya: `nomor_pam` baru dari `_gen_nomor_pam` (COUNT+1, 62–72) saat pindah ke on_process; total PAM = SUM setelah update pb. | fungsi plpgsql: ada penomoran `nomor_pam` → advisory lock. Tanpa penomoran, sisanya bisa batch (total via subquery SUM). | `test_update_pa_atomic_on_failure` |
| etf_payment_application | `modules/etf_payment_application/service.py:548` `delete_pa` | DELETE {lines_tbl} (573); DELETE {pa_tbl} (574) | Tidak. | batch: dua DELETE independen (cek "linked" tetap sebelum batch). | `test_delete_pa_atomic_on_failure` |

### Task 12: sahabat_etf

Tidak ada alur. `modules/sahabat_etf/` hanya membaca (`service.py`, `routes.py:354`).

### Task 13: sponsorship

`create_perusahaan`, `update_perusahaan`, `delete_perusahaan`, `create_transaksi`, `update_transaksi`: satu statement. `delete_transaksi` (873): satu DELETE dengan rollback (lihat § Akuntansi rollback). `migrate.py` ada di § Skrip one-off/import.

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| sponsorship | `modules/sponsorship/service.py:39` `seed_perusahaan` | INSERT OR IGNORE sponsorship_perusahaan ×N dalam loop (43) | Tidak. Hanya menjumlah rowcount. | batch (atau `executemany`, satu panggilan, rowcount dijumlah fhdb): baris independen; `ON CONFLICT DO NOTHING`. | `test_seed_perusahaan_atomic_on_failure` |
| sponsorship | `modules/sponsorship/service.py:809` `create_transaksi_bulk` | INSERT sponsorship_transaksi ×N (849). **`rollback()` di tengah loop (840, 846) setelah baris sebelumnya sudah masuk.** | Tidak. Lookup `get_perusahaan` hanya bacaan. | batch: validasi semua line dulu (cat1 ada, amount angka), lalu satu batch INSERT. Sekarang validasi gagal di baris k meninggalkan baris 1..k−1. | `test_create_transaksi_bulk_atomic_on_failure` |
| sponsorship | `modules/sponsorship/service.py:894` `sync_transaksi_excel` | Per baris Excel: INSERT sponsorship_perusahaan (972) atau UPDATE-nya (979); UPDATE sponsorship_transaksi (991) atau INSERT (1004). Validasi dengan `rollback()` di tengah loop (952, 955, 970). | Tidak antar-statement. Tapi baris Excel ke-n bisa bergantung pada perusahaan yang baru disisipkan baris ke-m<n (`get_perusahaan` lewat koneksi lain). | batch: parse dan validasi seluruh sheet dulu; perusahaan baru di-dedupe dan disisipkan dengan `ON CONFLICT (cat1) DO UPDATE`; lalu satu batch. | `test_sync_transaksi_excel_atomic_on_failure` |

### Task 14: general_ledger, spt_badan

`spt_badan.create_period` (93): satu INSERT + `except IntegrityError: rollback()` (§ Akuntansi rollback). `spt_badan.ensure_schema` (84, `executescript(_DDL)` 85): tabel statis, hapus pemanggilan (plan Task 14/15), bukan alur. `_prune` (146) adalah bagian dari `take_snapshot`.

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| general_ledger | `modules/general_ledger/service.py:50` `ensure_schema` | Per entitas: DROP TABLE legacy (57), DROP INDEX ×2 (58–59), ALTER TABLE RENAME → `_legacy` (60), `executescript(_table_ddl)` (62); `executescript(_LOG_DDL)` (63); ALTER gl_sync_log ADD COLUMN year (65) | Ya: rename hanya kalau `PRAGMA table_info` beda dari kolom yang diharapkan (bacaan sebelum tulis). | batch: bacaan PRAGMA dulu, lalu rename + DDL baru per entitas dalam satu batch. Kalau tidak, gagal di tengah meninggalkan tabel yang sudah di-rename tanpa pengganti. Plan Task 14: DDL per entitas dipertahankan dan diterjemahkan. | `test_ensure_schema_atomic_on_failure` (general_ledger) |
| general_ledger | `modules/general_ledger/service.py:77` `replace_year` | DELETE {table} tahun Y (87); `executemany` INSERT {table} (89); INSERT gl_sync_log (92) | Tidak (log dari argumen). | fungsi plpgsql + tabel staging: plan Task 14 meminta potongan ≤1000 baris per panggilan HTTPS. Itu tidak bisa atomik kalau dikirim sebagai banyak batch. Upload potongan ke staging (per `sync_token`), lalu satu fungsi melakukan DELETE + `INSERT ... SELECT` dari staging + log + bersihkan staging. Kalau satu file selalu di bawah batas request, cukup satu batch. | `test_replace_year_atomic_on_failure` |
| spt_badan | `modules/spt_badan/service.py:156` `take_snapshot` | UPDATE spt_snapshot is_current=0 (198); INSERT spt_snapshot (199); `executemany` INSERT spt_gl_line (205), spt_exception (212), spt_control (216); `_prune`: DELETE spt_gl_line/exception/control/snapshot lama (152–153) | Ya: semua anak butuh `snapshot_id`. | batch+currval: anak memakai `currval(... spt_snapshot ...)`. Ukuran: satu snapshot = semua baris GL setahun, bisa melewati batas request (lihat § Hal yang ambigu). Kalau melewati, pakai pola staging seperti `replace_year`. | `test_take_snapshot_atomic_on_failure` |

### Task 15: management_report, beasiswa

`coa_map.ensure_schema` (178: `executescript(_DDL)` 179 + 2× `ALTER ADD COLUMN`) dan `management_report/service.py` `ensure_schema` (47: `executescript(_DDL)` 48 + ALTER): tabel statis, hapus pemanggilan (plan Task 15). Bukan alur.

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| management_report | `modules/management_report/category_map.py:110` `ensure_schema` | `executescript(_DDL)` (111); INSERT OR IGNORE gl_mapping_meta version (112); `executemany` INSERT OR IGNORE gl_pph_alias (113) | Tidak. | batch: DDL dihapus (tabel statis), tapi dua seed idempoten tetap dibutuhkan → satu batch `ON CONFLICT DO NOTHING`, atau pindahkan seed ke migrasi lalu hapus fungsi. | `test_ensure_schema_atomic_on_failure` (category_map) |
| management_report | `modules/management_report/category_map.py:183` `sync_categories` | DELETE gl_category_map (197); `executemany` INSERT (198); `_on_synced` INSERT OR IGNORE gl_category_lk ×N (249); INSERT gl_category_sync_log (204); `bump_version` UPDATE gl_mapping_meta (119) | Tidak. `bump_version` increment di SQL. | batch: semua tulisan independen (replace-all + log + bump). | `test_sync_categories_atomic_on_failure` |
| management_report | `modules/management_report/category_map.py:264` `update_lk` | UPDATE gl_category_lk (280); `bump_version` (119) | Tidak. | batch: tulis + bump versi. | `test_update_lk_atomic_on_failure` |
| management_report | `modules/management_report/category_map.py:303` `add_pph_alias` | INSERT OR REPLACE gl_pph_alias (314); `bump_version` (119) | Tidak. | batch: tulis + bump (`ON CONFLICT (alias) DO UPDATE`). | `test_add_pph_alias_atomic_on_failure` |
| management_report | `modules/management_report/category_map.py:322` `delete_pph_alias` | DELETE gl_pph_alias (328); `bump_version` (119) | Ya, lemah: KeyError kalau rowcount DELETE = 0 (bump tidak boleh terjadi). | batch: `WITH d AS (DELETE ... RETURNING 1) UPDATE gl_mapping_meta ... WHERE EXISTS (SELECT 1 FROM d)`, atau batch dua statement dan terima bump ekstra (hanya cache-bust). | `test_delete_pph_alias_atomic_on_failure` |
| management_report | `modules/management_report/coa_map.py:240` `sync_coa` | DELETE gl_coa_map (255); DELETE gl_cc_map (256); `executemany` INSERT gl_coa_map (257); `executemany` INSERT gl_cc_map (262); INSERT gl_coa_sync_log (265) | Tidak. | batch: replace-all dua tabel + log, semua independen. | `test_sync_coa_atomic_on_failure` |
| management_report | `modules/management_report/service.py:73` `save_upload` | INSERT mr_upload (81); `executemany` INSERT mr_append (88); UPDATE mr_upload is_active=0 (94); UPDATE is_active=1 (95); `_purge_old`: DELETE mr_append + UPDATE purged ×N (69–70) | Ya: mr_append dan aktivasi butuh `upload_id`. | batch+currval: baris append + aktivasi memakai `currval(... mr_upload ...)`. `_purge_old` bisa jadi satu DELETE/UPDATE set-based (`id NOT IN (top keep)` dan `is_active=0`). Ukuran: lihat § Hal yang ambigu. | `test_save_upload_atomic_on_failure` |
| management_report | `modules/management_report/service.py:186` `activate_upload` | UPDATE mr_upload is_active=0 (195); UPDATE is_active=1 (196) | Tidak. | batch: dua UPDATE. Kalau gagal di tengah, tidak ada upload aktif. | `test_activate_upload_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:224` `delete_siswa` | DELETE budget_beasiswa (238); DELETE payment_beasiswa (239); DELETE siswa (240) | Tidak. | batch: tiga DELETE independen. | `test_delete_siswa_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:291` `add_payment_batch` | INSERT payment_beasiswa ×N (302) | Tidak. | batch: baris independen. | `test_add_payment_batch_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:425` `add_payment_multi` (+ helper `insert_payment_rows` 322) | `insert_payment_rows`: INSERT payment_beasiswa ×N (360), INSERT rekam_medis per baris medis (381), UPDATE {pa_tbl} on_process (408); `create_pam_record` (payment_memo:964): INSERT pam_records dengan nomor dari `generate_pam_number` (937, max_seq+1), UPDATE payment_beasiswa.pam ×N (990); UPDATE etf_pa/app_pa/sml_pa nomor_pam (473) | Ya: rekam_medis butuh `payment_id`; link pb.pam butuh id payment + `pam_no` hasil penomoran; PA butuh `pam_no`. | fungsi plpgsql: penomoran PAM (`pam_no` UNIQUE) → advisory lock `'pam_no:'\|\|company_code\|\|':'\|\|year`. Pakai fungsi bersama `fn_next_pam_no` / `fn_create_pam_record` dari Task 16. Alternatifnya: alokasi nomor via fungsi itu, lalu sisanya batch+currval. | `test_add_payment_multi_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:680` `delete_payment_row` | DELETE rekam_medis (696); DELETE payment_beasiswa (697); DELETE pam_records kalau tidak ada sisa (706); UPDATE {pa_tbl} open kalau tidak ada sisa (732, loop 3 tabel) | Ya: hitung sisa setelah DELETE (701, 722). | batch: kondisi pindah ke SQL (`DELETE pam_records WHERE pam_no=? AND NOT EXISTS (...)`, `UPDATE {pa_tbl} ... WHERE id=? AND NOT EXISTS (...)`). `pa_id` dari line dibaca sebelum batch. | `test_delete_payment_row_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:743` `delete_payment_beasiswa` | Sama dengan `delete_payment_row`: DELETE rekam_medis (761), payment_beasiswa (766), pam_records bersyarat (775), UPDATE {pa_tbl} bersyarat (801) | Ya: hitung sisa setelah DELETE. | batch: sama dengan `delete_payment_row` (keduanya hampir duplikat; perbaiki keduanya). | `test_delete_payment_beasiswa_atomic_on_failure` (beasiswa) |
| beasiswa | `modules/beasiswa/service.py:812` `update_payment_row` | UPDATE payment_beasiswa.pam (836); UPDATE pam_records.tanggal_bayar (847); `rollback()` (844, 852) | Ya, lemah: `rollback()` 852 dimaksudkan membatalkan UPDATE 836 kalau PAM target hilang. Target sudah divalidasi di 826, jadi rowcount 0 hanya terjadi kalau ada race. | batch: validasi target PAM sebelum batch, lalu kirim dua UPDATE dalam satu batch. | `test_update_payment_row_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:953` `add_klaim_multi` | Per baris: INSERT payment_beasiswa (975) lalu INSERT klaim_medical dengan `payment_id` (984) | Ya: klaim butuh `payment_id`. | batch+currval: pasangan pb → klaim berselang-seling; klaim memakai `currval(... payment_beasiswa ...)`. | `test_add_klaim_multi_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:1040` `delete_klaim_row` | DELETE payment_beasiswa (1057); DELETE klaim_medical (1059) | Tidak. | batch: dua DELETE. | `test_delete_klaim_row_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:1615` `add_budget_batch` | INSERT budget_beasiswa_requests ×N (1626) | Tidak (batch_id dari Python). | batch: baris independen. | `test_add_budget_batch_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:1682` `approve_budget_request_batch` | Per request: INSERT/UPDATE/DELETE budget_beasiswa (1692/1697/1702); UPDATE request → APPROVED (1704) | Ya: aksi tergantung isi request dan status PENDING (dibaca dulu). Dua BC yang approve bersamaan bisa menjalankan ADD dua kali. | fungsi plpgsql: `SELECT ... FOR UPDATE` request PENDING, lalu terapkan dan tandai approved. | `test_approve_budget_request_batch_atomic_on_failure` |
| beasiswa | `modules/beasiswa/service.py:1711` `reject_budget_request_batch` | UPDATE request → REJECTED ×N (1719) | Tidak (status dicek per baris). | batch: atau satu UPDATE `WHERE id IN (...) AND status='PENDING'` (rowcount = jumlah ditolak). | `test_reject_budget_request_batch_atomic_on_failure` |

### Task 16: payment_memo bagian 1 (PAM records, lines, klaim)

`save_others_payment` (685): satu INSERT + rollback (§ Akuntansi rollback). `update_pam_gl_account`, `update_pam_status`, `update_pam_record`: satu UPDATE lalu `sync_pam_to_bank_setf` di panggilan terpisah (§ Rantai lintas fungsi). `bulk_update_pam_lines_dates` (516): satu unit per id, sengaja parsial (§ Rantai lintas fungsi).

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| payment_memo | `modules/payment_memo/service.py:964` `create_pam_record` (+ `generate_pam_number` 937) | INSERT pam_records (974) dengan `pam_no` dari max_seq+1 (957–961); UPDATE payment_beasiswa.pam ×N (990) | Ya: nomor dari scan `LIKE` + max Python; `pam_no` UNIQUE. | fungsi plpgsql `fn_create_pam_record(...)` (atau `fn_next_pam_no` + batch): penomoran → `pg_advisory_xact_lock(hashtext('pam_no:'\|\|company_code\|\|':'\|\|year))`. Dipakai juga oleh `add_payment_multi` (beasiswa) dan `create_pam_from_etf_pa`. | `test_create_pam_record_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:449` `upsert_pam_lines` (+ `_convert_advance_to_smt` 490) | UPDATE atau INSERT {pillar}_pam_lines (473/480); kalau ADVANCE + tgl_paid: UPDATE pam_records pillar=SMT (505) + INSERT smt_pam_lines (509) | Tidak (`pam_id` dari argumen; vendor advance dibaca dulu, dan nilainya tidak berubah). | batch: upsert (`INSERT ... ON CONFLICT (pam_id) DO UPDATE` kalau ada unique, atau cek exist dulu) + konversi advance. | `test_upsert_pam_lines_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:605` `save_klaim_payment` | Per baris: INSERT payment_beasiswa (641) + INSERT klaim_medical dengan `pb_id` (651); INSERT pam_records (665) | Ya: klaim butuh `payment_id`. `pam_no` dari user. | batch+currval: pasangan pb → klaim memakai `currval(... payment_beasiswa ...)`, lalu INSERT pam_records. | `test_save_klaim_payment_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:734` `save_smt_pam_transaction` | INSERT pam_records (791); INSERT pam_transaction_lines ×N dengan `pam_id` (806) | Ya: line butuh `pam_id`. | batch+currval: line memakai `currval(... pam_records ...)`. | `test_save_smt_pam_transaction_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:828` `save_pa_payment` | `insert_payment_rows` (INSERT pb ×N, rekam_medis, UPDATE {pa_tbl} on_process); INSERT pam_records (887); UPDATE payment_beasiswa.pam WHERE id IN (payment_ids) (904); UPDATE {pa_tbl} nomor_pam (921) | Ya: link pb.pam butuh id payment; rekam_medis butuh `payment_id`. | batch+currval: urutan diubah. INSERT pam_records dulu, lalu INSERT pb langsung dengan `pam=pam_no` (tidak perlu UPDATE by id; tidak ada FK pada pb.pam), rekam_medis via currval pb, lalu UPDATE PA. `pa_ids` dibaca sebelum batch. | `test_save_pa_payment_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:2451` `create_pam_from_etf_pa` | INSERT pam_records (2491) dengan `generate_pam_number`; UPDATE etf_pa nomor_pam + on_process (2506) | Ya: nomor PAM; total dari SUM line (bacaan). | fungsi plpgsql: penomoran → pakai `fn_create_pam_record` yang sama (advisory lock). | `test_create_pam_from_etf_pa_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1153` `delete_payment_beasiswa` | DELETE klaim_medical (1165); DELETE payment_beasiswa (1166) | Tidak. | batch: dua DELETE. | `test_delete_payment_beasiswa_atomic_on_failure` (payment_memo) |
| payment_memo | `modules/payment_memo/service.py:1172` `cancel_pam_record` | etf_agri: UPDATE etf_pa (1187) + DELETE pam_records (1192). Beasiswa: DELETE klaim_medical (1201), payment_beasiswa (1202), pam_records (1203), UPDATE {pa_tbl} open kalau tidak ada sisa (1228, loop 5 tabel) | Ya: `line_ids` dibaca sebelum DELETE; revert PA tergantung hitung sisa setelah DELETE. | batch: `line_ids` dan mapping line→pa_id dibaca sebelum batch; revert PA dengan `WHERE NOT EXISTS (...)`. | `test_cancel_pam_record_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1239` `reject_pam_record` | etf_agri: UPDATE etf_pa (1255) + UPDATE pam_records (1260). Beasiswa: UPDATE pb rejected (1277); UPDATE pam_records rejected (1291) atau total=SUM (1300); UPDATE {pa_tbl} rejected kalau tidak ada sisa (1327) | Ya: cabang header tergantung sisa aktif setelah UPDATE pb; total = SUM. | batch: cabang jadi `CASE WHEN EXISTS(...)` / subquery SUM; PA dengan `NOT EXISTS`. | `test_reject_pam_record_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1338` `remove_student_from_pam` | DELETE klaim_medical (1372); DELETE payment_beasiswa (1374); DELETE pam_records kalau kosong (1385) atau UPDATE total=SUM (1393); UPDATE {pa_tbl} open kalau tidak ada sisa (1421) | Ya: sisa dan total dihitung setelah DELETE. | batch: kondisi/total pindah ke SQL (`NOT EXISTS`, subquery SUM). | `test_remove_student_from_pam_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1433` `reject_student_from_pam` | UPDATE pb rejected (1467); UPDATE pam_records rejected (1478) atau total=SUM (1487); UPDATE {pa_tbl} rejected kalau tidak ada sisa (1513) | Ya: sama dengan `remove_student_from_pam`. | batch: sama (CASE/NOT EXISTS/SUM). | `test_reject_student_from_pam_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1794` `update_beasiswa_line_amount` | UPDATE payment_beasiswa.amount (1802); UPDATE pam_records total += diff (1805) | Ya: diff = baru − lama (lama dibaca dulu; bisa berubah oleh user lain). | batch: UPDATE pam_records dulu dengan `total_amount + (? - (SELECT amount FROM payment_beasiswa WHERE id=?))`, lalu UPDATE pb. Diff dihitung di SQL dalam transaksi yang sama. | `test_update_beasiswa_line_amount_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1810` `update_pam_and_application` | UPDATE pam_records (1851); rename cascade: UPDATE payment_beasiswa.pam (1858) + UPDATE {etf,app,sml,setf}_pa.nomor_pam (1863); UPDATE payment_application.notes (1871); lalu `sync_pam_to_bank_setf` (1882, panggilan terpisah) | Tidak (old/new pam_no dari bacaan + argumen). | batch: semua UPDATE independen. Tidak ada FK pada pb.pam/nomor_pam (dicek di `0002_schema.sql`), jadi urutan bebas. Sync bank: § Rantai lintas fungsi. | `test_update_pam_and_application_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:2531` `set_pam_complete_cascade` | UPDATE pam_records complete (2552); etf_agri: UPDATE etf_pa (2562); lain: UPDATE pb paid/complete (2572/2584/2590), UPDATE {pa_tbl} per pillar (2613); lalu `sync_pam_to_bank_setf` (2624) | Ya, lemah: `line_rows` per pillar dibaca setelah UPDATE pb (etf_pa_line_id/pillar tidak berubah oleh UPDATE itu). | batch: baca `line_rows` sebelum batch, lalu semua UPDATE dalam satu batch. Sync bank: § Rantai lintas fungsi. | `test_set_pam_complete_cascade_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:2629` `mark_beasiswa_lines_complete` | Per PAM: UPDATE pb complete (2675/2680); per PA header: UPDATE complete (2715) / partial (2723); UPDATE pam_records complete (2733) / partial (2738); `commit()` + `sync_pam_to_bank_setf` **di dalam loop** (2743–2744) | Ya: status 3 arah (complete/partial/tetap) per PA header dan per PAM, dihitung setelah UPDATE pb; dua user yang menandai baris berbeda di PAM yang sama bisa saling menimpa status. | fungsi plpgsql `fn_mark_beasiswa_lines_complete(payment_ids, tanggal, company_id)`: banyak cabang yang bergantung bacaan setelah tulis, plus race → `FOR UPDATE` pada pam_records yang terlibat. Satu PAM = satu unit atomik (loop per-PAM boleh tetap; lihat § Hal yang ambigu). | `test_mark_beasiswa_lines_complete_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:2755` `realize_advance_payment` | UPDATE pb realized/complete (2796); UPDATE pam_records pillar kalau semua complete (2808); UPDATE {lines_tbl}.jumlah_pembayaran (2823); UPDATE {pa_tbl} complete kalau tidak ada yang open (2844) | Ya: dua kondisi "sisa = 0" dihitung setelah UPDATE pb. | batch: kondisi pindah ke `WHERE NOT EXISTS (...)`; `pa_id` + sibling ids dibaca sebelum batch. | `test_realize_advance_payment_atomic_on_failure` |

### Task 17: payment_memo bagian 2 (routes, sisa service)

`add_vendor` (2919) / `update_vendor` (2941): satu statement + `except sqlite3.IntegrityError: rollback()` (§ Akuntansi rollback). `routes.py:41` `_handle_pam_attachment_upload`: satu UPDATE baca-ubah-tulis setelah upload Drive (§ Rantai lintas fungsi, § Error yang tertelan). `bulk_complete_pams` (2516): loop `set_pam_complete_cascade` per PAM, sengaja parsial.

| modul | file:fungsi | statement tulis | butuh hasil langkah sebelumnya? | pola | test atomik |
|---|---|---|---|---|---|
| payment_memo | `modules/payment_memo/service.py:66` `create_memo` (+ `generate_memo_number` 15) | INSERT payment_memo (75) dengan `memo_number` dari max_seq+1 (koneksi terpisah, 18–31); INSERT payment_memo_items ×N (83); UPDATE payment_beasiswa on_process + memo_id (96) | Ya: item dan pb butuh `memo_id`; nomor memo dari scan + max (`memo_number` UNIQUE). | fungsi plpgsql: penomoran → advisory lock `'memo_number:'\|\|company_code\|\|':'\|\|year`; item/pb memakai id hasil `RETURNING`. | `test_create_memo_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:139` `update_memo_status` | UPDATE payment_memo status (154); UPDATE payment_beasiswa complete (160) / open (166) | Tidak. | batch: dua UPDATE. **Catatan:** baris 175–177 memakai `pam_data`, `current_status`, `pam_id` yang tidak didefinisikan, jadi NameError setelah commit (bug lama, lihat § Hal yang ambigu). | `test_update_memo_status_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:183` `set_memo_tanggal_bayar` | UPDATE payment_memo (203); UPDATE payment_beasiswa (209); UPDATE {pa_tbl} ×5 tabel (230) | Tidak (`line_ids` dibaca di tengah, tapi tidak berubah oleh UPDATE sebelumnya). | batch: baca `line_ids` sebelum batch. | `test_set_memo_tanggal_bayar_atomic_on_failure` |
| payment_memo | `modules/payment_memo/service.py:1923` `update_draft_and_linked` | UPDATE payment_beasiswa (1941); UPDATE pam_records (1952); UPDATE payment_application (1963) | Tidak. | batch: tiga UPDATE independen. | `test_update_draft_and_linked_atomic_on_failure` |

---

## Rantai lintas fungsi (beberapa panggilan, bukan satu fungsi)

Ini bukan baris work item tersendiri. Modul pemilik harus memutuskan dan mencatat keputusannya di test.

1. **`sync_pam_to_bank_setf` setelah commit.** Dipanggil di koneksi terpisah setelah tulisan PAM: `payment_memo/service.py:1116` (`update_pam_status`), `:1148` (`update_pam_record`), `:1882` (`update_pam_and_application`), `:2624` (`set_pam_complete_cascade`), `:2744` (`mark_beasiswa_lines_complete`, di dalam loop). Fungsi ini didesain idempoten ("safe to call after ANY pam_records mutation"), jadi kalau gagal, panggilan sync berikutnya akan merekonsiliasi. Saran: biarkan terpisah (eventual), dengan `fn_sync_pam_to_bank_setf` yang atomik (Task 9). Untuk `mark_beasiswa_lines_complete`, fungsi plpgsql-nya boleh langsung memanggil `fn_sync_pam_to_bank_setf` di dalam transaksi.
2. **Upload lampiran Google Drive setelah create.** `etf_payment_application/routes.py:188` `create` (create_pa → upload Drive → UPDATE {pa_tbl}.attachment_file_id 241) dan `payment_memo/routes.py:41` `_handle_pam_attachment_upload` (setelah `save_pa_payment`/`save_klaim_payment`/`save_others_payment`/`save_smt_pam_transaction`, routes.py:764/814/830/846). I/O eksternal tidak bisa ikut transaksi DB; ini memang dua langkah. `_handle_pam_attachment_upload` juga baca-ubah-tulis (`existing + "," + new`, 65–68). Saran: satu UPDATE `attachment_file_id = COALESCE(NULLIF(attachment_file_id,'') \|\| ',', '') \|\| ?`.
3. **Loop dengan commit per unit (sengaja parsial).** `bulk_update_pam_lines_dates` (payment_memo:516, koneksi + commit per id, memanggil `upsert_pam_lines`), `bulk_complete_pams` (payment_memo:2516, per PAM), `mark_beasiswa_lines_complete` (commit per PAM di 2743). Semuanya melaporkan "x dari y". Saran: pertahankan atomisitas per unit, jangan seluruh loop.
4. **Preview nomor PAM lalu simpan.** `get_next_pam_no` (payment_memo:549, rute `ipay_next_pam_no`) menampilkan nomor; user lalu mengirimnya sebagai `pam_no` ke `save_*`. Dua user bisa mendapat nomor yang sama. UNIQUE `pam_records.pam_no` akan menolak yang kedua (`IntegrityError`), jadi tidak ada data rusak, hanya error ke user. Di luar inventaris atomik.

## Penomoran (MAX()+1 / COUNT()+1)

Tidak ada `MAX(...)+1` di SQL. Pola yang sama ada di Python (scan nomor lalu max/count + 1). Semuanya dijadikan fungsi plpgsql dengan advisory lock:

| file:baris | fungsi | cara | kolom UNIQUE | alur pemakai |
|---|---|---|---|---|
| `modules/payment_memo/service.py:15–31` | `generate_memo_number` | `LIKE` + regex max + 1 (koneksi sendiri) | `payment_memo.memo_number` | `create_memo` |
| `modules/payment_memo/service.py:937–961` | `generate_pam_number` | `LIKE` + regex max + 1 | `pam_records.pam_no` | `create_pam_record`, `create_pam_from_etf_pa`, `add_payment_multi`, `get_next_pam_no` (preview) |
| `modules/payment_application/service.py:63–66` | `create_application` | `COUNT(*)+1` per company | `payment_application.application_number` | `create_application` |
| `modules/etf_payment_application/service.py:54–59` | `_gen_pa_number` | `COUNT(*)+1` per company | `{pa_tbl}.pa_number` | `create_pa` |
| `modules/etf_payment_application/service.py:62–72` | `_gen_nomor_pam` | `COUNT(*)+1` per bulan | tidak ada | `update_pa` |

`sponsorship/service.py:783` (`seq_by_year`) hanya nomor tampilan laporan MR, tidak ditulis ke DB. Di luar inventaris.

## Akuntansi `rollback()` (24 situs)

| file:baris | fungsi | status |
|---|---|---|
| `beasiswa/service.py:490` | `add_payment_multi` | alur (Task 15, plpgsql) |
| `beasiswa/service.py:844` | `update_payment_row` | alur (Task 15): sebelum tulisan apa pun, no-op |
| `beasiswa/service.py:852` | `update_payment_row` | alur (Task 15): dimaksudkan membatalkan UPDATE 836 |
| `general_ledger/service.py:101` | `replace_year` | alur (Task 14) |
| `management_report/category_map.py:212` | `sync_categories` | alur (Task 15) |
| `management_report/coa_map.py:272` | `sync_coa` | alur (Task 15) |
| `management_report/service.py:100` | `save_upload` | alur (Task 15) |
| `payment_memo/service.py:104` | `create_memo` | alur (Task 17) |
| `payment_memo/service.py:677` | `save_klaim_payment` | alur (Task 16) |
| `payment_memo/service.py:726` | `save_others_payment` | satu statement: rollback jadi no-op, hapus saja |
| `payment_memo/service.py:820` | `save_smt_pam_transaction` | alur (Task 16) |
| `payment_memo/service.py:929` | `save_pa_payment` | alur (Task 16) |
| `payment_memo/service.py:2935` | `add_vendor` | satu statement + `except sqlite3.IntegrityError`: aman (fhdb.IntegrityError subclass) |
| `payment_memo/service.py:2957` | `update_vendor` | sama dengan `add_vendor` |
| `sponsorship/service.py:840` | `create_transaksi_bulk` | alur (Task 13): **setelah INSERT sebelumnya** |
| `sponsorship/service.py:846` | `create_transaksi_bulk` | alur (Task 13): **setelah INSERT sebelumnya** |
| `sponsorship/service.py:869` | `create_transaksi_bulk` | alur (Task 13) |
| `sponsorship/service.py:891` | `delete_transaksi` | satu statement: no-op |
| `sponsorship/service.py:952` | `sync_transaksi_excel` | alur (Task 13): **setelah tulisan baris sebelumnya** |
| `sponsorship/service.py:955` | `sync_transaksi_excel` | alur (Task 13): **setelah tulisan baris sebelumnya** |
| `sponsorship/service.py:970` | `sync_transaksi_excel` | alur (Task 13): **setelah tulisan baris sebelumnya** |
| `sponsorship/service.py:1020` | `sync_transaksi_excel` | alur (Task 13) |
| `spt_badan/service.py:113` | `create_period` | satu statement + IntegrityError: aman |
| `spt_badan/service.py:224` | `take_snapshot` | alur (Task 14) |

Total 24: 19 milik alur di tabel utama, 5 satu-statement/aman (`save_others_payment`, `add_vendor`, `update_vendor`, `delete_transaksi`, `create_period`). Per file: 7 payment_memo, 8 sponsorship, 3 beasiswa, 2 spt_badan, 1 general_ledger, 1 category_map, 1 coa_map, 1 MR service.

## Akuntansi `executemany` (9) dan `executescript` (6)

| file:baris | jenis | status |
|---|---|---|
| `general_ledger/service.py:62` | executescript `_table_ddl` | alur `ensure_schema` GL (Task 14, batch) |
| `general_ledger/service.py:63` | executescript `_LOG_DDL` | alur `ensure_schema` GL (Task 14, batch) |
| `general_ledger/service.py:89` | executemany INSERT GL | alur `replace_year` (Task 14) |
| `management_report/category_map.py:111` | executescript `_DDL` | hapus (tabel statis); seed tetap: alur `ensure_schema` category_map (Task 15) |
| `management_report/category_map.py:113` | executemany seed alias | alur `ensure_schema` category_map (Task 15) |
| `management_report/category_map.py:198` | executemany INSERT category_map | alur `sync_categories` (Task 15) |
| `management_report/coa_map.py:179` | executescript `_DDL` | hapus (tabel statis, Task 15) |
| `management_report/coa_map.py:257` | executemany INSERT coa_map | alur `sync_coa` (Task 15) |
| `management_report/coa_map.py:262` | executemany INSERT cc_map | alur `sync_coa` (Task 15) |
| `management_report/service.py:48` | executescript `_DDL` | hapus (tabel statis, Task 15) |
| `management_report/service.py:88` | executemany INSERT mr_append | alur `save_upload` (Task 15) |
| `spt_badan/service.py:85` | executescript `_DDL` | hapus (tabel statis, Task 14) |
| `spt_badan/service.py:205` | executemany spt_gl_line | alur `take_snapshot` (Task 14) |
| `spt_badan/service.py:212` | executemany spt_exception | alur `take_snapshot` (Task 14) |
| `spt_badan/service.py:216` | executemany spt_control | alur `take_snapshot` (Task 14) |

`executemany` sendiri atomik (satu panggilan). Masalahnya, statement sebelum dan sesudahnya ada di panggilan lain. Untuk masuk ke `batch`, ekspansikan menjadi item per baris (`[(sql, row) for row in rows]`).

## Error database yang tertelan

`fhdb.errors.OperationalError` (DB tidak terjangkau) adalah subclass `sqlite3.OperationalError` dan `Exception`. Handler `@app.errorhandler(OperationalError)` di `app.py:122` mengembalikan 503. Handler di bawah menangkapnya lebih dulu, sehingga outage berubah jadi 200/500 atau sukses palsu. Perbaikan yang disarankan: tambahkan `except fhdb.errors.OperationalError: raise` sebelum `except Exception`, atau persempit `except`-nya.

Tidak ada `except sqlite3.OperationalError` di kode modul. Semua `except:` telanjang (`beasiswa/service.py:1561`, `payment_memo/exports.py:1061,1511`, `payment_memo/service.py:2007,2049`) dan `except Exception: pass` (`management_report/parser.py:139`) hanya membungkus parsing tanggal/angka/workbook, bukan DB.

| file:baris | fungsi | membungkus | yang tertelan |
|---|---|---|---|
| `modules/payment_memo/routes.py:71` | `_handle_pam_attachment_upload` | upload Drive + SELECT/UPDATE pam_records.attachment_file_id | Outage → respons tetap `ok: True` + "(Upload GDrive gagal: …)". File sudah ada di Drive tapi tidak tertaut. |
| `modules/etf_payment_application/routes.py:244` | `create` | upload Drive + UPDATE {pa_tbl}.attachment_file_id (241) | Outage → 200 `ok: True` "gagal upload lampiran". Lampiran tidak tertaut. |
| `modules/management_report/routes.py:467` | `mapping_page` | `combine_sources.gl_rows/sponsor_rows` (baca DB) | Outage → halaman 200 dengan `panel_error`, bukan 503. |
| `modules/beasiswa/service.py:489` | `add_payment_multi` | seluruh alur | Outage → `{"ok": False, "pesan": "Gagal menyimpan payment: …"}` (200). |
| `modules/payment_memo/service.py:103` | `create_memo` | seluruh alur | Outage → `ok: False` (200). |
| `modules/payment_memo/service.py:676` | `save_klaim_payment` | seluruh alur | Outage → `ok: False` (200). |
| `modules/payment_memo/service.py:725` | `save_others_payment` | INSERT pam_records | Outage → `ok: False` (200). |
| `modules/payment_memo/service.py:819` | `save_smt_pam_transaction` | seluruh alur | Outage → `ok: False` (200). |
| `modules/payment_memo/service.py:928` | `save_pa_payment` | seluruh alur | Outage → `ok: False` (200). |
| `modules/sponsorship/service.py:868` | `create_transaksi_bulk` | seluruh alur | Outage → `ok: False` (200). |
| `modules/sponsorship/service.py:890` | `delete_transaksi` | DELETE | Outage → `ok: False` (200). |
| `modules/sponsorship/service.py:1019` | `sync_transaksi_excel` | seluruh alur | Outage → `ok: False` (200). |
| `modules/general_ledger/routes.py:114` | `sync_excel` | `gl_sync.sync_rows` → `replace_year` | Outage → 500 "Sync gagal, data lama tidak berubah" (dengan fhdb klaim "tidak berubah" bisa salah). |
| `modules/management_report/routes.py:435` | `sync_mapping` | `coa_map.sync_coa` | Outage → 500, bukan 503. |
| `modules/management_report/routes.py:522` | `category_sync` | `category_map.sync_categories` | Outage → 500, bukan 503. |
| `modules/spt_badan/routes.py:118` | `snapshot` | `service.take_snapshot` | Outage → 500, bukan 503. |
| `modules/sahabat_etf/routes.py:161` | `api_report` | `build_report_data` (baca DB) | Outage → 500 + menulis traceback ke `C:/Financehub/last_500_error.txt`. |
| `modules/payment_memo/routes.py:758` | `ipay_next_pam_no` | `get_next_pam_no` (baca DB) | Outage → 500 dengan `pam_no: "ERROR-…"`. |

Dicatat tapi tidak perlu diubah:

- `tasks/flow_backup.py:123` `run_excel_backups`: job latar; `export_fn` membaca DB; error dicatat dan dilanjut ke modul berikutnya. Wajar untuk job tanpa HTTP.
- `except sqlite3.IntegrityError` (`payment_memo/service.py:2934,2956`, `spt_badan/service.py:112`, `sponsorship/migrate.py:98`): hanya IntegrityError, outage tetap naik.

## Skrip one-off/import

Bukan work item wajib Task 9–17. Modul pemilik yang memutuskan.

| file | apa yang ditulis | catatan |
|---|---|---|
| `modules/sponsorship/migrate.py:37` `migrate_sponsorship_from_excel` | `seed_perusahaan` (commit sendiri) lalu INSERT sponsorship_transaksi per baris (78) dengan skip `IntegrityError` per baris | Skip per baris tidak bisa di-batch begitu saja (satu error menggagalkan seluruh batch). Pilihan: pre-validasi + `ON CONFLICT DO NOTHING`, atau terima per-baris (importer satu kali). Plan Task 13: pastikan `fhdb.errors.IntegrityError` tertangkap (sudah, karena subclass). |
| `modules/sop/migrate.py:50` `migrate_sop_documents` | `create_document` per file (commit per dokumen) | Importer satu kali. Per-dokumen sudah atomik (satu INSERT). |
| `app/migrasi_pam_smt.py` | UPDATE pam_records + UPDATE/INSERT smt_pam_lines per baris CSV, satu commit (86–111) | Lewat `get_conn` → akan kena PG. Multi-langkah. |
| `app/import_siswa.py` | INSERT siswa per baris (`get_conn`) | Importer. |
| `app/migrate_status.py` | 12 UPDATE status (22–36) | Migrasi status lama; idempoten. |
| `app/fix_etf_pa_line_id_fk.py`, `app/import_vendors.py` | DDL/rebuild tabel lewat `sqlite3.connect(DB_PATH)` langsung | Hanya SQLite. Usang setelah migrasi. |
| `app/task45.py`, `app/update.py` | INSERT siswa / satu UPDATE perbaikan data | Skrip ad-hoc. |
| `app/database.py` | `init_db` seed-only (Task 4) | Di luar scope. |

## Hal yang ambigu (perlu keputusan di task modul)

1. **Ukuran payload vs atomik (Task 14, 15).** `replace_year` (GL setahun), `take_snapshot` (semua baris GL setahun → spt_gl_line), dan `save_upload` (mr_append) bisa melewati batas ukuran request HTTPS. Plan Task 14 meminta potongan ≤1000 baris, yang bertentangan dengan "satu panggilan = satu transaksi". Rekomendasi: staging table + fungsi plpgsql swap (§ Task 14). Kalau ukuran nyata selalu kecil, satu batch sudah cukup. Ukur dulu jumlah baris maksimum per file/tahun.
2. **`mark_beasiswa_lines_complete`: atomik per PAM atau seluruh panggilan?** Kode sekarang commit per PAM. Inventaris menganggap satu PAM = satu unit. Test atomik memaksa kegagalan di dalam satu PAM.
3. **Batch dengan kondisi SQL vs plpgsql untuk cascade PAM** (`cancel_pam_record`, `reject_pam_record`, `remove_student_from_pam`, `reject_student_from_pam`, `realize_advance_payment`, `delete_payment_row`). Semua dipetakan ke batch dengan `NOT EXISTS`/subquery SUM. Kalau penulisan ulang SQL-nya terlalu rumit atau mengubah perilaku, fungsi plpgsql adalah fallback yang sah.
4. **`update_memo_status`** (`payment_memo/service.py:175–177`) memakai `pam_data`, `current_status`, `pam_id` yang tidak didefinisikan. Setiap panggilan ke fungsi ini akan NameError setelah commit. Ini bug lama, bukan dari migrasi. Task 17 sebaiknya menandainya (test menangkap NameError, atau hapus blok mati itu dengan persetujuan).
5. **Duplikat definisi** `update_budget_row` di `beasiswa/service.py` (baris 250 dan 1594). Yang kedua menimpa yang pertama. Keduanya satu statement, jadi tidak masuk inventaris, tapi membingungkan.
6. **Efek samping non-DB dalam alur:** `save_klaim_payment` (`payment_memo/service.py:618–620`) menulis payload ke `C:/Financehub/debug_payload.txt` setiap panggilan, dan `sahabat_etf/routes.py:163` menulis traceback ke `C:/Financehub/last_500_error.txt`. Tidak memengaruhi atomik, tapi akan gagal di host yang tidak punya path itu.
7. **Koneksi tidak ditutup** di `create_transaksi_bulk` dan `sync_transaksi_excel` (tidak ada `finally: conn.close()`). Tidak berdampak di fhdb (koneksi stateless), dicatat saja.

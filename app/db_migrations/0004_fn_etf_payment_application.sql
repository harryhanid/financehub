-- 0004_fn_etf_payment_application.sql
-- Penomoran PA dan nomor PAM modul etf_payment_application yang aman dari race (Task 11, atomic-flows.md).
-- Placeholder {{schema}} diganti apply_migrations.py.
--
-- Dulu _gen_pa_number / _gen_nomor_pam (service.py) membaca COUNT(*) di satu panggilan lalu INSERT/UPDATE
-- di panggilan lain; dua request bersamaan mendapat nomor yang sama. Sekarang nomor dialokasikan oleh
-- fungsi di bawah, yang dipanggil DI DALAM statement tulisnya (INSERT ... VALUES (..., fn(...)) atau
-- UPDATE ... SET nomor_pam = fn(...)) sebagai bagian dari satu conn.batch. pg_advisory_xact_lock
-- ditahan sampai batch commit, jadi alokasi + tulisan berikutnya berurutan per tabel/company.
-- Fungsi VOLATILE: COUNT di dalamnya memakai snapshot baru setelah lock didapat, sehingga baris yang
-- di-commit pemegang lock sebelumnya ikut terhitung.
--
-- Format nomor sama persis dengan kode lama (Python f"{n:03d}" tidak memotong angka > 3 digit):
--   PA : PA/<prefix>/<count+1 3 digit>/<year>            (count = semua baris tabel PA milik company)
--   PAM: <count+1 3 digit>-<prefix>-<mm>-<yyyy>           (count = baris company dengan nomor_pam
--        IS NOT NULL dan strftime('%Y-%m', created_at) = '<yyyy>-<mm>')
-- Tahun/bulan dikirim dari Python (datetime.now() lokal server), sama dengan versi SQLite.
-- Nama tabel dinamis (tab agri/app/sml/setf/energy) dan dicek terhadap daftar tetap.
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak
-- memecah di ';' di dalam badan.

create or replace function {{schema}}.fn_etf_pa_next_pa_number(
    p_pa_tbl text,
    p_company_id bigint,
    p_prefix text,
    p_year text
)
returns text
language plpgsql
volatile
as '
declare
    v_count bigint;
begin
    if p_pa_tbl is null or p_pa_tbl not in (''etf_pa'', ''app_pa'', ''sml_pa'', ''setf_pa'', ''energy_pa'') then
        raise exception ''fn_etf_pa_next_pa_number: tabel % tidak diizinkan'', coalesce(p_pa_tbl, ''<null>'');
    end if;
    perform pg_advisory_xact_lock(hashtext(''pa:'' || p_pa_tbl || '':'' || p_company_id::text));
    execute format(''select count(*) from %I.%I where "company_id" = $1'', ''{{schema}}'', p_pa_tbl)
       into v_count
      using p_company_id;
    return ''PA/'' || p_prefix || ''/''
           || lpad((v_count + 1)::text, greatest(3, length((v_count + 1)::text)), ''0'')
           || ''/'' || p_year;
end
';

create or replace function {{schema}}.fn_etf_pa_next_nomor_pam(
    p_pa_tbl text,
    p_company_id bigint,
    p_prefix text,
    p_mm text,
    p_yyyy text
)
returns text
language plpgsql
volatile
as '
declare
    v_count bigint;
begin
    if p_pa_tbl is null or p_pa_tbl not in (''etf_pa'', ''app_pa'', ''sml_pa'', ''setf_pa'', ''energy_pa'') then
        raise exception ''fn_etf_pa_next_nomor_pam: tabel % tidak diizinkan'', coalesce(p_pa_tbl, ''<null>'');
    end if;
    perform pg_advisory_xact_lock(hashtext(''nomor_pam:'' || p_pa_tbl || '':'' || p_company_id::text));
    execute format(''select count(*) from %I.%I where "company_id" = $1 and "nomor_pam" is not null ''
                   || ''and %I.fh_strftime(''''%%Y-%%m'''', "created_at") = $2'',
                   ''{{schema}}'', p_pa_tbl, ''{{schema}}'')
       into v_count
      using p_company_id, p_yyyy || ''-'' || p_mm;
    return lpad((v_count + 1)::text, greatest(3, length((v_count + 1)::text)), ''0'')
           || ''-'' || p_prefix || ''-'' || p_mm || ''-'' || p_yyyy;
end
';

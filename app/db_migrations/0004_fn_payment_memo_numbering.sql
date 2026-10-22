-- 0004_fn_payment_memo_numbering.sql
-- Alokasi nomor PAM (pam_records.pam_no) yang aman dari race (R24, atomic-flows.md Task 15/16).
-- Placeholder {{schema}} diganti apply_migrations.py.
--
-- Dulu generate_pam_number (modules/payment_memo/service.py) membaca semua pam_no yang cocok di satu
-- panggilan, mengambil max di Python, lalu INSERT di panggilan lain; dua request bersamaan bisa
-- mendapat nomor sama (pam_no UNIQUE -> IntegrityError). Sekarang nomor dihitung oleh fungsi ini,
-- yang dipanggil DI DALAM statement tulisnya (INSERT INTO pam_records (..., pam_no, ...) VALUES
-- (..., fn_next_pam_no(?, ?, ?, ?), ...)) sebagai bagian dari satu conn.batch. pg_advisory_xact_lock
-- ditahan sampai batch commit, jadi alokasi + INSERT berurutan per kode/tahun. Fungsi VOLATILE: SELECT
-- di dalamnya memakai snapshot baru setelah lock didapat, sehingga nomor yang di-commit pemegang
-- lock sebelumnya ikut terhitung.
--
-- Perilaku sama persis dengan generate_pam_number:
--   * kandidat: pam_records milik p_company_id dengan pam_no LIKE 'PAM-%-<code>-%-<year>'
--     (LIKE SQLite tidak punya karakter escape -> ESCAPE '' di sini) DAN cocok regex Python
--     re.match(r'PAM-(\d+)-<code>-\d{2}-<year>') (berlabuh di awal, tidak di akhir; kode/tahun
--     di-escape seperti re.escape). Regex case-sensitive, jadi LIKE SQLite yang case-insensitive tidak
--     menambah kandidat; LIKE Postgres yang case-sensitive memberi himpunan yang sama.
--   * urutan reset hanya saat tahun berganti (semua bulan dalam tahun ikut dihitung), per company_id + kode.
--   * hasil: 'PAM-' || (max+1, minimal 3 digit, tidak dipotong kalau > 999) || '-<code>-<month>-<year>'.
-- Kunci lock: hashtext('pam_no:' || <code> || ':' || <year>).
-- Dipakai oleh beasiswa add_payment_multi (Task 15); payment_memo create_pam_record /
-- generate_pam_number / create_pam_from_etf_pa memakai fungsi yang sama (Task 16).
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak
-- memecah di ';' di dalam badan.

create or replace function {{schema}}.fn_next_pam_no(
    p_company_id bigint,
    p_company_code text,
    p_year text,
    p_month text
)
returns text
language plpgsql
volatile
as '
declare
    v_re  text;
    v_max numeric;
    v_next text;
begin
    perform pg_advisory_xact_lock(hashtext(''pam_no:'' || p_company_code || '':'' || p_year));
    -- re.escape: semua karakter selain huruf/angka/_ diberi backslash (di ARE, backslash + karakter
    -- non-alfanumerik = karakter itu sendiri).
    v_re := ''^PAM-([0-9]+)-''
            || regexp_replace(p_company_code, ''([^A-Za-z0-9_])'', ''\\\1'', ''g'')
            || ''-[0-9]{2}-''
            || regexp_replace(p_year, ''([^A-Za-z0-9_])'', ''\\\1'', ''g'');
    select coalesce(max(substring("pam_no" from v_re)::numeric), 0)
      into v_max
      from {{schema}}."pam_records"
     where "company_id" = p_company_id
       and "pam_no" like ''PAM-%-'' || p_company_code || ''-%-'' || p_year escape ''''
       and "pam_no" ~ v_re;
    v_next := (v_max + 1)::text;
    return ''PAM-'' || lpad(v_next, greatest(3, length(v_next)), ''0'')
           || ''-'' || p_company_code || ''-'' || p_month || ''-'' || p_year;
end
';


-- Alokasi nomor memo (payment_memo.memo_number UNIQUE) untuk create_memo (atomic-flows.md Task 17).
-- Dulu generate_memo_number membaca memo_number yang cocok di koneksi sendiri, mengambil max di
-- Python, lalu create_memo INSERT di panggilan lain (race -> nomor kembar). Sekarang dipanggil DI
-- DALAM INSERT payment_memo pada satu conn.batch; advisory lock 'memo_number:<code>:<year>' ditahan
-- sampai batch commit.
-- Perilaku sama persis dengan generate_memo_number:
--   * kandidat: payment_memo milik p_company_id yang cocok regex Python
--     re.match(r'PAM/<code>/<year>/(\d+)') (berlabuh di awal, tidak di akhir; kode/tahun di-escape
--     seperti re.escape). Regex itu case-sensitive dan setiap kecocokannya pasti juga lolos filter
--     SQLite `LIKE 'PAM/<code>/<year>/%'`, jadi filter LIKE tidak menambah/mengurangi kandidat.
--   * hasil: 'PAM/<code>/<year>/' || (max+1, minimal 3 digit, tidak dipotong kalau > 999).
create or replace function {{schema}}.fn_next_memo_no(
    p_company_id bigint,
    p_company_code text,
    p_year text
)
returns text
language plpgsql
volatile
as '
declare
    v_re  text;
    v_max numeric;
    v_next text;
begin
    perform pg_advisory_xact_lock(hashtext(''memo_number:'' || p_company_code || '':'' || p_year));
    v_re := ''^PAM/''
            || regexp_replace(p_company_code, ''([^A-Za-z0-9_])'', ''\\\1'', ''g'')
            || ''/''
            || regexp_replace(p_year, ''([^A-Za-z0-9_])'', ''\\\1'', ''g'')
            || ''/([0-9]+)'';
    select coalesce(max(substring("memo_number" from v_re)::numeric), 0)
      into v_max
      from {{schema}}."payment_memo"
     where "company_id" = p_company_id
       and "memo_number" ~ v_re;
    v_next := (v_max + 1)::text;
    return ''PAM/'' || p_company_code || ''/'' || p_year || ''/''
           || lpad(v_next, greatest(3, length(v_next)), ''0'');
end
';

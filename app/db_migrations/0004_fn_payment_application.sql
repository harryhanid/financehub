-- 0004_fn_payment_application.sql
-- Penomoran payment_application.application_number yang aman dari race (Task 9, atomic-flows.md).
-- Placeholder {{schema}} diganti apply_migrations.py.
--
-- fn_create_payment_application: dulu create_application membaca COUNT(*) lalu INSERT di dua
-- panggilan; dua request bersamaan mendapat nomor sama dan saling tabrak di UNIQUE.
-- Sekarang COUNT + INSERT jalan dalam satu transaksi di bawah advisory lock per company_id.
-- Format nomor sama persis dengan kode lama: APP/<company_id>/<year>/<count+1 4 digit>.
-- (Perilaku COUNT dipertahankan: setelah ada baris dihapus, nomor bisa bentrok -> IntegrityError.)
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak
-- memecah di ';' di dalam badan.

create or replace function {{schema}}.fn_create_payment_application(
    p_company_id bigint,
    p_memo_id bigint,
    p_year text,
    p_submitted_at text,
    p_target_payment_date text,
    p_notes text,
    p_created_at text
)
returns table (id bigint, application_number text)
language plpgsql
volatile
as '
declare
    v_count bigint;
    v_number text;
    v_id bigint;
begin
    perform pg_advisory_xact_lock(hashtext(''payment_application:'' || p_company_id::text));
    select count(*) into v_count
      from {{schema}}."payment_application" pa
     where pa."company_id" = p_company_id;
    -- lpad tanpa memotong (Python f"{n:04d}" tidak memotong angka > 4 digit)
    v_number := ''APP/'' || p_company_id::text || ''/'' || p_year || ''/''
                || lpad((v_count + 1)::text, greatest(4, length((v_count + 1)::text)), ''0'');
    insert into {{schema}}."payment_application"
        ("company_id", "memo_id", "application_number", "submitted_at", "target_payment_date",
         "notes", "status", "created_at")
    values (p_company_id, p_memo_id, v_number, p_submitted_at, p_target_payment_date,
            p_notes, ''open'', p_created_at)
    returning {{schema}}."payment_application"."id" into v_id;
    return query select v_id, v_number;
end
';

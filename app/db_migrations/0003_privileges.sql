-- 0003_privileges.sql
-- Hak akses schema FinanceHub + Row Level Security. Placeholder {{schema}} diganti apply_migrations.py.
--
-- - service_role (dipakai PostgREST saat memanggil public.fh_exec) mendapat usage + create pada schema
--   (create: general_ledger membuat tabel per entitas/tahun saat sync), semua hak atas tabel & sequence,
--   dan default privileges untuk objek baru.
-- - RLS diaktifkan untuk semua tabel di schema tanpa policy: anon/authenticated tidak bisa membaca apa
--   pun lewat PostgREST; service_role punya BYPASSRLS.
-- Role service_role tidak ada di Postgres lokal (test), jadi grant ke role itu bersyarat (pg_roles).
-- Badan DO ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) memecah file ini
-- dengan benar: ';' di dalam literal tidak dianggap pemisah statement.

do '
declare
    r record;
begin
    if exists (select 1 from pg_roles where rolname = ''service_role'') then
        execute ''grant usage, create on schema {{schema}} to service_role'';
        execute ''grant all on all tables in schema {{schema}} to service_role'';
        execute ''grant all on all sequences in schema {{schema}} to service_role'';
        execute ''alter default privileges in schema {{schema}} grant all on tables to service_role'';
        execute ''alter default privileges in schema {{schema}} grant all on sequences to service_role'';
    end if;
    for r in select tablename from pg_tables where schemaname = ''{{schema}}'' loop
        execute format(''alter table {{schema}}.%I enable row level security'', r.tablename);
    end loop;
end
';

-- 0007_prportal_api.sql
-- API publik PR Portal: PR Portal (Apps Script) memanggil PostgREST RPC dengan key anon/publishable.
-- anon HANYA boleh memanggil empat fungsi public.prp_* di bawah. Tiap fungsi memverifikasi p_key
-- (sha256 hex dicocokkan ke public.prp_keys, revoked_at is null) lalu meneruskan ke
-- <schema>.fn_prp_* (0006) milik schema kunci itu. Schema HANYA berasal dari prp_keys (check list),
-- tidak pernah dari masukan pemanggil.
--
-- File ini tidak memakai {{schema}}: objek di public. apply_migrations.py menerapkannya per schema;
-- semua statement idempoten (create ... if not exists / create or replace / revoke / grant).
-- Badan fungsi & DO ditulis sebagai literal '...' (bukan $$) karena split_script (fhdb.sqlbind).
-- Role Supabase (anon/authenticated/service_role) tidak ada di Postgres test lokal: grant/revoke
-- ke role itu bersyarat pg_roles.

create table if not exists public.prp_keys (
    key_hash    text primary key,
    schema_name text not null check (schema_name in ('financehub', 'financehub_staging', 'financehub_test')),
    label       text not null,
    created_at  timestamptz not null default now(),
    revoked_at  timestamptz
);

alter table public.prp_keys enable row level security;
revoke all on table public.prp_keys from public;

-- Kunci -> schema. Helper internal: bukan bagian API (EXECUTE dicabut dari semua role klien).
create or replace function public.prp_key_schema(p_key text)
returns text
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_schema text;
begin
    if p_key is null or length(p_key) = 0 then
        raise exception ''prp: kunci tidak valid'' using errcode = ''42501'';
    end if;
    select k.schema_name into v_schema
      from public.prp_keys k
     where k.key_hash = encode(sha256(convert_to(p_key, ''UTF8'')), ''hex'')
       and k.revoked_at is null;
    if v_schema is null or v_schema not in (''financehub'', ''financehub_staging'', ''financehub_test'') then
        raise exception ''prp: kunci tidak valid'' using errcode = ''42501'';
    end if;
    return v_schema;
end
';

create or replace function public.prp_search_siswa(p_key text, p_query text)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_search_siswa($1)'', public.prp_key_schema(p_key))
       into v_result using p_query;
    return v_result;
end
';

create or replace function public.prp_search_vendor(p_key text, p_query text)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_search_vendor($1)'', public.prp_key_schema(p_key))
       into v_result using p_query;
    return v_result;
end
';

create or replace function public.prp_budget_siswa(p_key text, p_code text)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_budget_siswa($1)'', public.prp_key_schema(p_key))
       into v_result using p_code;
    return v_result;
end
';

create or replace function public.prp_submit_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_submit_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_update_siswa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_update_siswa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_pa_for_print(p_key text, p_pa_number text, p_requested_by text)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_pa_for_print($1, $2)'', public.prp_key_schema(p_key))
       into v_result using p_pa_number, p_requested_by;
    return v_result;
end
';

create or replace function public.prp_pa_status(p_key text, p_numbers jsonb)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_pa_status($1)'', public.prp_key_schema(p_key))
       into v_result using p_numbers;
    return v_result;
end
';

create or replace function public.prp_serah_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_serah_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_terima_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_terima_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_tolak_serah_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_tolak_serah_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_list_serah(p_key text)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_list_serah()'', public.prp_key_schema(p_key))
       into v_result;
    return v_result;
end
';

create or replace function public.prp_verifikasi_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_verifikasi_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_tolak_verifikasi_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_tolak_verifikasi_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_teruskan_pa(p_key text, p_payload jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_teruskan_pa($1)'', public.prp_key_schema(p_key))
       into v_result using p_payload;
    return v_result;
end
';

create or replace function public.prp_list_verifikasi(p_key text)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_list_verifikasi()'', public.prp_key_schema(p_key))
       into v_result;
    return v_result;
end
';

create or replace function public.prp_serah_log(p_key text, p_pa_number text)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_result jsonb;
begin
    execute format(''select %I.fn_prp_serah_log($1)'', public.prp_key_schema(p_key))
       into v_result using p_pa_number;
    return v_result;
end
';

-- EXECUTE default PUBLIC dicabut. Supabase memberi default privileges di public ke anon/authenticated
-- untuk tabel & fungsi baru, jadi dicabut eksplisit; lalu anon hanya mendapat EXECUTE keempat wrapper.
revoke all on function public.prp_key_schema(text) from public;
revoke all on function public.prp_search_siswa(text, text) from public;
revoke all on function public.prp_update_siswa(text, jsonb) from public;
revoke all on function public.prp_search_vendor(text, text) from public;
revoke all on function public.prp_budget_siswa(text, text) from public;
revoke all on function public.prp_submit_pa(text, jsonb) from public;
revoke all on function public.prp_pa_for_print(text, text, text) from public;
revoke all on function public.prp_pa_status(text, jsonb) from public;
revoke all on function public.prp_serah_pa(text, jsonb) from public;
revoke all on function public.prp_terima_pa(text, jsonb) from public;
revoke all on function public.prp_tolak_serah_pa(text, jsonb) from public;
revoke all on function public.prp_list_serah(text) from public;
revoke all on function public.prp_verifikasi_pa(text, jsonb) from public;
revoke all on function public.prp_tolak_verifikasi_pa(text, jsonb) from public;
revoke all on function public.prp_teruskan_pa(text, jsonb) from public;
revoke all on function public.prp_list_verifikasi(text) from public;
revoke all on function public.prp_serah_log(text, text) from public;

do '
declare
    r text;
begin
    foreach r in array array[''anon'', ''authenticated''] loop
        if exists (select 1 from pg_roles where rolname = r) then
            execute format(''revoke all on table public.prp_keys from %I'', r);
            execute format(''revoke all on function public.prp_key_schema(text) from %I'', r);
            execute format(''revoke all on function public.prp_search_siswa(text, text) from %I'', r);
            execute format(''revoke all on function public.prp_update_siswa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_search_vendor(text, text) from %I'', r);
            execute format(''revoke all on function public.prp_budget_siswa(text, text) from %I'', r);
            execute format(''revoke all on function public.prp_submit_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_pa_for_print(text, text, text) from %I'', r);
            execute format(''revoke all on function public.prp_pa_status(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_serah_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_terima_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_tolak_serah_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_list_serah(text) from %I'', r);
            execute format(''revoke all on function public.prp_verifikasi_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_tolak_verifikasi_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_teruskan_pa(text, jsonb) from %I'', r);
            execute format(''revoke all on function public.prp_list_verifikasi(text) from %I'', r);
            execute format(''revoke all on function public.prp_serah_log(text, text) from %I'', r);
        end if;
    end loop;
    if exists (select 1 from pg_roles where rolname = ''anon'') then
        execute ''grant execute on function public.prp_search_siswa(text, text) to anon'';
        execute ''grant execute on function public.prp_update_siswa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_search_vendor(text, text) to anon'';
        execute ''grant execute on function public.prp_budget_siswa(text, text) to anon'';
        execute ''grant execute on function public.prp_submit_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_pa_for_print(text, text, text) to anon'';
        execute ''grant execute on function public.prp_pa_status(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_serah_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_terima_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_tolak_serah_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_list_serah(text) to anon'';
        execute ''grant execute on function public.prp_verifikasi_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_tolak_verifikasi_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_teruskan_pa(text, jsonb) to anon'';
        execute ''grant execute on function public.prp_list_verifikasi(text) to anon'';
        execute ''grant execute on function public.prp_serah_log(text, text) to anon'';
    end if;
    if exists (select 1 from pg_roles where rolname = ''service_role'') then
        execute ''grant all on table public.prp_keys to service_role'';
    end if;
end
';

notify pgrst, 'reload schema';

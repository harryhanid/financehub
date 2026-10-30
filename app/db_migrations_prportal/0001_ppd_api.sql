-- 0001_ppd_api.sql
-- API publik data PR Portal (Sheets -> Supabase). PR Portal (Apps Script) memanggil PostgREST RPC
-- dengan key anon/publishable. anon HANYA boleh memanggil empat fungsi publik di bawah:
--   public.ppd_select / ppd_upsert / ppd_delete / ppd_stats.
-- Tiap fungsi memverifikasi p_key (sha256 hex dicocokkan ke public.ppd_keys, revoked_at is null);
-- schema target HANYA berasal dari ppd_keys.schema_name (check list prportal*), tidak pernah dari
-- masukan pemanggil. p_table divalidasi (regex + harus tabel di schema kunci + bukan _*/ppd_*);
-- kolom di p_filter/p_rows harus kolom nyata tabel itu. Nama tabel/kolom selalu lewat format(%I);
-- nilai lewat jsonb_populate_record(set) + parameter EXECUTE ... USING, tidak pernah digabung string.
--
-- File ini tidak memakai {{schema}}: objek di public, semua statement idempoten
-- (create ... if not exists / create or replace / revoke / grant). Harus diterapkan sebagai pemilik
-- yang sama dengan fh_exec (postgres): SQL Editor / plugin Supabase; di test lewat psycopg2.
-- Badan fungsi & DO ditulis sebagai literal '...' (bukan $$) karena split_script (fhdb.sqlbind).
-- Role Supabase (anon/authenticated/service_role) tidak ada di Postgres test lokal: grant/revoke
-- ke role itu bersyarat pg_roles.

create table if not exists public.ppd_keys (
    key_hash    text primary key,
    schema_name text not null check (schema_name in ('prportal', 'prportal_staging', 'prportal_test')),
    label       text not null,
    created_at  timestamptz not null default now(),
    revoked_at  timestamptz
);

alter table public.ppd_keys enable row level security;
revoke all on table public.ppd_keys from public;

-- ---------------------------------------------------------------------------------------------
-- Helper internal (bukan API: EXECUTE dicabut dari semua role klien)
-- ---------------------------------------------------------------------------------------------

-- Kunci -> schema.
create or replace function public.ppd_key_schema(p_key text)
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
        raise exception ''ppd: kunci tidak valid'' using errcode = ''42501'';
    end if;
    select k.schema_name into v_schema
      from public.ppd_keys k
     where k.key_hash = encode(sha256(convert_to(p_key, ''UTF8'')), ''hex'')
       and k.revoked_at is null;
    if v_schema is null or v_schema not in (''prportal'', ''prportal_staging'', ''prportal_test'') then
        raise exception ''ppd: kunci tidak valid'' using errcode = ''42501'';
    end if;
    return v_schema;
end
';

-- p_table harus: ^[a-z][a-z0-9_]*$, <= 63 char, bukan _* / ppd_*, dan BASE TABLE di p_schema.
create or replace function public.ppd_check_table(p_schema text, p_table text)
returns void
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
begin
    if p_schema is null
       or p_schema not in (''prportal'', ''prportal_staging'', ''prportal_test'')
       or p_table is null
       or length(p_table) > 63
       or p_table !~ ''^[a-z][a-z0-9_]*$''
       or left(p_table, 1) = ''_''
       or left(p_table, 4) = ''ppd_''
       or not exists (select 1
                        from information_schema.tables t
                       where t.table_schema = p_schema
                         and t.table_name = p_table
                         and t.table_type = ''BASE TABLE'') then
        raise exception ''ppd: tabel tidak dikenal'' using errcode = ''22023'';
    end if;
end
';

-- Kolom yang tidak ada di tabel -> 42703 dengan nama kolomnya (kolom sistem/dropped tidak dihitung).
create or replace function public.ppd_check_cols(p_schema text, p_table text, p_cols text[])
returns void
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_rel regclass := format(''%I.%I'', p_schema, p_table)::regclass;
    v_bad text;
begin
    select c into v_bad
      from unnest(coalesce(p_cols, ''{}''::text[])) c
     where not exists (select 1
                         from pg_attribute a
                        where a.attrelid = v_rel
                          and a.attname = c
                          and a.attnum > 0
                          and not a.attisdropped)
     limit 1;
    if found then
        raise exception ''ppd: kolom tidak dikenal: %'', left(v_bad, 100) using errcode = ''42703'';
    end if;
end
';

-- Kolom primary key, urut posisi di indeks PK. Kosong bila tabel tanpa PK.
create or replace function public.ppd_pk_cols(p_schema text, p_table text)
returns text[]
language sql
stable
security definer
set search_path = public, pg_temp
as '
    select coalesce(array_agg(a.attname::text order by array_position(i.indkey::int2[], a.attnum)), ''{}''::text[])
      from pg_index i
      join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
     where i.indrelid = format(''%I.%I'', p_schema, p_table)::regclass
       and i.indisprimary
';

-- ---------------------------------------------------------------------------------------------
-- API publik (EXECUTE untuk anon)
-- ---------------------------------------------------------------------------------------------

-- Baris tabel sebagai array objek, urut primary key. p_filter = {kolom: nilai} (AND, kesetaraan;
-- null cocok dengan null). p_limit 0..5000 (default 1000), p_offset >= 0.
create or replace function public.ppd_select(p_key text, p_table text, p_filter jsonb default '{}',
                                             p_limit int default 1000, p_offset int default 0)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_schema text := public.ppd_key_schema(p_key);
    v_rel    text;
    v_pk     text[];
    v_where  text;
    v_order  text;
    v_oorder text;
    v_result jsonb;
begin
    perform public.ppd_check_table(v_schema, p_table);
    p_filter := coalesce(p_filter, ''{}''::jsonb);
    if jsonb_typeof(p_filter) <> ''object'' then
        raise exception ''ppd: p_filter harus objek'' using errcode = ''22023'';
    end if;
    p_limit := coalesce(p_limit, 1000);
    p_offset := coalesce(p_offset, 0);
    if p_limit < 0 or p_limit > 5000 then
        raise exception ''ppd: p_limit harus 0..5000'' using errcode = ''22023'';
    end if;
    if p_offset < 0 then
        raise exception ''ppd: p_offset harus >= 0'' using errcode = ''22023'';
    end if;
    perform public.ppd_check_cols(v_schema, p_table, array(select jsonb_object_keys(p_filter)));
    v_pk := public.ppd_pk_cols(v_schema, p_table);
    if cardinality(v_pk) = 0 then
        raise exception ''ppd: tabel tanpa primary key'' using errcode = ''22023'';
    end if;
    v_rel := format(''%I.%I'', v_schema, p_table);
    select coalesce(string_agg(format(''_ppd_t.%I is not distinct from _ppd_f.%I'', k, k), '' and ''), ''true'')
      into v_where
      from jsonb_object_keys(p_filter) k;
    select string_agg(format(''_ppd_t.%I'', c), '', '' order by o), string_agg(format(''_ppd_q.%I'', c), '', '' order by o)
      into v_order, v_oorder
      from unnest(v_pk) with ordinality u(c, o);
    execute format(
        ''select coalesce(jsonb_agg(to_jsonb(_ppd_q) order by %s), ''''[]''''::jsonb) from ''
        ''(select _ppd_t.* from %s _ppd_t, jsonb_populate_record(null::%s, $1) _ppd_f ''
        '' where %s order by %s limit $2 offset $3) _ppd_q'',
        v_oorder, v_rel, v_rel, v_where, v_order)
       into v_result
      using p_filter, p_limit, p_offset;
    return v_result;
end
';

-- Upsert array objek baris; konflik pada primary key -> update kolom yang dikirim. Satu transaksi.
-- Hanya kolom yang muncul di p_rows yang ditulis (kolom lain: default saat insert, tetap saat update).
create or replace function public.ppd_upsert(p_key text, p_table text, p_rows jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_schema text := public.ppd_key_schema(p_key);
    v_rel    text;
    v_pk     text[];
    v_cols   text[];
    v_list   text;
    v_pklist text;
    v_set    text;
    v_n      bigint;
begin
    perform public.ppd_check_table(v_schema, p_table);
    if p_rows is null or jsonb_typeof(p_rows) <> ''array''
       or exists (select 1 from jsonb_array_elements(p_rows) e where jsonb_typeof(e) <> ''object'') then
        raise exception ''ppd: p_rows harus array objek'' using errcode = ''22023'';
    end if;
    if jsonb_array_length(p_rows) = 0 then
        return jsonb_build_object(''upserted'', 0);
    end if;
    select array_agg(distinct k order by k) into v_cols
      from jsonb_array_elements(p_rows) e, jsonb_object_keys(e) k;
    perform public.ppd_check_cols(v_schema, p_table, v_cols);
    v_pk := public.ppd_pk_cols(v_schema, p_table);
    if cardinality(v_pk) = 0 then
        raise exception ''ppd: tabel tanpa primary key'' using errcode = ''22023'';
    end if;
    v_rel := format(''%I.%I'', v_schema, p_table);
    select string_agg(format(''%I'', c), '', '') into v_list from unnest(v_cols) c;
    select string_agg(format(''%I'', c), '', '' order by o) into v_pklist from unnest(v_pk) with ordinality u(c, o);
    select string_agg(format(''%I = excluded.%I'', c, c), '', '') into v_set
      from unnest(v_cols) c
     where c <> all(v_pk);
    if v_set is null then
        -- hanya kolom PK yang dikirim: no-op update supaya baris yang sudah ada tetap terhitung
        v_set := format(''%I = excluded.%I'', v_pk[1], v_pk[1]);
    end if;
    execute format(
        ''insert into %s as _ppd_t (%s) select %s from jsonb_populate_recordset(null::%s, $1) ''
        ''on conflict (%s) do update set %s'',
        v_rel, v_list, v_list, v_rel, v_pklist, v_set)
      using p_rows;
    get diagnostics v_n = row_count;
    return jsonb_build_object(''upserted'', v_n);
end
';

-- Hapus baris berdasarkan array nilai primary key (tabel dengan PK satu kolom).
create or replace function public.ppd_delete(p_key text, p_table text, p_keys jsonb)
returns jsonb
language plpgsql
volatile
security definer
set search_path = public, pg_temp
as '
declare
    v_schema text := public.ppd_key_schema(p_key);
    v_rel    text;
    v_pk     text[];
    v_n      bigint;
begin
    perform public.ppd_check_table(v_schema, p_table);
    if p_keys is null or jsonb_typeof(p_keys) <> ''array'' then
        raise exception ''ppd: p_keys harus array'' using errcode = ''22023'';
    end if;
    if jsonb_array_length(p_keys) = 0 then
        return jsonb_build_object(''deleted'', 0);
    end if;
    v_pk := public.ppd_pk_cols(v_schema, p_table);
    if cardinality(v_pk) <> 1 then
        raise exception ''ppd: ppd_delete butuh tabel dengan primary key satu kolom'' using errcode = ''22023'';
    end if;
    v_rel := format(''%I.%I'', v_schema, p_table);
    execute format(
        ''delete from %s _ppd_t using jsonb_array_elements($1) _ppd_e ''
        '' where _ppd_t.%I = (jsonb_populate_record(null::%s, jsonb_build_object($2::text, _ppd_e.value))).%I'',
        v_rel, v_pk[1], v_rel, v_pk[1])
      using p_keys, v_pk[1];
    get diagnostics v_n = row_count;
    return jsonb_build_object(''deleted'', v_n);
end
';

-- Jumlah baris + nama kolom (urut ordinal).
create or replace function public.ppd_stats(p_key text, p_table text)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, pg_temp
as '
declare
    v_schema text := public.ppd_key_schema(p_key);
    v_rel    text;
    v_n      bigint;
    v_cols   jsonb;
begin
    perform public.ppd_check_table(v_schema, p_table);
    v_rel := format(''%I.%I'', v_schema, p_table);
    execute format(''select count(*) from %s'', v_rel) into v_n;
    select coalesce(jsonb_agg(a.attname::text order by a.attnum), ''[]''::jsonb) into v_cols
      from pg_attribute a
     where a.attrelid = v_rel::regclass
       and a.attnum > 0
       and not a.attisdropped;
    return jsonb_build_object(''rows'', v_n, ''columns'', v_cols);
end
';

-- ---------------------------------------------------------------------------------------------
-- Hak akses. EXECUTE default PUBLIC dicabut. Supabase memberi default privileges di public ke
-- anon/authenticated untuk tabel & fungsi baru, jadi dicabut eksplisit; lalu anon hanya mendapat
-- EXECUTE keempat fungsi publik.
-- ---------------------------------------------------------------------------------------------
revoke all on function public.ppd_key_schema(text) from public;
revoke all on function public.ppd_check_table(text, text) from public;
revoke all on function public.ppd_check_cols(text, text, text[]) from public;
revoke all on function public.ppd_pk_cols(text, text) from public;
revoke all on function public.ppd_select(text, text, jsonb, int, int) from public;
revoke all on function public.ppd_upsert(text, text, jsonb) from public;
revoke all on function public.ppd_delete(text, text, jsonb) from public;
revoke all on function public.ppd_stats(text, text) from public;

do '
declare
    r text;
begin
    foreach r in array array[''anon'', ''authenticated''] loop
        if exists (select 1 from pg_roles where rolname = r) then
            execute format(''revoke all on table public.ppd_keys from %I'', r);
            execute format(''revoke all on function public.ppd_key_schema(text) from %I'', r);
            execute format(''revoke all on function public.ppd_check_table(text, text) from %I'', r);
            execute format(''revoke all on function public.ppd_check_cols(text, text, text[]) from %I'', r);
            execute format(''revoke all on function public.ppd_pk_cols(text, text) from %I'', r);
            execute format(''revoke all on function public.ppd_select(text, text, jsonb, int, int) from %I'', r);
            execute format(''revoke all on function public.ppd_upsert(text, text, jsonb) from %I'', r);
            execute format(''revoke all on function public.ppd_delete(text, text, jsonb) from %I'', r);
            execute format(''revoke all on function public.ppd_stats(text, text) from %I'', r);
        end if;
    end loop;
    if exists (select 1 from pg_roles where rolname = ''anon'') then
        execute ''grant execute on function public.ppd_select(text, text, jsonb, int, int) to anon'';
        execute ''grant execute on function public.ppd_upsert(text, text, jsonb) to anon'';
        execute ''grant execute on function public.ppd_delete(text, text, jsonb) to anon'';
        execute ''grant execute on function public.ppd_stats(text, text) to anon'';
    end if;
    if exists (select 1 from pg_roles where rolname = ''service_role'') then
        execute ''grant all on table public.ppd_keys to service_role'';
    end if;
end
';

notify pgrst, 'reload schema';

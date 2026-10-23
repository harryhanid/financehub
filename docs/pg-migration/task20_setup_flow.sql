-- Task 20 — setup awal project Flow (yqdgykxknrudsfxbxevf). Jalankan SEKALI di Supabase SQL Editor.
-- Isi: (1) hapus sisa spike, (2) fungsi public.fh_exec, (3) schema financehub/_staging/_test + izin service_role.
-- Aman diulang (idempotent). Tidak menyentuh project PR Portal.

-- (1) Sisa spike
drop function if exists public.fh_spike_exec(jsonb);
drop schema if exists fh_spike cascade;

-- (2) fh_exec (salinan app/db_migrations/0001_fh_exec.sql)
create or replace function public.fh_exec(stmts jsonb, schema text)
returns text
language plpgsql
as $$
declare
    s      text;
    skel   text;
    parts  text[] := '{}';
    r      text;
    cols   text;
    n      bigint;
    is_sel boolean;
    i      int := 0;
    pname  text;
    typs   text;
begin
    if schema is null or schema not in ('financehub', 'financehub_staging', 'financehub_test') then
        raise exception 'fh_exec: schema % tidak diizinkan', coalesce(schema, '<null>')
            using errcode = '42501';
    end if;
    perform set_config('search_path', schema || ',public', true);
    -- bind() meng-quote teks dengan asumsi standard_conforming_strings=on (backslash literal).
    perform set_config('standard_conforming_strings', 'on', true);

    for s in select jsonb_array_elements_text(stmts) loop
        -- Buang ';' dan spasi di ujung: statement dibungkus CTE/view, 'select 1;' akan jadi '(select 1;)'.
        s := regexp_replace(s, '[\s;]+$', '');
        -- Klasifikasi pada "kerangka" statement: literal '...' (escape ''), identifier "..." (escape ""),
        -- komentar -- dan /* */ diganti spasi dulu, supaya teks bebas user (diinline oleh bind)
        -- seperti 'returning goods' atau 'insert into' tidak mengubah rute.
        skel := regexp_replace(
            s,
            $re$'([^']|'')*'|"([^"]|"")*"|--[^\n]*|/\*([^*]|\*+[^*/])*\*+/$re$,
            ' ', 'g');
        is_sel := skel ~* '^\s*(select|with)\M';
        i := i + 1;
        if is_sel or skel ~* '\mreturning\M' then
            -- Tipe kolom hasil. PREPARE sesudah search_path diset (resolusi nama memakai schema ini).
            -- Prepared statement bersifat per sesi dan TIDAK ikut rollback: nama unik per posisi dalam
            -- panggilan ini, dan sisa dari panggilan sebelumnya (mis. batal di tengah) dibuang dulu.
            -- Sub-blok: PREPARE yang gagal tidak membatalkan transaksi; typs = null (tanpa "types").
            pname := 'fh_exec_t' || i;
            typs := null;
            begin
                if exists (select 1 from pg_prepared_statements where name = pname) then
                    execute format('deallocate %I', pname);
                end if;
                execute format(E'prepare %I as %s\n', pname, s);
                select coalesce(json_agg(format_type(t.typ::oid, null) order by t.ord), '[]'::json)::text
                  into typs
                  from pg_prepared_statements p,
                       unnest(p.result_types) with ordinality as t(typ, ord)
                 where p.name = pname;
                execute format('deallocate %I', pname);
            exception when others then
                typs := null;
            end;
            -- newline sebelum ')': komentar -- di akhir s tidak boleh menelan kurung penutup
            execute format(E'with _q as (%s\n) select json_agg(_q)::text from _q', s) into r;
            if r is not null then
                parts := parts || ('{"rows":' || r || coalesce(',"types":' || typs, '') || '}');
            else
                cols := '[]';
                if is_sel then
                    -- Nama kolom untuk hasil kosong: lewat temp view, urut attnum.
                    -- Sub-blok (subtransaksi): kalau view tidak bisa dibuat (mis. nama kolom kembar,
                    -- atau WITH berisi DML), columns = [] dan view tidak tertinggal.
                    begin
                        execute format(E'create temp view _fh_v as %s\n', s);
                        -- dinamis: regclass literal di SQL statis plpgsql bisa ter-cache ke OID view lama
                        execute 'select coalesce(json_agg(a.attname order by a.attnum), ''[]''::json)::text
                                   from pg_attribute a
                                  where a.attrelid = ''pg_temp._fh_v''::regclass
                                    and a.attnum > 0
                                    and not a.attisdropped'
                           into cols;
                        drop view pg_temp._fh_v;
                    exception when duplicate_column or feature_not_supported then
                        cols := '[]';
                    end;
                end if;
                parts := parts || ('{"rows":[],"columns":' || cols || coalesce(',"types":' || typs, '') || '}');
            end if;
        else
            execute s;
            get diagnostics n = row_count;
            parts := parts || ('{"rowcount":' || n || '}');
        end if;
    end loop;

    return '[' || array_to_string(parts, ',') || ']';
end
$$;

revoke all on function public.fh_exec(jsonb, text) from public;
revoke all on function public.fh_exec(jsonb, text) from anon;
revoke all on function public.fh_exec(jsonb, text) from authenticated;
grant execute on function public.fh_exec(jsonb, text) to service_role;

-- (3) Schema + izin
create schema if not exists financehub;
create schema if not exists financehub_staging;
create schema if not exists financehub_test;
grant usage, create on schema financehub, financehub_staging, financehub_test to service_role;

notify pgrst, 'reload schema';

-- Cek hasil: harus schemas=financehub,financehub_staging,financehub_test | spike=0 | anon_exec=false | service_exec=true | svc_create=true
select
  (select string_agg(nspname, ',' order by nspname) from pg_namespace where nspname like 'financehub%') as schemas,
  (select count(*) from pg_proc where proname = 'fh_spike_exec') + (select count(*) from pg_namespace where nspname = 'fh_spike') as spike,
  has_function_privilege('anon', 'public.fh_exec(jsonb,text)', 'execute') as anon_exec,
  has_function_privilege('service_role', 'public.fh_exec(jsonb,text)', 'execute') as service_exec,
  has_schema_privilege('service_role', 'financehub', 'create') as svc_create;

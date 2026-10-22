-- 0001_fh_exec.sql
-- Satu-satunya pintu SQL FinanceHub: daftar statement dijalankan dalam SATU transaksi
-- (satu panggilan RPC PostgREST = satu transaksi; di test lewat psycopg2 dengan semantik sama).
-- Kalau satu statement error, seluruh daftar dibatalkan.
--
-- Hasil: TEXT berisi array JSON, satu elemen per statement:
--   statement yang mengembalikan baris (SELECT/WITH/RETURNING) -> {"rows": [...]}            (ada baris)
--                                                              -> {"rows": [], "columns": [...]} (kosong)
--   statement lain                                             -> {"rowcount": n}
-- rows dibuat dengan json_agg (tipe json, bukan jsonb) agar urutan key dan key kembar tetap.
-- Return type text: PostgREST mengirimnya sebagai string JSON tanpa memformat ulang isinya.

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
        if is_sel or skel ~* '\mreturning\M' then
            -- newline sebelum ')': komentar -- di akhir s tidak boleh menelan kurung penutup
            execute format(E'with _q as (%s\n) select json_agg(_q)::text from _q', s) into r;
            if r is not null then
                parts := parts || ('{"rows":' || r || '}');
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
                parts := parts || ('{"rows":[],"columns":' || cols || '}');
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

-- Hanya service_role yang boleh memanggil. Role Supabase (anon/authenticated/service_role)
-- tidak ada di Postgres lokal untuk test, jadi grant/revoke ke role itu bersyarat.
revoke all on function public.fh_exec(jsonb, text) from public;
do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        execute 'revoke all on function public.fh_exec(jsonb, text) from anon';
    end if;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute 'revoke all on function public.fh_exec(jsonb, text) from authenticated';
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
        execute 'grant execute on function public.fh_exec(jsonb, text) to service_role';
    end if;
end
$$;

notify pgrst, 'reload schema';

-- 0001_fh_exec.sql
-- Satu-satunya pintu SQL FinanceHub: daftar statement dijalankan dalam SATU transaksi
-- (satu panggilan RPC PostgREST = satu transaksi; di test lewat psycopg2 dengan semantik sama).
-- Kalau satu statement error, seluruh daftar dibatalkan.
--
-- Hasil: TEXT berisi array JSON, satu elemen per statement:
--   statement yang mengembalikan baris (SELECT/WITH/RETURNING) -> {"rows": [...], "types": [...]}            (ada baris)
--                                                              -> {"rows": [], "columns": [...], "types": [...]} (kosong)
--   statement lain                                             -> {"rowcount": n}
-- "types" = tipe kolom hasil (format_type, mis. "bigint", "double precision"), urut posisi kolom; dipakai
-- client agar nilai double precision/real utuh (10.0 -> json 10) kembali sebagai float seperti sqlite3 REAL.
-- Diambil dengan PREPARE + pg_prepared_statements.result_types (PG >= 14) sebelum statement dijalankan.
-- Kalau PREPARE gagal, "types" tidak ada (client memakai nilai apa adanya); error aslinya muncul saat execute.
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

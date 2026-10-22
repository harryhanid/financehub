-- 0002b_compat.sql
-- Fungsi kompatibilitas SQLite untuk query FinanceHub di Postgres. Placeholder {{schema}}.
--
-- fh_strftime(fmt, x): pengganti strftime(fmt, x) SQLite untuk x berupa teks ISO.
--   Specifier yang didukung: %Y %m %d %H %M %S %j %w; sisa fmt disalin apa adanya.
--   x harus 'YYYY-MM-DD' dengan opsional '[ T]HH:MM[:SS[.fff]]' dan spasi di ujung; selain itu NULL
--   (sama dengan strftime SQLite atas teks non-ISO, mis. '15/03/2025' atau '').
--   Tanggal di luar rentang (bulan 1-12, hari 1-31) -> NULL; hari yang melewati akhir bulan
--   dinormalisasi seperti SQLite ('2025-02-30' -> 2025-03-02).
--   Tidak didukung (hasil NULL, berbeda dari SQLite): sufiks zona waktu, 'now', angka julian day.
-- Badan fungsi memakai bentuk SQL-standard (RETURN ...) tanpa ';' atau $$ di dalamnya, supaya
-- split_script (fhdb.sqlbind) bisa memecah file ini dengan aman.

create or replace function {{schema}}.fh_strftime(fmt text, x text)
returns text
language sql
immutable
return (
    select case when t.ts is null or fmt is null then null else
        replace(replace(replace(replace(replace(replace(replace(replace(fmt,
            '%Y', lpad(extract(year from t.ts)::int::text, 4, '0')),
            '%m', lpad(extract(month from t.ts)::int::text, 2, '0')),
            '%d', lpad(extract(day from t.ts)::int::text, 2, '0')),
            '%H', lpad(extract(hour from t.ts)::int::text, 2, '0')),
            '%M', lpad(extract(minute from t.ts)::int::text, 2, '0')),
            '%S', lpad(floor(extract(second from t.ts))::int::text, 2, '0')),
            '%j', lpad((t.ts::date - make_date(extract(year from t.ts)::int, 1, 1) + 1)::text, 3, '0')),
            '%w', extract(dow from t.ts)::int::text)
    end
    from (select regexp_match(x, '^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?\s*$') as m) r
    cross join lateral (
        select case
            when r.m is null then null
            when r.m[1]::int < 1 or r.m[2]::int not between 1 and 12 or r.m[3]::int not between 1 and 31
                 or coalesce(r.m[4], '0')::int > 24 or coalesce(r.m[5], '0')::int > 59
                 or coalesce(r.m[6], '0')::int > 59 then null
            else (make_date(r.m[1]::int, r.m[2]::int, 1) + (r.m[3]::int - 1))
                 + make_interval(hours => coalesce(r.m[4], '0')::int,
                                 mins => coalesce(r.m[5], '0')::int,
                                 secs => coalesce(r.m[6], '0')::int)
        end as ts
    ) t
);

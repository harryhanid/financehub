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
-- plpgsql (Task 21): versi lama (fungsi SQL dengan subquery LATERAL, tidak bisa di-inline) memakan
--   ~0,8 ms per baris di Supabase, jadi fh_strftime atas ~10 ribu baris payment_beasiswa melewati
--   statement_timeout 8 s. Versi ini hasilnya sama (test_generate_schema + test_fh_strftime_*),
--   ~10-20x lebih cepat; '%Y' langsung mengembalikan tahun hasil regex kalau jam < 24.
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) bisa
-- memecah file ini dengan aman (pola sama dengan 0004_fn_*.sql).

create or replace function {{schema}}.fh_strftime(fmt text, x text)
returns text
language plpgsql
immutable
parallel safe
as '
declare
    m text[];
    ts timestamp;
    r text;
begin
    if fmt is null or x is null then
        return null;
    end if;
    m := regexp_match(x, ''^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?\s*$'');
    if m is null then
        return null;
    end if;
    if m[1]::int < 1 or m[2]::int not between 1 and 12 or m[3]::int not between 1 and 31
       or coalesce(m[4], ''0'')::int > 24 or coalesce(m[5], ''0'')::int > 59
       or coalesce(m[6], ''0'')::int > 59 then
        return null;
    end if;
    if fmt = ''%Y'' and coalesce(m[4], ''0'')::int < 24 then
        return m[1];
    end if;
    ts := (make_date(m[1]::int, m[2]::int, 1) + (m[3]::int - 1))
          + make_interval(hours => coalesce(m[4], ''0'')::int,
                          mins => coalesce(m[5], ''0'')::int,
                          secs => coalesce(m[6], ''0'')::int);
    r := replace(fmt, ''%Y'', lpad(extract(year from ts)::int::text, 4, ''0''));
    r := replace(r, ''%m'', lpad(extract(month from ts)::int::text, 2, ''0''));
    r := replace(r, ''%d'', lpad(extract(day from ts)::int::text, 2, ''0''));
    r := replace(r, ''%H'', lpad(extract(hour from ts)::int::text, 2, ''0''));
    r := replace(r, ''%M'', lpad(extract(minute from ts)::int::text, 2, ''0''));
    r := replace(r, ''%S'', lpad(floor(extract(second from ts))::int::text, 2, ''0''));
    r := replace(r, ''%j'', lpad((ts::date - make_date(extract(year from ts)::int, 1, 1) + 1)::text, 3, ''0''));
    r := replace(r, ''%w'', extract(dow from ts)::int::text);
    return r;
end
';

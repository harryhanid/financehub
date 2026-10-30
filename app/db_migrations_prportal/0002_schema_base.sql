-- 0002_schema_base.sql
-- Tabel dasar per schema PR Portal ({{schema}} = prportal / prportal_staging / prportal_test).
-- Idempoten (create ... if not exists). Klien (anon/authenticated) tidak punya hak langsung ke
-- schema ini: akses hanya lewat public.ppd_* (0001, SECURITY DEFINER).

create schema if not exists {{schema}};

-- Tabel pilot: header sheet Announcements (Code.js) ternormalisasi: Timestamp, Title, Message, Author, Active.
create table if not exists {{schema}}.announcements (
    "timestamp" timestamptz primary key,
    title       text,
    message     text,
    author      text,
    active      boolean
);

-- Antrean tulis-sheet yang gagal (dipakai plan modul). Nama ppd_* -> tidak bisa disentuh lewat API ppd_*.
create table if not exists {{schema}}.ppd_sheet_retry (
    id         bigserial primary key,
    module     text,
    sheet_name text,
    row_key    text,
    payload    jsonb,
    error      text,
    created_at timestamptz not null default now(),
    done_at    timestamptz
);

revoke all on schema {{schema}} from public;
revoke all on all tables in schema {{schema}} from public;
revoke all on all sequences in schema {{schema}} from public;

do '
declare
    r text;
begin
    foreach r in array array[''anon'', ''authenticated''] loop
        if exists (select 1 from pg_roles where rolname = r) then
            execute format(''revoke all on schema {{schema}} from %I'', r);
            execute format(''revoke all on all tables in schema {{schema}} from %I'', r);
            execute format(''revoke all on all sequences in schema {{schema}} from %I'', r);
        end if;
    end loop;
end
';

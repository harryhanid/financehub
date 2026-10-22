-- 0004_fn_budget.sql
-- Persetujuan request budget secara atomik (Task 10, atomic-flows.md).
-- Placeholder {{schema}} diganti apply_migrations.py.
--
-- Dulu (modules/budget/service.py approve_carryover / approve_additional_budget): baca log Pending +
-- baris budget_master -> hitung deadline/amount baru di Python -> UPDATE budget_master -> UPDATE log
-- dalam dua panggilan. Dua approve bersamaan bisa memperpanjang deadline / menambah amount dua kali,
-- dan kegagalan di UPDATE log meninggalkan budget yang sudah diubah dengan log masih Pending.
-- Sekarang: log Pending dikunci FOR UPDATE (approve kedua menunggu, lalu tidak lagi melihat Pending),
-- budget_master dikunci FOR UPDATE, nilai baru dihitung di SQL, kedua UPDATE dalam satu transaksi.
--
-- Nilai waktu (p_today, p_ts) dikirim dari Python supaya sama persis dengan versi SQLite
-- (datetime.now() lokal server, _ts() isoformat detik).
-- Hasil: 0 = tidak ada log Pending tipe itu, 1 = budget tidak ditemukan, 2 = disetujui.
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak
-- memecah di ';' di dalam badan.

-- approve_carryover: deadline baru = deadline lama (atau hari ini kalau kosong) + N bulan.
-- `date + interval 'N months'` memotong ke akhir bulan, sama dengan _add_months di Python.
create or replace function {{schema}}.fn_budget_approve_carryover(
    p_budget_id text,
    p_username text,
    p_months bigint,
    p_today text,
    p_ts text
)
returns integer
language plpgsql
volatile
as '
declare
    v_log_id bigint;
    v_deadline text;
    v_base date;
begin
    -- SQLite tanpa ORDER BY mengembalikan baris pertama menurut rowid -> ORDER BY id.
    select l."id" into v_log_id
      from {{schema}}."budget_carryover_logs" l
     where l."budget_id" = p_budget_id and l."status" = ''Pending'' and l."type" = ''Carryover''
     order by l."id"
     limit 1
       for update;
    if not found then
        return 0;
    end if;

    select b."deadline" into v_deadline
      from {{schema}}."budget_master" b
     where b."id" = p_budget_id
       for update;
    if not found then
        return 1;
    end if;

    -- Python: datetime.fromisoformat(deadline).date() if deadline else datetime.now().date()
    if v_deadline is null or v_deadline = '''' then
        v_base := p_today::date;
    else
        v_base := v_deadline::timestamp::date;
    end if;

    update {{schema}}."budget_master"
       set "deadline" = to_char(v_base + make_interval(months => p_months::int), ''YYYY-MM-DD''),
           "updated_at" = p_ts
     where "id" = p_budget_id;

    update {{schema}}."budget_carryover_logs"
       set "status" = ''Approved'', "approval_date" = p_ts, "extension_months" = p_months,
           "approved_by" = p_username
     where "id" = v_log_id;
    return 2;
end
';

-- approve_additional_budget: amount baru = amount + additional_amount (NULL dihitung 0),
-- deadline baru = hari ini + N bulan. Mengembalikan additional_amount log untuk pesan.
create or replace function {{schema}}.fn_budget_approve_additional(
    p_budget_id text,
    p_username text,
    p_months bigint,
    p_today text,
    p_ts text
)
returns table (result integer, additional_amount double precision)
language plpgsql
volatile
as '
declare
    v_log_id bigint;
    v_add double precision;
    v_amount double precision;
begin
    select l."id", l."additional_amount" into v_log_id, v_add
      from {{schema}}."budget_carryover_logs" l
     where l."budget_id" = p_budget_id and l."status" = ''Pending'' and l."type" = ''Additional''
     order by l."id"
     limit 1
       for update;
    if not found then
        return query select 0, null::double precision;
        return;
    end if;

    select b."amount" into v_amount
      from {{schema}}."budget_master" b
     where b."id" = p_budget_id
       for update;
    if not found then
        return query select 1, v_add;
        return;
    end if;

    update {{schema}}."budget_master"
       set "amount" = coalesce(v_amount, 0) + coalesce(v_add, 0),
           "deadline" = to_char(p_today::date + make_interval(months => p_months::int), ''YYYY-MM-DD''),
           "updated_at" = p_ts
     where "id" = p_budget_id;

    update {{schema}}."budget_carryover_logs"
       set "status" = ''Approved'', "approval_date" = p_ts, "extension_months" = p_months,
           "approved_by" = p_username
     where "id" = v_log_id;
    return query select 2, v_add;
end
';

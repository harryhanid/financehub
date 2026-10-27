-- 0006_fn_prportal.sql
-- Fungsi untuk integrasi PR Portal -> Flow (PA Beasiswa). Dipakai lewat RPC; semua dijalankan di Postgres.
-- Placeholder {{schema}} diganti apply_migrations.py. Idempoten (create or replace).
--
-- Bagian ini (Task 2): fungsi BACA -- cari siswa dan daftar budget siswa. Fungsi tulis (buat PA, dst.)
-- ditambahkan di file ini oleh task berikutnya.
--
-- Aturan (lihat Global Constraints):
--  * company_id Beasiswa = companies.code 'ETF', dicari di SQL, tidak pernah dari masukan PR Portal.
--  * norek lengkap tidak pernah keluar: hanya bank, rekening_last4, nama_rekening, rekening_ok.
--  * Status efektif budget = 'non_aktif' bila siswa.status <> 'Aktif', selain itu status tersimpan.
--  * Budget dengan tgl_expired < hari ini (UTC+7) tidak ditawarkan; offset tetap +07:00 seperti modules/dashboard (Postgres test lokal tanpa tzdata, Jakarta tanpa DST).
--  * Urutan: cat1 (Pendidikan, Tunjangan, Penelitian, Medical, lainnya A-Z), cat2 natural, tanggal
--    -- sama dengan _laporan_row_key di modules/beasiswa/service.py.
--  * ipk_terakhir = ipk_sem10..ipk_sem1 pertama yang > 0 (sama dengan _latest_ipk di etf_payment_application).
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak
-- memecah di ';' di dalam badan.

create or replace function {{schema}}.fn_prp_budget_status(p_stored text, p_siswa_status text)
returns text
language plpgsql
immutable
as '
begin
    if coalesce(p_siswa_status, '''') <> ''Aktif'' then
        return ''non_aktif'';
    end if;
    return p_stored;
end
';

-- Objek siswa untuk PR Portal (tanpa norek lengkap). Pembantu internal.
create or replace function {{schema}}.fn_prp_siswa_json(p_siswa {{schema}}.siswa)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_digits text := regexp_replace(coalesce(p_siswa.norek, ''''), ''\D'', '''', ''g'');
    v_ipk double precision;
begin
    v_ipk := coalesce(
        nullif(greatest(p_siswa.ipk_sem10, 0), 0), nullif(greatest(p_siswa.ipk_sem9, 0), 0),
        nullif(greatest(p_siswa.ipk_sem8, 0), 0),  nullif(greatest(p_siswa.ipk_sem7, 0), 0),
        nullif(greatest(p_siswa.ipk_sem6, 0), 0),  nullif(greatest(p_siswa.ipk_sem5, 0), 0),
        nullif(greatest(p_siswa.ipk_sem4, 0), 0),  nullif(greatest(p_siswa.ipk_sem3, 0), 0),
        nullif(greatest(p_siswa.ipk_sem2, 0), 0),  nullif(greatest(p_siswa.ipk_sem1, 0), 0),
        0);
    return jsonb_build_object(
        ''code'', p_siswa.code,
        ''nama'', p_siswa.nama,
        ''jenjang'', p_siswa.jenjang,
        ''universitas'', p_siswa.universitas,
        ''program'', p_siswa.program,
        ''ipk_terakhir'', v_ipk,
        ''bank'', p_siswa.bank,
        ''rekening_last4'', case when length(v_digits) >= 4 then right(v_digits, 4) else '''' end,
        ''nama_rekening'', p_siswa.namarek,
        ''rekening_ok'', (length(trim(coalesce(p_siswa.bank, ''''))) > 0
                          and length(trim(coalesce(p_siswa.namarek, ''''))) > 0
                          and length(v_digits) >= 4));
end
';

create or replace function {{schema}}.fn_prp_search_siswa(p_query text)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_q text := trim(coalesce(p_query, ''''));
    v_pat text;
    v_company bigint;
    v_today text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD'');
    v_result jsonb;
begin
    if length(v_q) < 3 then
        return ''[]''::jsonb;
    end if;
    select id into v_company from companies where code = ''ETF'';
    v_pat := ''%'' || replace(replace(replace(v_q, ''\'', ''\\''), ''%'', ''\%''), ''_'', ''\_'') || ''%'';
    select coalesce(jsonb_agg(fn_prp_siswa_json(t) order by t.nama, t.code), ''[]''::jsonb)
      into v_result
      from (
            select s.*
              from siswa s
             where s.company_id = v_company
               and s.status = ''Aktif''
               and (s.nama ilike v_pat or s.code ilike v_pat)
               and exists (select 1 from budget_beasiswa b
                            where b.company_id = s.company_id and b.siswa_code = s.code
                              and b.status = ''open''
                              and (coalesce(b.tgl_expired, '''') = '''' or b.tgl_expired >= v_today))
             order by s.nama, s.code
             limit 10
           ) t;
    return v_result;
end
';

create or replace function {{schema}}.fn_prp_budget_siswa(p_code text)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_company bigint;
    v_siswa siswa%rowtype;
    v_today text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD'');
    v_rows jsonb;
begin
    select id into v_company from companies where code = ''ETF'';
    select * into v_siswa from siswa where company_id = v_company and code = p_code;
    if not found then
        return null;
    end if;
    select coalesce(jsonb_agg(jsonb_build_object(
               ''budget_id'', x.id,
               ''cat1'', x.cat1,
               ''cat2'', x.cat2,
               ''tanggal'', x.tanggal,
               ''amount'', x.amount,
               ''status'', fn_prp_budget_status(x.status, v_siswa.status),
               ''pa_number'', case when x.status = ''on_progress'' then (
                    select u.pa_number from (
                        select p.pa_number from etf_pa p join etf_pa_lines l on l.pa_id = p.id where l.budget_id = x.id
                        union all select p.pa_number from app_pa p join app_pa_lines l on l.pa_id = p.id where l.budget_id = x.id
                        union all select p.pa_number from sml_pa p join sml_pa_lines l on l.pa_id = p.id where l.budget_id = x.id
                        union all select p.pa_number from setf_pa p join setf_pa_lines l on l.pa_id = p.id where l.budget_id = x.id
                        union all select p.pa_number from energy_pa p join energy_pa_lines l on l.pa_id = p.id where l.budget_id = x.id
                    ) u limit 1) end
           ) order by x.k1, x.k2a, x.k2b, x.cat2, x.tanggal, x.id), ''[]''::jsonb)
      into v_rows
      from (
            select b.*,
                   (case b.cat1 when ''By Pendidikan'' then ''0'' when ''By Tunjangan'' then ''1''
                                when ''By Penelitian'' then ''2'' when ''By Medical'' then ''3''
                                else ''4'' || coalesce(b.cat1, '''') end) as k1,
                   regexp_replace(coalesce(b.cat2, ''''), ''\d+'', '''', ''g'') as k2a,
                   coalesce(nullif(substring(coalesce(b.cat2, '''') from ''\d+''), ''''), ''0'')::int as k2b
              from budget_beasiswa b
             where b.company_id = v_company and b.siswa_code = p_code
               and (coalesce(b.tgl_expired, '''') = '''' or b.tgl_expired >= v_today)
           ) x;
    return jsonb_build_object(
        ''siswa'', fn_prp_siswa_json(v_siswa) || jsonb_build_object(''status'', v_siswa.status),
        ''rows'', v_rows);
end
';

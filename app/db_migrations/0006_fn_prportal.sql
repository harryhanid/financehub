-- 0006_fn_prportal.sql
-- Fungsi untuk integrasi PR Portal -> Flow (PA Beasiswa). Dipakai lewat RPC; semua dijalankan di Postgres.
-- Placeholder {{schema}} diganti apply_migrations.py. Idempoten (create or replace).
--
-- Fungsi BACA (Task 2): cari siswa dan daftar budget siswa.
-- Fungsi TULIS (Task 3): fn_prp_submit_pa -- buat PA + baris + kunci budget dalam satu transaksi.
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

-- Nomor PA yang memakai baris budget (dari kelima tabel baris PA); PA id terbaru dulu supaya deterministik.
create or replace function {{schema}}.fn_prp_budget_pa_number(p_budget_id bigint)
returns text
language sql
stable
set search_path = {{schema}}
as '
    select u.pa_number from (
        select p.id, p.pa_number from etf_pa p join etf_pa_lines l on l.pa_id = p.id where l.budget_id = p_budget_id
        union all select p.id, p.pa_number from app_pa p join app_pa_lines l on l.pa_id = p.id where l.budget_id = p_budget_id
        union all select p.id, p.pa_number from sml_pa p join sml_pa_lines l on l.pa_id = p.id where l.budget_id = p_budget_id
        union all select p.id, p.pa_number from setf_pa p join setf_pa_lines l on l.pa_id = p.id where l.budget_id = p_budget_id
        union all select p.id, p.pa_number from energy_pa p join energy_pa_lines l on l.pa_id = p.id where l.budget_id = p_budget_id
    ) u
    order by u.id desc, u.pa_number desc
    limit 1
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
               ''pa_number'', case when x.status = ''on_progress'' then fn_prp_budget_pa_number(x.id) end
           ) order by x.k1, x.k2a, x.k2b, x.cat2, x.tanggal, x.id), ''[]''::jsonb)
      into v_rows
      from (
            select b.*,
                   (case b.cat1 when ''By Pendidikan'' then ''0'' when ''By Tunjangan'' then ''1''
                                when ''By Penelitian'' then ''2'' when ''By Medical'' then ''3''
                                else ''4'' || coalesce(b.cat1, '''') end) as k1,
                   regexp_replace(coalesce(b.cat2, ''''), ''\d+'', '''', ''g'') as k2a,
                   coalesce(nullif(substring(coalesce(b.cat2, '''') from ''\d+''), ''''), ''0'')::numeric as k2b
              from budget_beasiswa b
             where b.company_id = v_company and b.siswa_code = p_code
               and (coalesce(b.tgl_expired, '''') = '''' or b.tgl_expired >= v_today)
           ) x;
    return jsonb_build_object(
        ''siswa'', fn_prp_siswa_json(v_siswa) || jsonb_build_object(''status'', v_siswa.status),
        ''rows'', v_rows);
end
';

-- Tanggal 'YYYY-MM-DD' yang benar-benar ada (menolak 2026-02-30). Pembantu internal validasi.
create or replace function {{schema}}.fn_prp_is_date(p_v text)
returns boolean
language plpgsql
stable
as '
begin
    if p_v is null or p_v !~ ''^\d{4}-\d{2}-\d{2}$'' then
        return false;
    end if;
    return to_char(p_v::date, ''YYYY-MM-DD'') = p_v;
exception when others then
    return false;
end
';

-- Buat PA dari PR Portal secara atomik. Masukan:
--   {jenis, siswa_code, tgl_payment_application, tgl_surat_pengajuan, doc_received_by_educ,
--    received_pa_from_educ, keterangan, route, klasifikasi, attachment_file_id, requested_by, cost_center,
--    lines:[{budget_id, tahun_ajaran, jumlah}]}
-- Keluaran: {ok:true, pa_id, pa_number, jenis, total} atau {ok:false, pesan} tanpa tulisan apa pun.
-- Urutan: validasi bentuk -> lock siswa + budget (FOR UPDATE, urut id) -> validasi bisnis -> insert header
-- (nomor via fn_etf_pa_next_pa_number di dalam INSERT) -> insert baris -> budget on_progress.
-- Kolom header/baris sama dengan create_pa (modules/etf_payment_application/service.py) + source/requested_by/
-- cost_center/budget_id. Nama tabel hanya dari pemetaan tetap jenis -> tabel (format %I).
create or replace function {{schema}}.fn_prp_submit_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_jenis text := p->>''jenis'';
    v_pa_tbl text;
    v_lines_tbl text;
    v_prefix text;
    v_company bigint;
    v_siswa siswa%rowtype;
    v_sj jsonb;
    v_lines jsonb;
    v_line jsonb;
    v_n int;
    v_i int;
    v_id bigint;
    v_ids bigint[] := ''{}'';
    v_amts bigint[] := ''{}'';
    v_cat1 text[] := ''{}'';
    v_cat2 text[] := ''{}'';
    v_b budget_beasiswa%rowtype;
    v_f text;
    v_name text;
    v_used text;
    v_today text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD'');
    v_year text := to_char(now() at time zone interval ''+07:00'', ''YYYY'');
    v_ts text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD"T"HH24:MI:SS'');
    v_pa_id bigint;
    v_pa_number text;
    v_total bigint := 0;
begin
    -- 1. Validasi bentuk (belum ada lock / tulisan).
    if p is null or jsonb_typeof(p) <> ''object'' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: payload.'');
    end if;
    case v_jenis
        when ''agri''   then v_pa_tbl := ''etf_pa'';    v_lines_tbl := ''etf_pa_lines'';    v_prefix := ''ETF'';
        when ''app''    then v_pa_tbl := ''app_pa'';    v_lines_tbl := ''app_pa_lines'';    v_prefix := ''APP'';
        when ''sml''    then v_pa_tbl := ''sml_pa'';    v_lines_tbl := ''sml_pa_lines'';    v_prefix := ''SML'';
        when ''setf''   then v_pa_tbl := ''setf_pa'';   v_lines_tbl := ''setf_pa_lines'';   v_prefix := ''SETF'';
        when ''energy'' then v_pa_tbl := ''energy_pa''; v_lines_tbl := ''energy_pa_lines''; v_prefix := ''ENERGY'';
        else
            return jsonb_build_object(''ok'', false, ''pesan'', ''Jenis PA tidak dikenal.'');
    end case;
    if jsonb_typeof(p->''siswa_code'') is distinct from ''string'' or trim(p->>''siswa_code'') = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: siswa_code.'');
    end if;
    if jsonb_typeof(p->''route'') is distinct from ''string'' or p->>''route'' not in (''gl'', ''advance'') then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: route.'');
    end if;
    if jsonb_typeof(p->''klasifikasi'') is distinct from ''string'' or p->>''klasifikasi'' not in (''Normal'', ''With Memo'') then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: klasifikasi.'');
    end if;
    if jsonb_typeof(p->''tgl_payment_application'') is distinct from ''string''
       or not fn_prp_is_date(p->>''tgl_payment_application'') then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: tgl_payment_application.'');
    end if;
    foreach v_f in array array[''tgl_surat_pengajuan'', ''doc_received_by_educ'', ''received_pa_from_educ''] loop
        if coalesce(jsonb_typeof(p->v_f), ''null'') <> ''null''
           and (jsonb_typeof(p->v_f) <> ''string'' or (p->>v_f <> '''' and not fn_prp_is_date(p->>v_f))) then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: '' || v_f || ''.'');
        end if;
    end loop;
    foreach v_f in array array[''keterangan'', ''attachment_file_id'', ''cost_center''] loop
        if coalesce(jsonb_typeof(p->v_f), ''null'') not in (''null'', ''string'') then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: '' || v_f || ''.'');
        end if;
    end loop;
    if jsonb_typeof(p->''requested_by'') is distinct from ''string'' or trim(p->>''requested_by'') = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: requested_by.'');
    end if;
    v_lines := p->''lines'';
    if jsonb_typeof(v_lines) is distinct from ''array''
       or jsonb_array_length(v_lines) < 1 or jsonb_array_length(v_lines) > 50 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: lines.'');
    end if;
    v_n := jsonb_array_length(v_lines);
    for v_i in 0 .. v_n - 1 loop
        v_line := v_lines->v_i;
        if jsonb_typeof(v_line) <> ''object'' then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: lines.'');
        end if;
        -- Bilangan bulat JSON > 0: tipe number dan teks kanonik jsonb hanya digit (menolak 0, -5, 100.5, "100").
        if jsonb_typeof(v_line->''budget_id'') is distinct from ''number''
           or (v_line->>''budget_id'') !~ ''^[1-9][0-9]{0,17}$'' then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: budget_id.'');
        end if;
        v_id := (v_line->>''budget_id'')::bigint;
        if v_id = any(v_ids) then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: budget_id.'');
        end if;
        if jsonb_typeof(v_line->''jumlah'') is distinct from ''number''
           or (v_line->>''jumlah'') !~ ''^[1-9][0-9]{0,17}$'' then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: jumlah.'');
        end if;
        if coalesce(jsonb_typeof(v_line->''tahun_ajaran''), ''null'') not in (''null'', ''string'') then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: tahun_ajaran.'');
        end if;
        v_ids := array_append(v_ids, v_id);
        v_amts := array_append(v_amts, (v_line->>''jumlah'')::bigint);
    end loop;

    -- 2. Kunci siswa lalu baris budget (urut id) supaya submit bersamaan berurutan.
    select id into v_company from companies where code = ''ETF'';
    select * into v_siswa from siswa
     where company_id = v_company and code = trim(p->>''siswa_code'')
       for update;
    if not found then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: siswa_code.'');
    end if;
    perform 1 from budget_beasiswa
     where id = any(v_ids) and company_id = v_company and siswa_code = v_siswa.code
     order by id for update;

    -- 3. Validasi bisnis (baca ulang setelah lock: snapshot statement baru melihat commit pemegang lock).
    if coalesce(v_siswa.status, '''') <> ''Aktif'' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Siswa tidak aktif.'');
    end if;
    v_sj := fn_prp_siswa_json(v_siswa);
    if not coalesce((v_sj->>''rekening_ok'')::boolean, false) then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Rekening siswa belum lengkap di Flow. Hubungi Finance.'');
    end if;
    for v_i in 1 .. v_n loop
        select * into v_b from budget_beasiswa
         where id = v_ids[v_i] and company_id = v_company and siswa_code = v_siswa.code;
        if not found or (coalesce(v_b.tgl_expired, '''') <> '''' and v_b.tgl_expired < v_today) then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Baris budget tidak ditemukan untuk siswa ini.'');
        end if;
        v_name := coalesce(v_b.cat1, '''') || '' '' || coalesce(v_b.cat2, '''');
        if v_b.status = ''on_progress'' then
            v_used := fn_prp_budget_pa_number(v_b.id);
            return jsonb_build_object(''ok'', false, ''pesan'',
                ''Baris budget '' || v_name || '' sudah dipakai '' || coalesce(v_used, ''PA lain'') || ''.'');
        end if;
        if v_b.status <> ''open'' then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Baris budget '' || v_name || '' sudah Complete.'');
        end if;
        if v_amts[v_i] > coalesce(v_b.amount, 0) then
            return jsonb_build_object(''ok'', false, ''pesan'',
                ''Jumlah '' || v_name || '' melebihi budget ''
                || case when coalesce(v_b.amount, 0) = trunc(coalesce(v_b.amount, 0))
                        then trunc(coalesce(v_b.amount, 0))::bigint::text
                        else v_b.amount::text end
                || ''.'');
        end if;
        v_cat1 := array_append(v_cat1, coalesce(v_b.cat1, ''''));
        v_cat2 := array_append(v_cat2, coalesce(v_b.cat2, ''''));
    end loop;

    -- 4. Tulis: header (nomor PA dialokasikan di dalam INSERT, advisory lock sampai commit), baris, budget.
    execute format(
        ''insert into %I.%I (company_id, pa_number, tgl_payment_application, tgl_surat_pengajuan, keterangan, ''
        || ''doc_received_by_educ, received_pa_from_educ, status, route, klasifikasi, attachment_file_id, ''
        || ''created_at, source, requested_by, cost_center) ''
        || ''values ($1, fn_etf_pa_next_pa_number($2, $1, $3, $4), $5, $6, $7, $8, $9, $10, $11, $12, $13, ''
        || ''$14, $15, $16, $17) returning id, pa_number'',
        ''{{schema}}'', v_pa_tbl)
      into v_pa_id, v_pa_number
     using v_company, v_pa_tbl, v_prefix, v_year,
           p->>''tgl_payment_application'',
           coalesce(p->>''tgl_surat_pengajuan'', ''''),
           coalesce(p->>''keterangan'', ''''),
           coalesce(p->>''doc_received_by_educ'', ''''),
           coalesce(p->>''received_pa_from_educ'', ''''),
           ''open''::text,
           p->>''route'',
           p->>''klasifikasi'',
           coalesce(p->>''attachment_file_id'', ''''),
           v_ts,
           ''prportal''::text,
           trim(p->>''requested_by''),
           nullif(trim(coalesce(p->>''cost_center'', '''')), '''');
    for v_i in 1 .. v_n loop
        execute format(
            ''insert into %I.%I (pa_id, student_id, jenis_pembayaran, semester, tahun_ajaran, ''
            || ''ipk_sem_sebelumnya, jumlah_pembayaran, route, budget_id) ''
            || ''values ($1, $2, $3, $4, $5, $6, $7, $8, $9)'',
            ''{{schema}}'', v_lines_tbl)
         using v_pa_id, v_siswa.id, v_cat1[v_i], v_cat2[v_i],
               coalesce(v_lines->(v_i - 1)->>''tahun_ajaran'', ''''),
               (v_sj->>''ipk_terakhir'')::double precision,
               v_amts[v_i], p->>''route'', v_ids[v_i];
        v_total := v_total + v_amts[v_i];
    end loop;
    update budget_beasiswa set status = ''on_progress'' where id = any(v_ids);
    return jsonb_build_object(''ok'', true, ''pa_id'', v_pa_id, ''pa_number'', v_pa_number,
                              ''jenis'', v_jenis, ''total'', v_total);
end
';

-- Data cetak PA milik pemohon (hanya source='prportal', requested_by sama tanpa peka huruf besar). Cari di kelima
-- tabel PA; null bila tidak ada. Siswa dimasking (tanpa norek lengkap) lewat fn_prp_siswa_json.
create or replace function {{schema}}.fn_prp_pa_for_print(p_pa_number text, p_requested_by text)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_cfg text[][] := array[
        array[''agri'', ''etf_pa'', ''etf_pa_lines''], array[''app'', ''app_pa'', ''app_pa_lines''],
        array[''sml'', ''sml_pa'', ''sml_pa_lines''], array[''setf'', ''setf_pa'', ''setf_pa_lines''],
        array[''energy'', ''energy_pa'', ''energy_pa_lines'']];
    v_i int;
    v_hdr jsonb;
    v_lines jsonb;
    v_siswa siswa%rowtype;
    v_sj jsonb;
begin
    if p_pa_number is null or p_requested_by is null or trim(p_requested_by) = '''' then
        return null;
    end if;
    for v_i in 1 .. 5 loop
        execute format(
            ''select to_jsonb(p) from %I.%I p where p.pa_number = $1 and p.source = ''''prportal'''' ''
            || ''and lower(p.requested_by) = lower($2) order by p.id desc limit 1'',
            ''{{schema}}'', v_cfg[v_i][2])
          into v_hdr using p_pa_number, trim(p_requested_by);
        if v_hdr is null then
            continue;
        end if;
        execute format(
            ''select coalesce(jsonb_agg(jsonb_build_object(''
            || ''''''jenis_pembayaran'''', l.jenis_pembayaran, ''''semester'''', l.semester, ''''tahun_ajaran'''', l.tahun_ajaran, ''
            || ''''''ipk_sem_sebelumnya'''', l.ipk_sem_sebelumnya, ''''jumlah_pembayaran'''', l.jumlah_pembayaran) order by l.id), ''''[]''''::jsonb) ''
            || ''from %I.%I l where l.pa_id = $1'',
            ''{{schema}}'', v_cfg[v_i][3])
          into v_lines using (v_hdr->>''id'')::bigint;
        execute format(
            ''select s.* from %I.siswa s join %I.%I l on l.student_id = s.id where l.pa_id = $1 order by l.id limit 1'',
            ''{{schema}}'', ''{{schema}}'', v_cfg[v_i][3])
          into v_siswa using (v_hdr->>''id'')::bigint;
        v_sj := fn_prp_siswa_json(v_siswa);
        return jsonb_build_object(
            ''pa_number'', v_hdr->>''pa_number'',
            ''jenis'', v_cfg[v_i][1],
            ''tgl_payment_application'', coalesce(v_hdr->>''tgl_payment_application'', ''''),
            ''tgl_surat_pengajuan'', coalesce(v_hdr->>''tgl_surat_pengajuan'', ''''),
            ''doc_received_by_educ'', coalesce(v_hdr->>''doc_received_by_educ'', ''''),
            ''received_pa_from_educ'', coalesce(v_hdr->>''received_pa_from_educ'', ''''),
            ''keterangan'', coalesce(v_hdr->>''keterangan'', ''''),
            ''route'', v_hdr->>''route'',
            ''klasifikasi'', v_hdr->>''klasifikasi'',
            ''status'', v_hdr->>''status'',
            ''created_at'', v_hdr->>''created_at'',
            ''requested_by'', v_hdr->>''requested_by'',
            ''cost_center'', v_hdr->>''cost_center'',
            ''siswa'', jsonb_build_object(
                ''code'', v_sj->''code'', ''nama'', v_sj->''nama'', ''jenjang'', v_sj->''jenjang'',
                ''universitas'', v_sj->''universitas'', ''program'', v_sj->''program'', ''bank'', v_sj->''bank'',
                ''rekening_last4'', v_sj->''rekening_last4'', ''nama_rekening'', v_sj->''nama_rekening''),
            ''lines'', v_lines,
            ''total'', (select coalesce(sum((e->>''jumlah_pembayaran'')::numeric), 0)::bigint
                         from jsonb_array_elements(v_lines) e));
    end loop;
    return null;
end
';

-- Review akhir: fungsi fn_prp_* internal tidak boleh dipanggil langsung oleh siapa pun selain owner.
-- EXECUTE default PUBLIC dicabut; anon/authenticated (Supabase, bersyarat) juga dicabut. Wrapper
-- public.prp_* (0007) SECURITY DEFINER milik owner, jadi tetap bisa memanggil fungsi ini.
do '
declare
    f record;
    r text;
begin
    for f in select p.proname, pg_get_function_identity_arguments(p.oid) as args
               from pg_proc p join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = ''{{schema}}'' and p.proname like ''fn\_prp\_%''
    loop
        execute format(''revoke all on function %I.%I(%s) from public'', ''{{schema}}'', f.proname, f.args);
        foreach r in array array[''anon'', ''authenticated''] loop
            if exists (select 1 from pg_roles where rolname = r) then
                execute format(''revoke all on function %I.%I(%s) from %I'', ''{{schema}}'', f.proname, f.args, r);
            end if;
        end loop;
    end loop;
end
';

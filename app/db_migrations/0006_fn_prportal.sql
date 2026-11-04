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
        ''siswa'', fn_prp_siswa_detail(v_siswa),
        ''rows'', v_rows);
end
';

-- Menyamarkan teks pribadi: huruf pertama tiap kata + '***' ("Ryan Eka" -> "R*** E***"). Kosong tetap kosong.
create or replace function {{schema}}.fn_prp_mask_text(p_text text)
returns text
language sql
immutable
as '
    select regexp_replace(trim(coalesce(p_text, '''')), ''(\S)\S*'', ''\1***'', ''g'')
';

-- Profil siswa lengkap untuk form PR Portal. Bank & nama rekening DISAMARKAN, nomor rekening hanya 4 digit akhir.
-- Catatan Budget / Catatan Payment (catatan internal Finance) sengaja tidak ikut.
create or replace function {{schema}}.fn_prp_siswa_detail(p_siswa {{schema}}.siswa)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_base jsonb := fn_prp_siswa_json(p_siswa);
begin
    return jsonb_build_object(
        ''code'', p_siswa.code, ''nama'', p_siswa.nama, ''jenjang'', p_siswa.jenjang, ''angkatan'', p_siswa.angkatan,
        ''program'', p_siswa.program, ''group_setf'', coalesce(p_siswa.group_setf, ''''),
        ''status'', p_siswa.status, ''prodi'', coalesce(p_siswa.prodi, ''''),
        ''angkatan_kuliah'', coalesce(p_siswa.angkatan_kuliah, ''''), ''fakultas'', coalesce(p_siswa.fakultas, ''''),
        ''universitas'', coalesce(p_siswa.universitas, ''''), ''referensi'', coalesce(p_siswa.referensi, ''''),
        ''tanggal_lahir'', coalesce(p_siswa.tanggal_lahir, ''''), ''catatan'', coalesce(p_siswa.catatan, ''''),
        ''ipk_sem1'', p_siswa.ipk_sem1, ''ipk_sem2'', p_siswa.ipk_sem2, ''ipk_sem3'', p_siswa.ipk_sem3,
        ''ipk_sem4'', p_siswa.ipk_sem4, ''ipk_sem5'', p_siswa.ipk_sem5, ''ipk_sem6'', p_siswa.ipk_sem6,
        ''ipk_sem7'', p_siswa.ipk_sem7, ''ipk_sem8'', p_siswa.ipk_sem8, ''ipk_sem9'', p_siswa.ipk_sem9,
        ''ipk_sem10'', p_siswa.ipk_sem10, ''ipk_pen1'', p_siswa.ipk_pen1, ''ipk_pen2'', p_siswa.ipk_pen2,
        ''ipk_pen3'', p_siswa.ipk_pen3, ''ipk_terakhir'', v_base->''ipk_terakhir'',
        ''bank_masked'', fn_prp_mask_text(p_siswa.bank), ''rekening_last4'', v_base->''rekening_last4'',
        ''nama_rekening_masked'', fn_prp_mask_text(p_siswa.namarek), ''rekening_ok'', v_base->''rekening_ok'');
end
';

-- Galat satu field perubahan data siswa (null bila valid). Daftar jenjang/program/status = app/config.py
-- (dijaga test_prportal_siswa.py). Field di luar daftar (code, bank, norek, namarek, group_setf, catatan_*) ditolak.
create or replace function {{schema}}.fn_prp_siswa_field_error(p_key text, p_val jsonb)
returns text
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_t text := jsonb_typeof(p_val);
    v_s text := p_val #>> ''{}'';
    v_n numeric;
begin
    if p_key = ''nama'' then
        if v_t <> ''string'' or length(trim(v_s)) = 0 or length(v_s) > 150 then return ''Nama harus diisi (maks 150 karakter).''; end if;
    elsif p_key = ''jenjang'' then
        if v_t <> ''string'' or not (v_s = any (array[''SD'', ''SMP'', ''SMA'', ''SMK'', ''S1'', ''S2'', ''S3'', ''SETF''])) then return ''Jenjang tidak valid.''; end if;
    elsif p_key = ''program'' then
        if v_t <> ''string'' or not (v_s = any (array[''Kejaksaan'', ''Kejaksaan LN'', ''Polri'', ''Special Case'', ''Special Cases LN'',
            ''Tjipta Siswa Mandiri'', ''Bank Sinarmas'', ''IKPP'', ''SMART'', ''Tjipta Bangun Desa'', ''IKPP - Tjipta Bangun Desa'',
            ''Soci Mas'', ''SMMA'', ''Sahabat ETF'', ''Tjipta Sarjana Mandiri''])) then return ''Program tidak valid.''; end if;
    elsif p_key = ''status'' then
        if v_t <> ''string'' or not (v_s = any (array[''Aktif'', ''lulus'', ''gugur'', ''undur diri''])) then return ''Status tidak valid.''; end if;
    elsif p_key = ''angkatan'' then
        if v_t <> ''number'' or v_s !~ ''^20[0-9]{2}$'' then return ''Angkatan harus tahun 2000-2099.''; end if;
    elsif p_key = ''tanggal_lahir'' then
        if v_t <> ''string'' or (v_s <> '''' and not fn_prp_is_date(v_s)) then return ''Tanggal lahir tidak valid.''; end if;
    elsif p_key in (''prodi'', ''angkatan_kuliah'', ''fakultas'', ''universitas'', ''referensi'') then
        if v_t <> ''string'' or length(v_s) > 200 then return p_key || '' maksimal 200 karakter.''; end if;
    elsif p_key = ''catatan'' then
        if v_t <> ''string'' or length(v_s) > 1000 then return ''Catatan maksimal 1000 karakter.''; end if;
    elsif p_key ~ ''^ipk_(sem([1-9]|10)|pen[1-3])$'' then
        if v_t <> ''number'' then return ''IPK harus angka.''; end if;
        v_n := v_s::numeric;
        if v_n < 0 or v_n > 4 then return ''IPK harus 0 sampai 4.''; end if;
    else
        return ''Field tidak boleh diubah: '' || left(p_key, 40);
    end if;
    return null;
end
';

-- Ubah data siswa dari PR Portal (sama dengan Edit di Data Siswa Flow, kecuali Code, Group Sahabat, Bank, No Rekening,
-- Nama Rekening). Masukan: {code, requested_by, fields:{...}} -- hanya field yang dikirim yang diubah.
-- Keluaran: {ok:true, changed, siswa:{...disamarkan...}} atau {ok:false, pesan} tanpa tulisan apa pun.
create or replace function {{schema}}.fn_prp_update_siswa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_company bigint;
    v_siswa siswa%rowtype;
    v_f jsonb;
    v_k text;
    v_v jsonb;
    v_err text;
    v_n int := 0;
    v_ts text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD"T"HH24:MI:SS'');
begin
    if p is null or jsonb_typeof(p) <> ''object'' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data siswa tidak valid.'');
    end if;
    if jsonb_typeof(p->''code'') is distinct from ''string'' or trim(p->>''code'') = ''''
       or jsonb_typeof(p->''requested_by'') is distinct from ''string'' or trim(p->>''requested_by'') = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data siswa tidak valid.'');
    end if;
    v_f := p->''fields'';
    if jsonb_typeof(v_f) is distinct from ''object'' or v_f = ''{}''::jsonb then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Tidak ada perubahan.'');
    end if;
    for v_k, v_v in select key, value from jsonb_each(v_f) loop
        v_err := fn_prp_siswa_field_error(v_k, v_v);
        if v_err is not null then
            return jsonb_build_object(''ok'', false, ''pesan'', v_err);
        end if;
    end loop;
    select id into v_company from companies where code = ''ETF'';
    select * into v_siswa from siswa where company_id = v_company and code = trim(p->>''code'') for update;
    if not found then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Siswa tidak ditemukan.'');
    end if;
    for v_k, v_v in select key, value from jsonb_each(v_f) loop
        if v_k = ''angkatan'' then
            update siswa set angkatan = (v_v #>> ''{}'')::bigint where id = v_siswa.id;
        elsif v_k like ''ipk\_%'' then
            execute format(''update siswa set %I = $1 where id = $2'', v_k) using (v_v #>> ''{}'')::double precision, v_siswa.id;
        else
            execute format(''update siswa set %I = $1 where id = $2'', v_k) using trim(v_v #>> ''{}''), v_siswa.id;
        end if;
        v_n := v_n + 1;
    end loop;
    update siswa set updated_at = v_ts, updated_by = ''prportal:'' || trim(p->>''requested_by'') where id = v_siswa.id;
    select * into v_siswa from siswa where id = v_siswa.id;
    return jsonb_build_object(''ok'', true, ''changed'', v_n, ''siswa'', fn_prp_siswa_detail(v_siswa));
end
';

-- Pillar vendor -> jenis PA (tabel PA). null bila pillar tidak punya tabel PA ('-', NON PILLAR, NON ALLOCATED, ...).
create or replace function {{schema}}.fn_prp_pillar_jenis(p_pillar text)
returns text
language sql
immutable
as '
    select case upper(trim(coalesce(p_pillar, '''')))
        when ''AGRI'' then ''agri'' when ''APP'' then ''app'' when ''LAND'' then ''sml''
        when ''SETF'' then ''setf'' when ''EFIN'' then ''energy'' when ''ENERGY'' then ''energy'' else null end
';

-- Cari vendor (master Vendors Flow) untuk pembebanan PA. Min 3 huruf, maks 10 hasil, hanya vendor yang pillar-nya
-- punya tabel PA. Hanya id/nama/pillar/cost center/jenis; data bank vendor tidak pernah dikirim.
create or replace function {{schema}}.fn_prp_search_vendor(p_query text)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_q text := trim(coalesce(p_query, ''''));
    v_pat text;
begin
    if length(v_q) < 3 then
        return ''[]''::jsonb;
    end if;
    v_pat := ''%'' || replace(replace(replace(v_q, ''\'', ''\\''), ''%'', ''\%''), ''_'', ''\_'') || ''%'';
    return coalesce((
        select jsonb_agg(jsonb_build_object(
                   ''id'', x.id, ''name'', x.name, ''pillar'', x.pillar,
                   ''cost_center'', coalesce(x.cost_center, ''''), ''jenis'', x.jenis) order by x.name)
          from (select v.id, v.name, v.pillar, v.cost_center, fn_prp_pillar_jenis(v.pillar) as jenis
                  from vendors v
                 where v.name ilike v_pat
                   and fn_prp_pillar_jenis(v.pillar) is not null
                 order by v.name
                 limit 10) x), ''[]''::jsonb);
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
--    vendor_id (bila ada, menentukan jenis dan mengisi pembebanan_*; jenis diabaikan),
--    lines:[{budget_id, tahun_ajaran, jumlah}]}
-- Keluaran: {ok:true, pa_id, pa_number, jenis, total, tgl_payment_application, pembebanan_pt, pembebanan_cost_center} atau {ok:false, pesan} tanpa tulisan apa pun.
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
    v_vendor vendors%rowtype;
    v_pt text;
    v_pt_cc text;
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
    -- Pembebanan: vendor_id (master Vendors) menentukan jenis PA lewat pillar-nya. Tanpa vendor_id dipakai jenis
    -- eksplisit (jalur lama; tidak mengisi pembebanan_pt / pembebanan_cost_center).
    if coalesce(jsonb_typeof(p->''vendor_id''), ''null'') <> ''null'' then
        if jsonb_typeof(p->''vendor_id'') <> ''number'' or (p->>''vendor_id'') !~ ''^[1-9][0-9]{0,17}$'' then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: vendor_id.'');
        end if;
        select * into v_vendor from vendors where id = (p->>''vendor_id'')::bigint;
        if not found then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Vendor tidak ditemukan.'');
        end if;
        v_jenis := fn_prp_pillar_jenis(v_vendor.pillar);
        if v_jenis is null then
            return jsonb_build_object(''ok'', false, ''pesan'',
                ''Vendor '' || v_vendor.name || '' belum punya pillar PA (pillar: '' || coalesce(v_vendor.pillar, ''-'') || ''). Hubungi Finance.'');
        end if;
        v_pt := v_vendor.name;
        v_pt_cc := nullif(trim(coalesce(v_vendor.cost_center, '''')), '''');
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
    foreach v_f in array array[''keterangan'', ''keperluan'', ''attachment_file_id'', ''cost_center''] loop
        if coalesce(jsonb_typeof(p->v_f), ''null'') not in (''null'', ''string'') then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: '' || v_f || ''.'');
        end if;
    end loop;
    -- attachment_poin: huruf a-l dipisah koma, jumlahnya sama dengan jumlah id di attachment_file_id
    if coalesce(jsonb_typeof(p->''attachment_poin''), ''null'') not in (''null'', ''string'') then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: attachment_poin.'');
    end if;
    if coalesce(p->>''attachment_poin'', '''') <> '''' then
        if p->>''attachment_poin'' !~ ''^[a-l](,[a-l])*$''
           or array_length(string_to_array(p->>''attachment_poin'', '',''), 1)
              is distinct from array_length(string_to_array(coalesce(p->>''attachment_file_id'', ''''), '',''), 1) then
            return jsonb_build_object(''ok'', false, ''pesan'', ''Data PA tidak valid: attachment_poin.'');
        end if;
    end if;
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
        || ''created_at, source, requested_by, cost_center, pembebanan_pt, pembebanan_cost_center, attachment_poin, keperluan) ''
        || ''values ($1, fn_etf_pa_next_pa_number($2, $1, $3, $4), $5, $6, $7, $8, $9, $10, $11, $12, $13, ''
        || ''$14, $15, $16, $17, $18, $19, $20, $21) returning id, pa_number'',
        ''{{schema}}'', v_pa_tbl)
      into v_pa_id, v_pa_number
     using v_company, v_pa_tbl, v_prefix, v_year,
           v_today,   -- Tgl PA = tanggal input di server (Jakarta); nilai dari PR Portal tidak dipakai
           coalesce(p->>''tgl_surat_pengajuan'', ''''),
           ''''::text,   -- keterangan = catatan persetujuan FC, diisi FC di Flow
           coalesce(p->>''doc_received_by_educ'', ''''),
           coalesce(p->>''received_pa_from_educ'', ''''),
           ''on_review_fc''::text,   -- menunggu Approve/Reject FC di Flow; Approve -> open (bisa ditarik PAM)
           p->>''route'',
           p->>''klasifikasi'',
           coalesce(p->>''attachment_file_id'', ''''),
           v_ts,
           ''prportal''::text,
           trim(p->>''requested_by''),
           nullif(trim(coalesce(p->>''cost_center'', '''')), ''''),
           v_pt,
           v_pt_cc,
           nullif(coalesce(p->>''attachment_poin'', ''''), ''''),
           coalesce(p->>''keperluan'', p->>''keterangan'', '''');   -- fallback kunci lama: PR Portal versi lama masih mengirim keterangan
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
                              ''jenis'', v_jenis, ''total'', v_total,
                              ''tgl_payment_application'', v_today,
                              ''pembebanan_pt'', v_pt, ''pembebanan_cost_center'', v_pt_cc);
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
            ''keperluan'', coalesce(v_hdr->>''keperluan'', ''''),
            ''route'', v_hdr->>''route'',
            ''klasifikasi'', v_hdr->>''klasifikasi'',
            ''status'', v_hdr->>''status'',
            ''created_at'', v_hdr->>''created_at'',
            ''requested_by'', v_hdr->>''requested_by'',
            ''cost_center'', v_hdr->>''cost_center'',
            ''pembebanan_pt'', v_hdr->>''pembebanan_pt'',
            ''pembebanan_cost_center'', v_hdr->>''pembebanan_cost_center'',
            ''siswa'', jsonb_build_object(
                ''code'', v_sj->''code'', ''nama'', v_sj->''nama'', ''jenjang'', v_sj->''jenjang'',
                ''universitas'', v_sj->''universitas'', ''program'', v_sj->''program'', ''bank'', v_sj->''bank'',
                ''rekening_last4'', v_sj->''rekening_last4'', ''nama_rekening'', v_sj->''nama_rekening'',
                ''angkatan'', v_siswa.angkatan, ''angkatan_kuliah'', coalesce(v_siswa.angkatan_kuliah, '''')),
            ''lines'', v_lines,
            ''total'', (select coalesce(sum((e->>''jumlah_pembayaran'')::numeric), 0)::bigint
                         from jsonb_array_elements(v_lines) e));
    end loop;
    return null;
end
';

-- Status terkini PA milik PR Portal (source='prportal') untuk riwayat di PR Portal: nomor PA -> status, alasan reject,
-- lima tanggal tahap, nomor PAM, tanggal bayar, catatan FC (kolom keterangan); maks 200 nomor. Tanpa data siswa/rekening.
create or replace function {{schema}}.fn_prp_pa_status(p_numbers jsonb)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_tbls text[] := array[''etf_pa'', ''app_pa'', ''sml_pa'', ''setf_pa'', ''energy_pa''];
    v_t text;
    v_nums text[];
    v_out jsonb := ''{}''::jsonb;
    v_part jsonb;
begin
    if p_numbers is null or jsonb_typeof(p_numbers) <> ''array'' then
        return v_out;
    end if;
    select coalesce(array_agg(x), array[]::text[]) into v_nums
      from (select jsonb_array_elements_text(p_numbers) as x limit 200) q;
    foreach v_t in array v_tbls loop
        execute format(
            ''select coalesce(jsonb_object_agg(p.pa_number, jsonb_build_object(''''status'''', p.status, ''''reject_reason'''', p.reject_reason, ''''checked_by_fincon'''', p.checked_by_fincon, ''''approved_by_htj_1'''', p.approved_by_htj_1, ''''send_pa_back_to_educ'''', p.send_pa_back_to_educ, ''''pa_received_by_po_fin'''', p.pa_received_by_po_fin, ''''approval_by_htj_2'''', p.approval_by_htj_2, ''''nomor_pam'''', p.nomor_pam, ''''tanggal_bayar'''', p.tanggal_bayar, ''''catatan_fc'''', p.keterangan, ''''attachment_poin'''', p.attachment_poin, ''''serah_status'''', p.serah_status, ''''serah_at'''', p.serah_at, ''''serah_catatan'''', p.serah_catatan, ''''terima_at'''', p.terima_at, ''''pa_verified_by_po_fin'''', p.pa_verified_by_po_fin, ''''verif_at'''', p.verif_at, ''''verif_catatan'''', p.verif_catatan)), ''''{}''''::jsonb) ''
            || ''from %I.%I p where p.source = ''''prportal'''' and p.pa_number = any($1)'',
            ''{{schema}}'', v_t)
          into v_part using v_nums;
        v_out := v_out || v_part;
    end loop;
    return v_out;
end
';

-- Serah terima dokumen fisik PA Beasiswa. Pelaku diteruskan PR Portal (email sesi); kepemilikan & prasyarat dicek di sini.
-- Alur: pemohon serahkan (menunggu) -> Finance terima (menunggu_verifikasi) -> Verificator verifikasi (terverifikasi) atau tolak
-- (dikembalikan ke Finance) -> Finance teruskan (menunggu_verifikasi) atau tolak ke pemohon (ditolak). Setiap transisi ditulis ke
-- pa_serah_log; UPDATE bersyarat pada serah_status membuat dua pemanggil bersamaan hanya satu yang berhasil.
-- Letak PA (tabel + id) dari nomor PA, hanya source='prportal'.
create or replace function {{schema}}.fn_prp_pa_locate(p_pa_number text)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_tbls text[] := array[''etf_pa'', ''app_pa'', ''sml_pa'', ''setf_pa'', ''energy_pa''];
    v_t text;
    v_id bigint;
begin
    if p_pa_number is null or trim(p_pa_number) = '''' then
        return null;
    end if;
    foreach v_t in array v_tbls loop
        v_id := null;
        execute format(''select id from %I.%I where pa_number = $1 and source = ''''prportal'''' order by id desc limit 1'',
                       ''{{schema}}'', v_t) into v_id using p_pa_number;
        if v_id is not null then
            return jsonb_build_object(''tbl'', v_t, ''id'', v_id);
        end if;
    end loop;
    return null;
end
';

create or replace function {{schema}}.fn_prp_serah_log_add(p_pa_number text, p_kejadian text, p_oleh text, p_catatan text)
returns void
language plpgsql
volatile
set search_path = {{schema}}
as '
begin
    insert into pa_serah_log (pa_number, kejadian, oleh, waktu, catatan)
    values (p_pa_number, p_kejadian, p_oleh, to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD HH24:MI:SS''),
            nullif(coalesce(p_catatan, ''''), ''''));
end
';

create or replace function {{schema}}.fn_prp_serah_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_loc jsonb;
    v_row jsonb;
    v_by text := lower(trim(coalesce(p->>''requested_by'', '''')));
    v_now text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD HH24:MI:SS'');
    v_n int;
begin
    if jsonb_typeof(p->''pa_number'') is distinct from ''string'' or v_by = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data serah terima tidak valid.'');
    end if;
    v_loc := fn_prp_pa_locate(p->>''pa_number'');
    if v_loc is null then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    execute format(''select to_jsonb(t) from %I.%I t where id = $1'', ''{{schema}}'', v_loc->>''tbl'')
       into v_row using (v_loc->>''id'')::bigint;
    if lower(trim(coalesce(v_row->>''requested_by'', ''''))) <> v_by then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    if coalesce(v_row->>''status'', '''') <> ''open'' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA belum disetujui FC (status bukan Open).'');
    end if;
    if coalesce(v_row->>''send_pa_back_to_educ'', '''') = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Dokumen belum dikembalikan ke pemohon (Send Back Educ belum terisi).'');
    end if;
    if coalesce(v_row->>''pa_received_by_po_fin'', '''') <> '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Dokumen fisik PA ini sudah diterima Finance.'');
    end if;
    if v_row->>''serah_status'' = ''menunggu'' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA sudah diserahkan dan menunggu Finance.'');
    end if;
    if v_row->>''serah_status'' in (''menunggu_verifikasi'', ''dikembalikan'', ''terverifikasi'') then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA sudah diserahkan dan sedang diproses.'');
    end if;
    execute format(''update %I.%I set serah_status = ''''menunggu'''', serah_at = $2, serah_by = $3, serah_catatan = null, ''
                   || ''terima_by = null, terima_at = null, verif_by = null, verif_at = null, verif_catatan = null ''
                   || ''where id = $1 and status = ''''open'''' ''
                   || ''and coalesce(pa_received_by_po_fin, '''''''') = '''''''' ''
                   || ''and coalesce(serah_status, '''''''') not in (''''menunggu'''', ''''menunggu_verifikasi'''', ''''dikembalikan'''', ''''terverifikasi'''')'',
                   ''{{schema}}'', v_loc->>''tbl'')
      using (v_loc->>''id'')::bigint, v_now, v_by;
    get diagnostics v_n = row_count;
    if v_n = 0 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA sudah diserahkan atau diproses.'');
    end if;
    perform fn_prp_serah_log_add(p->>''pa_number'', ''diserahkan'', v_by, null);
    return jsonb_build_object(''ok'', true);
end
';

create or replace function {{schema}}.fn_prp_terima_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_loc jsonb;
    v_by text := lower(trim(coalesce(p->>''oleh'', '''')));
    v_now text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD HH24:MI:SS'');
    v_today text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD'');
    v_n int;
begin
    if jsonb_typeof(p->''pa_number'') is distinct from ''string'' or v_by = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data penerimaan tidak valid.'');
    end if;
    v_loc := fn_prp_pa_locate(p->>''pa_number'');
    if v_loc is null then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    execute format(''update %I.%I set serah_status = ''''menunggu_verifikasi'''', pa_received_by_po_fin = $2, terima_by = $3, terima_at = $4, ''
                   || ''verif_catatan = null where id = $1 and serah_status = ''''menunggu'''' and coalesce(pa_received_by_po_fin, '''''''') = '''''''''',
                   ''{{schema}}'', v_loc->>''tbl'')
      using (v_loc->>''id'')::bigint, v_today, v_by, v_now;
    get diagnostics v_n = row_count;
    if v_n = 0 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA ini tidak sedang menunggu penerimaan Finance.'');
    end if;
    perform fn_prp_serah_log_add(p->>''pa_number'', ''diterima_finance'', v_by, null);
    return jsonb_build_object(''ok'', true, ''tanggal'', v_today);
end
';

create or replace function {{schema}}.fn_prp_tolak_serah_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_loc jsonb;
    v_by text := lower(trim(coalesce(p->>''oleh'', '''')));
    v_alasan text := trim(coalesce(p->>''alasan'', ''''));
    v_now text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD HH24:MI:SS'');
    v_n int;
begin
    if jsonb_typeof(p->''pa_number'') is distinct from ''string'' or v_by = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data penolakan tidak valid.'');
    end if;
    if v_alasan = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Alasan penolakan wajib diisi.'');
    end if;
    if char_length(v_alasan) > 300 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Alasan penolakan maksimal 300 karakter.'');
    end if;
    v_loc := fn_prp_pa_locate(p->>''pa_number'');
    if v_loc is null then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    -- dari dikembalikan (Verificator -> Finance -> pemohon): siklus penerimaan diulang, jadi dua tanggal dikosongkan
    -- (riwayat tetap menyimpan tanggal lama); dari menunggu: tanggal tidak disentuh.
    execute format(''update %I.%I set pa_received_by_po_fin = case when serah_status = ''''dikembalikan'''' then '''''''' else pa_received_by_po_fin end, ''
                   || ''pa_verified_by_po_fin = case when serah_status = ''''dikembalikan'''' then null else pa_verified_by_po_fin end, ''
                   || ''serah_status = ''''ditolak'''', serah_catatan = $2, terima_by = $3, terima_at = $4 ''
                   || ''where id = $1 and serah_status in (''''menunggu'''', ''''dikembalikan'''')'',
                   ''{{schema}}'', v_loc->>''tbl'')
      using (v_loc->>''id'')::bigint, v_alasan, v_by, v_now;
    get diagnostics v_n = row_count;
    if v_n = 0 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA ini tidak sedang menunggu penerimaan Finance.'');
    end if;
    perform fn_prp_serah_log_add(p->>''pa_number'', ''ditolak_finance'', v_by, v_alasan);
    return jsonb_build_object(''ok'', true);
end
';

create or replace function {{schema}}.fn_prp_verifikasi_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_loc jsonb;
    v_row jsonb;
    v_by text := lower(trim(coalesce(p->>''oleh'', '''')));
    v_now text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD HH24:MI:SS'');
    v_today text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD'');
    v_n int;
begin
    if jsonb_typeof(p->''pa_number'') is distinct from ''string'' or v_by = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data verifikasi tidak valid.'');
    end if;
    v_loc := fn_prp_pa_locate(p->>''pa_number'');
    if v_loc is null then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    execute format(''select to_jsonb(t) from %I.%I t where id = $1'', ''{{schema}}'', v_loc->>''tbl'')
       into v_row using (v_loc->>''id'')::bigint;
    if v_row->>''serah_status'' is distinct from ''menunggu_verifikasi'' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA ini tidak sedang menunggu verifikasi.'');
    end if;
    if coalesce(v_row->>''nomor_pam'', '''') = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA belum punya Nomor PAM; PAM harus dibuat Finance sebelum verifikasi.'');
    end if;
    execute format(''update %I.%I set serah_status = ''''terverifikasi'''', pa_verified_by_po_fin = $2, verif_by = $3, verif_at = $4, verif_catatan = null ''
                   || ''where id = $1 and serah_status = ''''menunggu_verifikasi'''' and coalesce(nomor_pam, '''''''') <> '''''''''',
                   ''{{schema}}'', v_loc->>''tbl'')
      using (v_loc->>''id'')::bigint, v_today, v_by, v_now;
    get diagnostics v_n = row_count;
    if v_n = 0 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA ini tidak sedang menunggu verifikasi.'');
    end if;
    perform fn_prp_serah_log_add(p->>''pa_number'', ''terverifikasi'', v_by, null);
    return jsonb_build_object(''ok'', true, ''tanggal'', v_today);
end
';

create or replace function {{schema}}.fn_prp_tolak_verifikasi_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_loc jsonb;
    v_by text := lower(trim(coalesce(p->>''oleh'', '''')));
    v_alasan text := trim(coalesce(p->>''alasan'', ''''));
    v_now text := to_char(now() at time zone interval ''+07:00'', ''YYYY-MM-DD HH24:MI:SS'');
    v_n int;
begin
    if jsonb_typeof(p->''pa_number'') is distinct from ''string'' or v_by = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data penolakan tidak valid.'');
    end if;
    if v_alasan = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Alasan penolakan wajib diisi.'');
    end if;
    if char_length(v_alasan) > 300 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Alasan penolakan maksimal 300 karakter.'');
    end if;
    v_loc := fn_prp_pa_locate(p->>''pa_number'');
    if v_loc is null then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    execute format(''update %I.%I set serah_status = ''''dikembalikan'''', verif_catatan = $2, verif_by = $3, verif_at = $4 ''
                   || ''where id = $1 and serah_status = ''''menunggu_verifikasi'''''',
                   ''{{schema}}'', v_loc->>''tbl'')
      using (v_loc->>''id'')::bigint, v_alasan, v_by, v_now;
    get diagnostics v_n = row_count;
    if v_n = 0 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA ini tidak sedang menunggu verifikasi.'');
    end if;
    perform fn_prp_serah_log_add(p->>''pa_number'', ''dikembalikan_verificator'', v_by, v_alasan);
    return jsonb_build_object(''ok'', true);
end
';

create or replace function {{schema}}.fn_prp_teruskan_pa(p jsonb)
returns jsonb
language plpgsql
volatile
set search_path = {{schema}}
as '
declare
    v_loc jsonb;
    v_by text := lower(trim(coalesce(p->>''oleh'', '''')));
    v_n int;
begin
    if jsonb_typeof(p->''pa_number'') is distinct from ''string'' or v_by = '''' then
        return jsonb_build_object(''ok'', false, ''pesan'', ''Data penerusan tidak valid.'');
    end if;
    v_loc := fn_prp_pa_locate(p->>''pa_number'');
    if v_loc is null then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA tidak ditemukan.'');
    end if;
    execute format(''update %I.%I set serah_status = ''''menunggu_verifikasi'''', verif_catatan = null ''
                   || ''where id = $1 and serah_status = ''''dikembalikan'''''',
                   ''{{schema}}'', v_loc->>''tbl'')
      using (v_loc->>''id'')::bigint;
    get diagnostics v_n = row_count;
    if v_n = 0 then
        return jsonb_build_object(''ok'', false, ''pesan'', ''PA ini tidak sedang dikembalikan Verificator.'');
    end if;
    perform fn_prp_serah_log_add(p->>''pa_number'', ''diteruskan_finance'', v_by, null);
    return jsonb_build_object(''ok'', true);
end
';

-- Daftar kerja Finance: PA menunggu diterima (belum ada PA Recv PO Fin) dan PA yang dikembalikan Verificator.
create or replace function {{schema}}.fn_prp_list_serah()
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_tbls text[] := array[''etf_pa'', ''app_pa'', ''sml_pa'', ''setf_pa'', ''energy_pa''];
    v_t text;
    v_all jsonb := ''[]''::jsonb;
    v_part jsonb;
begin
    foreach v_t in array v_tbls loop
        execute format(
            ''select coalesce(jsonb_agg(jsonb_build_object(''''pa_number'''', t.pa_number, ''''requested_by'''', t.requested_by, ''''cost_center'''', t.cost_center, ''
            || ''''''total'''', (select coalesce(sum(l.jumlah_pembayaran), 0) from %I.%I l where l.pa_id = t.id), ''
            || ''''''serah_at'''', t.serah_at, ''''serah_by'''', t.serah_by, ''''status'''', t.serah_status, ''
            || ''''''catatan'''', case when t.serah_status = ''''dikembalikan'''' then coalesce(t.verif_catatan, '''''''') else '''''''' end, ''
            || ''''''nomor_pam'''', coalesce(t.nomor_pam, '''''''')) ''
            || ''), ''''[]''''::jsonb) from %I.%I t where t.source = ''''prportal'''' and (''
            || ''(t.serah_status = ''''menunggu'''' and coalesce(t.pa_received_by_po_fin, '''''''') = '''''''') or t.serah_status = ''''dikembalikan'''')'',
            ''{{schema}}'', v_t || ''_lines'', ''{{schema}}'', v_t)
          into v_part;
        v_all := v_all || v_part;
    end loop;
    return jsonb_build_object(''ok'', true,
        ''rows'', (select coalesce(jsonb_agg(e order by e->>''serah_at'', e->>''pa_number''), ''[]''::jsonb) from jsonb_array_elements(v_all) e));
end
';

-- Daftar kerja Verificator: PA yang sudah diterima Finance dan menunggu verifikasi.
create or replace function {{schema}}.fn_prp_list_verifikasi()
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
declare
    v_tbls text[] := array[''etf_pa'', ''app_pa'', ''sml_pa'', ''setf_pa'', ''energy_pa''];
    v_t text;
    v_all jsonb := ''[]''::jsonb;
    v_part jsonb;
begin
    foreach v_t in array v_tbls loop
        execute format(
            ''select coalesce(jsonb_agg(jsonb_build_object(''''pa_number'''', t.pa_number, ''''requested_by'''', t.requested_by, ''''cost_center'''', t.cost_center, ''
            || ''''''total'''', (select coalesce(sum(l.jumlah_pembayaran), 0) from %I.%I l where l.pa_id = t.id), ''
            || ''''''nomor_pam'''', coalesce(t.nomor_pam, ''''''''), ''''terima_at'''', t.terima_at)), ''''[]''''::jsonb) ''
            || ''from %I.%I t where t.source = ''''prportal'''' and t.serah_status = ''''menunggu_verifikasi'''''',
            ''{{schema}}'', v_t || ''_lines'', ''{{schema}}'', v_t)
          into v_part;
        v_all := v_all || v_part;
    end loop;
    return jsonb_build_object(''ok'', true,
        ''rows'', (select coalesce(jsonb_agg(e order by e->>''terima_at'', e->>''pa_number''), ''[]''::jsonb) from jsonb_array_elements(v_all) e));
end
';

-- Riwayat serah terima satu PA (kronologis). Hanya PA source=prportal.
create or replace function {{schema}}.fn_prp_serah_log(p_pa_number text)
returns jsonb
language plpgsql
stable
set search_path = {{schema}}
as '
begin
    if fn_prp_pa_locate(p_pa_number) is null then
        return jsonb_build_object(''ok'', true, ''rows'', ''[]''::jsonb);
    end if;
    return jsonb_build_object(''ok'', true, ''rows'',
        (select coalesce(jsonb_agg(jsonb_build_object(''kejadian'', l.kejadian, ''oleh'', l.oleh, ''waktu'', l.waktu, ''catatan'', coalesce(l.catatan, ''''))
                                   order by l.waktu, l.id), ''[]''::jsonb)
           from pa_serah_log l where l.pa_number = p_pa_number));
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

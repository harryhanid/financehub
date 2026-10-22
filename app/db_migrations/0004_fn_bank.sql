-- 0004_fn_bank.sql
-- Rekonsiliasi bank_setf terhadap satu pam_records SETF secara atomik (Task 9, atomic-flows.md).
-- Placeholder {{schema}} diganti apply_migrations.py.
--
-- fn_sync_pam_to_bank_setf(pam_id): terjemahan setia modules/bank/service.py sync_pam_to_bank_setf.
-- Dulu baca SUM -> hitung delta di Python -> DELETE/INSERT di beberapa panggilan; dua panggilan
-- bersamaan untuk PAM yang sama bisa menyisipkan delta dua kali, dan cabang delta<0 (DELETE lalu
-- INSERT) bisa berhenti setelah DELETE. Sekarang baca + hitung + tulis dalam satu transaksi di bawah
-- advisory lock per pam_id.
-- Hasil: 0 = tidak ada perubahan / PAM tidak ada, 1 = baris pam dihapus (bukan SETF/complete/partial),
-- 2 = delta disisipkan, 3 = baris dilipat ulang (delta negatif).
-- Badan fungsi ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak
-- memecah di ';' di dalam badan.

create or replace function {{schema}}.fn_sync_pam_to_bank_setf(p_pam_id bigint)
returns integer
language plpgsql
volatile
as '
declare
    v_pam record;
    v_has_lines boolean;
    v_paid double precision;
    v_recorded double precision;
    v_latest text;
    v_delta double precision;
    v_tanggal text;
begin
    perform pg_advisory_xact_lock(hashtext(''bank_setf:pam:'' || p_pam_id::text));

    select p."id", p."company_id", p."pam_no", p."tanggal_bayar", p."pam_date", p."keterangan",
           p."pillar", p."status", p."total_amount"
      into v_pam
      from {{schema}}."pam_records" p
     where p."id" = p_pam_id;
    if not found then
        return 0;
    end if;

    -- Python: pillar != ''SETF'' or status not in (''complete'', ''partial'') (NULL ikut cabang ini)
    if v_pam."pillar" is distinct from ''SETF''
       or v_pam."status" is null
       or v_pam."status" not in (''complete'', ''partial'') then
        delete from {{schema}}."bank_setf" b
         where b."pam_record_id" = p_pam_id and b."source" = ''pam'';
        return 1;
    end if;

    select exists (
        select 1 from {{schema}}."payment_beasiswa" pb
         where pb."pam" = v_pam."pam_no" and pb."company_id" = v_pam."company_id"
    ) into v_has_lines;

    if v_has_lines then
        select coalesce(sum(pb."amount"), 0) into v_paid
          from {{schema}}."payment_beasiswa" pb
         where pb."pam" = v_pam."pam_no" and pb."company_id" = v_pam."company_id"
           and pb."status" = ''complete'';
    elsif v_pam."status" = ''complete'' then
        v_paid := v_pam."total_amount";
    else
        v_paid := 0;
    end if;

    select coalesce(sum(b."jumlah"), 0) into v_recorded
      from {{schema}}."bank_setf" b
     where b."pam_record_id" = p_pam_id and b."source" = ''pam'';

    select max(pb."tgl_Paid_SETF") into v_latest
      from {{schema}}."payment_beasiswa" pb
     where pb."pam" = v_pam."pam_no" and pb."company_id" = v_pam."company_id"
       and pb."status" = ''complete'' and pb."tgl_Paid_SETF" is not null;

    v_delta := v_paid - v_recorded;
    -- Python: latest_paid or tanggal_bayar or pam_date (teks kosong dianggap falsy)
    v_tanggal := coalesce(nullif(v_latest, ''''), nullif(v_pam."tanggal_bayar", ''''), v_pam."pam_date");

    if v_delta > 0.01 then
        insert into {{schema}}."bank_setf"
            ("company_id", "tanggal", "jenis", "jumlah", "keterangan", "source", "pam_record_id")
        values (v_pam."company_id", v_tanggal, ''pengeluaran'', v_delta, v_pam."keterangan", ''pam'', p_pam_id);
        return 2;
    elsif v_delta < -0.01 then
        delete from {{schema}}."bank_setf" b
         where b."pam_record_id" = p_pam_id and b."source" = ''pam'';
        if v_paid > 0.01 then
            insert into {{schema}}."bank_setf"
                ("company_id", "tanggal", "jenis", "jumlah", "keterangan", "source", "pam_record_id")
            values (v_pam."company_id", v_tanggal, ''pengeluaran'', v_paid, v_pam."keterangan", ''pam'', p_pam_id);
        end if;
        return 3;
    end if;
    return 0;
end
';

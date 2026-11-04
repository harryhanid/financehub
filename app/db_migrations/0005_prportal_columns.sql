-- 0005_prportal_columns.sql
-- Kolom tambahan untuk integrasi PR Portal -> Flow (PA Beasiswa).
-- Placeholder {{schema}} diganti apply_migrations.py. Idempoten (aman dijalankan ulang).
--
-- 1. budget_beasiswa.status: open | on_progress | complete (status efektif non_aktif dihitung saat dibaca).
-- 2. budget_id di baris PA kelima jenis (etf/app/sml/setf/energy): budget yang dibayar oleh baris itu.
-- 3. source / requested_by / cost_center di header PA: asal PA ('flow' = dibuat di Flow, 'prportal').
-- Badan DO ditulis sebagai literal '...' (bukan $$) supaya split_script (fhdb.sqlbind) tidak memecah
-- di ';' di dalam badan.

alter table {{schema}}.budget_beasiswa add column if not exists "status" text collate "C" not null default 'open';

do '
begin
    if not exists (
        select 1 from pg_constraint
        where conname = ''budget_beasiswa_status_check''
          and conrelid = ''{{schema}}.budget_beasiswa''::regclass
    ) then
        alter table {{schema}}.budget_beasiswa
            add constraint budget_beasiswa_status_check check ("status" in (''open'', ''on_progress'', ''complete''));
    end if;
end
';

alter table {{schema}}.etf_pa_lines add column if not exists "budget_id" bigint;
alter table {{schema}}.app_pa_lines add column if not exists "budget_id" bigint;
alter table {{schema}}.sml_pa_lines add column if not exists "budget_id" bigint;
alter table {{schema}}.setf_pa_lines add column if not exists "budget_id" bigint;
alter table {{schema}}.energy_pa_lines add column if not exists "budget_id" bigint;

create index if not exists etf_pa_lines_budget_id_idx on {{schema}}.etf_pa_lines ("budget_id");
create index if not exists app_pa_lines_budget_id_idx on {{schema}}.app_pa_lines ("budget_id");
create index if not exists sml_pa_lines_budget_id_idx on {{schema}}.sml_pa_lines ("budget_id");
create index if not exists setf_pa_lines_budget_id_idx on {{schema}}.setf_pa_lines ("budget_id");
create index if not exists energy_pa_lines_budget_id_idx on {{schema}}.energy_pa_lines ("budget_id");

alter table {{schema}}.etf_pa add column if not exists "source" text collate "C" not null default 'flow';
alter table {{schema}}.etf_pa add column if not exists "requested_by" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "cost_center" text collate "C";
alter table {{schema}}.app_pa add column if not exists "source" text collate "C" not null default 'flow';
alter table {{schema}}.app_pa add column if not exists "requested_by" text collate "C";
alter table {{schema}}.app_pa add column if not exists "cost_center" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "source" text collate "C" not null default 'flow';
alter table {{schema}}.sml_pa add column if not exists "requested_by" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "cost_center" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "source" text collate "C" not null default 'flow';
alter table {{schema}}.setf_pa add column if not exists "requested_by" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "cost_center" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "source" text collate "C" not null default 'flow';
alter table {{schema}}.energy_pa add column if not exists "requested_by" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "cost_center" text collate "C";

-- 4. Pembebanan PA: vendor (Nama PT) dan Cost Center-nya, dipilih di PR Portal dari master Vendors Flow.
-- Terpisah dari cost_center di atas (cost center pemohon). Diisi hanya untuk PA yang masuk lewat vendor_id.
alter table {{schema}}.etf_pa add column if not exists "pembebanan_pt" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "pembebanan_cost_center" text collate "C";
alter table {{schema}}.app_pa add column if not exists "pembebanan_pt" text collate "C";
alter table {{schema}}.app_pa add column if not exists "pembebanan_cost_center" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "pembebanan_pt" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "pembebanan_cost_center" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "pembebanan_pt" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "pembebanan_cost_center" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "pembebanan_pt" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "pembebanan_cost_center" text collate "C";

-- 5. siswa.updated_by: siapa yang terakhir mengubah data siswa lewat PR Portal ('prportal:<email>'); null bila lewat Flow.
alter table {{schema}}.siswa add column if not exists "updated_by" text collate "C";

-- 6. attachment_poin: huruf poin checklist lampiran (a-l) per file di attachment_file_id, sejajar urutannya
-- (mis. 'a,c,h'). Diisi PR Portal; kosong untuk PA yang dibuat di Flow.
alter table {{schema}}.etf_pa add column if not exists "attachment_poin" text collate "C";
alter table {{schema}}.app_pa add column if not exists "attachment_poin" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "attachment_poin" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "attachment_poin" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "attachment_poin" text collate "C";

-- 7. keperluan: Keperluan/Penjelasan yang diketik pemohon di PR Portal (tampil di Flow dan cetak PA). Kolom keterangan
-- khusus catatan persetujuan FC. Backfill PA PR Portal lama: salin keterangan -> keperluan, kosongkan keterangan.
alter table {{schema}}.etf_pa add column if not exists "keperluan" text collate "C";
alter table {{schema}}.app_pa add column if not exists "keperluan" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "keperluan" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "keperluan" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "keperluan" text collate "C";
update {{schema}}.etf_pa set keperluan = keterangan, keterangan = '' where source = 'prportal' and keperluan is null;
update {{schema}}.app_pa set keperluan = keterangan, keterangan = '' where source = 'prportal' and keperluan is null;
update {{schema}}.sml_pa set keperluan = keterangan, keterangan = '' where source = 'prportal' and keperluan is null;
update {{schema}}.setf_pa set keperluan = keterangan, keterangan = '' where source = 'prportal' and keperluan is null;
update {{schema}}.energy_pa set keperluan = keterangan, keterangan = '' where source = 'prportal' and keperluan is null;

-- 8. Serah terima dokumen fisik PA Beasiswa: pemohon menyerahkan (menunggu), Finance menerima (diterima, mengisi
-- pa_received_by_po_fin) atau menolak (ditolak + serah_catatan). terima_by/terima_at = Finance yang memproses (terima ATAU tolak).
alter table {{schema}}.etf_pa add column if not exists "serah_status" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "serah_at" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "serah_by" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "serah_catatan" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "terima_by" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "terima_at" text collate "C";
alter table {{schema}}.app_pa add column if not exists "serah_status" text collate "C";
alter table {{schema}}.app_pa add column if not exists "serah_at" text collate "C";
alter table {{schema}}.app_pa add column if not exists "serah_by" text collate "C";
alter table {{schema}}.app_pa add column if not exists "serah_catatan" text collate "C";
alter table {{schema}}.app_pa add column if not exists "terima_by" text collate "C";
alter table {{schema}}.app_pa add column if not exists "terima_at" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "serah_status" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "serah_at" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "serah_by" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "serah_catatan" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "terima_by" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "terima_at" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "serah_status" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "serah_at" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "serah_by" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "serah_catatan" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "terima_by" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "terima_at" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "serah_status" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "serah_at" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "serah_by" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "serah_catatan" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "terima_by" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "terima_at" text collate "C";

-- 9. Verifikasi Verificator (PA Verified PO Fin): tanggal + pelaku terkini. serah_status diperluas: menunggu | ditolak |
-- menunggu_verifikasi | dikembalikan | terverifikasi. Nilai lama 'diterima' dipetakan ke menunggu_verifikasi.
alter table {{schema}}.etf_pa add column if not exists "pa_verified_by_po_fin" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "verif_by" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "verif_at" text collate "C";
alter table {{schema}}.etf_pa add column if not exists "verif_catatan" text collate "C";
alter table {{schema}}.app_pa add column if not exists "pa_verified_by_po_fin" text collate "C";
alter table {{schema}}.app_pa add column if not exists "verif_by" text collate "C";
alter table {{schema}}.app_pa add column if not exists "verif_at" text collate "C";
alter table {{schema}}.app_pa add column if not exists "verif_catatan" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "pa_verified_by_po_fin" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "verif_by" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "verif_at" text collate "C";
alter table {{schema}}.sml_pa add column if not exists "verif_catatan" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "pa_verified_by_po_fin" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "verif_by" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "verif_at" text collate "C";
alter table {{schema}}.setf_pa add column if not exists "verif_catatan" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "pa_verified_by_po_fin" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "verif_by" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "verif_at" text collate "C";
alter table {{schema}}.energy_pa add column if not exists "verif_catatan" text collate "C";
update {{schema}}.etf_pa set serah_status = 'menunggu_verifikasi' where serah_status = 'diterima';
update {{schema}}.app_pa set serah_status = 'menunggu_verifikasi' where serah_status = 'diterima';
update {{schema}}.sml_pa set serah_status = 'menunggu_verifikasi' where serah_status = 'diterima';
update {{schema}}.setf_pa set serah_status = 'menunggu_verifikasi' where serah_status = 'diterima';
update {{schema}}.energy_pa set serah_status = 'menunggu_verifikasi' where serah_status = 'diterima';

-- Riwayat serah terima: satu baris per kejadian (tidak pernah dihapus). Kejadian: diserahkan, diterima_finance, ditolak_finance,
-- dikembalikan_verificator, diteruskan_finance, terverifikasi. Waktu WIB 'YYYY-MM-DD HH24:MI:SS'.
create table if not exists {{schema}}.pa_serah_log (
    id bigserial primary key,
    pa_number text collate "C" not null,
    kejadian text collate "C" not null,
    oleh text collate "C",
    waktu text collate "C" not null,
    catatan text collate "C"
);
create index if not exists pa_serah_log_pa_number_idx on {{schema}}.pa_serah_log (pa_number);
alter table {{schema}}.pa_serah_log enable row level security;

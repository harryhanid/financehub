-- 0007_sponsorship_proposal_tipe_attachment.sql
alter table if exists {{schema}}."sponsorship_proposal" add column if not exists "tipe" text default 'Form';
alter table if exists {{schema}}."sponsorship_proposal" add column if not exists "attachment_file_id" text default '';
alter table if exists {{schema}}."sponsorship_proposal" add column if not exists "attachment_filename" text default '';

update {{schema}}."sponsorship_proposal" set "tipe" = 'Form' where "tipe" is null or "tipe" = '';

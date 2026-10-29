-- 0006_sponsorship_proposal_sync.sql
alter table if exists {{schema}}."sponsorship_transaksi" add column if not exists "proposal_id" bigint;
create index if not exists idx_sp_transaksi_proposal_id on {{schema}}."sponsorship_transaksi" ("proposal_id");

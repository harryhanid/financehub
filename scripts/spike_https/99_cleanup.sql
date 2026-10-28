-- Hapus semua sisa spike HTTPS. Jalankan di Supabase Dashboard > SQL Editor setelah uji selesai.
drop function if exists public.fh_spike_exec(jsonb);
drop schema if exists fh_spike cascade;
notify pgrst, 'reload schema';

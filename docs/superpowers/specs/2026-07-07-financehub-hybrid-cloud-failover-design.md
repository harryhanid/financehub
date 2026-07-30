# FinanceHub — Hybrid Local/Cloud Failover — PRD & Design Spec

**Date:** 2026-07-07 (revisi arsitektur: 2026-07-07)
**Status:** Approved — siap masuk implementation plan
**Scope:** Availability & remote-access failover untuk FinanceHub app (bukan modul fitur baru)

> **Catatan revisi:** Desain awal dokumen ini memakai Cloudflare Tunnel + Cloudflare Worker. Setelah dites langsung (lihat §4.1), laptop yang menjalankan FinanceHub ternyata **tidak bisa mengunduh binary dari GitHub Releases** (jalur distribusi `cloudflared` dan `Litestream`) karena diblokir jaringan kantor — baik lewat command line maupun browser biasa. Arsitektur direvisi total di §5–§14 supaya hanya bergantung pada `pip install` (PyPI, sudah terverifikasi bisa diakses) tanpa binary eksternal apa pun.

---

## 1. Latar Belakang

FinanceHub saat ini berjalan sebagai Flask + SQLite di laptop lokal (Harry atau teman), diakses lewat LAN via `http://financehub.local:8081` (mDNS). Sync satu-arah SQLite → Supabase Postgres pernah didesain (2026-06-24) sebagai read-only replica untuk reporting, **tapi setelah dicek langsung ke codebase (`C:\Financehub`, termasuk semua worktree) sync ini ternyata belum pernah diimplementasikan** — tidak ada kode, tidak ada `.env`, APScheduler yang ada cuma untuk job backup Excel/PDF. Implementation plan untuk desain ini karena itu harus membangun sync dari nol, bukan "memperluas" yang sudah ada.

**Masalah:**
1. Kalau laptop yang menjalankan server dimatikan atau sleep, FinanceHub sepenuhnya tidak bisa diakses siapa pun.
2. Tidak ada cara akses dari luar LAN kantor (WFH, mobile).
3. Data keuangan SMT/ETF sensitif — tidak mau dipindah permanen ke cloud, hanya boleh "numpang" di cloud saat darurat.
4. **Laptop yang menjalankan server bukan mesin dengan hak admin, dan jaringannya memblokir download binary dari GitHub Releases** (lihat §4.1) — ini membatasi tools apa saja yang boleh dipakai di sisi lokal.

**Tujuan dokumen ini:** mendesain infrastruktur hybrid local/cloud supaya app tetap bisa diakses (baca & tulis) walau laptop lokal mati, tanpa memindahkan data secara permanen ke cloud, tanpa biaya bulanan baru, dan **tanpa butuh instalasi/download binary apa pun di laptop lokal** — hanya `pip install --user` package Python biasa.

---

## 2. Goals

| # | Goal |
|---|---|
| G1 | Satu URL publik tetap, tidak peduli yang melayani request itu server lokal atau cloud standby |
| G2 | Kalau lokal down, user tetap bisa baca **dan tulis** data dalam hitungan puluhan detik, otomatis — tanpa perlu ganti URL manual |
| G3 | Data finansial SMT/ETF tetap di SQLite lokal sebagai source of truth pada kondisi normal; cloud hanya writable selama window darurat |
| G4 | Seluruh infrastruktur failover ini muat di free tier (Render/Fly.io, Supabase) — tidak ada biaya bulanan baru |
| G5 | Saat lokal kembali online, semua tulisan yang terjadi selama outage tersinkron balik ke SQLite otomatis, tanpa duplikat/ID collision |
| G6 | **Semua komponen di sisi laptop lokal HARUS bisa dipasang lewat `pip install --user` saja** — tidak ada `.exe`/`.msi`/binary GitHub Releases apa pun |

## 3. Non-Goals (Out of Scope)

- Multi-master (lokal & cloud menerima tulisan bersamaan) — sengaja dihindari, sesuai keputusan model failover
- Zero-downtime absolut — window deteksi beberapa detik dianggap dapat diterima
- Akses file attachment/PDF export saat berjalan dari cloud standby
- Memindahkan database utama secara permanen ke cloud
- Pembelian domain custom (pakai subdomain gratis dari Render/Fly.io, bisa upgrade nanti)
- Akses luar-LAN yang selalu real-time identik dengan lokal saat lokal justru sedang sehat — remote access tetap lewat relay yang sama (lihat §5), bukan koneksi terpisah, supaya tidak membuka celah multi-master

---

## 4. Approaches yang Dipertimbangkan

| Approach | Deskripsi | Keputusan |
|---|---|---|
| 1. Redirect-based via Cloudflare Worker + Tunnel | Worker cek health lokal via Cloudflare Tunnel, 302 redirect | ❌ **Dibatalkan setelah dites** — `cloudflared` didistribusikan lewat GitHub Releases yang diblokir jaringan kantor (§4.1) |
| 2. Transparent reverse-proxy via Cloudflare Worker | Sama seperti di atas tapi proxy penuh | ❌ Dibatalkan — bergantung pada Cloudflare Tunnel juga |
| 3. Cloud-primary, lokal jadi cadangan | Postgres jadi DB utama sehari-hari | ❌ Ditolak — bertentangan dengan G3 |
| 4. SQLite replication via Litestream | Replikasi file SQLite ke object storage, cloud standby jalankan codebase sama tanpa DB abstraction | ❌ **Dibatalkan setelah dites** — Litestream juga binary Go yang didistribusikan lewat GitHub Releases, kena blokir yang sama |
| **5. WebSocket relay + DB abstraction Postgres** (dipilih) | Cloud standby app (Render/Fly.io) merangkap gateway + relay + standby. Laptop lokal jalankan client Python (`websockets`, pip) yang connect keluar terus-menerus ke cloud app. Selama koneksi hidup, request diteruskan ke lokal; kalau putus, cloud app layani sendiri dari Postgres | ✅ **Dipilih** — semua dependency di sisi lokal cuma `pip install`, tidak ada binary GitHub Releases |

### 4.1 Temuan: GitHub Releases Diblokir

Dites langsung dari laptop yang menjalankan FinanceHub (2026-07-07):
- Browsing umum normal (google.com, github.com halaman utama, cloudflare.com, litestream.io — semua OK)
- Download binary dari **GitHub Releases gagal** — baik lewat PowerShell (`Invoke-WebRequest` ke `cloudflared-windows-amd64.exe` → SSL error) maupun lewat browser sungguhan (halaman release GitHub, bagian "Assets" gagal load: "Uh oh, there was an error while loading")
- Download dari CDN lain (Microsoft Sysinternals, 5MB) **berhasil normal**
- Kesimpulan: bukan soal admin/installer, tapi **jaringan kantor memblokir domain/infrastruktur GitHub Releases secara spesifik** — memengaruhi semua tool yang didistribusikan lewat sana (`cloudflared`, `Litestream`, kemungkinan juga `ngrok`, `wrangler` versi tertentu, dll)
- PyPI (`pypi.org`) **terverifikasi bisa diakses** — jadi `pip install --user <package>` tetap jadi jalur yang aman dipakai

---

## 5. Arsitektur

```
                          Internet / LAN
                                │
                                ▼
                 ┌───────────────────────────────┐
                 │  Cloud App (Render/Fly.io)     │   ← SATU URL publik tetap
                 │  Flask + Postgres (Supabase)   │      (mis. financehub.onrender.com)
                 │  + WebSocket relay endpoint     │
                 └───────────────┬────────────────┘
                                  │
                    Ada koneksi relay aktif dari lokal?
                    ┌─────────────┴─────────────┐
                   YA (lokal sehat)          TIDAK (lokal mati)
                    │                             │
                    ▼                             ▼
     ┌─────────────────────────┐    ┌─────────────────────────┐
     │ Teruskan request lewat   │    │ Layani sendiri dari      │
     │ WebSocket ke lokal,      │    │ Supabase Postgres        │
     │ tunggu respons, kirim    │    │ (writable saat darurat)  │
     │ balik ke user            │    └─────────────────────────┘
     └─────────────┬─────────────┘
                    ▼
     ┌───────────────────────────────┐
     │  Laptop Lokal (LAN)            │
     │  Flask + waitress (SQLite)     │──push sync tiap ~5 menit──▶ Supabase Postgres
     │  + relay client (Python,       │◀──catch-up sync saat boot──│ (untuk kesegaran data +
     │    `websockets`, pip-only)     │                             │  reporting)
     └───────────────────────────────┘
```

**Prinsip inti:** lokal = source of truth pada kondisi normal. Cloud hanya writable saat lokal down (mutually exclusive, bukan multi-master). Gateway, relay, dan standby app jadi **satu deployable** (cloud app di Render/Fly.io). Status "lokal sehat atau tidak" dideteksi langsung dari ada/tidaknya koneksi WebSocket — instan saat koneksi putus, bukan menunggu siklus polling.

---

## 6. Komponen

| Komponen | Fungsi | Cara pasang | Biaya |
|---|---|---|---|
| Cloud app (Render/Fly.io) | Flask app tunggal: terima traffic publik, jadi relay ke lokal, jadi standby Postgres | Deploy dari git (tidak ada instalasi lokal) | Gratis (cold-start ~30–50 detik kalau sleep) |
| WebSocket relay endpoint (di cloud app) | Terima koneksi persisten dari lokal, teruskan request/response | `pip install flask-sock` di cloud app | Gratis |
| WebSocket relay client (di lokal) | Buka & jaga koneksi outbound ke cloud app, eksekusi request yang diteruskan ke Flask lokal | `pip install --user websockets` | Gratis |
| DB abstraction layer | Supaya business logic yang sama jalan di SQLite (lokal) maupun Postgres (cloud) | `pip install --user psycopg2-binary sqlalchemy` (opsional, tergantung pendekatan) | Gratis |
| Sync job (dibangun dari nol) | SQLite → Supabase, tiap ~5 menit untuk tabel prioritas | Python murni | Gratis |
| Reverse catch-up sync (baru) | Supabase → SQLite, jalan sekali saat lokal boot, sebelum relay client connect | Python murni | Gratis |
| Tabel `central.failover_log` (baru) | Catat kapan cloud mulai/berhenti writable — acuan window reverse sync | 1 tabel baru di Supabase | Gratis |
| Override toggle (baru) | Set mode `auto`/`force_local`/`force_cloud` manual kalau salah deteksi | Endpoint admin di cloud app + kolom di Postgres | Gratis |
| Email notification (baru) | Kirim email tiap kali status relay berubah | `pip install --user requests`, panggil API Resend/Mailgun dari cloud app | Gratis (100 email/hari) |

### 6.1 WebSocket Relay — Logic

**Sisi cloud app (Flask, pakai `flask-sock`):**

```python
# pseudocode — cloud app
active_relay_socket = None   # hanya ada 1 laptop lokal, jadi 1 slot cukup

@sock.route("/relay")
def relay_endpoint(ws):
    global active_relay_socket
    if not verify_relay_token(ws):        # cek shared secret dulu, lihat §11
        ws.close()
        return
    active_relay_socket = ws
    send_email_notification("lokal terhubung (recovered)")
    try:
        while True:
            ws.receive()                  # jaga koneksi hidup, keepalive ping/pong
    finally:
        active_relay_socket = None
        send_email_notification("lokal terputus, switch ke cloud standby")

@app.route("/<path:path>", methods=["GET", "POST", ...])
def catch_all(path):
    override = get_override_mode()        # dari Postgres, default "auto"
    use_local = (override == "force_local") or (override == "auto" and active_relay_socket is not None)
    if use_local:
        return forward_via_relay(active_relay_socket, request)   # kirim request, tunggu respons
    else:
        return handle_with_postgres(request)                     # logic Flask biasa, DB=Postgres
```

**Sisi lokal (Python murni, `websockets`):**

```python
# pseudocode — relay client di laptop lokal
import asyncio, websockets, requests

async def maintain_relay():
    while True:
        try:
            async with websockets.connect(
                "wss://<cloud-app>/relay",
                extra_headers={"Authorization": f"Bearer {RELAY_TOKEN}"}
            ) as ws:
                async for message in ws:
                    req = parse_forwarded_request(message)
                    resp = requests.request(
                        req.method, f"http://localhost:8081{req.path}",
                        headers=req.headers, data=req.body
                    )
                    await ws.send(serialize_response(resp))
        except Exception:
            await asyncio.sleep(5)   # reconnect otomatis kalau putus (wifi blip, dsb)
```

Local server memanggil `http://localhost:8081` — **loopback, bukan network eksternal** — jadi tidak butuh port terbuka ke internet sama sekali.

### 6.2 Endpoint `/health` (Lokal, internal)

Dipakai relay client sebelum connect ke cloud, BUKAN dipoll dari luar lagi:
- Relay client cek `http://localhost:8081/health` sendiri sebelum membuka koneksi WebSocket
- Kalau lokal masih `starting` (proses catch-up sync belum selesai), relay client menunda connect

### 6.3 Manual Override & Notifikasi

- **Override:** admin endpoint `/admin/override` di cloud app (token terpisah dari relay token), tersimpan di tabel Postgres `central.override_state`.
- **Notifikasi email:** dikirim langsung dari cloud app di handler connect/disconnect WebSocket.

---

## 7. Data Flow

### 7.1 Operasi Normal
1. Laptop lokal boot, `run_production.py` start Flask + jalankan `migrate_db()` seperti biasa
2. Relay client cek `/health` lokal → `ready` → buka koneksi WebSocket ke cloud app
3. Cloud app terima koneksi, simpan sebagai `active_relay_socket`, kirim notifikasi "lokal terhubung"
4. User (LAN maupun luar LAN) selalu akses satu URL cloud app → diteruskan lewat relay ke lokal → baca/tulis ke SQLite
5. APScheduler lokal push perubahan ke Supabase Postgres tiap ~5 menit (tabel prioritas)

### 7.2 Failover Terjadi
1. Laptop lokal mati/sleep/wifi putus → koneksi WebSocket terputus (deteksi instan)
2. Cloud app: `active_relay_socket = None`, kirim notifikasi "lokal terputus"
3. Request berikutnya dilayani cloud app sendiri, baca/tulis langsung ke Supabase Postgres
4. `central.failover_log`: insert row `{started_at: now, status: 'active'}`

### 7.3 Recovery / Reconciliation
1. Laptop lokal nyala lagi, status awal = `starting`
2. Startup hook: reverse sync pull rows Postgres sejak failover mulai → upsert ke SQLite by id
3. Selesai tanpa error → status jadi `ready`, `failover_log` update `resolved`
4. Relay client BARU connect sekarang — setelah reverse sync selesai

---

## 8. Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | Cloud app HARUS meneruskan request ke lokal via relay ketika koneksi aktif dan mode `auto`/`force_local` |
| FR2 | Cloud app HARUS melayani sendiri dari Postgres ketika relay terputus dan mode `auto`/`force_cloud` |
| FR3 | Relay client HARUS mengecek `/health` lokal = `ready` sebelum membuka koneksi |
| FR4 | Cloud app HARUS bisa menjalankan business logic yang sama dengan `DB_BACKEND=postgres` |
| FR5 | Reverse catch-up sync HARUS selesai sebelum relay client connect kembali |
| FR6 | `password_hash` HARUS ikut disync ke Supabase supaya login tetap jalan di cloud standby |
| FR7 | Tabel-tabel modul Budget HARUS ditambahkan ke scope sync |
| FR8 | Semua upsert HARUS idempotent by `id` |
| FR9 | Sync tabel prioritas HARUS berjalan tiap ~5 menit |
| FR10 | Endpoint `/admin/override` HARUS mengecek token admin, diprioritaskan di atas status koneksi relay |
| FR11 | Cloud app HARUS mengirim notifikasi email persis saat event connect/disconnect |
| FR12 | Endpoint `/relay` HARUS menolak koneksi WebSocket tanpa token relay yang valid |
| FR13 | Semua dependency di sisi laptop lokal HARUS terpasang lewat `pip install --user` |

## 9. Non-Functional Requirements

- **Biaya:** $0/bulan tambahan
- **Availability target:** downtime maksimal beberapa puluh detik saat transisi
- **Konsistensi data:** tidak ada duplikat/ID collision setelah reconciliation
- **Keamanan:** Supabase service key & relay token tidak boleh ter-expose di source
- **Portabilitas:** semua tooling lokal harus tetap berfungsi di laptop non-admin dengan jaringan restriktif

---

## 10. Perubahan Kode yang Dibutuhkan

| Perubahan | Estimasi Effort | Catatan |
|---|---|---|
| DB abstraction layer (SQLite ↔ Postgres) | **Tinggi** | ~5.000 baris raw SQL SQLite-spesifik di 6 module service + migration script 1.200 baris di `database.py` |
| WebSocket relay server (cloud app) | Sedang | `flask-sock`, endpoint `/relay` + `catch_all` forwarding |
| WebSocket relay client (lokal) | Sedang | `websockets`, reconnect loop |
| Endpoint `/health` 3-status | Rendah | Route baru + flag in-memory/file |
| Reverse sync script | Sedang | Kebalikan dari sync yang sudah dibangun di Fase 1 |
| Tabel `central.failover_log` + `central.override_state` | Rendah | 2 tabel baru |
| Deploy cloud app | Sedang | Render/Fly.io, tanpa instalasi lokal |
| Endpoint `/admin/override` | Rendah | Route + token check |
| Integrasi email notification | Rendah | Saat connect/disconnect |

---

## 11. Keamanan

- **Relay token wajib** — endpoint `/relay` HARUS menolak koneksi tanpa token valid.
- **`password_hash` disync** — tetap dalam bentuk hash.
- **Koneksi outbound-only dari lokal** — tidak ada port terbuka ke internet.
- **Supabase service role key & relay token** disimpan sebagai environment secret.
- **Admin override token** terpisah dari relay token.
- **JWT/session saat failover:** login ulang saat pindah ke cloud standby.

---

## 12. Testing & Validation Plan

1. Matikan `run_production.py` lokal → verifikasi traffic pindah ke cloud standby dalam hitungan detik
2. Input data di cloud saat lokal "mati" → nyalakan lokal → verifikasi reverse sync tanpa duplikat
3. Simulasi wifi blip sesaat → verifikasi reconnect loop otomatis
4. Connect ke `/relay` tanpa token benar → verifikasi ditolak
5. Load test ringan cloud standby
6. Ukur delay cold-start Render/Fly.io
7. Verifikasi semua dependency lokal terpasang bersih lewat `pip install --user` tanpa admin

---

## 13. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Cold-start cloud standby | Delay ~30–50s saat failover pertama | Diterima sebagai trade-off free tier |
| Relay putus-nyambung berulang | Traffic "lompat-lompat" | Grace period 2–3 detik sebelum menandai down |
| Relay token bocor | Orang lain bisa menyamar jadi lokal | Token sebagai secret, rotate kalau bocor |
| DB abstraction tidak lengkap | Bug halus di cloud standby | Testing menyeluruh, terutama transaksi atomic PA→PAM |
| Cloud app jadi single point of failure baru | Render/Fly.io down → semua akses ikut down | Diterima — trade-off "satu URL publik tetap" |

---

## 14. Rollout Plan

| Fase | Isi |
|---|---|
| Fase 1 | **Bangun sync SQLite → Supabase dari nol**: skema Postgres, sync script incremental + insert-only per tabel, termasuk tabel Budget dan `password_hash`, interval 5 menit |
| Fase 2 | Bangun DB abstraction layer + deploy cloud app ke Render/Fly.io dengan `DB_BACKEND=postgres`, test manual (tanpa relay dulu) |
| Fase 3 | Bangun reverse catch-up sync + tabel `failover_log` + `override_state` |
| Fase 4 | Bangun WebSocket relay server (cloud) + client (lokal), termasuk token auth |
| Fase 5 | Bangun endpoint `/admin/override` + integrasi email notification |
| Fase 6 | End-to-end failover drill |

---

## 15. Success Criteria

- [ ] Mematikan server lokal → user tetap bisa akses & submit data via cloud standby dalam ≤60 detik
- [ ] Menyalakan lokal kembali → semua data selama outage muncul di SQLite tanpa duplikat
- [ ] Tidak ada biaya bulanan baru
- [ ] Modul Budget ikut tersedia di cloud standby
- [ ] Login tetap berfungsi di cloud standby
- [ ] Semua setup lokal berhasil tanpa admin rights dan tanpa download binary dari luar PyPI

---

## Referensi
- Dokumen ini juga tersimpan di vault Obsidian Harry: `02 - Area/Kerjaan Kantor` (untuk cross-reference dengan catatan proyek FinanceHub lainnya)
- Desain LAN access existing: mDNS `financehub.local` (`run_production.py`)
- Desain sync Supabase awal (2026-06-24) — didesain tapi belum diimplementasikan, jadi basis Fase 1 di atas

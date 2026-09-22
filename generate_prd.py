import sys

html_content = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dokumen Teknis & Produk - Financehub (FLOW)</title>
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Mermaid JS -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad:true, theme: 'dark'});</script>
    
    <style>
        :root {
            --void-navy: #06080F;
            --panel-ink: #0F1220;
            --deep-slate: #161927;
            --bone-white: #F0EEF8;
            --muted-periwinkle: #9896B0;
            --whisper-ink: #4E4D63;
            --accent: #4F6AFF;
            --coral: #FF5757;
            --success: #10B981;
        }
        
        body {
            background-color: var(--void-navy);
            color: var(--bone-white);
            font-family: 'Figtree', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            background-color: var(--panel-ink);
            padding: 60px 80px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.05);
        }

        .doc-header {
            margin-bottom: 50px;
        }

        .doc-eyebrow {
            font-family: 'DM Mono', monospace;
            color: var(--accent);
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.1em;
            margin-bottom: 15px;
        }

        h1 {
            font-size: 3rem;
            font-weight: 800;
            margin: 0 0 10px 0;
            letter-spacing: -0.03em;
            color: var(--bone-white);
        }
        
        .doc-subtitle {
            font-size: 1.4rem;
            color: var(--muted-periwinkle);
            margin-top: 0;
            margin-bottom: 30px;
        }

        .meta-header {
            font-family: 'DM Mono', monospace;
            color: var(--whisper-ink);
            font-size: 0.95rem;
            padding-top: 20px;
            border-top: 2px solid var(--deep-slate);
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }

        .meta-header div span {
            display: block;
            color: var(--bone-white);
            font-family: 'Figtree', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            margin-top: 5px;
        }

        h2 {
            font-size: 1.8rem;
            color: var(--bone-white);
            border-bottom: 2px solid var(--deep-slate);
            padding-bottom: 10px;
            margin-top: 3em;
            display: flex;
            align-items: baseline;
            gap: 15px;
        }
        
        h2 .chapter-num {
            color: var(--whisper-ink);
            font-family: 'DM Mono', monospace;
        }

        h3 {
            font-size: 1.3rem;
            color: var(--accent);
            margin-top: 2em;
        }

        p, ul, ol {
            color: var(--muted-periwinkle);
            font-size: 1.05rem;
        }

        .role-card {
            border: 1px solid var(--deep-slate);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 20px;
            background: rgba(22, 25, 39, 0.3);
        }
        
        .role-title {
            font-weight: 800;
            color: var(--bone-white);
            font-size: 1.2rem;
            margin-bottom: 5px;
        }
        
        .role-tag {
            font-size: 0.75rem;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'DM Mono', monospace;
        }
        
        .tag-green { background: rgba(16,185,129,0.1); color: var(--success); }
        .tag-orange { background: rgba(245,158,11,0.1); color: #F59E0B; }
        .tag-red { background: rgba(255,87,87,0.1); color: var(--coral); }

        .role-details {
            border-left: 1px solid var(--deep-slate);
            padding-left: 20px;
        }

        .detail-row {
            display: grid;
            grid-template-columns: 100px 1fr;
            margin-bottom: 10px;
            font-size: 0.95rem;
        }
        
        .detail-row span:first-child {
            color: var(--whisper-ink);
        }
        .detail-row span:last-child {
            color: var(--bone-white);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.95rem;
            background: rgba(22, 25, 39, 0.3);
            border-radius: 8px;
            overflow: hidden;
        }

        th, td {
            padding: 14px 18px;
            text-align: left;
            border-bottom: 1px solid var(--deep-slate);
        }

        th {
            background-color: var(--deep-slate);
            color: var(--whisper-ink);
            font-weight: 500;
            font-family: 'DM Mono', monospace;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.05em;
        }

        td {
            color: var(--muted-periwinkle);
        }
        
        td strong {
            color: var(--bone-white);
            font-family: 'DM Mono', monospace;
            background: var(--deep-slate);
            padding: 2px 6px;
            border-radius: 4px;
        }

        .check-yes { color: var(--success); font-weight: bold; }
        .check-no { color: var(--whisper-ink); }

        pre {
            background-color: var(--deep-slate);
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid rgba(255,255,255,0.05);
            font-family: 'DM Mono', monospace;
            font-size: 0.9rem;
            color: #c9c7e8;
        }

        .mermaid {
            background-color: var(--deep-slate);
            padding: 30px;
            border-radius: 12px;
            margin: 30px 0;
            display: flex;
            justify-content: center;
        }

        .tree-view {
            font-family: 'DM Mono', monospace;
            background: var(--deep-slate);
            padding: 20px;
            border-radius: 8px;
            font-size: 0.9rem;
            color: #a5b4fc;
            line-height: 1.8;
            white-space: pre;
            overflow-x: auto;
        }
    </style>
</head>
<body>

<div class="container">
    <div class="doc-header">
        <div class="doc-eyebrow">DOKUMENTASI RESMI · 2026</div>
        <h1>Dokumen Teknis<br>&amp; Produk</h1>
        <p class="doc-subtitle">Product Requirements Document (PRD)</p>
        
        <div style="margin-top: 40px; color: var(--bone-white); font-weight: 600;">
            Financehub (FLOW) - Financial Ledger & Operational Workspace
        </div>
        <p style="margin-top: 10px; max-width: 700px;">
            Sistem manajemen pengajuan pembayaran, realisasi anggaran, dan dashboard operasional tersentralisasi — dibangun di atas Python (Flask), SQLite, dan Vanilla HTML/JS.
        </p>

        <div class="meta-header">
            <div>VERSI <span>2.0</span></div>
            <div>TANGGAL <span>2026-09-09</span></div>
            <div>STATUS <span style="color: #F59E0B; border: 1px solid #F59E0B; padding: 2px 8px; border-radius: 12px; display: inline-block;">Final Draft</span></div>
            <div>PLATFORM <span>Python + SQLite</span></div>
        </div>
    </div>

    <!-- BUSINESS LAYER -->
    <div class="doc-eyebrow" style="margin-top: 80px; border-bottom: 1px solid var(--deep-slate); padding-bottom: 10px;">BUSINESS LAYER — NON-TECHNICAL READERS</div>
    
    <h2><span class="chapter-num">1</span> Executive Summary / Ringkasan Eksekutif</h2>
    <p><strong>Financehub (FLOW)</strong> adalah sistem manajemen keuangan berbasis web yang dibangun untuk menggantikan proses manual (kertas/email/excel) di Sinar Mas Tjipta (SMT) dan Eka Tjipta Foundation (ETF). Sistem ini menghadirkan alur persetujuan digital (*approval workflow*) yang terstruktur, terekam, dan dapat diaudit secara real-time.</p>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 30px 0;">
        <div class="role-card" style="display: block;">
            <div class="doc-eyebrow" style="margin-bottom: 5px;">PLATFORM</div>
            <div style="color: var(--bone-white); font-weight: 600;">Python Flask Web App</div>
        </div>
        <div class="role-card" style="display: block;">
            <div class="doc-eyebrow" style="margin-bottom: 5px;">DATABASE</div>
            <div style="color: var(--bone-white); font-weight: 600;">SQLite (finance_hub.db)</div>
        </div>
        <div class="role-card" style="display: block;">
            <div class="doc-eyebrow" style="margin-bottom: 5px;">FRONTEND</div>
            <div style="color: var(--bone-white); font-weight: 600;">HTML Service Templates (Vanilla)</div>
        </div>
        <div class="role-card" style="display: block;">
            <div class="doc-eyebrow" style="margin-bottom: 5px;">USER ROLES</div>
            <div style="color: var(--bone-white); font-weight: 600;">Requester, Verificator, Releaser, Admin</div>
        </div>
    </div>

    <h2><span class="chapter-num">2</span> Problem Statement / Latar Belakang & Tujuan</h2>
    <h3>2.1 Masalah Sebelumnya</h3>
    <ul>
        <li>Formulir dan pencatatan excel yang beredar antar departemen tanpa tracking status tersentralisasi.</li>
        <li>Tidak ada visibilitas real-time sisa anggaran (*budget*) sebelum mengajukan *Payment Memo*.</li>
        <li>Tidak ada audit trail yang dapat ditelusuri per dokumen.</li>
        <li>Data tersebar — tidak ada satu sumber kebenaran (*single source of truth*) untuk SMT & ETF.</li>
    </ul>

    <h3>2.2 Solusi & Tujuan Sistem</h3>
    <ol>
        <li><strong>Portal Terpusat</strong> — Pengajuan (Memo, Beasiswa) terpusat, tersimpan di database lokal.</li>
        <li><strong>Alur Persetujuan Bertingkat</strong> — Otomatisasi status dokumen (Draft → In_Review → Approved).</li>
        <li><strong>Validasi Budget</strong> — Pengecekan otomatis batas *budget* vs *realisasi*.</li>
        <li><strong>Dashboard Analitik (Premium UI)</strong> — Visualisasi Chart.js untuk tingkat eksekutif.</li>
        <li><strong>Native Backup</strong> — Fitur admin untuk mencadangkan database secara langsung.</li>
    </ol>

    <h2><span class="chapter-num">3</span> Role Profiles / Profil Pengguna</h2>
    <p>Sistem memiliki 4 *logical roles*. Pengguna dapat memegang akses operasional maupun administratif berdasarkan role di JWT.</p>

    <div class="role-card">
        <div>
            <div class="role-title">Requester</div>
            <span class="role-tag tag-green">Multi-role OK</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Siapa</span><span>Staf operasional / pembuat pengajuan</span></div>
            <div class="detail-row"><span>Scope</span><span>Data spesifik *company* (SMT atau ETF)</span></div>
            <div class="detail-row"><span>Aksi</span><span>Create Payment Memo, Input data Sponsorship</span></div>
        </div>
    </div>
    
    <div class="role-card">
        <div>
            <div class="role-title">Verificator</div>
            <span class="role-tag tag-green">Multi-role OK</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Siapa</span><span>Tim Keuangan / Controller</span></div>
            <div class="detail-row"><span>Scope</span><span>Semua dokumen di dalam *company* aktif</span></div>
            <div class="detail-row"><span>Aksi</span><span>Validasi Payment Memo, edit GL Account, Review</span></div>
        </div>
    </div>

    <div class="role-card">
        <div>
            <div class="role-title">Releaser</div>
            <span class="role-tag tag-orange">Eksekutif</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Siapa</span><span>Pimpinan / Pengambil keputusan akhir</span></div>
            <div class="detail-row"><span>Scope</span><span>Global (terbatas per *company*)</span></div>
            <div class="detail-row"><span>Aksi</span><span>Akses penuh Dashboard Analitik (Sahabat ETF), Approve Memo</span></div>
        </div>
    </div>

    <div class="role-card">
        <div>
            <div class="role-title">Admin</div>
            <span class="role-tag tag-red">Standalone</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Siapa</span><span>Administrator Sistem (IT)</span></div>
            <div class="detail-row"><span>Scope</span><span>Sistem Global (tanpa batasan *company*)</span></div>
            <div class="detail-row"><span>Aksi</span><span>Manajemen User, Backup Database, Audit Logs</span></div>
        </div>
    </div>

    <h2><span class="chapter-num">4</span> User Journey Flows / Alur Pengguna</h2>
    <h3>4.1 Alur Umum (Semua Role)</h3>
    <div class="tree-view">[Buka URL Lokal :8080]
  |
  ▼
[Login] --- gagal? ---> (Tolak akses, show toast)
  |
  ▼   (Login berhasil - JWT session dibuat di Cookie)
[Dashboard Hub]
  ├─ Tampilan Menu Cards dinamis (Carousel)
  └─ Pilih Modul Tujuan (Misal: Sahabat ETF, Beasiswa, Payment Memo)
       |
       ├─ [Modul Pengajuan / Input Data]
       ├─ [Modul Dashboard Analitik / Report]
       └─ [Modul Settings / Admin]</div>

    <h3>4.2 Alur Requester (Payment Memo)</h3>
    <div class="tree-view">Dashboard → Payment Memo → [Create Baru]
  → Isi form (Vendor, Amount, Keterangan)
  → Submit 
      → [Status: OPEN]
      → Dokumen terkirim ke antrean Verificator
  → Pantau status di Riwayat Memo</div>

    <h2><span class="chapter-num">5</span> Document Lifecycle / Alur Dokumen</h2>
    <div class="mermaid">
    stateDiagram-v2
        [*] --> Draft : Staf membuat Payment Memo
        Draft --> Open : Submit ke Sistem
        Open --> In_Review : Menunggu Validasi Verificator
        In_Review --> Approved : Releaser Menyetujui
        Approved --> Closed : Pembayaran / Realisasi Selesai
        In_Review --> Rejected : Ditolak / Overbudget
        Rejected --> [*]
        Closed --> [*]
    </div>


    <!-- TECHNICAL LAYER -->
    <div class="doc-eyebrow" style="margin-top: 100px; border-bottom: 1px solid var(--deep-slate); padding-bottom: 10px;">TECHNICAL LAYER — DEVELOPERS & MAINTAINERS</div>

    <h2><span class="chapter-num">6</span> System Architecture / Arsitektur Sistem</h2>
    <h3>6.1 Tech Stack</h3>
    <table>
        <thead><tr><th>Layer</th><th>Teknologi</th></tr></thead>
        <tbody>
            <tr><td>Backend</td><td>Python 3.9+ (Runtime), Flask (Web Framework), Waitress (WSGI Server)</td></tr>
            <tr><td>Frontend</td><td>Jinja2 HTML Templates, Vanilla CSS/JS, Chart.js, Tailwind-like utility classes</td></tr>
            <tr><td>Database</td><td>SQLite 3 (Multi-table relational schema di `finance_hub.db`)</td></tr>
            <tr><td>File Storage</td><td>Sistem File Lokal (untuk modul Native Backup)</td></tr>
            <tr><td>Auth</td><td>Flask-JWT-Extended (Session berbasis Cookie & Authorization Headers)</td></tr>
            <tr><td>Job Scheduler</td><td>APScheduler (Cron jobs internal)</td></tr>
        </tbody>
    </table>

    <h3>6.2 Arsitektur High-Level</h3>
    <div class="tree-view">┌────────────────────────────────────────────────────────┐
│ BROWSER (User Client LAN)                              │
│ HTML + CSS + JS (vanilla)                              │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTPS/HTTP requests
                           ▼
┌────────────────────────────────────────────────────────┐
│ PYTHON / WAITRESS SERVER (Port 8080)                   │
│                                                        │
│  app.py            — routing utama & blueprint regist  │
│  auth/routes.py    — auth login & set JWT cookies      │
│  middleware.py     — validasi JWT session per endpoint │
│  modules/*/routes  — controller per modul (API/HTML)   │
│  services.py       — abstraksi query SQLite            │
│                                                        │
│          ┌──────────────────────────────────┐          │
│          ▼                                  ▼          │
│  [ sqlite3 (finance_hub.db) ]     [ Local File I/O ]   │
└────────────────────────────────────────────────────────┘</div>

    <h2><span class="chapter-num">7</span> Data Architecture / Model Data</h2>
    <p>Database utama menggunakan <strong>SQLite</strong>. Berikut adalah spesifikasi tabel krusial dalam sistem (Referensi: <code>database.py</code>).</p>

    <h3>7.1 Tabel <code>users</code> & <code>refresh_tokens</code> (Otentikasi)</h3>
    <table>
        <thead><tr><th>Kolom</th><th>Tipe</th><th>Keterangan</th></tr></thead>
        <tbody>
            <tr><td><strong>id</strong></td><td>INTEGER</td><td>Primary key auto-increment</td></tr>
            <tr><td><strong>username</strong></td><td>TEXT</td><td>Unique identifier untuk login</td></tr>
            <tr><td><strong>password_hash</strong></td><td>TEXT</td><td>Password di-hash dengan bcrypt</td></tr>
            <tr><td><strong>role</strong></td><td>TEXT</td><td>Primary role (default 'requester', 'admin', 'releaser')</td></tr>
            <tr><td><strong>token_hash</strong></td><td>TEXT</td><td>(Di tabel refresh_tokens) Pelacak JWT untuk fitur logout</td></tr>
        </tbody>
    </table>

    <h3>7.2 Tabel <code>payment_beasiswa</code> (Transaksi Realisasi)</h3>
    <table>
        <thead><tr><th>Kolom</th><th>Tipe</th><th>Keterangan</th></tr></thead>
        <tbody>
            <tr><td><strong>id</strong></td><td>INTEGER</td><td>Primary key</td></tr>
            <tr><td><strong>siswa_code</strong></td><td>TEXT</td><td>Relasi ke tabel <code>siswa</code></td></tr>
            <tr><td><strong>amount</strong></td><td>REAL</td><td>Nominal realisasi</td></tr>
            <tr><td><strong>cat1, cat2, cat3</strong></td><td>TEXT</td><td>Kategori pengeluaran (misal: SPP, Uang Saku)</td></tr>
            <tr><td><strong>pillar</strong></td><td>TEXT</td><td>Pilar ETF (misal: SETF, AGRI)</td></tr>
            <tr><td><strong>status</strong></td><td>TEXT</td><td>Status transaksi ('open', 'closed')</td></tr>
        </tbody>
    </table>

    <h3>7.3 Tabel <code>payment_memo</code></h3>
    <table>
        <thead><tr><th>Kolom</th><th>Tipe</th><th>Keterangan</th></tr></thead>
        <tbody>
            <tr><td><strong>memo_number</strong></td><td>TEXT</td><td>Nomor dokumen unik</td></tr>
            <tr><td><strong>total_amount</strong></td><td>REAL</td><td>Akumulasi dari <code>payment_memo_items</code></td></tr>
            <tr><td><strong>status</strong></td><td>TEXT</td><td>'open', 'approved', 'rejected'</td></tr>
            <tr><td><strong>approved_by</strong></td><td>TEXT</td><td>Username yang melakukan aksi approval</td></tr>
        </tbody>
    </table>

    <h2><span class="chapter-num">8</span> Module Catalog / Katalog Modul</h2>
    <table>
        <thead><tr><th>Modul / Prefix URL</th><th>Tipe / Fungsi</th><th>Role yang Boleh Akses</th></tr></thead>
        <tbody>
            <tr><td><strong>/auth</strong></td><td><code>login()</code>, <code>logout()</code>, set Cookie JWT</td><td>Semua (pre/post-login)</td></tr>
            <tr><td><strong>/dashboard</strong></td><td>Hub navigasi dan <em>module switcher</em></td><td>Semua Terautentikasi</td></tr>
            <tr><td><strong>/sahabat-etf</strong></td><td>Dashboard Realisasi vs Budget (Grouped Stacked Bar Chart), Filter Pillar & Bulan</td><td>Releaser, Verificator, Requester (terbatas)</td></tr>
            <tr><td><strong>/beasiswa</strong></td><td>Manajemen Master Siswa, Laporan PDF (Page Break, Wrapping)</td><td>ETF Users</td></tr>
            <tr><td><strong>/payment-memo</strong></td><td>Pengajuan Memo Pembayaran, cetak dokumen PDF, routing vendor</td><td>Terautentikasi</td></tr>
            <tr><td><strong>/sponsorship</strong></td><td>Input data sponsorship SMT, tracking event</td><td>SMT Users</td></tr>
            <tr><td><strong>/backup</strong></td><td>Fitur Native Backup File Manager ke `D:\Backup`</td><td>Admin</td></tr>
            <tr><td><strong>/users</strong></td><td>Manajemen pengguna, ganti <em>role</em>, <em>revoke</em> sesi</td><td>Admin</td></tr>
        </tbody>
    </table>

    <h2><span class="chapter-num">9</span> Security & Access Control / Keamanan & Kontrol Akses</h2>
    <h3>9.1 Role-Access Matrix</h3>
    <table>
        <thead><tr><th>Modul / Aksi</th><th>REQ (Requester)</th><th>VER (Verificator)</th><th>REL (Releaser)</th><th>ADM (Admin)</th></tr></thead>
        <tbody>
            <tr><td>Login & Dashboard</td><td class="check-yes">✅</td><td class="check-yes">✅</td><td class="check-yes">✅</td><td class="check-yes">✅</td></tr>
            <tr><td>Input Payment Memo</td><td class="check-yes">✅</td><td class="check-yes">✅</td><td class="check-no">-</td><td class="check-yes">✅</td></tr>
            <tr><td>Validasi / Edit Memo</td><td class="check-no">-</td><td class="check-yes">✅</td><td class="check-yes">✅</td><td class="check-yes">✅</td></tr>
            <tr><td>Sahabat ETF Dashboard</td><td class="check-no">-</td><td class="check-yes">✅</td><td class="check-yes">✅</td><td class="check-yes">✅</td></tr>
            <tr><td>Backup Database</td><td class="check-no">-</td><td class="check-no">-</td><td class="check-no">-</td><td class="check-yes">✅</td></tr>
            <tr><td>User Management</td><td class="check-no">-</td><td class="check-no">-</td><td class="check-no">-</td><td class="check-yes">✅</td></tr>
        </tbody>
    </table>

    <h3>9.2 Session Object & Helper Functions</h3>
    <pre><code>// Data yang di-encode di dalam token JWT (auth/routes.py)
{
    "identity": "1",          // User ID
    "username": "admin",      // Username
    "role": "releaser",       // Akses kontrol
    "exp": 1735689600         // Expiry Time
}</code></pre>
    <p>Pengendalian rute di <code>middleware.py</code> menggunakan dekorator Python:</p>
    <ul>
        <li><code>@jwt_html_required</code>: Mengecek ketersediaan <em>cookie</em> JWT. Jika gagal → Redirect ke <code>/login</code>.</li>
        <li><code>@json_required</code>: Sama dengan di atas, namun mengembalikan status <code>401 JSON</code> untuk pemanggilan AJAX/API (menghindari error render HTML).</li>
        <li><code>@html_admin_required</code>: Mengevaluasi apakah <code>claims.get("role") == "admin"</code> atau <code>claims.get("username") == "admin"</code>. Jika tidak → Redirect ke Dashboard.</li>
    </ul>

    <h2><span class="chapter-num">10</span> Non-Functional Requirements / Batasan & Risiko</h2>
    <h3>10.1 Platform Constraints (Waitress & SQLite)</h3>
    <table>
        <thead><tr><th>Constraint</th><th>Detail</th></tr></thead>
        <tbody>
            <tr><td>Database Concurrency</td><td>Karena menggunakan SQLite, penguncian database (<em>database locking</em>) bisa terjadi pada <em>write</em> beruntun. Tidak direkomendasikan untuk transaksi e-commerce (aman untuk internal operasional perusahaan).</td></tr>
            <tr><td>File System Access</td><td>Fitur pencadangan modul Backup dibatasi ketat ke *path* <code>D:\Backup</code> melalui pengecekan <code>os.path.commonpath</code> untuk mencegah *Directory Traversal Attack*.</td></tr>
            <tr><td>Networking</td><td>Sistem didesain tanpa HTTPS bawaan karena ditujukan untuk LAN tertutup.</td></tr>
        </tbody>
    </table>

    <h3>10.2 Known Limitations</h3>
    <ul>
        <li>Belum ada integrasi dengan *Host-to-Host* API Perbankan untuk pencairan otomatis.</li>
        <li>Otorisasi belum memiliki fitur pendelegasian (*role delegation*) sementara (misalnya saat Releaser cuti).</li>
        <li>Tidak mendukung mode <em>offline</em> (berbeda dengan *Progressive Web App*).</li>
    </ul>

    <h3>10.3 Deployment Notes</h3>
    <table>
        <thead><tr><th>Item</th><th>Detail</th></tr></thead>
        <tbody>
            <tr><td>Environment</td><td>Windows Server (Bisa berjalan di laptop yang dicolok listrik konstan sesuai dokumentasi *Tips Laptop Server* di <code>README.md</code>).</td></tr>
            <tr><td>Start Command (Prod)</td><td><code>python run_production.py</code> (Menggunakan Waitress port 8080 dengan 4 threads).</td></tr>
            <tr><td>Requirements</td><td>Definisi library berada di <code>requirements.txt</code> (Flask, JWT-Extended, apscheduler, Waitress, bcrypt).</td></tr>
        </tbody>
    </table>

</div>

</body>
</html>
"""

    with open(r'C:\Financehub\PRD_Financehub.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Ultra-detailed PRD HTML generated successfully.")

if __name__ == '__main__':
    patch_html()

import sys

def patch_prd():
    filepath = r'C:\Financehub\PRD_Financehub.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start_tag = '<h2><span class="chapter-num">8</span> Module Catalog / Katalog Modul</h2>'
    end_tag = '<h2><span class="chapter-num">9</span> Security & Access Control'
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("Could not find markers.")
        return
        
    new_chapter_8 = """<h2><span class="chapter-num">8</span> Module Catalog / Katalog Modul</h2>
    <p>Sistem ini dirancang dengan pendekatan modular (Flask Blueprints) yang dipisahkan ke dalam folder <code>app/modules/</code>. Berikut adalah rincian fungsional dan teknis dari setiap modul operasional di dalam FLOW.</p>

    <div class="role-card">
        <div>
            <div class="role-title">8.1 Sahabat ETF</div>
            <span class="role-tag tag-orange">Eksekutif Dashboard</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Tujuan</span><span>Menyajikan analitik real-time perbandingan Budget vs Realisasi.</span></div>
            <div class="detail-row"><span>Fitur Utama</span><span>
                <ul>
                    <li>Grafik <em>Grouped-Stacked Bar</em> (Chart.js kustom).</li>
                    <li>Sistem Filter cerdas (Berdasarkan Bulan Cutoff dan Multi-select Pillar).</li>
                    <li><em>Smart Culling</em> (menyembunyikan label pada segmen bar yang terlalu kecil).</li>
                </ul>
            </span></div>
            <div class="detail-row"><span>Rute/File</span><span><code>/sahabat-etf</code> &mdash; <code>modules/sahabat_etf/routes.py</code></span></div>
        </div>
    </div>

    <div class="role-card">
        <div>
            <div class="role-title">8.2 Beasiswa</div>
            <span class="role-tag tag-green">Master Data</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Tujuan</span><span>Pusat manajemen profil siswa dan histori pencairan dana.</span></div>
            <div class="detail-row"><span>Fitur Utama</span><span>
                <ul>
                    <li>Tabel dinamis dengan pencarian dan filter status.</li>
                    <li>Cetak Laporan PDF per siswa (mendukung <em>Page Break</em> dan <em>Text Wrapping</em> tabel panjang).</li>
                    <li>Pencatatan perkembangan 10 Semester IPK siswa.</li>
                </ul>
            </span></div>
            <div class="detail-row"><span>Rute/File</span><span><code>/beasiswa</code> &mdash; <code>modules/beasiswa/routes.py</code></span></div>
        </div>
    </div>

    <div class="role-card">
        <div>
            <div class="role-title">8.3 Sponsorship</div>
            <span class="role-tag tag-green">Input Data</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Tujuan</span><span>Portal khusus SMT untuk merekam pengajuan dan realisasi acara (Sponsorship/CSR).</span></div>
            <div class="detail-row"><span>Fitur Utama</span><span>
                <ul>
                    <li>Formulir berdesain premium (<em>Glassmorphism UI</em>).</li>
                    <li>Sistem re-order (pengurutan kustom) untuk deskripsi lembaga/tujuan.</li>
                    <li>Tabel Full-bleed yang merespon bentang layar lebar.</li>
                </ul>
            </span></div>
            <div class="detail-row"><span>Rute/File</span><span><code>/sponsorship</code> &mdash; <code>modules/sponsorship/routes.py</code></span></div>
        </div>
    </div>

    <div class="role-card">
        <div>
            <div class="role-title">8.4 Payment Memo</div>
            <span class="role-tag tag-red">Core Transaksional</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Tujuan</span><span>Pusat pembuatan dokumen pengajuan dana (Memo) ke bendahara/manajemen.</span></div>
            <div class="detail-row"><span>Fitur Utama</span><span>
                <ul>
                    <li>Pembuatan <code>memo_number</code> terstandarisasi.</li>
                    <li><em>Persistent Bulk Selection</em> (memilih banyak baris pembayaran secara lintas-halaman).</li>
                    <li>Pencetakan PDF Memo dengan penempatan kolom vendor/rekening otomatis.</li>
                </ul>
            </span></div>
            <div class="detail-row"><span>Rute/File</span><span><code>/payment-memo</code> &mdash; <code>modules/payment_memo/routes.py</code></span></div>
        </div>
    </div>

    <div class="role-card">
        <div>
            <div class="role-title">8.5 Backup File Manager</div>
            <span class="role-tag tag-red">Administrator</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Tujuan</span><span>Fasilitas manajemen keamanan data mandiri.</span></div>
            <div class="detail-row"><span>Fitur Utama</span><span>
                <ul>
                    <li>Antarmuka Native UI untuk menggantikan penggunaan Windows Explorer eksternal.</li>
                    <li>Mencadangkan file <code>finance_hub.db</code> secara langsung ke <code>D:\\Backup</code>.</li>
                    <li>Validasi path ketat menggunakan <code>os.path.commonpath</code> untuk mencegah eksploitasi.</li>
                </ul>
            </span></div>
            <div class="detail-row"><span>Rute/File</span><span><code>/backup</code> &mdash; <code>modules/backup/routes.py</code></span></div>
        </div>
    </div>
    
    <div class="role-card">
        <div>
            <div class="role-title">8.6 Modul Lanjutan (Fase 2)</div>
            <span class="role-tag tag-orange">On-Progress</span>
        </div>
        <div class="role-details">
            <div class="detail-row"><span>Rincian</span><span>
                <ul>
                    <li><strong>Bank / Cash & Bank:</strong> Pencatatan mutasi harian dan rekonsiliasi.</li>
                    <li><strong>Account Payable / PAM:</strong> <em>Payment Approval Module</em> tersentralisasi.</li>
                    <li><strong>Petty Cash:</strong> Manajemen kas kecil dan <em>Advance</em>.</li>
                </ul>
            </span></div>
            <div class="detail-row"><span>Rute/File</span><span><code>/bank</code>, <code>/payment_application</code></span></div>
        </div>
    </div>

    """
    
    new_content = content[:start_idx] + new_chapter_8 + content[end_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patched Chapter 8 successfully!")

if __name__ == '__main__':
    patch_prd()

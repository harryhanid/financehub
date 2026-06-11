# Week 7 UNIQLO Analytics — Deliverable Plan

> **Status:** Semua analisis SELESAI. Plan ini hanya untuk menyusun dan submit deliverable.

**Goal:** Lengkapi semua deliverable Week 7 (Excel, screenshots, GPT log, 1-page write-up)

**Yang sudah ada:**
- ✅ Excel dengan risk_score: `UNIQLO_Week7_StepByStep.xlsx`
- ✅ 5 patterns dari data nyata
- ✅ Risk score formula (sudah dipahami)
- ✅ 3 what-if scenarios + angka
- ✅ 5 prompt templates UNIQLO: `Week7_UNIQLO_Prompt_Templates.txt`

**Yang belum ada (perlu diselesaikan):**
- [ ] Screenshot validasi formula
- [ ] GPT conversation log (5 prompt)
- [ ] 1-page write-up

---

## Task 1 — Buka dan Cek Excel File (5 menit)

- [ ] Buka `C:\Users\25010160\Downloads\UNIQLO_Week7_StepByStep.xlsx`
- [ ] Buka sheet **"Cara Baca Formula"** → baca dulu sebentar
- [ ] Pindah ke sheet **"Data + Risk Score"**
- [ ] Scroll ke kanan sampai kelihatan kolom **AD, AE, AF, AG, AH, AI**
  - AD = Langkah 1 (Jual Rugi?)
  - AE = Langkah 2 (Diskon Besar?)
  - AI = Total Risk Score (0–100, berwarna merah/kuning/hijau)
- [ ] Klik cell **AI2** → lihat formula bar → pastikan formula muncul (bukan error)

---

## Task 2 — Ambil Screenshot Validasi Formula (10 menit)

Screenshot ini dibutuhkan untuk deliverable.

**Screenshot A — Formula accuracy:**
- [ ] Klik header kolom AI → klik ikon filter → filter nilai **≥ 60**
- [ ] Lihat kolom AD — hampir semua baris = "YA (+40 poin)" → ini bukti HIGH risk = jual rugi
- [ ] **Screenshot seluruh layar** → simpan sebagai `screenshot_high_risk.png`
- [ ] Catat angkanya: dari total baris yang muncul, berapa persen kolom AD = "YA"?
  - Target: sekitar 97% → ini akurasi formula kamu

**Screenshot B — Formula di formula bar:**
- [ ] Clear filter, klik cell AI2
- [ ] **Screenshot** formula bar yang menampilkan formula lengkap + beberapa baris data
- [ ] Simpan sebagai `screenshot_formula.png`

**Screenshot C — Summary per risk level:**
- [ ] Buat PivotTable baru (Insert → PivotTable)
  - Rows: kolom AI dibagi bucket (bisa pakai Group: 0-29, 30-59, 60-100)
  - Values: COUNT of transaction_id, SUM of returned
- [ ] **Screenshot** pivot tersebut → simpan sebagai `screenshot_pivot.png`

---

## Task 3 — Jalankan 5 Prompt di ChatGPT/Claude (20 menit)

File prompt ada di: `C:\Users\25010160\Downloads\Week7_UNIQLO_Prompt_Templates.txt`

- [ ] Buka ChatGPT atau Claude baru (fresh conversation)
- [ ] **Copy-paste Prompt 1** (Pattern Discovery) → tunggu respons → **screenshot/copy hasilnya**
- [ ] **Copy-paste Prompt 2** (Risk Score Formula) → screenshot/copy hasilnya
- [ ] **Copy-paste Prompt 3** (Scenario A — Hapus SKU below-cost) → screenshot/copy hasilnya
- [ ] **Copy-paste Prompt 4** (Scenario B — Cap diskon 10%) → screenshot/copy hasilnya
- [ ] **Copy-paste Prompt 5** (Scenario C — Fix Medan) → screenshot/copy hasilnya
- [ ] Simpan semua respons di satu dokumen Word: `GPT_Conversation_Log.docx`

> **Tips:** Jika GPT kasih angka yang beda jauh dari expected, lihat bagian TROUBLESHOOTING
> di file prompt template. Tambahkan constraint seperti:
> "Base calculations on exactly 49,800 transactions over 5 years."

---

## Task 4 — Tulis 1-Page Write-Up (15 menit)

Buat dokumen Word/Google Doc baru. Isi dengan template berikut:

```
UNIQLO INDONESIA — WEEK 7 ANALYTICS SUMMARY
Team 2 – Group F4 | Emir · Harry · Leonardus · Syahra

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAGIAN 1: TOP 3 PATTERNS YANG DITEMUKAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pattern 1: SKU Below-Cost (cost_price > list_price)
→ 17.3% dari 49,800 transaksi (8,628 transaksi) melibatkan produk yang dijual
  di bawah harga modal. Ini menghasilkan kerugian unit senilai IDR 8.59 miliar
  selama 5 tahun — tanpa diskon sekalipun.

Pattern 2: Diskon 20%–30% Tanpa Dampak Volume
→ Diskon 20% menurunkan GP margin dari 90.2% menjadi 72.3%.
  Diskon 30% menurunkan GP margin menjadi 64.0%.
  Namun rata-rata unit per transaksi TETAP SAMA di semua level diskon (2.51 unit).
  Artinya diskon menghancurkan margin tanpa menaikkan penjualan.

Pattern 3: Toko Medan Center Underperform
→ Medan Center (728 m²) menghasilkan hanya IDR 29,178/m² — 4.2× lebih rendah
  dari Jakarta Flagship (IDR 123,266/m²). Selain itu, Medan memiliki return rate
  tertinggi (10.48%) dari semua toko.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAGIAN 2: CARA KERJA RISK FORMULA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Formula menghitung "Transaction Loss Risk Score" (0–100) per transaksi.
Setiap transaksi menjawab 5 pertanyaan, setiap jawaban "Ya" mendapat poin:

  +40 → Produk dijual di bawah harga modal (cost > price)
  +20 → Diskon 20% atau 30%
  +10 → Diskon 10%
  +15 → Dari toko Medan Center
  +15 → Kategori Accessories
  +10 → Bulan Februari/Mei/Agustus/Oktober (musim return tinggi)

Validasi: Transaksi dengan score ≥ 60 memiliki 97.2% adalah below-cost SKU
dan return rate 10.7% — membuktikan formula akurat mengidentifikasi risiko.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAGIAN 3: REKOMENDASI SKENARIO TERBAIK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Skenario yang Direkomendasikan: SCENARIO A — Hentikan Penjualan SKU Below-Cost

Alasan:
- Dampak langsung terbesar tanpa investasi tambahan
- Menghentikan IDR 1.72 miliar kerugian per tahun (IDR 8.59B dalam 5 tahun)
- Implementasi sederhana: tambah 1 validasi di sistem POS
  (blokir transaksi jika harga jual < harga modal)
- Break-even instan — setiap hari tanpa aturan ini = kerugian berlanjut

Perbandingan semua skenario:
  Scenario A (Hapus SKU below-cost):  IDR 1.72B/tahun,  biaya: Rp0
  Scenario B (Cap diskon 10%):        IDR 218 juta/tahun, biaya: Rp0
  Scenario C (Perbaiki toko Medan):   IDR 5.38B/tahun,   biaya: ada (investasi operasional)

Urutan implementasi yang disarankan:
1. Langsung: Scenario A (stop kerugian terjamin)
2. Bersamaan: Scenario B (kebijakan diskon)
3. Jangka menengah: Scenario C (butuh rencana operasional Medan)
```

- [ ] Simpan sebagai `Week7_WriteUp_Team2.docx`
- [ ] Tambahkan screenshots dari Task 2 ke dalam dokumen

---

## Task 5 — Final Checklist Sebelum Submit

Sesuai rubrik Week 7 (100 poin):

**Pattern Discovery (25 poin):**
- [ ] 5 pattern sudah ditulis dengan angka nyata dari data
- [ ] Cara verifikasi Excel disebutkan untuk setiap pattern

**Risk Formula (35 poin):**
- [ ] Formula Excel ditulis lengkap
- [ ] Screenshot formula di Excel (formula bar terlihat)
- [ ] Screenshot validasi: HIGH-risk group (score≥60) → 97.2% below-cost

**What-If Scenarios (30 poin):**
- [ ] 3 skenario diselesaikan via GPT conversation (log tersimpan)
- [ ] Angka realistic (dalam batas 49,800 transaksi / 5 tahun)
- [ ] Best scenario dipilih dan diberi justifikasi

**Documentation (10 poin):**
- [ ] 1-page write-up selesai
- [ ] Screenshots included

**File yang disubmit:**
- [ ] `UNIQLO_Week7_StepByStep.xlsx` (Excel dengan risk score)
- [ ] `GPT_Conversation_Log.docx` (5 prompt + respons)
- [ ] `Week7_WriteUp_Team2.docx` (1-page summary)
- [ ] 3 screenshots (formula, high-risk filter, pivot)

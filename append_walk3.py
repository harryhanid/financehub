with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/walkthrough.md", "r", encoding="utf-8") as f:
    text = f.read()

text += """
## Penambahan Tanggal Expired pada Budget
1. **Skema Database**: Kolom `tgl_expired` telah ditambahkan ke tabel `budget_beasiswa`.
2. **Formulir Input/Edit Budget**: Pada modul Data Siswa/Budget (saat menambah atau mengedit baris budget), kini telah tersedia field khusus untuk mengisi **Tanggal Expired** (opsional).
3. **Logika Kalkulasi Sisa Budget**: Kalkulasi plafon otomatis menyeleksi hanya _budget_ yang `tgl_expired`-nya kosong (tanpa masa berlaku) ATAU belum melewati tanggal hari ini. Plafon dari _budget_ yang kedaluwarsa tidak akan diikutsertakan lagi ke dalam pot perhitungan, sehingga "Sisa Budget" di menu Payment otomatis menyesuaikan.
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/walkthrough.md", "w", encoding="utf-8") as f:
    f.write(text)

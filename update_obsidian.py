file_path = "C:/Obsidian/01 - Proyek/FinanceHub/FinanceHub - Overview.md"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_log = """
### Per 2026-09-14 - Fix UI Sahabat ETF Dashboard
- Memulihkan file `sahabat_etf.js` yang sempat terhapus/revert (118MB bloat issue) dengan file *pristine* 28KB.
- Mengembalikan mapping API backend terbaru (`/api/breakdown`) yang mengembalikan data `budget` & `realisasi` untuk grafik *Budget vs Actual*.
- Mengembalikan *color mapping* agar sesuai dengan skema warna per-Kategori dan per-Pillar (AGRI hijau, APP biru, dsb).
- Menambahkan **Total Zone Plugin** (garis putus-putus untuk menyorot kolom "Total" dan sumbu Y sebelah kanan).
- Merapikan label bawah sumbu X (memberikan jarak `padding` pada sumbu X agar label Budget & Actual tidak dempet dengan teks pilar/kategori).
- Mengimplementasikan fitur **Export PDF (Virtual Layout Scaling)**: Chart kini di-resize secara *synchronous* ke 850x500px dan `devicePixelRatio = 3` *sebelum* di-snapshot menjadi gambar (base64) lalu dikembalikan ke ukuran normalnya. Hal ini membuat teks di dalam grafik sangat tajam dan proporsional untuk ditempel di laporan PPT.
"""

content = content.replace("### Progress Terbaru (per 2026-09-09)", "### Progress Terbaru (per 2026-09-09)\n" + new_log)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated Obsidian!")

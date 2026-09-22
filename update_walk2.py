with open('C:/Users/25010160/.gemini/antigravity/brain/22e62e0d-4278-4dda-8fc0-16742a75b1fd/walkthrough.md', 'r', encoding='utf-8') as f:
    c = f.read()

c += """

### Export Laporan PPT: Angka Berbeda dengan Layar Laporan

**Penyebab:**
Meskipun *filter* bulan dan pillar sudah terhubung, angka di dalam presentasi PPT sebelumnya tetap tidak "nyambung" karena *backend* (`report_pptx.py`) menggunakan rumus dan istilah kolom yang sama sekali berbeda dengan apa yang Anda lihat di layar:
- Di layar, Anda melihat **Plafon, Klaim, Dibayar, dan Saldo** (di mana Saldo memperhitungkan Perubahan Tambah/Kurang/PTA).
- Namun, di dalam file PPT, sistem mencetak kolom **Budget, Realisasi, On Progress, dan Sisa Budget**. 
- Permasalahan fatalnya adalah pada formula PPT: `Sisa Budget` dihitung secara paksa dari `Plafon - Klaim` yang mana sama sekali tidak mengikutsertakan nilai PTA yang Anda miliki, sehingga tidak akan pernah sama dengan `Saldo` yang ada di layar.

**Penyelesaian:**
- Saya telah membongkar modul *generator* PPT (`report_pptx.py`) dan menyeragamkan istilah serta rumusnya secara absolut dengan layar Laporan Anda.
- Kolom tabel PPT kini diubah menjadi **Plafon, Klaim, Dibayar, dan Saldo**.
- Angka yang ditampilkan kini secara 1:1 diambil dari kalkulator metrik sentral yang sama persis dengan tabel *Web* dan ekspor *Excel*. 
- Rekapitulasi di kotak ringkasan paling bawah (pada halaman tiap slide) juga telah diselaraskan bahasanya menjadi "Total Plafon", "Total Klaim", "Total Dibayar", dan "Total Saldo" menggunakan *logic* matematika yang sama dan valid.
"""

with open('C:/Users/25010160/.gemini/antigravity/brain/22e62e0d-4278-4dda-8fc0-16742a75b1fd/walkthrough.md', 'w', encoding='utf-8') as f:
    f.write(c)

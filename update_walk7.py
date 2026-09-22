with open('C:/Users/25010160/.gemini/antigravity/brain/22e62e0d-4278-4dda-8fc0-16742a75b1fd/walkthrough.md', 'r', encoding='utf-8') as f:
    c = f.read()

c += """

### Penyesuaian Kolom Tabel & Judul

Kesalahan sebelumnya terjadi karena injeksi kolom baru (*Budget* dan *Sisa*) hanya ditambahkan pada bagian isi tabel (`<tbody>`), namun sistem gagal memaksa pembaruan judul pada kepala tabel (`<thead>`) akibat penempatan kode yang keliru (hanya dieksekusi saat data kosong).

- Saya telah memindahkan logika injeksi *header* ke tingkat tertinggi eksekusi. Sekarang, setiap kali diagram dimuat, Javascript akan secara paksa mengganti seluruh kepala tabel menjadi urutan kolom yang benar: **Kategori/Pillar | Budget | Actual | Sisa**.
- Secara bersamaan, judul kartu pembungkus (*card*) tabel juga turut diperbarui menjadi **Budget vs Actual per Kategori (Tabel)** agar selaras dengan tabel lainnya.

"""

with open('C:/Users/25010160/.gemini/antigravity/brain/22e62e0d-4278-4dda-8fc0-16742a75b1fd/walkthrough.md', 'w', encoding='utf-8') as f:
    f.write(c)

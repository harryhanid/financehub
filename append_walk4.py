with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/walkthrough.md", "r", encoding="utf-8") as f:
    text = f.read()

text += """
## Fitur Safety Checking (Validasi Sisa Budget) di PAM
- Validasi baru telah ditambahkan ke _backend_ saat menyimpan Input PAM (`save_pa_payment` untuk pilar beasiswa reguler dan `save_klaim_payment` untuk klaim medis).
- Sistem akan menjumlahkan total tagihan per Kategori 1 untuk masing-masing siswa yang ada dalam 1 PAM, dan membandingkannya secara _real-time_ terhadap Sisa Budget siswa tersebut di database (dengan tetap menghormati Tanggal Expired).
- Jika ada satu saja siswa yang total tagihannya melampaui Sisa Budget aktifnya, seluruh dokumen PAM akan ditolak dan muncul pesan galat spesifik: *"Budget tidak cukup untuk [Siswa] (Kategori ...). Diminta: Rp ..., Sisa: Rp ..."*.
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/walkthrough.md", "w", encoding="utf-8") as f:
    f.write(text)

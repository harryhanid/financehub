with open('C:/Users/25010160/.gemini/antigravity/brain/22e62e0d-4278-4dda-8fc0-16742a75b1fd/walkthrough.md', 'r', encoding='utf-8') as f:
    c = f.read()

c += """

### Rombak Total Desain Grafik Tren (Tahunan)

Ini adalah perombakan *interface* yang paling masif! Grafik tren tahunan kini tidak lagi menggunakan tipe *stacked bar* generik, melainkan diramu ulang menggunakan konfigurasi kustom (*Custom Grouped-Stacked Bar*) tingkat tinggi:

1. **Penyelarasan Warna & Legenda**: Sebelumnya, warna grafik *Actual* dibedakan dengan meredupkan warnanya (-25%). Sekarang, warna untuk *Budget* maupun *Actual* dibuat 100% identik per kategori (mis. *Budget* Medical = ungu, *Actual* Medical = ungu). Legenda pun disederhanakan agar tidak menduplikasi daftar warna.
2. **Pengelompokan (Bgt vs Act)**: Untuk membedakan mana yang *Budget* dan *Actual*, saya memisahkan tumpukannya (*stack*) menjadi dua batang bersebelahan dalam setiap tahun. 
3. **Sub-Label X Dinamis**: Sama seperti grafik ringkasan, terdapat tulisan "Bgt" dan "Act" tepat di bawah sepasang batang di tiap-tiap tahun (termasuk pada tahun-tahun yang kosong sekalipun, labelnya akan menyesuaikan).
4. **Kolom TOTAL & Skala Kanan**: Bagian ujung kanan grafik kini dikhususkan untuk batang agregasi TOTAL, yang dibingkai kotak putus-putus abu-abu tebal dan dikalibrasi pembacaannya mengacu pada sumbu Y Sekunder di sebelah kanan (Skala Total).
5. **Data Label Cerdas**: Angka keterangan (mis. *4.546,2*) hanya akan dimunculkan satu kali di **puncak** tumpukan tertinggi grafik, bukan berjejal di setiap potongan warnanya! Ini persis dengan rancangan mahakarya yang ada pada draf Anda.

"""

with open('C:/Users/25010160/.gemini/antigravity/brain/22e62e0d-4278-4dda-8fc0-16742a75b1fd/walkthrough.md', 'w', encoding='utf-8') as f:
    f.write(c)

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/walkthrough.md", "r", encoding="utf-8") as f:
    text = f.read()

text += """
5. **Daftar PAM (Semua Tab)**:
   - Pada tabel list PAM di setiap tab pilar (AGRI, APP, LAND, EFIN, SETF), telah ditambahkan kolom **Klasifikasi**.
   - Kolom ini terletak persis sebelum kolom **Status**, yang akan secara langsung menginformasikan apakah sebuah PAM tersebut 'Normal' atau 'With Memo'.
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/walkthrough.md", "w", encoding="utf-8") as f:
    f.write(text)

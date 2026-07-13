import pandas as pd
import sqlite3

excel_path = r'C:\Users\25010160\Downloads\query_1-2026-07-07_50756 vendors 070726 dl.xlsx'
db_path = r'C:\Financehub\app\finance_hub.db'

print("Membaca file Excel...")
df = pd.read_excel(excel_path)
df = df.fillna('')  # Handle NaN values

print("Koneksi ke database...")
conn = sqlite3.connect(db_path)

# Pastikan kolom-kolom baru ada di tabel vendors
try:
    conn.execute("ALTER TABLE vendors ADD COLUMN Bank_Account_Name TEXT")
    conn.execute("ALTER TABLE vendors ADD COLUMN Bank_Name TEXT")
    conn.execute("ALTER TABLE vendors ADD COLUMN Bank_Account_Number TEXT")
    conn.execute("ALTER TABLE vendors ADD COLUMN Swift_Code TEXT")
except sqlite3.OperationalError:
    pass # Kolom sudah ada

print("Menghapus data vendors yang lama...")
conn.execute("DELETE FROM vendors")

print(f"Memasukkan {len(df)} data vendor baru...")
inserted = 0
for idx, row in df.iterrows():
    # Insert baris per baris
    try:
        conn.execute("""
            INSERT INTO vendors (id, name, pillar, cost_center, Bank_Account_Name, Bank_Name, Bank_Account_Number, Swift_Code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['id'],
            str(row['name']).strip(),
            str(row['pillar']).strip(),
            str(row['cost_center']).strip(),
            str(row['Bank_Account_Name']).strip(),
            str(row['Bank_Name']).strip(),
            str(row['Bank_Account_Number']).strip(),
            str(row['Swift_Code']).strip()
        ))
        inserted += 1
    except Exception as e:
        print(f"Error pada baris {idx}: {e}")

conn.commit()
conn.close()
print(f"Selesai! {inserted} data vendor berhasil dimasukkan.")

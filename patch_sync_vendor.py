import os
import re

service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

search_str = '''            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                conn.rollback()
                return {"ok": False, "pesan": f"Baris {idx}: Cat1 '{cat1}' tidak ditemukan di database."}
                
            cat2 = perusahaan["cat2"]
            cat3 = perusahaan["cat3"]'''

replace_str = '''            cat2_excel = row[6]
            cat3_excel = row[7]
            
            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                cat2 = (cat2_excel or "").strip()
                cat3 = (cat3_excel or "").strip()
                if not cat2 or not cat3:
                    conn.rollback()
                    return {"ok": False, "pesan": f"Baris {idx}: Cat1 '{cat1}' baru, namun Cat2 atau Cat3 kosong di Excel."}
                
                conn.execute(
                    "INSERT INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?)",
                    (cat1, cat2, cat3)
                )
            else:
                cat2 = perusahaan["cat2"]
                cat3 = perusahaan["cat3"]'''

if search_str in service_content:
    service_content = service_content.replace(search_str, replace_str)
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    print("service.py patched successfully.")
else:
    print("Search string not found in service.py!")

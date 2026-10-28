import os

service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

search_str = '''            # Abaikan baris yang kosong atau tidak valid
            if not cat1 or not tgl_form or not lembaga:
                continue'''

replace_str = '''            # Validasi kolom wajib
            if not cat1:
                if not tx_id and not tgl_form and not amt:
                    continue # Baris benar-benar kosong
                conn.rollback()
                return {"ok": False, "pesan": f"Baris {idx}: Cat1 (Perusahaan) wajib diisi."}
            if not tgl_form:
                conn.rollback()
                return {"ok": False, "pesan": f"Baris {idx}: Tanggal Form wajib diisi."}
                
            lembaga = str(lembaga).strip() if lembaga else ""
            desc = str(desc).strip() if desc else ""
            cat = str(cat).strip() if cat else ""'''

if search_str in service_content:
    service_content = service_content.replace(search_str, replace_str)
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    print("Patch applied to service.py")
else:
    print("search_str not found")

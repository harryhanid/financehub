import os
import re

service_path = r'C:\Financehub\app\modules\sponsorship\service.py'
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

# Replace the inner loop logic to be more robust and use ALL excel columns explicitly
search_pattern = r"            tx_id = row\[0\].*?updated_count \+= 1\s+else:\s+# Insert.*?inserted_count \+= 1"
# Wait, regex dotall is tricky in powershell replacement, let's just do a python string replace from known start to end

start_marker = "            tx_id = row[0]"
end_marker = "                inserted_count += 1"

start_idx = service_content.find(start_marker)
end_idx = service_content.find(end_marker) + len(end_marker)

if start_idx != -1 and end_idx != -1:
    new_logic = '''            tx_id = row[0]
            cat = row[1]
            desc = row[2]
            
            # Date handling
            import datetime
            tgl_form = row[3]
            if isinstance(tgl_form, datetime.datetime):
                tgl_form = tgl_form.strftime('%Y-%m-%d')
            tgl_pay = row[4]
            if isinstance(tgl_pay, datetime.datetime):
                tgl_pay = tgl_pay.strftime('%Y-%m-%d')
            if not tgl_pay:
                tgl_pay = None
                
            cat1 = row[5]
            cat2 = row[6]
            cat3 = row[7]
            lembaga = row[8]
            perihal = row[9]
            amt = row[10]
            reff = row[15]
            status = row[16]
            cat4 = row[17]
            coa = row[18]
            cc_total = row[19]
            cc = row[20]
            source = row[21]
            
            # Abaikan baris yang kosong atau tidak valid
            if not cat1 or not tgl_form or not lembaga:
                continue
                
            # Pastikan null aman
            cat1 = str(cat1).strip()
            cat2 = str(cat2).strip() if cat2 else ""
            cat3 = str(cat3).strip() if cat3 else ""
            
            perusahaan = get_perusahaan(cat1)
            if not perusahaan:
                if not cat2 or not cat3:
                    conn.rollback()
                    return {"ok": False, "pesan": f"Baris {idx}: Cat1 '{cat1}' baru, namun Cat2 atau Cat3 kosong di Excel."}
                conn.execute(
                    "INSERT INTO sponsorship_perusahaan (cat1, cat2, cat3) VALUES (?, ?, ?)",
                    (cat1, cat2, cat3)
                )
            else:
                # Update vendor info in DB if excel has different cat2/cat3
                if (cat2 and cat2 != perusahaan["cat2"]) or (cat3 and cat3 != perusahaan["cat3"]):
                    conn.execute(
                        "UPDATE sponsorship_perusahaan SET cat2=?, cat3=? WHERE cat1=?",
                        (cat2, cat3, cat1)
                    )
            
            try:
                amt = float(amt) if amt else 0
            except ValueError:
                amt = 0
                
            if tx_id:
                # Update
                conn.execute(
                    """
                    UPDATE sponsorship_transaksi 
                    SET cat=?, description=?, tanggal_form_sponsor=?, tanggal_payment=?,
                        cat1=?, cat2=?, cat3=?, lembaga_perorangan=?, perihal=?, amount_request=?, reff=?,
                        status=?, cat4=?, coa=?, cc_total=?, cc=?, source=?
                    WHERE id=? AND company_id=?
                    """,
                    (cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source, tx_id, company_id)
                )
                updated_count += 1
            else:
                # Insert
                conn.execute(
                    """
                    INSERT INTO sponsorship_transaksi
                        (company_id, cat, description, tanggal_form_sponsor, tanggal_payment,
                         cat1, cat2, cat3, lembaga_perorangan, perihal, amount_request, reff,
                         status, cat4, coa, cc_total, cc, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, '701078002'), COALESCE(?, 'SMT - Corporate Communication'), COALESCE(?, 'POSPON'), COALESCE(?, 'Sponsor'))
                    """,
                    (company_id, cat, desc, tgl_form, tgl_pay, cat1, cat2, cat3, lembaga, perihal, amt, reff, status, cat4, coa, cc_total, cc, source)
                )
                inserted_count += 1'''
                
    service_content = service_content[:start_idx] + new_logic + service_content[end_idx:]
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    print("Patch applied to service.py")
else:
    print("Markers not found!")

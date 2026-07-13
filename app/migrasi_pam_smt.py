import csv
import sys
import os

# Add current dir to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.payment_memo.service import save_smt_pam_transaction
from database import get_conn

def migrate(csv_file):
    if not os.path.exists(csv_file):
        print(f"File {csv_file} tidak ditemukan.")
        return

    conn = get_conn()
    cur = conn.cursor()
    # Find SMT company
    cur.execute("SELECT id, code FROM companies WHERE code LIKE '%SMT%' OR name LIKE '%Sinar Mas Tjipta%' LIMIT 1")
    company_row = cur.fetchone()
    if not company_row:
        print("Company Sinar Mas Tjipta tidak ditemukan di tabel companies.")
        return
    company_id, company_code = company_row['id'], company_row['code']

    # Read CSV
    pams = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pam_no = row['PAM_No'].strip()
            if not pam_no:
                continue
            if pam_no not in pams:
                pams[pam_no] = {
                    "tanggal": row.get('Tanggal', ''),
                    "pam_no": pam_no,
                    "perusahaan": row.get('Perusahaan', ''),
                    "cc": row.get('Cost_Center', ''),
                    "pillar": row.get('Pillar', ''),
                    "transaksi": row.get('Transaksi', ''),
                    # Approval Dates
                    "tanggal_bayar": row.get('Tanggal_Bayar', ''),
                    "tgl_received": row.get('Tgl_Received', ''),
                    "tgl_a0": row.get('Tgl_A0', ''),
                    "tgl_a1": row.get('Tgl_A1', ''),
                    "tgl_a2": row.get('Tgl_A2', ''),
                    "tgl_a3": row.get('Tgl_A3', ''),
                    "tgl_a4": row.get('Tgl_A4', ''),
                    "rows": []
                }
            
            pams[pam_no]['rows'].append({
                "klasifikasi_sr": row.get('Klasifikasi_SR', ''),
                "klasifikasi_mr": row.get('Klasifikasi_MR', ''),
                "gl_account": row.get('GL_Account', ''),
                "tipe_dokumen": row.get('Tipe_Dokumen', ''),
                "no_invoice": row.get('No_Invoice', ''),
                "vendor": row.get('Vendor', ''),
                "budget_activity": row.get('Budget_Activity', ''),
                "dpp": float(row.get('DPP') or 0),
                "ppn": float(row.get('PPN') or 0),
                "keterangan": row.get('Keterangan', '')
            })

    # Save each PAM
    success_count = 0
    error_count = 0
    for pam_no, pam_data in pams.items():
        print(f"Migrating {pam_no}...")
        
        # 1. Create PAM and Transaction Lines
        result = save_smt_pam_transaction(company_id, company_code, pam_data)
        
        if result.get('ok'):
            # 2. Update tracking dates
            try:
                # Find pam_id
                cur.execute("SELECT id FROM pam_records WHERE pam_no = ?", (pam_no,))
                pam_row = cur.fetchone()
                if pam_row:
                    pam_id = pam_row['id']
                    
                    # Update tanggal_bayar in pam_records
                    if pam_data['tanggal_bayar']:
                        cur.execute("UPDATE pam_records SET tanggal_bayar = ? WHERE id = ?", (pam_data['tanggal_bayar'], pam_id))
                    
                    # Upsert smt_pam_lines for the approval dates
                    cur.execute("SELECT id FROM smt_pam_lines WHERE pam_id = ?", (pam_id,))
                    line_exists = cur.fetchone()
                    
                    if line_exists:
                        cur.execute("""
                            UPDATE smt_pam_lines 
                            SET tgl_received=?, tgl_a0=?, tgl_a1=?, tgl_a2=?, tgl_a3=?, tgl_a4=?, tgl_paid=?
                            WHERE pam_id=?
                        """, (
                            pam_data['tgl_received'], pam_data['tgl_a0'], pam_data['tgl_a1'], 
                            pam_data['tgl_a2'], pam_data['tgl_a3'], pam_data['tgl_a4'], 
                            pam_data['tanggal_bayar'], pam_id
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO smt_pam_lines (pam_id, tgl_received, tgl_a0, tgl_a1, tgl_a2, tgl_a3, tgl_a4, tgl_paid)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            pam_id, pam_data['tgl_received'], pam_data['tgl_a0'], pam_data['tgl_a1'], 
                            pam_data['tgl_a2'], pam_data['tgl_a3'], pam_data['tgl_a4'], pam_data['tanggal_bayar']
                        ))
                    
                    conn.commit()
                    
                print(f"Sukses migrasi {pam_no} beserta tanggal approval.")
                success_count += 1
            except Exception as e:
                print(f"Sukses migrasi {pam_no}, TAPI gagal update tanggal: {e}")
                error_count += 1
        else:
            print(f"Gagal migrasi {pam_no}: {result.get('pesan')}")
            error_count += 1

    print(f"Selesai! Sukses: {success_count}, Gagal: {error_count}")

if __name__ == '__main__':
    csv_path = 'Template_Migrasi_PAM_SMT.csv'
    migrate(csv_path)

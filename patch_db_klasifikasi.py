import sqlite3

def patch_db():
    conn = sqlite3.connect("app/finance_hub.db")
    
    # 1. pam_records
    try:
        conn.execute("ALTER TABLE pam_records ADD COLUMN klasifikasi TEXT DEFAULT 'Normal'")
        print("Added klasifikasi to pam_records")
    except Exception as e:
        print("pam_records:", e)
        
    # 2. payment_beasiswa
    try:
        conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN klasifikasi_pam TEXT")
        print("Added klasifikasi_pam to payment_beasiswa")
    except Exception as e:
        print("payment_beasiswa:", e)
        
    # 3. klaim_medical
    try:
        conn.execute("ALTER TABLE klaim_medical ADD COLUMN klasifikasi_pam TEXT")
        print("Added klasifikasi_pam to klaim_medical")
    except Exception as e:
        print("klaim_medical:", e)
        
    # 4. pam_transaction_lines
    try:
        conn.execute("ALTER TABLE pam_transaction_lines ADD COLUMN klasifikasi_pam TEXT")
        print("Added klasifikasi_pam to pam_transaction_lines")
    except Exception as e:
        print("pam_transaction_lines:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    patch_db()

from database import get_conn
conn = get_conn()
conn.execute("UPDATE payment_beasiswa SET siswa_code = '3250250' WHERE siswa_code = '2180066' AND pam = 'PAM-114-ETF-12-2025'")
conn.commit()
print("Updated successfully")

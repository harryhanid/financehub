with open("app/database.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    'conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN klasifikasi_pa TEXT DEFAULT \'Normal\'")\n    except sqlite3.OperationalError:\n        pass',
    'conn.execute("ALTER TABLE payment_beasiswa ADD COLUMN klasifikasi_pa TEXT DEFAULT \'Normal\'")\n    except sqlite3.OperationalError:\n        pass\n\n    try:\n        conn.execute("ALTER TABLE budget_beasiswa ADD COLUMN tgl_expired TEXT DEFAULT NULL")\n    except sqlite3.OperationalError:\n        pass'
)

with open("app/database.py", "w", encoding="utf-8") as f:
    f.write(text)

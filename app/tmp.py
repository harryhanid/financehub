import sqlite3, config
c = sqlite3.connect(config.DB_PATH)
rows = c.execute("SELECT code, nama, group_setf FROM siswa WHERE CAST(code AS INTEGER) >= 5260056 AND (group_setf LIKE 'A.%' OR group_setf LIKE 'B.%')").fetchall()
for r in rows: print(r)

import sqlite3
conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
c = conn.cursor()
c.execute('SELECT username, role FROM users')
print(c.fetchall())
conn.close()

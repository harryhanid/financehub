import sqlite3
import bcrypt

conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
c = conn.cursor()

# Hash the password "Flow12345"
password = "Flow12345".encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

# Update the user tommy
c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (hashed, 'tommy'))
conn.commit()

# Verify
c.execute('SELECT username, is_active FROM users WHERE username = ?', ('tommy',))
print(c.fetchone())
conn.close()

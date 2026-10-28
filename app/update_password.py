import sqlite3
import bcrypt

username = 'harry'
new_password = '12345678'

pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(12)).decode()

conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
c = conn.cursor()
c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (pw_hash, username))
conn.commit()
conn.close()

print('Password for harry updated successfully.')

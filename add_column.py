import sqlite3

def add_column():
    conn = sqlite3.connect('C:/Financehub/app/finance_hub.db')
    try:
        conn.execute('ALTER TABLE siswa ADD COLUMN group_setf TEXT')
        conn.commit()
        print('Column group_setf added successfully.')
    except sqlite3.OperationalError as e:
        print('Error (might already exist):', e)
    finally:
        conn.close()

if __name__ == '__main__':
    add_column()

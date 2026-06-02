from app.database import init_db, get_conn

init_db()
conn = get_conn()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(tables)
conn.close()

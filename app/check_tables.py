from database import init_db, get_conn

init_db()
c = get_conn()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
c.close()
print("Tables in database:", tables)
print("\nSearching for etf_pa:", "etf_pa" in tables)
print("Searching for etf_pa_lines:", "etf_pa_lines" in tables)

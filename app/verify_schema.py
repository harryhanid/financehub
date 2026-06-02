from database import get_conn

c = get_conn()

# Check etf_pa columns
print("=== etf_pa columns ===")
etf_pa_info = c.execute("PRAGMA table_info(etf_pa)").fetchall()
for col in etf_pa_info:
    print(f"  {col[1]}: {col[2]}")

print("\n=== etf_pa_lines columns ===")
etf_pa_lines_info = c.execute("PRAGMA table_info(etf_pa_lines)").fetchall()
for col in etf_pa_lines_info:
    print(f"  {col[1]}: {col[2]}")

c.close()

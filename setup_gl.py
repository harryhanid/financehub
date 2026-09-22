import pandas as pd
import sqlite3
import os
import re

EXCEL_FILE = r'C:\Users\25010160\Downloads\contoh.xlsx'
DB_FILE = r'C:\Financehub\app\finance_hub.db'

def clean_col_name(col):
    col = str(col).lower()
    col = re.sub(r'[^a-z0-9]', '_', col)
    col = re.sub(r'_+', '_', col)
    return col.strip('_')

def main():
    print("Reading Excel...")
    df = pd.read_excel(EXCEL_FILE)
    
    print("Cleaning columns...")
    df.columns = [clean_col_name(c) for c in df.columns]
    
    print("Connecting to DB...")
    conn = sqlite3.connect(DB_FILE)
    
    # Generate DDL
    cols_ddl = []
    for col in df.columns:
        dt = df.dtypes[col]
        if 'int' in str(dt):
            sql_type = 'INTEGER'
        elif 'float' in str(dt):
            sql_type = 'REAL'
        elif 'datetime' in str(dt):
            sql_type = 'TEXT'
        else:
            sql_type = 'TEXT'
        cols_ddl.append(f"    {col} {sql_type}")
    
    ddl = "CREATE TABLE IF NOT EXISTS gl_transactions (\n    id_gl INTEGER PRIMARY KEY AUTOINCREMENT,\n" + ",\n".join(cols_ddl) + "\n);"
    
    # Inject DDL into database.py so it's persisted
    db_py_path = r'C:\Financehub\app\database.py'
    with open(db_py_path, 'r', encoding='utf-8') as f:
        db_py_content = f.read()
    
    if 'CREATE TABLE IF NOT EXISTS gl_transactions' not in db_py_content:
        # Find where to insert (before the close quote of DDL)
        end_ddl_idx = db_py_content.rfind('"""')
        # Actually it's better to just append it before the `"""` that closes the DDL string
        
        # In database.py, DDL starts with `DDL = """` and ends with `"""`
        # Let's just do a simple replacement
        lines = db_py_content.splitlines()
        for i, line in enumerate(lines):
            if 'INSERT INTO users' in line:
                # We reached the end of DDL string, the previous line or so is `"""`
                pass
        
        # Alternative: just execute it directly on SQLite for now to ensure it exists, 
        # and we can append to database.py safely
        print("Executing DDL on SQLite...")
        conn.execute("DROP TABLE IF EXISTS gl_transactions")
        conn.execute(ddl)
        
        # Convert df to string/proper types for sqlite
        print("Inserting data to SQLite...")
        # datetime needs to be string
        for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
            df[col] = df[col].astype(str)
            
        df.to_sql('gl_transactions', conn, if_exists='append', index=False)
        print("Done!")
    conn.close()

    # Now let's append the DDL to database.py
    if 'gl_transactions' not in db_py_content:
        # Find the last `"""` before `def init_db():`
        init_idx = db_py_content.find('def init_db():')
        if init_idx != -1:
            pre_init = db_py_content[:init_idx]
            last_quote_idx = pre_init.rfind('"""')
            if last_quote_idx != -1:
                new_db_py = db_py_content[:last_quote_idx] + "\n" + ddl + "\n" + db_py_content[last_quote_idx:]
                with open(db_py_path, 'w', encoding='utf-8') as f:
                    f.write(new_db_py)
                print("Appended DDL to database.py")


if __name__ == '__main__':
    main()

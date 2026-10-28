import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add get_distinct_angkatan if not exists
if "def get_distinct_angkatan" not in content:
    func = '''def get_distinct_angkatan(company_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT angkatan FROM siswa WHERE company_id=? AND angkatan IS NOT NULL ORDER BY angkatan DESC", (company_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]
'''
    content = content.replace("def get_distinct_universitas", func + "\ndef get_distinct_universitas")

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

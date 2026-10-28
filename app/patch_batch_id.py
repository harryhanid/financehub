import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure uuid is imported
if 'import uuid' not in content:
    content = 'import uuid\n' + content

# Patch delete_budget_row
content = re.sub(
    r'(?sm)(def delete_budget_row\(company_id: int, row_id: int, created_by: str\) -> dict:.*?)("INSERT INTO budget_beasiswa_requests \(company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by\).*?VALUES \(\?, \?, \'DELETE\', \?, \?, \?, \?, \?, \?, \?, \?\)")',
    r'\1"INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) " "VALUES (?, ?, \'DELETE\', ?, ?, ?, ?, ?, ?, ?, ?, ?)"',
    content
)
content = re.sub(
    r'(row\["amount"\], row\["pillar"\], row\["tgl_expired"\], created_by\))',
    r'\1[:-1] + (created_by, str(uuid.uuid4())[:8]))',
    content
)

# Patch update_budget_row
content = re.sub(
    r'(?sm)(def update_budget_row\(company_id: int, row_id: int, data: dict, created_by: str\) -> dict:.*?)("INSERT INTO budget_beasiswa_requests \(company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by\).*?VALUES \(\?, \?, \'EDIT\', \?, \?, \?, \?, \?, \?, \?, \?\)")',
    r'\1"INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, budget_id, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) " "VALUES (?, ?, \'EDIT\', ?, ?, ?, ?, ?, ?, ?, ?, ?)"',
    content
)
content = re.sub(
    r'(data\.get\("tgl_expired"\) or None, created_by\))',
    r'\1[:-1] + (created_by, str(uuid.uuid4())[:8]))',
    content
)

# Patch add_budget_batch
content = re.sub(
    r'(?sm)(def add_budget_batch\(company_id: int, siswa_code: str, tanggal: str,.*?conn  = get_conn\(\))',
    r'\1\n    batch_id = str(uuid.uuid4())[:8]',
    content
)
content = re.sub(
    r'(?sm)("INSERT INTO budget_beasiswa_requests \(company_id, siswa_code, action_type, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by\) ".*?VALUES \(\?, \?, \'ADD\', \?, \?, \?, \?, \?, \?, \?\)")',
    r'"INSERT INTO budget_beasiswa_requests (company_id, siswa_code, action_type, cat1, cat2, tanggal, amount, pillar, tgl_expired, created_by, batch_id) " "VALUES (?, ?, \'ADD\', ?, ?, ?, ?, ?, ?, ?, ?)"',
    content
)
content = re.sub(
    r'(item\.get\("tgl_expired"\) or None, created_by\))',
    r'\1[:-1] + (created_by, batch_id))',
    content
)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

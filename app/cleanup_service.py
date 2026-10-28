import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The first one that wasn't deleted
content = re.sub(r'(?sm)def delete_budget_row\(company_id: int, row_id: int\).*?return \{"ok": True, "pesan": "Baris budget dihapus\."\}', '', content)
content = re.sub(r'(?sm)def update_budget_row\(company_id: int, row_id: int, data: dict\).*?return \{"ok": True, "pesan": "Baris budget diperbarui\."\}', '', content)
content = re.sub(r'(?sm)def add_budget_batch\(company_id: int, siswa_code: str, tanggal: str,\s*pillar: str, items: list\) -> dict:.*?return \{"ok": True, "pesan": f"\{saved\} baris budget ditambahkan\."\}', '', content)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

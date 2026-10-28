import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'(?sm)def delete_budget_row\(company_id: int, row_id: int\) -> dict:.*?return \{"ok": True, "pesan": "Baris budget dihapus\."\}', '', content)
content = re.sub(r'(?sm)def update_budget_row\(company_id: int, row_id: int, data: dict\) -> dict:.*?return \{"ok": True, "pesan": "Baris budget diperbarui\."\}', '', content)
content = re.sub(r'(?sm)def add_budget_batch\(company_id: int, siswa_code: str, tanggal: str,\s*pillar: str, items: list\) -> dict:.*?return \{"ok": True, "pesan": f"\{saved\} baris budget berhasil disimpan\.", "saved": saved\}', '', content)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

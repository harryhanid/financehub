import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = r'def build_pohon_data\(company_id: int, years: list = None, month: int = 12, pillars: list = None\) -> dict:\n\s*"""[\s\S]*?"""\n\s*buckets = _build_diagram_buckets\(company_id, \[str\(report_year\)\], report_month, pillars\)'
repl1 = 'def build_pohon_data(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:\n    """Membangun struktur pohon (Root -> [Kesehatan, Pendidikan] -> [Siswa]) untuk UI Pohon Sahabat.\n    Hanya mengambil nilai Kumulatif (Cum) hingga report_year, dan Plafon + PTA untuk kolom Plafon."""\n    buckets = _build_diagram_buckets(company_id, years, month, pillars)'

target2 = r'def build_pohon_group_data\(company_id: int, years: list = None, month: int = 12, pillars: list = None\) -> dict:\n\s*buckets = _build_diagram_buckets\(company_id, \[str\(report_year\)\], report_month, pillars\)'
repl2 = 'def build_pohon_group_data(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:\n    buckets = _build_diagram_buckets(company_id, years, month, pillars)'

content = re.sub(target1, repl1, content)
content = re.sub(target2, repl2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed NameErrors in pohon functions!")

import re
file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Update _build_diagram_buckets signature
target1 = r'def _build_diagram_buckets\(company_id: int, years: list = None, pillars: list = None\) -> dict:'
repl1 = 'def _build_diagram_buckets(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:'
content = re.sub(target1, repl1, content)

# Add month filter to _build_diagram_buckets for budget and payment
# For budget_rows
content = re.sub(r'if years and r\["tahun"\] not in years:\s*continue',
                 'if years and r["tahun"] not in years:\n            continue\n        if r["bulan"] and r["bulan"] > month:\n            continue', content)

# For payment_rows
# The regex above will replace both! Because both have the same block.

# Update build_pohon_data signature
target2 = r'def build_pohon_data\(company_id: int, years: list = None, pillars: list = None\) -> dict:'
repl2 = 'def build_pohon_data(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:'
content = re.sub(target2, repl2, content)

# Update build_pohon_data internal call
target3 = r'buckets = _build_diagram_buckets\(company_id, years, pillars\)'
repl3 = 'buckets = _build_diagram_buckets(company_id, years, month, pillars)'
content = re.sub(target3, repl3, content)

# Update build_pohon_group_data signature
target4 = r'def build_pohon_group_data\(company_id: int, years: list = None, pillars: list = None\) -> dict:'
repl4 = 'def build_pohon_group_data(company_id: int, years: list = None, month: int = 12, pillars: list = None) -> dict:'
content = re.sub(target4, repl4, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated service.py")

file_path2 = "C:/Financehub/app/modules/sahabat_etf/routes.py"
with open(file_path2, "r", encoding="utf-8") as f:
    content2 = f.read()

target5 = r'"diagram1": build_pohon_data\(_cid\(\), parsed_years, pillars\),\s*"diagram2": build_pohon_group_data\(_cid\(\), parsed_years, pillars\)'
repl5 = '"diagram1": build_pohon_data(_cid(), parsed_years, month, pillars),\n            "diagram2": build_pohon_group_data(_cid(), parsed_years, month, pillars)'
content2 = re.sub(target5, repl5, content2)

with open(file_path2, "w", encoding="utf-8") as f:
    f.write(content2)
print("Updated routes.py")

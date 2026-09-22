file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re
# Delete all setfExportPdf functions completely
content = re.sub(r'(async )?function setfExportPdf\(\) \{[\s\S]*?\n\}\n', '', content)

with open("C:/Financehub/implement_pdf_scaling.py", "r", encoding="utf-8") as f:
    impl_content = f.read()

match = re.search(r'replacement = """(async function setfExportPdf\(\) \{[\s\S]*?\n\})"""', impl_content)
replacement = match.group(1)

content += "\n\n" + replacement

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Deleted old exports and injected new one!")

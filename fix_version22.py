import re

files = [
    "C:/Financehub/app/templates/sahabat_etf/index.html",
    "C:/Financehub/app/templates/beasiswa/index.html"
]

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r'sahabat_etf\.js\'\) \}\}\?v=4\.[0-9]+', "sahabat_etf.js') }}?v=4.993", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
print("Updated HTML files to v4.993!")

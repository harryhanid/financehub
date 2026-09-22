import re

files = [
    "C:/Financehub/app/templates/sahabat_etf/index.html",
    "C:/Financehub/app/templates/beasiswa/index.html"
]

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The regex in fix_version.py was: sahabat_etf\.js\?v=4\.[0-9]+
    # BUT in the HTML it is: js/sahabat_etf.js') }}?v=4.35
    # So the regex failed because of the ') }} part!
    content = re.sub(r'sahabat_etf\.js\'\) \}\}\?v=4\.[0-9]+', "sahabat_etf.js') }}?v=4.82", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
print("Updated HTML files!")

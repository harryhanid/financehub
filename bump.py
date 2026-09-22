file_path = "C:/Financehub/app/templates/sahabat_etf/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()
import re
new_content = re.sub(r'sahabat_etf\.js\?v=5\.\d+', 'sahabat_etf.js?v=5.008', content)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Bumped cache version to v=5.008")

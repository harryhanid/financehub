import glob
import re

files = [
    "C:/Financehub/app/templates/beasiswa/index.html",
    "C:/Financehub/app/templates/sahabat_etf/index.html"
]

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = re.sub(r'\?v=5\.\d+', '?v=5.009', content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Bumped {file_path}!")

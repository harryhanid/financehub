import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const container = document\.createElement\("div"\);\s*container\.style\.position = "absolute";\s*container\.style\.left = "-9999px";\s*container\.style\.top = "-9999px";'
replacement = """const container = document.createElement("div");"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

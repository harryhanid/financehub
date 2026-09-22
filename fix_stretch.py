import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_chart = r'img\.style\.maxWidth = "100%";\s*img\.style\.maxHeight = "100%";\s*img\.style\.objectFit = "contain";'
replacement_chart = """img.style.width = "100%";
            img.style.height = "100%";
            img.style.objectFit = "fill";"""
content = re.sub(target_chart, replacement_chart, content)

target_table_page = r'const tablePage = document\.createElement\("div"\);\s*tablePage\.style\.width = "1122px";\s*tablePage\.style\.height = "790px";'
replacement_table_page = """const tablePage = document.createElement("div");
        tablePage.style.width = "1122px";
        tablePage.style.minHeight = "790px";"""
content = re.sub(target_table_page, replacement_table_page, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

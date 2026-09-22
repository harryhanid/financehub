import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix chart objectFit back to contain
target_chart = r'img\.style\.width = "100%";\s*img\.style\.height = "100%";\s*img\.style\.objectFit = "fill";'
replacement_chart = """img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";"""
content = re.sub(target_chart, replacement_chart, content)

# 2. Reduce padding of table page to gain space
target_table_page = r'const tablePage = document\.createElement\("div"\);\s*tablePage\.style\.width = "1122px";\s*tablePage\.style\.minHeight = "790px";\s*tablePage\.style\.padding = "40px";'
replacement_table_page = """const tablePage = document.createElement("div");
        tablePage.style.width = "1122px";
        tablePage.style.minHeight = "790px";
        tablePage.style.padding = "20px 40px";""" # 20px top/bottom, 40px left/right
content = re.sub(target_table_page, replacement_table_page, content)

# 3. Reduce table font size slightly so Sahabat table fits on 1 page
target_table_font = r'tableClone\.style\.fontSize = "14px";'
replacement_table_font = 'tableClone.style.fontSize = "12px";'
content = re.sub(target_table_font, replacement_table_font, content)

target_table_padding = r'cell\.style\.padding = "8px 12px";'
replacement_table_padding = 'cell.style.padding = "6px 10px";'
content = re.sub(target_table_padding, replacement_table_padding, content)

# 4. Add tr to avoid breaking
target_opt = r'pagebreak:\s*\{\s*mode:\s*\[\'css\', \'legacy\'\]\s*\}'
replacement_opt = "pagebreak:    { mode: ['css', 'legacy'], avoid: 'tr' }"
content = re.sub(target_opt, replacement_opt, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

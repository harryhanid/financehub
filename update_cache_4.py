file_path = "C:/Financehub/app/templates/sahabat_etf/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("sahabat_etf.js?v=5.003", "sahabat_etf.js?v=5.004")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated cache version to 5.004!")

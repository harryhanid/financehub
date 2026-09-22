file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Delete lines 499 to 515 (0-indexed)
new_lines = lines[:499] + lines[516:]

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Deleted leftover lines!")

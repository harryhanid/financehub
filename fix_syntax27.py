file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = lines[:211] + lines[269:]

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Deleted broken plugin body!")

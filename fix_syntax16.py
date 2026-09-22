file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = lines[:884] + lines[890:]

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Deleted leftover lines 885-890!")

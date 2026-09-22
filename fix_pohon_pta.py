import re
file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix in build_pohon_data
# Currently: plafon_total = cum["plafon"]
# Replace with: plafon_total = cum["plafon"] + cum["pta"]
target1 = r'plafon_total = cum\["plafon"\]\s*realisasi = cum\["dibayar"\]'
repl1 = 'plafon_total = cum["plafon"] + cum["pta"]\n        realisasi = cum["dibayar"]'
content = re.sub(target1, repl1, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated service.py")

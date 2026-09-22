import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = r'let chartKategori = \[\n\s*\{\s*name:\s*"By Medical",\s*budget:\s*medBgt,\s*realisasi:\s*medAct\s*\}\,?\n\s*\{\s*name:\s*"By Pendidikan",\s*budget:\s*penBgt,\s*realisasi:\s*penAct\s*\}\n\s*\];'
replacement1 = """let chartKategori = [
        { name: "Kesehatan", budget: medBgt, realisasi: medAct, originalName: "By Medical" },
        { name: "Pendidikan", budget: penBgt, realisasi: penAct, originalName: "By Pendidikan" }
    ];"""
content = re.sub(target1, replacement1, content)

target2 = r'let color = setfColorForCategory\(item\.name\);'
replacement2 = """let color = setfColorForCategory(item.originalName || item.name);"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

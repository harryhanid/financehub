import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const stackData = \[\n\s*\{\s*name:\s*"By Medical",\s*budget:\s*kesBudget,\s*realisasi:\s*kesActual\s*\}\,?\n\s*\{\s*name:\s*"By Pendidikan",\s*budget:\s*penBudget,\s*realisasi:\s*penActual\s*\}\n\s*\];'
replacement = """const stackData = [
        { name: "Kesehatan", budget: kesBudget, realisasi: kesActual, originalName: "By Medical" },
        { name: "Pendidikan", budget: penBudget, realisasi: penActual, originalName: "By Pendidikan" }
    ];"""
content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

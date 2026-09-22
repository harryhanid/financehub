import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the inner map function string
target1 = """return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td></tr>";"""

repl1 = """return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.budget) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td>" +
          setfSisaCell((m.budget || 0) - (m.realisasi || 0)) + "</tr>";"""

content = content.replace(target1, repl1)

# Replace the totalRow string
target2 = """const totalRow = "<tr style=\\"font-weight:bold\\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td></tr>";"""

repl2 = """const totalRow = "<tr style=\\"font-weight:bold\\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_budget) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td>" +
        setfSisaCell((f.total_budget || 0) - (f.total_realisasi || 0)) + "</tr>";"""

content = content.replace(target2, repl2)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated setfRenderFamilyTable with exact string replacement!")

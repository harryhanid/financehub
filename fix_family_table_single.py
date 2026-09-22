import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# memberRows replacement
pattern1 = r'\'<td class="num-right">\' \+ setfFmtJutaan\(m\.realisasi\) \+ "</td></tr>";'
repl1 = r'\'<td class="num-right">\' + setfFmtJutaan(m.budget) + "</td>" + \'<td class="num-right">\' + setfFmtJutaan(m.realisasi) + "</td>" + setfSisaCell((m.budget || 0) - (m.realisasi || 0)) + "</tr>";'
content = re.sub(pattern1, repl1, content)

# totalRow replacement
pattern2 = r'\'<td class="num-right">\' \+ setfFmtJutaan\(f\.total_realisasi\) \+ "</td></tr>";'
repl2 = r'\'<td class="num-right">\' + setfFmtJutaan(f.total_budget) + "</td>" + \'<td class="num-right">\' + setfFmtJutaan(f.total_realisasi) + "</td>" + setfSisaCell((f.total_budget || 0) - (f.total_realisasi || 0)) + "</tr>";'
content = re.sub(pattern2, repl2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated setfRenderFamilyTable with regex on single lines!")

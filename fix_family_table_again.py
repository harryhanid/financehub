import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r"""const memberRows = f\.members\.map\(function \(m\) \{\s*return "<tr><td>" \+ f\.label \+ "</td><td>" \+ m\.nama \+ "</td>" \+\s*"<td>" \+ setfCatBadgeList\(m\.kategori\) \+ "</td>" \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(m\.realisasi\) \+ "</td></tr>";\s*\}\)\.join\(""\);\s*const totalRow = "<tr style=\\"font-weight:bold\\"><td>" \+ f\.label \+ " - Total</td><td></td><td></td>" \+\s*\'<td class="num-right">\' \+ setfFmtJutaan\(f\.total_realisasi\) \+ "</td></tr>";"""

repl = """const memberRows = f.members.map(function (m) {
        return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.budget) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td>" +
          setfSisaCell((m.budget || 0) - (m.realisasi || 0)) + "</tr>";
      }).join("");
      const totalRow = "<tr style=\\"font-weight:bold\\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_budget) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td>" +
        setfSisaCell((f.total_budget || 0) - (f.total_realisasi || 0)) + "</tr>";"""

content = re.sub(target, repl, content)

# Let's also fix the "Belum ada data" colspan which says colspan="4" but should be "6"
content = re.sub(r'colspan="4"(.*?)>Belum ada data sahabat', r'colspan="6"\1>Belum ada data sahabat', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated setfRenderFamilyTable successfully!")

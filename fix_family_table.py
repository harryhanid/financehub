import re
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderFamilyTable\(families\) \{[\s\S]*?return memberRows \+ totalRow;\n\s*\}\)\.join\(""\);\n\s*\}'

repl = """function setfRenderFamilyTable(families) {
    const tbody = document.querySelector("#setf-family-table tbody");
    if (!families.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada data sahabat.</td></tr>';
      return;
    }
    tbody.innerHTML = families.map(function (f) {
      const memberRows = f.members.map(function (m) {
        const bgt = m.budget || 0;
        const sisa = bgt - m.realisasi;
        return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(bgt) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td>" +
          setfSisaCell(sisa) + "</tr>";
      }).join("");
      
      const totalBudget = f.total_budget || f.members.reduce((a,b)=>a+(b.budget||0), 0);
      const totalSisa = totalBudget - f.total_realisasi;
      const totalRow = "<tr style=\\"font-weight:bold\\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(totalBudget) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td>" +
        setfSisaCell(totalSisa) + "</tr>";
      return memberRows + totalRow;
    }).join("");
  }"""

new_content = re.sub(target, repl, content)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Updated setfRenderFamilyTable!")

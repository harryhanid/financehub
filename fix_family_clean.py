import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderFamilyTable\(families\) \{.*?\n  \}'
repl = """function setfRenderFamilyTable(families) {
    const tbody = document.querySelector("#setf-family-table tbody");
    if (!families.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada data sahabat.</td></tr>';
      return;
    }
    tbody.innerHTML = families.map(function (f) {
      const memberRows = f.members.map(function (m) {
        return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.budget) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td>" +
          setfSisaCell((m.budget || 0) - (m.realisasi || 0)) + "</tr>";
      }).join("");
      const totalRow = "<tr style=\\"font-weight:bold\\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_budget) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td>" +
        setfSisaCell((f.total_budget || 0) - (f.total_realisasi || 0)) + "</tr>";
      return memberRows + totalRow;
    }).join("");
  }"""

content = re.sub(target, repl, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Rewrote setfRenderFamilyTable perfectly!")

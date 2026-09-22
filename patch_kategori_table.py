import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

start_idx = js_content.find("function setfRenderKategoriTable(kategoriRows)")
end_idx = js_content.find("\n\nlet setfYearlyData = null;", start_idx)

new_func = """function setfRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#setf-kategori-table tbody");
  if (!kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  
  const pddRows = kategoriRows.filter(k => k.cat1 !== "By Medical");
  const kesRows = kategoriRows.filter(k => k.cat1 === "By Medical");
  
  let html = "";
  
  if (pddRows.length > 0) {
      html += '<tr><td colspan="4" style="font-weight:bold; font-size:1.1em; padding-top:1rem; padding-bottom:0.5rem; color:var(--text-primary)">Pendidikan</td></tr>';
      html += pddRows.map(function (k) {
        const sisa = k.budget - k.realisasi;
        return "<tr>" +
          "<td>" + setfCatBadge(k.cat1) + "</td>" +
          "<td>" + setfFmtJutaan(k.budget) + "</td>" +
          "<td>" + setfFmtJutaan(k.realisasi) + "</td>" +
          setfSisaCell(sisa) +
          "</tr>";
      }).join("");
      
      const subBgt = pddRows.reduce((s, k) => s + k.budget, 0);
      const subAct = pddRows.reduce((s, k) => s + k.realisasi, 0);
      const subSisa = subBgt - subAct;
      html += '<tr style="font-weight:bold; background:rgba(241, 245, 249, 0.5)">' +
        '<td style="color:var(--text-primary)">Sub Total Pendidikan</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subBgt) + '</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subAct) + '</td>' +
        '<td ' + (subSisa < 0 ? 'class="setf-sisa-negative"' : '') + '>' + setfFmtJutaan(subSisa) + '</td></tr>';
  }
  
  if (kesRows.length > 0) {
      html += '<tr><td colspan="4" style="font-weight:bold; font-size:1.1em; padding-top:1rem; padding-bottom:0.5rem; color:var(--text-primary)">Kesehatan</td></tr>';
      html += kesRows.map(function (k) {
        const sisa = k.budget - k.realisasi;
        return "<tr>" +
          "<td>" + setfCatBadge(k.cat1) + "</td>" +
          "<td>" + setfFmtJutaan(k.budget) + "</td>" +
          "<td>" + setfFmtJutaan(k.realisasi) + "</td>" +
          setfSisaCell(sisa) +
          "</tr>";
      }).join("");
      
      const subBgt = kesRows.reduce((s, k) => s + k.budget, 0);
      const subAct = kesRows.reduce((s, k) => s + k.realisasi, 0);
      const subSisa = subBgt - subAct;
      html += '<tr style="font-weight:bold; background:rgba(241, 245, 249, 0.5)">' +
        '<td style="color:var(--text-primary)">Sub Total Kesehatan</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subBgt) + '</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subAct) + '</td>' +
        '<td ' + (subSisa < 0 ? 'class="setf-sisa-negative"' : '') + '>' + setfFmtJutaan(subSisa) + '</td></tr>';
  }
  
  const totalBgt = kategoriRows.reduce((s, k) => s + k.budget, 0);
  const totalAct = kategoriRows.reduce((s, k) => s + k.realisasi, 0);
  const totalSisa = totalBgt - totalAct;
  html += '<tr style="font-weight:bold;">' +
    '<td style="color:var(--text-primary); font-size: 1.05em; padding-top:1rem;">Total Pendidikan dan Kesehatan</td>' +
    '<td style="color:var(--text-primary); font-size: 1.05em; padding-top:1rem;">' + setfFmtJutaan(totalBgt) + '</td>' +
    '<td style="color:var(--text-primary); font-size: 1.05em; padding-top:1rem;">' + setfFmtJutaan(totalAct) + '</td>' +
    '<td style="font-size: 1.05em; padding-top:1rem;" ' + (totalSisa < 0 ? 'class="setf-sisa-negative"' : '') + '>' + setfFmtJutaan(totalSisa) + '</td></tr>';
    
  tbody.innerHTML = html;
}"""

js_content = js_content[:start_idx] + new_func + js_content[end_idx:]

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
    
print("Table patched!")

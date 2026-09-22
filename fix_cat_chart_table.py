import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the fetch block for chart-kategori labels
target1 = r'setfRenderBudgetVsRealisasiChart\("chart-kategori",\s*data\.kategori\.map\(function \(k\) \{ return k\.cat1; \}\),'
replacement1 = """let catLabels = data.kategori.map(function (k) {
          if (k.cat1 === "By Medical") return ["Kesehatan", k.cat1];
          if (k.cat1 === "By Pendidikan" || k.cat1 === "By Tunjangan") return ["Pendidikan", k.cat1];
          return k.cat1;
        });
        setfRenderBudgetVsRealisasiChart("chart-kategori",
            catLabels,"""
content = re.sub(target1, replacement1, content)

# 2. Update setfRenderKategoriTable
target2 = r'function setfRenderKategoriTable\(kategoriRows\) \{.*?\n  \}'
replacement2 = """function setfRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#setf-kategori-table tbody");
  if (!kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  
  let html = "";
  
  // PENDIDIKAN
  let penBgt = 0, penAct = 0;
  let tunjangan = kategoriRows.find(k => k.cat1 === "By Tunjangan");
  let pendidikan = kategoriRows.find(k => k.cat1 === "By Pendidikan");
  
  if (tunjangan || pendidikan) {
      html += "<tr style='background:transparent;'><td colspan='4'><strong style='font-size:1.05em;'>Pendidikan</strong></td></tr>";
      
      if (tunjangan) {
          penBgt += tunjangan.budget;
          penAct += tunjangan.realisasi;
          html += "<tr><td>" + setfCatBadge(tunjangan.cat1) + "</td><td>" + setfFmtJutaan(tunjangan.budget) + "</td><td>" + setfFmtJutaan(tunjangan.realisasi) + "</td>" + setfSisaCell(tunjangan.budget - tunjangan.realisasi) + "</tr>";
      }
      if (pendidikan) {
          penBgt += pendidikan.budget;
          penAct += pendidikan.realisasi;
          html += "<tr><td>" + setfCatBadge(pendidikan.cat1) + "</td><td>" + setfFmtJutaan(pendidikan.budget) + "</td><td>" + setfFmtJutaan(pendidikan.realisasi) + "</td>" + setfSisaCell(pendidikan.budget - pendidikan.realisasi) + "</tr>";
      }
      
      html += "<tr style='background:rgba(0,0,0,0.03); font-weight:bold;'><td>Sub Total Pendidikan</td><td>" + setfFmtJutaan(penBgt) + "</td><td>" + setfFmtJutaan(penAct) + "</td>" + setfSisaCell(penBgt - penAct) + "</tr>";
  }
  
  // KESEHATAN
  let medBgt = 0, medAct = 0;
  let medical = kategoriRows.find(k => k.cat1 === "By Medical");
  if (medical) {
      medBgt += medical.budget;
      medAct += medical.realisasi;
      html += "<tr style='background:transparent;'><td colspan='4'><strong style='font-size:1.05em;'>Kesehatan</strong></td></tr>";
      html += "<tr><td>" + setfCatBadge(medical.cat1) + "</td><td>" + setfFmtJutaan(medical.budget) + "</td><td>" + setfFmtJutaan(medical.realisasi) + "</td>" + setfSisaCell(medical.budget - medical.realisasi) + "</tr>";
      html += "<tr style='background:rgba(0,0,0,0.03); font-weight:bold;'><td>Sub Total Kesehatan</td><td>" + setfFmtJutaan(medBgt) + "</td><td>" + setfFmtJutaan(medAct) + "</td>" + setfSisaCell(medBgt - medAct) + "</tr>";
  }
  
  const totalBudget = kategoriRows.reduce((s, k) => s + k.budget, 0);
  const totalRealisasi = kategoriRows.reduce((s, k) => s + k.realisasi, 0);
  const totalRow = "<tr style='font-weight:bold; background:var(--bg-secondary)'><td>Total Pendidikan dan Kesehatan</td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    "<td>" + setfFmtJutaan(totalRealisasi) + "</td>" +
    setfSisaCell(totalBudget - totalRealisasi) + "</tr>";
    
  tbody.innerHTML = html + totalRow;
}"""
content = re.sub(target2, replacement2, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

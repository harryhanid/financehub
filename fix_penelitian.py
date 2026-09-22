import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Kategori Table
target_table = r'let tunjangan = kategoriRows\.find\(k => k\.cat1 === "By Tunjangan"\);\s*let pendidikan = kategoriRows\.find\(k => k\.cat1 === "By Pendidikan"\);\s*if \(tunjangan \|\| pendidikan\) \{'
replacement_table = """let tunjangan = kategoriRows.find(k => k.cat1 === "By Tunjangan");
    let pendidikan = kategoriRows.find(k => k.cat1 === "By Pendidikan");
    let penelitian = kategoriRows.find(k => k.cat1 === "By Penelitian");
    
    if (tunjangan || pendidikan || penelitian) {"""
content = re.sub(target_table, replacement_table, content)

target_table_2 = r'if \(pendidikan\) \{\s*penBgt \+= pendidikan\.budget;\s*penAct \+= pendidikan\.realisasi;\s*html \+= "<tr><td>" \+ setfCatBadge\(pendidikan\.cat1\) \+ "</td><td>" \+ setfFmtJutaan\(pendidikan\.budget\) \+ "</td><td>" \+ setfFmtJutaan\(pendidikan\.realisasi\) \+ "</td>" \+ setfSisaCell\(pendidikan\.budget - pendidikan\.realisasi\) \+ "</tr>";\s*\}'
replacement_table_2 = """if (pendidikan) {
            penBgt += pendidikan.budget;
            penAct += pendidikan.realisasi;
            html += "<tr><td>" + setfCatBadge(pendidikan.cat1) + "</td><td>" + setfFmtJutaan(pendidikan.budget) + "</td><td>" + setfFmtJutaan(pendidikan.realisasi) + "</td>" + setfSisaCell(pendidikan.budget - pendidikan.realisasi) + "</tr>";
        }
        if (penelitian) {
            penBgt += penelitian.budget;
            penAct += penelitian.realisasi;
            html += "<tr><td>" + setfCatBadge(penelitian.cat1) + "</td><td>" + setfFmtJutaan(penelitian.budget) + "</td><td>" + setfFmtJutaan(penelitian.realisasi) + "</td>" + setfSisaCell(penelitian.budget - penelitian.realisasi) + "</tr>";
        }"""
content = re.sub(target_table_2, replacement_table_2, content)

# 2. breakdown fetch
target_fetch = r'if \(k\.cat1 === "By Pendidikan" \|\| k\.cat1 === "By Tunjangan"\) return \["Pendidikan", k\.cat1\];'
replacement_fetch = 'if (k.cat1 === "By Pendidikan" || k.cat1 === "By Tunjangan" || k.cat1 === "By Penelitian") return ["Pendidikan", k.cat1];'
content = re.sub(target_fetch, replacement_fetch, content)

# 3. setfRenderTahunanKategori
target_tahunan_1 = r'if \(k\.name === "By Pendidikan" \|\| k\.name === "By Tunjangan"\) \{'
replacement_tahunan_1 = 'if (k.name === "By Pendidikan" || k.name === "By Tunjangan" || k.name === "By Penelitian") {'
content = re.sub(target_tahunan_1, replacement_tahunan_1, content)

target_tahunan_2 = r'let tunjangan = yearly\.kategori\.find\(k => k\.name === "By Tunjangan"\);\s*let pendidikan = yearly\.kategori\.find\(k => k\.name === "By Pendidikan"\);\s*let medical = yearly\.kategori\.find\(k => k\.name === "By Medical"\);\s*// PENDIDIKAN GROUP\s*if \(tunjangan \|\| pendidikan\) \{'
replacement_tahunan_2 = """let tunjangan = yearly.kategori.find(k => k.name === "By Tunjangan");
      let pendidikan = yearly.kategori.find(k => k.name === "By Pendidikan");
      let penelitian = yearly.kategori.find(k => k.name === "By Penelitian");
      let medical = yearly.kategori.find(k => k.name === "By Medical");
      
      // PENDIDIKAN GROUP
      if (tunjangan || pendidikan || penelitian) {"""
content = re.sub(target_tahunan_2, replacement_tahunan_2, content)

target_tahunan_3 = r'if \(tunjangan\) sortedKategori\.push\(tunjangan\);\s*if \(pendidikan\) sortedKategori\.push\(pendidikan\);'
replacement_tahunan_3 = """if (tunjangan) sortedKategori.push(tunjangan);
          if (pendidikan) sortedKategori.push(pendidikan);
          if (penelitian) sortedKategori.push(penelitian);"""
content = re.sub(target_tahunan_3, replacement_tahunan_3, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

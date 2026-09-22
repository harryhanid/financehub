import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderTahunanKategori\(yearly\) \{.*?setfRenderTotalTable\("setf-tahunan-kategori-table", yearly\.kategori, yearly\.years, katMode\);\n\}'

replacement = """function setfRenderTahunanKategori(yearly) {
    if (!yearly || !yearly.years || !yearly.years.length) {
      if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
      setfRenderTotalTable("setf-tahunan-kategori-table", [], []);
      return;
    }
    let katMode = "all";
    const selectedKat = document.querySelector('input[name="setf-tahunan-kat-mode"]:checked');
    if (selectedKat) katMode = selectedKat.value;

    let penBgt = yearly.years.map(() => 0);
    let penAct = yearly.years.map(() => 0);
    let medBgt = yearly.years.map(() => 0);
    let medAct = yearly.years.map(() => 0);

    yearly.kategori.forEach(k => {
        if (k.name === "By Pendidikan" || k.name === "By Tunjangan") {
            for(let i=0; i<yearly.years.length; i++) {
                penBgt[i] += k.budget[i] || 0;
                penAct[i] += k.realisasi[i] || 0;
            }
        } else if (k.name === "By Medical") {
            for(let i=0; i<yearly.years.length; i++) {
                medBgt[i] += k.budget[i] || 0;
                medAct[i] += k.realisasi[i] || 0;
            }
        }
    });

    let chartKategori = [
        { name: "By Medical", budget: medBgt, realisasi: medAct },
        { name: "By Pendidikan", budget: penBgt, realisasi: penAct }
    ];

    setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, chartKategori, katMode);
    
    // Sort kategori for table: Tunjangan, Pendidikan, Medical
    let sortedKategori = [];
    let tunjangan = yearly.kategori.find(k => k.name === "By Tunjangan");
    let pendidikan = yearly.kategori.find(k => k.name === "By Pendidikan");
    let medical = yearly.kategori.find(k => k.name === "By Medical");
    
    if (tunjangan) sortedKategori.push(tunjangan);
    if (pendidikan) sortedKategori.push(pendidikan);
    
    // Add Sub Total Pendidikan if we have either
    if (tunjangan || pendidikan) {
        sortedKategori.push({
            name: "Sub Total Pendidikan",
            isSubTotal: true,
            budget: penBgt,
            realisasi: penAct
        });
    }
    
    if (medical) sortedKategori.push(medical);

    setfRenderTotalTable("setf-tahunan-kategori-table", sortedKategori, yearly.years, katMode);
}"""

content = re.sub(target, replacement, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const pairs = \[\s*\{\s*title: "Budget vs Actual per Kategori"[\s\S]*?const opt = \{'

replacement = """const pairs = [
        { title: "Budget vs Actual per Kategori", chart: "chart-kategori", table: "setf-kategori-table" },
        { title: "Budget vs Actual per Pillar", chart: "chart-pillar", table: "setf-pillar-table" },
        { title: "Trend per Tahun per Kategori", chart: "chart-tahunan-kategori", table: "setf-tahunan-kategori-table" },
        { title: "Trend per Tahun per Pillar", chart: "chart-tahunan-pillar", table: "setf-tahunan-pillar-table" },
        { title: "Budget vs Actual per Sahabat", chart: "chart-keluarga", table: "setf-family-table" }
    ];

    pairs.forEach((pair, idx) => {
        // --- PAGE 1: CHART ---
        const chartPage = document.createElement("div");
        chartPage.style.width = "1122px";
        chartPage.style.height = "790px";
        chartPage.style.padding = "40px";
        chartPage.style.boxSizing = "border-box";
        chartPage.style.display = "flex";
        chartPage.style.flexDirection = "column";
        chartPage.style.background = bgColor;
        chartPage.style.color = textColor;
        
        // Always break after chart page to go to table page
        chartPage.classList.add("html2pdf__page-break");

        const chartTitle = document.createElement("h2");
        chartTitle.innerText = pair.title + " (Grafik)";
        chartTitle.style.margin = "0 0 30px 0";
        chartTitle.style.fontFamily = "sans-serif";
        chartTitle.style.fontSize = "26px";
        chartTitle.style.textAlign = "center";
        chartPage.appendChild(chartTitle);

        const chartContent = document.createElement("div");
        chartContent.style.flex = "1";
        chartContent.style.display = "flex";
        chartContent.style.alignItems = "center";
        chartContent.style.justifyContent = "center";

        if (setfCharts[pair.chart]) {
            const img = document.createElement("img");
            img.src = setfCharts[pair.chart].toBase64Image();
            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            chartContent.appendChild(img);
        }
        chartPage.appendChild(chartContent);
        container.appendChild(chartPage);


        // --- PAGE 2: TABLE ---
        const tablePage = document.createElement("div");
        tablePage.style.width = "1122px";
        tablePage.style.height = "790px";
        tablePage.style.padding = "40px";
        tablePage.style.boxSizing = "border-box";
        tablePage.style.display = "flex";
        tablePage.style.flexDirection = "column";
        tablePage.style.background = bgColor;
        tablePage.style.color = textColor;
        
        if (idx < pairs.length - 1) {
            tablePage.classList.add("html2pdf__page-break");
        }

        const tableTitle = document.createElement("h2");
        tableTitle.innerText = pair.title + " (Data Tabel)";
        tableTitle.style.margin = "0 0 30px 0";
        tableTitle.style.fontFamily = "sans-serif";
        tableTitle.style.fontSize = "26px";
        tableTitle.style.textAlign = "center";
        tablePage.appendChild(tableTitle);

        const tableContent = document.createElement("div");
        tableContent.style.flex = "1";
        tableContent.style.display = "flex";
        tableContent.style.alignItems = "center";
        tableContent.style.justifyContent = "center";
        
        // Wrap table in a div to allow it to be naturally sized
        const tableWrapper = document.createElement("div");
        tableWrapper.style.maxWidth = "100%";
        tableWrapper.style.maxHeight = "100%";
        tableWrapper.style.overflow = "hidden"; // Fallback

        const originalTable = document.getElementById(pair.table);
        if (originalTable) {
            const tableClone = originalTable.cloneNode(true);
            tableClone.style.width = "max-content"; // Let it take natural width
            tableClone.style.margin = "0 auto"; // Center horizontally
            tableClone.style.borderCollapse = "collapse";
            tableClone.style.fontSize = "14px"; // Larger font since it has the whole page!
            tableClone.style.fontFamily = "sans-serif";
            
            const cells = tableClone.querySelectorAll("th, td");
            cells.forEach(cell => {
                cell.style.padding = "8px 12px"; // Bigger padding
                cell.style.borderBottom = "1px solid " + borderColor;
                cell.style.color = textColor;
                if (cell.tagName === "TH") {
                    cell.style.textAlign = "left";
                    cell.style.fontWeight = "bold";
                    cell.style.background = isDark ? "#1e293b" : "#f8fafc";
                }
            });
            
            tableWrapper.appendChild(tableClone);
        }
        
        tableContent.appendChild(tableWrapper);
        tablePage.appendChild(tableContent);
        container.appendChild(tablePage);
    });

    const opt = {"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

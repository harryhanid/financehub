import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfExportPdf\(\) \{[\s\S]*?requestAnimationFrame\(function \(\) \{[\s\S]*?window\.print\(\);[\s\S]*?\}\);\s*\}\);\s*\}'
replacement = """async function setfExportPdf() {
    showToast("Mempersiapkan PDF... Mohon tunggu.", "info");

    if (typeof html2pdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.left = "-9999px";
    container.style.top = "-9999px";
    container.style.width = "1122px";
    container.style.background = "#ffffff";
    document.body.appendChild(container);

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#1e293b";
    const bgColor = isDark ? "#0f172a" : "#ffffff";
    const borderColor = isDark ? "#334155" : "#e2e8f0";

    const pairs = [
        { title: "Budget vs Actual per Kategori", chart: "chart-kategori", table: "setf-kategori-table" },
        { title: "Budget vs Actual per Pillar", chart: "chart-pillar", table: "setf-pillar-table" },
        { title: "Trend per Tahun per Kategori", chart: "chart-tahunan-kategori", table: "setf-tahunan-kategori-table" },
        { title: "Trend per Tahun per Pillar", chart: "chart-tahunan-pillar", table: "setf-tahunan-pillar-table" },
        { title: "Budget vs Actual per Sahabat", chart: "chart-keluarga", table: "setf-family-table" }
    ];

    pairs.forEach((pair, idx) => {
        const page = document.createElement("div");
        page.style.width = "1122px";
        page.style.height = "790px";
        page.style.padding = "40px";
        page.style.boxSizing = "border-box";
        page.style.display = "flex";
        page.style.flexDirection = "column";
        page.style.background = bgColor;
        page.style.color = textColor;
        
        if (idx < pairs.length - 1) {
            page.style.pageBreakAfter = "always";
        }

        const title = document.createElement("h2");
        title.innerText = pair.title;
        title.style.margin = "0 0 20px 0";
        title.style.fontFamily = "sans-serif";
        title.style.fontSize = "24px";
        page.appendChild(title);

        const content = document.createElement("div");
        content.style.display = "flex";
        content.style.flex = "1";
        content.style.gap = "20px";

        const chartSide = document.createElement("div");
        chartSide.style.flex = "0 0 73%";
        chartSide.style.display = "flex";
        chartSide.style.alignItems = "center";
        chartSide.style.justifyContent = "center";

        if (setfCharts[pair.chart]) {
            const img = document.createElement("img");
            img.src = setfCharts[pair.chart].toBase64Image();
            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            chartSide.appendChild(img);
        }

        const tableSide = document.createElement("div");
        tableSide.style.flex = "0 0 25%";
        tableSide.style.overflow = "hidden";

        const originalTable = document.getElementById(pair.table);
        if (originalTable) {
            const tableClone = originalTable.cloneNode(true);
            tableClone.style.width = "100%";
            tableClone.style.borderCollapse = "collapse";
            tableClone.style.fontSize = "11px";
            tableClone.style.fontFamily = "sans-serif";
            
            const cells = tableClone.querySelectorAll("th, td");
            cells.forEach(cell => {
                cell.style.padding = "6px";
                cell.style.borderBottom = "1px solid " + borderColor;
                cell.style.color = textColor;
                if (cell.tagName === "TH") {
                    cell.style.textAlign = "left";
                    cell.style.fontWeight = "bold";
                    cell.style.background = isDark ? "#1e293b" : "#f8fafc";
                }
            });
            
            tableSide.appendChild(tableClone);
        }

        content.appendChild(chartSide);
        content.appendChild(tableSide);
        page.appendChild(content);
        container.appendChild(page);
    });

    const opt = {
        margin:       0,
        filename:     'Sahabat_ETF_Dashboard.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false },
        jsPDF:        { unit: 'pt', format: 'a4', orientation: 'landscape' }
    };

    html2pdf().set(opt).from(container).save().then(() => {
        document.body.removeChild(container);
        showToast("PDF berhasil diunduh!", "success");
    }).catch(err => {
        console.error(err);
        document.body.removeChild(container);
        showToast("Terjadi kesalahan saat membuat PDF.", "error");
    });
}"""

if re.search(target, content):
    content = re.sub(target, replacement, content)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("REPLACED")
else:
    print("NOT FOUND")

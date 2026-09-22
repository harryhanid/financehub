file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """function setfExportPdf() {
  const accordions = document.querySelectorAll(".setf-accordion");
  const prevState = Array.from(accordions).map(function (d) { return d.open; });
  accordions.forEach(function (d) { d.open = true; });

  function resizeCharts() {
    Object.keys(setfCharts).forEach(function (key) {
      if (setfCharts[key]) setfCharts[key].resize();
    });
  }
  function onBeforePrint() { resizeCharts(); }
  function restore() {
    accordions.forEach(function (d, i) { d.open = prevState[i]; });
    window.removeEventListener("beforeprint", onBeforePrint);
    window.removeEventListener("afterprint", restore);
  }
  window.addEventListener("beforeprint", onBeforePrint);
  window.addEventListener("afterprint", restore);

  // Let the DOM reflow after opening the accordions (which can change chart
  // container widths) before charts resize and the print snapshot is taken.
  resizeCharts();
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      resizeCharts();
      window.print();
    });
  });
}"""

repl = """async function setfExportPdf() {
    // Tampilkan toast loading
    showToast("Mempersiapkan PDF... Mohon tunggu.", "info");

    // Load html2pdf dynamically
    if (typeof html2pdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // Buat container tersembunyi
    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.left = "-9999px";
    container.style.top = "-9999px";
    container.style.width = "1122px"; // A4 landscape width approx
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
        
        // Agar ada page break kecuali di elemen terakhir
        if (idx < pairs.length - 1) {
            page.style.pageBreakAfter = "always";
        }

        const title = document.createElement("h2");
        title.innerText = pair.title;
        title.style.margin = "0 0 20px 0";
        title.style.fontFamily = "sans-serif";
        title.style.fontSize = "24px";
        page.appendChild(title);

        const contentDiv = document.createElement("div");
        contentDiv.style.display = "flex";
        contentDiv.style.flex = "1";
        contentDiv.style.gap = "20px";

        // Chart side (75%)
        const chartSide = document.createElement("div");
        chartSide.style.flex = "0 0 73%";
        chartSide.style.display = "flex";
        chartSide.style.alignItems = "center";
        chartSide.style.justifyContent = "center";

        if (setfCharts[pair.chart]) {
            const chart = setfCharts[pair.chart];
            const parent = chart.canvas.parentNode;
            
            // Backup original state
            const origWidth = parent.style.width;
            const origHeight = parent.style.height;
            const origPos = parent.style.position;
            const origMaxWidth = parent.style.maxWidth;
            const origAspectRatio = chart.options.maintainAspectRatio;
            const origPixelRatio = chart.options.devicePixelRatio;
            const origAnimation = chart.options.animation;

            // Virtual layout configuration (scaling strategy)
            parent.style.position = "absolute";
            parent.style.maxWidth = "none";
            parent.style.width = "850px"; 
            parent.style.height = "500px";
            chart.options.maintainAspectRatio = false;
            chart.options.devicePixelRatio = 3; 
            chart.options.animation = false;
            
            // Apply layout changes SYNCHRONOUSLY
            chart.resize();
            chart.update('none');
            
            const img = document.createElement("img");
            img.src = chart.toBase64Image();
            
            // Restore original state
            parent.style.position = origPos;
            parent.style.maxWidth = origMaxWidth;
            parent.style.width = origWidth;
            parent.style.height = origHeight;
            chart.options.maintainAspectRatio = origAspectRatio !== undefined ? origAspectRatio : true;
            chart.options.devicePixelRatio = origPixelRatio || window.devicePixelRatio;
            chart.options.animation = origAnimation;
            
            // Apply original state SYNCHRONOUSLY
            chart.resize();
            chart.update('none');

            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            chartSide.appendChild(img);
        }

        // Table side (25%)
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
            
            // Format sel clone
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

        contentDiv.appendChild(chartSide);
        contentDiv.appendChild(tableSide);
        page.appendChild(contentDiv);
        container.appendChild(page);
    });

    // Opsi html2pdf
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

if target in content:
    new_content = content.replace(target, repl)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Replaced setfExportPdf perfectly!")
else:
    print("Target not found! Wait, maybe line endings are \r\n?")
    import re
    target_regex = re.escape(target).replace(r'\n', r'\r?\n')
    new_content = re.sub(target_regex, repl, content)
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Replaced using regex perfectly!")
    else:
        print("Target REALLY not found!")

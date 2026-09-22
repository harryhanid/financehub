import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const chartSide = document\.createElement\("div"\);[\s\S]*?tableSide\.appendChild\(tableClone\);\s*\}'
replacement = """const chartSide = document.createElement("div");
        chartSide.style.flex = "0 0 70%";
        chartSide.style.display = "flex";
        chartSide.style.alignItems = "flex-start"; // Align to top instead of center
        chartSide.style.justifyContent = "center";

        if (setfCharts[pair.chart]) {
            const img = document.createElement("img");
            img.src = setfCharts[pair.chart].toBase64Image();
            img.style.maxWidth = "100%";
            // Don't restrict maxHeight too much, let it scale naturally
            img.style.objectFit = "contain"; 
            chartSide.appendChild(img);
        }

        const tableSide = document.createElement("div");
        tableSide.style.flex = "0 0 28%";
        tableSide.style.overflow = "hidden"; // Still hide overflow, but we'll scale the contents

        const originalTable = document.getElementById(pair.table);
        if (originalTable) {
            const tableClone = originalTable.cloneNode(true);
            tableClone.style.width = "max-content"; // Allow table to stretch to its natural width
            tableClone.style.borderCollapse = "collapse";
            tableClone.style.fontSize = "10px";
            tableClone.style.fontFamily = "sans-serif";
            
            const cells = tableClone.querySelectorAll("th, td");
            cells.forEach(cell => {
                cell.style.padding = "6px 8px";
                cell.style.borderBottom = "1px solid " + borderColor;
                cell.style.color = textColor;
                if (cell.tagName === "TH") {
                    cell.style.textAlign = "left";
                    cell.style.fontWeight = "bold";
                    cell.style.background = isDark ? "#1e293b" : "#f8fafc";
                }
            });
            
            // Wrap in a scaler div to shrink it into the 28% flex column
            const scaler = document.createElement("div");
            scaler.style.transformOrigin = "top left";
            
            if (pair.table.includes("tahunan")) {
                scaler.style.transform = "scale(0.55)";
                scaler.style.width = "181%"; 
            } else if (pair.table.includes("family")) {
                scaler.style.transform = "scale(0.65)";
                scaler.style.width = "153%";
            } else {
                scaler.style.transform = "scale(0.85)";
                scaler.style.width = "117%";
            }
            
            scaler.appendChild(tableClone);
            tableSide.appendChild(scaler);
        }"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_chart = r'if \(setfCharts\[pair\.chart\]\) \{[\s\S]*?chartContent\.appendChild\(img\);\s*\}'
replacement_chart = """if (setfCharts[pair.chart]) {
            const chart = setfCharts[pair.chart];
            const parent = chart.canvas.parentNode;
            const origHeight = parent.style.height;
            
            // Perbesar height container sementara agar proporsi chart membesar (tidak gepeng)
            parent.style.height = "650px";
            chart.resize();
            
            const img = document.createElement("img");
            img.src = chart.toBase64Image();
            
            // Kembalikan ke ukuran normal di layar
            parent.style.height = origHeight;
            chart.resize();

            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            chartContent.appendChild(img);
        }"""
content = re.sub(target_chart, replacement_chart, content)

target_padding = r'chartPage\.style\.padding = "40px";'
replacement_padding = 'chartPage.style.padding = "10px 20px";'
content = re.sub(target_padding, replacement_padding, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

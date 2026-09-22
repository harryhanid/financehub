import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'scales: \{\n\s*x: \{\n\s*ticks: \{ color: textColor, padding: 16 \},\n\s*grid: \{ display: false \}\n\s*\},'
replacement = """scales: {
                x: {
                    ticks: { 
                        color: textColor, 
                        padding: 16,
                        callback: function(val, idx) {
                            let lbl = this.getLabelForValue(val);
                            if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
                            return lbl;
                        }
                    },
                    grid: { display: false }
                },"""

if re.search(target, content):
    content = re.sub(target, replacement, content)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("REPLACED!")
else:
    print("NOT FOUND!")

import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function initSahabatEtf\(\) \{'
replacement = """function initSahabatEtf() {
    if (typeof pattern === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/patternomaly@1.3.2/dist/patternomaly.min.js';
        script.onload = function() {
            setfApplyFilters();
        };
        document.head.appendChild(script);
        // Don't render immediately, wait for patternomaly
        return;
    }
"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

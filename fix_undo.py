import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r"    if \(typeof pattern === 'undefined'\) \{\n        const script = document\.createElement\('script'\);\n        script\.src = 'https://cdn\.jsdelivr\.net/npm/patternomaly@1\.3\.2/dist/patternomaly\.min\.js';\n        script\.onload = function\(\) \{\n            setfApplyFilters\(\);\n        \};\n        document\.head\.appendChild\(script\);\n        // Don't render immediately, wait for patternomaly\n        return;\n    \}\n"
content = content.replace(target, "")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

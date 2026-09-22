import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const container = document\.createElement\("div"\);[\s\S]*?document\.body\.appendChild\(container\);'
replacement = """const container = document.createElement("div");
    container.style.width = "1122px";
    container.style.background = "#ffffff";
    container.style.padding = "0";
    container.style.margin = "0";"""

content = re.sub(target, replacement, content)

target2 = r'html2pdf\(\)\.set\(opt\)\.from\(container\)\.save\(\)\.then\(\(\) => \{\n\s*document\.body\.removeChild\(container\);'
replacement2 = """html2pdf().set(opt).from(container).save().then(() => {"""
content = re.sub(target2, replacement2, content)

target3 = r'document\.body\.removeChild\(container\);\n\s*showToast\("Terjadi kesalahan saat membuat PDF\.", "error"\);'
replacement3 = """showToast("Terjadi kesalahan saat membuat PDF.", "error");"""
content = re.sub(target3, replacement3, content)

target4 = r'page\.style\.pageBreakAfter = "always";'
replacement4 = """page.classList.add("html2pdf__page-break");"""
content = re.sub(target4, replacement4, content)

target5 = r'jsPDF:\s*\{\s*unit:\s*\'pt\',\s*format:\s*\'a4\',\s*orientation:\s*\'landscape\'\s*\}'
replacement5 = """jsPDF:        { unit: 'pt', format: 'a4', orientation: 'landscape' },
        pagebreak:    { mode: ['css', 'legacy'] }"""
content = re.sub(target5, replacement5, content)

# Wait, the chart images might take time to load because of animation!
# We are using `toBase64Image()`. `toBase64Image()` immediately returns the canvas content.
# But what if the canvas is blank because it hasn't rendered? No, it's already on the screen!

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated!")

import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'datalabels: \{\n\s*display: function\(context\) \{ return context\.dataset\.data\[context\.dataIndex\] > 0; \},\n\s*color: "#ffffff",'
repl = """datalabels: {
                        display: false,
                        color: "#ffffff","""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Disabled inner datalabels in setfRenderStackedGroupedChart!")

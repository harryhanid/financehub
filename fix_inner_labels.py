import re
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'datalabels: \{\n\s*display: function\(context\) \{ return context\.dataset\.data\[context\.dataIndex\] > 0; \},\n\s*color: "#ffffff",\n\s*textStrokeColor: "rgba\(0,0,0,0\.6\)",\n\s*textStrokeWidth: 3,\n\s*font: \{ size: 9, weight: "bold" \},\n\s*formatter: function\(val\)?(?:, context)? \{([\s\S]*?return setfFmtJutaan\(val\);\n)\s*\}\n\s*\}'

# The user explicitly asked: "untuk label amount stack yang ada di tengah sepenuhnya di hilangkan saja jadi cuma ada label yang on top"
# Since setfStackTotalPlugin ALREADY draws the label on top, we just need to disable ChartDataLabels!
repl = """datalabels: {
                    display: false
                }"""

new_content = re.sub(target, repl, content)
if new_content != content:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Disabled inner datalabels!")
else:
    print("Failed to replace datalabels!")

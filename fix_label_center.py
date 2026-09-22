import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'for \(let j = 0; j < meta\.data\.length; j\+\+\) \{\n\s*if \(meta\.data\[j\]\) \{\n\s*ctx\.fillText\(lbl, meta\.data\[j\]\.x, yBaseline \+ 4\);\n\s*\}\n\s*\}'

repl = """for (let j = 0; j < meta.data.length; j++) {
                  if (meta.data[j] && dataset.data[j] !== null && dataset.data[j] !== undefined) {
                      ctx.fillText(lbl, meta.data[j].x, yBaseline + 4);
                  }
              }"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated setfGroupedSublabelPlugin to skip nulls!")

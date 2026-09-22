import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Budget Vs Realisasi
target1 = r'ticks: \{ \n\s*color: function\(ctx\) \{\n\s*let lbl = ctx\.chart && ctx\.chart\.data \? ctx\.chart\.data\.labels\[ctx\.index\] : null;\n\s*if \(Array\.isArray\(lbl\)\) return \'transparent\';\n\s*return setfThemeColor\("--text-secondary", "#94a3b8"\);\n\s*\} \}'
replacement1 = """ticks: {
              color: setfThemeColor("--text-secondary", "#94a3b8"),
              callback: function(val, idx) {
                  let lbl = this.getLabelForValue(val);
                  if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
                  return lbl;
              }
            }"""
content = re.sub(target1, replacement1, content)

# 2. Stacked Grouped
target2 = r'ticks: \{ \n\s*color: function\(ctx\) \{\n\s*let lbl = ctx\.chart && ctx\.chart\.data \? ctx\.chart\.data\.labels\[ctx\.index\] : null;\n\s*if \(Array\.isArray\(lbl\)\) return \'transparent\';\n\s*return textColor;\n\s*\}, \n\s*padding: 16 \n\s*\}'
replacement2 = """ticks: {
                            color: textColor,
                            padding: 16,
                            callback: function(val, idx) {
                                let lbl = this.getLabelForValue(val);
                                if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
                                return lbl;
                            }
                        }"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")

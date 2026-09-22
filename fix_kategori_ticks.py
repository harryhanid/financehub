import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'x: \{ ticks: \{ \n\s*color: function\(ctx\) \{\n\s*let lbl = ctx\.chart && ctx\.chart\.data \? ctx\.chart\.data\.labels\[ctx\.index\] : null;\n\s*if \(Array\.isArray\(lbl\)\) return \'transparent\';\n\s*return setfThemeColor\("--text-secondary", "#94a3b8"\);\n\s*\} \n\s*\}, grid: \{ color: "rgba\(148,163,184,0\.1\)" \} \},'

replacement = """x: { 
            ticks: {
              color: setfThemeColor("--text-secondary", "#94a3b8"),
              callback: function(val, idx) {
                  let lbl = this.getLabelForValue(val);
                  if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
                  return lbl;
              }
            }, 
            grid: { color: "rgba(148,163,184,0.1)" } 
          },"""

if re.search(target, content):
    content = re.sub(target, replacement, content)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("REPLACED!")
else:
    print("NOT FOUND!")

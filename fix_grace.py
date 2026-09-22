import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace suggestedMax logic with grace
target = r'if \(scales\.y && !scales\.y\.suggestedMax\) \{\n\s*scales\.y\.suggestedMax = maxLeft \* 1\.4;\n\s*\}\n\s*scales\["y-right"\]\.suggestedMax = maxRight \* 1\.25;'

repl = """if (scales.y) {
      scales.y.grace = '35%';
  }
  scales["y-right"].grace = '25%';"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated to use grace instead of suggestedMax!")

import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'    activeItems\.forEach\(function\(item\) \{'
replacement = """    const shapes = ['diagonal', 'weave', 'dot', 'square', 'zigzag', 'triangle', 'cross'];
    activeItems.forEach(function(item, idx) {
         let shape = shapes[idx % shapes.length];"""

content = re.sub(target, replacement, content)

target2 = r'                 backgroundColor: color,'
replacement2 = '                 backgroundColor: typeof pattern !== "undefined" ? pattern.draw(shape, color) : color,'

content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

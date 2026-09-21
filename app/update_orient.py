import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# Replace orient, top/left, label position
old_config = """        type: 'tree',
        data: data,
        top: '1%', left: '7%', bottom: '1%', right: '20%',
        symbolSize: 7,
        initialTreeDepth: 2,
        roam: true,
        label: {
          position: 'left',
          verticalAlign: 'middle',
          align: 'right',"""

new_config = """        type: 'tree',
        orient: 'TB',
        data: data,
        top: '10%', left: '1%', bottom: '20%', right: '1%',
        symbolSize: 7,
        initialTreeDepth: 2,
        roam: true,
        label: {
          position: 'top',
          verticalAlign: 'middle',
          align: 'center',"""

content = content.replace(old_config, new_config)

# Replace leaves position
old_leaves = """leaves: { label: { position: 'right', verticalAlign: 'middle', align: 'left' } },"""
new_leaves = """leaves: { label: { position: 'bottom', verticalAlign: 'middle', align: 'center' } },"""

content = content.replace(old_leaves, new_leaves)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated orient to TB!")

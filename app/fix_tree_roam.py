import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_config = """        orient: 'TB',
        data: data,
        top: '10%', left: '1%', bottom: '20%', right: '1%',"""

new_config = """        orient: 'TB',
        data: data,
        top: 80, left: 20, bottom: 80, right: 20,"""

if old_config in content:
    content = content.replace(old_config, new_config)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated tree layout values to absolute pixels!")
else:
    print("Could not find the tree layout config!")

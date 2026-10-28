import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_label = """            let n = params.data.name || '';
            let lastCode = params.data.id ? params.data.id.split('.').pop() : '';
            if (lastCode && lastCode !== 'A' && lastCode !== 'B') {
                n = n + ' (' + lastCode + ')';
            }"""

new_label = """            let n = params.data.name || '';
            let fullCode = params.data.id ? params.data.id : '';
            if (fullCode && fullCode !== 'A' && fullCode !== 'B') {
                n = n + ' (' + fullCode + ')';
            }"""

if old_label in content:
    content = content.replace(old_label, new_label)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed bloodline node code formatter successfully!")
else:
    print("Could not find old label logic!")

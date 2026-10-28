import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the reqW and reqH calculation
old_req = """    let reqW = leaves * 140 * (window.treeSpacingMultiplier || 1.0);
    let reqH = (maxDepth + 1) * 450 * (window.treeSpacingMultiplier || 1.0);"""
new_req = """    let reqW = leaves * 250 * (window.treeSpacingMultiplier || 1.0) * (window.textZoomMultiplier || 1.0);
    let reqH = (maxDepth + 1) * 450 * (window.treeSpacingMultiplier || 1.0) * (window.textZoomMultiplier || 1.0);"""

if old_req in content:
    content = content.replace(old_req, new_req)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Injected textZoomMultiplier into dimension calculations!")
else:
    print("Could not find reqW/reqH block!")

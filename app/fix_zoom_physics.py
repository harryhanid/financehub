import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_req = """    let reqW = leaves * 250 * (window.treeSpacingMultiplier || 1.0) * (window.textZoomMultiplier || 1.0);
    let reqH = (maxDepth + 1) * 450 * (window.treeSpacingMultiplier || 1.0) * (window.textZoomMultiplier || 1.0);"""

new_req = """    let tz = window.textZoomMultiplier || 1.0;
    let ts = window.treeSpacingMultiplier || 1.0;
    // Box is ~160px at tz=1.0. Fixed 90px horizontal whitespace.
    let reqW = leaves * (160 * tz + 90) * ts;
    // Vertical distance fixed at 450px base, completely unaffected by text zoom
    let reqH = (maxDepth + 1) * 450 * ts;"""

if old_req in content:
    content = content.replace(old_req, new_req)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Injected perfect visual physics for text zoom!")
else:
    print("Could not find the reqW block!")

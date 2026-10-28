import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_req = """    let tz = window.textZoomMultiplier || 1.0;
    let ts = window.treeSpacingMultiplier || 1.0;
    // Box is ~160px at tz=1.0. Fixed 90px horizontal whitespace.
    let reqW = leaves * (260 * tz + 120 * ts);
    // Vertical distance fixed at 450px base, completely unaffected by text zoom
    let reqH = (maxDepth + 1) * (160 * tz + 290 * ts);"""

new_req = """    let tz = window.textZoomMultiplier || 1.0;
    let ts = window.treeSpacingMultiplier || 1.0;
    
    // Fully flexible proportional formula. Default 250px prevents overlap.
    // ts can aggressively compress everything to 0 if desired (free & flexible).
    let reqW = leaves * 250 * tz * ts;
    // Vertical is immune to text zoom (so zooming text only widens diagram horizontally, keeping vertical lines stable)
    let reqH = (maxDepth + 1) * 450 * ts;"""

if old_req in content:
    content = content.replace(old_req, new_req)
    
    # Also restore min spacing to 0.1 to allow extreme compression
    content = content.replace(
        "if (window.treeSpacingMultiplier < 0.0) window.treeSpacingMultiplier = 0.0;",
        "if (window.treeSpacingMultiplier < 0.1) window.treeSpacingMultiplier = 0.1;"
    )
    
    # And allow extreme text zooming
    content = content.replace(
        "if (window.textZoomMultiplier < 0.4) window.textZoomMultiplier = 0.4;",
        "if (window.textZoomMultiplier < 0.2) window.textZoomMultiplier = 0.2;"
    )
    content = content.replace(
        "if (window.textZoomMultiplier > 3.0) window.textZoomMultiplier = 3.0;",
        "if (window.textZoomMultiplier > 5.0) window.textZoomMultiplier = 5.0;"
    )
    
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Reverted to fully flexible proportional physics!")
else:
    print("Could not find the reqW block!")

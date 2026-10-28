import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_req = """    let tz = window.textZoomMultiplier || 1.0;
    let ts = window.treeSpacingMultiplier || 1.0;
    
    // Fully flexible proportional formula. Default 250px prevents overlap.
    // ts can aggressively compress everything to 0 if desired (free & flexible).
    let reqW = leaves * 250 * tz * ts;
    // Vertical is immune to text zoom (so zooming text only widens diagram horizontally, keeping vertical lines stable)
    let reqH = (maxDepth + 1) * 450 * ts;"""

new_req = """    let tz = window.textZoomMultiplier || 1.0;
    let ts = window.treeSpacingMultiplier || 1.0;
    
    // Smart Positioning Safety Net:
    // 1. Box width is ~160px at tz=1.0. We enforce a hard floor of 170px to guarantee no overlap.
    let minReqW = leaves * 170 * tz;
    let userReqW = leaves * 250 * tz * ts;
    let reqW = Math.max(minReqW, userReqW);
    
    // 2. Box height is ~120px at tz=1.0. We enforce a hard floor of 140px.
    // Vertical spacing (userReqH) ignores text zoom to maintain layout shape, unless the text grows so large it risks overlapping.
    let minReqH = (maxDepth + 1) * 140 * tz;
    let userReqH = (maxDepth + 1) * 450 * ts;
    let reqH = Math.max(minReqH, userReqH);"""

if old_req in content:
    content = content.replace(old_req, new_req)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Injected Smart Positioning Safety Nets!")
else:
    print("Could not find the reqW block!")

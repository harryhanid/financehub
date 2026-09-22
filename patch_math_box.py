import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# First replace beforeDraw with beforeDatasetsDraw
js_content = js_content.replace('beforeDraw: (chart) => {', 'beforeDatasetsDraw: (chart) => {')

bad_meta_code = """        const lastIndex = labels.length - 1;
        const metaBgt = chart.getDatasetMeta(2); // Budget (Total)
        const metaAct = chart.getDatasetMeta(3); // Actual (Total)
        
        let leftX = 0;
        let rightX = chart.chartArea.right;
        
        try {
            if (metaBgt.data[lastIndex] && metaAct.data[lastIndex]) {
                const bgtX = metaBgt.data[lastIndex].x;
                const actX = metaAct.data[lastIndex].x;
                
                // Assuming the bars are centered around the category tick
                // We'll give it a nice padding
                const barDistance = Math.abs(actX - bgtX);
                const padding = barDistance; 
                
                leftX = Math.min(bgtX, actX) - padding;
                // rightX = Math.max(bgtX, actX) + padding; // Or just to the edge:
                rightX = chart.chartArea.right; 
            } else {
                return; // cannot draw box
            }
        } catch (e) {
            console.error("Total Box Plugin Error:", e);
            return;
        }"""

good_math_code = """        if (!labels || labels.length === 0) return;
        
        // Mathematical absolute calculation for the last column (TOTAL)
        const tickWidth = (chart.chartArea.right - chart.chartArea.left) / labels.length;
        const leftX = chart.chartArea.right - tickWidth;
        const rightX = chart.chartArea.right;"""

if bad_meta_code in js_content:
    js_content = js_content.replace(bad_meta_code, good_math_code)
else:
    print("Could not find bad meta code!")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Math Box patched")

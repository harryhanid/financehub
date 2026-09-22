import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

bad_box = """        const lastIndex = labels.length - 1;
        // get bounding box for the TOTAL category
        const tickWidth = xAxis.getPixelForTick(1) - xAxis.getPixelForTick(0);
        const center = xAxis.getPixelForTick(lastIndex);
        const leftX = center - tickWidth/2;
        const rightX = center + tickWidth/2;"""

good_box = """        const lastIndex = labels.length - 1;
        let leftX = 0;
        let rightX = chart.chartArea.right;
        
        if (lastIndex > 0) {
            const center = xAxis.getPixelForValue(lastIndex);
            const prevCenter = xAxis.getPixelForValue(lastIndex - 1);
            const tickWidth = center - prevCenter;
            leftX = center - tickWidth/2;
            rightX = chart.chartArea.right; // span to the very edge
        } else {
            leftX = chart.chartArea.left;
        }"""

js_content = js_content.replace(bad_box, good_box)

# Also ensure strokeStyle is visible. "#cbd5e1" is light grey.
# Maybe the user can't see it because it's too light?
# Let's change it to "#94a3b8" (darker grey) to make it more visible.
js_content = js_content.replace('ctx.strokeStyle = setfThemeColor("--border-color", "#cbd5e1");', 'ctx.strokeStyle = setfThemeColor("--border-color", "#94a3b8");')

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Box patched")

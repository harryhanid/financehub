import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

bad_box_code = """        const lastIndex = labels.length - 1;
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
        }
        
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = setfThemeColor("--border-color", "#94a3b8");
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        // draw slightly gray background for total box
        ctx.fillStyle = "rgba(241, 245, 249, 0.3)";
        ctx.fill();
        ctx.restore();"""

good_box_code = """        const lastIndex = labels.length - 1;
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
        }
        
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = setfThemeColor("--border-color", "#94a3b8");
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        ctx.fillStyle = "rgba(241, 245, 249, 0.3)";
        ctx.fill();
        ctx.restore();"""

if bad_box_code in js_content:
    js_content = js_content.replace(bad_box_code, good_box_code)
else:
    print("WARNING: Could not find bad box code")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Meta Box patched")

import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Define the setfTotalZonePlugin
plugin_code = """
const setfTotalZonePlugin = {
    id: 'totalZonePlugin',
    beforeDraw: function(chart) {
        const labels = chart.data.labels;
        if (!labels || labels[labels.length - 1] !== "TOTAL") return;

        const ctx = chart.ctx;
        const yRight = chart.scales['y-right'];
        if (!yRight) return;

        let meta = null;
        for (let i = 0; i < chart.data.datasets.length; i++) {
            meta = chart.getDatasetMeta(i);
            if (!meta.hidden && meta.data && meta.data.length > 0) break;
        }
        if (!meta) return;

        const lastData = meta.data[meta.data.length - 1];
        if (!lastData) return;

        const prevData = meta.data[meta.data.length - 2];
        const halfWidth = prevData ? (lastData.x - prevData.x) / 2 : 40;

        const xLeft = lastData.x - halfWidth + 10; // Give a little padding
        const xRight = chart.width - 5;
        const yTop = chart.chartArea.top - 20;
        const yBottom = chart.height - 5;

        ctx.save();
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        
        // Faint background
        ctx.fillStyle = isDark ? "rgba(255, 255, 255, 0.03)" : "rgba(0, 0, 0, 0.03)";
        ctx.fillRect(xLeft, yTop, xRight - xLeft, yBottom - yTop);

        // Dashed border
        ctx.setLineDash([6, 6]);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = isDark ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.2)";
        ctx.strokeRect(xLeft, yTop, xRight - xLeft, yBottom - yTop);

        ctx.restore();
    }
};
"""

if "const setfTotalZonePlugin" not in content:
    # Insert it right before setfStackTotalPlugin
    content = content.replace("const setfStackTotalPlugin = {", plugin_code + "\nconst setfStackTotalPlugin = {")
    
    # Add to plugins array in setfRenderStackedGroupedChart
    target_plugins = r'plugins: \[ChartDataLabels, setfStackTotalPlugin\],'
    repl_plugins = "plugins: [ChartDataLabels, setfStackTotalPlugin, setfTotalZonePlugin],"
    content = re.sub(target_plugins, repl_plugins, content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added setfTotalZonePlugin!")
else:
    print("Plugin already exists!")

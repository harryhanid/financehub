import os
import subprocess

plugins = """
const setfStackTotalPlugin = {
  id: "setfStackTotal",
  afterDatasetsDraw: function (chart) {
    const totals = {};
    chart.data.datasets.forEach(function (ds) {
      if (!ds.hidden) {
        ds.data.forEach(function (v, i) { totals[i] = (totals[i] || 0) + (v || 0); });
      }
    });
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data.length) return;
    const ctx = chart.ctx;
    const yScale = chart.scales.y;
    ctx.save();
    ctx.font = "bold 10px sans-serif";
    ctx.fillStyle = setfThemeColor("--text-primary", "#e2e8f0");
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    meta.data.forEach(function (bar, i) {
      const total = totals[i] || 0;
      if (!total) return;
      ctx.fillText(setfFmtJutaan(total), bar.x, yScale.getPixelForValue(total) - 4);
    });
    ctx.restore();
  }
};

const setfTotalZonePlugin = {
  id: 'totalZone',
  beforeDraw: function(chart) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const ctx = chart.ctx;
    const xAxis = chart.scales.x;
    const yAxisRight = chart.scales['y-right'];
    if (!xAxis || !yAxisRight) return;
    
    let totalIndex = -1;
    xAxis.getTicks().forEach((tick, i) => {
       if (tick.label === "TOTAL") totalIndex = i;
    });
    if (totalIndex === -1) return;
    
    const leftX = totalIndex === 0 ? xAxis.left : (xAxis.getPixelForTick(totalIndex - 1) + xAxis.getPixelForTick(totalIndex)) / 2;
    const rightX = xAxis.right;
    
    const topY = chart.chartArea.top;
    const bottomY = chart.chartArea.bottom;
    
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)";
    ctx.rect(leftX, topY, rightX - leftX, bottomY - topY);
    ctx.stroke();
    
    ctx.fillStyle = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.02)";
    ctx.fill();
    ctx.restore();
  }
};
"""

def restore():
    # 1. Restore file from git
    subprocess.run(["git", "restore", "app/static/js/sahabat_etf.js"], check=True)
    
    # 2. Append plugins at the top
    with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
        f.write(plugins + "\n" + content)
    
    print("Plugins restored.")

    # 3. Run all patches sequentially
    patches = [
        "patch_dashboard2.py",
        "patch_tables.py",
        "patch_thead.py",
        "patch_colspan.py",
        "patch_title.py",
        "patch_kategori_chart.py",
        "patch_box.py",
        "patch_meta_box.py",
        "patch_math_box.py",
        "patch_pillar_chart.py"
    ]
    
    for p in patches:
        if os.path.exists(p):
            print(f"Running {p}...")
            subprocess.run(["python", p], check=True)
        else:
            print(f"WARNING: {p} not found!")

if __name__ == '__main__':
    restore()

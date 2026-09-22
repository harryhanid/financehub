import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the plugin to draw custom labels
target1 = r'              for \(let j = 0; j < meta\.data\.length; j\+\+\) \{\n                  if \(meta\.data\[j\]\) \{\n                      ctx\.fillText\(lbl, meta\.data\[j\]\.x, yBaseline \+ 4\);\n                  \}\n              \}\n          \}\n        \}\);\n        ctx\.restore\(\);\n      \}'

replacement1 = """              for (let j = 0; j < meta.data.length; j++) {
                  if (meta.data[j]) {
                      ctx.fillText(lbl, meta.data[j].x, yBaseline + 4);
                  }
              }
          }
        });
        
        // Draw main labels if they are arrays (to support bold first line)
        const xAxis = chart.scales.x;
        xAxis.ticks.forEach(function(tick, idx) {
            const label = tick.label;
            if (Array.isArray(label) && label.length > 1) {
                const xPos = xAxis.getPixelForTick(idx);
                const yPos = yBaseline + 20; // Just below Bgt/Act
                
                ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
                ctx.font = 'bold 11px sans-serif';
                ctx.fillText(label[0], xPos, yPos);
                
                ctx.font = '11px sans-serif';
                ctx.fillText(label[1], xPos, yPos + 14);
            }
        });
        
        ctx.restore();
      }"""
content = re.sub(target1, replacement1, content)

# 2. Hide default labels ONLY for arrays in setfRenderBudgetVsRealisasiChart
target2 = r'x: \{ ticks: \{ color: setfThemeColor\("--text-secondary", "#94a3b8"\) \}, grid: \{ color: "rgba\(148,163,184,0\.1\)" \} \},'
replacement2 = """x: { ticks: { 
            color: function(ctx) {
                if (ctx.tick && Array.isArray(ctx.tick.label)) return 'transparent';
                return setfThemeColor("--text-secondary", "#94a3b8");
            } 
          }, grid: { color: "rgba(148,163,184,0.1)" } },"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

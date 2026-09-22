import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """           ctx.fillText(lbl, anyMeta.x, yBaseline + 4);
        }
      }
    }
    ctx.restore();
  }
};"""

replacement = """           ctx.fillText(lbl, anyMeta.x, yBaseline + 4);
        }
      }
    }
    
    // Draw main labels if they are arrays (to support bold first line)
    const xAxis = chart.scales.x;
    if (xAxis && xAxis.ticks) {
        xAxis.ticks.forEach(function(tick, idx) {
            const label = tick.label;
            if (Array.isArray(label) && label.length > 1) {
                const xPos = xAxis.getPixelForTick(idx);
                const yPos = yBaseline + 20;
                
                ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                
                ctx.font = 'bold 11px sans-serif';
                ctx.fillText(label[0], xPos, yPos);
                
                ctx.font = '11px sans-serif';
                ctx.fillText(label[1], xPos, yPos + 14);
            }
        });
    }
    
    ctx.restore();
  }
};"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("REPLACED!")
else:
    print("NOT FOUND!")

import os
path = r'C:\Financehub\app\static\js\sahabat_etf.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('ctx.strokeStyle = setfThemeColor("--border-color", "#94a3b8");', 'ctx.strokeStyle = "rgba(255, 205, 86, 1)";')
content = content.replace('ctx.fillStyle = "rgba(241, 245, 249, 0.3)";', 'ctx.fillStyle = "rgba(255, 205, 86, 0.2)";')

content = content.replace('ctx.strokeStyle = isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)";', 'ctx.strokeStyle = "rgba(255, 205, 86, 1)";')
content = content.replace('ctx.fillStyle = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.02)";', 'ctx.fillStyle = "rgba(255, 205, 86, 0.2)";')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')

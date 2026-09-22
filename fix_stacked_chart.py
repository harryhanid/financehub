import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'x: \{\n\s*stacked: true,\n\s*ticks: \{ color: textColor, padding: 16 \}'
replacement = """x: {
                      stacked: true,
                      ticks: { 
                          color: function(ctx) {
                              if (ctx.tick && Array.isArray(ctx.tick.label)) return 'transparent';
                              return textColor;
                          }, 
                          padding: 16 
                      }"""
content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

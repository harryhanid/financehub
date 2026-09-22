import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = r'color: function\(ctx\) \{\n\s*if \(ctx\.tick && Array\.isArray\(ctx\.tick\.label\)\) return \'transparent\';\n\s*return setfThemeColor\("--text-secondary", "#94a3b8"\);\n\s*\}'
replacement1 = """color: function(ctx) {
                let lbl = ctx.chart && ctx.chart.data ? ctx.chart.data.labels[ctx.index] : null;
                if (Array.isArray(lbl)) return 'transparent';
                return setfThemeColor("--text-secondary", "#94a3b8");
            }"""
content = re.sub(target1, replacement1, content)

target2 = r'color: function\(ctx\) \{\n\s*if \(ctx\.tick && Array\.isArray\(ctx\.tick\.label\)\) return \'transparent\';\n\s*return textColor;\n\s*\}'
replacement2 = """color: function(ctx) {
                                let lbl = ctx.chart && ctx.chart.data ? ctx.chart.data.labels[ctx.index] : null;
                                if (Array.isArray(lbl)) return 'transparent';
                                return textColor;
                            }"""
content = re.sub(target2, replacement2, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

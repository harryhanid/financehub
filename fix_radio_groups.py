import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'      let dispMode = "all";\s*const modeToggles = document\.querySelectorAll\("input\[name=\'setf-tahunan-kat-mode\'\]"\);\s*if \(modeToggles && modeToggles\.length\) \{\s*modeToggles\.forEach\(r => \{ if \(r\.checked\) dispMode = r\.value; \}\);\s*\}\s*setfRenderStackedGroupedChart\("chart-tahunan-kategori", yearly\.years, yearly\.kategori, dispMode\);\s*setfRenderStackedGroupedChart\("chart-tahunan-pillar", yearly\.years, yearly\.pillar, dispMode\);'

replacement = """      let dispModeKat = "all";
      const modeTogglesKat = document.querySelectorAll("input[name='setf-tahunan-kat-mode']");
      if (modeTogglesKat && modeTogglesKat.length) {
         modeTogglesKat.forEach(r => { if (r.checked) dispModeKat = r.value; });
      }

      let dispModePil = "all";
      const modeTogglesPil = document.querySelectorAll("input[name='setf-tahunan-pil-mode']");
      if (modeTogglesPil && modeTogglesPil.length) {
         modeTogglesPil.forEach(r => { if (r.checked) dispModePil = r.value; });
      }
      
      setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, yearly.kategori, dispModeKat);
      setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar, dispModePil);"""

content = re.sub(target, replacement, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

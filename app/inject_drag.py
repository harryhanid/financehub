import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

drag_script = """  const slider = document.getElementById("tree-wrapper");
  if (slider) {
      let isDown = false;
      let startX, startY, scrollLeft, scrollTop;
      slider.style.cursor = 'grab';
      slider.addEventListener('mousedown', (e) => {
          if (e.button !== 0) return;
          isDown = true;
          slider.style.cursor = 'grabbing';
          startX = e.pageX - slider.offsetLeft;
          startY = e.pageY - slider.offsetTop;
          scrollLeft = slider.scrollLeft;
          scrollTop = slider.scrollTop;
      });
      window.addEventListener('mouseup', () => {
          isDown = false;
          if(slider) slider.style.cursor = 'grab';
      });
      slider.addEventListener('mousemove', (e) => {
          if (!isDown) return;
          e.preventDefault();
          const x = e.pageX - slider.offsetLeft;
          const y = e.pageY - slider.offsetTop;
          slider.scrollLeft = scrollLeft - (x - startX);
          slider.scrollTop = scrollTop - (y - startY);
      });
  }"""

# Inject right after treeChartInstance = echarts.init(chartDom);
content = content.replace(
    "treeChartInstance = echarts.init(chartDom);",
    "treeChartInstance = echarts.init(chartDom);\n" + drag_script
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Injected drag-to-scroll logic!")

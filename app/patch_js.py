import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_js = '''function dashFilterSearch(input) {
  const filter = input.value.toLowerCase();
  const panel = input.closest('.beasiswa-dash-filter-panel');
  const labels = panel.querySelectorAll('.panel-opts label');
  labels.forEach(lbl => {
    const text = lbl.textContent.toLowerCase();
    if (text.includes(filter)) {
      lbl.style.setProperty('display', 'flex', 'important');
    } else {
      lbl.style.setProperty('display', 'none', 'important');
    }
  });
}'''

content = re.sub(
    r'function dashFilterSearch\(input\) \{.*?\}\}\);\s*\}',
    new_js,
    content,
    flags=re.DOTALL
)

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

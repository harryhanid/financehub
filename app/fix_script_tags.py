import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken script tag for echarts
content = re.sub(
    r'<script src="https://cdn\.jsdelivr\.net/npm/echarts@5\.5\.0/dist/echarts\.min\.js">\s*function dashFilterSearch\(input\) \{.*?</script>',
    r'<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>',
    content, flags=re.DOTALL
)

# Remove any duplicate dashFilterSearch functions at the bottom and just put one clean one
content = re.sub(
    r'function dashFilterSearch\(input\) \{.*?</script>',
    r'</script>',
    content, flags=re.DOTALL
)

# Inject dashFilterSearch cleanly before the last {% endblock %}
clean_script = '''
<script>
function dashFilterSearch(input) {
  const filter = input.value.toLowerCase();
  const panel = input.closest('.beasiswa-dash-filter-panel');
  const labels = panel.querySelectorAll('.panel-opts label');
  labels.forEach(lbl => {
    const text = lbl.textContent.toLowerCase();
    if (text.includes(filter)) {
      lbl.style.display = 'flex';
    } else {
      lbl.style.display = 'none';
    }
  });
}
</script>
'''

# Find the very last {% endblock %} and insert it there
parts = content.rsplit('{% endblock %}', 1)
content = parts[0] + clean_script + '{% endblock %}' + (parts[1] if len(parts)>1 else '')

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

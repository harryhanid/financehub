import re

with open('C:/Financehub/app/templates/beasiswa/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

angkatan_chip = '''
            <div class="beasiswa-dash-filter-chip">
              <span class="lbl">Angkatan</span>
              <span class="val">Semua</span>
              <span class="caret">▼</span>
              <div class="beasiswa-dash-filter-panel">
                <div class="panel-head">
                  <button type="button" data-act="all">Semua</button>
                  <button type="button" data-act="none">Kosongkan</button>
                </div>
                <div class="panel-search" style="padding:0.4rem;border-bottom:1px solid var(--border);">
                  <input type="text" class="dash-filter-search dm-inp" placeholder="Cari Angkatan..." style="width:100%;font-size:0.75rem;" onkeyup="dashFilterSearch(this)">
                </div>
                <div class="panel-opts" id="dash-filter-angkatan">
                  {% for a in angkatan_list %}
                  <label><input type="checkbox" class="dash-angkatan-cb" value="{{ a }}" checked> {{ a }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>
'''

content = content.replace(
    '<div class="beasiswa-dash-filter-chip">\n              <span class="lbl">Status</span>',
    angkatan_chip + '\n            <div class="beasiswa-dash-filter-chip">\n              <span class="lbl">Status</span>'
)

# Now inject the search box into the other existing filter chips
def inject_search(html_block, placeholder):
    return html_block.replace(
        '<div class="panel-opts"',
        f'<div class="panel-search" style="padding:0.4rem;border-bottom:1px solid var(--border);"><input type="text" class="dash-filter-search dm-inp" placeholder="{placeholder}" style="width:100%;font-size:0.75rem;" onkeyup="dashFilterSearch(this)"></div>\n                <div class="panel-opts"'
    )

content = inject_search(content, "Cari...")

# Add dashFilterSearch js function at the bottom of the script or inside the template
script_block = '''
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
'''
content = content.replace('</script>\n{% endblock %}', script_block + '</script>\n{% endblock %}')

with open('C:/Financehub/app/templates/beasiswa/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

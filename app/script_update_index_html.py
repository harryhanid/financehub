import re

path = r"C:\Financehub\app\templates\beasiswa\index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Add Program and Jenjang filters next to Pillar filter
old_html = """            <div class="filter-field">
              <label>Pillar</label>
              <div id="dash-filter-pillar">
                {% for p in pillar %}
                <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
                  <input type="checkbox" class="dash-pillar-cb" value="{{ p }}" checked>
                  {{ p }}
                </label>
                {% endfor %}
              </div>
            </div>"""

new_html = """            <div class="filter-field">
              <label>Pillar</label>
              <div id="dash-filter-pillar">
                {% for p in pillar %}
                <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
                  <input type="checkbox" class="dash-pillar-cb" value="{{ p }}" checked>
                  {{ p }}
                </label>
                {% endfor %}
              </div>
            </div>
            
            <div class="filter-field" style="position:relative;">
              <label>Program</label>
              <button type="button" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem" onclick="document.querySelectorAll('.dash-program-cb').forEach(c=>c.checked=true);loadDashboard()">Pilih Semua</button>
              <div id="dash-filter-program" style="max-height:80px; overflow-y:auto; border:1px solid #e2e8f0; padding:4px; border-radius:4px; background:var(--card, #fff); min-width:180px;">
                {% for p in program %}
                <label style="display:block;font-weight:400;margin-bottom:2px">
                  <input type="checkbox" class="dash-program-cb" value="{{ p }}" checked>
                  {{ p }}
                </label>
                {% endfor %}
              </div>
            </div>
            
            <div class="filter-field" style="position:relative;">
              <label>Jenjang Studi</label>
              <button type="button" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem" onclick="document.querySelectorAll('.dash-jenjang-cb').forEach(c=>c.checked=true);loadDashboard()">Pilih Semua</button>
              <div id="dash-filter-jenjang" style="max-height:80px; overflow-y:auto; border:1px solid #e2e8f0; padding:4px; border-radius:4px; background:var(--card, #fff); min-width:140px;">
                {% for j in jenjang %}
                <label style="display:block;font-weight:400;margin-bottom:2px">
                  <input type="checkbox" class="dash-jenjang-cb" value="{{ j }}" checked>
                  {{ j }}
                </label>
                {% endfor %}
              </div>
            </div>"""

c = c.replace(old_html, new_html)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")

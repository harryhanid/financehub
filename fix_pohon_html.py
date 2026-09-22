file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """<div class="filter-field">
        <label>Tahun Laporan</label>
        <select id="setf-pohon-year">
          <option value="all">Semua Tahun</option>
          {% for y in available_years|reverse %}
          <option value="{{ y }}">{{ y }}</option>
          {% endfor %}
        </select>
      </div>"""

replacement = """<div class="beasiswa-dash-filter-chip">
        <span class="lbl">Tahun Laporan</span>
        <span class="val">Semua Tahun</span>
        <span class="caret">?</span>
        <div class="beasiswa-dash-filter-panel">
          <div class="panel-head">
            <button type="button" data-act="all">Semua</button>
            <button type="button" data-act="none">Kosongkan</button>
          </div>
          <div class="panel-opts" id="setf-pohon-year">
            {% for y in available_years %}
            <label><input type="checkbox" class="setf-pohon-year-cb" value="{{ y }}" checked> {{ y }}</label>
            {% endfor %}
          </div>
        </div>
      </div>"""

import re
content = content.replace(target, replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated _panel.html")

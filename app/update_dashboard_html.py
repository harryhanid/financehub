path = r"C:\Financehub\app\templates\sponsorship\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

# Add cat4 filter
c = c.replace(
"""    <select class="sp-dash-filter" data-param="tahun"><option value="">Semua Tahun</option>
      {% for y in years %}<option value="{{ y }}">{{ y }}</option>{% endfor %}
    </select>
    <select class="sp-dash-filter" data-param="cat">""",
"""    <select class="sp-dash-filter" data-param="tahun"><option value="">Semua Tahun</option>
      {% for y in years %}<option value="{{ y }}">{{ y }}</option>{% endfor %}
    </select>
    <select class="sp-dash-filter" data-param="cat4">
      <option value="include">Include</option>
      <option value="exclude">Exclude</option>
      <option value="bib_include">BIB Include</option>
      <option value="all">All</option>
    </select>
    <select class="sp-dash-filter" data-param="cat">"""
)

# Add scorecards container and new chart layout
c = c.replace(
"""  </div>
  <div class="budget-summary-grid" id="sp-summary"></div>
  <div class="budget-chart-grid" style="margin-top: 20px;">
    <!-- New complex chart and tables -->
    <div class="budget-chart-card" style="grid-column: 1 / -1;">
      <h3 style="text-align:center; background:#ea580c; color:white; padding:10px; margin:-20px -20px 20px -20px; border-radius: 8px 8px 0 0;">CSR & SPONSORSHIP OVERVIEW</h3>
      <canvas id="sp-chart-year-pillar" style="max-height:400px;"></canvas>
    </div>""",
"""  </div>
  <!-- Pillar Scorecards -->
  <div class="sp-scorecards-grid" id="sp-scorecards" style="margin-top: 15px;"></div>

  <div class="budget-summary-grid" id="sp-summary" style="margin-top: 20px;"></div>
  
  <div class="budget-chart-grid" style="margin-top: 20px;">
    <!-- CSR OVERVIEW CHART -->
    <div class="budget-chart-card" style="grid-column: 1 / -1;">
      <h3 style="text-align:center; background:#ea580c; color:white; padding:10px; margin:-20px -20px 20px -20px; border-radius: 8px 8px 0 0;">CSR & SPONSORSHIP OVERVIEW</h3>
      <canvas id="sp-chart-year-pillar" style="max-height:400px;"></canvas>
    </div>
    
    <!-- Status & Top Lembaga -->
    <div class="budget-chart-card setf-compact-card">
      <h3>Status Sponsorship</h3>
      <div style="height:350px; display:flex; align-items:center; justify-content:center;">
        <canvas id="sp-chart-status"></canvas>
      </div>
    </div>
    
    <div class="budget-chart-card setf-compact-card">
      <h3>Top 5 Penerima</h3>
      <div class="setf-compact-scroll" style="max-height: 350px;">
        <table id="sp-table-lembaga">
          <thead>
            <tr><th>Lembaga</th><th class="num-right">TOTAL</th></tr>
          </thead>
          <tbody><tr><td colspan="2">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>"""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done dashboard.html")

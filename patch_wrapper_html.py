import sys

def patch_html():
    with open(r'C:\Financehub\app\templates\sahabat_etf\_panel.html', 'r', encoding='utf-8') as f:
        content = f.read()

    old_html = """        <div class="budget-chart-card">
          <h3>Trend per Tahun per Kategori</h3>
          <div style="height: 350px;"><canvas id="chart-tahunan-kategori"></canvas></div>
        </div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Total per Kategori</h3>
          <div class="setf-compact-scroll" style="max-height: 350px;">
            <table id="setf-tahunan-kategori-table" class="budget-table">
              <thead><tr><th>Kategori</th><th class="num-right">Total Budget</th><th class="num-right">Total Realisasi</th><th class="num-right">Total Sisa</th><th class="num-right">% Sisa</th></tr></thead>
              <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>

        <div class="budget-chart-card">
          <h3>Trend per Tahun per Pillar</h3>
          <div style="height: 350px;"><canvas id="chart-tahunan-pillar"></canvas></div>
        </div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Total per Pillar</h3>
          <div class="setf-compact-scroll" style="max-height: 350px;">
            <table id="setf-tahunan-pillar-table" class="budget-table">
              <thead><tr><th>Pillar</th><th class="num-right">Total Budget</th><th class="num-right">Total Realisasi</th><th class="num-right">Total Sisa</th><th class="num-right">% Sisa</th></tr></thead>
              <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>"""

    new_html = """        <div style="grid-column: 1 / -1; display: grid; grid-template-columns: 4fr 1fr; gap: 1rem;">
          <div class="budget-chart-card" style="margin-bottom: 0;">
            <h3>Trend per Tahun per Kategori</h3>
            <div style="height: 350px;"><canvas id="chart-tahunan-kategori"></canvas></div>
          </div>
          <div class="budget-chart-card setf-compact-card" style="margin-bottom: 0;">
            <h3>Total per Kategori</h3>
            <div class="setf-compact-scroll" style="max-height: 350px;">
              <table id="setf-tahunan-kategori-table" class="budget-table">
                <thead><tr><th>Kategori</th><th class="num-right">Total Budget</th><th class="num-right">Total Realisasi</th><th class="num-right">Total Sisa</th><th class="num-right">% Sisa</th></tr></thead>
                <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>

        <div style="grid-column: 1 / -1; display: grid; grid-template-columns: 4fr 1fr; gap: 1rem;">
          <div class="budget-chart-card" style="margin-bottom: 0;">
            <h3>Trend per Tahun per Pillar</h3>
            <div style="height: 350px;"><canvas id="chart-tahunan-pillar"></canvas></div>
          </div>
          <div class="budget-chart-card setf-compact-card" style="margin-bottom: 0;">
            <h3>Total per Pillar</h3>
            <div class="setf-compact-scroll" style="max-height: 350px;">
              <table id="setf-tahunan-pillar-table" class="budget-table">
                <thead><tr><th>Pillar</th><th class="num-right">Total Budget</th><th class="num-right">Total Realisasi</th><th class="num-right">Total Sisa</th><th class="num-right">% Sisa</th></tr></thead>
                <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>"""

    if old_html in content:
        content = content.replace(old_html, new_html)
        with open(r'C:\Financehub\app\templates\sahabat_etf\_panel.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched _panel.html successfully")
    else:
        print("Could not find old_html")

if __name__ == '__main__':
    patch_html()

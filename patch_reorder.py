import sys

def move_sahabat():
    with open(r'C:\Financehub\app\templates\sahabat_etf\_panel.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # The block to move
    kategori_block = """        <div class="budget-chart-card"><h3>Realisasi per Kategori</h3><canvas id="chart-kategori"></canvas></div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Realisasi per Kategori (Tabel)</h3>
          <div class="setf-compact-scroll">
            <table id="setf-kategori-table">
              <thead><tr><th>Kategori</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
              <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>"""

    # Remove it from the original location
    if kategori_block in content:
        content = content.replace(kategori_block + "\n", "")
        # Note: the original location is after Realisasi per Sahabat
        
        # Insert it at the top of the grid
        target_location = '<div class="setf-grafik-grid">\n'
        new_insert = target_location + kategori_block + "\n"
        
        content = content.replace(target_location, new_insert)

        with open(r'C:\Financehub\app\templates\sahabat_etf\_panel.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Moved in sahabat_etf/_panel.html")

def move_dashboard():
    with open(r'C:\Financehub\app\templates\beasiswa\index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    trend_panel = """            <div class="beasiswa-dash-section-panel">
              <div class="beasiswa-dash-section-title">Trend</div>
              <div class="beasiswa-dash-grafik-grid">
                <div class="beasiswa-dash-chart-card"><h3>Trend per Bulan</h3><canvas id="dash-chart-bulanan"></canvas></div>
                <div class="beasiswa-dash-chart-card"><h3>Trend per Tahun</h3><canvas id="dash-chart-tahunan"></canvas></div>
              </div>
              <div class="beasiswa-dash-grafik-grid">
                <div class="beasiswa-dash-chart-card compact">
                  <h3>Perbandingan Realisasi per Bulan per Tahun</h3>
                  <div class="setf-compact-scroll">
                    <table id="dash-monthly-table">
                      <thead><tr id="dash-monthly-thead-row"><th>Bulan</th></tr></thead>
                      <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>"""

    breakdown_panel = """            <div class="beasiswa-dash-section-panel">
              <div class="beasiswa-dash-section-title">Breakdown Realisasi</div>
              <div class="beasiswa-dash-grafik-grid">
                <div class="beasiswa-dash-chart-card"><h3>Realisasi per Kategori</h3><canvas id="dash-chart-kategori"></canvas></div>
              </div>
              <div class="beasiswa-dash-grafik-grid">
                <div class="beasiswa-dash-chart-card compact">
                  <h3>Realisasi per Kategori (Tabel)</h3>
                  <div class="setf-compact-scroll">
                    <table id="dash-kategori-table">
                      <thead><tr><th>Kategori</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
                      <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
                  </div>
                </div>
                <div class="beasiswa-dash-chart-card compact">
                  <h3>Realisasi per Jenjang Studi</h3>
                  <div class="setf-compact-scroll">
                    <table id="dash-jenjang-table">
                      <thead><tr><th>Jenjang</th><th class="num-right">Budget</th><th class="num-right">Realisasi</th><th class="num-right">Sisa</th></tr></thead>
                      <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
                  </div>
                </div>
                <div class="beasiswa-dash-chart-card compact">
                  <h3>Realisasi per Pillar per Tahun</h3>
                  <div class="setf-compact-scroll">
                    <table id="dash-pillar-year-table">
                      <thead><tr id="dash-pillar-year-thead"><th>Pillar</th></tr></thead>
                      <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
                  </div>
                </div>
                <div class="beasiswa-dash-chart-card compact">
                  <h3>Rincian Budget vs Realisasi per Program</h3>
                  <div class="setf-compact-scroll">
                    <table id="dash-program-table">
                      <thead>
                        <tr><th>Program</th><th class="num-right">Budget</th><th class="num-right">Payment</th><th class="num-right">Sisa</th></tr>
                      </thead>
                      <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>"""

    if trend_panel in content and breakdown_panel in content:
        # We need to swap them. 
        # First let's remove both, then re-insert them in opposite order.
        content = content.replace(trend_panel + "\n\n" + breakdown_panel, breakdown_panel + "\n\n" + trend_panel)
        with open(r'C:\Financehub\app\templates\beasiswa\index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Moved in beasiswa/index.html")

if __name__ == '__main__':
    move_sahabat()
    move_dashboard()

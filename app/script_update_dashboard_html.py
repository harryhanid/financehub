path = r"C:\Financehub\app\templates\sponsorship\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

new_html = """
  <div class="budget-chart-grid" style="margin-top: 20px;">
    <!-- New complex chart and tables -->
    <div class="budget-chart-card" style="grid-column: 1 / -1;">
      <h3 style="text-align:center; background:#ea580c; color:white; padding:10px; margin:-20px -20px 20px -20px; border-radius: 8px 8px 0 0;">CSR & SPONSORSHIP OVERVIEW</h3>
      <canvas id="sp-chart-year-pillar" style="max-height:400px;"></canvas>
    </div>
    
    <div class="budget-chart-card setf-compact-card" style="grid-column: span 2;">
      <h3>Description vs Pillar</h3>
      <div class="setf-compact-scroll" style="max-height: 350px;">
        <table id="sp-table-desc-pillar">
          <thead>
            <tr><th>Description</th><th class="num-right">TOTAL</th><th class="num-right">APP</th><th class="num-right">ENERGY & FINANCE</th><th class="num-right">PROPERTY</th><th class="num-right">AGRI</th></tr>
          </thead>
          <tbody><tr><td colspan="6">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>
    
    <div class="budget-chart-card setf-compact-card">
      <h3>Sponsorship Allocation</h3>
      <div class="setf-compact-scroll" style="max-height: 350px;">
        <table id="sp-table-pillar-summary">
          <thead>
            <tr><th>Row Labels</th><th class="num-right">Amount</th><th class="num-right">% Alloc</th></tr>
          </thead>
          <tbody><tr><td colspan="3">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>
    
    <div class="budget-chart-card setf-compact-card" style="grid-column: 1 / -1;">
      <h3>Description vs Year</h3>
      <div class="setf-compact-scroll" style="max-height: 350px;">
        <table id="sp-table-desc-year">
          <thead id="sp-thead-desc-year">
            <tr><th>Row Labels</th></tr>
          </thead>
          <tbody><tr><td>Loading...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
"""

c = c.replace('  <div class="budget-summary-grid" id="sp-summary"></div>', '  <div class="budget-summary-grid" id="sp-summary"></div>' + new_html)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")

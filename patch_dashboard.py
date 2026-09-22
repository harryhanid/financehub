with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Fix setfRenderAlert
old_alert = """function setfRenderAlert(overBudget) {
  const card = document.getElementById("setf-alert-card");
  const list = document.getElementById("setf-alert-list");
  if (!overBudget.length) {"""

new_alert = """function setfRenderAlert(overBudget) {
  const card = document.getElementById("setf-alert-card");
  const list = document.getElementById("setf-alert-list");
  if (!card || !list) return;
  if (!overBudget || !overBudget.length) {"""
c = c.replace(old_alert, new_alert)

# 2. Add setfRenderPillarChart
new_func = """function setfRenderYearlyChart(yearly) {
"""

insert_pillar_chart = """function setfRenderPillarChart(pillarRows) {
  if (!pillarRows || !pillarRows.length) {
    if (setfCharts["chart-pillar"]) { setfCharts["chart-pillar"].destroy(); delete setfCharts["chart-pillar"]; }
    return;
  }
  setfRenderBarChart("chart-pillar", pillarRows.map(function (p) { return p.pillar; }), [
    { label: "Realisasi", data: pillarRows.map(function (p) { return p.realisasi; }), backgroundColor: "#10b981" },
    { label: "Budget", data: pillarRows.map(function (p) { return p.budget; }), backgroundColor: "#3b82f6" }
  ]);
}

function setfRenderYearlyChart(yearly) {"""
c = c.replace(new_func, insert_pillar_chart)

# 3. Call setfRenderPillarChart in fetch block
old_fetch = """      setfRenderYearlyChart(data.yearly);
      setfRenderPillarTable(data.pillar);"""

new_fetch = """      setfRenderYearlyChart(data.yearly);
      setfRenderPillarChart(data.pillar);
      setfRenderPillarTable(data.pillar);"""
c = c.replace(old_fetch, new_fetch)


with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("Dashboard patched successfully")

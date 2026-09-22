import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace setfRenderAlert call with setfRenderExecSummary
target_call = r'setfRenderAlert\(data\.over_budget\);'
replacement_call = 'setfRenderExecSummary(data);'
content = re.sub(target_call, replacement_call, content)

# Replace the setfRenderAlert function definition
target_func = r'function setfRenderAlert\(overBudget\) \{[\s\S]*?\}\.join\(""\);\s*\}'
replacement_func = """function setfRenderExecSummary(data) {
  const card = document.getElementById("setf-exec-summary-card");
  const textEl = document.getElementById("setf-exec-summary-text");
  if (!card || !textEl) return;

  const kategori = data.kategori || [];
  const pillar = data.pillar || [];

  let totalBgt = 0, totalAct = 0;
  let penAct = 0, kesAct = 0;

  kategori.forEach(k => {
    totalBgt += k.budget || 0;
    totalAct += k.realisasi || 0;
    if (["By Pendidikan", "By Tunjangan", "By Penelitian"].includes(k.cat1)) {
      penAct += k.realisasi || 0;
    } else if (k.cat1 === "By Medical") {
      kesAct += k.realisasi || 0;
    }
  });

  let setfAct = 0, nonSetfAct = 0;
  pillar.forEach(p => {
    if (p.pillar === "SETF") {
      setfAct += p.realisasi || 0;
    } else {
      nonSetfAct += p.realisasi || 0;
    }
  });

  // Calculate percentages
  const pctTotal = totalBgt > 0 ? (totalAct / totalBgt * 100).toFixed(1) : "0.0";
  const pctPen = totalAct > 0 ? (penAct / totalAct * 100).toFixed(1) : "0.0";
  const pctKes = totalAct > 0 ? (kesAct / totalAct * 100).toFixed(1) : "0.0";
  const pctSetf = totalAct > 0 ? (setfAct / totalAct * 100).toFixed(1) : "0.0";
  const pctNonSetf = totalAct > 0 ? (nonSetfAct / totalAct * 100).toFixed(1) : "0.0";

  // Date formatting
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sept", "Okt", "Nov", "Des"];
  const today = new Date();
  const dateStr = today.getDate() + " " + months[today.getMonth()] + " " + today.getFullYear();

  const summary = `Total Budget sebesar <strong>Rp ${setfFmtJutaan(totalBgt)}</strong> dengan realisasi sampai dengan ${dateStr} mencapai <strong>${pctTotal}%</strong> dengan rincian Pendidikan (By Pendidikan + By Tunjangan + By Penelitian) sebesar Rp ${setfFmtJutaan(penAct)} (${pctPen}%) dan Kesehatan (By Medical) sebesar Rp ${setfFmtJutaan(kesAct)} (${pctKes}%). <br><br>Porsi Beasiswa yang ditanggung SETF sebesar Rp ${setfFmtJutaan(setfAct)} atau ${pctSetf}% dan Non SETF (AGRI, APP, FINANCE) sebesar Rp ${setfFmtJutaan(nonSetfAct)} atau ${pctNonSetf}% dari Total Realisasi <strong>Rp ${setfFmtJutaan(totalAct)}</strong>.`;

  textEl.innerHTML = summary;
}"""
content = re.sub(target_func, replacement_func, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated JS.")

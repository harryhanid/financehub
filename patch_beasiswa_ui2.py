with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. _bgtAddItemRow
text = text.replace(
    'row.style.cssText = "display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:.5rem;margin-bottom:.5rem;align-items:end";',
    'row.style.cssText = "display:grid;grid-template-columns:1fr 1fr 1fr 130px auto;gap:.5rem;margin-bottom:.5rem;align-items:end";'
)

# Add tgl_expired input
text = text.replace(
    'amtFg.appendChild(amtLbl); amtFg.appendChild(amtInp);',
    'amtFg.appendChild(amtLbl); amtFg.appendChild(amtInp);\n  const expInp = document.createElement("input");\n  expInp.type = "date"; expInp.className = "bgt-row-expired";\n  expInp.onclick = function(){ this.showPicker() };\n  expInp.onkeydown = function(){ return false };\n  expInp.style.width = "100%";'
)
text = text.replace(
    'row.appendChild(amtFg);\n  row.appendChild(rmBtn);',
    'row.appendChild(amtFg);\n  row.appendChild(fg("Expired", expInp));\n  row.appendChild(rmBtn);'
)

# 2. bgtSaveRows
text = text.replace(
    'amount: parseFloat(r.querySelector(".bgt-row-amount").value.replace(/,/g, \'\')) || 0,',
    'amount: parseFloat(r.querySelector(".bgt-row-amount").value.replace(/,/g, \'\')) || 0,\n    tgl_expired: r.querySelector(".bgt-row-expired").value || null,'
)

with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)

with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. Add Tgl Expired to bgt-edit-section UI
text = text.replace(
    'grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:.5rem;margin-bottom:.5rem"',
    'grid-template-columns:1fr 1fr 1fr 1fr 1fr 1fr;gap:.5rem;margin-bottom:.5rem"'
)
text = text.replace(
    '<div class="form-group" style="margin:0"><label>Amount</label><input type="text" id="bgt-amount" placeholder="0" oninput="let v=this.value.replace(/[^0-9]/g,\'\');this.value=v?parseInt(v,10).toLocaleString(\'en-US\'):\'\'"></div>',
    '<div class="form-group" style="margin:0"><label>Amount</label><input type="text" id="bgt-amount" placeholder="0" oninput="let v=this.value.replace(/[^0-9]/g,\'\');this.value=v?parseInt(v,10).toLocaleString(\'en-US\'):\'\'"></div>\n          <div class="form-group" style="margin:0"><label>Expired</label><input type="date" id="bgt-edit-expired" onclick="this.showPicker()" onkeydown="return false"></div>'
)

# 2. bgtEditRow function mapping
text = text.replace(
    'function bgtEditRow(id, cat1, cat2, tanggal, pillar, amount) {',
    'function bgtEditRow(id, cat1, cat2, tanggal, pillar, amount, tgl_expired) {'
)
text = text.replace(
    'document.getElementById("bgt-amount").value = amount ? parseInt(amount, 10).toLocaleString(\'en-US\') : "";',
    'document.getElementById("bgt-amount").value = amount ? parseInt(amount, 10).toLocaleString(\'en-US\') : "";\n  document.getElementById("bgt-edit-expired").value = tgl_expired || "";'
)

# 3. bgtSaveRow payload mapping
text = text.replace(
    'const amount = parseFloat(document.getElementById("bgt-amount").value.replace(/,/g, \'\')) || 0;',
    'const amount = parseFloat(document.getElementById("bgt-amount").value.replace(/,/g, \'\')) || 0;\n  const tgl_expired = document.getElementById("bgt-edit-expired").value || null;'
)
text = text.replace(
    'const body = JSON.stringify({ cat1, cat2, tanggal, pillar, amount });',
    'const body = JSON.stringify({ cat1, cat2, tanggal, pillar, amount, tgl_expired });'
)

# 4. ibgtEditRow wrapper mapping
text = text.replace(
    'function ibgtEditRow(id, cat1, cat2, tanggal, pillar, amount) {\n  _bgtContext = "input";\n  bgtEditRow(id, cat1, cat2, tanggal, pillar, amount);\n}',
    'function ibgtEditRow(id, cat1, cat2, tanggal, pillar, amount, tgl_expired) {\n  _bgtContext = "input";\n  bgtEditRow(id, cat1, cat2, tanggal, pillar, amount, tgl_expired);\n}'
)

with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)

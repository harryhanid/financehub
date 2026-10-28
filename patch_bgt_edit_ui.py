with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    '<div class="form-group" style="margin:0">\n            <label>Pillar</label>\n            <select id="bgt-edit-pillar">{% for p in pillar %}<option value="{{ p }}">{{ p }}</option>{% endfor %}</select>\n          </div>\n          <div class="form-group" style="margin:0"><label>Amount</label><input type="text" id="bgt-amount" placeholder="0" oninput="let v=this.value.replace(/[^0-9]/g,\'\');this.value=v?parseInt(v,10).toLocaleString(\'en-US\'):\'\'"></div>\n          <div class="form-group" style="margin:0"><label>Expired</label><input type="date" id="bgt-edit-expired" onclick="this.showPicker()" onkeydown="return false"></div>',
    '<div class="form-group" style="margin:0"><label>Expired</label><input type="date" id="bgt-edit-expired" onclick="this.showPicker()" onkeydown="return false"></div>\n          <div class="form-group" style="margin:0">\n            <label>Pillar</label>\n            <select id="bgt-edit-pillar">{% for p in pillar %}<option value="{{ p }}">{{ p }}</option>{% endfor %}</select>\n          </div>\n          <div class="form-group" style="margin:0"><label>Amount</label><input type="text" id="bgt-amount" placeholder="0" oninput="let v=this.value.replace(/[^0-9]/g,\'\');this.value=v?parseInt(v,10).toLocaleString(\'en-US\'):\'\'"></div>'
)

with open("app/templates/beasiswa/index.html", "w", encoding="utf-8") as f:
    f.write(text)

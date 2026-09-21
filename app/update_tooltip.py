import re

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_tooltip = "tooltip: { trigger: 'item', triggerOn: 'mousemove' },"
new_tooltip = """tooltip: { 
      trigger: 'item', 
      triggerOn: 'mousemove',
      formatter: function(params) {
         let d = params.data;
         if (!d) return '';
         let html = '<div style="font-weight:bold;margin-bottom:5px;border-bottom:1px solid #eee;padding-bottom:3px;">' + (d.name || '') + '</div>';
         
         let hasInfo = false;
         if (d.tanggal_lahir) { html += '<div style="font-size:12px;"><b>Tanggal Lahir:</b> ' + d.tanggal_lahir + '</div>'; hasInfo = true; }
         if (d.catatan) { html += '<div style="font-size:12px;max-width:250px;white-space:normal;"><b>Catatan:</b> ' + d.catatan + '</div>'; hasInfo = true; }
         if (!hasInfo) { html += '<div style="font-size:12px;color:#888;"><i>Tidak ada informasi tambahan</i></div>'; }
         
         if (d.partners && d.partners.length > 0) {
             html += '<hr style="margin:8px 0; border:0; border-top:1px solid #ddd">';
             d.partners.forEach(p => {
                 html += '<div style="font-weight:bold;margin-bottom:3px;">' + (p.name || '') + ' <span style="font-size:10px;color:#666;font-weight:normal;">(Partner)</span></div>';
                 let hasPInfo = false;
                 if (p.tanggal_lahir) { html += '<div style="font-size:12px;"><b>Tanggal Lahir:</b> ' + p.tanggal_lahir + '</div>'; hasPInfo = true; }
                 if (p.catatan) { html += '<div style="font-size:12px;max-width:250px;white-space:normal;"><b>Catatan:</b> ' + p.catatan + '</div>'; hasPInfo = true; }
                 if (!hasPInfo) { html += '<div style="font-size:12px;color:#888;"><i>Tidak ada informasi tambahan</i></div>'; }
             });
         }
         return html;
      }
    },"""

if old_tooltip in content:
    content = content.replace(old_tooltip, new_tooltip)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated tooltip formatter!")
else:
    print("Could not find old tooltip config!")

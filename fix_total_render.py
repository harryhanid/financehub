import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'    dataList\.forEach\(function\(item\) \{\n       if \(item\.isSubTotal\) return;\n       item\.realisasi\.forEach\(function\(val, idx\) \{\n           if \(\(val \|\| 0\) > maxPerYear\[idx\]\) maxPerYear\[idx\] = val;\n       \}\);\n    \}\);\n    \n    dataList\.forEach\(function\(item\) \{\n       const totalRealisasi = item\.realisasi\.reduce\(\(a, b\) => a \+ \(b\|\|0\), 0\);\n       \n       if \(\!item\.isSubTotal\) grandRealisasi \+= totalRealisasi;\n       \n       let nameHtml = item\.name;\n       let trStyle = "";\n       if \(item\.isSubTotal\) \{\n           nameHtml = "<strong>" \+ item\.name \+ "</strong>";\n           trStyle = " style=\'background:rgba\(0,0,0,0\.03\);\'";\n       \} else \{\n           if \(tableId\.includes\("kategori"\)\) nameHtml = setfCatBadge\(item\.name\);\n           else if \(tableId\.includes\("pillar"\)\) nameHtml = setfPillarBadge\(item\.name\);\n       \}\n       \n       let rowHtml = "<tr" \+ trStyle \+ "><td>" \+ nameHtml \+ "</td>";\n       \n       item\.realisasi\.forEach\(function\(val, idx\) \{\n           if \(\!item\.isSubTotal\) grandYearlyRealisasi\[idx\] \+= \(val \|\| 0\);\n           let v = val \|\| 0;\n           let tdStyle = "";\n           if \(\!item\.isSubTotal && v > 0 && v === maxPerYear\[idx\]\) \{\n               tdStyle = " style=\'font-weight:bold; color:var\(--positive, #10b981\); background:rgba\(16, 185, 129, 0\.1\); border-radius: 4px;\'";\n           \}\n           let innerHtml = setfFmtJutaan\(v\);\n           if \(item\.isSubTotal\) innerHtml = "<strong>" \+ innerHtml \+ "</strong>";\n           rowHtml \+= "<td class=\'num-right\'" \+ tdStyle \+ ">" \+ innerHtml \+ "</td>";\n       \}\);\n       rowHtml \+= "<td class=\'num-right\' style=\'font-weight:bold;\'>" \+ setfFmtJutaan\(totalRealisasi\) \+ "</td></tr>";\n       tbodyHtml \+= rowHtml;\n    \}\);\n    \n    let totalRowHtml = "<tr style=\'font-weight:bold; background:var\(--bg-secondary\)\'><td>Total Keseluruhan</td>";'

replacement = """    dataList.forEach(function(item) {
       if (item.isSubTotal || item.isHeaderOnly) return;
       item.realisasi.forEach(function(val, idx) {
           if ((val || 0) > maxPerYear[idx]) maxPerYear[idx] = val;
       });
    });
    
    dataList.forEach(function(item) {
       const totalRealisasi = item.realisasi.reduce((a, b) => a + (b||0), 0);
       
       if (!item.isSubTotal && !item.isHeaderOnly) grandRealisasi += totalRealisasi;
       
       let nameHtml = item.name;
       let trStyle = "";
       if (item.isHeaderOnly) {
           nameHtml = "<strong style='font-size:1.05em;'>" + item.name + "</strong>";
       } else if (item.isSubTotal) {
           nameHtml = "<strong>" + item.name + "</strong>";
           trStyle = " style='background:rgba(0,0,0,0.03);'";
       } else {
           if (tableId.includes("kategori")) nameHtml = setfCatBadge(item.name);
           else if (tableId.includes("pillar")) nameHtml = setfPillarBadge(item.name);
       }
       
       let rowHtml = "<tr" + trStyle + "><td>" + nameHtml + "</td>";
       
       item.realisasi.forEach(function(val, idx) {
           if (item.isHeaderOnly) {
               rowHtml += "<td class='num-right'></td>";
               return;
           }
           if (!item.isSubTotal) grandYearlyRealisasi[idx] += (val || 0);
           let v = val || 0;
           let tdStyle = "";
           if (!item.isSubTotal && v > 0 && v === maxPerYear[idx]) {
               tdStyle = " style='font-weight:bold; color:var(--positive, #10b981); background:rgba(16, 185, 129, 0.1); border-radius: 4px;'";
           }
           let innerHtml = setfFmtJutaan(v);
           if (item.isSubTotal) innerHtml = "<strong>" + innerHtml + "</strong>";
           rowHtml += "<td class='num-right'" + tdStyle + ">" + innerHtml + "</td>";
       });
       if (item.isHeaderOnly) {
           rowHtml += "<td class='num-right'></td></tr>";
       } else {
           rowHtml += "<td class='num-right' style='font-weight:bold;'>" + setfFmtJutaan(totalRealisasi) + "</td></tr>";
       }
       tbodyHtml += rowHtml;
    });
    
    let grandTotalLabel = tableId.includes("kategori") ? "Total Pendidikan dan Kesehatan" : "Total Keseluruhan";
    let totalRowHtml = "<tr style='font-weight:bold; background:var(--bg-secondary)'><td>" + grandTotalLabel + "</td>";"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

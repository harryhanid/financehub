with open('app/static/js/sahabat_etf.js', 'r', encoding='utf-8') as f:
    c = f.read()

start_idx = c.find('function setfUpdateReportExportLink() {')
if start_idx != -1:
    end_idx = c.find('function setfRenderDetailTable', start_idx)
    # The block we replace is between start_idx and the start of the next section, roughly.
    # Actually, we can just find the closing bracket of the function.
    # The current setfUpdateReportExportLink ends at link.href = "/beasiswa/sahabat/export/report?" + qs;\n}
    end_brace = c.find('}', start_idx)
    
    # Wait, my previous replacement was up to the `}`. Let's find the `}` after `/beasiswa/sahabat/export/report?" + qs;`
    end_brace = c.find('}', c.find('/beasiswa/sahabat/export/report?" + qs;', start_idx))
    
    if end_brace != -1:
        new_func = """function setfUpdateReportExportLink() {
  const sel = document.getElementById("setf-report-year");
  if (!sel) return;
  
  let qs = "year=" + encodeURIComponent(sel.value);
  const monthSel = document.getElementById("setf-report-month");
  if (monthSel) qs += "&month=" + encodeURIComponent(monthSel.value);
  
  const pillars = Array.from(document.querySelectorAll(".setf-laporan-pillar-cb:checked")).map(function (cb) { return cb.value; });
  pillars.forEach(function (p) { qs += "&pillars[]=" + encodeURIComponent(p); });
  
  const linkReport = document.getElementById("setf-export-report");
  if (linkReport) linkReport.href = "/beasiswa/sahabat/export/report?" + qs;

  const linkDetail = document.getElementById("setf-export-report-detail");
  if (linkDetail) linkDetail.href = "/beasiswa/sahabat/export/report/detail?" + qs;

  const linkPptFy = document.getElementById("setf-export-ppt-fy");
  if (linkPptFy) linkPptFy.href = "/beasiswa/sahabat/api/report/export_ppt?mode=fy&" + qs;

  const linkPptYtd = document.getElementById("setf-export-ppt-ytd");
  if (linkPptYtd) linkPptYtd.href = "/beasiswa/sahabat/api/report/export_ppt?mode=ytd&" + qs;
}"""
        c = c[:start_idx] + new_func + c[end_brace+1:]
        with open('app/static/js/sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(c)
        print("Replaced!")
    else:
        print("End brace not found")
else:
    print("Function not found")

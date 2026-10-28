import re

with open('C:/Financehub/app/static/js/dashboard_beasiswa.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Modify dashGetSelectedFilters
get_filters_new = '''function dashGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".dash-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  const programs = Array.from(document.querySelectorAll(".dash-program-cb:checked")).map(function (cb) { return cb.value; });
  const jenjangs = Array.from(document.querySelectorAll(".dash-jenjang-cb:checked")).map(function (cb) { return cb.value; });
  const angkatans = Array.from(document.querySelectorAll(".dash-angkatan-cb:checked")).map(function (cb) { return cb.value; });
  const statuses = Array.from(document.querySelectorAll(".dash-status-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars, programs: programs, jenjangs: jenjangs, angkatans: angkatans, statuses: statuses };
}'''
content = re.sub(r'function dashGetSelectedFilters\(\) \{.*?return \{ years: years, pillars: pillars, programs: programs, jenjangs: jenjangs \};\n\}', get_filters_new, content, flags=re.DOTALL)

# Modify dashBuildQueryString
build_qs_new = '''function dashBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years && filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars && filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  if (filters.programs && filters.programs.length) params.set("programs", filters.programs.join(","));
  if (filters.jenjangs && filters.jenjangs.length) params.set("jenjangs", filters.jenjangs.join(","));
  if (filters.angkatans && filters.angkatans.length) params.set("angkatans", filters.angkatans.join(","));
  if (filters.statuses && filters.statuses.length) params.set("statuses", filters.statuses.join(","));
  return params.toString();
}'''
content = re.sub(r'function dashBuildQueryString\(filters\) \{.*?return params\.toString\(\);\n\}', build_qs_new, content, flags=re.DOTALL)

with open('C:/Financehub/app/static/js/dashboard_beasiswa.js', 'w', encoding='utf-8') as f:
    f.write(content)

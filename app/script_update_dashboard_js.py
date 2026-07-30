import re

path = r"C:\Financehub\app\static\js\dashboard_beasiswa.js"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Update dashGetSelectedFilters
old_get = """function dashGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".dash-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}"""
new_get = """function dashGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".dash-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".dash-pillar-cb:checked")).map(function (cb) { return cb.value; });
  const programs = Array.from(document.querySelectorAll(".dash-program-cb:checked")).map(function (cb) { return cb.value; });
  const jenjangs = Array.from(document.querySelectorAll(".dash-jenjang-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars, programs: programs, jenjangs: jenjangs };
}"""
c = c.replace(old_get, new_get)

# Update dashBuildQueryString
old_build = """function dashBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  return params.toString();
}"""
new_build = """function dashBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  if (filters.programs && filters.programs.length) params.set("programs", filters.programs.join(","));
  if (filters.jenjangs && filters.jenjangs.length) params.set("jenjangs", filters.jenjangs.join(","));
  return params.toString();
}"""
c = c.replace(old_build, new_build)

# Add event listeners for new checkboxes
old_init = """document.querySelectorAll(".dash-pillar-cb").forEach(function (cb) {
    cb.addEventListener("change", function () { loadDashboard(); });
  });"""
new_init = """document.querySelectorAll(".dash-pillar-cb").forEach(function (cb) {
    cb.addEventListener("change", function () { loadDashboard(); });
  });
  document.querySelectorAll(".dash-program-cb").forEach(function (cb) {
    cb.addEventListener("change", function () { loadDashboard(); });
  });
  document.querySelectorAll(".dash-jenjang-cb").forEach(function (cb) {
    cb.addEventListener("change", function () { loadDashboard(); });
  });"""
c = c.replace(old_init, new_init)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done")

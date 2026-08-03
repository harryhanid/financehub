path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace('<button type="submit" class="budget-btn">Terapkan Filter</button>',
              '<button type="submit" class="budget-btn">Terapkan Filter</button>\n    <button type="button" class="budget-btn" style="background-color:#10b981;margin-left:auto" onclick="exportDataExcel()">Export to Excel</button>')

script = """
<script>
function exportDataExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/data/export?" + params.toString();
}
</script>
"""
c = c.replace("{% endblock %}", script + "\n{% endblock %}")
with open(path, "w", encoding="utf-8") as f:
    f.write(c)

path2 = r"C:\Financehub\app\templates\sponsorship\outstanding.html"
with open(path2, "r", encoding="utf-8") as f:
    c2 = f.read()

c2 = c2.replace('<button type="submit" class="budget-btn">Terapkan Filter</button>',
              '<button type="submit" class="budget-btn">Terapkan Filter</button>\n    <button type="button" class="budget-btn" style="background-color:#10b981;margin-left:auto" onclick="exportOutstandingExcel()">Export to Excel</button>')

script2 = """
<script>
function exportOutstandingExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/outstanding/export?" + params.toString();
}
</script>
"""
c2 = c2.replace("{% endblock %}", script2 + "\n{% endblock %}")
with open(path2, "w", encoding="utf-8") as f:
    f.write(c2)

print("done")

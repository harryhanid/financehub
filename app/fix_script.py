path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace the misplaced script
c = c.replace(
"""{% endblock %}

<script>
function exportDataExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/data/export?" + params.toString();
}
</script>""",
"""
<script>
function exportDataExcel() {
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/data/export?" + params.toString();
}
</script>
{% endblock %}"""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done script fix")

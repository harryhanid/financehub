for path, func_name in [
    (r"C:\Financehub\app\templates\sponsorship\data.html", "exportDataExcel"),
    (r"C:\Financehub\app\templates\sponsorship\outstanding.html", "exportOutstandingExcel")
]:
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    
    # Remove all injected scripts
    import re
    # The script looks like:
    # <script>\nfunction exportDataExcel() {\n  const form = document.getElementById("sp-data-filter-form");\n  const params = new URLSearchParams(new FormData(form));\n  window.location.href = "/sponsorship/data/export?" + params.toString();\n}\n</script>\n\n{% endblock %}
    
    c = re.sub(r'<script>\nfunction ' + func_name + r'\(\).*?</script>\n\n', '', c, flags=re.DOTALL)
    
    # Now append it exactly once at the end of the file
    script = f"""
<script>
function {func_name}() {{
  const form = document.getElementById("sp-data-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/{func_name.replace('export', '').replace('Excel', '').lower()}/export?" + params.toString();
}}
</script>
"""
    c += script
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)

print("done")

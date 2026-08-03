file_path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Remove the autofocus
html = html.replace("    if (searchInp) searchInp.focus();\n", "")

# Add keydown listener for F and Escape
keydown_logic = """    if (searchInp) {
      document.addEventListener('keydown', function(e) {
        // Only trigger 'f' if we're not already typing in an input/textarea
        if (e.key.toLowerCase() === 'f' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
          e.preventDefault();
          searchInp.focus();
        }
        if (e.key === 'Escape' && document.activeElement === searchInp) {
          searchInp.blur();
        }
      });
    }"""
html = html.replace("const searchInp = document.getElementById('pa-siswa-search');", "const searchInp = document.getElementById('pa-siswa-search');\n" + keydown_logic)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)
print("Updated successfully")

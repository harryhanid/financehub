file_path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Replace max-height:calc(100vh - 230px) with calc(100vh - 120px)
html = html.replace('max-height:calc(100vh - 230px)', 'max-height:calc(100vh - 120px)')

# Ensure they have height 100% so they stretch? 
# max-height alone will let it shrink if data is small. If we want it to stretch, we can add height:calc(100vh - 120px)
html = html.replace('max-height:calc(100vh - 120px)', 'max-height:calc(100vh - 120px); height:calc(100vh - 120px)')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)
print("Updated successfully")

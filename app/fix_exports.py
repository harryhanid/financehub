exports_path = r"C:\Financehub\app\modules\payment_memo\exports.py"
with open(exports_path, "r", encoding="utf-8") as f:
    exports = f.read()

# Fix the broken import by replacing it back
bad_block = "    from format_utils import format_rupiah\nfrom modules.payment_memo.service import"
if bad_block in exports:
    exports = exports.replace(bad_block, "    from modules.payment_memo.service import")
    
# Now put the import near the top of the file.
# The plan said: "after the existing imports (the last one is `from openpyxl.styles import Font, PatternFill, Alignment, Border, Side`, followed by the `from modules.payment_memo.service import (...)` block)"
# Let's just find "import urllib.parse" or "import datetime" or "from io import BytesIO" and put it at the very top.
if "from format_utils import format_rupiah" not in exports:
    exports = "from format_utils import format_rupiah\n" + exports

with open(exports_path, "w", encoding="utf-8") as f:
    f.write(exports)

print("Fixed exports.py")

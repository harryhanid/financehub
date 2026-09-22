import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# The hanging block starts right after the newly inserted setfRenderBudgetVsRealisasiChart
# And it is essentially the old plugins and scales block.
# Let's find exactly where it starts.
junk_regex = r'\},[\s\n]*plugins: \{[\s\n]*legend: \{ position: "top", labels: \{ color: textColor \} \},[\s\S]*?x: \{[\s\n]*grid: \{ display: false \},[\s\n]*ticks: \{ color: textColor \}[\s\n]*\}[\s\n]*\}[\s\n]*\}[\s\n]*\}\);[\s\n]*\}'

match = re.search(junk_regex, content)
if match:
    print("Found hanging block! Removing...")
    content = content[:match.start()] + content[match.end():]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("Could not find hanging block.")

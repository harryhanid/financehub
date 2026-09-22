import re

with open("C:/Financehub/pristine_sahabat.js", "r", encoding="utf-8") as f:
    pristine = f.read()

# We need to extract the block of missing functions.
# They are between the end of setfRenderStackedBarChart and the beginning of setfRenderDoughnutChart!
# Let's verify this block!
start_str = "function setfRenderFamilyTable(families) {"
end_str = "function setfRenderDoughnutChart(canvasId, labels, values, colors) {"

start_idx = pristine.find(start_str)
end_idx = pristine.find(end_str)

missing_block = pristine[start_idx:end_idx]

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    current = f.read()

# We want to insert missing_block right before setfRenderDoughnutChart in current!
current_end_idx = current.find("function setfRenderDoughnutChart(canvasId, labels, values, colors) {")

if current_end_idx != -1:
    new_content = current[:current_end_idx] + missing_block + current[current_end_idx:]
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully restored missing block!")
else:
    print("Could not find setfRenderDoughnutChart in current file.")

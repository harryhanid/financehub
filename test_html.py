with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "subgraph FC" in line:
        for j in range(max(0, i-2), min(len(lines), i+30)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break

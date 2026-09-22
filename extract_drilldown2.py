import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
log_path = r"C:\Users\25010160\.gemini\antigravity\brain\394dd2ba-193f-4720-bb15-f06a4f4fe4ca\.system_generated\logs\transcript_full.jsonl"

found_block = ""
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("type") == "GENERIC" and "content" in data:
                content = data["content"]
                if "function setfRenderDrilldownChip()" in content:
                    found_block = content
                    break
        except:
            pass

if found_block:
    start = found_block.find("let setfActiveKategoriDrilldown = null;")
    if start == -1: start = found_block.find("function setfRenderDrilldownChip()") - 200
    print(found_block[start:start+2500])
else:
    print("Not found")

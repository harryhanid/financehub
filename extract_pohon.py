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
                if "function setfLoadPohon()" in content and "setfRenderDiagram1" in content:
                    found_block = content
                    break
        except:
            pass

if found_block:
    print("Found block of length:", len(found_block))
    with open("C:/Financehub/extracted_pohon.txt", "w", encoding="utf-8") as out:
        out.write(found_block)
else:
    print("Not found")

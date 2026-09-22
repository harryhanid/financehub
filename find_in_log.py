import json
import os

log_path = r"C:\Users\25010160\.gemini\antigravity\brain\394dd2ba-193f-4720-bb15-f06a4f4fe4ca\.system_generated\logs\transcript_full.jsonl"
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data.get("type") == "TOOL_RESPONSE":
            content = data.get("content", "")
            # Check if this tool response contains the word "setfLoadPohon"
            if "function setfLoadPohon" in content and "const years = Array.from" in content:
                print("FOUND IT!")
                with open("found.txt", "w", encoding="utf-8") as out:
                    out.write(content)
                break

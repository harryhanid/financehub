import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
log_path = r"C:\Users\25010160\.gemini\antigravity\brain\394dd2ba-193f-4720-bb15-f06a4f4fe4ca\.system_generated\logs\transcript_full.jsonl"

found = ""
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            # Find python scripts I wrote to inject it
            if data.get("type") == "PLANNER_RESPONSE":
                for tc in data.get("tool_calls", []):
                    args = tc.get("args", {})
                    cmd = args.get("CommandLine", "")
                    if "function setfRenderDiagram1" in cmd and "set-content" in cmd.lower():
                        found = cmd
                        break
        except:
            pass

if found:
    print("Found the injection script!")
    with open("C:/Financehub/extracted_pohon_script.txt", "w", encoding="utf-8") as out:
        out.write(found)
else:
    print("Not found")

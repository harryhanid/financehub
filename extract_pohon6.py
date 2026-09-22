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
            if data.get("type") == "PLANNER_RESPONSE":
                for tc in data.get("tool_calls", []):
                    if tc.get("name") == "write_to_file":
                        args = tc.get("args", {})
                        repl = args.get("CodeContent", "")
                        if "function setfRenderDiagram1" in repl:
                            found = repl
                            break
        except:
            pass

if found:
    with open("C:/Financehub/extracted_diagram.txt", "w", encoding="utf-8") as out:
        out.write(found)
    print("Found in write_to_file!")
else:
    print("Not found")

import json
transcript_path = r"C:\Users\25010160\.gemini\antigravity\brain\394dd2ba-193f-4720-bb15-f06a4f4fe4ca\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        step = json.loads(line)
        if step.get("type") == "PLANNER_RESPONSE" and "tool_calls" in step:
            for call in step["tool_calls"]:
                name = call.get("name")
                args = call.get("args", {})
                if name == "replace_file_content":
                    print(args.get("TargetFile", ""))

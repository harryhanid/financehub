import json

log_path = r"C:\Users\25010160\.gemini\antigravity\brain\394dd2ba-193f-4720-bb15-f06a4f4fe4ca\.system_generated\logs\transcript_full.jsonl"
largest = ""
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data.get("type") == "TOOL_RESPONSE":
            content = data.get("content", "")
            if "function setfRenderBudgetVsRealisasiChart" in content and len(content) > 10000:
                print(f"Found a tool response of length {len(content)}")
                if len(content) > len(largest):
                    largest = content

if largest:
    with open("recovered_js.txt", "w", encoding="utf-8") as out:
        out.write(largest)
    print("Saved recovered_js.txt")
else:
    print("Not found.")

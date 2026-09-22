import json
import re
import builtins
import os

transcript_path = r"C:\Users\25010160\.gemini\antigravity\brain\394dd2ba-193f-4720-bb15-f06a4f4fe4ca\.system_generated\logs\transcript_full.jsonl"
with open("C:/Financehub/pristine_sahabat.js", "r", encoding="utf-8") as f:
    current_content = f.read()

# Mocking open for python scripts
class MockFile:
    def __init__(self, content): self.content = content.replace("\r\n", "\n")
    def read(self): return self.content
    def write(self, s):
        global current_content
        current_content = s.replace("\r\n", "\n")
    def __enter__(self): return self
    def __exit__(self, *a): pass

original_open = builtins.open
def mocked_open(file, mode='r', *args, **kwargs):
    if 'sahabat_etf.js' in str(file): return MockFile(current_content)
    if 'w' in mode:
        class DummyFile:
            def write(self, *a, **k): pass
            def __enter__(self): return self
            def __exit__(self, *a, **k): pass
        return DummyFile()
    return original_open(file, mode, *args, **kwargs)

builtins.open = mocked_open

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        step = json.loads(line)
        if step.get("type") == "PLANNER_RESPONSE" and "tool_calls" in step:
            for call in step["tool_calls"]:
                name = call.get("name")
                args = call.get("args", {})
                
                if name == "replace_file_content":
                    target_file = args.get("TargetFile", "")
                    if "sahabat_etf.js" in target_file:
                        target = args.get("TargetContent", "")
                        replacement = args.get("ReplacementContent", "")
                        if target in current_content:
                            current_content = current_content.replace(target, replacement)
                            print(f"Applied replace_file_content for {target[:20]}...")
                        else:
                            print(f"FAILED to match replace_file_content for {target[:20]}...")
                            
                elif name == "run_command":
                    cmd = args.get("CommandLine", "")
                    if "python" in cmd and ".py" in cmd:
                        # extract script name
                        match = re.search(r'python\s+([a-zA-Z0-9_\-\.]+\.py)', cmd)
                        if match:
                            script_name = match.group(1)
                            script_path = os.path.join("C:/Financehub", script_name)
                            
                            # We want to skip destructive/recovery scripts
                            if any(x in script_name for x in ["recover", "replay", "restore", "runner", "debug", "test_mock"]):
                                continue
                            if script_name in ["check_scripts.py", "find_origwidth.py", "find_killer.py", "find_skipped.py", "test_old_scripts.py", "fix_family_clean.py", "fix_family_clean2.py", "fix_family_table_single.py", "rewrite_func.py", "fix_syntax.py"]:
                                continue
                            
                            if os.path.exists(script_path):
                                print(f"Running {script_name}")
                                with original_open(script_path, "r", encoding="utf-8") as sf:
                                    code = sf.read()
                                try:
                                    exec(code, globals())
                                except Exception as e:
                                    print(f"Error in {script_name}: {e}")

builtins.open = original_open
with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(current_content)
print("Finished true recovery!")

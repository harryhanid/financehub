import re, base64, urllib.request, json

def get_mermaid_image():
    with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "r", encoding="utf-8") as f:
        text = f.read()
    
    match = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL)
    if not match:
        print("No mermaid code found")
        return
        
    mermaid_code = match.group(1).strip()
    
    # Create the state object expected by mermaid.ink
    state = {
        "code": mermaid_code,
        "mermaid": '{"theme": "default"}',
        "autoSync": True,
        "updateDiagram": True
    }
    
    # Compress and encode to base64 for mermaid.ink
    json_str = json.dumps(state)
    import zlib
    # Actually mermaid.ink uses base64 encoded string directly!
    # Wait, mermaid.ink accepts base64url of the raw text OR json.
    # Older mermaid.ink uses base64 of raw string.
    # Let's try base64 of json string!
    # No, mermaid.ink uses base64url encoding.
    encoded = base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8')
    url = f"https://mermaid.ink/img/{encoded}"
    
    try:
        urllib.request.urlretrieve(url, "C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.png")
        print("Success")
    except Exception as e:
        print(f"Error: {e}")

get_mermaid_image()

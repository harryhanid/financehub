import re, base64, urllib.request, urllib.error, json

def get_mermaid_image():
    with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "r", encoding="utf-8") as f:
        text = f.read()
    
    match = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL)
    if not match:
        return
        
    mermaid_code = match.group(1).strip()
    
    state = {
        "code": mermaid_code,
        "mermaid": '{"theme": "default"}',
        "autoSync": True,
        "updateDiagram": True
    }
    
    json_str = json.dumps(state)
    import zlib
    # pako deflate might be needed for mermaid.live but mermaid.ink supports raw base64url of JSON
    # let's try raw base64url of JSON
    # mermaid.ink uses base64url of json or pako deflated json.
    
    encoded = base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8').rstrip('=')
    url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=FFFFFF"
    
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    
    try:
        with urllib.request.urlopen(req) as response, open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.png", 'wb') as out_file:
            out_file.write(response.read())
        print("Success")
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read()}")
    except Exception as e:
        print(f"Error: {e}")

get_mermaid_image()

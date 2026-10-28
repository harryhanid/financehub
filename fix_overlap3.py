import re

def update_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Move Route and BgtReady into the subgraphs
    text = re.sub(r'(\s+)Finish\n\s+end', r'\1Finish\n\1Route\n    end', text)
    text = re.sub(r'(\s+)AppPAM\n\s+end', r'\1AppPAM\n\1BgtReady\n    end', text)
    
    # Remove their global definitions so they aren't floating outside
    text = re.sub(r'\s+Route{"\(Flow\) Cek Klasifikasi<br>Akhir"}\n', '\n', text)
    text = re.sub(r'\s+BgtReady\(\["\(Flow\) Pool Budget<br>Bertambah"\]\)\n', '\n', text)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

update_file("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md")
update_file("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html")

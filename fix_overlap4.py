import re

def update_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace("        Route\n    end", "        Route{\"[(]Flow[)] Cek Klasifikasi<br>Akhir\"}\n    end")
    text = text.replace("        BgtReady\n    end", "        BgtReady([\"[(]Flow[)] Pool Budget<br>Bertambah\"])\n    end")
    text = text.replace("[(]Flow[)]", "(Flow)")

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

update_file("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md")
update_file("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html")

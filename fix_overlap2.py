with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "r", encoding="utf-8") as f:
    text = f.read()

# Replace Route outside with Route inside FIN
text = text.replace("    Finish\n    end", "    Finish\n        Route\n    end")
text = text.replace("    Route{\"[(]Flow[)] Cek Klasifikasi<br>Akhir\"}\n", "")
text = text.replace("    BgtReady\n", "")
text = text.replace("    AppPAM\n    end", "    AppPAM\n        BgtReady\n    end")

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "w", encoding="utf-8") as f:
    f.write(text)

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("    Finish\n    end", "    Finish\n        Route\n    end")
html = html.replace("    Route{\"[(]Flow[)] Cek Klasifikasi<br>Akhir\"}\n", "")
html = html.replace("    BgtReady\n", "")
html = html.replace("    AppPAM\n    end", "    AppPAM\n        BgtReady\n    end")

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(html)

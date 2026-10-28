html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Light Theme</title>
  <style>
    body {
      margin: 0;
      padding: 2rem;
      background-color: #ffffff; /* Light background */
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      font-family: sans-serif;
    }
    .mermaid {
      background-color: #ffffff;
    }
  </style>
</head>
<body>
  
  <pre class="mermaid">
%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%
flowchart TD
    classDef fc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;
    classDef bc fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef fin fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef system fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph FC [1. Financial Controller - FC]
        direction TB
        PA["Buat Payment Application"] ::: fc
        PA_Class{"Klasifikasi PA:<br>Normal / With Memo"} ::: decision
        PropBgt["Ajukan Tambahan Budget"] ::: fc
    end

    subgraph BC [2. Budget Controller - BC]
        direction TB
        AppBgt["Review & Approve Budget"] ::: bc
        AppPAM["Review & Approve PAM<br>(With Memo)"] ::: bc
    end

    subgraph FIN [3. Finance Specialist - Fin]
        direction TB
        CreatePAM["Buat PAM dari PA"] ::: fin
        PAM_Class{"Klasifikasi PAM:<br>Revisi Normal / Memo?"} ::: decision
        CheckBgt{"Sistem Cek Budget:<br>Amount <= Sisa?"} ::: decision
        Block["PAM Diblokir Sistem"] ::: system
        Save["PAM Disimpan Sistem"] ::: system
        Finish(["Selesai / Ready to Pay"]) ::: system
    end

    PA --> PA_Class
    PA_Class --> CreatePAM
    
    CreatePAM --> PAM_Class
    PAM_Class --> CheckBgt
    
    CheckBgt -- "Tidak Cukup" --> Block
    Block --> PropBgt
    
    PropBgt --> AppBgt
    AppBgt --> |"Budget Aktif"| CheckBgt
    
    CheckBgt -- "Cukup" --> Save
    Save --> Route{"Cek Klasifikasi<br>Akhir"} ::: decision
    
    Route -- "Ada 'With Memo'<br>(dari PA atau PAM)" --> AppPAM
    Route -- "Keduanya Normal" --> Finish
    
    AppPAM --> Finish
  </pre>

  <script src="mermaid.min.js"></script>
  <script>
    if (typeof mermaid === 'undefined') {
        var script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js';
        script.onload = function() {
            mermaid.initialize({ startOnLoad: true, theme: 'default' });
        };
        document.head.appendChild(script);
    } else {
        mermaid.initialize({ startOnLoad: true, theme: 'default' });
    }
  </script>
</body>
</html>
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(html)

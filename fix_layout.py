html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Light Theme</title>
  <style>
    body {
      margin: 0;
      padding: 2rem;
      background-color: #ffffff; /* Tema Terang */
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      font-family: sans-serif;
    }
  </style>
</head>
<body>
  
  <pre class="mermaid">
flowchart TD
    %% Define the subgraphs WITHOUT direction TB to allow organic Dagre layout (atas-bawah)
    subgraph FC [1. Financial Controller - FC]
        PropBgt[Ajukan Tambahan Budget]
        PA[Buat Payment Application]
        PA_Class{Klasifikasi PA Normal atau With Memo}
    end

    subgraph BC [2. Budget Controller - BC]
        AppBgt[Review dan Approve Budget]
        AppPAM[Review dan Approve PAM With Memo]
    end

    subgraph FIN [3. Finance Specialist - Fin]
        CreatePAM[Buat PAM dari PA]
        PAM_Class{Klasifikasi PAM Revisi Normal atau Memo}
        CheckBgt{Sistem Cek Budget Amount vs Sisa}
        Block[PAM Diblokir Sistem]
        Save[PAM Disimpan Sistem]
        Finish([Selesai Ready to Pay])
    end

    Route{Cek Klasifikasi Akhir}

    PA --> PA_Class
    PA_Class --> CreatePAM
    CreatePAM --> PAM_Class
    PAM_Class --> CheckBgt
    CheckBgt -->|Tidak Cukup| Block
    Block --> PropBgt
    PropBgt --> AppBgt
    AppBgt -->|Budget Aktif| CheckBgt
    CheckBgt -->|Cukup| Save
    Save --> Route
    Route -->|Ada With Memo| AppPAM
    Route -->|Keduanya Normal| Finish
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

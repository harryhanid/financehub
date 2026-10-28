html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Mermaid</title>
</head>
<body style="margin: 0; padding: 2rem; background: #fff; font-family: sans-serif;">
  
  <h2 style="text-align: center; color: #333;">Workflow RBAC (Native Mermaid HTML)</h2>
  
  <pre class="mermaid" style="text-align: center;">
flowchart TD
    classDef fc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;
    classDef bc fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef fin fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef system fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;

    %% SWIMLANES (Kolom)
    subgraph FC [1. Financial Controller - FC]
        direction TB
        PA[Buat Payment Application] ::: fc
        PA_Class{Klasifikasi PA:\nNormal / With Memo} ::: decision
        PropBgt[Ajukan Tambahan Budget] ::: fc
    end

    subgraph BC [2. Budget Controller - BC]
        direction TB
        AppBgt[Review & Approve Budget] ::: bc
        AppPAM[Review & Approve PAM\n(With Memo)] ::: bc
    end

    subgraph FIN [3. Finance Specialist - Fin]
        direction TB
        CreatePAM[Buat PAM dari PA] ::: fin
        PAM_Class{Klasifikasi PAM:\nNormal / With Memo} ::: decision
        CheckBgt{Sistem Cek Budget:\nAmount <= Sisa?} ::: decision
        Block[PAM Diblokir Sistem] ::: system
        Save[PAM Disimpan Sistem] ::: system
        Finish([Selesai / Ready to Pay]) ::: system
    end

    %% ALUR PROSES
    PA --> PA_Class
    PA_Class --> CreatePAM
    
    CreatePAM --> PAM_Class
    PAM_Class --> CheckBgt
    
    CheckBgt -- Tidak Cukup --> Block
    Block --> PropBgt
    
    PropBgt --> AppBgt
    AppBgt --> |Budget Aktif| CheckBgt
    
    CheckBgt -- Cukup --> Save
    Save --> Route{Cek Klasifikasi\nAkhir} ::: decision
    
    Route -- Ada 'With Memo'\n(dari PA atau PAM) --> AppPAM
    Route -- Keduanya Normal --> Finish
    
    AppPAM --> Finish
  </pre>

  <script src="mermaid.min.js"></script>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'default' });
  </script>
</body>
</html>
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(html)

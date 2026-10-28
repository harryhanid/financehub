html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Light Theme</title>
  <style>
    body {
      margin: 0;
      padding: 2rem;
      background-color: #ffffff;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      font-family: sans-serif;
    }
    .legend {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1rem 1.5rem;
      margin-bottom: 2rem;
      width: 100%;
      max-width: 800px;
    }
    .legend h3 { margin-top: 0; color: #334155; }
    .legend ul { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
    .legend li { display: flex; align-items: center; font-size: 14px; color: #475569; }
    .dot { width: 14px; height: 14px; border-radius: 50%; margin-right: 8px; display: inline-block; border: 2px solid; }
    
    /* Colors */
    .fc { background: #e3f2fd; border-color: #1976d2; }
    .bc { background: #fff3e0; border-color: #f57c00; }
    .fin { background: #f3e5f5; border-color: #8e24aa; }
    .dec { background: #fff9c4; border-color: #fbc02d; }
    .sys { background: #f9f9f9; border-color: #333; border-style: dashed; }
    .end { background: #dcfce7; border-color: #16a34a; }
  </style>
</head>
<body>
  
  <div class="legend">
    <h3>📌 Legenda Warna (Role & Fungsi)</h3>
    <ul>
      <li><span class="dot fc"></span> Financial Controller (FC)</li>
      <li><span class="dot bc"></span> Budget Controller (BC)</li>
      <li><span class="dot fin"></span> Finance Specialist (Fin)</li>
      <li><span class="dot dec"></span> Keputusan / Pengecekan Sistem</li>
      <li><span class="dot sys"></span> Proses Sistem Otomatis</li>
      <li><span class="dot end"></span> Selesai / Hasil Akhir</li>
    </ul>
  </div>

  <pre class="mermaid">
flowchart TD
    %% Define Nodes
    PA["(FC) Buat Payment Application"]
    PA_Class{"(FC) Klasifikasi PA:<br>Normal / With Memo"}
    
    NewBgt["(FC) Pengajuan Budget Baru"]
    AddBgt["(FC) Pengajuan Tambahan Budget<br>(Karena PAM Diblokir)"]

    AppNewBgt["(BC) Review & Approve<br>Budget Baru"]
    AppAddBgt["(BC) Review & Approve<br>Tambahan Budget"]
    AppPAM["(BC) Review & Approve PAM<br>(With Memo)"]

    CreatePAM["(Fin) Buat PAM dari PA"]
    PAM_Class{"(Fin) Klasifikasi PAM:<br>Normal / With Memo"}
    CheckBgt{"(Sistem) Cek Budget:<br>Amount <= Sisa?"}
    Block["(Sistem) PAM Diblokir Sistem<br>(Sisa Kurang / Expired)"]
    Save["(Sistem) PAM Disimpan Sistem"]
    Finish(["(Sistem) Selesai / Ready to Pay"])

    Route{"(Sistem) Cek Klasifikasi<br>Akhir"}
    BgtReady(["(Sistem) Pool Budget<br>Bertambah"])

    %% Subgraphs
    subgraph FC [1. Financial Controller - FC]
        NewBgt
        PA
        PA_Class
        AddBgt
    end

    subgraph BC [2. Budget Controller - BC]
        AppNewBgt
        AppAddBgt
        AppPAM
    end

    subgraph FIN [3. Finance Specialist - Fin]
        CreatePAM
        PAM_Class
        CheckBgt
        Block
        Save
        Finish
    end

    %% Flow: Budget Baru
    NewBgt --> AppNewBgt
    AppNewBgt -->|"Approve"| BgtReady

    %% Flow: Payment Memo
    PA --> PA_Class
    PA_Class --> CreatePAM
    CreatePAM --> PAM_Class
    PAM_Class --> CheckBgt
    
    %% Loop Cek Budget & Tambahan Budget
    CheckBgt -->|"Tidak Cukup"| Block
    Block --> AddBgt
    AddBgt --> AppAddBgt
    AppAddBgt -->|"Approve"| CheckBgt
    
    %% Lanjut Approval PAM
    CheckBgt -->|"Cukup"| Save
    Save --> Route
    Route -->|"Ada With Memo"| AppPAM
    Route -->|"Keduanya Normal"| Finish
    AppPAM --> Finish

    classDef fc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef bc fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef fin fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    classDef system fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    classDef endnode fill:#dcfce7,stroke:#16a34a,stroke-width:2px

    class PA,NewBgt,AddBgt fc
    class AppNewBgt,AppAddBgt,AppPAM bc
    class CreatePAM fin
    class PA_Class,PAM_Class,CheckBgt,Route decision
    class Block,Save system
    class Finish,BgtReady endnode
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

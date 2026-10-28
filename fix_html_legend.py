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

    classDef fc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef bc fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef fin fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    classDef system fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    classDef endnode fill:#dcfce7,stroke:#16a34a,stroke-width:2px

    class PA,PropBgt fc
    class AppBgt,AppPAM bc
    class CreatePAM,Finish fin
    class PA_Class,PAM_Class,CheckBgt,Route decision
    class Block,Save system
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

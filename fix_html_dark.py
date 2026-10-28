html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Dark Theme</title>
  <style>
    body {
      margin: 0;
      padding: 2rem;
      background-color: #1e1e1e; /* Dark background matching the screenshot */
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }
    .mermaid {
      background-color: #1e1e1e;
    }
  </style>
</head>
<body>
  
  <pre class="mermaid">
flowchart TD
    subgraph FC [1. Financial Controller - FC]
        PropBgt[Ajukan Tambahan Budget]
        PA[Buat Payment Application]
        PA_Class{Klasifikasi PA:\nNormal / With Memo}
    end

    Route{Cek Klasifikasi\nAkhir}

    subgraph BC [2. Budget Controller - BC]
        AppPAM[Review & Approve PAM\n(With Memo)]
        AppBgt[Review & Approve Budget]
    end

    subgraph FIN [3. Finance Specialist - Fin]
        CreatePAM[Buat PAM dari PA]
        Finish([Selesai / Ready to Pay])
        PAM_Class{Klasifikasi PAM:\nNormal / With Memo}
        CheckBgt{Sistem Cek Budget:\nAmount <= Sisa?}
        Block[PAM Diblokir Sistem]
        Save[PAM Disimpan Sistem]
    end

    PA --> PA_Class
    PA_Class --> CreatePAM
    
    CreatePAM --> PAM_Class
    PAM_Class --> CheckBgt
    
    CheckBgt -- Tidak Cukup --> Block
    CheckBgt -- Cukup --> Save
    
    Block --> PropBgt
    PropBgt --> AppBgt
    AppBgt --> CheckBgt
    
    Save --> Route
    Route -- Ada 'With Memo'\n(dari PA atau PAM) --> AppPAM
    Route -- Keduanya Normal --> Finish
    
    AppPAM --> Finish
  </pre>

  <!-- Menggunakan versi CDN mermaid terbaru sebagai fallback jika lokal gagal, 
       atau file lokal jika di-buka dari file:/// -->
  <script src="mermaid.min.js"></script>
  <script>
    if (typeof mermaid === 'undefined') {
        var script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js';
        script.onload = function() {
            mermaid.initialize({ startOnLoad: true, theme: 'dark' });
        };
        document.head.appendChild(script);
    } else {
        mermaid.initialize({ startOnLoad: true, theme: 'dark' });
    }
  </script>
</body>
</html>
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(html)

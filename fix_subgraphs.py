md_path = "C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md"
with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

import re
mermaid = """flowchart TD
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
    CheckBgt{"(Flow) Cek Budget:<br>Amount <= Sisa?"}
    Block["(Flow) PAM Diblokir Sistem<br>(Sisa Kurang / Expired)"]
    Save["(Flow) PAM Disimpan Sistem"]
    Finish(["(Flow) Selesai / Ready to Pay"])

    Route{"(Flow) Cek Klasifikasi<br>Akhir"}
    BgtReady(["(Flow) Pool Budget<br>Bertambah"])

    %% Flow: Budget Baru (Independent)
    NewBgt --> AppNewBgt
    AppNewBgt -->|"Approve"| BgtReady

    %% Flow: Payment Memo
    PA --> PA_Class
    PA_Class --> CreatePAM
    CreatePAM --> PAM_Class
    PAM_Class --> CheckBgt
    
    %% Cek Budget & Tambahan Budget (Loop)
    CheckBgt -->|"Tidak Cukup"| Block
    Block --> AddBgt
    AddBgt --> AppAddBgt
    AppAddBgt -->|"Approve"| CheckBgt
    
    %% Lanjut ke Approval PAM
    CheckBgt -->|"Cukup"| Save
    Save --> Route
    Route -->|"Ada With Memo"| AppPAM
    Route -->|"Keduanya Normal"| Finish
    AppPAM --> Finish

    %% Define Colors / Styles
    classDef fc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef bc fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef fin fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    classDef system fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    classDef endnode fill:#dcfce7,stroke:#16a34a,stroke-width:2px

    %% Apply Classes
    class PA,NewBgt,AddBgt fc
    class AppNewBgt,AppAddBgt,AppPAM bc
    class CreatePAM fin
    class PA_Class,PAM_Class,CheckBgt,Route decision
    class Block,Save system
    class Finish,BgtReady endnode
"""

new_text = re.sub(r'flowchart TD.*class Finish,BgtReady endnode\n', mermaid, text, flags=re.DOTALL)
with open(md_path, "w", encoding="utf-8") as f:
    f.write(new_text)

html_path = "C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()
new_html = re.sub(r'flowchart TD.*class Block,Save system\n', mermaid, html, flags=re.DOTALL)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_html)

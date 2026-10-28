with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "r", encoding="utf-8") as f:
    text = f.read()

new_content = """# Rancangan Sistem Alur (Roles & Workflow)

Berikut adalah gambaran alur sistem (System Flow) komprehensif yang melibatkan *Role-Based Access Control* (RBAC) dan proses persetujuan (Approval) berdasarkan peran: **FC** (Financial Controller), **BC** (Budget Controller), dan **Fin** (Finance Specialist).

```mermaid
flowchart TD
    %% Define Styles
    classDef fc fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;
    classDef fin fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px;
    classDef bc fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef system fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;

    %% Nodes
    subgraph FC [Financial Controller]
        PA[Buat Payment Application] ::: fc
        ClassifyPA{Klasifikasi PA:\nNormal / With Memo} ::: decision
        InputBudget[Input/Ajukan Tambahan Budget] ::: fc
    end

    subgraph FIN [Finance Specialist]
        CreatePAM[Buat PAM dari PA] ::: fin
        ClassifyPAM{Klasifikasi PAM:\nNormal / With Memo} ::: decision
    end

    subgraph SYSTEM [System Validation]
        BudgetCheck{Cek Sisa Budget:\nTagihan <= Sisa?} ::: decision
        BlockPAM[Blokir Penyimpanan PAM!\nSisa Budget Tidak Cukup] ::: system
        SavePAM[Simpan PAM & Payment] ::: system
        Finish[Selesai / Ready to Pay] ::: system
    end

    subgraph BC [Budget Controller]
        ApproveBudget[Review & Approve Budget] ::: bc
        ApprovePAM[Review & Approve PAM\n(With Memo)] ::: bc
    end

    %% Flow - Budgeting
    InputBudget --> ApproveBudget
    ApproveBudget --> |Budget Aktif| BudgetCheck

    %% Flow - PA
    PA --> ClassifyPA
    ClassifyPA --> CreatePAM

    %% Flow - PAM & Budget Check
    CreatePAM --> ClassifyPAM
    ClassifyPAM --> BudgetCheck
    BudgetCheck -- Tidak Cukup --> BlockPAM
    BlockPAM -.-> |Membutuhkan Tambahan| InputBudget
    BudgetCheck -- Cukup --> SavePAM

    %% Flow - Routing Approval PAM
    SavePAM --> RouteApproval{Apakah PA atau PAM\n'With Memo'?} ::: decision
    RouteApproval -- Ya (With Memo) --> ApprovePAM
    RouteApproval -- Tidak (Keduanya Normal) --> Finish
    ApprovePAM --> |Approved| Finish
```

## Pembagian Tugas & Wewenang (RBAC):

### 1. FC (Financial Controller)
*   **Pembuat Payment Application (PA)**: Menginisiasi pengajuan pembayaran.
*   **Klasifikasi PA**: Menentukan sejak awal apakah transaksi PA ini "Normal" atau "With Memo".
*   **Pengelola Budget**: Menginput budget baru atau mengajukan tambahan budget apabila saat proses PAM ternyata Sisa Budget kurang/expired.

### 2. Fin (Finance Specialist)
*   **Pembuat Payment Approval Memo (PAM)**: Memproses PA yang diajukan oleh FC menjadi dokumen PAM.
*   **Klasifikasi PAM**: Berwenang merevisi klasifikasi di level PAM (misal PA awalnya "Normal", namun oleh Fin diubah menjadi "With Memo").

### 3. BC (Budget Controller)
*   **Otoritas Budget**: Melakukan persetujuan (*approval*) terhadap budget yang diajukan oleh FC sebelum budget tersebut aktif dan dapat digunakan.
*   **Otoritas Transaksi Khusus**: Melakukan *review* dan persetujuan akhir terhadap semua dokumen PAM yang memiliki klasifikasi "With Memo" (baik klasifikasi itu datang dari turunan PA si FC, ataupun diubah langsung oleh si Fin).

## Logika Pengecekan Budget:
Saat Fin mencoba menyimpan PAM, sistem akan mengecek ketersediaan plafon. Jika **Sisa Budget < Nominal PAM**, maka sistem memblokir PAM. Fin tidak dapat melanjutkan proses. Alur akan berbalik ke **FC**, di mana FC harus menginput usulan tambahan budget, yang kemudian harus di-*approve* oleh **BC** terlebih dahulu. Setelah budget baru aktif, barulah **Fin** bisa melanjutkan proses simpan PAM tersebut.
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/system_flowchart.md", "w", encoding="utf-8") as f:
    f.write(new_content)

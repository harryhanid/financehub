new_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Swimlane</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    .node-card { transition: all 0.2s ease-in-out; }
    .node-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .arrow-down { font-size: 1.5rem; color: #9ca3af; line-height: 1; text-align: center; margin: 0.5rem 0; font-weight: bold; }
    .arrow-right { font-size: 1.5rem; color: #9ca3af; font-weight: bold; }
    .arrow-left { font-size: 1.5rem; color: #9ca3af; font-weight: bold; }
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-6 font-sans">
  
  <div class="max-w-6xl mx-auto bg-[var(--card)] border border-[var(--border)] rounded-2xl shadow-sm overflow-x-auto">
    
    <!-- Header -->
    <div class="p-6 border-b border-[var(--border)] bg-[var(--background)] sticky left-0">
      <h2 class="text-2xl font-bold text-[var(--foreground)]">Alur Sistem & Persetujuan Dokumen</h2>
      <p class="text-[var(--muted-foreground)] mt-1">Pembagian tugas (Swimlane) antara Financial Controller (FC), Budget Controller (BC), dan Finance Specialist (Fin).</p>
    </div>

    <!-- Swimlane Grid -->
    <div class="grid grid-cols-3 min-w-[900px]">
      
      <!-- Kolom FC -->
      <div class="border-r border-[var(--border)] bg-blue-50/30">
        <div class="bg-blue-600 text-white font-semibold p-4 text-center shadow-sm">
          1. Financial Controller (FC)
        </div>
        <div class="p-6 flex flex-col items-center">
          
          <div class="node-card w-full max-w-xs bg-white border-2 border-blue-200 rounded-xl p-4 text-center">
            <div class="text-xs font-bold text-blue-600 uppercase tracking-wide mb-1">Mulai</div>
            <div class="font-semibold text-gray-800">Buat Payment Application (PA)</div>
          </div>
          
          <div class="arrow-down">↓</div>

          <div class="node-card w-full max-w-xs bg-yellow-50 border-2 border-yellow-300 rounded-xl p-4 text-center relative">
            <div class="text-xs font-bold text-yellow-600 uppercase tracking-wide mb-1">Keputusan</div>
            <div class="font-semibold text-gray-800">Klasifikasi PA:<br><span class="text-gray-500 font-normal">Normal / With Memo</span></div>
            <!-- Arrow to Right -->
            <div class="absolute -right-12 top-1/2 -translate-y-1/2 flex items-center gap-1 z-10 w-12 justify-center">
              <span class="arrow-right">→</span>
            </div>
          </div>

          <!-- Padded spacer to align with bottom rows -->
          <div style="height: 280px;"></div>

          <div class="node-card w-full max-w-xs bg-red-50 border-2 border-red-200 rounded-xl p-4 text-center relative">
            <div class="text-xs font-bold text-red-600 uppercase tracking-wide mb-1">Kekurangan Budget</div>
            <div class="font-semibold text-gray-800">Ajukan Tambahan Budget</div>
            
            <div class="arrow-down absolute -bottom-10 left-1/2 -translate-x-1/2">↓</div>
          </div>

        </div>
      </div>

      <!-- Kolom BC -->
      <div class="border-r border-[var(--border)] bg-orange-50/30">
        <div class="bg-orange-500 text-white font-semibold p-4 text-center shadow-sm">
          2. Budget Controller (BC)
        </div>
        <div class="p-6 flex flex-col items-center">
          
          <div style="height: 485px;"></div>

          <div class="node-card w-full max-w-xs bg-white border-2 border-orange-200 rounded-xl p-4 text-center relative">
            <div class="text-xs font-bold text-orange-600 uppercase tracking-wide mb-1">Persetujuan Budget</div>
            <div class="font-semibold text-gray-800">Review & Approve Budget</div>
            <div class="absolute -right-12 top-1/2 -translate-y-1/2 flex items-center gap-1 z-10 w-12 justify-center text-green-500">
              <span class="text-[0.65rem] absolute -top-4 font-bold">Approved</span>
              <span class="arrow-right text-green-500">→</span>
            </div>
          </div>

          <div style="height: 120px;"></div>

          <div class="node-card w-full max-w-xs bg-white border-2 border-orange-200 rounded-xl p-4 text-center relative">
            <div class="text-xs font-bold text-orange-600 uppercase tracking-wide mb-1">Otorisasi Akhir</div>
            <div class="font-semibold text-gray-800">Review & Approve PAM<br><span class="text-gray-500 font-normal">(With Memo)</span></div>
            <div class="arrow-down absolute -bottom-10 left-1/2 -translate-x-1/2 text-green-500">↓</div>
          </div>

        </div>
      </div>

      <!-- Kolom FIN -->
      <div class="bg-purple-50/30">
        <div class="bg-purple-600 text-white font-semibold p-4 text-center shadow-sm">
          3. Finance Specialist (Fin)
        </div>
        <div class="p-6 flex flex-col items-center">
          
          <div style="height: 120px;"></div>

          <div class="node-card w-full max-w-xs bg-white border-2 border-purple-200 rounded-xl p-4 text-center">
            <div class="text-xs font-bold text-purple-600 uppercase tracking-wide mb-1">Proses Transaksi</div>
            <div class="font-semibold text-gray-800">Buat PAM dari PA</div>
          </div>
          
          <div class="arrow-down">↓</div>

          <div class="node-card w-full max-w-xs bg-yellow-50 border-2 border-yellow-300 rounded-xl p-4 text-center">
            <div class="text-xs font-bold text-yellow-600 uppercase tracking-wide mb-1">Keputusan</div>
            <div class="font-semibold text-gray-800">Klasifikasi PAM:<br><span class="text-gray-500 font-normal">Revisi Normal / With Memo?</span></div>
          </div>

          <div class="arrow-down">↓</div>
          
          <div class="node-card w-full max-w-xs bg-gray-100 border-2 border-gray-300 rounded-xl p-4 text-center border-dashed relative">
            <div class="text-xs font-bold text-gray-600 uppercase tracking-wide mb-1">Sistem</div>
            <div class="font-semibold text-gray-800">Cek Sisa Budget Aktif</div>
            
            <div class="arrow-down absolute -bottom-10 left-1/4 -translate-x-1/2 text-red-500">↓</div>
            <div class="arrow-down absolute -bottom-10 right-1/4 translate-x-1/2 text-green-500">↓</div>
          </div>
          
          <div style="height: 40px;"></div>

          <div class="flex w-full gap-4 max-w-xs">
            <div class="w-1/2 flex flex-col items-center relative">
              <div class="node-card w-full bg-red-100 border-2 border-red-400 rounded-xl p-3 text-center">
                <div class="font-bold text-red-700 text-sm">Tidak Cukup</div>
                <div class="text-xs text-red-600">Sistem memblokir PAM</div>
              </div>
              <div class="absolute -left-[530px] top-1/2 -translate-y-1/2 flex items-center z-10 w-[530px] justify-center text-red-500">
                <span class="arrow-left text-red-500">←</span>
                <div class="h-[2px] w-full bg-red-500"></div>
              </div>
            </div>
            
            <div class="w-1/2 flex flex-col items-center">
              <div class="node-card w-full bg-green-100 border-2 border-green-400 rounded-xl p-3 text-center">
                <div class="font-bold text-green-700 text-sm">Cukup</div>
                <div class="text-xs text-green-600">Sistem menyimpan PAM</div>
              </div>
              <div class="arrow-down">↓</div>
            </div>
          </div>
          
          <div class="node-card w-full max-w-xs bg-yellow-50 border-2 border-yellow-300 rounded-xl p-4 text-center ml-auto mr-0 w-1/2 relative">
            <div class="text-xs font-bold text-yellow-600 uppercase tracking-wide mb-1">Routing</div>
            <div class="font-semibold text-gray-800">Cek 'With Memo'</div>
            
            <div class="absolute -left-12 top-1/2 -translate-y-1/2 flex items-center gap-1 z-10 w-12 justify-center text-orange-500">
              <span class="text-[0.6rem] absolute -top-4 font-bold w-[100px] text-center left-[-30px]">Ya (With Memo)</span>
              <span class="arrow-left text-orange-500">←</span>
            </div>
            
            <div class="arrow-down absolute -bottom-10 left-1/2 -translate-x-1/2 text-green-500">↓</div>
          </div>
          
          <div style="height: 40px;"></div>

          <div class="node-card w-full max-w-xs bg-green-500 border-2 border-green-600 rounded-xl p-4 text-center ml-auto mr-0 w-1/2 shadow-md relative">
            <span class="text-[0.6rem] absolute -top-4 right-0 font-bold w-[100px] text-center text-green-600">Tidak (Normal)</span>
            <div class="font-bold text-white uppercase tracking-wider">Selesai</div>
          </div>

          <div class="absolute -left-[300px] bottom-10 flex items-center z-10 w-[300px] justify-end text-green-500">
            <div class="h-[2px] w-full bg-green-500"></div>
            <span class="arrow-right text-green-500">→</span>
          </div>

        </div>
      </div>

    </div>
  </div>
</body>
</html>
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(new_html)

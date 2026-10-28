html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>System Workflow - Grid</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body { font-family: sans-serif; background: #f8fafc; margin: 0; padding: 2rem; }
    .table-grid {
      display: grid;
      grid-template-columns: 240px 60px 240px 60px 240px;
      gap: 0px;
      justify-content: center;
      margin-top: 2rem;
    }
    .cell { display: flex; align-items: center; justify-center: center; position: relative; justify-content: center; min-height: 50px; }
    
    /* Nodes */
    .proc { border: 2px solid; border-radius: 8px; padding: 12px; text-align: center; font-weight: 600; font-size: 14px; width: 200px; z-index: 10; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .proc-fc { border-color: #3b82f6; color: #1e40af; background: #eff6ff; }
    .proc-fin { border-color: #a855f7; color: #6b21a8; background: #faf5ff; }
    .proc-bc { border-color: #f97316; color: #9a3412; background: #fff7ed; }
    .proc-sys { border-color: #6b7280; color: #374151; background: #f9fafb; border-style: dashed; }
    .proc-end { border-color: #22c55e; color: #14532d; background: #f0fdf4; border-radius: 99px; }

    /* Diamonds */
    .diamond-wrap { position: relative; width: 200px; height: 120px; display: flex; align-items: center; justify-content: center; z-index: 10; }
    .diamond-bg { position: absolute; width: 100%; height: 100%; z-index: 0; }
    .diamond-bg polygon { fill: #fefce8; stroke: #eab308; stroke-width: 2; }
    .diamond-bg.sys polygon { fill: #f9fafb; stroke: #6b7280; stroke-dasharray: 4; }
    .diamond-text { position: relative; z-index: 1; text-align: center; font-size: 13px; font-weight: 600; padding: 0 20px; }

    /* Arrows */
    .arrow-v { width: 2px; height: 100%; background: #9ca3af; position: absolute; }
    .arrow-v::after { content: ''; position: absolute; bottom: 0; left: -4px; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 8px solid #9ca3af; }
    
    .arrow-h { width: 100%; height: 2px; background: #9ca3af; position: absolute; }
    .arrow-h.right::after { content: ''; position: absolute; right: 0; top: -4px; border-top: 5px solid transparent; border-bottom: 5px solid transparent; border-left: 8px solid #9ca3af; }
    .arrow-h.left::after { content: ''; position: absolute; left: 0; top: -4px; border-top: 5px solid transparent; border-bottom: 5px solid transparent; border-right: 8px solid #9ca3af; }

    .line-v { width: 2px; height: 100%; background: #9ca3af; position: absolute; }
    .line-h { width: 100%; height: 2px; background: #9ca3af; position: absolute; }

    /* Labels */
    .lbl { position: absolute; background: white; padding: 2px 6px; font-size: 11px; color: #4b5563; font-weight: 600; border-radius: 4px; border: 1px solid #e5e7eb; z-index: 5; white-space: nowrap; }
    .lbl-right { left: 50%; transform: translateX(-50%) translateY(-15px); }
  </style>
</head>
<body>

  <div class="max-w-6xl mx-auto bg-white border border-gray-200 rounded-xl shadow-sm p-8">
    <h2 class="text-2xl font-bold text-gray-800 text-center mb-6">Workflow RBAC (Bentuk Standar Flowchart)</h2>
    
    <!-- Header Swimlane -->
    <div class="grid grid-cols-3 gap-0 max-w-[840px] mx-auto text-center font-bold text-white mb-4">
      <div class="bg-blue-600 py-2 rounded-l-lg mr-[30px]">Financial Controller</div>
      <div class="bg-orange-500 py-2 mx-[30px]">Budget Controller</div>
      <div class="bg-purple-600 py-2 rounded-r-lg ml-[30px]">Finance Specialist</div>
    </div>

    <!-- The Grid -->
    <div class="table-grid">
      <!-- Row 1 -->
      <div class="cell"><div class="proc proc-fc">Buat Payment Application</div></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div><div class="cell"></div>

      <!-- Row 2 -->
      <div class="cell h-10"><div class="arrow-v"></div></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div><div class="cell"></div>

      <!-- Row 3 -->
      <div class="cell">
        <div class="diamond-wrap">
          <svg class="diamond-bg" viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points="50,2 98,50 50,98 2,50"/></svg>
          <div class="diamond-text text-yellow-800">Klasifikasi PA<br><span class="text-[11px] font-normal text-yellow-700">Normal / Memo</span></div>
        </div>
      </div>
      <div class="cell"><div class="arrow-h right"></div></div>
      <div class="cell"><div class="line-h"></div></div>
      <div class="cell"><div class="arrow-h right"></div></div>
      <div class="cell"><div class="proc proc-fin">Buat PAM dari PA</div></div>

      <!-- Row 4 -->
      <div class="cell h-10"></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      <div class="cell h-10"><div class="arrow-v"></div></div>

      <!-- Row 5 -->
      <div class="cell"></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      <div class="cell">
        <div class="diamond-wrap">
          <svg class="diamond-bg" viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points="50,2 98,50 50,98 2,50"/></svg>
          <div class="diamond-text text-yellow-800">Klasifikasi PAM<br><span class="text-[11px] font-normal text-yellow-700">Revisi Normal / Memo?</span></div>
        </div>
      </div>

      <!-- Row 6 -->
      <div class="cell h-10"></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      <div class="cell h-10"><div class="arrow-v"></div></div>

      <!-- Row 7 -->
      <div class="cell"><div class="proc proc-fc">Ajukan Tambahan Budget</div></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      <div class="cell">
        <div class="diamond-wrap">
          <svg class="diamond-bg sys" viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points="50,2 98,50 50,98 2,50"/></svg>
          <div class="diamond-text">Cek Sisa Budget<br><span class="text-[11px] font-normal">Amount <= Sisa?</span></div>
        </div>
      </div>

      <!-- Row 8 -->
      <div class="cell h-16"><div class="arrow-v"></div></div>
      <div class="cell"></div><div class="cell"></div>
      <div class="cell relative">
        <div class="arrow-h left" style="width:50%; right:0;"></div>
        <div class="line-h" style="width:100%; top:50%; right:0;"></div>
        <div class="line-v" style="height:50%; top:0; left:50%;"></div>
        <span class="lbl" style="top:-10px; right:10px; color:#dc2626">Tdk Cukup</span>
      </div>
      <div class="cell h-16"><div class="arrow-v" style="height:100%"></div><span class="lbl" style="left:50%;top:50%;transform:translate(-50%,-50%);color:#16a34a">Cukup</span></div>

      <!-- Row 9 -->
      <div class="cell"></div>
      <div class="cell">
        <div class="line-h" style="width:50%; left:0;"></div>
        <div class="line-v" style="height:50%; bottom:0; right:50%;"></div>
        <div class="arrow-h right" style="width:50%; right:0;"></div>
      </div>
      <div class="cell"><div class="proc proc-bc">Review & Approve Budget</div></div>
      <div class="cell relative"><div class="arrow-h right"></div><span class="lbl" style="top:-10px;">Budget Aktif</span></div>
      <div class="cell"><div class="proc proc-sys">Simpan PAM</div></div>

      <!-- Row 10 -->
      <div class="cell h-10"></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      <div class="cell h-10"><div class="arrow-v"></div></div>

      <!-- Row 11 -->
      <div class="cell"></div>
      <div class="cell"></div><div class="cell"></div><div class="cell"></div>
      <div class="cell">
        <div class="diamond-wrap">
          <svg class="diamond-bg" viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points="50,2 98,50 50,98 2,50"/></svg>
          <div class="diamond-text text-yellow-800">Routing Approval<br><span class="text-[11px] font-normal text-yellow-700">Ada 'With Memo'?</span></div>
        </div>
      </div>

      <!-- Row 12 -->
      <div class="cell h-16"></div>
      <div class="cell"></div>
      <div class="cell"></div>
      <div class="cell relative"><div class="arrow-h left"></div><span class="lbl" style="top:-10px; white-space:nowrap;">Ya (With Memo)</span></div>
      <div class="cell h-16 relative"><div class="arrow-v"></div><span class="lbl" style="top:50%; left:50%; transform:translate(-50%,-50%)">Tidak (Normal)</span></div>

      <!-- Row 13 -->
      <div class="cell"></div>
      <div class="cell"></div>
      <div class="cell"><div class="proc proc-bc">Review & Approve PAM</div></div>
      <div class="cell"></div>
      <div class="cell"><div class="proc proc-end">Selesai</div></div>

      <!-- Row 14 -->
      <div class="cell h-10"></div>
      <div class="cell"></div>
      <div class="cell h-10 relative"><div class="line-v"></div></div>
      <div class="cell relative"><div class="arrow-h right"></div><div class="line-h" style="width:50%; right:0;"></div><div class="line-v" style="height:50%; bottom:50%; left:0;"></div></div>
      <div class="cell"></div>

    </div>

  </div>

</body>
</html>
"""

with open("C:/Users/25010160/.gemini/antigravity/brain/ee41c5ca-9ca2-43eb-ad90-8257e8262bb6/workflow_diagram.html", "w", encoding="utf-8") as f:
    f.write(html)

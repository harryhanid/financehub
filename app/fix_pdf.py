import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_func = """  async function exportTreePDF() {
    if (!treeChartInstance) return;
    showToast("Mempersiapkan PDF... Memotong area kosong agar maksimal.", "info");
    
    if (typeof html2pdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }"""

new_func = """  async function exportTreePDF() {
    if (!treeChartInstance) return;
    showToast("Mempersiapkan PDF... Memotong area kosong agar maksimal.", "info");
    
    if (typeof window.jspdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }"""

if old_func in content:
    content = content.replace(old_func, new_func)
    print("Replaced script loader successfully!")
else:
    print("Could not find script loader block!")

old_export = """    let img = new Image();
    img.onload = function() {
        if (img.height > img.width) {
            opt.jsPDF.orientation = 'portrait';
        }
        
        let container = document.createElement('div');
        container.style.width = '100%';
        container.style.textAlign = 'center';
        
        let pdfImg = document.createElement('img');
        pdfImg.src = imgData;
        pdfImg.style.maxWidth = '100%';
        container.appendChild(pdfImg);
        
        html2pdf().set(opt).from(container).save().then(() => {
            showToast("PDF berhasil diunduh!", "success");
        });
    };
    img.src = imgData;
  }"""

new_export = """    let img = new Image();
    img.onload = function() {
        const { jsPDF } = window.jspdf;
        let orientation = img.height > img.width ? 'portrait' : 'landscape';
        let doc = new jsPDF({
            orientation: orientation,
            unit: 'mm',
            format: 'a4'
        });
        
        let pdfW = doc.internal.pageSize.getWidth();
        let pdfH = doc.internal.pageSize.getHeight();
        let margin = 10; // 10mm margin
        let maxW = pdfW - (margin * 2);
        let maxH = pdfH - (margin * 2);
        
        let ratio = Math.min(maxW / img.width, maxH / img.height);
        let finalW = img.width * ratio;
        let finalH = img.height * ratio;
        
        let x = (pdfW - finalW) / 2;
        let y = (pdfH - finalH) / 2;
        
        doc.addImage(imgData, 'JPEG', x, y, finalW, finalH);
        doc.save('Sahabat_ETF_Tree.pdf');
        
        showToast("PDF berhasil diunduh!", "success");
    };
    img.src = imgData;
  }"""

# Remove the let opt = {...} block because we don't need it anymore
content = re.sub(r"let opt = \{[\s\S]*?\};\s*let img =", "let img =", content)

if old_export in content:
    content = content.replace(old_export, new_export)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced PDF generation logic successfully!")
else:
    print("Could not find PDF generation block!")

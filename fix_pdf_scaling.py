import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r"""            // Backup original state
            const origWidth = parent\.style\.width;
            const origHeight = parent\.style\.height;
            const origAspectRatio = chart\.options\.maintainAspectRatio;
            const origPixelRatio = chart\.options\.devicePixelRatio;

            // Virtual layout configuration
            // 850x450 makes the text proportionally much larger
            parent\.style\.width = "850px"; 
            parent\.style\.height = "450px";
            chart\.options\.maintainAspectRatio = false;
            chart\.options\.devicePixelRatio = 3; // 3x resolution for crispness
            
            // Apply layout changes
            chart\.update\(\);
            chart\.resize\(\);
            
            const img = document\.createElement\("img"\);
            img\.src = chart\.toBase64Image\(\);
            
            // Restore original state
            parent\.style\.width = origWidth;
            parent\.style\.height = origHeight;
            chart\.options\.maintainAspectRatio = origAspectRatio !== undefined \? origAspectRatio : true;
            chart\.options\.devicePixelRatio = origPixelRatio || window\.devicePixelRatio;
            
            // Apply original state
            chart\.update\(\);
            chart\.resize\(\);"""

repl = """            // Backup original state
            const origWidth = parent.style.width;
            const origHeight = parent.style.height;
            const origPos = parent.style.position;
            const origMaxWidth = parent.style.maxWidth;
            const origAspectRatio = chart.options.maintainAspectRatio;
            const origPixelRatio = chart.options.devicePixelRatio;

            // Force exact layout ignoring CSS constraints
            parent.style.position = "absolute";
            parent.style.maxWidth = "none";
            parent.style.width = "850px"; 
            parent.style.height = "500px";
            chart.options.maintainAspectRatio = false;
            chart.options.devicePixelRatio = 3; 
            
            // Apply layout changes SYNCHRONOUSLY
            chart.resize();
            chart.update('none');
            
            const img = document.createElement("img");
            img.src = chart.toBase64Image();
            
            // Restore original state
            parent.style.position = origPos;
            parent.style.maxWidth = origMaxWidth;
            parent.style.width = origWidth;
            parent.style.height = origHeight;
            chart.options.maintainAspectRatio = origAspectRatio !== undefined ? origAspectRatio : true;
            chart.options.devicePixelRatio = origPixelRatio || window.devicePixelRatio;
            
            // Apply original state SYNCHRONOUSLY
            chart.resize();
            chart.update('none');"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated virtual layout scaling logic!")

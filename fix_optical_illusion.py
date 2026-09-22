import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: niceMax explicitly sets the max axis values
target_grace = r'if \(scales\.y\) \{\n\s*scales\.y\.grace = \'35%\';\n\s*\}\n\s*scales\["y-right"\]\.grace = \'25%\';'
repl_grace = """function niceMax(val) {
        if (val <= 0) return 10;
        const order = Math.floor(Math.log10(val));
        const factor = Math.pow(10, order);
        const normalized = val / factor;
        let nice;
        if (normalized <= 1) nice = 1;
        else if (normalized <= 2) nice = 2;
        else if (normalized <= 2.5) nice = 2.5;
        else if (normalized <= 5) nice = 5;
        else nice = 10;
        return nice * factor;
    }
    
    if (scales.y) {
        scales.y.max = niceMax(maxLeft * 1.5);
    }
    scales["y-right"].max = niceMax(maxRight * 1.25);"""

content = re.sub(target_grace, repl_grace, content)

# Fix 2: Force parseFloat inside setfStackTotalPlugin
target_val = r'const val = layers\[l\]\.data\[j\];\n\s*if \(layers\[l\]\.meta\.data\[j\]\) anyMeta = layers\[l\]\.meta\.data\[j\];\n\s*if \(val\) \{'
repl_val = """const rawVal = layers[l].data[j];
             const val = rawVal ? parseFloat(rawVal) : 0;
             if (layers[l].meta.data[j]) anyMeta = layers[l].meta.data[j];
             if (val > 0) {"""

content = re.sub(target_val, repl_val, content)

# Also force parseFloat inside setfInjectDualYAxis
target_sum = r'dsClone\.data\.forEach\(function\(v, idx\) \{\n\s*if \(typeof v === "number" && !isNaN\(v\)\) \{'
repl_sum = """dsClone.data.forEach(function(v, idx) { 
        if (v !== null && v !== undefined && !isNaN(parseFloat(v))) {
            v = parseFloat(v);"""

content = re.sub(target_sum, repl_sum, content)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated niceMax and parseFloat!")

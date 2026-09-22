import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace lastValidMeta logic to track the layer and use the correct axis
target_loop = r'let lastValidMeta = null;\n\s*let anyMeta = null; // To get X coord even if sum is 0\n\s*for \(let l = 0; l < layers\.length; l\+\+\) \{\n\s*const rawVal = layers\[l\]\.data\[j\];\n\s*const val = rawVal \? parseFloat\(rawVal\) : 0;\n\s*if \(layers\[l\]\.meta\.data\[j\]\) anyMeta = layers\[l\]\.meta\.data\[j\];\n\s*if \(val > 0\) \{\n\s*sum \+= val;\n\s*lastValidMeta = layers\[l\]\.meta\.data\[j\];\n\s*\}\n\s*\}'

repl_loop = """let lastValidMeta = null;
          let lastValidLayer = null;
          let anyMeta = null; // To get X coord even if sum is 0
          
          for (let l = 0; l < layers.length; l++) {
             const rawVal = layers[l].data[j];
             const val = rawVal ? parseFloat(rawVal) : 0;
             if (layers[l].meta.data[j]) anyMeta = layers[l].meta.data[j];
             if (val > 0) {
                sum += val;
                lastValidMeta = layers[l].meta.data[j];
                lastValidLayer = layers[l];
             }
          }"""

content = re.sub(target_loop, repl_loop, content)

target_draw = r'if \(sum > 0 && lastValidMeta\) \{\n\s*ctx\.textBaseline = \'bottom\';\n\s*const xPos = lastValidMeta\.x;\n\s*const yPos = chart\.scales\.y\.getPixelForValue\(sum\);'

repl_draw = """if (sum > 0 && lastValidMeta && lastValidLayer) {
             ctx.textBaseline = 'bottom';
             const xPos = lastValidMeta.x;
             const yAxisId = lastValidLayer.meta.yAxisID || 'y';
             const yPos = chart.scales[yAxisId].getPixelForValue(sum);"""

content = re.sub(target_draw, repl_draw, content)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated setfStackTotalPlugin to use correct yAxisId!")
